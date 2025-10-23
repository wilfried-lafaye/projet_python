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


st.set_page_config(page_title="Life expectancy — choropleth", layout="wide")
st.title("Life expectancy at birth — world choropleth")

#def load a mettre dans clean data et nécessaire ?

#@st.cache_data(show_spinner=False)
#def load_csv(p: Path) -> pd.DataFrame:
#    if not p.exists():
#        raise FileNotFoundError(f"Missing file: {p}")
#    df = pd.read_csv(p)
#    req = {"SpatialDimType", "SpatialDim", "TimeDim", "Dim1", "NumericValue"}
#    miss = req - set(df.columns)
#    if miss:
#        raise KeyError(f"CSV missing columns: {sorted(miss)}")
#    df = df[df["SpatialDimType"].astype(str).str.upper() == "COUNTRY"].copy()
#    df["SpatialDim"] = df["SpatialDim"].astype(str).str.upper()  # ISO3
#    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")
#    return df


@st.cache_data(show_spinner=False)
def load_world_geojson() -> dict:
    with urllib.request.urlopen(WORLD_GEOJSON_URL, timeout=15) as resp:
        gj = json.load(resp)
    return gj  # feature.id = ISO3 ; properties.name (ou ADMIN selon versions)


# Charger (chemin CSV fixe)
try:
    df = pd.read_csv(DEFAULT_CSV)
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


# Use direct values from Dim1 column (no normalization)
sex_codes_avail_raw = df.loc[df["TimeDim"] == year_sel, "Dim1"].dropna().unique().tolist()
# Filter the sex codes to those matching keys in SEXLBL inverse by label comparison
# Find which keys in SEXLBL have corresponding raw values in the CSV for the selected year
# We keep only those options whose values match any raw Dim1 value after stripping/lowercasing
# Since original normalizing used many variants, you may need to adjust this as needed
# For simplicity, just present the raw unique values here for user selection

sex_sel_readable = st.sidebar.radio("Sex (raw values)", sex_codes_avail_raw, index=0)
# Because no normalization, just use the selected raw value
sex_code_raw = sex_sel_readable


# --- Sous-ensemble filtré ---
subset = df[(df["TimeDim"] == year_sel) & (df["Dim1"] == sex_code_raw)].copy()



if subset.empty:
    st.warning("No data for this Year/Sex combination. Try another filter.")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    folium.GeoJson(world_gj, name="countries").add_to(m)
    st_folium(m, height=650, width=None)
    st.stop()


# Agrège une valeur par pays ISO3
subset = subset.groupby("SpatialDim", as_index=False)["NumericValue"].mean()
subset.rename(columns={"SpatialDim": "iso3"}, inplace=True)
subset["iso3"] = subset["iso3"].str.upper()


# ---------- Carte Folium (légende Folium déplacée en bas, bandeau plus bas) ----------
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


# Choropleth AVEC légende intégrée (une seule légende)
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


# Déplacer la légende intégrée de Folium en bas-centre
legend_css = """
<style>
.legend {
  position: fixed !important;
  bottom: 18px; left:18px;
  transform: None;
  z-index: 9999;
  box-shadow: 0 2px 6px rgba(0,0,0,.25);
  border-radius: 6px;
  font-size: 12px;
}
</style>
"""
m.get_root().html.add_child(folium.Element(legend_css))


# Tooltips: injecte la valeur + uniformise le nom
val_by_iso3 = dict(zip(subset["iso3"], subset["NumericValue"]))
world_gj_tt = {"type": world_gj["type"], "features": []}
for feat in world_gj["features"]:
    props = dict(feat.get("properties", {}))
    props["value"] = val_by_iso3.get(feat.get("id"))
    if "ADMIN" in props and "name" not in props:
        props["name"] = props["ADMIN"]
    world_gj_tt["features"].append({
        "type": feat.get("type", "Feature"),
        "id": feat.get("id"),
        "properties": props,
        "geometry": feat.get("geometry"),
    })


tooltip = folium.features.GeoJsonTooltip(
    fields=["name", "value"], aliases=["Country", "Life expectancy"],
    localize=True, labels=True, sticky=False,
)
folium.GeoJson(
    world_gj_tt,
    name="countries",
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
    tooltip=tooltip,
).add_to(m)


# Bandeau Année / Sexe : plus bas (ajuste 'top' si tu veux encore descendre)
label_html = f"""
<div style="
  position:fixed; top:230px; left:25px; z-index:9999;
  background: rgba(255,255,255,0.88);
  padding: 8px 14px; border-radius: 12px;
  font-size: 22px; color:#c2702b; font-weight:800;">
  {year_sel} &nbsp; {sex_sel_readable}
</div>
"""
m.get_root().html.add_child(folium.Element(label_html))


st_folium(m, height=650, width=None)
