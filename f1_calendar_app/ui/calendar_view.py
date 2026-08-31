from datetime import datetime
import fastf1
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QScrollArea, QGridLayout
)
from PySide6.QtGui import QColor, QIntValidator
from PySide6.QtCore import Signal, Qt

from ui.calendar_event_card import CalendarEventCard

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    COLOR_PASADO = QColor("#54190a")
    COLOR_FUTURO = QColor("#313333")
    COLOR_PROXIMA = QColor("#524a03")

    COLUMNAS_GRID = 5
    ANIO_MIN = 1950
    ANIO_MAX = datetime.now().year

    def __init__(self):
        super().__init__()
        self.calendario = None
        self.anio_actual = self.ANIO_MAX

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

        self.contenedor_grid = QWidget()
        self.grid = QGridLayout()
        self.contenedor_grid.setLayout(self.grid)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.contenedor_grid)
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

        for fila, (indice_pandas, evento) in enumerate(self.calendario.iterrows()):
            if indice_pandas == indice_proxima:
                color = self.COLOR_PROXIMA
            elif evento['EventDate'] < hoy:
                color = self.COLOR_PASADO
            else:
                color = self.COLOR_FUTURO

            tarjeta = CalendarEventCard(fila, evento, color)
            tarjeta.clickeada.connect(self.evento_seleccionado.emit)

            fila_grid = fila // self.COLUMNAS_GRID
            col_grid = fila % self.COLUMNAS_GRID
            self.grid.addWidget(tarjeta, fila_grid, col_grid)