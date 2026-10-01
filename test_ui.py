"""Chequeos mínimos de la lógica no trivial de la UI.

Sin frameworks ni fixtures: un QApplication offscreen y asserts. Corre tanto con
`pytest test_ui.py` como con `python test_ui.py`.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

# Referencia viva a nivel de módulo: si se recolecta, cualquier widget creado
# después crashea. No se usa en ningún lado a propósito.
_app = QApplication.instance() or QApplication([])

import pandas as pd

import ui.calendar_view as calendar_view
from ui.topbar import TopBar
from ui.calendar_view import CalendarView
from ui.calendar_event_card import CalendarEventCard
from ui.event_detail_view import EventDetailView
from PySide6.QtGui import QPixmap


def test_ir_a_anio_clampea_los_dos_extremos():
    barra = TopBar()
    emitidos = []
    barra.anio_cambiado.connect(emitidos.append)
    # El debounce real es de 150 ms; acá lo colapsamos a 0 para no dormir.
    barra._timer_emision.setInterval(0)

    barra.ir_a_anio(TopBar.ANIO_MIN - 50)
    assert barra.anio_actual == TopBar.ANIO_MIN
    assert barra.campo_anio.text() == str(TopBar.ANIO_MIN)
    assert not barra.boton_anio_anterior.isEnabled()
    # El campo y los botones se actualizan en el acto; lo que se posterga es
    # sólo la emisión que dispara la carga de datos.
    assert emitidos == []
    _app.processEvents()

    barra.ir_a_anio(TopBar.ANIO_MAX + 50)
    assert barra.anio_actual == TopBar.ANIO_MAX
    assert not barra.boton_anio_siguiente.isEnabled()
    _app.processEvents()

    assert emitidos == [TopBar.ANIO_MIN, TopBar.ANIO_MAX]


def test_el_debounce_colapsa_una_rafaga_en_una_sola_carga():
    """El auto-repeat del teclado dispara ~30 pulsaciones por segundo. Si cada
    una emitiera, mantener la flecha apretada arrancaba un QThread y una carga
    de datos por año recorrido."""
    barra = TopBar()
    emitidos = []
    barra.anio_cambiado.connect(emitidos.append)
    barra._timer_emision.setInterval(0)

    for _ in range(10):
        barra._anio_anterior()
    assert emitidos == [], "emitió durante la ráfaga"

    _app.processEvents()
    assert emitidos == [TopBar.ANIO_MAX - 10], emitidos


def test_el_calendario_no_trae_los_tests_de_pretemporada():
    """Los tests de pretemporada vienen con RoundNumber 0, y
    get_session(year, 0, ...) tira 'Cannot get testing event by round number!':
    todos los botones de sesión de esas tarjetas terminaban en error."""
    import workers.calendar_worker as cw

    llamadas = []
    original = cw.fastf1.get_event_schedule
    cw.fastf1.get_event_schedule = lambda year, **kw: llamadas.append((year, kw)) or "df"
    try:
        worker = cw.CalendarWorker(2026)
        emitidos = []
        worker.terminado.connect(emitidos.append)
        worker.run()
    finally:
        cw.fastf1.get_event_schedule = original

    assert llamadas == [(2026, {"include_testing": False})], llamadas
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
            assert vista.grid.count() == CARRERAS_POR_ANIO[year]
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


if __name__ == "__main__":
    test_ir_a_anio_clampea_los_dos_extremos()
    test_el_debounce_colapsa_una_rafaga_en_una_sola_carga()
    test_el_calendario_no_trae_los_tests_de_pretemporada()
    test_mapa_tardio_de_otro_circuito_se_descarta()
    test_el_mapa_no_se_re_escala_si_el_tamano_no_cambio()
    test_calcular_columnas_nunca_devuelve_cero()
    test_todos_los_alias_apuntan_a_un_circuito_real()
    test_distancia_coherente_con_longitud_por_vueltas()
    test_cambiar_de_anio_no_deja_tarjetas_del_anio_anterior()
    test_el_cache_de_anios_tiene_tope()
    test_las_tarjetas_nunca_se_muestran_como_ventana()
    print("ok")
