import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QEvent, QRect
from PySide6.QtGui import QColor, QPixmap
from core.flags import obtener_ruta_bandera

class CalendarEventCard(QWidget):
    """
    Tarjeta de un evento del calendario.
    `estado` es uno de: 'proxima' | 'pasado' | 'futuro'.

    La tarjeta real (`_interior`) vive un poco más chica que este contenedor
    (`self`, de tamaño fijo para no romper el QGridLayout) y se anima para
    "crecer" hasta llenarlo por completo al pasar el mouse. El color ya no
    se pinta a mano: el estado se expone como propiedad Qt y el look vive
    en style.qss (QWidget#tarjetaEvento[estado="..."]).
    """
    clickeada = Signal(int)

    MARGEN = 5  # cuánto "crece" la tarjeta hacia cada lado al hacer hover

    def __init__(self, indice_fila, evento, estado):
        super().__init__()
        self.indice_fila = indice_fila
        self._ancho = 190
        self._alto = 100

        bandera = QLabel()
        bandera.setStyleSheet("background: transparent;")
        ruta_bandera = obtener_ruta_bandera(evento['Country'])
        if ruta_bandera:
            bandera.setPixmap(QPixmap(ruta_bandera))        
        self.setFixedSize(self._ancho, self._alto)
        self.setCursor(Qt.PointingHandCursor)

        # Tarjeta interior: la que realmente se ve y se anima.
        self._interior = QWidget(self)
        self._interior.setObjectName("tarjetaEvento")
        self._interior.setProperty("estado", estado)
        self._interior.setAttribute(Qt.WA_StyledBackground, True)
        self._interior.setAttribute(Qt.WA_Hover, True)
        self._interior.setCursor(Qt.PointingHandCursor)
        self._interior.installEventFilter(self)
        self._interior.setGeometry(
            self.MARGEN, self.MARGEN,
            self._ancho - 2 * self.MARGEN, self._alto - 2 * self.MARGEN
        )

        self._geometria_normal = QRect(
            self.MARGEN, self.MARGEN,
            self._ancho - 2 * self.MARGEN, self._alto - 2 * self.MARGEN
        )
        self._geometria_hover = QRect(0, 0, self._ancho, self._alto)

        # Sombra animable: la tarjeta "flota" un poco al pasar el mouse.
        self._sombra = QGraphicsDropShadowEffect(self)
        self._sombra.setColor(QColor(0, 0, 0, 190))
        self._sombra.setOffset(0, 2)
        self._sombra.setBlurRadius(0)
        self.setGraphicsEffect(self._sombra)

        self._animacion_sombra = QPropertyAnimation(self._sombra, b"blurRadius")
        self._animacion_sombra.setDuration(130)
        self._animacion_sombra.setEasingCurve(QEasingCurve.OutCubic)

        self._animacion_tamano = QPropertyAnimation(self._interior, b"geometry")
        self._animacion_tamano.setDuration(130)
        self._animacion_tamano.setEasingCurve(QEasingCurve.OutCubic)

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
        self._interior.setLayout(layout)

    def eventFilter(self, obj, event):
        if obj is self._interior:
            if event.type() == QEvent.MouseButtonPress:
                self.clickeada.emit(self.indice_fila)
                return True
            if event.type() == QEvent.Enter:
                self._animar(destino_geometria=self._geometria_hover, blur=20, offset_y=7)
                return False
            if event.type() == QEvent.Leave:
                self._animar(destino_geometria=self._geometria_normal, blur=0, offset_y=2)
                return False
        return super().eventFilter(obj, event)

    def mousePressEvent(self, evento_mouse):
        self.clickeada.emit(self.indice_fila)

    def _animar(self, destino_geometria, blur, offset_y):
        self._sombra.setOffset(0, offset_y)
        self._animacion_sombra.stop()
        self._animacion_sombra.setStartValue(self._sombra.blurRadius())
        self._animacion_sombra.setEndValue(blur)
        self._animacion_sombra.start()

        self._animacion_tamano.stop()
        self._animacion_tamano.setStartValue(self._interior.geometry())
        self._animacion_tamano.setEndValue(destino_geometria)
        self._animacion_tamano.start()
