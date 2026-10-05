from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal, Qt, QSize, QTimer
from datetime import datetime

from ui.icons import icono, MUTED


class SelectorTemporada(QFrame):
    """Año que se está mirando. Vive arriba de la sidebar: la temporada es el
    contexto de las tres vistas, no de una sola."""
    anio_cambiado = Signal(int)

    ANIO_MIN = 1950
    ANIO_MAX = datetime.now().year

    # El auto-repeat del teclado dispara ~30 pulsaciones por segundo: sin esto,
    # mantener una flecha apretada arrancaba un QThread (y una carga) por año.
    RETARDO_EMISION_MS = 150

    def __init__(self):
        super().__init__()
        self.setObjectName("selectorTemporada")
        self.anio_actual = self.ANIO_MAX

        etiqueta = QLabel("TEMPORADA")
        etiqueta.setObjectName("etiquetaRonda")

        self.boton_anio_anterior = QPushButton()
        self.boton_anio_siguiente = QPushButton()
        for boton, nombre_icono in ((self.boton_anio_anterior, "chevron-left"),
                                    (self.boton_anio_siguiente, "chevron-right")):
            boton.setObjectName("botonAnio")
            boton.setIcon(icono(nombre_icono, MUTED, 14))
            boton.setIconSize(QSize(14, 14))
            boton.setFixedSize(28, 28)
            boton.setCursor(Qt.PointingHandCursor)
        self.boton_anio_anterior.setToolTip("Año anterior (←)")
        self.boton_anio_siguiente.setToolTip("Año siguiente (→)")

        self.campo_anio = QLineEdit(str(self.anio_actual))
        self.campo_anio.setObjectName("campoAnio")
        self.campo_anio.setAlignment(Qt.AlignCenter)
        self.campo_anio.setFixedWidth(72)
        self.campo_anio.setValidator(QIntValidator(self.ANIO_MIN, self.ANIO_MAX))
        self.campo_anio.setToolTip(f"Año entre {self.ANIO_MIN} y {self.ANIO_MAX}")

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.boton_anio_anterior)
        fila.addStretch()
        fila.addWidget(self.campo_anio)
        fila.addStretch()
        fila.addWidget(self.boton_anio_siguiente)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(etiqueta)
        layout.addLayout(fila)

        self.boton_anio_anterior.clicked.connect(self._anio_anterior)
        self.boton_anio_siguiente.clicked.connect(self._anio_siguiente)
        self.campo_anio.editingFinished.connect(self._anio_escrito_manualmente)

        self._timer_emision = QTimer(self)
        self._timer_emision.setSingleShot(True)
        self._timer_emision.setInterval(self.RETARDO_EMISION_MS)
        self._timer_emision.timeout.connect(
            lambda: self.anio_cambiado.emit(self.anio_actual)
        )

        self._actualizar_botones()

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
        # Debounce: el último año gana. La UI (campo y botones) ya se actualizó,
        # lo que se posterga es sólo la carga de datos.
        self._timer_emision.start()

    def _actualizar_botones(self):
        self.boton_anio_anterior.setEnabled(self.anio_actual > self.ANIO_MIN)
        self.boton_anio_siguiente.setEnabled(self.anio_actual < self.ANIO_MAX)
