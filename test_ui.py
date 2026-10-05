"""Chequeos mínimos de la lógica no trivial de la UI.

Sin frameworks ni fixtures: un QApplication offscreen y asserts. Corre tanto con
`pytest test_ui.py` como con `python test_ui.py`.
"""
import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

# Referencia viva a nivel de módulo: si se recolecta, cualquier widget creado
# después crashea. No se usa en ningún lado a propósito.
_app = QApplication.instance() or QApplication([])

import pandas as pd

import ui.calendar_view as calendar_view
from ui.selector_temporada import SelectorTemporada
from ui.calendar_view import CalendarView
from ui.calendar_event_card import CalendarEventCard
from ui.event_detail_view import EventDetailView
from ui.icons import PODIO
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

import workers.pilotos_worker as pilotos_worker
from test_historial import base_de_prueba
from ui.fichas_pilotos import formato_celda, sigla
import ui.pilotos_view as pilotos_view
from core import historial


def test_ir_a_anio_clampea_los_dos_extremos():
    barra = SelectorTemporada()
    emitidos = []
    barra.anio_cambiado.connect(emitidos.append)
    # El debounce real es de 150 ms; acá lo colapsamos a 0 para no dormir.
    barra._timer_emision.setInterval(0)

    barra.ir_a_anio(SelectorTemporada.ANIO_MIN - 50)
    assert barra.anio_actual == SelectorTemporada.ANIO_MIN
    assert barra.campo_anio.text() == str(SelectorTemporada.ANIO_MIN)
    assert not barra.boton_anio_anterior.isEnabled()
    # El campo y los botones se actualizan en el acto; lo que se posterga es
    # sólo la emisión que dispara la carga de datos.
    assert emitidos == []
    _app.processEvents()

    barra.ir_a_anio(SelectorTemporada.ANIO_MAX + 50)
    assert barra.anio_actual == SelectorTemporada.ANIO_MAX
    assert not barra.boton_anio_siguiente.isEnabled()
    _app.processEvents()

    assert emitidos == [SelectorTemporada.ANIO_MIN, SelectorTemporada.ANIO_MAX]


def test_el_debounce_colapsa_una_rafaga_en_una_sola_carga():
    """El auto-repeat del teclado dispara ~30 pulsaciones por segundo. Si cada
    una emitiera, mantener la flecha apretada arrancaba un QThread y una carga
    de datos por año recorrido."""
    barra = SelectorTemporada()
    emitidos = []
    barra.anio_cambiado.connect(emitidos.append)
    barra._timer_emision.setInterval(0)

    for _ in range(10):
        barra._anio_anterior()
    assert emitidos == [], "emitió durante la ráfaga"

    _app.processEvents()
    assert emitidos == [SelectorTemporada.ANIO_MAX - 10], emitidos


def test_el_calendario_no_trae_los_tests_de_pretemporada():
    """Los tests de pretemporada vienen con RoundNumber 0, y
    get_session(year, 0, ...) tira 'Cannot get testing event by round number!':
    todos los botones de sesión de esas tarjetas terminaban en error."""
    import fastf1
    import workers.calendar_worker as cw

    llamadas = []
    original = fastf1.get_event_schedule
    fastf1.get_event_schedule = lambda year, **kw: llamadas.append((year, kw)) or "df"
    try:
        # El año en curso: los terminados salen de cache_calendarios sin pedir nada.
        anio = date.today().year
        worker = cw.CalendarWorker(anio)
        emitidos = []
        worker.terminado.connect(emitidos.append)
        worker.run()
    finally:
        fastf1.get_event_schedule = original

    assert llamadas == [(anio, {"include_testing": False})], llamadas
    assert emitidos == ["df"]


def test_mapa_tardio_de_otro_circuito_se_descarta():
    """Generar un mapa baja la telemetría de una carrera entera. Si el worker
    termina después de que el usuario abrió otro GP, pintarlo mostraría el
    circuito equivocado en la ficha."""
    vista = EventDetailView()
    vista._location_mapa = "Monza"

    class _WorkerMapaFalso:
        location = "Spa-Francorchamps"

    vista.sender = lambda: _WorkerMapaFalso()

    pintados = []
    vista._pintar_mapa = lambda ruta=None: pintados.append(ruta)

    vista._on_mapa_generado("spa.png")
    assert pintados == [], "pintó el mapa de otro circuito"

    _WorkerMapaFalso.location = "Monza"
    vista._on_mapa_generado("monza.png")
    assert pintados == ["monza.png"]


