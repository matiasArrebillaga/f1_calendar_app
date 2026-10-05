# Pestaña "Pilotos" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sumar a la sidebar una pestaña "Pilotos" con tarjetas de pilotos y equipos (con foto), ficha de piloto (temporada, tira de resultados, carrera completa) y ficha de equipo con cara a cara, alimentada por una base SQLite con todo el historial de Ergast.

**Architecture:** `core/historial.py` baja temporadas de Jolpica (Ergast) con `urllib` y las guarda en SQLite; las consultas devuelven dicts planos sin Qt. `core/fotos.py` resuelve la foto (oficial F1 → Wikipedia → None). `workers/pilotos_worker.py` hace la red en QThreads; `ui/pilotos_view.py` + `ui/fichas_pilotos.py` copian los patrones de `ui/standings_view.py`. Un script local (`precache_historial.py`) llena la base que viaja en el build.

**Tech Stack:** Python 3.14, PySide6, sqlite3 / urllib / json (stdlib), FastF1 (sólo para la URL de la foto oficial), PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-05-pestana-pilotos-design.md`

## Global Constraints

- Sin dependencias nuevas: SQLite, HTTP y JSON con la stdlib.
- API: `https://api.jolpi.ca/ergast/f1/<ruta>.json?limit=100&offset=N`; límites 4 req/s y 500 req/h sin autenticación.
- Ergast no tiene clasificación antes de **1994** (`ANIO_CLASIFICACION = 1994`).
- "Largó" = `posicion_texto` no es `F` ni `W`. "Abandono" = largó y `posicion_texto` no es número.
- Foto oficial: `session.results["HeadshotUrl"]` de FastF1 con `/1col/` reemplazado por `/2col/` (206 px).
- Wikipedia: `https://en.wikipedia.org/api/rest_v1/page/summary/<título>` con User-Agent propio.
- Paleta de `style.qss`: app `#090A0D`, panel `#12161C`, surface `#1B2029`, hover `#262D38`, border `#2D3541`, text `#F3F6F9`, text2 `#CAD2DC`, muted `#A4AEBC`, dato `#52DEEC`, rojo `#E10600` sólo para foco/estado.
- Titillium Web sólo en textos de 17 px o más.
- Todo selector `Tipo#nombre` nuevo de `style.qss` tiene que aparecer como literal en `ui/*.py` (lo exige `test_qss_no_tiene_reglas_muertas`).
- Tests sin frameworks: asserts planos; cada archivo corre con `python -m pytest <archivo>` y con `python <archivo>`.
- Idioma de la UI y de los nombres: español rioplatense, como el resto del código.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Sin internet**: temporada guardada → se muestra igual (también la en curso); temporada que falta → error, y al volver a abrir la pestaña se reintenta. (Task 5 y Task 7)
2. **Cambiar de año rápido**: un resultado que llega tarde de otro año no pisa la grilla. (Task 7)
3. **Temporadas viejas**: pilotos sin sigla ni número, equipos sin color, sin campeonato de constructores (antes de 1958), no clasificados metidos en los resultados → nada crashea y los números no se inflan. (Task 2, Task 6)
4. **Temporada sin carreras todavía** (la en curso antes de la ronda 1) → estado vacío, no error. (Task 7)
5. **Equipos con más de dos pilotos** (reemplazos a mitad de año) → el cara a cara toma el par con más carreras juntos. (Task 3)

## Antes de empezar

El repo quedó con un rebase de `master` a medio terminar (`git status` lo muestra). Con eso no se puede cambiar de rama. **Le toca al usuario resolverlo** (`git rebase --quit` lo cierra sin tocar las ramas). Después:

```bash
git switch -c feat/pestana-pilotos
git add docs/superpowers/specs/2026-10-05-pestana-pilotos-design.md docs/superpowers/plans/2026-10-05-pestana-pilotos.md
git commit -m "Spec y plan: pestaña Pilotos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## File Structure

| Archivo | Qué hace |
|---|---|
| `core/historial.py` (nuevo) | Esquema SQLite, descarga de temporadas, apertura de la base, consultas y cara a cara. Sin Qt. |
| `core/fotos.py` (nuevo) | Cadena de fotos con caché en disco. Sin Qt. |
| `core/i18n.py` | `NACIONALIDADES_ES` + `traducir_nacionalidad`. |
| `workers/pilotos_worker.py` (nuevo) | `PilotosWorker` (asegura la temporada y lee pilotos/equipos) y `FotosWorker`. |
| `ui/fichas_pilotos.py` (nuevo) | Widgets: `FotoPiloto`, tarjetas, `GrillaTarjetas`, `FichaPiloto`, `TiraResultados`, `FichaEquipo`, y las funciones puras `formato_celda` y `sigla`. |
| `ui/estado.py` (nuevo) | `aplicar_estado()`: el `_set_estado` que hoy está copiado en tres vistas (su `ponytail:` pide extraerlo con la tercera). |
| `ui/pilotos_view.py` (nuevo) | La vista: encabezado, solapas, stack interno, carga diferida, workers. |
| `ui/icons.py` | Constante `SUPERFICIE`. |
| `ui/sidebar.py`, `main.py` | Botón, índice 3 del stack, Esc y cierre. |
| `style.qss` | Reglas de las tarjetas, fichas, tira y cara a cara. |
| `test_historial.py` (nuevo) | Base falsa + tests de `core/historial.py` y `core/fotos.py`. |
| `test_ui.py` | Tests de worker, widgets y vista. |
| `precache_historial.py` (nuevo, local) | Llena la base para el build. |
| `F1CalendarApp.spec`, `.gitignore` (locales) | Empaquetar `cache_historial` y `cache_fotos`. |

---

### Task 1: Base histórica: esquema, descarga y apertura

**Files:**
- Create: `core/historial.py`
- Test: `test_historial.py` (nuevo)

**Interfaces:**
- Produces:
  - `historial.ESQUEMA: str`, `historial.CARPETA = "cache_historial"`, `historial.ARCHIVO = "historial_f1.db"`, `historial.PAUSA_S`, `historial.ANIO_CLASIFICACION = 1994`
  - `historial.pedir_json(ruta: str, offset: int = 0, reintentos: int = 1) -> dict` (devuelve `MRData`)
  - `historial.descargar_temporada(con: sqlite3.Connection, anio: int, pedir=pedir_json) -> None`
  - `historial.temporada_guardada(con, anio: int) -> bool`
  - `historial.abrir_base() -> sqlite3.Connection`
  - `test_historial.base_de_prueba() -> sqlite3.Connection` (en memoria, temporadas 1988, 1990 y 2025) y `test_historial.pedir_falso(ruta, offset=0)`

- [ ] **Step 1: Escribir la base falsa y los tests que fallan**

Crear `test_historial.py`:

```python
"""Chequeos de core/historial.py y core/fotos.py, sin red.

La base se arma pasando respuestas falsas de Jolpica por descargar_temporada,
así cada test prueba también el parseo. Corre con `pytest test_historial.py`
y con `python test_historial.py`.
"""
import os
import sqlite3
import tempfile

from core import historial

historial.PAUSA_S = 0   # las páginas falsas no necesitan esperar

LIMITE = 6   # páginas chicas: la ronda 2 de 2025 queda partida entre dos


def _piloto(driver_id, nombre, apellido, codigo=None, numero=None, nacionalidad="British"):
    d = {"driverId": driver_id, "givenName": nombre, "familyName": apellido,
         "dateOfBirth": "1990-01-01", "nationality": nacionalidad,
         "url": f"http://en.wikipedia.org/wiki/{nombre}_{apellido}"}
    if codigo:
        d["code"] = codigo
    if numero:
        d["permanentNumber"] = numero
    return d


NOR = _piloto("norris", "Lando", "Norris", "NOR", "4")
PIA = _piloto("piastri", "Oscar", "Piastri", "PIA", "81", "Australian")
LEC = _piloto("leclerc", "Charles", "Leclerc", "LEC", "16", "Monegasque")
LAW = _piloto("lawson", "Liam", "Lawson", "LAW", "30", "New Zealander")
SEN = _piloto("senna", "Ayrton", "Senna", nacionalidad="Brazilian")
PRO = _piloto("prost", "Alain", "Prost", nacionalidad="French")
DNQ = _piloto("nadie", "Nadie", "Nunca", nacionalidad="Italian")

MCL = {"constructorId": "mclaren", "name": "McLaren"}
FER = {"constructorId": "ferrari", "name": "Ferrari"}
COL = {"constructorId": "coloni", "name": "Coloni"}

AUS = ("Australian Grand Prix", "Australia")
CHN = ("Chinese Grand Prix", "China")
JPN = ("Japanese Grand Prix", "Japan")
BHR = ("Bahrain Grand Prix", "Bahrain")
USA = ("United States Grand Prix", "USA")
BRA = ("Brazilian Grand Prix", "Brazil")

# (ronda, (gp, país), piloto, equipo, número, largada, positionText, puntos, status)
RESULTADOS = {
    2025: [
        (1, AUS, NOR, MCL, "4", 1, "1", 25, "Finished"),
        (1, AUS, PIA, MCL, "81", 2, "2", 18, "Finished"),
        (1, AUS, LEC, FER, "16", 3, "R", 0, "Engine"),
        (1, AUS, LAW, MCL, "30", 10, "8", 4, "Finished"),
        (2, CHN, PIA, MCL, "81", 1, "1", 25, "Finished"),
        (2, CHN, LEC, FER, "16", 2, "2", 18, "Finished"),
        (2, CHN, NOR, MCL, "4", 4, "3", 15, "Finished"),
        (3, JPN, LEC, FER, "16", 0, "1", 25, "Finished"),
        (3, JPN, NOR, MCL, "4", 2, "R", 0, "Collision"),
        (3, JPN, PIA, MCL, "81", 3, "R", 0, "Collision"),
        (4, BHR, NOR, MCL, "4", 5, "5", 10, "Finished"),
        (4, BHR, PIA, MCL, "81", 6, "R", 0, "Brakes"),
        (4, BHR, LEC, FER, "16", 1, "D", 0, "Disqualified"),
    ],
    1990: [
        (1, USA, SEN, MCL, "27", 1, "1", 9, "Finished"),
        (1, USA, PRO, FER, "1", 2, "R", 0, "Gearbox"),
        (1, USA, DNQ, COL, "31", 0, "F", 0, "Did not qualify"),
    ],
    1988: [
        (1, BRA, SEN, MCL, "12", 1, "1", 9, "Finished"),
        (1, BRA, PRO, MCL, "11", 3, "2", 6, "Finished"),
    ],
}
# (ronda, (gp, país), piloto, equipo, posición)
CLASIFICACION = {
    2025: [
        (1, AUS, NOR, MCL, 1), (1, AUS, PIA, MCL, 2), (1, AUS, LEC, FER, 3), (1, AUS, LAW, MCL, 4),
        (2, CHN, PIA, MCL, 1), (2, CHN, LEC, FER, 2), (2, CHN, NOR, MCL, 3),
        (3, JPN, LEC, FER, 1), (3, JPN, NOR, MCL, 2), (3, JPN, PIA, MCL, 3),
        (4, BHR, LEC, FER, 1), (4, BHR, NOR, MCL, 2), (4, BHR, PIA, MCL, 3),
    ],
}
# (posición o None, piloto, equipo, puntos, victorias)
CAMPEONATO = {
    2025: [(1, NOR, MCL, 50, 1), (2, PIA, MCL, 43, 1), (3, LEC, FER, 43, 1), (4, LAW, MCL, 4, 0)],
    1990: [(1, SEN, MCL, 9, 1), (2, PRO, FER, 0, 0), (None, DNQ, COL, 0, 0)],
    1988: [(1, SEN, MCL, 9, 1), (2, PRO, MCL, 6, 0)],
}
# (posición, equipo, puntos, victorias). 1988 y 1990 quedan sin campeonato de
# constructores a propósito, como pasa antes de 1958.
CONSTRUCTORES = {
    2025: [(1, MCL, 97, 2), (2, FER, 43, 1)],
}


