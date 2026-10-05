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