def test_la_sesion_tardia_de_otro_gp_se_descarta():
    """Abrir un GP arranca en la carrera, y la del GP anterior también es 'R':
    comparar sólo el código mostraba sus resultados (o su error) en el nuevo."""
    vista = EventDetailView()
    vista._sesion_pedida = (2025, 5, "R")

    class _WorkerSesionFalso:
        year, gp, codigo_sesion = 2025, 4, "R"

    vista.sender = lambda: _WorkerSesionFalso()
    vista.on_sesion_cargada(None)   # descartada antes de tocar la sesión
    vista.on_error("del GP anterior")
    assert vista.estado.objectName() != "estadoError"

    _WorkerSesionFalso.gp = 5
    vista.on_error("sin red")
    assert vista.estado.objectName() == "estadoError"


def test_el_mapa_no_se_re_escala_si_el_tamano_no_cambio():
    """resizeEvent entra acá por cada píxel que se arrastra el borde, y los PNG
    de cache_tracks llegan a 2275x2400: re-escalar con SmoothTransformation cada
    vez (más el drop shadow del QLabel, que fuerza render por software) tironea."""
    vista = EventDetailView()
    vista._pixmap_mapa = QPixmap(400, 300)
    vista._tamano_mapa_pintado = None

    escalados = []
    vista.imagen_circuito.setPixmap = lambda pixmap: escalados.append(pixmap)

    for _ in range(5):
        vista._pintar_mapa()

    assert len(escalados) == 1, f"{len(escalados)} re-escalados con el mismo tamaño"


def test_calcular_columnas_nunca_devuelve_cero():
    vista = CalendarView()
    # Viewport sin mostrar mide 0 de ancho: sin el max(1, ...) el grid haría
    # una división por cero al calcular fila/columna.
    assert vista._calcular_columnas() >= 1

    vista.resize(1300, 750)
    columnas_anchas = vista._calcular_columnas()
    vista.resize(400, 750)
    assert 1 <= vista._calcular_columnas() <= columnas_anchas


def test_todos_los_alias_apuntan_a_un_circuito_real():
    """Un alias con el destino mal escrito deja al circuito sin datos sin avisar:
    obtener_datos_circuito devuelve None y la UI muestra solo el nombre."""
    from core.circuits import ALIAS_LOCATION, DATOS_CIRCUITOS, obtener_datos_circuito

    for crudo, canonico in ALIAS_LOCATION.items():
        assert canonico in DATOS_CIRCUITOS, (
            f"el alias {crudo!r} apunta a {canonico!r}, que no es una clave de "
            f"DATOS_CIRCUITOS")
        assert obtener_datos_circuito(crudo) is not None, f"{crudo!r} quedó sin datos"

    # Un alias no puede apuntar a otro alias: normalizar_location se aplica una
    # sola vez, así que la cadena nunca se resolvería.
    for crudo, canonico in ALIAS_LOCATION.items():
        assert canonico not in ALIAS_LOCATION, (
            f"{crudo!r} -> {canonico!r}, que a su vez es un alias")

    # Toda entrada de datos tiene los campos que el panel del circuito pinta.
    campos = ("nombre_completo", "longitud_km", "vueltas", "distancia_km",
              "curvas", "record_vuelta", "primer_gp")
    for clave, datos in DATOS_CIRCUITOS.items():
        faltan = [c for c in campos if c not in datos]
        assert not faltan, f"{clave!r} no tiene {faltan}"


def test_distancia_coherente_con_longitud_por_vueltas():
    """distancia_km tiene que ser longitud_km * vueltas, con el margen que deja
    la línea de meta adelantada respecto del punto de largada."""
    from core.circuits import DATOS_CIRCUITOS

    for clave, d in DATOS_CIRCUITOS.items():
        esperado = d["longitud_km"] * d["vueltas"]
        diferencia = abs(esperado - d["distancia_km"])
        assert diferencia < d["longitud_km"], (
            f"{clave}: {d['longitud_km']} km x {d['vueltas']} vueltas = "
            f"{esperado:.3f}, pero distancia_km dice {d['distancia_km']} "
            f"(difieren {diferencia:.3f} km)")