def pedir_falso(ruta, offset=0):
    anio, recurso = ruta.split("/")
    anio = int(anio)
    if recurso == "results":
        filas = [(r, gp, {"number": num, "positionText": pt, "points": str(pts),
                          "grid": str(grid), "status": st, "Driver": d, "Constructor": c})
                 for r, gp, d, c, num, grid, pt, pts, st in RESULTADOS.get(anio, [])]
        return _pagina_carreras(anio, filas, offset, "Results")
    if recurso == "qualifying":
        filas = [(r, gp, {"position": str(pos), "Driver": d, "Constructor": c})
                 for r, gp, d, c, pos in CLASIFICACION.get(anio, [])]
        return _pagina_carreras(anio, filas, offset, "QualifyingResults")
    if recurso == "driverStandings":
        filas = [{**({"position": str(pos)} if pos else {}),
                  "positionText": str(pos) if pos else "-",
                  "points": str(pts), "wins": str(v), "Driver": d, "Constructors": [c]}
                 for pos, d, c, pts, v in CAMPEONATO.get(anio, [])]
        return _pagina_standings(filas, offset, "DriverStandings")
    if recurso == "constructorStandings":
        filas = [{"position": str(pos), "positionText": str(pos), "points": str(pts),
                  "wins": str(v), "Constructor": c}
                 for pos, c, pts, v in CONSTRUCTORES.get(anio, [])]
        return _pagina_standings(filas, offset, "ConstructorStandings")
    raise AssertionError(f"ruta inesperada: {ruta}")


def _pagina_carreras(anio, filas, offset, clave):
    """Como Ergast: corta por filas y agrupa las de cada página por carrera."""
    carreras = []
    for ronda, (gp, pais), fila in filas[offset:offset + LIMITE]:
        if not carreras or carreras[-1]["round"] != str(ronda):
            carreras.append({"season": str(anio), "round": str(ronda), "raceName": gp,
                             "date": f"{anio}-03-0{ronda}",
                             "Circuit": {"Location": {"country": pais}}, clave: []})
        carreras[-1][clave].append(fila)
    return {"limit": str(LIMITE), "offset": str(offset), "total": str(len(filas)),
            "RaceTable": {"Races": carreras}}


def _pagina_standings(filas, offset, clave):
    pagina = filas[offset:offset + LIMITE]
    return {"limit": str(LIMITE), "offset": str(offset), "total": str(len(filas)),
            "StandingsTable": {"StandingsLists": [{clave: pagina}] if pagina else []}}


def base_de_prueba():
    """Base en memoria con 1988, 1990 y 2025. La usa también test_ui.py."""
    con = sqlite3.connect(":memory:")
    con.executescript(historial.ESQUEMA)
    for anio in (1988, 1990, 2025):
        historial.descargar_temporada(con, anio, pedir=pedir_falso)
    return con


def _contar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_descarga_guarda_la_temporada_aunque_venga_partida_en_paginas():
    con = base_de_prueba()
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025") == 13
    # La ronda 2 viene repartida entre dos páginas: igual quedan sus 3 resultados.
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025 AND ronda = 2") == 3
    assert _contar(con, "SELECT COUNT(*) FROM carreras WHERE temporada = 2025") == 4
    assert historial.temporada_guardada(con, 2025)
    assert not historial.temporada_guardada(con, 2024)
    assert con.execute("SELECT codigo FROM pilotos WHERE driver_id = 'norris'").fetchone() == ("NOR",)
    assert con.execute("SELECT codigo FROM pilotos WHERE driver_id = 'senna'").fetchone() == (None,)


def test_posicion_queda_vacia_si_no_es_un_numero():
    con = base_de_prueba()
    filas = con.execute("""SELECT driver_id, posicion, posicion_texto FROM resultados
                           WHERE temporada = 2025 AND ronda = 3 ORDER BY driver_id""").fetchall()
    assert filas == [("leclerc", 1, "1"), ("norris", None, "R"), ("piastri", None, "R")]


def test_volver_a_descargar_reemplaza_en_vez_de_duplicar():
    con = base_de_prueba()
    historial.descargar_temporada(con, 2025, pedir=pedir_falso)
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025") == 13
    assert _contar(con, "SELECT COUNT(*) FROM campeonato_pilotos WHERE temporada = 2025") == 4


def test_si_la_red_se_corta_la_base_queda_como_estaba():
    con = base_de_prueba()

    def pedir_que_falla(ruta, offset=0):
        if ruta.endswith("driverStandings"):
            raise OSError("sin red")
        return pedir_falso(ruta, offset)

    try:
        historial.descargar_temporada(con, 2025, pedir=pedir_que_falla)
    except OSError:
        pass
    else:
        raise AssertionError("tenía que propagar el error de red")
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025") == 13
    assert _contar(con, "SELECT COUNT(*) FROM campeonato_pilotos WHERE temporada = 2025") == 4


def test_antes_de_1994_no_se_pide_la_clasificacion():
    pedidas = []

    def pedir_anotando(ruta, offset=0):
        pedidas.append(ruta)
        return pedir_falso(ruta, offset)

    con = sqlite3.connect(":memory:")
    con.executescript(historial.ESQUEMA)
    historial.descargar_temporada(con, 1990, pedir=pedir_anotando)
    assert "1990/qualifying" not in pedidas, pedidas


def test_abrir_base_copia_la_empaquetada_la_primera_vez():
    empaquetado, escribible = tempfile.mkdtemp(), tempfile.mkdtemp()
    os.makedirs(os.path.join(empaquetado, historial.CARPETA))
    origen = sqlite3.connect(os.path.join(empaquetado, historial.CARPETA, historial.ARCHIVO))
    origen.executescript(historial.ESQUEMA)
    origen.execute("INSERT INTO temporadas VALUES (1999, 'x')")
    origen.commit()
    origen.close()

    originales = (historial.data_path, historial.resource_path)
    historial.data_path = lambda carpeta: os.path.join(escribible, carpeta)
    historial.resource_path = lambda relativa: os.path.join(empaquetado, relativa)
    try:
        con = historial.abrir_base()
        assert historial.temporada_guardada(con, 1999)
        con.close()
        assert os.path.exists(os.path.join(escribible, historial.CARPETA, historial.ARCHIVO))
    finally:
        historial.data_path, historial.resource_path = originales


if __name__ == "__main__":
    for nombre, prueba in list(globals().items()):
        if nombre.startswith("test_"):
            prueba()
    print("ok")
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_historial.py -q`
Expected: FAIL con `ModuleNotFoundError` / `ImportError` (no existe `core.historial`).

- [ ] **Step 3: Implementar `core/historial.py`**

```python
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
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_historial.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add core/historial.py test_historial.py
git commit -m "Historial de Ergast en SQLite: esquema y descarga por temporada

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Consultas de temporada y de carrera

**Files:**
- Modify: `core/historial.py` (agregar al final)
- Test: `test_historial.py` (agregar antes del bloque `if __name__`)

**Interfaces:**
- Consumes: `ESQUEMA`, `LARGO_SQL`, `ANIO_CLASIFICACION`, `base_de_prueba()` (Task 1)
- Produces (todas devuelven tipos planos):
  - `pilotos_temporada(con, anio) -> list[dict]` con claves `driver_id, codigo, nombre, apellido, nacionalidad, nacimiento, url_wiki, headshot_url, constructor_id, equipo, posicion, puntos, numero`
  - `equipos_temporada(con, anio) -> list[dict]` con `constructor_id, nombre, posicion, puntos`
  - `stats_temporada(con, anio, driver_id) -> dict` con `victorias, podios, abandonos, prom_llegada, prom_largada, poles, posicion, puntos`
  - `tira_resultados(con, anio, driver_id) -> list[dict]` con `ronda, gp, largada, posicion, posicion_texto`
  - `carrera_completa(con, driver_id) -> dict` con `victorias, podios, gps, debut, titulos`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `test_historial.py`:

```python
def test_pilotos_ordenados_por_campeonato_y_sin_posicion_al_final():
    con = base_de_prueba()
    pilotos = historial.pilotos_temporada(con, 2025)
    assert [p["driver_id"] for p in pilotos] == ["norris", "piastri", "leclerc", "lawson"]
    nor = pilotos[0]
    assert (nor["codigo"], nor["numero"], nor["equipo"], nor["puntos"]) == ("NOR", "4", "McLaren", 50)

    pilotos_1990 = historial.pilotos_temporada(con, 1990)
    assert [p["driver_id"] for p in pilotos_1990] == ["senna", "prost", "nadie"]
    assert pilotos_1990[0]["codigo"] is None   # Ergast no tiene siglas de esa época
    assert historial.pilotos_temporada(con, 2026) == []


def test_equipos_sin_campeonato_de_constructores_suman_resultados():
    con = base_de_prueba()
    assert [(e["constructor_id"], e["posicion"], e["puntos"])
            for e in historial.equipos_temporada(con, 2025)] == [("mclaren", 1, 97), ("ferrari", 2, 43)]
    assert [(e["constructor_id"], e["posicion"], e["puntos"])
            for e in historial.equipos_temporada(con, 1988)] == [("mclaren", None, 15)]


def test_stats_de_temporada():
    con = base_de_prueba()
    assert historial.stats_temporada(con, 2025, "norris") == {
        "victorias": 1, "podios": 2, "abandonos": 1, "prom_llegada": 3.0,
        "prom_largada": 3.0, "poles": 1, "posicion": 1, "puntos": 50}
    lec = historial.stats_temporada(con, 2025, "leclerc")
    # R1 roto (R) y R4 descalificado (D) son abandonos; largar desde boxes
    # (largada 0) no entra al promedio de largada.
    assert (lec["abandonos"], lec["prom_largada"], lec["poles"]) == (2, 2.0, 2)


def test_antes_de_1994_la_pole_sale_de_la_largada_y_no_clasificar_no_es_abandonar():
    con = base_de_prueba()
    assert historial.stats_temporada(con, 1990, "senna")["poles"] == 1
    assert historial.stats_temporada(con, 1990, "prost")["abandonos"] == 1
    assert historial.stats_temporada(con, 1990, "nadie")["abandonos"] == 0


def test_tira_de_resultados():
    con = base_de_prueba()
    tira = historial.tira_resultados(con, 2025, "norris")
    assert [(f["ronda"], f["gp"], f["largada"], f["posicion"], f["posicion_texto"]) for f in tira] == [
        (1, "Australian Grand Prix", 1, 1, "1"),
        (2, "Chinese Grand Prix", 4, 3, "3"),
        (3, "Japanese Grand Prix", 2, None, "R"),
        (4, "Bahrain Grand Prix", 5, 5, "5"),
    ]


def test_carrera_completa():
    con = base_de_prueba()
    assert historial.carrera_completa(con, "senna") == {
        "victorias": 2, "podios": 2, "gps": 2, "debut": 1988, "titulos": 2}
    # Ergast lo anota en los resultados, pero no largó: no suma GP ni debut.
    assert historial.carrera_completa(con, "nadie") == {
        "victorias": 0, "podios": 0, "gps": 0, "debut": None, "titulos": 0}
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_historial.py -q`
Expected: los 6 nuevos FAIL con `AttributeError: module 'core.historial' has no attribute 'pilotos_temporada'` (y similares).

- [ ] **Step 3: Implementar las consultas**

Agregar al final de `core/historial.py`:

```python
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
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_historial.py -q`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add core/historial.py test_historial.py
git commit -m "Historial: consultas de pilotos, equipos, stats, tira y carrera completa

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Cara a cara entre compañeros

