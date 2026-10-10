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
import re
import shutil
import sqlite3
import sys
import time
import urllib.request
from datetime import date

from core import historial
from core.circuits import DATOS_CIRCUITOS
from core.equipos import COLORES_EQUIPO, SLUG_LOGO, url_logo
from core.flags import CODIGOS_PAIS
from core.i18n import EVENTOS_ES, NACIONALIDADES_ES, PAISES_ES

DATOS = os.path.join("web", "datos")
MAPAS = os.path.join("web", "mapas")
# El deploy arranca sin caché y hace ~50 pedidos seguidos; Jolpica admite 4
# por segundo y contesta 429 al pasarse. Como precache_historial.py.
REINTENTOS = 5
OPENF1 = "https://api.openf1.org/v1"
# Slug de cada equipo en el CDN nuevo de F1 (verificados contra el CDN el
# 2026-10-06). ponytail: tabla fija como las de core/equipos.py; cada año el
# CDN usa la carpeta del año, y si F1 todavía no la publicó (enero) las
# imágenes dan 404 y la web las saca (onerror).
SLUG_CDN = {
    "mercedes": "mercedes", "ferrari": "ferrari", "mclaren": "mclaren",
    "red_bull": "redbullracing", "rb": "racingbulls", "aston_martin": "astonmartin",
    "alpine": "alpine", "williams": "williams", "haas": "haasf1team",
    "audi": "audi", "cadillac": "cadillac",
}
CDN = "https://media.formula1.com/image/upload/c_lfill,w_{ancho}/q_auto/v1740000000/common/f1/{anio}/{ruta}.webp"
# El código de la foto en la URL de OpenF1: .../ANDANT01_Kimi_Antonelli/andant01.png...
CODIGO_FOTO = re.compile(r"/([a-z]{6}\d{2})\.png")


def pedir(ruta, offset=0):
    # historial.pedir_json se busca al llamar (no como valor por defecto):
    # así los tests lo pueden reemplazar.
    return historial.pedir_json(ruta, offset, reintentos=REINTENTOS)


def url_cdn(anio, ruta, ancho):
    return CDN.format(anio=anio, ruta=ruta, ancho=ancho)


