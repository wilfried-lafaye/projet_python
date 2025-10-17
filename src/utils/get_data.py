import requests
import pandas as pd

# URL de l'API WHO pour l'espérance de vie
url = "https://ghoapi.azureedge.net/api/WHOSIS_000001"

# Requête GET vers l'API
response = requests.get(url)
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