**Files:**
- Modify: `core/historial.py` (imports arriba, función al final)
- Test: `test_historial.py`

**Interfaces:**
- Consumes: `_dicts`, `LARGO_SQL`, `ANIO_CLASIFICACION`, `base_de_prueba()`
- Produces: `cara_a_cara(con, anio, constructor_id) -> dict | None`. El dict trae `"a"` y `"b"` (cada uno con `driver_id, codigo, nombre, apellido, headshot_url, url_wiki`; `a` es el de más puntos) y las tuplas `(a, b)` de `"clasificacion"`, `"carrera"`, `"puntos"`, `"victorias"` y `"podios"`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_cara_a_cara_entre_companeros():
    con = base_de_prueba()
    duelo = historial.cara_a_cara(con, 2025, "mclaren")
    # Lawson corrió una sola carrera para McLaren: el duelo es Norris-Piastri,
    # que corrieron juntos las cuatro. Norris primero por tener más puntos.
    assert (duelo["a"]["driver_id"], duelo["b"]["driver_id"]) == ("norris", "piastri")
    assert duelo["clasificacion"] == (3, 1)
    # R1 Norris, R2 Piastri, R3 abandonaron los dos (no cuenta),
    # R4 Norris terminó y Piastri no.
    assert duelo["carrera"] == (2, 1)
    assert duelo["puntos"] == (50, 43)
    assert duelo["victorias"] == (1, 1)
    assert duelo["podios"] == (2, 2)


def test_cara_a_cara_sin_companero_es_none():
    con = base_de_prueba()
    assert historial.cara_a_cara(con, 2025, "ferrari") is None
    assert historial.cara_a_cara(con, 2025, "no_existe") is None


