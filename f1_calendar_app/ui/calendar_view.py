import fastf1
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout
from PySide6.QtCore import Signal

class CalendarView(QWidget):
    evento_seleccionado = Signal(int)  # emite el número de fila seleccionada

    def __init__(self):
        super().__init__()
        self.calendario = None

        self.tabla = QTableWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tabla)
        self.setLayout(layout)

        self.tabla.cellDoubleClicked.connect(self._on_double_click)
        self.cargar_calendario()

    def cargar_calendario(self):
        self.calendario = fastf1.get_event_schedule(1953)

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