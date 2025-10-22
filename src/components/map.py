#!/usr/bin/env python3
# Streamlit + Folium — choroplèthe ISO3, sans GeoPandas (robuste genres/années)
import math
import numpy as np
from pathlib import Path
import json
import urllib.request
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

# --- Config / constantes ---
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "cleaned" / "cleaneddata.csv"
WORLD_GEOJSON_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"

SEXLBL = {"SEX_BTSX": "Both sexes", "SEX_MLE": "Male", "SEX_FMLE": "Female"}
SEXLBL_INV = {v: k for k, v in SEXLBL.items()}

def normalize_dim1(val: str | None) -> str | None:
    if val is None:
        return None
    s = str(val).strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    # variantes OMS/courantes
    if s in {"sexbtsx", "btsx", "bothsexes", "both", "bothsex"}:
        return "SEX_BTSX"
    if s in {"sexmle", "mle", "male", "m", "homme"}:
        return "SEX_MLE"
    if s in {"sexfmle", "fmle", "female", "f", "femme"}:
        return "SEX_FMLE"
    # cas déjà normalisés
    if s in {"sex_btsx", "sex_mle", "sex_fmle"}:
        return s.upper()
    return None

st.set_page_config(page_title="Life expectancy — choropleth", layout="wide")
st.title("Life expectancy at birth — world choropleth")

# --- Sidebar: chemin CSV ---
csv_path_str = st.sidebar.text_input("Chemin du CSV nettoyé", str(DEFAULT_CSV))
CSV = Path(csv_path_str)

@st.cache_data(show_spinner=False)
def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    df = pd.read_csv(p)
    req = {"SpatialDimType","SpatialDim","TimeDim","Dim1","NumericValue"}
    miss = req - set(df.columns)
    if miss:
        raise KeyError(f"CSV missing columns: {sorted(miss)}")

    # Garde pays + types
    df = df[df["SpatialDimType"].astype(str).str.upper()=="COUNTRY"].copy()
    df["SpatialDim"]  = df["SpatialDim"].astype(str).str.upper()       # ISO3
    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")
    df = df.dropna(subset=["NumericValue"])

    # Normalise sexe
    df["Dim1_norm"] = df["Dim1"].apply(normalize_dim1)
    return df

@st.cache_data(show_spinner=False)
def load_world_geojson() -> dict:
    with urllib.request.urlopen(WORLD_GEOJSON_URL, timeout=15) as resp:
        gj = json.load(resp)
    return gj  # feature.id = ISO3 ; properties.name (ou ADMIN selon versions)

# Charger
try:
    df = load_csv(CSV)
    world_gj = load_world_geojson()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# --- Filtres dynamiques ---
years = sorted(df["TimeDim"].dropna().unique().tolist())
if not years:
    st.warning("Aucune année disponible dans le CSV.")
    st.stop()

st.sidebar.header("Filters")
default_year = years[-1]
year_sel = st.sidebar.selectbox("Year", years, index=years.index(default_year))

# sexes disponibles pour l'année choisie (après normalisation)
sex_codes_avail = (
    df.loc[df["TimeDim"] == year_sel, "Dim1_norm"].dropna().unique().tolist()
)
sex_options_readable = [SEXLBL[c] for c in ["SEX_BTSX","SEX_MLE","SEX_FMLE"] if c in sex_codes_avail]

if not sex_options_readable:
    st.warning("Aucun sexe disponible pour cette année. Choisis une autre année.")
    st.stop()

sex_sel_readable = st.sidebar.radio("Sex", sex_options_readable, index=0)
sex_code = SEXLBL_INV[sex_sel_readable]

# --- Sous-ensemble filtré ---
subset = df[(df["TimeDim"] == year_sel) & (df["Dim1_norm"] == sex_code)].copy()