def test_cara_a_cara_antes_de_1994_compara_la_largada():
    duelo = historial.cara_a_cara(base_de_prueba(), 1988, "mclaren")
    assert (duelo["a"]["driver_id"], duelo["clasificacion"], duelo["carrera"]) == \
        ("senna", (1, 0), (1, 0))
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_historial.py -q`
Expected: 3 FAIL con `AttributeError: ... 'cara_a_cara'`.

- [ ] **Step 3: Implementar**

En `core/historial.py`, agregar a los imports:

```python
from collections import Counter, defaultdict
from itertools import combinations
```

Y al final:

```python
def cara_a_cara(con, anio, constructor_id):
    """Duelo entre los dos pilotos del equipo que más carreras largaron juntos.
    None si el equipo nunca tuvo dos pilotos en una misma carrera."""
    filas = _dicts(con.execute(f"""
        SELECT ronda, driver_id, largada, posicion FROM resultados
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

    puntos = dict(con.execute("""SELECT driver_id, puntos FROM campeonato_pilotos
                                  WHERE temporada = ? AND driver_id IN (?, ?)""",
                              (anio, a, b)).fetchall())
    if puntos.get(b, 0) > puntos.get(a, 0):
        a, b = b, a

    rondas = [r for r, pilotos in por_ronda.items() if a in pilotos and b in pilotos]
    if anio >= ANIO_CLASIFICACION:
        grilla = defaultdict(dict)
        for ronda, piloto, posicion in con.execute(
                """SELECT ronda, driver_id, posicion FROM clasificacion
                    WHERE temporada = ? AND driver_id IN (?, ?)""", (anio, a, b)):
            grilla[ronda][piloto] = posicion
    else:   # sin clasificación en Ergast: la grilla de largada (0 = boxes, no cuenta)
        grilla = {r: {p: f["largada"] or None for p, f in pilotos.items()}
                  for r, pilotos in por_ronda.items()}

    clasificacion, carrera = [0, 0], [0, 0]
    for ronda in rondas:
        qa, qb = grilla.get(ronda, {}).get(a), grilla.get(ronda, {}).get(b)
        if qa and qb:
            clasificacion[0 if qa < qb else 1] += 1
        pa, pb = por_ronda[ronda][a]["posicion"], por_ronda[ronda][b]["posicion"]
        if pa is None and pb is None:
            continue   # abandonaron los dos: la carrera no cuenta
        if pb is None or (pa is not None and pa < pb):
            carrera[0] += 1
        else:
            carrera[1] += 1

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
        "puntos": (puntos.get(a, 0), puntos.get(b, 0)),
        "victorias": (contar(a, 1), contar(b, 1)),
        "podios": (contar(a, 3), contar(b, 3)),
    }
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_historial.py -q`
Expected: `15 passed`

- [ ] **Step 5: Commit**

```bash
git add core/historial.py test_historial.py
git commit -m "Historial: cara a cara entre compañeros de equipo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Fotos de pilotos

**Files:**
- Create: `core/fotos.py`
- Test: `test_historial.py`

**Interfaces:**
- Produces: `fotos.obtener_ruta_foto(driver_id: str, headshot_url: str | None = None, url_wiki: str | None = None) -> str | None`, más los internos `_bajar(url, destino)`, `_url_wikipedia(url_wiki) -> str | None` y `_fallidas: set` (los tests los reemplazan).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `test_historial.py` (el import va arriba, con los demás):

```python
from core import fotos


def _fotos_en_carpeta_temporal():
    carpeta = tempfile.mkdtemp()
    originales = (fotos.data_path, fotos.ruta_cache, fotos._bajar, fotos._url_wikipedia)
    fotos.data_path = lambda nombre: carpeta
    fotos.ruta_cache = lambda nombre, archivo: (os.path.join(carpeta, archivo), True)
    fotos._fallidas.clear()
    return carpeta, originales


def _restaurar_fotos(originales):
    fotos.data_path, fotos.ruta_cache, fotos._bajar, fotos._url_wikipedia = originales


def _archivo_vacio(destino):
    open(destino, "wb").close()


def test_foto_oficial_primero_y_despues_del_cache():
    carpeta, originales = _fotos_en_carpeta_temporal()
    bajadas = []

    def bajar(url, destino):
        bajadas.append(url)
        _archivo_vacio(destino)

    def wikipedia(url_wiki):
        raise AssertionError("con foto oficial no hacía falta Wikipedia")

    fotos._bajar, fotos._url_wikipedia = bajar, wikipedia
    try:
        ruta = fotos.obtener_ruta_foto("norris", "https://f1/norris.png",
                                       "http://en.wikipedia.org/wiki/Lando_Norris")
        assert ruta == os.path.join(carpeta, "norris.png")
        assert fotos.obtener_ruta_foto("norris", "https://f1/norris.png") == ruta
        assert bajadas == ["https://f1/norris.png"], "la segunda vez tenía que salir del caché"
    finally:
        _restaurar_fotos(originales)


def test_si_falla_la_oficial_usa_wikipedia():
    carpeta, originales = _fotos_en_carpeta_temporal()

    def bajar(url, destino):
        if url.startswith("https://f1/"):
            raise OSError("404")
        _archivo_vacio(destino)

    fotos._bajar = bajar
    fotos._url_wikipedia = lambda url_wiki: "https://upload.wikimedia.org/senna.jpg"
    try:
        assert fotos.obtener_ruta_foto(
            "senna", "https://f1/senna.png",
            "http://en.wikipedia.org/wiki/Ayrton_Senna") == os.path.join(carpeta, "senna.jpg")
    finally:
        _restaurar_fotos(originales)


def test_sin_ninguna_foto_devuelve_none_y_no_reintenta():
    carpeta, originales = _fotos_en_carpeta_temporal()
    intentos = []

    def bajar(url, destino):
        intentos.append(url)
        raise OSError("sin red")

    fotos._bajar = bajar
    fotos._url_wikipedia = lambda url_wiki: "https://upload.wikimedia.org/x.jpg"
    try:
        for _ in range(2):
            assert fotos.obtener_ruta_foto("nadie", "https://f1/x.png",
                                           "http://en.wikipedia.org/wiki/X") is None
        assert len(intentos) == 2, intentos   # oficial + Wikipedia, una sola vez
    finally:
        _restaurar_fotos(originales)
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_historial.py -q`
Expected: FAIL al importar (`ImportError: cannot import name 'fotos'`).

- [ ] **Step 3: Implementar `core/fotos.py`**

```python
"""Fotos de pilotos: la oficial de F1, si no la de Wikipedia, si no None (la
UI dibuja la sigla sobre el color del equipo). Mismo esquema de caché que las
banderas de core/flags.py: lo empaquetado primero, si no se baja al lado del exe.
"""
import json
import os
import urllib.request

from core.paths import data_path, ruta_cache

CARPETA = "cache_fotos"
USER_AGENT = "F1CalendarApp/1.0"   # Wikimedia rechaza pedidos sin User-Agent

# Pilotos sin foto en ninguna fuente: no se reintenta en esta sesión.
_fallidas = set()


def _bajar(url, destino):
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        datos = respuesta.read()
    # Se escribe recién con todo bajado: un corte de red no deja un archivo a medias.
    with open(destino, "wb") as archivo:
        archivo.write(datos)


def _url_wikipedia(url_wiki):
    titulo = url_wiki.rstrip("/").rsplit("/wiki/", 1)[-1]
    pedido = urllib.request.Request(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{titulo}",
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        return (json.load(respuesta).get("thumbnail") or {}).get("source")


def obtener_ruta_foto(driver_id, headshot_url=None, url_wiki=None):
    for extension in ("png", "jpg"):
        ruta, _ = ruta_cache(CARPETA, f"{driver_id}.{extension}")
        if os.path.exists(ruta):
            return ruta
    if driver_id in _fallidas:
        return None

    fuentes = []
    if headshot_url:
        fuentes.append(("png", lambda: headshot_url))
    if url_wiki:
        fuentes.append(("jpg", lambda: _url_wikipedia(url_wiki)))

    os.makedirs(data_path(CARPETA), exist_ok=True)
    for extension, buscar_url in fuentes:
        try:
            origen = buscar_url()
            if not origen:
                continue
            destino = os.path.join(data_path(CARPETA), f"{driver_id}.{extension}")
            _bajar(origen, destino)
            return destino
        except Exception:
            continue
    _fallidas.add(driver_id)
    return None
```

(La miniatura de Wikipedia a veces es PNG aunque se guarde como `.jpg`. No hay problema: `QPixmap` detecta el formato mirando el contenido del archivo.)

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_historial.py -q`
Expected: `18 passed`

- [ ] **Step 5: Commit**

```bash
git add core/fotos.py test_historial.py
git commit -m "Fotos de pilotos: oficial F1, Wikipedia o nada, con caché en disco

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Workers, foto oficial y nacionalidades

**Files:**
- Modify: `core/historial.py` (agregar `completar_headshots`)
- Modify: `core/i18n.py` (agregar al final)
- Create: `workers/pilotos_worker.py`
- Test: `test_ui.py`

**Interfaces:**
- Consumes: `historial.abrir_base`, `temporada_guardada`, `descargar_temporada`, `pilotos_temporada`, `equipos_temporada` (Tasks 1-2); `fotos.obtener_ruta_foto` (Task 4)
- Produces:
  - `historial.completar_headshots(con, anio) -> None`
  - `i18n.traducir_nacionalidad(gentilicio: str | None) -> str`
  - `pilotos_worker.anio_actual() -> int`, `pilotos_worker._ACTUALIZADAS: set`
  - `PilotosWorker(year)`: atributo `.year`, señales `terminado(object)` (emite `{"pilotos": list[dict], "equipos": list[dict]}`) y `error(str)`
  - `FotosWorker(pilotos: list[dict])`: señal `foto_lista(str driver_id, str ruta)`

- [ ] **Step 1: Escribir los tests que fallan**

En `test_ui.py`, agregar después de los imports existentes:

```python
import workers.pilotos_worker as pilotos_worker
from test_historial import base_de_prueba
```

Y antes del bloque `if __name__ == "__main__":`:

```python
def _correr_pilotos_worker(year, descargar, anio_actual, limpiar=True):
    """Corre PilotosWorker.run() en el hilo del test, con la base falsa y la
    descarga reemplazada. Devuelve (emitidos por terminado, emitidos por error)."""
    base = base_de_prueba()   # antes de reemplazar descargar_temporada: la usa
    h = pilotos_worker.historial
    originales = (h.abrir_base, h.descargar_temporada, h.completar_headshots,
                  pilotos_worker.anio_actual)
    h.abrir_base = lambda: base
    h.descargar_temporada = descargar
    h.completar_headshots = lambda con, anio: None
    pilotos_worker.anio_actual = lambda: anio_actual
    if limpiar:
        pilotos_worker._ACTUALIZADAS.clear()
    try:
        worker = pilotos_worker.PilotosWorker(year)
        datos, errores = [], []
        worker.terminado.connect(datos.append)
        worker.error.connect(errores.append)
        worker.run()
        return datos, errores
    finally:
        (h.abrir_base, h.descargar_temporada, h.completar_headshots,
         pilotos_worker.anio_actual) = originales


def _sin_red(con, anio):
    raise OSError("sin red")


def test_temporada_terminada_y_guardada_no_toca_la_red():
    datos, errores = _correr_pilotos_worker(2025, _sin_red, anio_actual=2026)
    assert not errores, errores
    assert [p["driver_id"] for p in datos[0]["pilotos"]] == ["norris", "piastri", "leclerc", "lawson"]
    assert [e["constructor_id"] for e in datos[0]["equipos"]] == ["mclaren", "ferrari"]


def test_temporada_en_curso_sin_red_muestra_lo_guardado():
    datos, errores = _correr_pilotos_worker(2025, _sin_red, anio_actual=2025)
    assert not errores, errores
    assert len(datos[0]["pilotos"]) == 4


def test_temporada_que_falta_y_sin_red_da_error():
    datos, errores = _correr_pilotos_worker(2026, _sin_red, anio_actual=2026)
    assert datos == [] and errores == ["sin red"], (datos, errores)


def test_la_temporada_en_curso_se_baja_una_sola_vez_por_sesion():
    llamadas = []
    _correr_pilotos_worker(2025, lambda con, anio: llamadas.append(anio), anio_actual=2025)
    _correr_pilotos_worker(2025, lambda con, anio: llamadas.append(anio), anio_actual=2025,
                           limpiar=False)
    assert llamadas == [2025], llamadas
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_ui.py -q`
Expected: FAIL al importar (`ModuleNotFoundError: No module named 'workers.pilotos_worker'`).

- [ ] **Step 3: Implementar**

Agregar al final de `core/historial.py`:

```python
def completar_headshots(con, anio):
    """Foto oficial de F1 de los pilotos del año, sacada de la última carrera.
    FastF1 la trae vacía en temporadas viejas (en 2018 ya no viene)."""
    import fastf1   # pesado: sólo se importa cuando hace falta

    ultima = con.execute("SELECT MAX(ronda) FROM resultados WHERE temporada = ?",
                         (anio,)).fetchone()[0]
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
```

Agregar al final de `core/i18n.py`:

```python
# Ergast da la nacionalidad como gentilicio en inglés ("British"); la ficha
# muestra el país.
NACIONALIDADES_ES = {
    "American": "Estados Unidos", "American-Italian": "Estados Unidos",
    "Argentine": "Argentina", "Argentine-Italian": "Argentina",
    "Australian": "Australia", "Austrian": "Austria", "Belgian": "Bélgica",
    "Brazilian": "Brasil", "British": "Reino Unido", "Canadian": "Canadá",
    "Chilean": "Chile", "Chinese": "China", "Colombian": "Colombia",
    "Czech": "República Checa", "Danish": "Dinamarca", "Dutch": "Países Bajos",
    "East German": "Alemania Oriental", "Finnish": "Finlandia", "French": "Francia",
    "German": "Alemania", "Hungarian": "Hungría", "Indian": "India",
    "Indonesian": "Indonesia", "Irish": "Irlanda", "Italian": "Italia",
    "Japanese": "Japón", "Liechtensteiner": "Liechtenstein", "Malaysian": "Malasia",
    "Mexican": "México", "Monegasque": "Mónaco", "New Zealander": "Nueva Zelanda",
    "Polish": "Polonia", "Portuguese": "Portugal", "Rhodesian": "Rodesia",
    "Russian": "Rusia", "South African": "Sudáfrica", "Spanish": "España",
    "Swedish": "Suecia", "Swiss": "Suiza", "Thai": "Tailandia",
    "Uruguayan": "Uruguay", "Venezuelan": "Venezuela",
}


def traducir_nacionalidad(texto):
    if texto is None:
        return ""
    return NACIONALIDADES_ES.get(str(texto), str(texto))
```

Crear `workers/pilotos_worker.py`:

```python
from datetime import date

from PySide6.QtCore import QThread, Signal

from core import historial
from core.fotos import obtener_ruta_foto

# Temporadas en curso ya refrescadas en esta sesión de la app: la API se
# consulta una vez por arranque, no cada vez que se vuelve a la pestaña.
_ACTUALIZADAS = set()


def anio_actual():
    return date.today().year


class PilotosWorker(QThread):
    terminado = Signal(object)   # {'pilotos': [dict], 'equipos': [dict]}
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year

    def run(self):
        try:
            con = historial.abrir_base()
        except Exception as e:
            self.error.emit(str(e))
            return
        try:
            self._actualizar(con)
            datos = {"pilotos": historial.pilotos_temporada(con, self.year),
                     "equipos": historial.equipos_temporada(con, self.year)}
        except Exception as e:
            self.error.emit(str(e))
            return
        finally:
            con.close()
        self.terminado.emit(datos)

    def _actualizar(self, con):
        guardada = historial.temporada_guardada(con, self.year)
        en_curso = self.year >= anio_actual()
        if guardada and (not en_curso or self.year in _ACTUALIZADAS):
            return
        try:
            historial.descargar_temporada(con, self.year)
        except Exception:
            if not guardada:
                raise     # no hay nada guardado que mostrar
            return        # sin red: se muestra lo último guardado
        _ACTUALIZADAS.add(self.year)
        if en_curso:
            try:
                historial.completar_headshots(con, self.year)
            except Exception:
                pass      # sin foto oficial quedan Wikipedia o el placeholder


class FotosWorker(QThread):
    foto_lista = Signal(str, str)   # driver_id, ruta local

    def __init__(self, pilotos):
        super().__init__()
        self.pilotos = pilotos

    def run(self):
        for piloto in self.pilotos:
            if self.isInterruptionRequested():
                return    # cambiaron de año: estas fotos ya no hacen falta
            ruta = obtener_ruta_foto(piloto["driver_id"], piloto.get("headshot_url"),
                                     piloto.get("url_wiki"))
            if ruta:
                self.foto_lista.emit(piloto["driver_id"], ruta)
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_ui.py test_historial.py -q`
Expected: todo PASS (los 14 tests de antes de `test_ui.py` + 4 nuevos + 18 de historial).

- [ ] **Step 5: Commit**

```bash
git add core/historial.py core/i18n.py workers/pilotos_worker.py test_ui.py
git commit -m "Workers de pilotos y fotos; foto oficial y nacionalidades

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Widgets de tarjetas y fichas

**Files:**
- Create: `ui/fichas_pilotos.py`
- Modify: `ui/icons.py` (constante `SUPERFICIE` junto a las otras de la paleta)
- Modify: `style.qss` (bloque nuevo antes de `/* ---------- Estado (cargando / error) ---------- */`)
- Test: `test_ui.py`

**Interfaces:**
- Consumes: `traducir_evento`, `traducir_nacionalidad` (`core/i18n.py`); `MUTED, PRIMARIO, DATO, BORDE, SUPERFICIE` (`ui/icons.py`); los dicts de las Tasks 2-3
- Produces:
  - `formato_celda(fila: dict) -> tuple[str, str, str]` → `(texto, delta, estado)`, con `estado` en `{"podio", "normal", "abandono", "ausente"}`
  - `sigla(piloto: dict) -> str`
  - `FotoPiloto(lado)`, con `.driver_id`, `set_piloto(driver_id, sigla, numero, color)` y `set_foto(ruta)`
  - `TarjetaPiloto(piloto, color)` y `TarjetaEquipo(equipo, color)`: señal `clicked(str)`, atributo `.clave`; además `TarjetaPiloto.foto`
  - `GrillaTarjetas()`, con `set_tarjetas(list)` y `tarjetas() -> list`
  - `FichaPiloto()`, con `.foto`, `.tira` y `mostrar(piloto, color, anio, stats, tira, carrera)`
  - `TiraResultados()`, con `set_resultados(filas)` y `celdas() -> list`
  - `FichaEquipo()`, con `.foto_a`, `.foto_b`, `.filas` (dict `clave -> FilaCaraACara`), `.sin_duelo`, `.bloque_duelo` y `mostrar(equipo, color, anio, h2h)`
  - `FilaCaraACara`, con `.valor_a` y `.valor_b` (QLabel)

- [ ] **Step 1: Escribir los tests que fallan**

En `test_ui.py`, agregar a los imports:

```python
from ui.fichas_pilotos import formato_celda, sigla
```

Antes del `if __name__`:

```python
def test_formato_de_las_celdas_de_la_tira():
    def celda(largada, posicion, texto):
        return formato_celda({"largada": largada, "posicion": posicion, "posicion_texto": texto})

    assert celda(1, 1, "1") == ("P1", "=", "podio")
    assert celda(4, 3, "3") == ("P3", "▲1", "podio")
    assert celda(2, 7, "7") == ("P7", "▼5", "normal")
    assert celda(0, 1, "1") == ("P1", "boxes", "podio")
    assert celda(2, None, "R") == ("DNF", "", "abandono")
    assert celda(1, None, "D") == ("DSQ", "", "abandono")
    assert celda(0, None, "F") == ("DNQ", "", "ausente")
    assert celda(0, None, "W") == ("DNS", "", "ausente")


def test_sigla_de_pilotos_sin_codigo():
    assert sigla({"codigo": "NOR", "apellido": "Norris"}) == "NOR"
    assert sigla({"codigo": None, "apellido": "Senna"}) == "SEN"
```

En `test_contraste_de_la_paleta`, agregar dos pares a la lista `pares` (después de `"dato / bg-sunken"`):

```python
        # Tira de resultados: podio y abandono sobre el panel de la celda.
        ("oro / bg-panel",              "#F3D27A", "#12161C", AA_TEXTO),
        ("error / bg-panel",            "#FF6B57", "#12161C", AA_TEXTO),
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_ui.py -q`
Expected: FAIL al importar (`ModuleNotFoundError: No module named 'ui.fichas_pilotos'`).

- [ ] **Step 3: Implementar**

En `ui/icons.py`, debajo de `BORDE = "#2D3541"`:

```python
SUPERFICIE = "#1B2029"  # fondo de las fotos de piloto, bajo el degradé del equipo
```

Crear `ui/fichas_pilotos.py`:

```python
"""Piezas de la pestaña Pilotos: foto, tarjetas, grilla y fichas.

Los datos llegan como dicts planos de core/historial.py; acá sólo se pintan.
"""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
)

from core.i18n import traducir_evento, traducir_nacionalidad
from ui.icons import BORDE, DATO, MUTED, PRIMARIO, SUPERFICIE


def formato_celda(fila):
    """(texto, delta contra la largada, estado) de una celda de la tira."""
    posicion, texto = fila["posicion"], fila["posicion_texto"]
    if posicion is not None:
        largada = fila["largada"]
        if not largada:
            delta = "boxes"
        elif largada > posicion:
            delta = f"▲{largada - posicion}"
        elif largada < posicion:
            delta = f"▼{posicion - largada}"
        else:
            delta = "="
        return f"P{posicion}", delta, "podio" if posicion <= 3 else "normal"
    if texto in ("D", "E"):
        return "DSQ", "", "abandono"
    if texto == "F":
        return "DNQ", "", "ausente"
    if texto == "W":
        return "DNS", "", "ausente"
    return "DNF", "", "abandono"


def sigla(piloto):
    """Ergast no tiene siglas para los pilotos viejos: tres letras del apellido."""
    return piloto.get("codigo") or (piloto.get("apellido") or "?")[:3].upper()


def _numero(valor):
    return None if valor is None else f"{valor:g}"


def _promedio(valor):
    return None if valor is None else f"{valor:.1f}"


class FotoPiloto(QWidget):
    """Foto recortada en cuadrado sobre un degradé del color del equipo. Sin
    foto (todavía bajando, o no existe ninguna) muestra la sigla."""

    def __init__(self, lado, parent=None):
        super().__init__(parent)
        self.setFixedSize(lado, lado)
        self.driver_id = None
        self._sigla = ""
        self._numero = ""
        self._color = QColor(MUTED)
        self._pixmap = None

    def set_piloto(self, driver_id, sigla_piloto, numero, color):
        self.driver_id = driver_id
        self._sigla = sigla_piloto
        self._numero = str(numero) if numero else ""
        self._color = QColor(color or MUTED)
        self._pixmap = None
        self.update()

    def set_foto(self, ruta):
        original = QPixmap(ruta)
        if original.isNull():
            return
        # Se escala una sola vez (el tamaño es fijo) y se recorta anclado
        # arriba, que es donde están las caras.
        dpr = self.devicePixelRatioF()
        lado = round(self.width() * dpr)
        escalado = original.scaled(lado, lado, Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
        self._pixmap = escalado.copy((escalado.width() - lado) // 2, 0, lado, lado)
        self._pixmap.setDevicePixelRatio(dpr)
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        borde = QPainterPath()
        borde.addRoundedRect(rect, 4, 4)
        pintor.setClipPath(borde)

        tono = QColor(self._color)
        tono.setAlpha(150)
        degrade = QLinearGradient(0, 0, 0, rect.height())
        degrade.setColorAt(0, tono)
        degrade.setColorAt(1, QColor(SUPERFICIE))
        pintor.fillRect(rect, degrade)

        if self._pixmap is not None:
            pintor.drawPixmap(0, 0, self._pixmap)
        else:
            fuente = QFont("Titillium Web")
            fuente.setPixelSize(max(17, self.height() // 4))
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QColor(PRIMARIO))
            pintor.drawText(rect, Qt.AlignCenter, self._sigla)

        if self._numero and self.width() >= 100:
            fuente = QFont()
            fuente.setPixelSize(13)
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QColor(PRIMARIO))
            pintor.drawText(rect.adjusted(8, 6, -8, -6), Qt.AlignLeft | Qt.AlignTop, self._numero)


class _TarjetaClickeable(QFrame):
    """Click o Enter/Espacio emiten `clicked(clave)`."""
    clicked = Signal(str)

    def __init__(self, nombre_objeto, clave):
        super().__init__()
        self.setObjectName(nombre_objeto)
        self.clave = clave
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, evento):
        evento.accept()   # sin esto, el release no llega a la tarjeta

    def mouseReleaseEvent(self, evento):
        if evento.button() == Qt.LeftButton and self.rect().contains(evento.position().toPoint()):
            self.clicked.emit(self.clave)

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit(self.clave)
            return
        super().keyPressEvent(evento)


class TarjetaPiloto(_TarjetaClickeable):
    ANCHO = 140

    def __init__(self, piloto, color):
        super().__init__("tarjetaPiloto", piloto["driver_id"])
        self.setFixedWidth(self.ANCHO)
        self.setToolTip(f"{piloto['nombre']} {piloto['apellido']}")

        self.foto = FotoPiloto(self.ANCHO - 2)   # 1 px de borde por lado
        self.foto.set_piloto(piloto["driver_id"], sigla(piloto), piloto.get("numero"), color)
        franja = QFrame()
        franja.setFixedHeight(3)
        franja.setStyleSheet(f"background-color: {color or MUTED};")

        codigo = QLabel(sigla(piloto))
        codigo.setObjectName("siglaTarjeta")
        equipo = QLabel(piloto.get("equipo") or "")
        equipo.setObjectName("detalleTarjeta")
        puntos = QLabel(_numero(piloto.get("puntos")) or "")
        puntos.setObjectName("puntosTarjeta")

        fila = QHBoxLayout()
        fila.setSpacing(6)
        fila.addWidget(equipo, 1)
        fila.addWidget(puntos)
        pie = QVBoxLayout()
        pie.setContentsMargins(10, 6, 10, 8)
        pie.setSpacing(0)
        pie.addWidget(codigo)
        pie.addLayout(fila)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.foto)
        layout.addWidget(franja)
        layout.addLayout(pie)


class TarjetaEquipo(_TarjetaClickeable):
    ANCHO = 220

    def __init__(self, equipo, color):
        super().__init__("tarjetaEquipo", equipo["constructor_id"])
        self.setFixedWidth(self.ANCHO)

        franja = QFrame()
        franja.setFixedWidth(4)
        franja.setStyleSheet(f"background-color: {color or MUTED}; border-radius: 2px;")
        nombre = QLabel(equipo["nombre"])
        nombre.setObjectName("nombreTarjeta")
        partes = [f"P{equipo['posicion']}"] if equipo["posicion"] else []
        partes.append(f"{_numero(equipo['puntos'] or 0)} pts")
        detalle = QLabel("  ·  ".join(partes))
        detalle.setObjectName("detalleTarjeta")

        columna = QVBoxLayout()
        columna.setSpacing(2)
        columna.addWidget(nombre)
        columna.addWidget(detalle)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(franja)
        layout.addLayout(columna, 1)


class GrillaTarjetas(QScrollArea):
    """Tarjetas de ancho fijo en tantas columnas como entren a lo ancho."""
    ESPACIO = 10

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        # Sin scroll horizontal: se comería las flechas que cambian de año.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        contenedor = QWidget()
        self._grilla = QGridLayout(contenedor)
        self._grilla.setContentsMargins(0, 0, 0, 16)
        self._grilla.setSpacing(self.ESPACIO)
        self._grilla.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setWidget(contenedor)
        self._tarjetas = []
        self._columnas = 0

    def tarjetas(self):
        return list(self._tarjetas)

    def set_tarjetas(self, tarjetas):
        for vieja in self._tarjetas:
            self._grilla.removeWidget(vieja)
            vieja.deleteLater()
        self._tarjetas = list(tarjetas)
        for tarjeta in self._tarjetas:
            # Con padre antes de mostrarse: si no, show() la vuelve una ventana suelta.
            tarjeta.setParent(self.widget())
        self._columnas = 0
        self._acomodar()

    def _acomodar(self):
        if not self._tarjetas:
            return
        paso = self._tarjetas[0].maximumWidth() + self.ESPACIO
        columnas = max(1, (self.viewport().width() + self.ESPACIO) // paso)
        if columnas == self._columnas:
            return
        self._columnas = columnas
        for tarjeta in self._tarjetas:
            self._grilla.removeWidget(tarjeta)
        for i, tarjeta in enumerate(self._tarjetas):
            self._grilla.addWidget(tarjeta, i // columnas, i % columnas)
            tarjeta.show()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._acomodar()


class FilaStats(QWidget):
    """Cajas KPI (mismo estilo que Clasificación) en una grilla de `columnas`."""

    def __init__(self, etiquetas, columnas, dato=False):
        super().__init__()
        self._dato = dato
        self._valores = []
        grilla = QGridLayout(self)
        grilla.setContentsMargins(0, 0, 0, 0)
        grilla.setSpacing(8)
        for i, texto in enumerate(etiquetas):
            caja = QFrame()
            caja.setObjectName("kpi")
            etiqueta = QLabel(texto.upper())
            etiqueta.setObjectName("etiquetaRonda")
            valor = QLabel("—")
            valor.setObjectName("valorKpi")
            columna = QVBoxLayout(caja)
            columna.setContentsMargins(12, 8, 12, 8)
            columna.setSpacing(2)
            columna.addWidget(etiqueta)
            columna.addWidget(valor)
            grilla.addWidget(caja, i // columnas, i % columnas)
            self._valores.append(valor)

    def set_valores(self, valores):
        for etiqueta, valor in zip(self._valores, valores):
            texto = "—" if valor is None else str(valor)
            etiqueta.setText(f"<span style='color:{DATO};'>{texto}</span>" if self._dato else texto)


def _celda(fila):
    texto, delta, estado = formato_celda(fila)
    celda = QFrame()
    celda.setObjectName("celdaResultado")
    celda.setProperty("estado", estado)
    celda.setFixedWidth(46)
    celda.setToolTip(f"R{fila['ronda']} · {traducir_evento(fila['gp'])}")
    arriba = QLabel(texto)
    arriba.setObjectName("textoCelda")
    arriba.setAlignment(Qt.AlignCenter)
    abajo = QLabel(delta or " ")
    abajo.setObjectName("deltaCelda")
    abajo.setAlignment(Qt.AlignCenter)
    abajo.setProperty("sentido", "sube" if delta.startswith("▲") else "otro")
    columna = QVBoxLayout(celda)
    columna.setContentsMargins(2, 4, 2, 4)
    columna.setSpacing(0)
    columna.addWidget(arriba)
    columna.addWidget(abajo)
    return celda


class TiraResultados(QWidget):
    """Una celda por carrera: llegada (o DNF/DSQ/DNQ/DNS) y delta contra la largada."""
    POR_FILA = 12

    def __init__(self):
        super().__init__()
        self._grilla = QGridLayout(self)
        self._grilla.setContentsMargins(0, 0, 0, 0)
        self._grilla.setSpacing(4)
        self._grilla.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._celdas = []

    def celdas(self):
        return list(self._celdas)

    def set_resultados(self, filas):
        while self._grilla.count():
            item = self._grilla.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._celdas = [_celda(fila) for fila in filas]
        for i, celda in enumerate(self._celdas):
            self._grilla.addWidget(celda, i // self.POR_FILA, i % self.POR_FILA)
        if not filas:
            vacio = QLabel("Sin carreras disputadas.")
            vacio.setObjectName("estadoVacio")
            self._grilla.addWidget(vacio, 0, 0, 1, self.POR_FILA)


class FichaPiloto(QWidget):
    def __init__(self):
        super().__init__()
        self.foto = FotoPiloto(180)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreFicha")
        self.meta = QLabel()
        self.meta.setObjectName("metaFicha")
        self.titulo_temporada = QLabel()
        self.titulo_temporada.setObjectName("etiquetaRonda")
        self.stats_temporada = FilaStats(
            ["Posición", "Puntos", "Victorias", "Podios", "Poles", "Abandonos",
             "Prom. llegada", "Prom. largada"], columnas=4)
        titulo_tira = QLabel("CARRERA POR CARRERA")
        titulo_tira.setObjectName("etiquetaRonda")
        self.tira = TiraResultados()
        titulo_carrera = QLabel("CARRERA COMPLETA")
        titulo_carrera.setObjectName("etiquetaRonda")
        self.stats_carrera = FilaStats(["Títulos", "Victorias", "Podios", "GPs", "Debut"],
                                       columnas=5, dato=True)

        columna = QVBoxLayout()
        columna.setSpacing(8)
        columna.addWidget(self.nombre)
        columna.addWidget(self.meta)
        columna.addSpacing(8)
        for widget in (self.titulo_temporada, self.stats_temporada, titulo_tira, self.tira,
                       titulo_carrera, self.stats_carrera):
            columna.addWidget(widget)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self.foto, alignment=Qt.AlignTop)
        layout.addLayout(columna, 1)

    def mostrar(self, piloto, color, anio, stats, tira, carrera):
        self.foto.set_piloto(piloto["driver_id"], sigla(piloto), piloto.get("numero"), color)
        self.nombre.setText(f"{piloto['nombre']} {piloto['apellido']}")
        partes = []
        if piloto.get("numero"):
            partes.append(f"#{piloto['numero']}")
        if piloto.get("equipo"):
            partes.append(piloto["equipo"])
        if piloto.get("nacionalidad"):
            partes.append(traducir_nacionalidad(piloto["nacionalidad"]))
        if piloto.get("nacimiento"):
            partes.append(f"{anio - int(piloto['nacimiento'][:4])} años en {anio}")
        self.meta.setText("  ·  ".join(partes))

        self.titulo_temporada.setText(f"TEMPORADA {anio}")
        self.stats_temporada.set_valores([
            f"P{stats['posicion']}" if stats["posicion"] else None,
            _numero(stats["puntos"]), stats["victorias"], stats["podios"], stats["poles"],
            stats["abandonos"], _promedio(stats["prom_llegada"]),
            _promedio(stats["prom_largada"])])
        self.tira.set_resultados(tira)
        self.stats_carrera.set_valores([carrera["titulos"], carrera["victorias"],
                                        carrera["podios"], carrera["gps"], carrera["debut"]])


class BarraPartida(QWidget):
    """Barra repartida en proporción a (a, b): a en DATO, b en gris."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(8)
        self._a = self._b = 0

    def set_proporcion(self, a, b):
        self._a, self._b = a, b
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        ancho, alto = self.width(), self.height()
        total = self._a + self._b
        if total <= 0:
            pintor.setBrush(QColor(BORDE))
            pintor.drawRoundedRect(QRectF(0, 0, ancho, alto), 4, 4)
            return
        corte = round(ancho * self._a / total)
        pintor.setBrush(QColor(DATO))
        pintor.drawRoundedRect(QRectF(0, 0, corte, alto), 4, 4)
        pintor.setBrush(QColor(BORDE))
        pintor.drawRoundedRect(QRectF(corte + 2, 0, max(0, ancho - corte - 2), alto), 4, 4)


class FilaCaraACara(QWidget):
    def __init__(self, nombre):
        super().__init__()
        self.valor_a = QLabel()
        self.valor_a.setObjectName("valorDuelo")
        self.valor_a.setFixedWidth(56)
        self.valor_b = QLabel()
        self.valor_b.setObjectName("valorDuelo")
        self.valor_b.setFixedWidth(56)
        self.valor_b.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        etiqueta = QLabel(nombre.upper())
        etiqueta.setObjectName("etiquetaRonda")
        etiqueta.setAlignment(Qt.AlignCenter)
        self.barra = BarraPartida()

        centro = QVBoxLayout()
        centro.setSpacing(4)
        centro.addWidget(etiqueta)
        centro.addWidget(self.barra)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.valor_a)
        layout.addLayout(centro, 1)
        layout.addWidget(self.valor_b)

    def set_valores(self, a, b):
        self.valor_a.setText(f"{a:g}")
        self.valor_b.setText(f"{b:g}")
        for etiqueta, gana in ((self.valor_a, a > b), (self.valor_b, b > a)):
            etiqueta.setProperty("gana", gana)
            etiqueta.style().unpolish(etiqueta)
            etiqueta.style().polish(etiqueta)
        self.barra.set_proporcion(a, b)


class FichaEquipo(QWidget):
    FILAS = (("clasificacion", "Clasificación"), ("carrera", "Carrera"),
             ("puntos", "Puntos"), ("victorias", "Victorias"), ("podios", "Podios"))

    def __init__(self):
        super().__init__()
        self.franja = QFrame()
        self.franja.setFixedWidth(6)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreFicha")
        self.meta = QLabel()
        self.meta.setObjectName("metaFicha")
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(self.nombre)
        textos.addWidget(self.meta)
        cabeza = QHBoxLayout()
        cabeza.setSpacing(12)
        cabeza.addWidget(self.franja)
        cabeza.addLayout(textos, 1)

        self.foto_a = FotoPiloto(72)
        self.foto_b = FotoPiloto(72)
        self.nombre_a = QLabel()
        self.nombre_a.setObjectName("nombreDuelo")
        self.nombre_b = QLabel()
        self.nombre_b.setObjectName("nombreDuelo")
        self.nombre_b.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        duelo = QHBoxLayout()
        duelo.setSpacing(10)
        duelo.addWidget(self.foto_a)
        duelo.addWidget(self.nombre_a, 1)
        duelo.addWidget(self.nombre_b, 1)
        duelo.addWidget(self.foto_b)

        self.titulo_duelo = QLabel()
        self.titulo_duelo.setObjectName("etiquetaRonda")
        self.filas = {clave: FilaCaraACara(texto) for clave, texto in self.FILAS}
        self.bloque_duelo = QWidget()
        columna = QVBoxLayout(self.bloque_duelo)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(10)
        columna.addLayout(duelo)
        columna.addWidget(self.titulo_duelo)
        for fila in self.filas.values():
            columna.addWidget(fila)

        self.sin_duelo = QLabel("Este equipo no tuvo dos pilotos en una misma carrera.")
        self.sin_duelo.setObjectName("estadoVacio")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(cabeza)
        layout.addWidget(self.bloque_duelo)
        layout.addWidget(self.sin_duelo)

    def mostrar(self, equipo, color, anio, h2h):
        color = color or MUTED
        self.franja.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        self.nombre.setText(equipo["nombre"])
        partes = [f"P{equipo['posicion']} en constructores"] if equipo["posicion"] else []
        partes.append(f"{_numero(equipo['puntos'] or 0)} puntos en {anio}")
        self.meta.setText("  ·  ".join(partes))

        self.bloque_duelo.setVisible(h2h is not None)
        self.sin_duelo.setVisible(h2h is None)
        if h2h is None:
            return
        for foto, nombre, piloto in ((self.foto_a, self.nombre_a, h2h["a"]),
                                     (self.foto_b, self.nombre_b, h2h["b"])):
            foto.set_piloto(piloto["driver_id"], sigla(piloto), None, color)
            nombre.setText(f"{piloto['nombre']} {piloto['apellido']}")
        self.titulo_duelo.setText(f"CARA A CARA {anio}  ·  QUIÉN TERMINÓ ADELANTE")
        for clave, fila in self.filas.items():
            fila.set_valores(*h2h[clave])
```

En `style.qss`, antes de `/* ---------- Estado (cargando / error) ---------- */`:

```css
/* ---------- Pilotos y equipos ----------
   Tarjetas y fichas de la pestaña Pilotos. Las cajas de stats reusan
   QFrame#kpi / QLabel#valorKpi de Clasificación. */
QFrame#tarjetaPiloto,
QFrame#tarjetaEquipo {
    background-color: #12161C;
    border: 1px solid #2D3541;
    border-radius: 4px;
}

