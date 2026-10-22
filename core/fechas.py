"""Fechas del calendario en el formato que muestra la app (GMT-3, español).

Los nombres van en tuplas y no con QLocale: las abreviaturas de CLDR para
español cambian entre versiones de Qt ("sept", "sept.", "sep") y acá tienen que
ser siempre las mismas tres letras.
"""
from datetime import timedelta

import pandas as pd

MESES = ("ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE")
MESES_CORTOS = tuple(mes[:3] for mes in MESES)
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


# Duración típica de cada sesión, por el nombre de FastF1: no hay datos en
# vivo, así que con el horario se sabe si se está corriendo. La web usa la
# misma tabla por la clave de Jolpica (formato.DURACION_MIN), y
# web/test/casos_sesiones.json fija las dos.
DURACION_MIN = {"Practice 1": 60, "Practice 2": 60, "Practice 3": 60,
                "Sprint Shootout": 45, "Sprint Qualifying": 45, "Sprint": 45,
                "Qualifying": 60, "Race": 120}


def estado_sesion(nombre, inicio, ahora, sin_hora=False):
    """'hecha', 'vivo' o 'proxima'. `inicio` y `ahora` en GMT-3 sin zona. Sin
    hora publicada (`inicio` es el día a las 00:00) no se sabe cuándo está en
    vivo: se da por hecha al terminar el día."""
    duracion = timedelta(days=1) if sin_hora else timedelta(minutes=DURACION_MIN.get(nombre, 60))
    if ahora >= inicio + duracion:
        return "hecha"
    return "vivo" if ahora >= inicio and not sin_hora else "proxima"


def a_gmt_menos_3(timestamp):
    """Timestamp con zona → hora de Argentina, sin zona (para comparar contra
    pd.Timestamp.now()). Sin zona o NaT vuelve tal cual."""
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        return timestamp
    return timestamp.tz_convert('Etc/GMT+3').tz_localize(None)


def dia_hora(timestamp):
    """'vie 06:30'."""
    return f"{DIAS[timestamp.weekday()]} {timestamp:%H:%M}"


def rango_fechas(evento):
    """'9 – 11 OCT', o '30 OCT – 1 NOV' si el fin de semana cruza de mes.
    Las dos puntas en GMT-3, como la web: Las Vegas larga el sábado allá y el
    domingo acá."""
    fin = largada(evento)
    inicio = a_gmt_menos_3(evento.get('Session1Date'))
    if pd.isna(inicio) or inicio.date() >= fin.date():
        return f"{fin.day} {MESES_CORTOS[fin.month - 1]}"
    if inicio.month == fin.month:
        return f"{inicio.day} – {fin.day} {MESES_CORTOS[fin.month - 1]}"
    return (f"{inicio.day} {MESES_CORTOS[inicio.month - 1]} – "
            f"{fin.day} {MESES_CORTOS[fin.month - 1]}")


def largada(evento):
    """Hora de largada de la carrera (la última sesión del fin de semana), en
    GMT-3 sin zona. Sin horarios publicados: el día de la carrera a las 00:00."""
    for i in range(5, 0, -1):
        fecha = a_gmt_menos_3(evento.get(f'Session{i}Date'))
        if pd.notna(fecha):
            return fecha
    return evento['EventDate']
