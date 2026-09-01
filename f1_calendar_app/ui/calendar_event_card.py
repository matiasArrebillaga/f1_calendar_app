import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor


class CalendarEventCard(QWidget):
    """
    Tarjeta de un evento del calendario.
    `estado` es uno de: 'proxima' | 'pasado' | 'futuro'.
    El color ya no se pinta a mano: el estado se expone como propiedad Qt
    y el look real vive en style.qss (QWidget#tarjetaEvento[estado="..."]).
    """
    clickeada = Signal(int)

    def __init__(self, indice_fila, evento, estado):
        super().__init__()
        self.indice_fila = indice_fila

        self.setObjectName("tarjetaEvento")
        self.setProperty("estado", estado)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(190, 100)
        self.setCursor(Qt.PointingHandCursor)

        # Sombra animable: la tarjeta "flota" un poco al pasar el mouse.
        self._sombra = QGraphicsDropShadowEffect(self)
        self._sombra.setColor(QColor(0, 0, 0, 180))
        self._sombra.setOffset(0, 2)
        self._sombra.setBlurRadius(0)
        self.setGraphicsEffect(self._sombra)

        self._animacion = QPropertyAnimation(self._sombra, b"blurRadius")
        self._animacion.setDuration(120)
        self._animacion.setEasingCurve(QEasingCurve.OutCubic)

        fila_superior = QHBoxLayout()
        fila_superior.setContentsMargins(0, 0, 0, 0)
        fila_superior.setSpacing(6)

        ronda = evento.get('RoundNumber')
        texto_ronda = f"R{int(ronda)}" if pd.notna(ronda) else ""
        etiqueta_ronda = QLabel(texto_ronda)
        etiqueta_ronda.setObjectName("etiquetaRonda")
        fila_superior.addWidget(etiqueta_ronda)
        fila_superior.addStretch()

        if estado == 'proxima':
            etiqueta_proxima = QLabel("PRÓXIMA")
            etiqueta_proxima.setObjectName("etiquetaProxima")
            fila_superior.addWidget(etiqueta_proxima)

        nombre = QLabel(str(evento['EventName']))
        nombre.setObjectName("nombreEvento")
        nombre.setWordWrap(True)

        pais = QLabel(str(evento['Country']))
        pais.setObjectName("paisEvento")

        fecha = QLabel(str(evento['EventDate'].date()))
        fecha.setObjectName("fechaEvento")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        layout.addLayout(fila_superior)
        layout.addWidget(nombre)
        layout.addWidget(pais)
        layout.addStretch()
        layout.addWidget(fecha)
        self.setLayout(layout)

    def mousePressEvent(self, evento_mouse):
        self.clickeada.emit(self.indice_fila)

    def enterEvent(self, event):
        self._animar_sombra(destino=18, offset_y=6)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animar_sombra(destino=0, offset_y=2)
        super().leaveEvent(event)

    def _animar_sombra(self, destino, offset_y):
        self._sombra.setOffset(0, offset_y)
        self._animacion.stop()
        self._animacion.setStartValue(self._sombra.blurRadius())
        self._animacion.setEndValue(destino)
        self._animacion.start()
