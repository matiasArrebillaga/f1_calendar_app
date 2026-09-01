import os
import urllib.request

CACHE_DIR = "cache_flags"

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
    "San Marino": "sm", "Luxembourg": "lu",
}


def obtener_ruta_bandera(pais):
    codigo = CODIGOS_PAIS.get(pais)
    if codigo is None:
        return None

    os.makedirs(CACHE_DIR, exist_ok=True)
    ruta_local = os.path.join(CACHE_DIR, f"{codigo}.png")

    if not os.path.exists(ruta_local):
        url = f"https://flagcdn.com/32x24/{codigo}.png"
        try:
            urllib.request.urlretrieve(url, ruta_local)
        except Exception:
            return None

    return ruta_local