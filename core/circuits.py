import os
import urllib.request

from core.paths import ruta_cache, data_path

CACHE_DIR_NOMBRE = "cache_circuitos"

DATOS_CIRCUITOS = {
    "Monza": {
        "nombre_completo": "Autodromo Nazionale Monza",
        "longitud_km": 5.793,
        "vueltas": 53,
        "distancia_km": 306.720,
        "curvas": 11,
        "record_vuelta": "1:21.046 — Rubens Barrichello (2004)",
        "primer_gp": 1950,
    },
    "Bahrain": {
        "nombre_completo": "Bahrain International Circuit",
        "longitud_km": 5.412,
        "vueltas": 57,
        "distancia_km": 308.238,
        "curvas": 15,
        "record_vuelta": "1:31.447 — Pedro de la Rosa (2005)",
        "primer_gp": 2004,
    },
    "Jeddah": {
        "nombre_completo": "Jeddah Corniche Circuit",
        "longitud_km": 6.174,
        "vueltas": 50,
        "distancia_km": 308.450,
        "curvas": 27,
        "record_vuelta": "1:30.734 — Lewis Hamilton (2021)",
        "primer_gp": 2021,
    },
    "Melbourne": {
        "nombre_completo": "Albert Park Circuit",
        "longitud_km": 5.278,
        "vueltas": 58,
        "distancia_km": 306.124,
        "curvas": 14,
        "record_vuelta": "1:19.813 — Charles Leclerc (2024)",
        "primer_gp": 1996,
    },
    "Imola": {
        "nombre_completo": "Autodromo Enzo e Dino Ferrari",
        "longitud_km": 4.909,
        "vueltas": 63,
        "distancia_km": 309.049,
        "curvas": 19,
        "record_vuelta": "1:15.484 — Lewis Hamilton (2020)",
        "primer_gp": 1980,
    },
    "Miami": {
        "nombre_completo": "Miami International Autodrome",
        "longitud_km": 5.412,
        "vueltas": 57,
        "distancia_km": 308.326,
        "curvas": 19,
        "record_vuelta": "1:29.708 — Max Verstappen (2023)",
        "primer_gp": 2022,
    },
    "Catalunya": {
        "nombre_completo": "Circuit de Barcelona-Catalunya",
        "longitud_km": 4.657,
        "vueltas": 66,
        "distancia_km": 307.236,
        "curvas": 14,
        "record_vuelta": "1:16.330 — Max Verstappen (2023)",
        "primer_gp": 1991,
    },
    "Monaco": {
        "nombre_completo": "Circuit de Monaco",
        "longitud_km": 3.337,
        "vueltas": 78,
        "distancia_km": 260.286,
        "curvas": 19,
        "record_vuelta": "1:12.909 — Lewis Hamilton (2021)",
        "primer_gp": 1950,
    },
    "Montreal": {
        "nombre_completo": "Circuit Gilles-Villeneuve",
        "longitud_km": 4.361,
        "vueltas": 70,
        "distancia_km": 305.270,
        "curvas": 14,
        "record_vuelta": "1:13.078 — Valtteri Bottas (2019)",
        "primer_gp": 1978,
    },
    "Red Bull Ring": {
        "nombre_completo": "Red Bull Ring",
        "longitud_km": 4.318,
        "vueltas": 71,
        "distancia_km": 306.452,
        "curvas": 10,
        "record_vuelta": "1:05.619 — Carlos Sainz (2020)",
        "primer_gp": 1970,
    },
    "Silverstone": {
        "nombre_completo": "Silverstone Circuit",
        "longitud_km": 5.891,
        "vueltas": 52,
        "distancia_km": 306.198,
        "curvas": 18,
        "record_vuelta": "1:27.097 — Max Verstappen (2020)",
        "primer_gp": 1950,
    },
    "Hungaroring": {
        "nombre_completo": "Hungaroring",
        "longitud_km": 4.381,
        "vueltas": 70,
        "distancia_km": 306.630,
        "curvas": 14,
        "record_vuelta": "1:16.627 — Lewis Hamilton (2020)",
        "primer_gp": 1986,
    },
    "Spa-Francorchamps": {
        "nombre_completo": "Circuit de Spa-Francorchamps",
        "longitud_km": 7.004,
        "vueltas": 44,
        "distancia_km": 308.052,
        "curvas": 19,
        "record_vuelta": "1:46.286 — Valtteri Bottas (2018)",
        "primer_gp": 1950,
    },
    "Zandvoort": {
        "nombre_completo": "Circuit Zandvoort",
        "longitud_km": 4.259,
        "vueltas": 72,
        "distancia_km": 306.587,
        "curvas": 14,
        "record_vuelta": "1:11.097 — Lewis Hamilton (2021)",
        "primer_gp": 1952,
    },
    "Baku": {
        "nombre_completo": "Baku City Circuit",
        "longitud_km": 6.003,
        "vueltas": 51,
        "distancia_km": 306.049,
        "curvas": 20,
        "record_vuelta": "1:43.009 — Charles Leclerc (2019)",
        "primer_gp": 2016,
    },
    "Marina Bay": {
        "nombre_completo": "Marina Bay Street Circuit",
        "longitud_km": 4.940,
        "vueltas": 62,
        "distancia_km": 306.143,
        "curvas": 19,
        "record_vuelta": "1:35.867 — Lewis Hamilton (2023)",
        "primer_gp": 2008,
    },
    "Suzuka": {
        "nombre_completo": "Suzuka International Racing Course",
        "longitud_km": 5.807,
        "vueltas": 53,
        "distancia_km": 307.471,
        "curvas": 18,
        "record_vuelta": "1:30.983 — Lewis Hamilton (2019)",
        "primer_gp": 1987,
    },
    "COTA": {
        "nombre_completo": "Circuit of The Americas",
        "longitud_km": 5.513,
        "vueltas": 56,
        "distancia_km": 308.405,
        "curvas": 20,
        "record_vuelta": "1:36.169 — Charles Leclerc (2019)",
        "primer_gp": 2012,
    },
    "Hermanos Rodriguez": {
        "nombre_completo": "Autódromo Hermanos Rodríguez",
        "longitud_km": 4.304,
        "vueltas": 71,
        "distancia_km": 305.354,
        "curvas": 17,
        "record_vuelta": "1:17.774 — Valtteri Bottas (2021)",
        "primer_gp": 1963,
    },
    "Interlagos": {
        "nombre_completo": "Autódromo José Carlos Pace",
        "longitud_km": 4.309,
        "vueltas": 71,
        "distancia_km": 305.879,
        "curvas": 15,
        "record_vuelta": "1:10.540 — Valtteri Bottas (2018)",
        "primer_gp": 1973,
    },
    "Las Vegas": {
        "nombre_completo": "Las Vegas Strip Circuit",
        "longitud_km": 6.201,
        "vueltas": 50,
        "distancia_km": 310.050,
        "curvas": 17,
        "record_vuelta": "1:35.490 — Oscar Piastri (2023)",
        "primer_gp": 2023,
    },
    "Losail": {
        "nombre_completo": "Lusail International Circuit",
        "longitud_km": 5.419,
        "vueltas": 57,
        "distancia_km": 308.611,
        "curvas": 16,
        "record_vuelta": "1:24.319 — Max Verstappen (2023)",
        "primer_gp": 2021,
    },
    "Yas Marina": {
        "nombre_completo": "Yas Marina Circuit",
        "longitud_km": 5.281,
        "vueltas": 58,
        "distancia_km": 306.183,
        "curvas": 16,
        "record_vuelta": "1:26.103 — Max Verstappen (2021)",
        "primer_gp": 2009,
    },
    "Paul Ricard": {
        "nombre_completo": "Circuit Paul Ricard",
        "longitud_km": 5.842,
        "vueltas": 53,
        "distancia_km": 309.690,
        "curvas": 15,
        "record_vuelta": "1:32.740 — Sebastian Vettel (2019)",
        "primer_gp": 1971,
    },
    "Portimao": {
        "nombre_completo": "Algarve International Circuit",
        "longitud_km": 4.653,
        "vueltas": 66,
        "distancia_km": 306.828,
        "curvas": 15,
        "record_vuelta": "1:18.750 — Lewis Hamilton (2020)",
        "primer_gp": 2020,
    }
}
def obtener_datos_circuito(location):
    return DATOS_CIRCUITOS.get(location)


def obtener_ruta_imagen_circuito(location):
    datos = obtener_datos_circuito(location)
    if not datos or not datos.get("imagen_url"):
        return None

    url = datos["imagen_url"]
    ruta_sin_query = url.split("?")[0]  # sacamos los parámetros de tracking antes de mirar la extensión
    extension = ruta_sin_query.rsplit(".", 1)[-1]
    nombre_archivo = location.lower().replace(" ", "_") + f".{extension}"

    ruta, es_escribible = ruta_cache(CACHE_DIR_NOMBRE, nombre_archivo)

    if not es_escribible:
        return ruta

    if not os.path.exists(ruta):
        os.makedirs(data_path(CACHE_DIR_NOMBRE), exist_ok=True)
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "F1CalendarApp/1.0 (proyecto educativo personal)"}
            )
            with urllib.request.urlopen(request) as respuesta, open(ruta, "wb") as archivo:
                archivo.write(respuesta.read())
        except Exception as e:
            print(f"No se pudo descargar la imagen del circuito: {e}")
            return None

    return ruta