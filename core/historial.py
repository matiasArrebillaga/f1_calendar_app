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
from collections import Counter, defaultdict
from itertools import combinations

from core.paths import data_path, resource_path

API = "https://api.jolpi.ca/ergast/f1"
CARPETA = "cache_historial"
ARCHIVO = "historial_f1.db"
USER_AGENT = "F1CalendarApp/2.0"
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


def _rondas_desde(anio, desde, pedir):
    """Resultados y clasificación de a una ronda, desde `desde` hasta la
    primera que todavía no se corrió."""
    carreras, clasificacion = [], []
    ronda = desde
    while nuevas := _carreras(f"{anio}/{ronda}/results", pedir):
        carreras += nuevas
        if anio >= ANIO_CLASIFICACION:
            clasificacion += _carreras(f"{anio}/{ronda}/qualifying", pedir)
        ronda += 1
    return carreras, clasificacion


def descargar_temporada(con, anio, pedir=pedir_json, desde=None):
    """Baja la temporada y la reemplaza en una sola transacción.

    Con `desde`, sólo las rondas a partir de esa: las anteriores ya están
    guardadas. Los campeonatos se bajan enteros siempre (incluyen los sprints,
    que pueden sumar sin que haya carrera nueva).

    Primero se pide todo y recién después se escribe: si la red se corta a
    mitad de camino, la base queda exactamente como estaba."""
    if desde is None:
        carreras = _carreras(f"{anio}/results", pedir)
        clasificacion = (_carreras(f"{anio}/qualifying", pedir)
                         if anio >= ANIO_CLASIFICACION else [])
    else:
        carreras, clasificacion = _rondas_desde(anio, desde, pedir)
    camp_pilotos = _standings(f"{anio}/driverStandings", "DriverStandings", pedir)
    camp_equipos = _standings(f"{anio}/constructorStandings", "ConstructorStandings", pedir)

    with con:
        for tabla in TABLAS_POR_TEMPORADA:
            if desde is not None and tabla in ("carreras", "resultados", "clasificacion"):
                # Puede haber una clasificación guardada de una ronda que
                # todavía no tenía carrera.
                con.execute(f"DELETE FROM {tabla} WHERE temporada = ? AND ronda >= ?",
                            (anio, desde))
            else:
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


