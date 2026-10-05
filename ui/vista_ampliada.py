from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor


class VistaAmpliada(QDialog):
    """Capa sobre toda la ventana: fondo oscuro translúcido, un título y
    `contenido` centrado. Se cierra con Esc, con el botón Cerrar o con un clic
    fuera del contenido. La usan el mapa grande y los datos del circuito."""

    FONDO = QColor(5, 6, 8, 242)

    def __init__(self, titulo, contenido, padre):
        ventana = padre.window()
        super().__init__(ventana)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setGeometry(ventana.geometry())
        self._contenido = contenido

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("titulo")
        cerrar = QPushButton("Cerrar   Esc")
        cerrar.setCursor(Qt.PointingHandCursor)
        cerrar.clicked.connect(self.reject)
        # Sin foco: si no, arranca con el anillo rojo puesto (es lo único
        # enfocable). Desde el teclado se cierra con Esc.
        cerrar.setFocusPolicy(Qt.NoFocus)

        arriba = QHBoxLayout()
        arriba.addWidget(etiqueta)
        arriba.addStretch()
        arriba.addWidget(cerrar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 28, 40, 40)
        layout.setSpacing(16)
        layout.addLayout(arriba)
        layout.addWidget(contenido, 1, Qt.AlignCenter)

    def paintEvent(self, evento):
        QPainter(self).fillRect(self.rect(), self.FONDO)

    def mousePressEvent(self, evento):
        if not self._contenido.geometry().contains(evento.position().toPoint()):
            self.reject()
            return
        super().mousePressEvent(evento)
