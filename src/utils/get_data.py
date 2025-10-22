import requests
import pandas as pd

from pathlib import Path
import sys
# ajoute la racine du projet au sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from config import URL

# URL de l'API WHO pour l'espérance de vie


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
