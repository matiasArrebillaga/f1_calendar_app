"""Fotos de pilotos: la oficial de F1, si no la de Wikipedia, si no None (la
UI dibuja la sigla sobre el color del equipo). Mismo esquema de caché que las
banderas de core/flags.py: lo empaquetado primero, si no se baja al lado del exe.
"""
import json
import os
import urllib.request

from core.paths import data_path, ruta_cache

CARPETA = "cache_fotos"
USER_AGENT = "F1CalendarApp/1.0"   # Wikimedia rechaza pedidos sin User-Agent

# Pilotos sin foto en ninguna fuente: no se reintenta en esta sesión.
_fallidas = set()


def _bajar(url, destino):
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        datos = respuesta.read()
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
    for extension in ("png", "jpg"):
        ruta, _ = ruta_cache(CARPETA, f"{driver_id}.{extension}")
        if os.path.exists(ruta):
            return ruta
    if driver_id in _fallidas:
        return None

    fuentes = []
    if headshot_url:
        fuentes.append(("png", lambda: headshot_url))
    if url_wiki:
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
    return None