QFrame#tarjetaPiloto:hover,
QFrame#tarjetaEquipo:hover {
    background-color: #1B2029;
    border-color: #52DEEC;
}

QFrame#tarjetaPiloto:focus,
QFrame#tarjetaEquipo:focus {
    border: 1px solid #E10600;
}

QLabel#siglaTarjeta {
    font-family: "Titillium Web";
    font-size: 17px;
    font-weight: 700;
}

QLabel#detalleTarjeta {
    color: #A4AEBC;
    font-size: 12px;
}

QLabel#puntosTarjeta {
    color: #52DEEC;
    font-size: 12px;
    font-weight: 600;
}

QLabel#nombreTarjeta {
    font-size: 14px;
    font-weight: 600;
}

QLabel#nombreFicha {
    font-family: "Titillium Web";
    font-size: 26px;
    font-weight: 700;
}

QLabel#metaFicha {
    color: #A4AEBC;
    font-size: 13px;
}

QFrame#celdaResultado {
    background-color: #12161C;
    border: 1px solid #2D3541;
    border-radius: 3px;
}

QFrame#celdaResultado[estado="podio"] {
    border-top: 2px solid #F3D27A;
}

QLabel#textoCelda {
    font-size: 13px;
    font-weight: 600;
}

QFrame#celdaResultado[estado="podio"] QLabel#textoCelda {
    color: #F3D27A;
}

