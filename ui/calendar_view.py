from collections import OrderedDict

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QLabel,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve

from ui.calendar_event_card import CalendarEventCard
from ui.spinner_widget import SpinnerWidget
from workers.calendar_worker import CalendarWorker

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    ANCHO_TARJETA = 190
    ESPACIADO = 10
    RESERVA_LATERAL = 0

    RETARDO_ENTRADA = 18   # ms entre la entrada de una tarjeta y la siguiente
    MAX_ESCALONES = 12     # tope: una temporada de 24 carreras no tarda 2s

    MAX_ANIOS_CACHEADOS = 5

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.calendario = None
        self._tarjetas = []
        self._columnas_actual = None
        # {year: (calendario, tarjetas)} — el DataFrame va junto con las
        # tarjetas porque MainWindow resuelve el click con
        # self.calendario.iloc[fila]. OrderedDict para poder desalojar por LRU.
        self._cache_por_anio = OrderedDict()
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash
        self._year_actual = None
        self._recien_cargado = False
        self._animaciones_entrada = []

        self.contenedor_grid = QWidget()
        self.grid = QGridLayout(self.contenedor_grid)
        self.grid.setSpacing(self.ESPACIADO)
        self.grid.setContentsMargins(0, 0, 0, 0)

        wrapper = QWidget()
        layout_wrapper = QHBoxLayout(wrapper)
        layout_wrapper.setContentsMargins(6, 10, 6, 10)
        layout_wrapper.addWidget(self.contenedor_grid, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout_wrapper.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidget(wrapper)
        self.scroll.setWidgetResizable(True)
        # El grid se recalcula para entrar a lo ancho, así que no hay scroll
        # horizontal que hacer — y si existiera, se comería las flechas
        # izquierda/derecha que MainWindow usa para cambiar de año.
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.spinner = SpinnerWidget(tamano=18)
        self.spinner.hide()
        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")

        layout_estado = QHBoxLayout()
        layout_estado.setContentsMargins(12, 8, 12, 0)
        layout_estado.addWidget(self.spinner)
        layout_estado.addWidget(self.estado)
        layout_estado.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(layout_estado)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def cargar_calendario(self, year):
        self._year_actual = year

        # Las tarjetas del año que sale se ocultan y salen del grid SIN
        # destruirse: si pertenecen a un año cacheado tienen que sobrevivir
        # para reusarse después.
        #
        # Esto va ANTES del chequeo de caché. Si solo se hace en el camino que
        # va a la red, al volver a un año ya visitado las tarjetas viejas
        # quedan visibles: salen del layout pero siguen pintadas donde estaban,
        # así que se ven dos (o tres) años superpuestos y parece que el
        # calendario no se actualizó.
        for tarjeta in self._tarjetas:
            tarjeta.hide()
        while self.grid.count():
            self.grid.takeAt(0)
        self._tarjetas = []

        if year in self._cache_por_anio:
            self._cache_por_anio.move_to_end(year)
            self._set_estado("")
            self.spinner.detener()
            self.calendario, tarjetas = self._cache_por_anio[year]
            self._montar_tarjetas(tarjetas, animar=False)
            return

        self._set_estado(f"Cargando calendario {year}...", "cargando")
        self.spinner.iniciar()

        worker = CalendarWorker(year)
        worker.terminado.connect(self._on_calendario_cargado)
        worker.error.connect(self._on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def _on_calendario_cargado(self, calendario):
        worker = self.sender()
        if worker.year != self._year_actual:
            return  # llegó tarde: el usuario ya cambió de año

        self.spinner.detener()
        self._set_estado("")
        self.calendario = calendario

        if calendario is None or calendario.empty:
            self._set_estado(f"No hay calendario disponible para {worker.year}.", "vacio")
            return

        hoy = pd.Timestamp.now()
        fechas_futuras = calendario[calendario['EventDate'] >= hoy]
        indice_proxima = fechas_futuras.index.min() if not fechas_futuras.empty else None

        tarjetas_nuevas = []
        for fila, (indice_pandas, evento) in enumerate(calendario.iterrows()):
            if indice_pandas == indice_proxima:
                estado = 'proxima'
            elif evento['EventDate'] < hoy:
                estado = 'pasado'
            else:
                estado = 'futuro'

            tarjeta = CalendarEventCard(fila, evento, estado)
            tarjeta.clickeada.connect(self.evento_seleccionado.emit)
            tarjetas_nuevas.append(tarjeta)

        self._cache_por_anio[worker.year] = (calendario, tarjetas_nuevas)
        self._recortar_cache()
        self._montar_tarjetas(tarjetas_nuevas, animar=True)

    def _recortar_cache(self):
        """Tope de años en memoria. Cada año guarda su DataFrame y ~24
        tarjetas, y cada tarjeta es un QWidget con 5 hijos, un drop shadow y dos
        animaciones: recorrer de 1950 a hoy con las flechas dejaba más de mil
        tarjetas vivas. El año actual es siempre el último insertado, así que
        nunca es el que se desaloja."""
        while len(self._cache_por_anio) > self.MAX_ANIOS_CACHEADOS:
            _, (_, tarjetas) = self._cache_por_anio.popitem(last=False)
            for tarjeta in tarjetas:
                tarjeta.deleteLater()

    def _on_error(self, mensaje):
        worker = self.sender()
        if worker.year != self._year_actual:
            return
        self.spinner.detener()
        self._set_estado(f"No se pudo cargar el calendario: {mensaje}", "error")

    def _montar_tarjetas(self, tarjetas, animar):
        self._tarjetas = tarjetas
        self._columnas_actual = None
        self._recien_cargado = animar

        # El grid PRIMERO: las tarjetas nacen sin padre (QWidget.__init__ sin
        # argumentos), y un widget sin padre que recibe show() se convierte en
        # ventana top-level — una por evento parpadeando en el centro de la
        # pantalla. grid.addWidget() las reparenta a contenedor_grid, y recién
        # entonces show() las muestra dentro de la vista.
        self._reorganizar_grid()

        # Hace falta igual: las tarjetas que vienen del caché fueron ocultadas
        # con hide() explícito, y addWidget no revierte un hide() explícito.
        for tarjeta in self._tarjetas:
            tarjeta.show()

    def _set_estado(self, texto, tipo=""):
        nombres = {
            "": "estadoVacio",
            "cargando": "estadoCargando",
            "error": "estadoError",
            "vacio": "estadoVacio",
        }
        self.estado.setObjectName(nombres.get(tipo, "estadoVacio"))
        self.estado.setText(texto)
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)

    def _calcular_columnas(self):
        ancho_disponible = self.scroll.viewport().width() - self.RESERVA_LATERAL
        ancho_por_tarjeta = self.ANCHO_TARJETA + self.ESPACIADO
        return max(1, ancho_disponible // ancho_por_tarjeta)

    def _reorganizar_grid(self):
        if not self._tarjetas:
            return

        columnas = self._calcular_columnas()
        if columnas == self._columnas_actual:
            return
        self._columnas_actual = columnas

        while self.grid.count():
            self.grid.takeAt(0)

        for indice, tarjeta in enumerate(self._tarjetas):
            fila_grid = indice // columnas
            col_grid = indice % columnas
            self.grid.addWidget(tarjeta, fila_grid, col_grid)

        # Entrada escalonada SOLO en una carga nueva de año: _reorganizar_grid
        # también corre en cada resizeEvent, y ahí animar sería ruido.
        if self._recien_cargado:
            self._recien_cargado = False
            self._animar_entrada()

    def _animar_entrada(self):
        # ponytail: un efecto de opacidad por tarjeta (~24 en una temporada
        # completa). Si llega a trabar, animar solo las filas visibles.
        self._animaciones_entrada = []
        for indice, tarjeta in enumerate(self._tarjetas):
            efecto = QGraphicsOpacityEffect(tarjeta)
            efecto.setOpacity(0.0)
            # La tarjeta ya usa su sombra como graphicsEffect, y Qt admite uno
            # solo por widget: el fade va sobre `_interior`, que no tiene efecto.
            tarjeta._interior.setGraphicsEffect(efecto)

            animacion = QPropertyAnimation(efecto, b"opacity", self)
            animacion.setDuration(220)
            animacion.setStartValue(0.0)
            animacion.setEndValue(1.0)
            animacion.setEasingCurve(QEasingCurve.OutCubic)
            # Devolvemos el pintado nativo al terminar: el efecto fuerza render
            # por software en todo el subárbol mientras está puesto. Del efecto
            # se encarga Qt (es su dueño); la animación es hija de self, así que
            # sin el deleteLater quedarían ~24 por año cargado.
            animacion.finished.connect(
                lambda t=tarjeta, a=animacion: (
                    t._interior.setGraphicsEffect(None), a.deleteLater()
                )
            )
            self._animaciones_entrada.append(animacion)

            retardo = min(indice, self.MAX_ESCALONES) * self.RETARDO_ENTRADA
            QTimer.singleShot(retardo, animacion.start)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reorganizar_grid()

    def showEvent(self, event):
        super().showEvent(event)
        self._reorganizar_grid()