def temporada_completa(con, anio):
    """Guardada después de que terminó el año: ya no le pueden faltar carreras.
    Una guardada a mitad de temporada hay que volver a bajarla aunque ese año
    ya haya pasado."""
    return con.execute("SELECT 1 FROM temporadas WHERE temporada = ? AND actualizada >= ?",
                       (anio, f"{anio + 1}-01-01")).fetchone() is not None


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
    `numero` es el del último resultado: antes de 2014 cambiaba por carrera.
    `equipos`: todos por los que corrió en el año, en orden."""
    pilotos = _dicts(con.execute("""
        SELECT c.driver_id, p.codigo, p.nombre, p.apellido, p.nacionalidad,
               p.nacimiento, p.url_wiki, p.headshot_url, c.constructor_id,
               e.nombre AS equipo, c.posicion, c.puntos, c.victorias,
               (SELECT r.numero FROM resultados r
                 WHERE r.temporada = c.temporada AND r.driver_id = c.driver_id
                 ORDER BY r.ronda DESC LIMIT 1) AS numero
          FROM campeonato_pilotos c
          JOIN pilotos p ON p.driver_id = c.driver_id
          LEFT JOIN equipos e ON e.constructor_id = c.constructor_id
         WHERE c.temporada = ?
         ORDER BY c.posicion IS NULL, c.posicion, c.puntos DESC""", (anio,)))

    equipos = defaultdict(list)
    for driver_id, nombre in con.execute("""
            SELECT r.driver_id, e.nombre FROM resultados r
              JOIN equipos e ON e.constructor_id = r.constructor_id
             WHERE r.temporada = ?
             GROUP BY r.driver_id, r.constructor_id
             ORDER BY MIN(r.ronda)""", (anio,)):
        equipos[driver_id].append(nombre)
    for p in pilotos:
        p["equipos"] = equipos.get(p["driver_id"]) or ([p["equipo"]] if p["equipo"] else [])
    return pilotos


def equipos_temporada(con, anio):
    """Campeonato de constructores. No existe antes de 1958: ahí se suman los
    puntos de los resultados y los equipos quedan sin posición."""
    filas = _dicts(con.execute("""
        SELECT c.constructor_id, e.nombre, c.posicion, c.puntos,
               (SELECT COUNT(*) FROM resultados r
                 WHERE r.temporada = c.temporada AND r.constructor_id = c.constructor_id
                   AND r.posicion = 1) AS victorias
          FROM campeonato_equipos c
          JOIN equipos e ON e.constructor_id = c.constructor_id
         WHERE c.temporada = ?
         ORDER BY c.posicion IS NULL, c.posicion""", (anio,)))
    if filas:
        return filas
    return _dicts(con.execute("""
        SELECT r.constructor_id, e.nombre, NULL AS posicion, SUM(r.puntos) AS puntos,
               IFNULL(SUM(r.posicion = 1), 0) AS victorias
          FROM resultados r
          JOIN equipos e ON e.constructor_id = r.constructor_id
         WHERE r.temporada = ?
         GROUP BY r.constructor_id, e.nombre
         ORDER BY puntos DESC, e.nombre""", (anio,)))


def ultima_ronda(con, anio):
    """Última carrera con resultados; None si todavía no se corrió ninguna."""
    return con.execute("SELECT MAX(ronda) FROM resultados WHERE temporada = ?",
                       (anio,)).fetchone()[0]


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
        SELECT r.ronda, c.nombre AS gp, c.pais, r.largada, r.posicion, r.posicion_texto
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
    # Sólo temporadas terminadas (mismo criterio que temporada_completa): el
    # que va primero a mitad de año todavía no es campeón.
    carrera["titulos"] = con.execute("""SELECT COUNT(*) FROM campeonato_pilotos c
                                          JOIN temporadas t ON t.temporada = c.temporada
                                         WHERE c.driver_id = ? AND c.posicion = 1
                                           AND t.actualizada >= (c.temporada + 1) || '-01-01'""",
                                     (driver_id,)).fetchone()[0]
    return carrera


def stats_equipo(con, anio, constructor_id):
    victorias = con.execute("""SELECT COUNT(*) FROM resultados
                                WHERE temporada = ? AND constructor_id = ? AND posicion = 1""",
                            (anio, constructor_id)).fetchone()[0]
    dobletes = con.execute("""SELECT COUNT(*) FROM (
                                SELECT ronda FROM resultados
                                 WHERE temporada = ? AND constructor_id = ? AND posicion IN (1, 2)
                                 GROUP BY ronda HAVING COUNT(*) = 2)""",
                           (anio, constructor_id)).fetchone()[0]
    return {"victorias": victorias, "dobletes": dobletes}


def cara_a_cara(con, anio, constructor_id):
    """Duelo entre los dos pilotos del equipo que más carreras largaron juntos.
    None si el equipo nunca tuvo dos pilotos en una misma carrera."""
    filas = _dicts(con.execute(f"""
        SELECT ronda, driver_id, largada, posicion, posicion_texto FROM resultados
         WHERE temporada = ? AND constructor_id = ? AND {LARGO_SQL}""",
        (anio, constructor_id)))
    por_ronda = defaultdict(dict)
    for fila in filas:
        # Dos autos el mismo día (años 50): vale el primero.
        por_ronda[fila["ronda"]].setdefault(fila["driver_id"], fila)

    juntos = Counter(par for pilotos in por_ronda.values()
                     for par in combinations(sorted(pilotos), 2))
    if not juntos:
        return None
    a, b = juntos.most_common(1)[0][0]

    campeonato = dict(con.execute("""SELECT driver_id, puntos FROM campeonato_pilotos
                                      WHERE temporada = ? AND driver_id IN (?, ?)""",
                                  (anio, a, b)).fetchall())

    def puntos_en_el_equipo(piloto):
        # El total del campeonato incluye los sprints, que `resultados` no
        # tiene; pero si corrió para otro equipo, también lo que sumó ahí.
        cambio = con.execute("""SELECT 1 FROM resultados WHERE temporada = ?
                                 AND driver_id = ? AND constructor_id != ?""",
                             (anio, piloto, constructor_id)).fetchone()
        if cambio is None:
            return campeonato.get(piloto, 0)
        return con.execute("""SELECT IFNULL(SUM(puntos), 0) FROM resultados
                               WHERE temporada = ? AND driver_id = ? AND constructor_id = ?""",
                           (anio, piloto, constructor_id)).fetchone()[0]

    puntos = {piloto: puntos_en_el_equipo(piloto) for piloto in (a, b)}
    if puntos[b] > puntos[a]:
        a, b = b, a

    rondas = sorted(r for r, pilotos in por_ronda.items() if a in pilotos and b in pilotos)
    if anio >= ANIO_CLASIFICACION:
        grilla = defaultdict(dict)
        for ronda, piloto, posicion in con.execute(
                """SELECT ronda, driver_id, posicion FROM clasificacion
                    WHERE temporada = ? AND driver_id IN (?, ?)""", (anio, a, b)):
            grilla[ronda][piloto] = posicion
    else:   # sin clasificación en Ergast: la grilla de largada (0 = boxes, no cuenta)
        grilla = {r: {p: f["largada"] or None for p, f in pilotos.items()}
                  for r, pilotos in por_ronda.items()}

    carreras = {ronda: (nombre, pais) for ronda, nombre, pais in con.execute(
        "SELECT ronda, nombre, pais FROM carreras WHERE temporada = ?", (anio,))}
    clasificacion, carrera, por_carrera = [0, 0], [0, 0], []
    for ronda in rondas:
        qa, qb = grilla.get(ronda, {}).get(a), grilla.get(ronda, {}).get(b)
        if qa and qb:
            clasificacion[0 if qa < qb else 1] += 1
        fila_a, fila_b = por_ronda[ronda][a], por_ronda[ronda][b]
        pa, pb = fila_a["posicion"], fila_b["posicion"]
        if pa is None and pb is None:
            adelante = None   # abandonaron los dos: la carrera no cuenta
        else:
            adelante = 0 if pb is None or (pa is not None and pa < pb) else 1
            carrera[adelante] += 1
        gp, pais = carreras.get(ronda, ("", ""))
        por_carrera.append({"ronda": ronda, "gp": gp, "pais": pais,
                            "a": fila_a, "b": fila_b, "adelante": adelante})

    def poles(piloto):
        return sum(1 for ronda, pilotos in por_ronda.items()
                   if piloto in pilotos and grilla.get(ronda, {}).get(piloto) == 1)

    def contar(piloto, maximo):
        return sum(1 for f in filas
                   if f["driver_id"] == piloto and f["posicion"] is not None
                   and f["posicion"] <= maximo)

    pilotos = {p["driver_id"]: p for p in _dicts(con.execute(
        """SELECT driver_id, codigo, nombre, apellido, headshot_url, url_wiki
             FROM pilotos WHERE driver_id IN (?, ?)""", (a, b)))}
    return {
        "a": pilotos[a], "b": pilotos[b],
        "clasificacion": tuple(clasificacion),
        "carrera": tuple(carrera),
        "puntos": (puntos[a], puntos[b]),
        "victorias": (contar(a, 1), contar(b, 1)),
        "podios": (contar(a, 3), contar(b, 3)),
        "poles": (poles(a), poles(b)),
        "por_carrera": por_carrera,
    }


def completar_headshots(con, anio):
    """Foto oficial de F1 de los pilotos del año, sacada de la última carrera.
    FastF1 la trae vacía en temporadas viejas (en 2018 ya no viene)."""
    import fastf1   # pesado: sólo se importa cuando hace falta

    ultima = ultima_ronda(con, anio)
    if ultima is None:
        return
    sesion = fastf1.get_session(anio, ultima, "R")
    sesion.load(laps=False, telemetry=False, weather=False, messages=False)
    with con:
        for _, fila in sesion.results.iterrows():
            url = fila.get("HeadshotUrl")
            if isinstance(url, str) and url:
                # /1col/ son 93 px; /2col/ son 206, que alcanzan para la ficha.
                con.execute("UPDATE pilotos SET headshot_url = ? WHERE driver_id = ?",
                            (url.replace("/1col/", "/2col/"), fila["DriverId"]))


CARPETA_GANADORES = "cache_ganadores"
VIGENCIA_GANADORES_S = 7 * 24 * 3600   # a lo sumo una carrera nueva por circuito por año


def ganadores_circuito(circuit_id, pedir=pedir_json):
    """Ganadores de cada GP corrido en el circuito, del más nuevo al más viejo:
    [{"anio", "gp", "piloto", "equipo"}]. Va por circuito y no por nombre del
    GP: el GP de España, por ejemplo, se corrió en cuatro circuitos.

    Se guarda en un JSON por circuito y se vuelve a pedir pasada una semana;
    si la red falla, sirve el guardado aunque esté vencido."""
    ruta = os.path.join(data_path(CARPETA_GANADORES), f"{circuit_id}.json")
    if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < VIGENCIA_GANADORES_S:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    try:
        carreras = _carreras(f"circuits/{circuit_id}/results/1", pedir)
    except Exception:
        if not os.path.exists(ruta):
            raise
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)

    # En los años 50 una victoria podía ser compartida: vienen los dos.
    ganadores = [
        {"anio": int(c["season"]), "ronda": int(c["round"]), "gp": c["raceName"],
         "piloto": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
         "equipo": r["Constructor"]["name"]}
        for c in carreras for r in c["Results"]
    ]
    ganadores.sort(key=lambda g: (g["anio"], g["ronda"]), reverse=True)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(ganadores, archivo, ensure_ascii=False)
    return ganadores


def mas_victorias(ganadores):
    """("Lewis Hamilton", 5) del que más ganó; en un empate, los nombres juntos."""
    conteo = Counter(g["piloto"] for g in ganadores).most_common()
    if not conteo:
        return None
    tope = conteo[0][1]
    return ", ".join(p for p, n in conteo if n == tope), tope