def pedir_openf1(ruta):
    pedido = urllib.request.Request(f"{OPENF1}/{ruta}", headers={"User-Agent": historial.USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=30) as respuesta:
        return json.load(respuesta)


def completar_fotos(datos, anio, pedir=pedir_openf1):
    """Foto oficial de los pilotos de la temporada en curso, desde los pilotos
    del último fin de semana de OpenF1 cruzados por sigla (todo el fin de
    semana: en un EL1 con novatos, el titular no está en la sesión). En escritorio la pone
    FastF1, que no corre en el deploy. Si OpenF1 falla, se exporta sin fotos:
    la web cae en Wikipedia o la sigla, como antes."""
    try:
        de_openf1 = {d["name_acronym"]: d.get("headshot_url") for d in pedir("drivers?meeting_key=latest")
                     if d.get("headshot_url")}
    except Exception as error:   # red, JSON roto o una respuesta con otra forma
        print(f"OpenF1 sin fotos: {error!r}")
        return
    for p in datos["pilotos"]:
        url = de_openf1.get(p.get("codigo"))
        if not url:
            continue
        # /1col/ son 93 px; /2col/ son 206, que alcanzan para los avatares.
        p["headshot_url"] = url.replace("/1col/", "/2col/")
        codigo = CODIGO_FOTO.search(url)
        slug = SLUG_CDN.get(p.get("constructor_id"))
        if codigo and slug:
            c = codigo[1]
            p["foto_cuerpo"] = url_cdn(anio, f"{slug}/{c}/{anio}{slug}{c}right", 440)
    por_id = {p["driver_id"]: p for p in datos["pilotos"]}
    for e in datos["equipos"]:
        cara = e.get("cara_a_cara")
        for lado in ("a", "b") if cara else ():
            piloto = por_id.get(cara[lado]["driver_id"])
            if piloto:
                cara[lado]["headshot_url"] = piloto.get("headshot_url")


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
        # Los 11 equipos actuales del CDN nuevo; los viejos, con la ruta de 2025 de core.
        "logos": {**{constructor_id: url_logo(constructor_id) for constructor_id in SLUG_LOGO},
                  **{cid: url_cdn(anio_actual, f"{slug}/{anio_actual}{slug}logowhite", 200)
                     for cid, slug in SLUG_CDN.items()}},
        "autos": {cid: url_cdn(anio_actual, f"{slug}/{anio_actual}{slug}carright", 640)
                  for cid, slug in SLUG_CDN.items()},
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


def ganadores(pedir_pagina=None):
    """Ganadores de cada circuito con ficha. Un circuito que falla queda
    afuera en vez de tirar abajo todo el deploy: la web muestra "sin
    ganadores" para ese."""
    pedir_pagina = pedir_pagina or pedir
    resultado = {}
    for d in DATOS_CIRCUITOS.values():
        time.sleep(historial.PAUSA_S)
        try:
            lista = historial.ganadores_circuito(d["circuit_id"], pedir_pagina)
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


def indice(con, terminadas):
    """Todos los pilotos y equipos con la última temporada terminada que
    corrieron: el buscador de la web (Ctrl+K) lleva a esa ficha. Los que más
    ganaron primero, así "senna" es Ayrton y no Bruno."""
    marcas = ",".join("?" * len(terminadas))

    def ultimos(sql):
        return [{"id": i, "nombre": nombre, "anio": anio}
                for i, nombre, anio in con.execute(sql.format(marcas), terminadas)]
    return {
        "pilotos": ultimos("SELECT p.driver_id, p.nombre || ' ' || p.apellido, MAX(r.temporada) "
                           "FROM pilotos p JOIN resultados r USING (driver_id) WHERE r.temporada IN ({}) "
                           "GROUP BY p.driver_id ORDER BY SUM(r.posicion = 1) DESC, MAX(r.temporada) DESC, p.apellido"),
        "equipos": ultimos("SELECT e.constructor_id, e.nombre, MAX(r.temporada) "
                           "FROM equipos e JOIN resultados r USING (constructor_id) WHERE r.temporada IN ({}) "
                           "GROUP BY e.constructor_id ORDER BY SUM(r.posicion = 1) DESC, MAX(r.temporada) DESC, e.nombre"),
    }


def exportar_historico():
    con = historial.abrir_base()
    terminadas = temporadas_terminadas(con)
    a_medias = [anio for (anio,) in con.execute("SELECT temporada FROM temporadas")
                if anio not in terminadas and anio < date.today().year]
    if a_medias:
        print(f"Sin exportar, guardadas antes de terminar: {a_medias}. Abrilas en la app "
              "(o corré precache_historial.py) para bajarlas completas.", file=sys.stderr)
    for anio in terminadas:
        escribir_json(os.path.join(DATOS, "temporadas", f"{anio}.json"), temporada(con, anio))
    escribir_json(os.path.join(DATOS, "carreras_previas.json"), carreras_previas(con))
    escribir_json(os.path.join(DATOS, "indice.json"), indice(con, terminadas))
    print(f"{len(terminadas)} temporadas, {copiar_mapas()} mapas")


def base_de(anio):
    """Base en memoria con sólo esa temporada (~10 pedidos a Jolpica): el
    deploy no tiene la base completa, y para las fichas del año no hace falta."""
    con = sqlite3.connect(":memory:")
    con.executescript(historial.ESQUEMA)
    historial.descargar_temporada(con, anio, pedir=pedir)
    return con


def sumar_a_previas(previas, carrera):
    """Suma la carrera de una temporada a la acumulada de carreras_previas."""
    if previas is None:
        return carrera
    debuts = [d for d in (previas["debut"], carrera["debut"]) if d is not None]
    return {**{k: (previas[k] or 0) + (carrera[k] or 0) for k in ("titulos", "victorias", "podios", "gps")},
            "debut": min(debuts) if debuts else None}


def exportar_terminada(anio):
    """La temporada que terminó y todavía no pasó por --historico (en enero,
    hasta que se corra en la PC): su JSON y su parte de carreras_previas. Sin
    esto la web la perdía, porque actual.json ya es del año nuevo."""
    con = base_de(anio)
    escribir_json(os.path.join(DATOS, "temporadas", f"{anio}.json"), temporada(con, anio))
    ruta = os.path.join(DATOS, "carreras_previas.json")
    with open(ruta, encoding="utf-8") as archivo:
        previas = json.load(archivo)
    for (driver_id,) in con.execute("SELECT DISTINCT driver_id FROM resultados"):
        previas[driver_id] = sumar_a_previas(previas.get(driver_id), historial.carrera_completa(con, driver_id))
    escribir_json(ruta, previas)
    print(f"{anio}: agregada a temporadas/ y carreras_previas (falta correr --historico)")


def exportar_actual(anio):
    if not os.path.exists(os.path.join(DATOS, "temporadas", f"{anio - 1}.json")):
        exportar_terminada(anio - 1)
    con = base_de(anio)
    datos = temporada(con, anio)
    for p in datos["pilotos"]:
        p["carrera"] = historial.carrera_completa(con, p["driver_id"])
    completar_fotos(datos, anio)
    escribir_json(os.path.join(DATOS, "actual.json"), datos)
    escribir_json(os.path.join(DATOS, "ganadores.json"), ganadores())
    escribir_json(os.path.join(DATOS, "comun.json"), datos_comunes(anio))
    print(f"{anio}: {len(datos['pilotos'])} pilotos, ronda {datos['ronda']}")


if __name__ == "__main__":
    if "--historico" in sys.argv:
        exportar_historico()
    else:
        exportar_actual(date.today().year)
