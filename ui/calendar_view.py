from collections import OrderedDict

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QLabel,
    QGraphicsOpacityEffect, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QPoint

from core.fechas import MESES, largada
from ui.calendar_event_card import CalendarEventCard
from ui.proxima_carrera import ProximaCarrera
from ui.spinner_widget import SpinnerWidget
from workers.calendar_worker import CalendarWorker

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    ANCHO_TARJETA = 200
    ESPACIADO = 10
    RESERVA_LATERAL = 0

    RETARDO_ENTRADA = 18   # ms entre la entrada de una tarjeta y la siguiente
    MAX_ESCALONES = 12     # tope: una temporada de 24 carreras no tarda 2s

    MAX_ANIOS_CACHEADOS = 5

    # Una carrera sigue siendo "la próxima" hasta un rato después de largar:
    # el día de la carrera, a las 9 de la mañana, todavía no terminó.
    DURACION_CARRERA = pd.Timedelta(hours=2)
    # Alto aproximado de un mes con una fila de tarjetas. El scroll deja ese
    # margen libre al final para que hasta el último mes pueda quedar arriba.
    ALTO_FILA_MES = 160

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.calendario = None
        self._tarjetas = []
        # Tarjetas y encabezados de mes en el orden en que van en el grid.
        self._orden = []
        self._encabezados = []   # [(mes, QLabel)], para saber adónde scrollear
        self._columnas_actual = None
        # {year: (calendario, orden, encabezados)} — el DataFrame va junto con
        # los widgets porque MainWindow resuelve el click con
        # self.calendario.iloc[fila]. OrderedDict para poder desalojar por LRU.
        self._cache_por_anio = OrderedDict()
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash
        self._year_actual = None
        self._recien_cargado = False
        self._animaciones_entrada = []

        # --- Fijo arriba: encabezado + próxima carrera ---
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("etiquetaRonda")
        titulo = QLabel("Calendario")
        titulo.setObjectName("titulo")
        columna_titulo = QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(self.eyebrow)
        columna_titulo.addWidget(titulo)

        self.texto_progreso = QLabel()
        self.texto_progreso.setObjectName("textoProgreso")
        self.progreso = QProgressBar()
        self.progreso.setObjectName("progresoTemporada")
        self.progreso.setTextVisible(False)
        self.progreso.setFixedSize(220, 4)
        columna_progreso = QVBoxLayout()
        columna_progreso.setSpacing(6)
        columna_progreso.addStretch()
        columna_progreso.addWidget(self.texto_progreso)
        columna_progreso.addWidget(self.progreso)

        encabezado = QHBoxLayout()
        encabezado.addLayout(columna_titulo)
        encabezado.addStretch()
        encabezado.addLayout(columna_progreso)

        self.bloque_proxima = ProximaCarrera()
        self.bloque_proxima.clickeada.connect(self.evento_seleccionado.emit)
        self.bloque_proxima.hide()

        # --- Lo que scrollea: los meses ---
        self.contenedor_grid = QWidget()
        self.grid = QGridLayout(self.contenedor_grid)
        self.grid.setHorizontalSpacing(self.ESPACIADO)
        self.grid.setVerticalSpacing(4)
        self.grid.setContentsMargins(0, 0, 0, 0)

        wrapper = QWidget()
        layout_wrapper = QHBoxLayout(wrapper)
        layout_wrapper.setContentsMargins(0, 0, 0, 16)
        self._layout_wrapper = layout_wrapper
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
        layout_estado.setContentsMargins(0, 0, 0, 0)
        layout_estado.addWidget(self.spinner)
        layout_estado.addWidget(self.estado)
        layout_estado.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 16, 0)
        layout.setSpacing(12)
        layout.addLayout(encabezado)
        layout.addLayout(layout_estado)
        layout.addWidget(self.bloque_proxima)
        layout.addWidget(self.scroll, 1)
        self.setLayout(layout)

    def cargar_calendario(self, year):
        self._year_actual = year
        self.eyebrow.setText(f"TEMPORADA {year}")

        # Lo del año que sale se oculta y sale del grid SIN destruirse: si
        # pertenece a un año cacheado tiene que sobrevivir para reusarse.
        #
        # Esto va ANTES del chequeo de caché. Si solo se hace en el camino que
        # va a la red, al volver a un año ya visitado las tarjetas viejas
        # quedan visibles: salen del layout pero siguen pintadas donde estaban,
        # así que se ven dos (o tres) años superpuestos y parece que el
        # calendario no se actualizó.
        for widget in self._orden:
            widget.hide()
        while self.grid.count():
            self.grid.takeAt(0)
        self._tarjetas, self._orden, self._encabezados = [], [], []

        if year in self._cache_por_anio:
            self._cache_por_anio.move_to_end(year)
            self._set_estado("")
            self.spinner.detener()
            self.calendario, orden, encabezados = self._cache_por_anio[year]
            self._montar(orden, encabezados, animar=False)
            return

        self.bloque_proxima.ocultar()
        self._actualizar_progreso(None)
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

        terminadas = self._terminadas(calendario)
        pendientes = calendario.index[~terminadas]
        indice_proxima = pendientes.min() if len(pendientes) else None

        orden, encabezados = [], []
        meses = calendario['EventDate'].dt.month
        for fila, (indice_pandas, evento) in enumerate(calendario.iterrows()):
            mes = evento['EventDate'].month
            if not encabezados or encabezados[-1][0] != mes:
                cantidad = int((meses == mes).sum())
                encabezado = QLabel(
                    f"{MESES[mes - 1]}   ·   {cantidad} {'carrera' if cantidad == 1 else 'carreras'}")
                encabezado.setObjectName("encabezadoMes")
                encabezados.append((mes, encabezado))
                orden.append(encabezado)

            if indice_pandas == indice_proxima:
                estado = 'proxima'
            elif terminadas[indice_pandas]:
                estado = 'pasado'
            else:
                estado = 'futuro'

            tarjeta = CalendarEventCard(fila, evento, estado)
            tarjeta.clickeada.connect(self.evento_seleccionado.emit)
            orden.append(tarjeta)

        self._cache_por_anio[worker.year] = (calendario, orden, encabezados)
        self._recortar_cache()
        self._montar(orden, encabezados, animar=True)

    def _recortar_cache(self):
        """Tope de años en memoria. Cada año guarda su DataFrame y ~24
        tarjetas, y cada tarjeta es un QWidget con 5 hijos, un drop shadow y dos
        animaciones: recorrer de 1950 a hoy con las flechas dejaba más de mil
        tarjetas vivas. El año actual es siempre el último insertado, así que
        nunca es el que se desaloja."""
        while len(self._cache_por_anio) > self.MAX_ANIOS_CACHEADOS:
            _, (_, orden, _) = self._cache_por_anio.popitem(last=False)
            for widget in orden:
                widget.deleteLater()

    def _on_error(self, mensaje):
        worker = self.sender()
        if worker.year != self._year_actual:
            return
        self.spinner.detener()
        self._set_estado(f"No se pudo cargar el calendario: {mensaje}", "error")

    def _montar(self, orden, encabezados, animar):
        self._orden = orden
        self._encabezados = encabezados
        self._tarjetas = [w for w in orden if isinstance(w, CalendarEventCard)]
        self._columnas_actual = None
        self._recien_cargado = animar

        # El grid PRIMERO: los widgets nacen sin padre, y uno sin padre que
        # recibe show() se convierte en ventana top-level — una por evento
        # parpadeando en el centro de la pantalla. grid.addWidget() los
        # reparenta a contenedor_grid, y recién entonces show() los muestra
        # dentro de la vista.
        self._reorganizar_grid()

        # Hace falta igual: los que vienen del caché fueron ocultados con hide()
        # explícito, y addWidget no revierte un hide() explícito.
        for widget in self._orden:
            widget.show()

        self._actualizar_progreso(self.calendario)
        self._actualizar_proxima()
        # En el próximo ciclo: recién ahí el layout tiene las posiciones reales.
        QTimer.singleShot(0, self._ir_al_mes_actual)

    def _actualizar_progreso(self, calendario):
        if calendario is None or calendario.empty:
            self.texto_progreso.setText("")
            self.progreso.hide()
            return
        total = len(calendario)
        disputadas = int(self._terminadas(calendario).sum())
        self.texto_progreso.setText(f"Carreras disputadas   <b>{disputadas}</b> / {total}")
        self.progreso.setRange(0, total)
        self.progreso.setValue(disputadas)
        self.progreso.show()

    def _terminadas(self, calendario):
        """Serie booleana: qué carreras ya terminaron (largada + duración)."""
        fines = calendario.apply(largada, axis=1) + self.DURACION_CARRERA
        return fines < pd.Timestamp.now()

    def _ajustar_margen_final(self):
        self._layout_wrapper.setContentsMargins(
            0, 0, 0, max(16, self.scroll.viewport().height() - self.ALTO_FILA_MES))

    def _actualizar_proxima(self):
        proxima = next((t for t in self._tarjetas if t.estado == 'proxima'), None)
        if proxima is None:
            self.bloque_proxima.ocultar()
            return
        self.bloque_proxima.mostrar(proxima.indice_fila,
                                    self.calendario.iloc[proxima.indice_fila])
        self.bloque_proxima.show()

    def mes_destino(self, hoy=None):
        """Mes en el que abre el calendario: el actual (o el próximo con
        carreras, si en este no hay) en la temporada en curso; el último si la
        temporada ya terminó; el primero en cualquier otro año."""
        if not self._encabezados:
            return None
        hoy = hoy if hoy is not None else pd.Timestamp.now()
        if self._year_actual != hoy.year:
            return self._encabezados[0][0]
        return next((mes for mes, _ in self._encabezados if mes >= hoy.month),
                    self._encabezados[-1][0])

    def _ir_al_mes_actual(self, hoy=None):
        mes = self.mes_destino(hoy)
        if mes is None:
            return
        encabezado = dict(self._encabezados)[mes]
        self._ajustar_margen_final()
        self.scroll.widget().layout().activate()
        self.scroll.verticalScrollBar().setValue(
            encabezado.mapTo(self.scroll.widget(), QPoint(0, 0)).y())

    def _set_estado(self, texto, tipo=""):
        nombres = {
            "": "estadoVacio",
            "cargando": "estadoCargando",
            "error": "estadoError",
            "vacio": "estadoVacio",
        }
        self.estado.setObjectName(nombres.get(tipo, "estadoVacio"))
        self.estado.setText(texto)
        self.estado.setVisible(bool(texto))
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)

    def _calcular_columnas(self):
        ancho_disponible = self.scroll.viewport().width() - self.RESERVA_LATERAL
        ancho_por_tarjeta = self.ANCHO_TARJETA + self.ESPACIADO
        return max(1, ancho_disponible // ancho_por_tarjeta)

    def _reorganizar_grid(self):
        if not self._orden:
            return

        columnas = self._calcular_columnas()
        if columnas == self._columnas_actual:
            return
        self._columnas_actual = columnas

        while self.grid.count():
            self.grid.takeAt(0)

        # Cada mes arranca en una fila propia: su encabezado ocupa todo el ancho
        # y sus tarjetas van debajo, `columnas` por fila.
        fila, col = 0, 0
        for widget in self._orden:
            if isinstance(widget, CalendarEventCard):
                self.grid.addWidget(widget, fila, col)
                col += 1
                if col == columnas:
                    fila, col = fila + 1, 0
            else:
                if col:
                    fila, col = fila + 1, 0
                self.grid.addWidget(widget, fila, 0, 1, columnas)
                fila += 1

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
        self._ajustar_margen_final()
        self._reorganizar_grid()

    def showEvent(self, event):
        super().showEvent(event)
        self._reorganizar_grid()