QFrame#celdaResultado[estado="abandono"] QLabel#textoCelda {
    color: #FF6B57;
}

QFrame#celdaResultado[estado="ausente"] QLabel#textoCelda {
    color: #A4AEBC;
}

QLabel#deltaCelda {
    color: #A4AEBC;
    font-size: 11px;
}

QLabel#deltaCelda[sentido="sube"] {
    color: #52DEEC;
}

QLabel#nombreDuelo {
    font-size: 14px;
    font-weight: 600;
}

QLabel#valorDuelo {
    font-family: "Titillium Web";
    font-size: 19px;
    font-weight: 700;
    color: #A4AEBC;
}

QLabel#valorDuelo[gana="true"] {
    color: #F3F6F9;
}
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_ui.py -q`
Expected: todo PASS. Eso incluye `test_qss_no_tiene_reglas_muertas`, porque todos los nombres nuevos están como literales en `ui/fichas_pilotos.py`, y `test_contraste_de_la_paleta` con los dos pares nuevos.

- [ ] **Step 5: Commit**

```bash
git add ui/fichas_pilotos.py ui/icons.py style.qss test_ui.py
git commit -m "Tarjetas, fichas, tira de resultados y cara a cara de pilotos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Vista PilotosView (y `aplicar_estado` compartido)

**Files:**
- Create: `ui/estado.py`
- Create: `ui/pilotos_view.py`
- Modify: `ui/standings_view.py:128-137`, `ui/event_detail_view.py:592-603`, `ui/calendar_view.py` (`_set_estado`, línea ~307)
- Test: `test_ui.py`

**Interfaces:**
- Consumes: todo lo de las Tasks 2-6
- Produces:
  - `estado.aplicar_estado(etiqueta: QLabel, texto: str, tipo: str = "") -> None`
  - `pilotos_view.GRILLA_PILOTOS, FICHA_PILOTO, GRILLA_EQUIPOS, FICHA_EQUIPO` (0..3)
  - `PilotosView`, con `pedir_anio(year)`, `cargar_datos(year)`, `abrir_piloto(driver_id)`, `abrir_equipo(constructor_id)` y `volver_a_grilla() -> bool`
  - Atributos que leen los tests y `main.py`: `.estado`, `.stack_interno`, `.grilla_pilotos`, `.grilla_equipos`, `.ficha_piloto`, `.ficha_equipo`, `._workers_activos` y `._con`

- [ ] **Step 1: Escribir los tests que fallan**

En `test_ui.py`, agregar a los imports:

```python
import ui.pilotos_view as pilotos_view
from core import historial
```

Antes del `if __name__`:

