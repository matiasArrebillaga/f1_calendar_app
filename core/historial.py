"""Historial de resultados de F1 (Ergast vía Jolpica) guardado en SQLite.

Las temporadas terminadas no cambian nunca: precache_historial.py las baja una
vez y viajan en el build. La app sólo pide la temporada en curso o alguna que
falte. Todo lo de acá es Python plano (sin Qt), para poder testearlo sin red.
"""
import json
import os
import shutil
import sqlite3
import time
import urllib.error
import urllib.request

from core.paths import data_path, resource_path

API = "https://api.jolpi.ca/ergast/f1"
CARPETA = "cache_historial"
ARCHIVO = "historial_f1.db"
USER_AGENT = "F1CalendarApp/1.0"
PAUSA_S = 0.3              # entre páginas: Jolpica admite 4 consultas por segundo
ESPERA_429_S = 60
ANIO_CLASIFICACION = 1994  # Ergast no tiene clasificaciones antes de esto

# positionText de Ergast: F = no clasificó, W = se retiró antes de largar.
# Ergast los mete en los resultados, pero no largaron.
LARGO_SQL = "posicion_texto NOT IN ('F', 'W')"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS temporadas (
    temporada INTEGER PRIMARY KEY, actualizada TEXT);
CREATE TABLE IF NOT EXISTS carreras (
    temporada INTEGER, ronda INTEGER, nombre TEXT, pais TEXT, fecha TEXT,
    PRIMARY KEY (temporada, ronda));
CREATE TABLE IF NOT EXISTS pilotos (
    driver_id TEXT PRIMARY KEY, codigo TEXT, numero TEXT, nombre TEXT,
    apellido TEXT, nacionalidad TEXT, nacimiento TEXT, url_wiki TEXT,
    headshot_url TEXT);
CREATE TABLE IF NOT EXISTS equipos (
    constructor_id TEXT PRIMARY KEY, nombre TEXT);
-- Sin clave primaria: en los años 50 un piloto podía correr dos autos en la
-- misma carrera.
CREATE TABLE IF NOT EXISTS resultados (
    temporada INTEGER, ronda INTEGER, driver_id TEXT, constructor_id TEXT,
    numero TEXT, largada INTEGER, posicion INTEGER, posicion_texto TEXT,
    puntos REAL, estado TEXT);
CREATE INDEX IF NOT EXISTS idx_resultados_piloto ON resultados (driver_id, temporada);
CREATE INDEX IF NOT EXISTS idx_resultados_equipo ON resultados (temporada, constructor_id);
CREATE TABLE IF NOT EXISTS clasificacion (
    temporada INTEGER, ronda INTEGER, driver_id TEXT, posicion INTEGER);
CREATE TABLE IF NOT EXISTS campeonato_pilotos (
    temporada INTEGER, driver_id TEXT, constructor_id TEXT, posicion INTEGER,
    puntos REAL, victorias INTEGER);
CREATE TABLE IF NOT EXISTS campeonato_equipos (
    temporada INTEGER, constructor_id TEXT, posicion INTEGER, puntos REAL);
