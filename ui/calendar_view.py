import fastf1
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from ui.calendar_event_card import CalendarEventCard

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    ANCHO_TARJETA = 190
    ESPACIADO = 10
    RESERVA_LATERAL = 0

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.calendario = None
        self._tarjetas = []
        self._columnas_actual = None

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

        layout = QVBoxLayout()
        layout.addWidget(self.scroll)
        self.setLayout(layout)

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

        self._columnas_actual = None
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