```python
class _PilotosWorkerFalso(_WorkerFalso):
    """Emite pilotos y equipos de la base falsa. Con `pendientes` puesto,
    start() no emite: se guarda para emitir después (resultado tardío)."""
    con = None
    pendientes = None

    def start(self):
        if _PilotosWorkerFalso.pendientes is not None:
            _PilotosWorkerFalso.pendientes.append(self)
            return
        self.emitir()

    def emitir(self):
        _WorkerFalso.vista.sender = lambda: self
        datos = {"pilotos": historial.pilotos_temporada(self.con, self.year),
                 "equipos": historial.equipos_temporada(self.con, self.year)}
        for cb in self._terminado:
            cb(datos)
        for cb in self._finished:
            cb()


class _FotosWorkerFalso:
    def __init__(self, pilotos):
        self.pilotos = pilotos

    @property
    def foto_lista(self):
        return _WorkerFalso._Senal([])

    @property
    def finished(self):
        return _WorkerFalso._Senal([])

    def start(self):
        pass

    def requestInterruption(self):
        pass


_WORKERS_PILOTOS = (pilotos_view.PilotosWorker, pilotos_view.FotosWorker)


def _vista_pilotos():
    con = base_de_prueba()
    _PilotosWorkerFalso.con = con
    pilotos_view.PilotosWorker = _PilotosWorkerFalso
    pilotos_view.FotosWorker = _FotosWorkerFalso
    vista = pilotos_view.PilotosView()
    vista._con = con
    _WorkerFalso.vista = vista
    vista.resize(1000, 700)
    return vista


def _restaurar_pilotos():
    pilotos_view.PilotosWorker, pilotos_view.FotosWorker = _WORKERS_PILOTOS
    _PilotosWorkerFalso.pendientes = None
    _WorkerFalso.vista = None


def test_pilotos_muestra_una_tarjeta_por_piloto_y_por_equipo():
    vista = _vista_pilotos()
    try:
        vista.cargar_datos(2025)
        assert [t.clave for t in vista.grilla_pilotos.tarjetas()] == \
            ["norris", "piastri", "leclerc", "lawson"]
        assert [t.clave for t in vista.grilla_equipos.tarjetas()] == ["mclaren", "ferrari"]
        assert vista.estado.isHidden()
    finally:
        _restaurar_pilotos()


def test_fichas_de_piloto_y_de_equipo():
    vista = _vista_pilotos()
    try:
        vista.cargar_datos(2025)
        vista.abrir_piloto("norris")
        assert vista.stack_interno.currentIndex() == pilotos_view.FICHA_PILOTO
        assert len(vista.ficha_piloto.tira.celdas()) == 4
        assert vista.volver_a_grilla()
        assert vista.stack_interno.currentIndex() == pilotos_view.GRILLA_PILOTOS
        assert not vista.volver_a_grilla(), "desde la grilla, Esc le toca a MainWindow"

        vista.abrir_equipo("mclaren")
        assert vista.stack_interno.currentIndex() == pilotos_view.FICHA_EQUIPO
        assert vista.ficha_equipo.filas["carrera"].valor_a.text() == "2"
        assert vista.ficha_equipo.sin_duelo.isHidden()

        vista.abrir_equipo("ferrari")   # un solo piloto: sin cara a cara
        assert not vista.ficha_equipo.sin_duelo.isHidden()
        assert vista.ficha_equipo.bloque_duelo.isHidden()

        vista.cargar_datos(1990)        # sin siglas, equipos sin color
        vista.abrir_piloto("senna")
        vista.abrir_equipo("coloni")
    finally:
        _restaurar_pilotos()


def test_pilotos_de_otro_anio_que_llegan_tarde_se_descartan():
    vista = _vista_pilotos()
    try:
        pendientes = []
        _PilotosWorkerFalso.pendientes = pendientes
        vista.cargar_datos(2025)        # queda en vuelo
        _PilotosWorkerFalso.pendientes = None
        vista.cargar_datos(1990)        # llega enseguida
        pendientes[0].emitir()          # y recién ahora llega 2025
        assert [t.clave for t in vista.grilla_pilotos.tarjetas()] == ["senna", "prost", "nadie"]
    finally:
        _restaurar_pilotos()


def test_temporada_sin_resultados_muestra_estado_vacio():
    vista = _vista_pilotos()
    try:
        vista.cargar_datos(2026)
        assert vista.grilla_pilotos.tarjetas() == []
        assert vista.estado.objectName() == "estadoVacio"
        assert "2026" in vista.estado.text()
    finally:
        _restaurar_pilotos()


def test_un_error_de_red_se_reintenta_al_volver_a_la_pestania():
    vista = _vista_pilotos()
    try:
        vista.cargar_datos(2025)

        class _Worker2025:
            year = 2025

        vista.sender = lambda: _Worker2025()
        vista.on_error("sin red")
        assert vista.estado.objectName() == "estadoError"
        # Con year puesto, showEvent no vuelve a pedir el año que falló.
        assert vista.year is None
    finally:
        _restaurar_pilotos()
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_ui.py -q`
Expected: FAIL al importar (`ModuleNotFoundError: No module named 'ui.pilotos_view'`).

- [ ] **Step 3: Implementar**

Crear `ui/estado.py`:

```python
"""Etiqueta de estado (cargando / error / vacío) que comparten las vistas."""

_NOMBRES = {"": "estadoVacio", "cargando": "estadoCargando",
            "error": "estadoError", "vacio": "estadoVacio"}


def aplicar_estado(etiqueta, texto, tipo=""):
    """El objectName elige el estilo en style.qss; sin texto, se oculta."""
    etiqueta.setObjectName(_NOMBRES.get(tipo, "estadoVacio"))
    etiqueta.setText(texto)
    etiqueta.setVisible(bool(texto))
    etiqueta.style().unpolish(etiqueta)
    etiqueta.style().polish(etiqueta)
```

En `ui/standings_view.py`, `ui/event_detail_view.py` y `ui/calendar_view.py`, reemplazar el cuerpo entero de `_set_estado(self, texto, tipo="")`, incluido el comentario `ponytail:` de standings que pedía esta extracción, por:

```python
    def _set_estado(self, texto, tipo=""):
        aplicar_estado(self.estado, texto, tipo)
```

y sumar `from ui.estado import aplicar_estado` a los imports de cada uno. (Antes de reemplazar, leer el `_set_estado` de `calendar_view.py` y confirmar que hace lo mismo que los otros dos. Si hace algo más, como tocar el spinner, dejar esa línea extra después de la llamada.)

Crear `ui/pilotos_view.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget
)

from core import historial
from core.equipos import color_equipo
from ui.estado import aplicar_estado
from ui.fichas_pilotos import (
    FichaEquipo, FichaPiloto, FotoPiloto, GrillaTarjetas, TarjetaEquipo, TarjetaPiloto
)
from ui.spinner_widget import SpinnerWidget
from workers.pilotos_worker import FotosWorker, PilotosWorker

GRILLA_PILOTOS, FICHA_PILOTO, GRILLA_EQUIPOS, FICHA_EQUIPO = range(4)


class PilotosView(QWidget):
    """Pilotos y equipos de la temporada: grillas de tarjetas y sus fichas.

    Mismo esquema que StandingsView: el año se anota con pedir_anio y se carga
    recién cuando la vista se muestra. Las fichas leen la base local desde el
    hilo de la UI, porque son consultas de milisegundos.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.year = None
        self._year_pedido = None
        self._cache_por_anio = {}   # {year: datos}; los errores no: la red puede volver
        self._datos = None
        self._fotos = {}            # {driver_id: ruta}; la foto no depende del año
        self._con = None            # conexión de la UI, se abre con la primera ficha
        self._workers_activos = []  # referencias vivas mientras corren
        self._worker_fotos = None

        # --- Encabezado: título + solapas Pilotos/Equipos ---
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("etiquetaRonda")
        titulo = QLabel("Pilotos")
        titulo.setObjectName("titulo")
        columna_titulo = QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(self.eyebrow)
        columna_titulo.addWidget(titulo)

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_pilotos.setObjectName("tabHorizontalIzq")
        self.boton_equipos = QPushButton("Equipos")
        self.boton_equipos.setObjectName("tabHorizontalDer")
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setCheckable(True)
            boton.setMinimumHeight(34)
            boton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            boton.setCursor(Qt.PointingHandCursor)
        self.boton_pilotos.setChecked(True)

        encabezado = QHBoxLayout()
        encabezado.setSpacing(0)
        encabezado.addLayout(columna_titulo)
        encabezado.addStretch()
        encabezado.addWidget(self.boton_pilotos, alignment=Qt.AlignBottom)
        encabezado.addWidget(self.boton_equipos, alignment=Qt.AlignBottom)

        self.spinner = SpinnerWidget(tamano=18)
        self.spinner.hide()
        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")
        fila_estado = QHBoxLayout()
        fila_estado.setContentsMargins(0, 0, 0, 0)
        fila_estado.addWidget(self.spinner)
        fila_estado.addWidget(self.estado)
        fila_estado.addStretch()

        self.grilla_pilotos = GrillaTarjetas()
        self.grilla_equipos = GrillaTarjetas()
        self.ficha_piloto = FichaPiloto()
        self.ficha_equipo = FichaEquipo()
        self.stack_interno = QStackedWidget()
        self.stack_interno.addWidget(self.grilla_pilotos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_piloto, "Pilotos", GRILLA_PILOTOS))
        self.stack_interno.addWidget(self.grilla_equipos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_equipo, "Equipos", GRILLA_EQUIPOS))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(12)
        layout.addLayout(encabezado)
        layout.addLayout(fila_estado)
        layout.addWidget(self.stack_interno, 1)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(GRILLA_PILOTOS))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(GRILLA_EQUIPOS))

    def _pagina_ficha(self, ficha, volver_a, indice_grilla):
        miga = QPushButton(f"← {volver_a}")
        miga.setObjectName("migaVolver")
        miga.setCursor(Qt.PointingHandCursor)
        miga.clicked.connect(lambda: self.stack_interno.setCurrentIndex(indice_grilla))
        contenido = QWidget()
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 8, 16)
        columna.setSpacing(12)
        columna.addWidget(miga, alignment=Qt.AlignLeft)
        columna.addWidget(ficha)
        columna.addStretch()
        scroll = QScrollArea()
        scroll.setWidget(contenido)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == GRILLA_PILOTOS)
        self.boton_equipos.setChecked(indice == GRILLA_EQUIPOS)
        self.stack_interno.setCurrentIndex(indice)

    def volver_a_grilla(self):
        """Esc desde una ficha vuelve a su grilla. False si ya estaba en una."""
        actual = self.stack_interno.currentIndex()
        if actual == FICHA_PILOTO:
            self.stack_interno.setCurrentIndex(GRILLA_PILOTOS)
            return True
        if actual == FICHA_EQUIPO:
            self.stack_interno.setCurrentIndex(GRILLA_EQUIPOS)
            return True
        return False

    def _set_estado(self, texto, tipo=""):
        aplicar_estado(self.estado, texto, tipo)
        if tipo == "cargando":
            self.spinner.iniciar()
        else:
            self.spinner.detener()

    # --- Carga por año ---

    def pedir_anio(self, year):
        """Anota el año sin pedir nada a la red. La carga real ocurre en
        showEvent, cuando esta vista es la que se está mirando."""
        self._year_pedido = year
        if self.isVisible():
            self.cargar_datos(year)

    def showEvent(self, event):
        super().showEvent(event)
        if self._year_pedido is not None and self._year_pedido != self.year:
            self.cargar_datos(self._year_pedido)

    def cargar_datos(self, year):
        self.year = year
        self.eyebrow.setText(f"TEMPORADA {year}")
        self._cambiar_tab(GRILLA_EQUIPOS if self.boton_equipos.isChecked() else GRILLA_PILOTOS)

        if year in self._cache_por_anio:
            self._mostrar(self._cache_por_anio[year])
            return

        self._set_estado(f"Cargando pilotos {year}...", "cargando")
        self._datos = None
        self.grilla_pilotos.set_tarjetas([])
        self.grilla_equipos.set_tarjetas([])

        worker = PilotosWorker(year)
        worker.terminado.connect(self.on_datos_cargados)
        worker.error.connect(self.on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def on_datos_cargados(self, datos):
        worker = self.sender()
        self._cache_por_anio[worker.year] = datos
        if worker.year != self.year:
            return   # llegó tarde: el usuario ya cambió de año
        self._mostrar(datos)

    def on_error(self, mensaje):
        worker = self.sender()
        if worker.year != self.year:
            return
        self._set_estado(f"No se pudieron cargar los pilotos de {self.year}. "
                         "Revisá la conexión y volvé a abrir la pestaña.", "error")
        self.year = None   # así showEvent lo vuelve a pedir

    def _mostrar(self, datos):
        self._datos = datos
        if datos["pilotos"]:
            self._set_estado("")
        else:
            self._set_estado(f"Todavía no hay resultados de {self.year}.", "vacio")

        tarjetas = []
        for piloto in datos["pilotos"]:
            tarjeta = TarjetaPiloto(piloto, color_equipo(piloto["constructor_id"]))
            tarjeta.clicked.connect(self.abrir_piloto)
            self._poner_foto(tarjeta.foto)
            tarjetas.append(tarjeta)
        self.grilla_pilotos.set_tarjetas(tarjetas)

        tarjetas = []
        for equipo in datos["equipos"]:
            tarjeta = TarjetaEquipo(equipo, color_equipo(equipo["constructor_id"]))
            tarjeta.clicked.connect(self.abrir_equipo)
            tarjetas.append(tarjeta)
        self.grilla_equipos.set_tarjetas(tarjetas)

        self._pedir_fotos(datos["pilotos"])

    # --- Fotos ---

    def _poner_foto(self, foto):
        ruta = self._fotos.get(foto.driver_id)
        if ruta:
            foto.set_foto(ruta)

    def _pedir_fotos(self, pilotos):
        if self._worker_fotos is not None:
            self._worker_fotos.requestInterruption()   # las del año anterior ya no hacen falta
            self._worker_fotos = None
        faltan = [p for p in pilotos if p["driver_id"] not in self._fotos]
        if not faltan:
            return
        worker = FotosWorker(faltan)
        worker.foto_lista.connect(self._on_foto_lista)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        self._worker_fotos = worker
        worker.start()

    def _on_foto_lista(self, driver_id, ruta):
        self._fotos[driver_id] = ruta
        for foto in self.findChildren(FotoPiloto):
            if foto.driver_id == driver_id:
                foto.set_foto(ruta)

    # --- Fichas ---

    def _conexion(self):
        if self._con is None:
            self._con = historial.abrir_base()
        return self._con

    def abrir_piloto(self, driver_id):
        piloto = next(p for p in self._datos["pilotos"] if p["driver_id"] == driver_id)
        con = self._conexion()
        self.ficha_piloto.mostrar(
            piloto, color_equipo(piloto["constructor_id"]), self.year,
            historial.stats_temporada(con, self.year, driver_id),
            historial.tira_resultados(con, self.year, driver_id),
            historial.carrera_completa(con, driver_id))
        self._poner_foto(self.ficha_piloto.foto)
        self.stack_interno.setCurrentIndex(FICHA_PILOTO)

    def abrir_equipo(self, constructor_id):
        equipo = next(e for e in self._datos["equipos"] if e["constructor_id"] == constructor_id)
        duelo = historial.cara_a_cara(self._conexion(), self.year, constructor_id)
        self.ficha_equipo.mostrar(equipo, color_equipo(constructor_id), self.year, duelo)
        self._poner_foto(self.ficha_equipo.foto_a)
        self._poner_foto(self.ficha_equipo.foto_b)
        self.stack_interno.setCurrentIndex(FICHA_EQUIPO)
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python -m pytest test_ui.py test_historial.py -q`
Expected: todo PASS (también los tests viejos de calendario y detalle, que siguen usando `_set_estado`).

