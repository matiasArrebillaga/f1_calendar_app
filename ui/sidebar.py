from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal

class Sidebar(QWidget):
    navegar = Signal(str)  # emite "calendario" o "standings"

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)

        self.boton_calendario = QPushButton("CALENDAR")
        self.boton_standings = QPushButton("STANDINGS")

        for boton in (self.boton_calendario, self.boton_standings):
            boton.setCheckable(True)

        self.boton_calendario.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(self.boton_calendario)
        layout.addWidget(self.boton_standings)
        layout.addStretch()
        self.setLayout(layout)

        self.boton_calendario.clicked.connect(lambda: self._seleccionar("calendario"))
        self.boton_standings.clicked.connect(lambda: self._seleccionar("standings"))

    def _seleccionar(self, destino):
        self.boton_calendario.setChecked(destino == "calendario")
        self.boton_standings.setChecked(destino == "standings")
        self.navegar.emit(destino)

    def marcar_calendario(self):
        self._seleccionar("calendario")