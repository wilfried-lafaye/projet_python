# app.py — Streamlit choroplèthe (ISO3) avec filtres année / sexe
from pathlib import Path
import pandas as pd
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from geodatasets import get_path   # remplace l'ancien geopandas.datasets.get_path
import streamlit as st
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parents[2]  # <- remonte de src/components/ à la racine du repo
CLEANED = (ROOT / "data" / "cleaned" / "cleaneddata.csv").resolve()


SEX_LABEL = {
    "SEX_BTSX": "Both sexes",
    "SEX_MLE": "Male",
    "SEX_FMLE": "Female",
}
SEX_LABEL_INV = {v: k for k, v in SEX_LABEL.items()}

# ----- chargements (cache) -----
@st.cache_data(show_spinner=False)
def load_cleaned(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    df = pd.read_csv(p)
    needed = {"SpatialDimType","SpatialDim","TimeDim","Dim1","NumericValue"}
    miss = needed - set(df.columns)
    if miss:
        raise KeyError(f"CSV missing columns: {sorted(miss)}")
    df = df[df["SpatialDimType"].astype(str).str.upper() == "COUNTRY"].copy()
    df["NumericValue"] = pd.to_numeric(df["NumericValue"], errors="coerce")
    df.dropna(subset=["NumericValue"], inplace=True)
    # ISO3 en majuscules
    df["SpatialDim"] = df["SpatialDim"].astype(str).str.upper()
    return df

@st.cache_data(show_spinner=False)
def load_world() -> gpd.GeoDataFrame:
    """
    Charge la couche monde (ISO3) avec 3 fallbacks :
    1) geodatasets.get_path("naturalearth_lowres")
    2) GeoJSON en ligne de Folium (world-countries.json)
    3) GeoJSON local si présent: data/ref/world-countries.json
    """
    # 1) geodatasets
    try:
        from geodatasets import get_path
        world_path = get_path("naturalearth_lowres")
        world = gpd.read_file(world_path).to_crs(epsg=4326)
        # Natural Earth: iso_a3, certains '-99' -> None
        world = world[world["name"] != "Antarctica"].copy()
        world["iso3"] = world["iso_a3"].replace({"-99": None})
        return world[["name", "iso3", "geometry"]]
    except Exception:
        pass  # on tente les fallbacks

    # 2) GeoJSON en ligne (Folium demo) — feature.id = ISO3
    try:
        import json, urllib.request, tempfile
        url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
        with urllib.request.urlopen(url, timeout=10) as resp:
            gj = json.load(resp)
        # Construire un GeoDataFrame depuis le GeoJSON
        gdf = gpd.GeoDataFrame.from_features(gj["features"], crs="EPSG:4326")
        # Normaliser les champs : name (ADMIN) et iso3 (id)
        if "name" not in gdf.columns:
            gdf["name"] = gdf.get("ADMIN", gdf.get("name", None))
        gdf["iso3"] = gdf.get("id")
        gdf = gdf[gdf["iso3"].notna()].copy()
        # Retirer l’Antarctique si présent
        gdf = gdf[gdf["name"].astype(str).str.lower() != "antarctica"]
        return gdf[["name", "iso3", "geometry"]]
    except Exception:
        pass

    # 3) GeoJSON local (si tu l’as ajouté au repo)
    local = (ROOT / "data" / "ref" / "world-countries.json")
    if local.exists():
        gdf = gpd.read_file(local).to_crs(epsg=4326)
        if "name" not in gdf.columns:
            gdf["name"] = gdf.get("ADMIN", gdf.get("name", None))
        if "iso3" not in gdf.columns:
            gdf["iso3"] = gdf.get("id")  # beaucoup de fichiers ont 'id' = ISO3
        gdf = gdf[gdf["iso3"].notna()].copy()
        gdf = gdf[gdf["name"].astype(str).str.lower() != "antarctica"]
        return gdf[["name", "iso3", "geometry"]]

    # Si tout échoue :
    raise RuntimeError(
        "Impossible de charger la couche monde. "
        "Installe geodatasets OU place un GeoJSON local dans data/ref/world-countries.json."
    )


def make_map(world_gdf: gpd.GeoDataFrame, data_df: pd.DataFrame, year: int, sex_code: str) -> folium.Map:
    # 1) Filtrer & agréger une valeur par pays ISO3
    df = data_df[(data_df["TimeDim"] == year) & (data_df["Dim1"] == sex_code)].copy()
    if df.empty:
        # Pas de données pour ce filtre → carte vide mais sans planter
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
        folium.GeoJson(world_gdf.to_json(), name="countries").add_to(m)
        folium.map.LayerControl(collapsed=True).add_to(m)
        return m

    df = df.groupby("SpatialDim", as_index=False)["NumericValue"].mean()
    df.rename(columns={"SpatialDim": "iso3"}, inplace=True)
    df["iso3"] = df["iso3"].astype(str).str.upper()

    # 2) Jointure avec la couche monde
    gdf = world_gdf.merge(df, on="iso3", how="left")

    # 3) Carte choroplèthe
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    bins = [50, 60, 70, 80, 87]

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

    # 4) Tooltip robuste : seulement si les champs existent
    available = set(gdf.columns.astype(str))
    fields = [c for c in ["name", "NumericValue"] if c in available]
    if fields:
        folium.GeoJson(
            gdf.to_json(),
            name="countries",
            style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
            tooltip=GeoJsonTooltip(
                fields=fields,
                aliases=["Country", "Life expectancy"][: len(fields)],
                localize=True,
                labels=True,
                sticky=False,
            ),
        ).add_to(m)
    else:
        # fallback sans tooltip
        folium.GeoJson(
            gdf.to_json(),
            name="countries",
            style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
        ).add_to(m)

    return m

# ----- UI -----
st.set_page_config(page_title="Life expectancy — choropleth", layout="wide")
st.title("Life expectancy at birth — world choropleth")

try:
    df_clean = load_cleaned(CLEANED)
    world = load_world()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# Filtres
years = sorted(df_clean["TimeDim"].dropna().unique().tolist())
default_year = years[-1] if years else None
sex_readable = ["Both sexes","Male","Female"]

st.sidebar.header("Filters")
year_sel = st.sidebar.selectbox("Year", years, index=(years.index(default_year) if default_year in years else 0))
sex_sel_readable = st.sidebar.radio("Sex", sex_readable, index=0)
sex_code = SEX_LABEL_INV[sex_sel_readable]

# Carte
with st.spinner("Building map..."):
    fmap = make_map(world, df_clean, year_sel, sex_code)
st_folium(fmap, height=650, width=None)

# (optionnel) liste des pays sans donnée pour ce filtre
missing = world.merge(
    df_clean[(df_clean["TimeDim"]==year_sel)&(df_clean["Dim1"]==sex_code)][["SpatialDim"]],
    left_on="iso3", right_on="SpatialDim", how="left")
missing = missing[missing["SpatialDim"].isna()][["name","iso3"]].sort_values("name")
with st.expander("Countries without data for current filters"):
    st.dataframe(missing, use_container_width=True)
