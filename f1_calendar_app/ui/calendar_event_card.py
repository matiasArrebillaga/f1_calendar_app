from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt

class CalendarEventCard(QWidget):
    clickeada = Signal(int)

    def __init__(self, indice_fila, evento, color_fondo):
        super().__init__()
        self.indice_fila = indice_fila

        self.setObjectName("tarjetaEvento")
        self.setAttribute(Qt.WA_StyledBackground, True)  # ← esta línea es la clave
        self.setStyleSheet(
            f"#tarjetaEvento {{ background-color: {color_fondo.name()}; "
            f"border: 1px solid black; border-radius: 6px; }}"
        )
        self.setFixedSize(180, 90)
        self.setCursor(Qt.PointingHandCursor)

        nombre = QLabel(str(evento['EventName']))
        nombre.setStyleSheet("font-weight: bold; background: transparent;")

        pais = QLabel(str(evento['Country']))
        pais.setStyleSheet("background: transparent;")

        fecha = QLabel(str(evento['EventDate'].date()))
        fecha.setStyleSheet("background: transparent; color: #cccccc;")

        layout = QVBoxLayout()
        layout.addWidget(nombre)
        layout.addWidget(pais)
        layout.addWidget(fecha)
        layout.addStretch()
        self.setLayout(layout)

    def mousePressEvent(self, evento_mouse):
        self.clickeada.emit(self.indice_fila)