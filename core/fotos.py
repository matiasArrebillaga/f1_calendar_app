"""Fotos de pilotos: la oficial de F1, si no la de Wikipedia, si no None (la
UI dibuja la sigla sobre el color del equipo). Mismo esquema de caché que las
banderas de core/flags.py: lo empaquetado primero, si no se baja al lado del exe.
"""
import json
import os
import urllib.request

from core.equipos import url_logo
from core.paths import data_path, ruta_cache

CARPETA = "cache_fotos"
CARPETA_LOGOS = "cache_logos"
USER_AGENT = "F1CalendarApp/2.0"   # Wikimedia rechaza pedidos sin User-Agent

# Pilotos sin foto en ninguna fuente: no se reintenta en esta sesión.
_fallidas = set()


def _bajar(url, destino):
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        datos = respuesta.read()
    # Si F1 no tiene la foto devuelve una silueta gris de ~1,4 KB: no sirve.
    if len(datos) < 2048:
        raise ValueError(f"imagen demasiado chica: {url}")
    # Se escribe recién con todo bajado: un corte de red no deja un archivo a medias.
    with open(destino, "wb") as archivo:
        archivo.write(datos)


def _url_wikipedia(url_wiki):
    titulo = url_wiki.rstrip("/").rsplit("/wiki/", 1)[-1]
    pedido = urllib.request.Request(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{titulo}",
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        return (json.load(respuesta).get("thumbnail") or {}).get("source")


def obtener_ruta_foto(driver_id, headshot_url=None, url_wiki=None):
    png, _ = ruta_cache(CARPETA, f"{driver_id}.png")
    if os.path.exists(png):
        return png
    # Un JPG de Wikipedia guardado antes de tener la oficial no la tapa: se
    # intenta la oficial y, si falla, se sigue usando el JPG.
    jpg, _ = ruta_cache(CARPETA, f"{driver_id}.jpg")
    respaldo = jpg if os.path.exists(jpg) else None
    if driver_id in _fallidas or (respaldo and not headshot_url):
        return respaldo

    fuentes = []
    if headshot_url:
        fuentes.append(("png", lambda: headshot_url))
    if url_wiki and not respaldo:
        fuentes.append(("jpg", lambda: _url_wikipedia(url_wiki)))

    os.makedirs(data_path(CARPETA), exist_ok=True)
    for extension, buscar_url in fuentes:
        try:
            origen = buscar_url()
            if not origen:
                continue
            destino = os.path.join(data_path(CARPETA), f"{driver_id}.{extension}")
            _bajar(origen, destino)
            return destino
        except Exception:
            continue
    _fallidas.add(driver_id)
    return respaldo


def obtener_ruta_logo(constructor_id):
    """Logo oficial del equipo, o None (la UI muestra las iniciales)."""
    url = url_logo(constructor_id)
    if url is None:
        return None
    ruta, _ = ruta_cache(CARPETA_LOGOS, f"{constructor_id}.png")
    if os.path.exists(ruta):
        return ruta
    if ("logo", constructor_id) in _fallidas:
        return None
    os.makedirs(data_path(CARPETA_LOGOS), exist_ok=True)
    destino = os.path.join(data_path(CARPETA_LOGOS), f"{constructor_id}.png")
    try:
        _bajar(url, destino)
        return destino
    except Exception:
        _fallidas.add(("logo", constructor_id))
        return None
