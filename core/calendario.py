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
