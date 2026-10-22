"""Calendario de una temporada, sin los tests de pretemporada.

El caché HTTP de FastF1 vence a las 12 h, así que cada día volvía a pedir los
calendarios de todos los años que se miraban. Los de años terminados ya no
cambian: se guardan acá (y precache.py los mete en el build) y no se piden más.
"""
import os
from datetime import date

import pandas as pd

from core.paths import data_path, ruta_cache

CARPETA = "cache_calendarios"


def anio_actual():
    return date.today().year


def obtener_calendario(year):
    archivo = f"{year}.pkl"
    ruta, _ = ruta_cache(CARPETA, archivo)
    if os.path.exists(ruta):
        return pd.read_pickle(ruta)

    import fastf1   # pesado: sólo si hay que pedirlo
    # Sin include_testing=False el calendario trae los tests de pretemporada
    # con RoundNumber 0, y get_session(year, 0, ...) tira "Cannot get testing
    # event by round number!".
    calendario = fastf1.get_event_schedule(year, include_testing=False)
    if year < anio_actual():
        os.makedirs(data_path(CARPETA), exist_ok=True)
        calendario.to_pickle(os.path.join(data_path(CARPETA), archivo))
    return calendario


# Lo máximo que se lleva un piloto (1º) o un equipo (1º y 2º) en cada carrera.
PUNTOS_CARRERA = {"pilotos": 25, "equipos": 25 + 18}
PUNTOS_SPRINT = {"pilotos": 8, "equipos": 8 + 7}


def rondas_y_sprints(calendario):
    """[(ronda, con_sprint)] de un calendario de FastF1. EventFormat es
    'sprint', 'sprint_shootout' o 'sprint_qualifying' según el año; los fines
    de semana normales, 'conventional'."""
    return [(int(ronda), "sprint" in str(formato))
            for ronda, formato in zip(calendario["RoundNumber"], calendario["EventFormat"])]


def en_juego(ronda, rondas, solapa):
    """"Puntos en juego" tras `ronda`: {"valor": int | None, "detalle": str}.
    `rondas`: [(ronda, con_sprint)] del calendario; `solapa`: "pilotos" o
    "equipos". La web hace la misma cuenta (formato.enJuego): los casos de
    web/test/casos_en_juego.json fijan las dos."""
    if ronda is None or not rondas:
        return {"valor": None, "detalle": "sin datos del calendario"}
    faltan = [con_sprint for r, con_sprint in rondas if r > ronda]
    if not faltan:
        return {"valor": None, "detalle": "Temporada terminada"}
    restantes, sprints = len(faltan), sum(faltan)
    texto = f"{restantes} {'carrera' if restantes == 1 else 'carreras'}"
    if sprints:
        texto += f" y {sprints} {'sprint' if sprints == 1 else 'sprints'}"
    plural = restantes > 1 or sprints > 0
    return {"valor": restantes * PUNTOS_CARRERA[solapa] + sprints * PUNTOS_SPRINT[solapa],
            "detalle": f"{texto} {'restantes' if plural else 'restante'}"}
