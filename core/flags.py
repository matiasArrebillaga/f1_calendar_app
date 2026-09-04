import os
import urllib.request
from core.paths import ruta_cache, data_path

CACHE_DIR_NOMBRE = "cache_flags"

CODIGOS_PAIS = {
    "United Kingdom": "gb", "UK": "gb", "Great Britain": "gb",
    "USA": "us", "United States": "us",
    "Monaco": "mc", "Italy": "it", "Belgium": "be", "Netherlands": "nl",
    "Spain": "es", "Austria": "at", "France": "fr", "Germany": "de",
    "Hungary": "hu", "Azerbaijan": "az", "Singapore": "sg", "Japan": "jp",
    "Qatar": "qa", "Mexico": "mx", "Brazil": "br",
    "United Arab Emirates": "ae", "Saudi Arabia": "sa", "Bahrain": "bh",
    "Australia": "au", "China": "cn", "Canada": "ca", "Portugal": "pt",
    "Sweden": "se", "Switzerland": "ch", "South Africa": "za",
    "Argentina": "ar", "Morocco": "ma", "India": "in", "Korea": "kr",
    "Turkey": "tr", "Russia": "ru", "Malaysia": "my",
    "San Marino": "sm", "Luxembourg": "lu","Abu Dhabi":"ae","UAE": "ae"
}


def obtener_ruta_bandera(pais):
    codigo = CODIGOS_PAIS.get(pais)
    if codigo is None:
        return None

    nombre_archivo = f"{codigo}.png"
    ruta, es_escribible = ruta_cache(CACHE_DIR_NOMBRE, nombre_archivo)

    if not es_escribible:
        return ruta  # ya viene empaquetado, ni siquiera hace falta chequear que exista

    if not os.path.exists(ruta):
        os.makedirs(data_path(CACHE_DIR_NOMBRE), exist_ok=True)
        url = f"https://flagcdn.com/32x24/{codigo}.png"
        try:
            urllib.request.urlretrieve(url, ruta)
        except Exception:
            return None

    return ruta