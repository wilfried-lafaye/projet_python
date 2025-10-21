# app.py — Streamlit choroplèthe (ISO3) avec filtres année / sexe
from pathlib import Path
import re
import pandas as pd
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from geopandas.datasets import get_path
import streamlit as st
from streamlit_folium import st_folium

CLEANED = Path("data/cleaned/cleaneddata.csv")

SEX_LABEL = {
    "SEX_BTSX": "Deux sexes",
    "SEX_MLE": "Homme",
    "SEX_FMLE": "Femme",
}
SEX_LABEL_INV = {v: k for k, v in SEX_LABEL.items()}

# ---------- Chargements (mis en cache) ----------
@st.cache_data(show_spinner=False)
def load_cleaned(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.resolve()}")
    df = pd.read_csv(path)
    # Assainir colonnes attendues
    required = {"SpatialDimType", "SpatialDim", "TimeDim", "Dim1", "NumericValue"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"CSV missing columns: {sorted(missing)}")
    # garder uniquement pays
    df = df[df["SpatialDimType"].astype(str).str.upper() == "COUNTRY"].copy()
    # NumericValue -> float
    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")
    df.dropna(subset=["NumericValue"], inplace=True)
    return df

@st.cache_data(show_spinner=False)
def load_world() -> gpd.GeoDataFrame:
    world = gpd.read_file(get_path("naturalearth_lowres")).to_crs(epsg=4326)
    world = world[world["name"] != "Antarctica"].copy()
    # iso_a3 -> iso3 (quelques -99 -> None)
    world["iso3"] = world["iso_a3"].replace({"-99": None})
    return world[["name", "iso3", "geometry"]]

# ---------- Carte Folium ----------
def make_map(world_gdf: gpd.GeoDataFrame, data_df: pd.DataFrame, year: int, sex_code: str) -> folium.Map:
    df = data_df[(data_df["TimeDim"] == year) & (data_df["Dim1"] == sex_code)].copy()
    # Agréger une valeur par pays ISO3
    df = df[["SpatialDim", "NumericValue"]].groupby("SpatialDim", as_index=False)["NumericValue"].mean()
    df.rename(columns={"SpatialDim": "iso3"}, inplace=True)

    gdf = world_gdf.merge(df, on="iso3", how="left")

    bins = [50, 60, 70, 80, 87]
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=gdf.__geo_interface__,
        data=gdf,
        columns=["iso3", "NumericValue"],
        key_on="feature.properties.iso3",
        fill_color="Greens",
        fill_opacity=0.9,
        line_opacity=0.2,
        nan_fill_color="#e6e6e6",
        bins=bins,
        legend_name="Life expectancy at birth (years)",
    ).add_to(m)

    folium.GeoJson(
        gdf.to_json(),
        name="countries",
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
        tooltip=GeoJsonTooltip(
            fields=["name", "NumericValue"],
            aliases=["Country", "Life expectancy"],
            localize=True,
            labels=True,
            sticky=False,
        ),
    ).add_to(m)

    # Bandeau année / sexe
    label_html = f"""
    <div style="position:fixed;top:10px;left:20px;z-index:9999;font-size:22px;color:#c2702b;font-weight:600;">
      {year}
    </div>
    <div style="position:fixed;top:10px;left:100px;z-index:9999;font-size:22px;color:#c2702b;font-weight:600;">
      {SEX_LABEL.get(sex_code, sex_code)}
    </div>
    """
    m.get_root().html.add_child(folium.Element(label_html))
    return m

# ---------- UI ----------
st.set_page_config(page_title="Life expectancy map", layout="wide")
st.title("Life expectancy at birth — world choropleth")

try:
    df_clean = load_cleaned(CLEANED)
    world = load_world()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# Filtres (sidebar)
years = sorted(df_clean["TimeDim"].dropna().unique().tolist())
default_year = max(years) if years else None
sex_readable = ["Both sexes", "Male", "Female"]

st.sidebar.header("Filters")
year_sel = st.sidebar.selectbox("Year", years, index=(years.index(default_year) if default_year in years else 0))
sex_sel_readable = st.sidebar.radio("Sex", sex_readable, index=0)
sex_code = SEX_LABEL_INV[sex_sel_readable]

# Carte
with st.spinner("Building map..."):
    fmap = make_map(world, df_clean, year_sel, sex_code)
st_folium(fmap, height=600, width=None)

# Infos manquantes (optionnel)
missing = world.merge(
    df_clean[(df_clean["TimeDim"] == year_sel) & (df_clean["Dim1"] == sex_code)][["SpatialDim"]],
    left_on="iso3", right_on="SpatialDim", how="left"
)
missing = missing[missing["SpatialDim"].isna()][["name","iso3"]].sort_values("name")
with st.expander("Show countries without data for current filters"):
    st.dataframe(missing, use_container_width=True)
