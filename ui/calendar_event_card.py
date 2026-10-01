import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QEvent, QRect
from PySide6.QtGui import QColor, QPixmap
from core.flags import obtener_ruta_bandera
from core.i18n import traducir_evento, traducir_pais

class CalendarEventCard(QWidget):
    """
    Tarjeta de un evento del calendario.
    `estado` es uno de: 'proxima' | 'pasado' | 'futuro'.

    La tarjeta real (`_interior`) vive un poco más chica que este contenedor
    (`self`, de tamaño fijo para no romper el QGridLayout) y se anima para
    "crecer" hasta llenarlo por completo al pasar el mouse. El color ya no
    se pinta a mano: el estado se expone como propiedad Qt y el look vive
    en style.qss (QWidget#tarjetaEvento[estado="..."]).

    Foco y pressed van por el mismo mecanismo de propiedades Qt (`foco`,
    `presionada`). No se puede usar el pseudo-estado :focus de Qt porque el
    foco lo recibe `self`, mientras lo que se pinta es el hijo `_interior`.
    """
    clickeada = Signal(int)

    MARGEN = 6  # cuánto "crece" la tarjeta hacia cada lado al hacer hover
    _cache_pixmaps = {}
    def __init__(self, indice_fila, evento, estado):
        super().__init__()
        self.indice_fila = indice_fila
        self._ancho = 200
        self._alto = 120

        self.setFixedSize(self._ancho, self._alto)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        # Preparamos la bandera ACÁ (antes de armar fila_superior) porque
        # necesitamos conocer su ancho para reservarle espacio en el layout.
        self.ancho_bandera = 22
        self.margen_bandera = 14
        self._pixmap_bandera = self._obtener_pixmap_bandera(evento['Country'])

        nombre_evento_es = traducir_evento(evento['EventName'])
        pais_es = traducir_pais(evento['Country'])

        # Tarjeta interior: la que realmente se ve y se anima.
        self._interior = QWidget(self)
        self._interior.setObjectName("tarjetaEvento")
        self._interior.setProperty("estado", estado)
        self._interior.setProperty("foco", "false")
        self._interior.setProperty("presionada", "false")
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

        self.setToolTip(f"{nombre_evento_es} — {evento['EventDate'].date()}")

        # Sombra animable: la tarjeta "flota" un poco al pasar el mouse.
        self._sombra = QGraphicsDropShadowEffect(self)
        self._sombra.setColor(QColor(0, 0, 0, 190))
        self._sombra.setOffset(0, 2)
        self._sombra.setBlurRadius(0)
        self.setGraphicsEffect(self._sombra)

        self._animacion_sombra = QPropertyAnimation(self._sombra, b"blurRadius")
        self._animacion_sombra.setDuration(200)
        self._animacion_sombra.setEasingCurve(QEasingCurve.OutCubic)

        self._animacion_tamano = QPropertyAnimation(self._interior, b"geometry")
        self._animacion_tamano.setDuration(200)
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

        # Reservamos un hueco vacío del ancho de la bandera + un margen chico,
        # así "PRÓXIMA" no queda escondida debajo de la bandera flotante.
        if self._pixmap_bandera is not None:
            fila_superior.addSpacing(self.ancho_bandera + 8)
        nombre = QLabel(nombre_evento_es)
        nombre.setObjectName("nombreEvento")
        nombre.setWordWrap(True)

        pais = QLabel(pais_es)
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


        if self._pixmap_bandera is not None:
            self._bandera = QLabel(self)
            self._bandera.setPixmap(self._pixmap_bandera)
            self._bandera.setFixedSize(self._pixmap_bandera.size())
            self._bandera.setStyleSheet("background: transparent;")
            self._bandera.move(
                self._ancho - self._pixmap_bandera.width() - self.margen_bandera,
                self.margen_bandera
            )
            self._bandera.raise_()

    def eventFilter(self, obj, event):
        if obj is self._interior:
            if event.type() == QEvent.MouseButtonPress:
                self._marcar(presionada=True)
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self._marcar(presionada=False)
                self.setFocus(Qt.MouseFocusReason)
                self.clickeada.emit(self.indice_fila)
                return True
            if event.type() == QEvent.Enter:
                self._animar(destino_geometria=self._geometria_hover, blur=22, offset_y=7)
                return False
            if event.type() == QEvent.Leave:
                self._marcar(presionada=False)
                if not self.hasFocus():
                    self._animar(destino_geometria=self._geometria_normal, blur=0, offset_y=2)
                return False
        return super().eventFilter(obj, event)

    def mousePressEvent(self, evento_mouse):
        # Clicks que caen en `self` y no en `_interior`: la bandera flotante y
        # el margen de 6px que la tarjeta deja libre cuando no está en hover.
        self._marcar(presionada=True)

    def mouseReleaseEvent(self, evento_mouse):
        self._marcar(presionada=False)
        self.setFocus(Qt.MouseFocusReason)
        self.clickeada.emit(self.indice_fila)

    def keyPressEvent(self, evento_tecla):
        if evento_tecla.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clickeada.emit(self.indice_fila)
            return
        super().keyPressEvent(evento_tecla)

    def focusInEvent(self, evento_foco):
        super().focusInEvent(evento_foco)
        self._marcar(foco=True)
        self._animar(destino_geometria=self._geometria_hover, blur=22, offset_y=7)

    def focusOutEvent(self, evento_foco):
        super().focusOutEvent(evento_foco)
        self._marcar(foco=False, presionada=False)
        if not self._interior.underMouse():
            self._animar(destino_geometria=self._geometria_normal, blur=0, offset_y=2)

    def _marcar(self, foco=None, presionada=None):
        """Actualiza las propiedades Qt que el .qss usa para foco/pressed y
        fuerza el repintado (Qt no reevalúa el stylesheet por sí solo cuando
        cambia una propiedad dinámica)."""
        if foco is not None:
            self._interior.setProperty("foco", "true" if foco else "false")
        if presionada is not None:
            self._interior.setProperty("presionada", "true" if presionada else "false")
        self._interior.style().unpolish(self._interior)
        self._interior.style().polish(self._interior)

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
    @classmethod
    def _obtener_pixmap_bandera(cls, pais):
        if pais in cls._cache_pixmaps:
            return cls._cache_pixmaps[pais]

        ruta_bandera = obtener_ruta_bandera(pais)
        if not ruta_bandera:
            cls._cache_pixmaps[pais] = None
            return None

        pixmap_original = QPixmap(ruta_bandera)
        pixmap_escalado = pixmap_original.scaledToWidth(22, Qt.SmoothTransformation)

        cls._cache_pixmaps[pais] = pixmap_escalado
        return pixmap_escalado
