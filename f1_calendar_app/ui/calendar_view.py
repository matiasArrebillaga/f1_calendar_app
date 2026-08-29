import fastf1
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PySide6.QtCore import Signal

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)

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

        for fila, (_, evento) in enumerate(self.calendario.iterrows()):
            for col, nombre_col in enumerate(columnas):
                item = QTableWidgetItem(str(evento[nombre_col]))
                self.tabla.setItem(fila, col, item)

        self.tabla.resizeColumnsToContents()

    def _on_double_click(self, fila, columna):
        self.evento_seleccionado.emit(fila)