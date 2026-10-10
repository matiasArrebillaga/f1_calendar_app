"""Chequeos de exportar_web.py, sin red. Reusa la base falsa de
test_historial.py (1988, 1990 y 2025, todas terminadas)."""
import json
import os
import tempfile

import exportar_web
from core import historial
from test_historial import NOR, _pagina_ganadores, _piloto, base_de_prueba


def test_temporada_trae_fichas_de_pilotos_y_equipos():
    datos = exportar_web.temporada(base_de_prueba(), 2025)
    assert datos["anio"] == 2025 and datos["ronda"] == 4
    norris = datos["pilotos"][0]
    assert norris["driver_id"] == "norris"
    assert norris["stats"]["victorias"] == 1
    assert [f["ronda"] for f in norris["tira"]] == [1, 2, 3, 4]
    mclaren = next(e for e in datos["equipos"] if e["constructor_id"] == "mclaren")
    assert mclaren["stats"]["victorias"] == 2
    assert mclaren["cara_a_cara"]["por_carrera"]
    json.dumps(datos)   # tiene que poder escribirse tal cual


def test_carreras_previas_no_cuenta_la_temporada_en_curso():
    con = base_de_prueba()
    # 2025 guardada a mitad de año: todavía no terminó.
    con.execute("UPDATE temporadas SET actualizada = '2025-06-01' WHERE temporada = 2025")
    con.commit()   # el backup de carreras_previas copia lo confirmado
    previas = exportar_web.carreras_previas(con)
    assert "norris" not in previas          # sólo corrió en 2025
    assert previas["senna"]["titulos"] == 2
    assert previas["senna"]["victorias"] == 2
    # La base original no se toca: el recorte se hace sobre una copia.
    assert con.execute("SELECT COUNT(*) FROM resultados WHERE temporada = 2025").fetchone()[0] > 0


def test_temporadas_terminadas():
    con = base_de_prueba()
    con.execute("UPDATE temporadas SET actualizada = '2025-06-01' WHERE temporada = 2025")
    con.commit()
    assert exportar_web.temporadas_terminadas(con) == [1988, 1990]


def test_indice_del_buscador_lleva_a_la_ultima_temporada_terminada():
    con = base_de_prueba()
    datos = exportar_web.indice(con, [1988, 1990])   # 2025 todavía en curso
    pilotos = {p["id"]: p for p in datos["pilotos"]}
    assert pilotos["senna"] == {"id": "senna", "nombre": "Ayrton Senna", "anio": 1990}
    assert "norris" not in pilotos          # sólo corrió en 2025
    assert {e["id"] for e in datos["equipos"]} >= {"mclaren"}
    victorias = [con.execute("SELECT COUNT(*) FROM resultados WHERE driver_id = ? AND posicion = 1 "
                             "AND temporada IN (1988, 1990)", (p["id"],)).fetchone()[0] for p in datos["pilotos"]]
    assert victorias == sorted(victorias, reverse=True)   # los que más ganaron primero
    json.dumps(datos)


def test_datos_comunes_salen_de_core_y_marcan_los_mapas():
    carpeta = tempfile.mkdtemp()
    open(os.path.join(carpeta, "monza.png"), "wb").close()
    original = exportar_web.MAPAS
    exportar_web.MAPAS = carpeta
    try:
        comun = exportar_web.datos_comunes(2026)
    finally:
        exportar_web.MAPAS = original
    assert comun["anio_actual"] == 2026
    assert comun["banderas"]["UK"] == "gb"
    assert comun["eventos"]["Monaco Grand Prix"] == "Gran Premio de Mónaco"
    assert comun["logos"]["mclaren"].startswith("https://")
    assert comun["logos"]["audi"].endswith("/2026/audi/2026audilogowhite.webp")
    assert comun["autos"]["cadillac"].endswith("/2026/cadillac/2026cadillaccarright.webp")
    assert comun["circuitos"]["monza"]["mapa"] is True
    assert comun["circuitos"]["baku"]["mapa"] is False
    assert comun["circuitos"]["baku"]["vueltas"] == 51


def test_ganadores_sigue_aunque_falle_un_circuito():
    VER = _piloto("max_verstappen", "Max", "Verstappen")
    carreras = [{"season": "2025", "round": "1", "raceName": "X Grand Prix",
                 "Results": [{"Driver": NOR, "Constructor": {"name": "McLaren"}}]},
                {"season": "2024", "round": "1", "raceName": "X Grand Prix",
                 "Results": [{"Driver": VER, "Constructor": {"name": "Red Bull"}}]}]

    def pedir(ruta, offset=0):
        if ruta == "circuits/monza/results/1":
            raise OSError("sin red")
        return _pagina_ganadores(carreras, offset)

    carpeta = tempfile.mkdtemp()
    original = historial.data_path
    historial.data_path = lambda nombre: os.path.join(carpeta, nombre)
    try:
        ganadores = exportar_web.ganadores(pedir)
    finally:
        historial.data_path = original
    assert "monza" not in ganadores
    assert [g["piloto"] for g in ganadores["baku"]["lista"]] == ["Lando Norris", "Max Verstappen"]
    assert ganadores["baku"]["mas"] == ["Lando Norris, Max Verstappen", 1]


def test_copiar_mapas_los_renombra_por_circuit_id():
    origen, destino = tempfile.mkdtemp(), tempfile.mkdtemp()
    for nombre in ("monza.png", "marina_bay.png"):
        open(os.path.join(origen, nombre), "wb").close()
    original = exportar_web.MAPAS
    exportar_web.MAPAS = destino
    try:
        assert exportar_web.copiar_mapas(origen) == 2
    finally:
        exportar_web.MAPAS = original
    assert sorted(os.listdir(destino)) == ["marina_bay.png", "monza.png"]


