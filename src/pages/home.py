# src/pages/home.py
import dash
from dash import dcc, html, Output, Input
import dash_bootstrap_components as dbc
from src.utils.get_data import load_clean_data, load_world_geojson
from src.components.map_dash import create_map

df = load_clean_data()
world_gj = load_world_geojson()
years = sorted(df["TimeDim"].dropna().unique().tolist())
sex_codes_avail_raw = ['Female', 'Both', 'Male']

page_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Life expectancy at birth — world choropleth"),
            html.Label("Year"),
            dcc.Dropdown(id="year-dropdown", options=[{"label": y, "value": y} for y in years], value=years[-1]),
            html.Br(),
            html.Label("Sex"),
            dcc.RadioItems(id="sex-radio", options=[{"label": s, "value": s} for s in sex_codes_avail_raw], value="Female"),
        ], width=3, style={"padding": "20px", "backgroundColor": "#f8f9fa", "borderRadius": "8px"}),
        dbc.Col([
            html.Iframe(id="map-iframe", srcDoc=None, style={"width": "100%", "height": "650px", "border": "none"}),
        ], width=9)
    ])
], fluid=True)

def register_callbacks(app):
    @app.callback(
        Output("map-iframe", "srcDoc"),
        [Input("year-dropdown", "value"), Input("sex-radio", "value")]
    )
    def updatemap(year_selected, sex_selected):
        return create_map(df, world_gj, year_selected, sex_selected)
