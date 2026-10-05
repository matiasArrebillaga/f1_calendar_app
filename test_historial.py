"""Chequeos de core/historial.py y core/fotos.py, sin red.

La base se arma pasando respuestas falsas de Jolpica por descargar_temporada,
así cada test prueba también el parseo. Corre con `pytest test_historial.py`
y con `python test_historial.py`.
"""
import os
import sqlite3
import sys
import tempfile

from core import calendario, fotos, historial, paths

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
    """"2025/results" (temporada) o "2025/3/results" (una ronda)."""
    partes = ruta.split("/")
    anio, recurso = int(partes[0]), partes[-1]
    ronda = int(partes[1]) if len(partes) == 3 else None

    def de_la_ronda(filas):
        return [f for f in filas if ronda is None or f[0] == ronda]

    if recurso == "results":
        filas = [(r, gp, {"number": num, "positionText": pt, "points": str(pts),
                          "grid": str(grid), "status": st, "Driver": d, "Constructor": c})
                 for r, gp, d, c, num, grid, pt, pts, st in RESULTADOS.get(anio, [])]
        return _pagina_carreras(anio, de_la_ronda(filas), offset, "Results")
    if recurso == "qualifying":
        filas = [(r, gp, {"position": str(pos), "Driver": d, "Constructor": c})
                 for r, gp, d, c, pos in CLASIFICACION.get(anio, [])]
        return _pagina_carreras(anio, de_la_ronda(filas), offset, "QualifyingResults")
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
    assert duelo["poles"] == (1, 1)
    assert [(c["ronda"], c["gp"], c["pais"], c["adelante"]) for c in duelo["por_carrera"]] == [
        (1, "Australian Grand Prix", "Australia", 0), (2, "Chinese Grand Prix", "China", 1),
        (3, "Japanese Grand Prix", "Japan", None), (4, "Bahrain Grand Prix", "Bahrain", 0)]
    assert duelo["por_carrera"][2]["a"]["posicion_texto"] == "R"


def test_stats_equipo():
    con = base_de_prueba()
    # R1 Norris-Piastri 1-2; R2 ganó Piastri con Norris tercero.
    assert historial.stats_equipo(con, 2025, "mclaren") == {"victorias": 2, "dobletes": 1}
    assert historial.stats_equipo(con, 2025, "no_existe") == {"victorias": 0, "dobletes": 0}


def test_cara_a_cara_sin_companero_es_none():
    con = base_de_prueba()
    assert historial.cara_a_cara(con, 2025, "ferrari") is None
    assert historial.cara_a_cara(con, 2025, "no_existe") is None


def test_cara_a_cara_antes_de_1994_compara_la_largada():
    duelo = historial.cara_a_cara(base_de_prueba(), 1988, "mclaren")
    assert (duelo["a"]["driver_id"], duelo["clasificacion"], duelo["carrera"]) == \
        ("senna", (1, 0), (1, 0))


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


def test_jpg_de_wikipedia_viejo_no_tapa_la_oficial():
    carpeta, originales = _fotos_en_carpeta_temporal()
    _archivo_vacio(os.path.join(carpeta, "norris.jpg"))
    _archivo_vacio(os.path.join(carpeta, "piastri.jpg"))

    def bajar(url, destino):
        if url == "https://f1/piastri.png":
            raise OSError("404")
        _archivo_vacio(destino)

    def wikipedia(url_wiki):
        raise AssertionError("ya había JPG: no hacía falta volver a Wikipedia")

    fotos._bajar, fotos._url_wikipedia = bajar, wikipedia
    try:
        assert fotos.obtener_ruta_foto("norris", "https://f1/norris.png", "http://w/N") ==             os.path.join(carpeta, "norris.png")
        assert fotos.obtener_ruta_foto("piastri", "https://f1/piastri.png", "http://w/P") ==             os.path.join(carpeta, "piastri.jpg")
    finally:
        _restaurar_fotos(originales)


def test_logo_oficial_se_baja_una_vez_y_sin_logo_es_none():
    carpeta, originales = _fotos_en_carpeta_temporal()
    bajadas = []

    def bajar(url, destino):
        bajadas.append(url)
        _archivo_vacio(destino)

    fotos._bajar = bajar
    try:
        ruta = fotos.obtener_ruta_logo("red_bull")
        assert ruta == os.path.join(carpeta, "red_bull.png")
        assert fotos.obtener_ruta_logo("red_bull") == ruta
        assert len(bajadas) == 1 and "red-bull-racing-logo" in bajadas[0]
        assert fotos.obtener_ruta_logo("coloni") is None   # equipo sin logo oficial
    finally:
        _restaurar_fotos(originales)


