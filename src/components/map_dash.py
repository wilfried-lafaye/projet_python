import folium
import numpy as np

def create_map(df, world_gj, selected_year, selected_sex):
    """
    Génère une carte choroplèthe Folium du monde selon l'année et le sexe sélectionnés.

    Args:
        df (pd.DataFrame): DataFrame contenant les données nettoyées.
        world_gj (dict): GeoJSON des frontières.
        selected_year: Année à afficher.
        selected_sex: Sexe à afficher.

    Returns:
        str: HTML de la carte Folium à intégrer à Dash.
    """
    # Filtrer les données selon sélection
    subset = df[(df["TimeDim"] == selected_year) & (df["Dim1"] == selected_sex)].copy()

    # Calculer l'échelle de couleurs (bornes)
    values = subset["NumericValue"].dropna().values
    if len(values) == 0:
        vmin, vmax = 60, 90
    else:
        vmin, vmax = np.percentile(values, 2), np.percentile(values, 98)

    # Créer la carte
    m = folium.Map(zoom_start=2, location=[20, 0], tiles="cartodb positron")

    # Ajouter la couche choroplèthe principale
    folium.Choropleth(
        geo_data=world_gj,
        name="Choropleth",
        data=subset,
        columns=["SpatialDim", "NumericValue"],
        key_on="feature.id",
        fill_color="YlGnBu",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Life expectancy at birth",
        nan_fill_color="lightgrey",
        highlight=True,
        bins=10,
        reset=True,
        smooth_factor=0,
    ).add_to(m)

    # Optionnel : pas de tooltip, pas de GeoJson supplémentaire

    return m._repr_html_()
