from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtCore import Signal


class Sidebar(QWidget):
    navegar = Signal(str)  # emite "calendario" o "standings"

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebarPrincipal")
        self.setFixedWidth(170)

        etiqueta = QLabel("MENÚ")
        etiqueta.setObjectName("etiquetaRonda")

        self.boton_calendario = QPushButton("Calendario")
        self.boton_standings = QPushButton("Clasificación")

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)

        for boton in (self.boton_calendario, self.boton_standings):
            boton.setObjectName("navLateral")
            boton.setCheckable(True)
            boton.setMinimumHeight(44)
            self.grupo.addButton(boton)

        self.boton_calendario.setChecked(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(6)
        layout.addWidget(etiqueta)
        layout.addSpacing(6)
        layout.addWidget(self.boton_calendario)
        layout.addWidget(self.boton_standings)
        layout.addStretch()
        self.setLayout(layout)

        self.boton_calendario.clicked.connect(lambda: self.navegar.emit("calendario"))
        self.boton_standings.clicked.connect(lambda: self.navegar.emit("standings"))

    def marcar_calendario(self):
        self.boton_calendario.setChecked(True)
