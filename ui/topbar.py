from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal, Qt
from datetime import datetime

class TopBar(QWidget):
    logo_clickeado = Signal()
    anio_cambiado = Signal(int)

    ANIO_MIN = 1950
    ANIO_MAX = datetime.now().year

    def __init__(self):
        super().__init__()
        self.anio_actual = self.ANIO_MAX

        boton_logo = QPushButton("F1")
        boton_logo.setFixedWidth(60)
        boton_logo.clicked.connect(self.logo_clickeado.emit)

        titulo_app = QLabel("F1 Calendar App")
        titulo_app.setObjectName("tituloApp")

        self.boton_anio_anterior = QPushButton("<")
        self.boton_anio_siguiente = QPushButton(">")
        self.campo_anio = QLineEdit(str(self.anio_actual))
        self.campo_anio.setAlignment(Qt.AlignCenter)
        self.campo_anio.setFixedWidth(60)
        self.campo_anio.setValidator(QIntValidator(self.ANIO_MIN, self.ANIO_MAX))

        self.boton_anio_anterior.setFixedWidth(36)
        self.boton_anio_siguiente.setFixedWidth(36)

        # --- Sección izquierda: logo + título, pegados a la izquierda ---
        seccion_izquierda = QWidget()
        layout_izquierda = QHBoxLayout(seccion_izquierda)
        layout_izquierda.setContentsMargins(0, 0, 0, 0)
        layout_izquierda.addWidget(boton_logo)
        layout_izquierda.addWidget(titulo_app)
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

        # --- Sección derecha: vacía por ahora, balancea visualmente a la izquierda ---
        seccion_derecha = QWidget()

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

    def _ir_a_anio(self, nuevo_anio):
        self.anio_actual = nuevo_anio
        self.campo_anio.setText(str(self.anio_actual))
        self._actualizar_botones()
        self.anio_cambiado.emit(self.anio_actual)

    def _actualizar_botones(self):
        self.boton_anio_anterior.setEnabled(self.anio_actual > self.ANIO_MIN)
        self.boton_anio_siguiente.setEnabled(self.anio_actual < self.ANIO_MAX)