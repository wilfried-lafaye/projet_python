
import pandas as pd

# Charger le fichier CSV
df = pd.read_csv('../data/raw/raw_data.csv')  # Correction du chemin relatif

# Nettoyer les colonnes : enlever les espaces et mettre en minuscules
df['ParentLocation'] = df['ParentLocation'].str.strip().str.lower()
df['Location'] = df['Location'].str.strip().str.lower()

# Supprimer les lignes dupliquées
df = df.drop_duplicates()

# Supprimer les lignes avec des valeurs manquantes dans ParentLocation ou Location
df = df.dropna(subset=['ParentLocation', 'Location'])

# Compter le nombre de régions uniques dans la colonne "ParentLocation"
nombre_région = df['ParentLocation'].nunique()
print(f"Nombre de régions distincts : {nombre_région}")

# Compter le nombre de pays uniques dans la colonne "Location"
nombre_pays = df['Location'].nunique()
print(f"Nombre de pays distincts : {nombre_pays}")

# Sauvegarder le fichier nettoyé si besoin
df.to_csv('../data/cleaned_data.csv', index=False) 