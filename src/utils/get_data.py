import requests
import pandas as pd
from config import DEFAULT_CSV, WORLD_GEOJSON_URL
from pathlib import Path
import urllib.request
import json
import sys
# ajoute la racine du projet au sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from config import URL

# URL de l'API WHO pour l'espérance de vie

def load_world_geojson():
    with urllib.request.urlopen(WORLD_GEOJSON_URL, timeout=15) as resp:
        gj = json.load(resp)
    return gj

def load_clean_data():
    return pd.read_csv(DEFAULT_CSV)

# Requête GET vers l'API
response = requests.get(URL)
response.raise_for_status()

# Conversion de la réponse en JSON
json_data = response.json()

# Extraction des données dans la clé 'value'
records = json_data.get('value', [])

# Conversion en DataFrame pandas
df = pd.DataFrame.from_records(records)

# Chemin complet pour sauvegarder dans data/raw/rawdata.csv
output_path = "data/raw/rawdata.csv"

# Sauvegarde du DataFrame dans ce fichier CSV sans l'index
df.to_csv(output_path, index=False)

print(f"Données enregistrées dans {output_path}")