def _ratio_contraste(hex_a, hex_b):
    """Ratio de contraste WCAG 2.1 entre dos colores #RRGGBB."""
    def luminancia(h):
        canales = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                  for c in canales]
        return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]

    a, b = luminancia(hex_a), luminancia(hex_b)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def test_contraste_de_la_paleta():
    """Los pares texto/fondo de la cabecera de style.qss tienen que pasar WCAG AA.

    Ojo con text-muted: el fondo más claro donde aparece es bg-surface-hover,
    así que oscurecerlo o aclarar ese fondo es lo primero que rompe esto.
    """
    AA_TEXTO, AA_UI = 4.5, 3.0
    pares = [
        ("text-primary / bg-app",       "#F3F6F9", "#090A0D", AA_TEXTO),
        ("text-primary / bg-surface",   "#F3F6F9", "#1B2029", AA_TEXTO),
        ("text-secondary / bg-surface", "#CAD2DC", "#1B2029", AA_TEXTO),
        ("text-muted / bg-app",         "#A4AEBC", "#090A0D", AA_TEXTO),
        ("text-muted / bg-surface",     "#A4AEBC", "#1B2029", AA_TEXTO),
        ("text-muted / bg-panel",       "#A4AEBC", "#12161C", AA_TEXTO),
        ("text-muted / bg-hover",       "#A4AEBC", "#262D38", AA_TEXTO),
        ("cargando / bg-app",           "#E8B931", "#090A0D", AA_TEXTO),
        ("error / bg-app",              "#FF6B57", "#090A0D", AA_TEXTO),
        # El rojo de acento sólo pinta bordes de foco: es UI, no texto.
        ("foco accent / bg-app",        "#E10600", "#090A0D", AA_UI),
        ("foco accent / bg-surface",    "#E10600", "#1B2029", AA_UI),
        ("blanco / chip accent",        "#FFFFFF", "#E10600", AA_TEXTO),
        ("dato / bg-panel",             "#52DEEC", "#12161C", AA_TEXTO),
        ("dato / bg-sunken",            "#52DEEC", "#0C0E12", AA_TEXTO),
        # Tira de resultados: podio y abandono sobre el panel de la celda.
        ("oro / bg-panel",              "#F3D27A", "#12161C", AA_TEXTO),
        ("error / bg-panel",            "#FF6B57", "#12161C", AA_TEXTO),
        # Bloque de próxima carrera: horarios y lugar sobre accent-wash.
        ("text-muted / accent-wash",    "#A4AEBC", "#261519", AA_TEXTO),
        ("text-secondary / accent-wash", "#CAD2DC", "#261519", AA_TEXTO),
        # Número de las medallas contra el tono más oscuro de su degradé.
        *((f"medalla {i + 1}", texto, abajo, AA_TEXTO)
          for i, (_, abajo, texto) in enumerate(PODIO)),
    ]
    for nombre, fg, bg, minimo in pares:
        ratio = _ratio_contraste(fg, bg)
        assert ratio >= minimo, f"{nombre}: {ratio:.2f}:1, hace falta {minimo}:1"


def test_qss_no_tiene_reglas_muertas():
    """Un selector #objectName que ningún widget usa es estilo que no se aplica
    y nadie nota. Antes de este chequeo había tres: #selectorTabs,
    #panelInfoCircuito y #textoInfoCircuito.

    Se comparan contra TODOS los literales de los módulos de ui/ y no sólo
    contra setObjectName("..."), porque _set_estado asigna el nombre desde un
    dict (estadoCargando / estadoError nunca aparecen como literal en la
    llamada).
    """
    import glob
    import re

    qss = open("style.qss", encoding="utf-8").read()
    sin_comentarios = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    selectores = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*#([A-Za-z_][A-Za-z0-9_]*)",
                                sin_comentarios))
    assert selectores, "no se extrajo ningún selector: el regex se rompió"

    literales = set()
    for archivo in glob.glob("ui/*.py") + ["main.py"]:
        literales |= set(re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']",
                                    open(archivo, encoding="utf-8").read()))

    muertos = sorted(selectores - literales)
    assert not muertos, f"selectores sin widget que los use: {muertos}"


CARRERAS_POR_ANIO = {2026: 5, 2025: 7, 2024: 9, 2023: 6,
                     2022: 8, 2021: 4, 2020: 3, 2019: 5}


def _calendario_falso(year):
    base = pd.Timestamp(f"{year}-03-01")
    return pd.DataFrame([{
        "EventName": f"GP{year}-{i}",
        "Country": "Italy",
        "EventDate": base + pd.Timedelta(30 * i, unit="D"),
        "RoundNumber": i + 1,
    } for i in range(CARRERAS_POR_ANIO[year])])