"""
TABLAS_POR_TEMPORADA = ("carreras", "resultados", "clasificacion",
                        "campeonato_pilotos", "campeonato_equipos")


def pedir_json(ruta, offset=0, reintentos=1):
    """Una página de la API (`MRData`). `ruta` es lo que va después de /f1/,
    sin el .json: "2025/results"."""
    url = f"{API}/{ruta}.json?limit=100&offset={offset}"
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for intento in range(reintentos):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as respuesta:
                return json.load(respuesta)["MRData"]
        except urllib.error.HTTPError as error:
            if error.code != 429 or intento == reintentos - 1:
                raise
            time.sleep(ESPERA_429_S)


def _paginar(ruta, pedir):
    """Todas las páginas de un endpoint. Ergast pagina por filas, no por
    carrera: una misma carrera puede venir partida entre dos páginas."""
    offset = 0
    while True:
        pagina = pedir(ruta, offset)
        yield pagina
        offset += int(pagina["limit"])
        if offset >= int(pagina["total"]):
            return
        time.sleep(PAUSA_S)


def _carreras(ruta, pedir):
    return [c for pagina in _paginar(ruta, pedir) for c in pagina["RaceTable"]["Races"]]


def _standings(ruta, clave, pedir):
    return [fila for pagina in _paginar(ruta, pedir)
            for lista in pagina["StandingsTable"]["StandingsLists"]
            for fila in lista[clave]]


def _entero(texto):
    return int(texto) if texto is not None and str(texto).isdigit() else None


def _guardar_piloto(con, d):
    # COALESCE: no todas las respuestas traen sigla o número; si ya estaban,
    # no se pisan con vacío. headshot_url no se toca: la llena otra función.
    con.execute("""
        INSERT INTO pilotos (driver_id, codigo, numero, nombre, apellido,
                             nacionalidad, nacimiento, url_wiki)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (driver_id) DO UPDATE SET
            codigo = COALESCE(excluded.codigo, codigo),
            numero = COALESCE(excluded.numero, numero),
            nombre = excluded.nombre, apellido = excluded.apellido,
            nacionalidad = excluded.nacionalidad,
            nacimiento = excluded.nacimiento, url_wiki = excluded.url_wiki""",
        (d["driverId"], d.get("code"), d.get("permanentNumber"), d.get("givenName"),
         d.get("familyName"), d.get("nationality"), d.get("dateOfBirth"), d.get("url")))


def _guardar_equipo(con, e):
    con.execute("""INSERT INTO equipos VALUES (?, ?)
                   ON CONFLICT (constructor_id) DO UPDATE SET nombre = excluded.nombre""",
                (e["constructorId"], e.get("name")))


def descargar_temporada(con, anio, pedir=pedir_json):
    """Baja la temporada entera y la reemplaza en una sola transacción.

    Primero se pide todo y recién después se escribe: si la red se corta a
    mitad de camino, la base queda exactamente como estaba."""
    carreras = _carreras(f"{anio}/results", pedir)
    clasificacion = (_carreras(f"{anio}/qualifying", pedir)
                     if anio >= ANIO_CLASIFICACION else [])
    camp_pilotos = _standings(f"{anio}/driverStandings", "DriverStandings", pedir)
    camp_equipos = _standings(f"{anio}/constructorStandings", "ConstructorStandings", pedir)

    with con:
        for tabla in TABLAS_POR_TEMPORADA:
            con.execute(f"DELETE FROM {tabla} WHERE temporada = ?", (anio,))

        for carrera in carreras:
            ronda = int(carrera["round"])
            con.execute("INSERT OR REPLACE INTO carreras VALUES (?, ?, ?, ?, ?)",
                        (anio, ronda, carrera["raceName"],
                         carrera["Circuit"]["Location"]["country"], carrera["date"]))
            for r in carrera["Results"]:
                _guardar_piloto(con, r["Driver"])
                _guardar_equipo(con, r["Constructor"])
                texto = r["positionText"]
                con.execute("INSERT INTO resultados VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (anio, ronda, r["Driver"]["driverId"],
                             r["Constructor"]["constructorId"], r.get("number"),
                             _entero(r.get("grid")) or 0, _entero(texto), texto,
                             float(r.get("points") or 0), r.get("status", "")))

        for carrera in clasificacion:
            for q in carrera["QualifyingResults"]:
                con.execute("INSERT INTO clasificacion VALUES (?, ?, ?, ?)",
                            (anio, int(carrera["round"]), q["Driver"]["driverId"],
                             _entero(q.get("position"))))

        for fila in camp_pilotos:
            _guardar_piloto(con, fila["Driver"])
            equipos = fila.get("Constructors") or []
            for equipo in equipos:
                _guardar_equipo(con, equipo)
            con.execute("INSERT INTO campeonato_pilotos VALUES (?, ?, ?, ?, ?, ?)",
                        (anio, fila["Driver"]["driverId"],
                         equipos[-1]["constructorId"] if equipos else None,
                         _entero(fila.get("position")), float(fila.get("points") or 0),
                         int(fila.get("wins") or 0)))

        for fila in camp_equipos:
            _guardar_equipo(con, fila["Constructor"])
            con.execute("INSERT INTO campeonato_equipos VALUES (?, ?, ?, ?)",
                        (anio, fila["Constructor"]["constructorId"],
                         _entero(fila.get("position")), float(fila.get("points") or 0)))

        con.execute("INSERT OR REPLACE INTO temporadas VALUES (?, datetime('now'))", (anio,))


def temporada_guardada(con, anio):
    return con.execute("SELECT 1 FROM temporadas WHERE temporada = ?",
                       (anio,)).fetchone() is not None


def abrir_base():
    """Conexión a la copia escribible. La primera vez la copia desde el build
    (que es de sólo lectura); si no hay ninguna, arranca vacía."""
    carpeta = data_path(CARPETA)
    ruta = os.path.join(carpeta, ARCHIVO)
    if not os.path.exists(ruta):
        os.makedirs(carpeta, exist_ok=True)
        empaquetada = resource_path(os.path.join(CARPETA, ARCHIVO))
        if os.path.exists(empaquetada):
            shutil.copyfile(empaquetada, ruta)
    con = sqlite3.connect(ruta, timeout=10)
    con.executescript(ESQUEMA)
    return con


def _dicts(cursor):
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def pilotos_temporada(con, anio):
    """Pilotos del campeonato en orden; los que no tienen posición, al final.
    `numero` es el del último resultado: antes de 2014 cambiaba por carrera."""
    return _dicts(con.execute("""
        SELECT c.driver_id, p.codigo, p.nombre, p.apellido, p.nacionalidad,
               p.nacimiento, p.url_wiki, p.headshot_url, c.constructor_id,
               e.nombre AS equipo, c.posicion, c.puntos,
               (SELECT r.numero FROM resultados r
                 WHERE r.temporada = c.temporada AND r.driver_id = c.driver_id
                 ORDER BY r.ronda DESC LIMIT 1) AS numero
          FROM campeonato_pilotos c
          JOIN pilotos p ON p.driver_id = c.driver_id
          LEFT JOIN equipos e ON e.constructor_id = c.constructor_id
         WHERE c.temporada = ?
         ORDER BY c.posicion IS NULL, c.posicion, c.puntos DESC""", (anio,)))


def equipos_temporada(con, anio):
    """Campeonato de constructores. No existe antes de 1958: ahí se suman los
    puntos de los resultados y los equipos quedan sin posición."""
    filas = _dicts(con.execute("""
        SELECT c.constructor_id, e.nombre, c.posicion, c.puntos
          FROM campeonato_equipos c
          JOIN equipos e ON e.constructor_id = c.constructor_id
         WHERE c.temporada = ?
         ORDER BY c.posicion IS NULL, c.posicion""", (anio,)))
    if filas:
        return filas
    return _dicts(con.execute("""
        SELECT r.constructor_id, e.nombre, NULL AS posicion, SUM(r.puntos) AS puntos
          FROM resultados r
          JOIN equipos e ON e.constructor_id = r.constructor_id
         WHERE r.temporada = ?
         GROUP BY r.constructor_id, e.nombre
         ORDER BY puntos DESC, e.nombre""", (anio,)))


def stats_temporada(con, anio, driver_id):
    stats = _dicts(con.execute(f"""
        SELECT IFNULL(SUM(posicion = 1), 0) AS victorias,
               IFNULL(SUM(posicion <= 3), 0) AS podios,
               IFNULL(SUM(posicion IS NULL AND {LARGO_SQL}), 0) AS abandonos,
               AVG(posicion) AS prom_llegada,
               AVG(CASE WHEN largada > 0 THEN largada END) AS prom_largada
          FROM resultados
         WHERE temporada = ? AND driver_id = ?""", (anio, driver_id)))[0]

    if anio >= ANIO_CLASIFICACION:
        sql_poles = """SELECT COUNT(*) FROM clasificacion
                        WHERE temporada = ? AND driver_id = ? AND posicion = 1"""
    else:   # sin clasificación en Ergast: el primero de la grilla
        sql_poles = """SELECT COUNT(*) FROM resultados
                        WHERE temporada = ? AND driver_id = ? AND largada = 1"""
    stats["poles"] = con.execute(sql_poles, (anio, driver_id)).fetchone()[0]

    campeonato = con.execute("""SELECT posicion, puntos FROM campeonato_pilotos
                                 WHERE temporada = ? AND driver_id = ?""",
                             (anio, driver_id)).fetchone() or (None, None)
    stats["posicion"], stats["puntos"] = campeonato
    return stats


def tira_resultados(con, anio, driver_id):
    return _dicts(con.execute("""
        SELECT r.ronda, c.nombre AS gp, r.largada, r.posicion, r.posicion_texto
          FROM resultados r
          JOIN carreras c ON c.temporada = r.temporada AND c.ronda = r.ronda
         WHERE r.temporada = ? AND r.driver_id = ?
         ORDER BY r.ronda""", (anio, driver_id)))


def carrera_completa(con, driver_id):
    carrera = _dicts(con.execute(f"""
        SELECT IFNULL(SUM(posicion = 1), 0) AS victorias,
               IFNULL(SUM(posicion <= 3), 0) AS podios,
               COUNT(DISTINCT CASE WHEN {LARGO_SQL} THEN temporada * 100 + ronda END) AS gps,
               MIN(CASE WHEN {LARGO_SQL} THEN temporada END) AS debut
          FROM resultados
         WHERE driver_id = ?""", (driver_id,)))[0]
    carrera["titulos"] = con.execute("""SELECT COUNT(*) FROM campeonato_pilotos
                                         WHERE driver_id = ? AND posicion = 1""",
                                     (driver_id,)).fetchone()[0]
    return carrera
