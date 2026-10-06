"""Datos de la versión web (web/datos/), sacados de core/.

`python exportar_web.py` baja la temporada en curso y escribe los JSON que
cambian con cada carrera (actual, ganadores, comun). Lo corre el deploy todos
los lunes, así que esos archivos no se versionan.

`python exportar_web.py --historico` escribe, desde la base local del
historial, las temporadas terminadas y la carrera previa de cada piloto, y
copia los mapas. Se corre en la PC cuando cambia algo del pasado (típicamente
en enero) y lo que genera sí se versiona.
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import date

from core import historial
from core.circuits import DATOS_CIRCUITOS
from core.equipos import COLORES_EQUIPO, SLUG_LOGO, url_logo
from core.flags import CODIGOS_PAIS
from core.i18n import EVENTOS_ES, NACIONALIDADES_ES, PAISES_ES

DATOS = os.path.join("web", "datos")
MAPAS = os.path.join("web", "mapas")


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, separators=(",", ":"))


def datos_comunes(anio_actual):
    """Tablas de core/ que la web necesita: así no hay copias en JS que se
    desactualicen."""
    return {
        "anio_actual": anio_actual,
        "eventos": EVENTOS_ES,
        "paises": PAISES_ES,
        "nacionalidades": NACIONALIDADES_ES,
        "banderas": CODIGOS_PAIS,
        "colores": COLORES_EQUIPO,
        "logos": {constructor_id: url_logo(constructor_id) for constructor_id in SLUG_LOGO},
        "circuitos": {
            d["circuit_id"]: {**d, "mapa": os.path.exists(os.path.join(MAPAS, f"{d['circuit_id']}.png"))}
            for d in DATOS_CIRCUITOS.values()
        },
    }


def temporada(con, anio):
    """Todo lo que muestran la grilla y las fichas de un año."""
    pilotos = historial.pilotos_temporada(con, anio)
    for p in pilotos:
        p["stats"] = historial.stats_temporada(con, anio, p["driver_id"])
        p["tira"] = historial.tira_resultados(con, anio, p["driver_id"])
    equipos = historial.equipos_temporada(con, anio)
    for e in equipos:
        e["stats"] = historial.stats_equipo(con, anio, e["constructor_id"])
        e["cara_a_cara"] = historial.cara_a_cara(con, anio, e["constructor_id"])
    return {"anio": anio, "ronda": historial.ultima_ronda(con, anio),
            "pilotos": pilotos, "equipos": equipos}


def temporadas_terminadas(con):
    return [anio for (anio,) in con.execute("SELECT temporada FROM temporadas ORDER BY temporada")
            if historial.temporada_completa(con, anio)]


def carreras_previas(con):
    """Carrera completa de cada piloto contando sólo temporadas terminadas. La
    web le suma la temporada en curso (actual.json), así no hace falta volver
    a correr esto después de cada carrera."""
    copia = sqlite3.connect(":memory:")
    con.backup(copia)
    terminadas = temporadas_terminadas(copia)
    marcas = ",".join("?" * len(terminadas))
    with copia:
        for tabla in historial.TABLAS_POR_TEMPORADA + ("temporadas",):
            copia.execute(f"DELETE FROM {tabla} WHERE temporada NOT IN ({marcas})", terminadas)
    ids = [driver_id for (driver_id,) in copia.execute("SELECT DISTINCT driver_id FROM resultados")]
    return {driver_id: historial.carrera_completa(copia, driver_id) for driver_id in ids}


def ganadores(pedir=historial.pedir_json):
    """Ganadores de cada circuito con ficha. Un circuito que falla queda
    afuera en vez de tirar abajo todo el deploy: la web muestra "sin
    ganadores" para ese."""
    resultado = {}
    for d in DATOS_CIRCUITOS.values():
        try:
            lista = historial.ganadores_circuito(d["circuit_id"], pedir)
        except Exception as error:
            print(f"ganadores de {d['circuit_id']}: {error}", file=sys.stderr)
            continue
        mas = historial.mas_victorias(lista)
        resultado[d["circuit_id"]] = {"lista": lista, "mas": list(mas) if mas else None}
    return resultado


def copiar_mapas(origen="cache_tracks"):
    """Los PNG de escritorio se llaman como la location ("marina_bay.png");
    en la web van por circuit_id, que es lo que trae Jolpica."""
    os.makedirs(MAPAS, exist_ok=True)
    copiados = 0
    for location, d in DATOS_CIRCUITOS.items():
        ruta = os.path.join(origen, location.lower().replace(" ", "_") + ".png")
        if os.path.exists(ruta):
            shutil.copyfile(ruta, os.path.join(MAPAS, f"{d['circuit_id']}.png"))
            copiados += 1
    return copiados


def exportar_historico():
    con = historial.abrir_base()
    terminadas = temporadas_terminadas(con)
    for anio in terminadas:
        escribir_json(os.path.join(DATOS, "temporadas", f"{anio}.json"), temporada(con, anio))
    escribir_json(os.path.join(DATOS, "carreras_previas.json"), carreras_previas(con))
    print(f"{len(terminadas)} temporadas, {copiar_mapas()} mapas")


def exportar_actual(anio):
    # Base en memoria con sólo la temporada en curso (~10 pedidos a Jolpica):
    # el deploy no tiene la base completa, y para las fichas del año no hace falta.
    con = sqlite3.connect(":memory:")
    con.executescript(historial.ESQUEMA)
    historial.descargar_temporada(con, anio)
    datos = temporada(con, anio)
    for p in datos["pilotos"]:
        p["carrera"] = historial.carrera_completa(con, p["driver_id"])
    escribir_json(os.path.join(DATOS, "actual.json"), datos)
    escribir_json(os.path.join(DATOS, "ganadores.json"), ganadores())
    escribir_json(os.path.join(DATOS, "comun.json"), datos_comunes(anio))
    print(f"{anio}: {len(datos['pilotos'])} pilotos, ronda {datos['ronda']}")


if __name__ == "__main__":
    if "--historico" in sys.argv:
        exportar_historico()
    else:
        exportar_actual(date.today().year)