class _WorkerFalso:
    """Emite el calendario en el acto, sin red. Imita la forma de CalendarWorker."""

    vista = None

    def __init__(self, year):
        self.year = year
        self._terminado, self._error, self._finished = [], [], []

    class _Senal:
        def __init__(self, destinos):
            self._destinos = destinos

        def connect(self, cb):
            self._destinos.append(cb)

    @property
    def terminado(self):
        return self._Senal(self._terminado)

    @property
    def error(self):
        return self._Senal(self._error)

    @property
    def finished(self):
        return self._Senal(self._finished)

    def start(self):
        _WorkerFalso.vista.sender = lambda: self
        for cb in self._terminado:
            cb(_calendario_falso(self.year))
        for cb in self._finished:
            cb()


def test_cambiar_de_anio_no_deja_tarjetas_del_anio_anterior():
    """Volver a un año cacheado tiene que ocultar las tarjetas que salen.

    Si no, siguen pintadas fuera del layout y se ven dos años superpuestos:
    el botón del año cambia pero el calendario parece no actualizarse.
    """
    original = calendar_view.CalendarWorker
    calendar_view.CalendarWorker = _WorkerFalso
    try:
        vista = CalendarView()
        _WorkerFalso.vista = vista
        vista.resize(1130, 695)
        vista.show()

        # atrás (años nuevos) y después adelante (años ya cacheados)
        for year in (2026, 2025, 2024, 2025, 2026, 2024):
            vista.cargar_calendario(year)

            visibles = [c for c in vista.contenedor_grid.children()
                        if isinstance(c, CalendarEventCard) and c.isVisible()]
            anios = {c.toolTip().split("-")[0].replace("GP", "") for c in visibles}

            assert len(visibles) == CARRERAS_POR_ANIO[year], (
                f"{year}: {len(visibles)} tarjetas visibles, "
                f"se esperaban {CARRERAS_POR_ANIO[year]}")
            en_grid = [vista.grid.itemAt(i).widget() for i in range(vista.grid.count())]
            assert sum(isinstance(w, CalendarEventCard) for w in en_grid) == CARRERAS_POR_ANIO[year]
            assert anios == {str(year)}, f"{year}: años superpuestos {sorted(anios)}"
    finally:
        calendar_view.CalendarWorker = original
        _WorkerFalso.vista = None


def test_el_cache_de_anios_tiene_tope():
    """Sin tope, recorrer el calendario con las flechas deja vivas las tarjetas
    de todos los años: ~24 QWidgets con drop shadow y dos animaciones cada uno."""
    original = calendar_view.CalendarWorker
    calendar_view.CalendarWorker = _WorkerFalso
    try:
        vista = CalendarView()
        _WorkerFalso.vista = vista
        vista.show()

        anios = sorted(CARRERAS_POR_ANIO)
        assert len(anios) > CalendarView.MAX_ANIOS_CACHEADOS, "el test no desborda nada"
        for year in anios:
            vista.cargar_calendario(year)

        assert len(vista._cache_por_anio) == CalendarView.MAX_ANIOS_CACHEADOS
        # El año que se está mirando es el último insertado: nunca se desaloja.
        assert anios[-1] in vista._cache_por_anio
    finally:
        calendar_view.CalendarWorker = original
        _WorkerFalso.vista = None


def test_el_calendario_abre_en_el_mes_actual():
    """Los meses anteriores quedan arriba (se llega scrolleando para arriba) y
    los siguientes abajo. 2025 falso: carreras de marzo a agosto."""
    original = calendar_view.CalendarWorker
    calendar_view.CalendarWorker = _WorkerFalso
    try:
        vista = CalendarView()
        _WorkerFalso.vista = vista
        vista.resize(1130, 500)
        vista.show()
        vista.cargar_calendario(2025)

        assert [m for m, _ in vista._encabezados] == [3, 4, 5, 6, 7, 8]
        assert vista.mes_destino(pd.Timestamp("2025-06-15")) == 6
        # enero no tiene carreras: el próximo mes que sí
        assert vista.mes_destino(pd.Timestamp("2025-01-10")) == 3
        # temporada terminada: el último mes
        assert vista.mes_destino(pd.Timestamp("2025-12-01")) == 8
        # otro año que el que se mira: desde el principio
        assert vista.mes_destino(pd.Timestamp("2026-06-15")) == 3

        vista._ir_al_mes_actual(pd.Timestamp("2025-06-15"))
        barra = vista.scroll.verticalScrollBar()
        junio = dict(vista._encabezados)[6]
        y_junio = junio.mapTo(vista.scroll.widget(), calendar_view.QPoint(0, 0)).y()
        assert barra.value() > 0, "no scrolleó: marzo quedó arriba"
        assert barra.value() == min(y_junio, barra.maximum())
    finally:
        calendar_view.CalendarWorker = original
        _WorkerFalso.vista = None


