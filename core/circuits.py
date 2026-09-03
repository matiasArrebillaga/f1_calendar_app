import os
import urllib.request

CACHE_DIR = "cache_circuitos"

DATOS_CIRCUITOS = {

    "Monza": {
        "nombre_completo": "Autodromo Nazionale Monza",
        "longitud_km": 5.793,
        "vueltas": 53,
        "distancia_km": 306.720,
        "curvas": 11,
        "record_vuelta": "1:21.046 — Rubens Barrichello (2004)",
        "primer_gp": 1950,
        "imagen_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Monza_track_map.svg/960px-Monza_track_map.svg.png",
    },

}

def obtener_datos_circuito(location):
    return DATOS_CIRCUITOS.get(location)


def obtener_ruta_imagen_circuito(location):
    datos = obtener_datos_circuito(location)
    if not datos or not datos.get("imagen_url"):
        return None

    os.makedirs(CACHE_DIR, exist_ok=True)

    url = datos["imagen_url"]
    ruta_sin_query = url.split("?")[0]  # sacamos los parámetros de tracking antes de mirar la extensión
    extension = ruta_sin_query.rsplit(".", 1)[-1]
    nombre_archivo = location.lower().replace(" ", "_") + f".{extension}"
    ruta_local = os.path.join(CACHE_DIR, nombre_archivo)

    if not os.path.exists(ruta_local):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "F1CalendarApp/1.0 (proyecto educativo personal)"}
            )
            with urllib.request.urlopen(request) as respuesta, open(ruta_local, "wb") as archivo:
                archivo.write(respuesta.read())
        except Exception as e:
            print(f"No se pudo descargar la imagen del circuito: {e}")
            return None

    return ruta_local