def test_el_deploy_reintenta_los_429_de_jolpica():
    """El deploy arranca sin caché y hace ~50 pedidos seguidos: sin reintentos,
    un 429 tiraba abajo el deploy o dejaba un circuito sin ganadores."""
    llamadas = []

    def pedir_falso(ruta, offset=0, reintentos=1):
        llamadas.append((ruta, reintentos))
        return {"limit": "100", "offset": str(offset), "total": "0",
                "RaceTable": {"Races": []}, "StandingsTable": {"StandingsLists": []}}

    carpeta = tempfile.mkdtemp()
    originales = historial.pedir_json, historial.data_path, exportar_web.DATOS
    historial.pedir_json = pedir_falso
    historial.data_path = lambda nombre: os.path.join(carpeta, nombre)
    exportar_web.DATOS = carpeta
    # 2025 ya exportada: si no, el deploy la agregaría (el test de abajo).
    os.makedirs(os.path.join(carpeta, "temporadas"))
    open(os.path.join(carpeta, "temporadas", "2025.json"), "w").close()
    try:
        exportar_web.exportar_actual(2026)
    finally:
        historial.pedir_json, historial.data_path, exportar_web.DATOS = originales
    assert any(ruta == "2026/results" for ruta, _ in llamadas)
    assert any(ruta.startswith("circuits/") for ruta, _ in llamadas)
    assert {reintentos for _, reintentos in llamadas} == {exportar_web.REINTENTOS}
    assert exportar_web.REINTENTOS > 1



def test_en_enero_el_deploy_agrega_la_temporada_que_termino():
    """Si todavía no se corrió --historico, el año que terminó se exporta solo y
    se suma a carreras_previas: si no, la web lo perdía."""
    carpeta = tempfile.mkdtemp()
    previa = {"titulos": 0, "victorias": 5, "podios": 20, "gps": 100, "debut": 2019}
    with open(os.path.join(carpeta, "carreras_previas.json"), "w", encoding="utf-8") as archivo:
        json.dump({"norris": previa}, archivo)
    originales = exportar_web.base_de, exportar_web.DATOS
    exportar_web.base_de = lambda anio: base_de_prueba()
    exportar_web.DATOS = carpeta
    try:
        exportar_web.exportar_terminada(2025)
    finally:
        exportar_web.base_de, exportar_web.DATOS = originales
    with open(os.path.join(carpeta, "temporadas", "2025.json"), encoding="utf-8") as archivo:
        assert json.load(archivo)["anio"] == 2025
    with open(os.path.join(carpeta, "carreras_previas.json"), encoding="utf-8") as archivo:
        previas = json.load(archivo)
    nueva = historial.carrera_completa(base_de_prueba(), "norris")
    assert previas["norris"]["gps"] == 100 + nueva["gps"]
    assert previas["norris"]["victorias"] == 5 + nueva["victorias"]
    assert previas["norris"]["debut"] == 2019
    assert previas["senna"] == historial.carrera_completa(base_de_prueba(), "senna")


if __name__ == "__main__":
    for nombre, prueba in list(globals().items()):
        if nombre.startswith("test_"):
            prueba()
    print("ok")


URL_ANT = ("https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/"
           "drivers/K/ANDANT01_Kimi_Antonelli/andant01.png.transform/1col/image.png")


def _datos_fotos():
    return {
        "pilotos": [
            {"driver_id": "antonelli", "codigo": "ANT", "constructor_id": "mercedes", "headshot_url": None},
            {"driver_id": "tsunoda", "codigo": "TSU", "constructor_id": "red_bull", "headshot_url": None},
        ],
        "equipos": [{"constructor_id": "mercedes", "cara_a_cara": {
            "a": {"driver_id": "antonelli", "headshot_url": None},
            "b": {"driver_id": "russell", "headshot_url": None}}}],
    }


def test_completar_fotos_cruza_openf1_por_sigla():
    datos = _datos_fotos()
    exportar_web.completar_fotos(datos, 2026, lambda ruta: [
        {"name_acronym": "ANT", "headshot_url": URL_ANT},
        {"name_acronym": "RUS", "headshot_url": None},
    ])
    ant, tsu = datos["pilotos"]
    assert ant["headshot_url"] == URL_ANT.replace("/1col/", "/2col/")
    assert ant["foto_cuerpo"] == ("https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/"
                                  "common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp")
    # Sin coincidencia en OpenF1: queda como antes (Wikipedia o sigla).
    assert tsu["headshot_url"] is None and "foto_cuerpo" not in tsu
    cara = datos["equipos"][0]["cara_a_cara"]
    assert cara["a"]["headshot_url"] == ant["headshot_url"]
    assert cara["b"]["headshot_url"] is None


def test_completar_fotos_sin_openf1_no_rompe_el_deploy():
    def caido(ruta):
        raise OSError("sin red")
    datos = _datos_fotos()
    exportar_web.completar_fotos(datos, 2026, caido)
    assert datos["pilotos"][0]["headshot_url"] is None


def test_completar_fotos_con_respuesta_rara_de_openf1_no_rompe_el_deploy():
    for respuesta in ({"detail": "No results found."}, [{"headshot_url": URL_ANT}]):
        datos = _datos_fotos()
        exportar_web.completar_fotos(datos, 2026, lambda ruta, r=respuesta: r)
        assert datos["pilotos"][0]["headshot_url"] is None
