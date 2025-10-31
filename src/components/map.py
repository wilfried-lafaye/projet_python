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

# Libellés lisibles
SEX_LABEL = {"SEX_FMLE": "Female", "SEX_MLE": "Male", "SEX_BTSX": "Both sexes"}
SEX_LABEL_INV = {v: k for k, v in SEX_LABEL.items()}

st.set_page_config(page_title="Life expectancy — choropleth", layout="wide")
st.markdown(
    "<h1 style='text-align:center;margin-top:0;'>Life expectancy at birth in the world</h1>",
    unsafe_allow_html=True,
)

# ----------------------- Loaders -----------------------
@st.cache_data(show_spinner=False)
def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    df = pd.read_csv(p)
    req = {"SpatialDimType", "SpatialDim", "TimeDim", "Dim1", "NumericValue"}
    miss = req - set(df.columns)
    if miss:
        raise KeyError(f"CSV missing columns: {sorted(miss)}")

    # Pays uniquement + conversions utiles
    df = df[df["SpatialDimType"].astype(str).str.upper() == "COUNTRY"].copy()
    df["SpatialDim"] = df["SpatialDim"].astype(str).str.upper()      # ISO3
    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")

    # Normalisation Dim1 -> Dim1_norm
    mapping = {
        "sexfmle": "SEX_FMLE", "fmle": "SEX_FMLE", "female": "SEX_FMLE", "f": "SEX_FMLE", "femme": "SEX_FMLE",
        "sexmle": "SEX_MLE", "mle": "SEX_MLE", "male": "SEX_MLE", "m": "SEX_MLE", "homme": "SEX_MLE",
        "sexbtsx": "SEX_BTSX", "btsx": "SEX_BTSX", "bothsexes": "SEX_BTSX", "bothsex": "SEX_BTSX", "both": "SEX_BTSX",
    }
    norm = (
        df["Dim1"]
        .astype(str)
        .str.strip().str.lower().str.replace(" ", "").str.replace("-", "").str.replace("_", "")
        .map(mapping)
    )
    df["Dim1_norm"] = norm
    # Conserver les codes déjà normalisés exacts
    mask_exact = df["Dim1"].isin(["SEX_FMLE", "SEX_MLE", "SEX_BTSX"])
    df.loc[mask_exact, "Dim1_norm"] = df.loc[mask_exact, "Dim1"]

    return df

@st.cache_data(show_spinner=False)
def load_world_geojson() -> dict:
    with urllib.request.urlopen(WORLD_GEOJSON_URL, timeout=15) as resp:
        return json.load(resp)  # feature.id = ISO3 ; properties.name/ADMIN

def patch_world_ids(gj: dict) -> dict:
    """
    Corrige certains IDs du GeoJSON pour qu'ils matchent l'ISO3 du CSV.
    - South Sudan  -> SSD
    - Côte d'Ivoire -> CIV
    - Eswatini/Swaziland -> SWZ
    - Myanmar/Burma -> MMR
    (Tu peux ajouter d'autres cas au besoin.)
    """
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        name = props.get("name") or props.get("ADMIN") or ""
        # Normalise quelques cas fréquents
        if name == "South Sudan":
            feat["id"] = "SSD"
        elif name in ("Côte d'Ivoire", "Ivory Coast"):
            feat["id"] = "CIV"
        elif name in ("Eswatini", "Swaziland", "Eswatini, Kingdom of"):
            feat["id"] = "SWZ"
        elif name in ("Myanmar", "Burma"):
            feat["id"] = "MMR"
        # Si jamais l'ID est en minuscule, remonte-le
        if isinstance(feat.get("id"), str):
            feat["id"] = feat["id"].upper()
    return gj

# ----------------------- Chargement -----------------------
try:
    df = load_csv(DEFAULT_CSV)
    world_gj = load_world_geojson()
    world_gj = patch_world_ids(world_gj)  # <-- IMPORTANT pour South Sudan = SSD
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# ----------------------- Filtres dynamiques -----------------------
years = sorted(df["TimeDim"].dropna().unique().tolist())
if not years:
    st.warning("Aucune année disponible dans le CSV.")
    st.stop()

