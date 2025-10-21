#!/usr/bin/env python3
# Streamlit + Folium — choroplèthe ISO3, sans GeoPandas.

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
SEX_LABEL = {"SEX_BTSX": "Both sexes", "SEX_MLE": "Male", "SEX_FMLE": "Female"}
SEX_LABEL_INV = {v: k for k, v in SEX_LABEL.items()}

st.set_page_config(page_title="Life expectancy — choropleth", layout="wide")
st.title("Life expectancy at birth — world choropleth")

# --- Sidebar: chemin CSV + filtres ---
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
    df = df[df["SpatialDimType"].astype(str).str.upper()=="COUNTRY"].copy()
    df["SpatialDim"] = df["SpatialDim"].astype(str).str.upper()
    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")
    df = df.dropna(subset=["NumericValue"])
    return df

@st.cache_data(show_spinner=False)
def load_world_geojson() -> dict:
    with urllib.request.urlopen(WORLD_GEOJSON_URL, timeout=15) as resp:
        gj = json.load(resp)
    # Dans ce fichier, feature.id = ISO3 ; properties.ADMIN = nom
    return gj

# Charger données + monde
try:
    df = load_csv(CSV)
    world_gj = load_world_geojson()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

years = sorted(df["TimeDim"].dropna().unique().tolist())
if not years:
    st.warning("Aucune année disponible dans le CSV.")
    st.stop()

sex_readable = ["Both sexes","Male","Female"]
default_year = years[-1]
st.sidebar.header("Filters")
year_sel = st.sidebar.selectbox("Year", years, index=years.index(default_year))
sex_sel_readable = st.sidebar.radio("Sex", sex_readable, index=0)
sex_code = SEX_LABEL_INV[sex_sel_readable]

# Sous-ensemble filtré
subset = df[(df["TimeDim"]==year_sel) & (df["Dim1"]==sex_code)].copy()
if subset.empty:
    st.warning("No data for this Year/Sex combination. Try another filter.")
    # Afficher juste la couche pays
    m = folium.Map(location=[20,0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()

# Agréger une valeur par pays ISO3
subset = subset.groupby("SpatialDim", as_index=False)["NumericValue"].mean()
subset.rename(columns={"SpatialDim":"iso3"}, inplace=True)
subset["iso3"] = subset["iso3"].str.upper()

# ---------- Carte Folium robuste ----------
m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
bins = [50, 60, 70, 80, 87]

# Choroplèthe : key_on = feature.id (ISO3) pour ce GeoJSON
folium.Choropleth(
    geo_data=world_gj,
    data=subset,
    columns=["iso3", "NumericValue"],
    key_on="feature.id",
    fill_color="Greens",
    fill_opacity=0.9,
    line_opacity=0.2,
    nan_fill_color="#e6e6e6",
    bins=bins,
    legend_name="Life expectancy at birth (years)",
).add_to(m)

# --------- Tooltips robustes ---------
# 1) Injecter la valeur dans les propriétés du GeoJSON (pour pouvoir l'afficher)
val_by_iso3 = dict(zip(subset["iso3"], subset["NumericValue"]))
# On clone pour ne pas modifier l'original en cache
world_gj_for_tooltip = {"type": world_gj["type"], "features": []}
for feat in world_gj["features"]:
    props = dict(feat.get("properties", {}))
    props["value"] = val_by_iso3.get(feat.get("id"))  # None si manquant
    world_gj_for_tooltip["features"].append({
        "type": feat.get("type", "Feature"),
        "id": feat.get("id"),
        "properties": props,
        "geometry": feat.get("geometry"),
    })

# 2) Déterminer le bon champ de nom (ADMIN ou name)
sample_props = world_gj_for_tooltip["features"][0]["properties"]
name_key = "ADMIN" if "ADMIN" in sample_props else ("name" if "name" in sample_props else None)

# 3) Construire le tooltip seulement avec les champs disponibles
tooltip_fields, tooltip_aliases = [], []
if name_key:
    tooltip_fields.append(name_key)
    tooltip_aliases.append("Country")
tooltip_fields.append("value")
tooltip_aliases.append("Life expectancy")

folium.GeoJson(
    world_gj_for_tooltip,
    name="countries",
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
    tooltip=folium.features.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True,
        labels=True,
        sticky=False,
    ),
).add_to(m)

st_folium(m, height=650, width=None)

# Choroplèthe : key_on est feature.id (ISO3) pour ce GeoJSON
folium.Choropleth(
    geo_data=world_gj,
    data=subset,
    columns=["iso3","NumericValue"],
    key_on="feature.id",
    fill_color="Greens",
    fill_opacity=0.9,
    line_opacity=0.2,
    nan_fill_color="#e6e6e6",
    bins=bins,
    legend_name="Life expectancy at birth (years)",
).add_to(m)

# Tooltips robustes : nom du pays (properties.ADMIN) + valeur si dispo
def feature_style(_): return {"fillOpacity": 0, "color": "transparent"}
tooltip = folium.features.GeoJsonTooltip(
    fields=["ADMIN"],  # nom du pays
    aliases=["Country"],
    localize=True, sticky=False, labels=True,
)

folium.GeoJson(
    world_gj,
    name="countries",
    style_function=feature_style,
    tooltip=tooltip
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

# (facultatif) Aperçu rapide
with st.expander("Preview (first 10 rows)"):
    st.dataframe(subset.head(10), use_container_width=True)