def test_cara_a_cara_con_un_piloto_que_cambio_de_equipo_cuenta_solo_sus_puntos_ahi():
    """Como Tsunoda y Lawson en 2025: el total del campeonato incluye lo que
    sumaron con el otro equipo, que no es parte de este duelo."""
    con = base_de_prueba()
    # Piastri corre la R4 para Ferrari y suma 8: llega a 51 en el campeonato,
    # pero con McLaren hizo 43.
    con.execute("""UPDATE resultados SET constructor_id = 'ferrari', posicion = 5,
                   posicion_texto = '5', puntos = 8
                   WHERE temporada = 2025 AND ronda = 4 AND driver_id = 'piastri'""")
    con.execute("""UPDATE campeonato_pilotos SET puntos = 51
                   WHERE temporada = 2025 AND driver_id = 'piastri'""")
    duelo = historial.cara_a_cara(con, 2025, "mclaren")
    assert (duelo["a"]["driver_id"], duelo["puntos"]) == ("norris", (50, 43)), duelo["puntos"]


def test_la_temporada_en_curso_no_suma_titulo():
    """Antonelli lideraba 2026 a mitad de año y la ficha le daba un título."""
    con = base_de_prueba()
    assert historial.carrera_completa(con, "norris")["titulos"] == 1
    con.execute("UPDATE temporadas SET actualizada = '2025-06-01' WHERE temporada = 2025")
    assert historial.carrera_completa(con, "norris")["titulos"] == 0


def test_la_clasificacion_trae_victorias_y_todos_los_equipos_del_piloto():
    con = base_de_prueba()
    # Piastri corre la R4 para Ferrari: la tabla lo muestra con los dos equipos.
    con.execute("""UPDATE resultados SET constructor_id = 'ferrari'
                   WHERE temporada = 2025 AND ronda = 4 AND driver_id = 'piastri'""")
    pilotos = {p["driver_id"]: p for p in historial.pilotos_temporada(con, 2025)}
    assert pilotos["piastri"]["equipos"] == ["McLaren", "Ferrari"]
    assert (pilotos["norris"]["equipos"], pilotos["norris"]["victorias"]) == (["McLaren"], 1)
    assert [(e["constructor_id"], e["victorias"])
            for e in historial.equipos_temporada(con, 2025)] == [("mclaren", 2), ("ferrari", 1)]
    assert [(e["constructor_id"], e["victorias"])
            for e in historial.equipos_temporada(con, 1988)] == [("mclaren", 1)]
    assert historial.ultima_ronda(con, 2025) == 4
    assert historial.ultima_ronda(con, 2026) is None


def test_en_el_exe_los_datos_van_a_localappdata():
    """Al lado del .exe puede no haber permiso de escritura (Program Files)."""
    originales = getattr(sys, "frozen", None), os.environ.get("LOCALAPPDATA")
    sys.frozen, os.environ["LOCALAPPDATA"] = True, r"C:\local"
    try:
        assert paths.data_path("cache") == os.path.join(r"C:\local", "F1CalendarApp", "cache")
    finally:
        if originales[0] is None:
            del sys.frozen
        if originales[1] is None:   # en el CI (Linux) no existe
            del os.environ["LOCALAPPDATA"]
        else:
            os.environ["LOCALAPPDATA"] = originales[1]


def test_con_desde_baja_solo_las_rondas_nuevas_y_los_campeonatos():
    con = base_de_prueba()
    # Como si se hubiera guardado después de la R2: faltan la 3 y la 4.
    for tabla in ("carreras", "resultados", "clasificacion"):
        con.execute(f"DELETE FROM {tabla} WHERE temporada = 2025 AND ronda > 2")
    con.execute("UPDATE campeonato_pilotos SET puntos = 0 WHERE temporada = 2025")
    pedidas = []

    def pedir_anotando(ruta, offset=0):
        pedidas.append(ruta)
        return pedir_falso(ruta, offset)

    historial.descargar_temporada(con, 2025, pedir=pedir_anotando, desde=3)
    assert pedidas == ["2025/3/results", "2025/3/qualifying", "2025/4/results",
                       "2025/4/qualifying", "2025/5/results",
                       "2025/driverStandings", "2025/constructorStandings"], pedidas
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025") == 13
    assert _contar(con, "SELECT COUNT(*) FROM carreras WHERE temporada = 2025") == 4
    assert _contar(con, "SELECT puntos FROM campeonato_pilotos WHERE driver_id = 'norris'") == 50
    # Las otras temporadas no se tocan.
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 1988") > 0


