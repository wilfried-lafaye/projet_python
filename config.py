
# config.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = "/workspaces/projet_python/data/cleaned/cleaneddata.csv"

WORLD_GEOJSON_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
URL = "https://ghoapi.azureedge.net/api/WHOSIS_000001"