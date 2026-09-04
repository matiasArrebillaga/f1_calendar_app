from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal, Qt
from datetime import datetime
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Signal, Qt, QSize
import sys
import os

def resource_path(ruta_relativa):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, ruta_relativa)
class TopBar(QWidget):
    logo_clickeado = Signal()
    anio_cambiado = Signal(int)

    ANIO_MIN = 1950
    ANIO_MAX = datetime.now().year

    def __init__(self):
        super().__init__()
        self.setObjectName("topBar")
        self.anio_actual = self.ANIO_MAX

        self.boton_logo = QPushButton()
        self.boton_logo.setFixedSize(55, 55)
        self.boton_logo.setIcon(QIcon(resource_path("assets/logo.png")))
        self.boton_logo.setIconSize(QSize(55, 55))
        self.boton_logo.setCursor(Qt.PointingHandCursor)
        self.boton_logo.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                background-color: transparent;
            }
        """)
        self.boton_logo.clicked.connect(self.logo_clickeado)

        titulo_app = QLabel("CALENDARIO F1")
        titulo_app.setObjectName("tituloApp")

        self.boton_anio_anterior = QPushButton("<")
        self.boton_anio_siguiente = QPushButton(">")
        self.campo_anio = QLineEdit(str(self.anio_actual))
        self.campo_anio.setAlignment(Qt.AlignCenter)
        self.campo_anio.setFixedWidth(60)
        self.campo_anio.setValidator(QIntValidator(self.ANIO_MIN, self.ANIO_MAX))

        self.boton_anio_anterior.setFixedWidth(36)
        self.boton_anio_siguiente.setFixedWidth(36)

        # --- Sección izquierda: logo, pegado a la izquierda ---
        seccion_izquierda = QWidget()
        layout_izquierda = QHBoxLayout(seccion_izquierda)
        layout_izquierda.setContentsMargins(0, 0, 0, 0)
        layout_izquierda.addWidget(self.boton_logo)
        layout_izquierda.addStretch()

        # --- Sección central: selector de año, centrado dentro de su propia columna ---
        seccion_centro = QWidget()
        layout_centro = QHBoxLayout(seccion_centro)
        layout_centro.setContentsMargins(0, 0, 0, 0)
        layout_centro.addStretch()
        layout_centro.addWidget(self.boton_anio_anterior)
        layout_centro.addWidget(self.campo_anio)
        layout_centro.addWidget(self.boton_anio_siguiente)
        layout_centro.addStretch()

        # --- Sección derecha: título, pegado a la derecha ---
        seccion_derecha = QWidget()
        layout_derecha = QHBoxLayout(seccion_derecha)
        layout_derecha.setContentsMargins(0, 0, 0, 0)
        layout_derecha.addStretch()
        layout_derecha.addWidget(titulo_app)

        layout = QHBoxLayout()
        layout.addWidget(seccion_izquierda, 1)
        layout.addWidget(seccion_centro, 1)
        layout.addWidget(seccion_derecha, 1)
        self.setLayout(layout)

        self.boton_anio_anterior.clicked.connect(self._anio_anterior)
        self.boton_anio_siguiente.clicked.connect(self._anio_siguiente)
        self.campo_anio.editingFinished.connect(self._anio_escrito_manualmente)

        self._actualizar_botones()

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
        anio_pedido = max(self.ANIO_MIN, min(int(texto), self.ANIO_MAX))
        self._ir_a_anio(anio_pedido)

    def _anio_anterior(self):
        if self.anio_actual > self.ANIO_MIN:
            self.ir_a_anio(self.anio_actual - 1)

    def _anio_siguiente(self):
        if self.anio_actual < self.ANIO_MAX:
            self.ir_a_anio(self.anio_actual + 1)

    def _anio_escrito_manualmente(self):
        texto = self.campo_anio.text()
        if not texto:
            self.campo_anio.setText(str(self.anio_actual))
            return
        self.ir_a_anio(int(texto))

    def ir_a_anio(self, nuevo_anio):
        nuevo_anio = max(self.ANIO_MIN, min(nuevo_anio, self.ANIO_MAX))
        self.anio_actual = nuevo_anio
        self.campo_anio.setText(str(self.anio_actual))
        self._actualizar_botones()
        self.anio_cambiado.emit(self.anio_actual)

    def _actualizar_botones(self):
        self.boton_anio_anterior.setEnabled(self.anio_actual > self.ANIO_MIN)
        self.boton_anio_siguiente.setEnabled(self.anio_actual < self.ANIO_MAX)