def test_con_desde_y_sin_rondas_nuevas_solo_baja_los_campeonatos():
    con = base_de_prueba()
    pedidas = []

    def pedir_anotando(ruta, offset=0):
        pedidas.append(ruta)
        return pedir_falso(ruta, offset)

    historial.descargar_temporada(con, 2025, pedir=pedir_anotando, desde=5)
    assert pedidas == ["2025/5/results", "2025/driverStandings",
                       "2025/constructorStandings"], pedidas
    assert _contar(con, "SELECT COUNT(*) FROM resultados WHERE temporada = 2025") == 13


def test_los_calendarios_de_anios_terminados_se_guardan_y_no_se_vuelven_a_pedir():
    import fastf1
    import pandas as pd
    carpeta = tempfile.mkdtemp()
    pedidos = []

    def get_event_schedule(anio, include_testing):
        pedidos.append((anio, include_testing))
        return pd.DataFrame({"RoundNumber": [1, 2]})

    originales = (calendario.ruta_cache, calendario.data_path, fastf1.get_event_schedule)
    calendario.data_path = lambda nombre: os.path.join(carpeta, nombre)
    calendario.ruta_cache = lambda nombre, archivo: (os.path.join(carpeta, nombre, archivo), True)
    fastf1.get_event_schedule = get_event_schedule
    try:
        actual = calendario.anio_actual()
        for _ in range(2):
            assert list(calendario.obtener_calendario(2010)["RoundNumber"]) == [1, 2]
            calendario.obtener_calendario(actual)
    finally:
        calendario.ruta_cache, calendario.data_path, fastf1.get_event_schedule = originales
    # 2010 se pidió una sola vez; el año en curso puede cambiar y se pide siempre.
    assert pedidos == [(2010, False), (actual, False), (actual, False)], pedidos


def _pagina_ganadores(carreras, offset):
    pagina = carreras[offset:offset + LIMITE]
    return {"limit": str(LIMITE), "offset": str(offset), "total": str(len(carreras)),
            "RaceTable": {"Races": pagina}}


def test_ganadores_del_circuito_ordenados_y_guardados():
    def carrera(anio, ronda, *pilotos):
        return {"season": str(anio), "round": str(ronda), "raceName": "Bahrain Grand Prix",
                "Results": [{"Driver": p, "Constructor": {"name": "McLaren"}} for p in pilotos]}
    VER = _piloto("max_verstappen", "Max", "Verstappen")
    carreras = [carrera(2004 + i, 1, NOR if i % 2 else VER) for i in range(7)]
    carreras.append(carrera(2020, 16, NOR, VER))   # dos ganadores: victoria compartida
    pedidos = []

    def pedir(ruta, offset=0):
        pedidos.append((ruta, offset))
        return _pagina_ganadores(carreras, offset)

    carpeta = tempfile.mkdtemp()
    original = historial.data_path
    historial.data_path = lambda nombre: os.path.join(carpeta, nombre)
    try:
        ganadores = historial.ganadores_circuito("bahrain", pedir)
        assert [(g["anio"], g["piloto"]) for g in ganadores[:3]] ==             [(2020, "Lando Norris"), (2020, "Max Verstappen"), (2010, "Max Verstappen")], ganadores
        assert len(ganadores) == 9
        assert historial.mas_victorias(ganadores) == ("Max Verstappen", 5)
        # La segunda vez sale del JSON guardado, sin pedir nada.
        cantidad = len(pedidos)
        assert historial.ganadores_circuito("bahrain", pedir) == ganadores
        assert len(pedidos) == cantidad
    finally:
        historial.data_path = original
    assert pedidos[0][0] == "circuits/bahrain/results/1"


if __name__ == "__main__":
    for nombre, prueba in list(globals().items()):
        if nombre.startswith("test_"):
            prueba()
    print("ok")
