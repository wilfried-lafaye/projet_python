"""
Module de nettoyage et préparation des données.
Ce script charge les données brutes, effectue un nettoyage
des colonnes et des lignes, supprime les colonnes vides, 
et exporte les données nettoyées ainsi que les statistiques descriptives.
"""

import pandas as pd

# =============================================================
# CONFIGURATION GENERALE
# =============================================================
pd.set_option('display.max_columns', None)

# =============================================================
# CHARGEMENT DES DONNÉES
# =============================================================
# Chargement du fichier CSV brut
RAW_DATA_PATH = 'data/raw/raw_data.csv'
df = pd.read_csv(RAW_DATA_PATH)

# =============================================================
# NETTOYAGE DES DONNÉES
# =============================================================
# -- Nettoyage des chaînes de caractères --
df['ParentLocation'] = df['ParentLocation'].str.strip().str.lower()
df['Location'] = df['Location'].str.strip().str.lower()

# -- Suppression des doublons et valeurs manquantes --
df = df.drop_duplicates()
df = df.dropna(subset=['ParentLocation', 'Location'])

# =============================================================
# ANALYSE SOMMAIRE DES DONNÉES
# =============================================================
# Comptage des régions et pays distincts
nombre_region = df['ParentLocation'].nunique()  # renommer sans accent
print(f"Nombre de régions distinctes : {nombre_region}")

nombre_pays = df['Location'].nunique()
print(f"Nombre de pays distincts : {nombre_pays}")

# Export des statistiques initiales
statistiques_raw = df.describe(include='all')
statistiques_raw.to_csv('data/raw/statistiques.csv', encoding='utf-8')

# =============================================================
# SUPPRESSION DES COLONNES VIDES ET COLONNES INUTILISÉES
# =============================================================
def is_column_empty(series: pd.Series) -> bool:
    """Vérifie si une colonne est entièrement vide (NaN ou chaînes vides)."""
    if series.dropna().empty:
        return True
    if series.dtype == 'object':
        non_empty = series.dropna().apply(lambda x: str(x).strip() != '')
        return not non_empty.any()
    return False

# Identifier les colonnes vides
empty_cols = [col for col in df.columns if is_column_empty(df[col])]

# Suppression des colonnes entièrement vides
df = df.drop(columns=empty_cols)

df = df.drop(columns=['Language','DateModified'])  # Suppression des colonnes inutilisées

# =============================================================
# EXPORT DES DONNÉES NETTOYÉES
# =============================================================
statistiques_cleaned = df.describe(include='all')
statistiques_cleaned.to_csv('data/cleaned/statistiques_data_cleaned.csv', encoding='utf-8')

print(df.dtypes)


df.to_csv('data/cleaned/cleaned_data.csv', index=False)