# Petit panneau debug (optionnel) : montre ce qui existe réellement pour cette année
with st.expander("Diagnostic (disponibilités pour l'année sélectionnée)"):
    st.write("Sexes trouvés (bruts) :", sorted(df.loc[df["TimeDim"]==year_sel, "Dim1"].dropna().unique().tolist()))
    st.write("Sexes normalisés :", sorted(sex_codes_avail))

if subset.empty:
    st.warning("No data for this Year/Sex combination. Try another filter.")
    m = folium.Map(location=[20,0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()

# Agrège une valeur par pays ISO3
subset = subset.groupby("SpatialDim", as_index=False)["NumericValue"].mean()
subset.rename(columns={"SpatialDim":"iso3"}, inplace=True)
subset["iso3"] = subset["iso3"].str.upper()

# ---------- Carte Folium robuste ----------
# valeurs présentes pour ce filtre (après l'agrégation)
vals = subset["NumericValue"].dropna().to_numpy()

# Sécurité: si aucune valeur exploitable, afficher juste la couche pays
if vals.size == 0:
    st.warning("No numeric values for this selection.")
    m = folium.Map(location=[20,0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()

vmin, vmax = float(np.min(vals)), float(np.max(vals))

# 1) bins 'standard' OMS si ça couvre toutes les valeurs
standard = [50, 60, 70, 80, 87]
if vmin >= standard[0] and vmax <= standard[-1]:
    bins = standard
else:
    # 2) sinon, on fabrique des bins dynamiques qui englobent TOUTES les valeurs
    low  = math.floor(vmin)
    high = math.ceil(vmax)
    # garder des coupures "par dizaines" + bornes min/max
    cuts = sorted(set([low, 50, 60, 70, 80, 87, high]))
    # Folium exige des bornes strictement croissantes et au moins 3 seuils
    cuts = [c for i, c in enumerate(cuts) if i == 0 or c > cuts[i-1]]
    if len(cuts) < 3:
        # si très peu de variance, on crée 4 intervalles égaux
        cuts = list(np.linspace(low, high if high > low else low + 1, 5))
    bins = cuts

# Carte + choroplèthe
m = folium.Map(location=[20,0], zoom_start=2, tiles="cartodbpositron")
folium.Choropleth(
    geo_data=world_gj,
    data=subset,
    columns=["iso3","NumericValue"],
    key_on="feature.id",
    fill_color="Greens",
    fill_opacity=0.9,
    line_opacity=0.2,
    nan_fill_color="#e6e6e6",
    bins=bins,                     # <-- bins dynamiques
    legend_name="Life expectancy at birth (years)",
).add_to(m)

# Tooltips: on injecte la valeur dans properties + on choisit le bon champ de nom
val_by_iso3 = dict(zip(subset["iso3"], subset["NumericValue"]))
world_gj_tt = {"type": world_gj["type"], "features": []}
for feat in world_gj["features"]:
    props = dict(feat.get("properties", {}))
    props["value"] = val_by_iso3.get(feat.get("id"))
    # uniformiser key du nom
    if "ADMIN" in props and "name" not in props:
        props["name"] = props["ADMIN"]
    world_gj_tt["features"].append({
        "type": feat.get("type","Feature"),
        "id": feat.get("id"),
        "properties": props,
        "geometry": feat.get("geometry"),
    })

tooltip = folium.features.GeoJsonTooltip(
    fields=["name","value"], aliases=["Country","Life expectancy"],
    localize=True, labels=True, sticky=False,
)
folium.GeoJson(
    world_gj_tt,
    name="countries",
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
    tooltip=tooltip,
).add_to(m)

# Bandeau Année / Sexe
label_html = f"""
<div style="position:fixed;top:10px;left:20px;z-index:9999;font-size:22px;color:#c2702b;font-weight:600;">
  {year_sel}
</div>
<div style="position:fixed;top:10px;left:100px;z-index:9999;font-size:22px;color:#c2702b;font-weight:600;">
  {sex_sel_readable}
</div>
"""
m.get_root().html.add_child(folium.Element(label_html))

st_folium(m, height=650, width=None)