def test_las_tarjetas_nunca_se_muestran_como_ventana():
    """Una QWidget sin padre que recibe show() se vuelve ventana top-level y
    parpadea en el centro de la pantalla."""
    original = calendar_view.CalendarWorker
    show_real = CalendarEventCard.show
    huerfanas = []

    def show_vigilado(self):
        if self.parent() is None:
            huerfanas.append(self)
        return show_real(self)

    calendar_view.CalendarWorker = _WorkerFalso
    CalendarEventCard.show = show_vigilado
    try:
        vista = CalendarView()
        _WorkerFalso.vista = vista
        vista.show()
        for year in (2026, 2025, 2026):   # nuevo, nuevo, cacheado
            vista.cargar_calendario(year)
        assert not huerfanas, f"{len(huerfanas)} tarjetas mostradas sin padre"
    finally:
        calendar_view.CalendarWorker = original
        CalendarEventCard.show = show_real
        _WorkerFalso.vista = None


def _correr_pilotos_worker(year, descargar, anio_actual, limpiar=True, actualizada=None,
                           clase=None):
    """Corre PilotosWorker.run() (u otro worker que lea la base, con `clase`) en
    el hilo del test, con la base falsa y la descarga reemplazada. Devuelve
    (emitidos por terminado, emitidos por error). `actualizada` pisa la fecha en
    que se guardó la temporada `year`."""
    base = base_de_prueba()   # antes de reemplazar descargar_temporada: la usa
    if actualizada is not None:
        base.execute("UPDATE temporadas SET actualizada = ? WHERE temporada = ?",
                     (actualizada, year))
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
        worker = (clase or pilotos_worker.PilotosWorker)(year)
        datos, errores = [], []
        worker.terminado.connect(datos.append)
        worker.error.connect(errores.append)
        worker.run()
        return datos, errores
    finally:
        (h.abrir_base, h.descargar_temporada, h.completar_headshots,
         pilotos_worker.anio_actual) = originales


def _sin_red(con, anio, desde=None):
    raise OSError("sin red")


def test_temporada_terminada_y_guardada_no_toca_la_red():
    datos, errores = _correr_pilotos_worker(2025, _sin_red, anio_actual=2026)
    assert not errores, errores
    assert [p["driver_id"] for p in datos[0]["pilotos"]] == ["norris", "piastri", "leclerc", "lawson"]
    assert [e["constructor_id"] for e in datos[0]["equipos"]] == ["mclaren", "ferrari"]
    assert len(datos) == 1, datos   # terminada: no hay nada que actualizar


def test_temporada_en_curso_sin_red_muestra_lo_guardado():
    datos, errores = _correr_pilotos_worker(2025, _sin_red, anio_actual=2025,
                                            actualizada="2025-06-01 12:00:00")
    assert not errores, errores
    assert len(datos[0]["pilotos"]) == 4


def test_temporada_que_falta_y_sin_red_da_error():
    datos, errores = _correr_pilotos_worker(2026, _sin_red, anio_actual=2026)
    assert datos == [] and errores == ["sin red"], (datos, errores)


def test_la_temporada_en_curso_se_baja_una_sola_vez_por_sesion():
    llamadas = []
    _correr_pilotos_worker(2025, lambda con, anio, desde=None: llamadas.append(anio), anio_actual=2025,
                           actualizada="2025-06-01 12:00:00")
    _correr_pilotos_worker(2025, lambda con, anio, desde=None: llamadas.append(anio), anio_actual=2025,
                           limpiar=False, actualizada="2025-06-01 12:00:00")
    assert llamadas == [2025], llamadas


