"""Fechas del calendario en el formato que muestra la app (GMT-3, español).

Los nombres van en tuplas y no con QLocale: las abreviaturas de CLDR para
español cambian entre versiones de Qt ("sept", "sept.", "sep") y acá tienen que
ser siempre las mismas tres letras.
"""
import pandas as pd

MESES = ("ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE")
MESES_CORTOS = tuple(mes[:3] for mes in MESES)
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


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
