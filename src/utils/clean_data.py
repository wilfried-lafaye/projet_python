"""
Module de nettoyage et préparation des données.
Ce script charge les données brutes, effectue un nettoyage
des colonnes et des lignes, supprime les colonnes vides,
et exporte les données nettoyées ainsi que les statistiques descriptives.
"""

import pandas as pd
import pycountry as pc
from geopy.geocoders import Nominatim

# =============================================================
# CONFIGURATION GENERALE
# =============================================================
pd.set_option('display.max_columns', None)
geolocator = Nominatim(user_agent="mon_app_unique_et_descriptive")

# =============================================================
# CHARGEMENT DES DONNÉES
# =============================================================
RAW_DATA_PATH = 'data/raw/rawdata.csv'
df = pd.read_csv(RAW_DATA_PATH)


# =============================================================
# FONCTIONS UTILITAIRES
# =============================================================
def is_column_empty(series: pd.Series) -> bool:
    """Vérifie si une colonne est entièrement vide (NaN ou chaînes vides)."""
    if series.dropna().empty:
        return True
    if series.dtype == 'object':
        non_empty = series.dropna().apply(lambda x: str(x).strip() != '')
        return not non_empty.any()
    return False

# =============================================================
# SUPPRESSION DES COLONNES VIDES ET INUTILES
# =============================================================
# Identifier les colonnes vides
empty_cols = [col for col in df.columns if is_column_empty(df[col])]

# Suppression des colonnes vides
df = df.drop(columns=empty_cols)

# Suppression des colonnes inutilisées spécifiques
unused_cols = [
    'TimeDimType',
    'ParentLocationCode',
    'TimeDimensionValue',
    'TimeDimensionBegin',
    'TimeDimensionEnd',
    'Date',
    'Dim1Type',
    'Id',
    'IndicatorCode',
    'Low',
    'High',
    'Value'
]
df = df.drop(columns=unused_cols)


# =============================================================
# GÉOLOCALISATION ET MAPPING DES CODES PAYS
# =============================================================
# Extraction des codes uniques SpatialDim pour les pays
"""
spatialdim_unique = df.loc[df['SpatialDimType'] == 'COUNTRY', 'SpatialDim'].unique().tolist()

# Création d'un dictionnaire ISO3 -> ISO2
iso3_to_iso2 = {}
iso2_coords = {}

for code in spatialdim_unique:
    country = pc.countries.get(alpha_3=code)
    if country:
        iso3_to_iso2[code] = country.alpha_2
        iso2_coords[country.alpha_2] = None
    else:
        iso3_to_iso2[code] = None

# Géolocalisation des codes ISO2
for code in iso2_coords.keys():
    location = geolocator.geocode(code, timeout=2)
    if location:
        iso2_coords[code] = (location.latitude, location.longitude)
    else:
        iso2_coords[code] = None  # En cas d'échec

# Remplacement de SpatialDim par ISO2 et ajout des coordonnées
df['SpatialDim'] = df['SpatialDim'].replace(iso3_to_iso2)
df['Coordonnees'] = df['SpatialDim'].map(iso2_coords)

print(iso2_coords)
"""

# =============================================================
# SAUVEGARDE DU FICHIER NETTOYÉ
# =============================================================
df.to_csv('data/cleaned/cleaneddata.csv', index=False)