def test_una_temporada_guardada_a_mitad_de_anio_se_completa_cuando_termina():
    """Guardada en noviembre, con dos carreras por correr: en enero ya no es la
    temporada en curso, pero le faltan esas carreras y el campeón."""
    llamadas = []
    _correr_pilotos_worker(2025, lambda con, anio, desde=None: llamadas.append(anio), anio_actual=2026,
                           actualizada="2025-11-20 10:00:00")
    assert llamadas == [2025], llamadas
    # Bajada después de fin de año ya está completa: no se vuelve a pedir.
    _correr_pilotos_worker(2025, lambda con, anio, desde=None: llamadas.append(anio), anio_actual=2026,
                           actualizada="2026-01-03 10:00:00")
    assert llamadas == [2025], llamadas


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
    def __init__(self, pilotos, equipos=()):
        self.pilotos = pilotos

    @property
    def foto_lista(self):
        return _WorkerFalso._Senal([])

    @property
    def logo_listo(self):
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
        assert [t.clave for t in vista.grilla_pilotos.tarjetas()] ==             ["norris", "piastri", "leclerc", "lawson"]
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
        assert len(vista.ficha_piloto.grafico.carreras()) == 4
        assert vista.volver_a_grilla()
        assert vista.stack_interno.currentIndex() == pilotos_view.GRILLA_PILOTOS
        assert not vista.volver_a_grilla(), "desde la grilla, Esc le toca a MainWindow"

        vista.abrir_equipo("mclaren")
        assert vista.stack_interno.currentIndex() == pilotos_view.FICHA_EQUIPO
        assert vista.ficha_equipo.filas["carrera"].valor_a.text() == "2"
        assert vista.ficha_equipo.sin_duelo.isHidden()
        assert vista.ficha_equipo.grandes._valores[2].text() == "2"   # victorias
        assert len(vista.ficha_equipo.tira.celdas()) == 8               # 4 carreras x 2

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


def test_las_tarjetas_de_equipo_llenan_el_ancho_y_muestran_sus_pilotos():
    vista = _vista_pilotos()
    try:
        vista.show()
        vista.cargar_datos(2025)
        vista._cambiar_tab(pilotos_view.GRILLA_EQUIPOS)
        QApplication.processEvents()
        mclaren, ferrari = vista.grilla_equipos.tarjetas()
        disponible = vista.grilla_equipos.viewport().width()
        # Dos tarjetas en una fila que ocupa todo el ancho (no 320 px cada una).
        assert mclaren.width() + ferrari.width() > disponible * 0.9,             (mclaren.width(), ferrari.width(), disponible)
        assert [f.driver_id for f in mclaren.fotos] == ["norris", "piastri"]
        assert ferrari.logo.iniciales == "FER"   # sin logo bajado: iniciales
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


def test_la_sidebar_lleva_a_pilotos():
    from ui.sidebar import Sidebar
    sidebar = Sidebar()
    destinos = []
    sidebar.navegar.connect(destinos.append)
    sidebar.boton_pilotos.click()
    assert destinos == ["pilotos"]


def test_cambiar_de_equipo_no_deja_celdas_ni_tarjetas_del_anterior():
    """Lo que sale del layout queda pintado hasta que deleteLater lo borra de
    verdad: sin ocultarlo, la tira de McLaren 1988 mostraba al final celdas de
    McLaren 2025 (el mismo bug que tuvo el calendario con las tarjetas)."""
    from PySide6.QtWidgets import QLabel
    vista = _vista_pilotos()
    try:
        vista.show()
        vista.cargar_datos(2025)
        vista.abrir_equipo("mclaren")           # 4 carreras
        vista.cargar_datos(1988)
        vista.abrir_equipo("mclaren")           # 1 carrera
        celdas = [c for c in vista.ficha_equipo.tira.findChildren(QLabel, "celdaDuelo")
                  if c.isVisible()]
        assert len(celdas) == 2, f"{len(celdas)} celdas visibles"
        # La grilla está tapada por la ficha: lo que cuenta es si cada tarjeta
        # quedó oculta a propósito, no si se ve en este momento.
        tarjetas = [t for t in vista.grilla_pilotos.widget().children()
                    if getattr(t, "clave", None) and not t.isHidden()]
        assert sorted(t.clave for t in tarjetas) == ["prost", "senna"],             sorted(t.clave for t in tarjetas)
    finally:
        _restaurar_pilotos()