st.sidebar.header("Filters")
default_year = years[-1]
year_sel = st.sidebar.selectbox("Year", years, index=years.index(default_year))

# Sexes disponibles (normalisés → libellés lisibles)
avail_codes = df.loc[df["TimeDim"] == year_sel, "Dim1_norm"].dropna().unique().tolist()
sex_options_readable = [SEX_LABEL[c] for c in ["SEX_FMLE", "SEX_MLE", "SEX_BTSX"] if c in avail_codes]
if not sex_options_readable:
    st.warning("Aucun sexe disponible pour cette année. Choisis une autre année.")
    st.stop()
sex_sel_readable = st.sidebar.radio("Sex", sex_options_readable, index=0)
sex_code = SEX_LABEL_INV[sex_sel_readable]

# ----------------------- Sous-ensemble & agrégation -----------------------
subset = df[(df["TimeDim"] == year_sel) & (df["Dim1_norm"] == sex_code)].copy()
if subset.empty:
    st.warning("No data for this Year/Sex combination. Try another filter.")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()

subset = subset.groupby("SpatialDim", as_index=False)["NumericValue"].mean()
subset.rename(columns={"SpatialDim": "iso3"}, inplace=True)
subset["iso3"] = subset["iso3"].str.upper()

# ----------------------- Carte & bins -----------------------
vals = subset["NumericValue"].dropna().to_numpy()
if vals.size == 0:
    st.warning("No numeric values for this selection.")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()

vmin, vmax = float(np.min(vals)), float(np.max(vals))
standard = [50, 60, 70, 80, 87]
if vmin >= standard[0] and vmax <= standard[-1]:
    bins = standard
else:
    low, high = math.floor(vmin), math.ceil(vmax)
    cuts = sorted(set([low, 50, 60, 70, 80, 87, high]))
    cuts = [c for i, c in enumerate(cuts) if i == 0 or c > cuts[i - 1]]
    if len(cuts) < 3:
        cuts = list(np.linspace(low, high if high > low else low + 1, 5))
    bins = cuts

m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")

# Choropleth avec une seule légende (déplacée via CSS)
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

# Déplacer la légende intégrée en bas-gauche
legend_css = """
<style>
.legend {
  position: fixed !important;
  bottom: 18px; left: 18px;
  transform: none;
  z-index: 9999;
  box-shadow: 0 2px 6px rgba(0,0,0,.25);
  border-radius: 6px;
  font-size: 12px;
}
</style>
"""
m.get_root().html.add_child(folium.Element(legend_css))

# ----------------------- Tooltips robustes -----------------------
val_by_iso3 = dict(zip(subset["iso3"], subset["NumericValue"]))
world_gj_tt = {"type": world_gj["type"], "features": []}
for feat in world_gj["features"]:
    props = dict(feat.get("properties", {}))
    val = val_by_iso3.get(feat.get("id"))
    props["value_str"] = f"{val:.1f}" if val is not None and not pd.isna(val) else "No data"
    if "ADMIN" in props and "name" not in props:
        props["name"] = props["ADMIN"]
    world_gj_tt["features"].append({
        "type": feat.get("type", "Feature"),
        "id": feat.get("id"),
        "properties": props,
        "geometry": feat.get("geometry"),
    })

tooltip = folium.features.GeoJsonTooltip(
    fields=["name", "value_str"],
    aliases=["Country", "Life expectancy"],
    localize=True, labels=True, sticky=False,
)
folium.GeoJson(
    world_gj_tt,
    name="countries",
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
    tooltip=tooltip,
).add_to(m)

# ----------------------- Badge Année / Sexe -----------------------
badge_css = """
<style>
.year-sex-badge{
  position: fixed;
  top: 300px; left: 25px; z-index: 9999;
  background: rgba(255,255,255,0.9);
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 22px;
  font-weight: 800;
  color: #c2702b;
  box-shadow: 0 2px 6px rgba(0,0,0,.15);
}
</style>
"""
m.get_root().html.add_child(folium.Element(badge_css))
m.get_root().html.add_child(
    folium.Element(f'<div class="year-sex-badge">{year_sel} &nbsp; {SEX_LABEL[sex_code]}</div>')
)



st_folium(m, height=650, width=None)
