from datetime import datetime
import fastf1
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QScrollArea, QGridLayout
)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal, Qt

from ui.calendar_event_card import CalendarEventCard

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    ANIO_MIN = 1950
    ANIO_MAX = datetime.now().year

    ANCHO_TARJETA = 190
    ESPACIADO = 10          # tarjetas más juntas entre sí
    RESERVA_LATERAL = 110   # espacio que se deja libre a la derecha para la futura barra de opciones

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.calendario = None
        self.anio_actual = self.ANIO_MAX
        self._tarjetas = []
        self._columnas_actual = None

        self.boton_anio_anterior = QPushButton("<")
        self.boton_anio_siguiente = QPushButton(">")

        self.campo_anio = QLineEdit(str(self.anio_actual))
        self.campo_anio.setAlignment(Qt.AlignCenter)
        self.campo_anio.setFixedWidth(60)
        self.campo_anio.setValidator(QIntValidator(self.ANIO_MIN, self.ANIO_MAX))

        self.boton_anio_anterior.setFixedWidth(36)
        self.boton_anio_siguiente.setFixedWidth(36)

        layout_superior = QHBoxLayout()
        layout_superior.addStretch()
        layout_superior.addWidget(self.boton_anio_anterior)
        layout_superior.addWidget(self.campo_anio)
        layout_superior.addWidget(self.boton_anio_siguiente)
        layout_superior.addStretch()

        # El grid vive en un contenedor que solo ocupa el ancho que
        # realmente necesita (según cuántas columnas entren); el resto del
        # espacio a la derecha queda libre para la futura barra lateral.
        self.contenedor_grid = QWidget()
        self.grid = QGridLayout(self.contenedor_grid)
        self.grid.setSpacing(self.ESPACIADO)
        self.grid.setContentsMargins(0, 0, 0, 0)

        wrapper = QWidget()
        layout_wrapper = QHBoxLayout(wrapper)
        layout_wrapper.setContentsMargins(6, 10, 6, 10)
        layout_wrapper.addStretch()
        layout_wrapper.addWidget(self.contenedor_grid, alignment=Qt.AlignTop | Qt.AlignLeft)

        self.scroll = QScrollArea()
        self.scroll.setWidget(wrapper)
        self.scroll.setWidgetResizable(True)

        layout = QVBoxLayout()
        layout.addLayout(layout_superior)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.boton_anio_anterior.clicked.connect(self._anio_anterior)
        self.boton_anio_siguiente.clicked.connect(self._anio_siguiente)
        self.campo_anio.editingFinished.connect(self._anio_escrito_manualmente)

        self._actualizar_botones()
        self.cargar_calendario(self.anio_actual)

    def _anio_anterior(self):
        if self.anio_actual > self.ANIO_MIN:
            self._ir_a_anio(self.anio_actual - 1)

    def _anio_siguiente(self):
        if self.anio_actual < self.ANIO_MAX:
            self._ir_a_anio(self.anio_actual + 1)

    def _anio_escrito_manualmente(self):
        texto = self.campo_anio.text()
        if not texto:
            self.campo_anio.setText(str(self.anio_actual))
            return

        anio_pedido = int(texto)
        anio_pedido = max(self.ANIO_MIN, min(anio_pedido, self.ANIO_MAX))
        self._ir_a_anio(anio_pedido)

    def _ir_a_anio(self, nuevo_anio):
        self.anio_actual = nuevo_anio
        self.campo_anio.setText(str(self.anio_actual))
        self._actualizar_botones()
        self.cargar_calendario(self.anio_actual)

    def _actualizar_botones(self):
        self.boton_anio_anterior.setEnabled(self.anio_actual > self.ANIO_MIN)
        self.boton_anio_siguiente.setEnabled(self.anio_actual < self.ANIO_MAX)

    def cargar_calendario(self, year):
        self.calendario = fastf1.get_event_schedule(year)

        while self.grid.count():
            item = self.grid.takeAt(0)
            item.widget().deleteLater()

        hoy = pd.Timestamp.now()
        fechas_futuras = self.calendario[self.calendario['EventDate'] >= hoy]
        indice_proxima = fechas_futuras.index.min() if not fechas_futuras.empty else None

        self._tarjetas = []
        for fila, (indice_pandas, evento) in enumerate(self.calendario.iterrows()):
            if indice_pandas == indice_proxima:
                estado = 'proxima'
            elif evento['EventDate'] < hoy:
                estado = 'pasado'
            else:
                estado = 'futuro'

            tarjeta = CalendarEventCard(fila, evento, estado)
            tarjeta.clickeada.connect(self.evento_seleccionado.emit)
            self._tarjetas.append(tarjeta)

        self._columnas_actual = None  # fuerza un reacomodo aunque el número de columnas no cambie
        self._reorganizar_grid()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reorganizar_grid()

    def showEvent(self, event):
        super().showEvent(event)
        self._reorganizar_grid()