def test_las_flechas_siguen_cambiando_de_anio_desde_la_pestania_pilotos():
    """QAbstractScrollArea se queda con ←/→ aunque no tenga scroll horizontal:
    después de tocar una tarjeta, las flechas dejaban de cambiar de año."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    vista = _vista_pilotos()
    try:
        scrolls = [vista.grilla_pilotos, vista.grilla_equipos,
                   vista.stack_interno.widget(pilotos_view.FICHA_PILOTO),
                   vista.stack_interno.widget(pilotos_view.FICHA_EQUIPO)]
        for scroll in scrolls:
            for tecla in (Qt.Key_Left, Qt.Key_Right):
                evento = QKeyEvent(QEvent.KeyPress, tecla, Qt.NoModifier)
                scroll.keyPressEvent(evento)
                assert not evento.isAccepted(), f"{type(scroll).__name__} se comió {tecla}"
    finally:
        _restaurar_pilotos()


def test_en_juego_cuenta_los_sprints_que_faltan():
    from ui.standings_view import StandingsView
    vista = StandingsView()
    pilotos = [{"nombre": "Kimi", "apellido": "Antonelli", "puntos": 320.0}]
    equipos = [{"nombre": "Mercedes", "puntos": 500.0}]
    vista._datos = {"pilotos": pilotos, "equipos": equipos, "ronda": 20,
                    "total_rondas": 24, "sprints_restantes": 2}
    _, valor, detalle = vista._kpis[2]

    vista._cambiar_tab(0)
    assert ">116<" in valor.text(), valor.text()          # 4 × 25 + 2 × 8
    assert detalle.text() == "4 carreras y 2 sprints restantes", detalle.text()
    vista._cambiar_tab(1)
    assert ">202<" in valor.text(), valor.text()          # 4 × 43 + 2 × 15

    vista._datos["sprints_restantes"] = 0
    vista._actualizar_kpis()
    assert detalle.text() == "4 carreras restantes", detalle.text()


def _correr_standings_worker(*args, **kwargs):
    """Como _correr_pilotos_worker, con un calendario de 6 fechas (la 5 con
    sprint) en lugar del de FastF1."""
    import workers.standings_worker as standings_worker
    calendario = pd.DataFrame({"RoundNumber": range(1, 7),
                               "EventFormat": ["conventional"] * 4 + ["sprint_qualifying", "conventional"]})
    original = standings_worker.obtener_calendario
    standings_worker.obtener_calendario = lambda anio: calendario
    try:
        return _correr_pilotos_worker(*args, clase=standings_worker.StandingsWorker, **kwargs)
    finally:
        standings_worker.obtener_calendario = original


def test_la_clasificacion_sale_de_la_base_sin_pedirle_nada_a_ergast():
    datos, errores = _correr_standings_worker(2025, _sin_red, anio_actual=2026)
    assert not errores, errores
    assert len(datos) == 1, datos   # terminada: no hay segunda emisión
    d = datos[0]
    assert [p["driver_id"] for p in d["pilotos"]] == ["norris", "piastri", "leclerc", "lawson"]
    assert [e["constructor_id"] for e in d["equipos"]] == ["mclaren", "ferrari"]
    assert (d["ronda"], d["total_rondas"], d["sprints_restantes"]) == (4, 6, 1)


def test_la_clasificacion_de_sesion_baja_vueltas_solo_si_ergast_no_la_tiene():
    import workers.session_worker as session_worker

    class SesionFalsa:
        def __init__(self, posiciones):
            self.cargas = []
            self.results = pd.DataFrame({"Position": posiciones, "Q1": pd.NaT,
                                         "Q2": pd.NaT, "Q3": pd.NaT})

        def load(self, **opciones):
            self.cargas.append((opciones["laps"], opciones["messages"]))

    def cargas(codigo, posiciones):
        sesion = SesionFalsa(posiciones)
        original = session_worker.fastf1.get_session
        session_worker.fastf1.get_session = lambda *args: sesion
        try:
            session_worker.SessionWorker(2026, 1, codigo).run()
        finally:
            session_worker.fastf1.get_session = original
        return sesion.cargas

    assert cargas("Q", [1.0, 2.0]) == [(False, False)]
    # Recién terminada: Ergast todavía no la publicó y FastF1 la calcula de las
    # vueltas, para lo que necesita los mensajes (vueltas borradas).
    assert cargas("Q", [None, None]) == [(False, False), (True, True)]
    assert cargas("SQ", [None, None]) == [(True, True)]
    assert cargas("R", [1.0, 2.0]) == [(False, False)]


def _subir_puntos(con, anio, desde=None):
    """Descarga falsa: la temporada nueva trae 10 puntos más para todos."""
    con.execute("UPDATE campeonato_pilotos SET puntos = puntos + 10 WHERE temporada = ?", (anio,))


def test_temporada_en_curso_muestra_lo_guardado_y_despues_lo_nuevo():
    for correr in (_correr_pilotos_worker, _correr_standings_worker):
        datos, errores = correr(2025, _subir_puntos, anio_actual=2025,
                                actualizada="2025-06-01 12:00:00")
        assert not errores, errores
        assert [(d["actualizando"], d["pilotos"][0]["puntos"]) for d in datos] ==             [(True, 50), (False, 60)], correr


def test_la_clasificacion_y_pilotos_se_actualizan_sin_aviso():
    from ui.standings_view import StandingsView
    from ui.pilotos_view import PilotosView
    for correr, Vista in ((_correr_standings_worker, StandingsView),
                          (_correr_pilotos_worker, PilotosView)):
        datos, _ = correr(2025, _subir_puntos, anio_actual=2025,
                          actualizada="2025-06-01 12:00:00")
        vista = Vista()
        vista.year = 2025
        vista._mostrar(datos[0])
        assert vista.estado.text() == "", (Vista, vista.estado.text())


def test_la_temporada_en_curso_baja_solo_desde_la_ronda_que_falta():
    """La guardada llega a la R4: se pide desde la 5. Una ya terminada se baja
    entera una última vez, por si corrigieron resultados después de guardarla."""
    llamadas = []

    def anotar(con, anio, desde=None):
        llamadas.append(desde)

    _correr_pilotos_worker(2025, anotar, anio_actual=2025, actualizada="2025-06-01 12:00:00")
    _correr_pilotos_worker(2025, anotar, anio_actual=2026, actualizada="2025-11-20 10:00:00")
    assert llamadas == [5, None], llamadas


def test_el_mapa_y_la_ficha_se_abren_con_un_clic():
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QKeyEvent, QMouseEvent
    from ui.vista_ampliada import VistaAmpliada

    vista = EventDetailView()
    vista.resize(1200, 800)
    vista._pixmap_mapa = QPixmap(400, 400)
    vista._ficha_actual = ("Bahrain International Circuit", None, None)

    def abiertas():
        return [w for w in QApplication.topLevelWidgets()
                if isinstance(w, VistaAmpliada) and w.isVisible()]

    clic = QMouseEvent(QEvent.MouseButtonRelease, QPointF(5, 5), QPointF(5, 5),
                       Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(vista.imagen_circuito, clic)
    capa = abiertas()
    assert len(capa) == 1, capa
    QApplication.sendEvent(capa[0], QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert not abiertas()

    # La ficha de datos también se abre con un clic (sin circuit_id no pide nada a la red).
    QApplication.sendEvent(vista.texto_info, clic)
    capa = abiertas()
    assert len(capa) == 1, capa
    capa[0].reject()


def test_doble_clic_en_la_clasificacion_pide_la_ficha_del_piloto_o_del_equipo():
    from ui.standings_view import StandingsView
    datos, _ = _correr_standings_worker(2025, lambda *a, **k: None, anio_actual=2026)
    vista = StandingsView()
    vista.year = 2025
    vista._mostrar(datos[-1])
    pedidas = []
    vista.abrir_ficha.connect(lambda tipo, id_: pedidas.append((tipo, id_)))
    tabla = vista.tabla_pilotos
    tabla.activated.emit(tabla.model().index(0, 1))   # nombre del líder
    tabla.activated.emit(tabla.model().index(0, 2))   # su equipo
    lider = datos[-1]["pilotos"][0]
    assert pedidas == [("piloto", lider["driver_id"]), ("equipo", lider["constructor_id"])], pedidas


def test_la_ficha_pedida_de_afuera_espera_los_datos_y_volver_avisa():
    from ui.pilotos_view import PilotosView, FICHA_PILOTO, GRILLA_PILOTOS
    datos, _ = _correr_pilotos_worker(2025, lambda *a, **k: None, anio_actual=2026)
    vista = PilotosView()
    vista._con = base_de_prueba()
    vista.year = 2025
    volvio = []
    vista.volver_origen.connect(lambda: volvio.append(True))

    # Un piloto que no corrió el campeonato no abre nada.
    vista._mostrar(datos[-1])
    vista.abrir_ficha_externa("piloto", "no_existe")
    assert vista.stack_interno.currentIndex() == GRILLA_PILOTOS

    # Antes de que lleguen los datos queda pendiente; al llegar, se abre.
    vista._datos = None
    driver_id = datos[-1]["pilotos"][0]["driver_id"]
    vista.abrir_ficha_externa("piloto", driver_id)
    assert vista.stack_interno.currentIndex() == GRILLA_PILOTOS
    vista._mostrar(datos[-1])
    assert vista.stack_interno.currentIndex() == FICHA_PILOTO

    assert vista.volver_a_grilla() and volvio == [True]
    assert vista.stack_interno.currentIndex() == GRILLA_PILOTOS


if __name__ == "__main__":
    for nombre, prueba in list(globals().items()):
        if nombre.startswith("test_"):
            prueba()
    print("ok")