- [ ] **Step 5: Commit**

```bash
git add ui/estado.py ui/pilotos_view.py ui/standings_view.py ui/event_detail_view.py ui/calendar_view.py test_ui.py
git commit -m "Vista Pilotos: grillas, fichas y carga por año; estado compartido

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Integración en la sidebar y la ventana

**Files:**
- Create: `assets/icons/users.svg` (local: `assets/` está fuera de git)
- Modify: `ui/sidebar.py:67-69` y `:84-85`
- Modify: `main.py` (imports, `__init__`, `on_navegar_sidebar`, `on_anio_cambiado`, `keyPressEvent`, `closeEvent`)
- Test: `test_ui.py`

**Interfaces:**
- Consumes: `PilotosView` y `volver_a_grilla()` (Task 7)
- Produces: `Sidebar.boton_pilotos` y la emisión `navegar("pilotos")`

- [ ] **Step 1: Escribir el test que falla**

```python
def test_la_sidebar_lleva_a_pilotos():
    from ui.sidebar import Sidebar
    sidebar = Sidebar()
    destinos = []
    sidebar.navegar.connect(destinos.append)
    sidebar.boton_pilotos.click()
    assert destinos == ["pilotos"]
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python -m pytest test_ui.py -q -k sidebar`
Expected: FAIL con `AttributeError: 'Sidebar' object has no attribute 'boton_pilotos'`.

- [ ] **Step 3: Implementar**

Crear `assets/icons/users.svg` (Lucide "users", ISC):

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
```

En `ui/sidebar.py`, después de crear `self.boton_standings`:

```python
        self.boton_pilotos = self._agregar_nav(
            layout, "Pilotos", "users", "Pilotos y equipos de la temporada")
```

y junto a las otras conexiones:

```python
        self.boton_pilotos.clicked.connect(lambda: self.navegar.emit("pilotos"))
```

En `main.py`:

```python
from ui.pilotos_view import PilotosView
```

En `__init__`, después de `self.standings_view = StandingsView()`:

```python
        self.pilotos_view = PilotosView()
```

y después de `self.stack.addWidget(self.standings_view)   # índice 2`:

```python
        self.stack.addWidget(self.pilotos_view)     # índice 3
```

En `on_navegar_sidebar`, agregar:

```python
        elif destino == "pilotos":
            self._mostrar_vista(3)
```

En `on_anio_cambiado`, al final:

```python
        self.pilotos_view.pedir_anio(year)
```

En `keyPressEvent`, antes del `if tecla == Qt.Key_Escape and ...` que ya existe:

```python
        # Esc dentro de una ficha de piloto o equipo vuelve a su grilla; desde
        # la grilla, al calendario como en el resto de las vistas.
        if (tecla == Qt.Key_Escape and self.stack.currentWidget() is self.pilotos_view
                and self.pilotos_view.volver_a_grilla()):
            return
```

En `closeEvent`, reemplazar el bucle por:

```python
        for vista in (self.calendar_view, self.detail_view, self.standings_view,
                      self.pilotos_view):
            for worker in list(getattr(vista, '_workers_activos', [])):
                worker.requestInterruption()   # FotosWorker corta entre foto y foto
                worker.wait(self.TIMEOUT_CIERRE_MS)
```

- [ ] **Step 4: Correr tests y la app**

Run: `python -m pytest test_ui.py test_historial.py -q`
Expected: todo PASS.

Run: `python main.py`, ir a "Pilotos" en la sidebar.
Expected: con la base vacía, baja la temporada actual (spinner amarillo y después tarjetas). Esc en una ficha vuelve a la grilla, y Esc en la grilla vuelve al calendario.

- [ ] **Step 5: Commit**

```bash
git add ui/sidebar.py main.py test_ui.py
git commit -m "Sidebar y ventana: pestaña Pilotos en el índice 3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(`assets/icons/users.svg` no se commitea porque `assets/` está en `.gitignore`.)

---

### Task 9: Script de precarga y build

**Files:**
- Create: `precache_historial.py` (local, como `precache.py`)
- Modify: `.gitignore`, `F1CalendarApp.spec` (local)

**Interfaces:**
- Consumes: `historial.abrir_base`, `temporada_guardada`, `descargar_temporada`, `pedir_json`, `completar_headshots`, `pilotos_temporada`; `fotos.obtener_ruta_foto`

- [ ] **Step 1: Crear `precache_historial.py`**

```python
"""Llena cache_historial/historial_f1.db con todo el historial de F1 (Ergast
vía Jolpica) para empaquetarlo en el build, y baja las fotos de la grilla actual.

Se puede cortar y volver a correr: saltea las temporadas que ya están (salvo
la actual, que siempre se refresca). Jolpica permite 500 consultas por hora,
así que la primera vez tarda entre 1 y 1,5 h.
"""
import logging
import time
from datetime import datetime

import fastf1

from core import historial
from core.fotos import obtener_ruta_foto

PAUSA_S = 7.5   # 480 consultas por hora: debajo del límite de 500 de Jolpica

fastf1.Cache.enable_cache('cache')
fastf1.set_log_level(logging.ERROR)
anio_actual = datetime.now().year
con = historial.abrir_base()


def pedir_lento(ruta, offset=0):
    time.sleep(PAUSA_S)
    return historial.pedir_json(ruta, offset, reintentos=5)


print("=== Historial ===")
for anio in range(1950, anio_actual + 1):
    if anio < anio_actual and historial.temporada_guardada(con, anio):
        continue
    try:
        historial.descargar_temporada(con, anio, pedir=pedir_lento)
        print(f"{anio}: OK")
    except Exception as e:
        print(f"{anio}: ERROR - {e}")

print("\n=== Fotos oficiales (2018 en adelante) ===")
for anio in range(2018, anio_actual + 1):
    try:
        historial.completar_headshots(con, anio)
        print(f"{anio}: OK")
    except Exception as e:
        print(f"{anio}: ERROR - {e}")

print("\n=== Fotos de la grilla actual ===")
for piloto in historial.pilotos_temporada(con, anio_actual):
    ruta = obtener_ruta_foto(piloto["driver_id"], piloto["headshot_url"], piloto["url_wiki"])
    print(f"{piloto['driver_id']}: {'OK' if ruta else 'sin foto'}")
con.close()
```

- [ ] **Step 2: Prueba corta**

Para probar sin esperar una hora, correr temporalmente sólo tres temporadas: cambiar el `range(1950, ...)` por `(1955, 1988, anio_actual)`, ejecutar `python precache_historial.py` y después volver el `range` a como estaba.
Expected: `1955: OK`, `1988: OK` y `<año actual>: OK`; `OK` en headshots del año actual; fotos de la grilla actual en `cache_fotos/`.

- [ ] **Step 3: Build**

En `.gitignore`, junto a los otros `cache_*`:

```
cache_historial/
cache_fotos/
precache_historial.py
```

En `F1CalendarApp.spec`, línea `datas=`:

```python
datas=[('style.qss', '.'), ('assets', 'assets'), ('cache_flags', 'cache_flags'), ('cache_tracks', 'cache_tracks'), ('cache_historial', 'cache_historial'), ('cache_fotos', 'cache_fotos')],
```

- [ ] **Step 4: Verificación manual de punta a punta**

Con la base de la prueba corta (1955, 1988 y el año actual), correr `python main.py` y revisar:

- **Año actual:** tarjetas con fotos oficiales. La ficha muestra la tira con los deltas ▲/▼, y la ficha de McLaren el cara a cara.
- **1988:** Prost y Senna con foto de Wikipedia, siglas armadas con el apellido y equipos sin franja de color. Las poles salen de la largada.
- **1955:** placeholders donde no haya foto. La solapa Equipos muestra puntos sin posición.
- **Cambio rápido de año:** apretar ← → varias veces seguidas con la pestaña abierta y confirmar que la grilla termina mostrando el año que dice el selector.
- **Sin red** (cortar el Wi-Fi):
  - 1988 se ve igual;
  - un año no guardado (por ejemplo 1975) muestra el error;
  - con la red de vuelta, cambiar de vista y volver a Pilotos lo carga.
- Cerrar la app con fotos bajando: no tiene que aparecer "QThread: Destroyed while thread is still running".

- [ ] **Step 5: Correr todos los tests y dejar el árbol limpio**

Run: `python -m pytest -q` y `python test_ui.py` y `python test_historial.py`
Expected: todo PASS, y `ok` impreso por los dos scripts.

```bash
git add .gitignore
git commit -m "Ignorar la base de historial y las fotos generadas localmente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
