from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

from src.pages.home import page_layout, register_callbacks
from src.components.histogramme import layout as histogram_layout

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

app.title = "Dashboard"
app.layout = html.Div([
    dcc.Location(id="url"),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Carte", href="/")),
            dbc.NavItem(dbc.NavLink("Histogramme", href="/histogram"))
        ],
        brand="Life Expectancy Dashboard",
        color="primary", dark=True,
    ),
    html.Div(id="page-content")
])

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname):
    if pathname == "/histogram":
        return histogram_layout
    return page_layout

register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8051)

