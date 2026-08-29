import fastf1
import pandas as pd
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

    COLOR_PASADO = QColor("#54190a")   # gris claro
    COLOR_FUTURO = QColor("#313333") 
    COLOR_PROXIMA = QColor("#524a03")  # celeste claro

    def __init__(self):
        super().__init__()
        self.calendario = None

        self.selector_anio = QComboBox()
        self.selector_anio.addItems([str(a) for a in range(2018, 2027)])
        self.selector_anio.setCurrentText("2026")

        self.tabla = QTableWidget()

        layout_superior = QHBoxLayout()
        layout_superior.addWidget(QLabel("Año:"))
        layout_superior.addWidget(self.selector_anio)
        layout_superior.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(layout_superior)
        layout.addWidget(self.tabla)
        self.setLayout(layout)

        self.tabla.cellDoubleClicked.connect(self._on_double_click)
        self.selector_anio.currentTextChanged.connect(self._on_anio_cambiado)

        self.cargar_calendario(2026)

    def _on_anio_cambiado(self, texto_anio):
        self.cargar_calendario(int(texto_anio))

    def cargar_calendario(self, year):
        self.calendario = fastf1.get_event_schedule(year)

        columnas = ['RoundNumber', 'EventName', 'Country', 'EventDate']
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.setRowCount(len(self.calendario))

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

            for col, nombre_col in enumerate(columnas):
                item = QTableWidgetItem(str(evento[nombre_col]))
                item.setBackground(color)
                self.tabla.setItem(fila, col, item)

    def _on_double_click(self, fila, columna):
        self.evento_seleccionado.emit(fila)