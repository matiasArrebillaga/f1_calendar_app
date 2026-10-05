from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Qt, QSize, QVariantAnimation, QEasingCurve

from core.paths import resource_path
from ui.icons import icono, MUTED
from ui.selector_temporada import SelectorTemporada


class Sidebar(QWidget):
    """Marca, temporada y navegación.

    Para sumar una función: un botón más en `_agregar_nav` dentro de su grupo
    (cada grupo es una etiqueta + botones en el mismo QVBoxLayout). Colapsada
    queda en íconos solos, así el menú puede crecer sin comerle ancho al
    calendario.
    """
    navegar = Signal(str)
    logo_clickeado = Signal()

    ANCHO = 224
    ANCHO_COLAPSADA = 60
    DURACION_COLAPSO = 200

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebarPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.ANCHO)
        self._colapsada = False
        self._textos = {}   # {boton: texto}: colapsada, el texto vive en el tooltip

        self.boton_marca = QPushButton("F1 CALENDAR")
        self.boton_marca.setObjectName("botonMarca")
        self.boton_marca.setIcon(QIcon(resource_path("assets/logo.png")))
        self.boton_marca.setIconSize(QSize(28, 28))
        self.boton_marca.setCursor(Qt.PointingHandCursor)
        self.boton_marca.setToolTip("Volver al calendario")
        self.boton_marca.clicked.connect(self.logo_clickeado)
        self._textos[self.boton_marca] = "F1 CALENDAR"

        self.selector = SelectorTemporada()
        # Colapsada no entra el selector: queda el año a secas, para no perder
        # de vista qué temporada se está mirando.
        self.anio_mini = QLabel(str(self.selector.anio_actual))
        self.anio_mini.setObjectName("anioMini")
        self.anio_mini.setAlignment(Qt.AlignCenter)
        self.anio_mini.hide()
        self.selector.anio_cambiado.connect(lambda anio: self.anio_mini.setText(str(anio)))

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self._etiquetas_grupo = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 8)
        layout.setSpacing(2)
        layout.addWidget(self.boton_marca)
        layout.addSpacing(8)
        layout.addWidget(self.selector)
        layout.addWidget(self.anio_mini)
        layout.addSpacing(14)

        self._agregar_etiqueta_grupo(layout, "MENÚ")
        self.boton_calendario = self._agregar_nav(
            layout, "Calendario", "calendar-days", "Calendario de la temporada (Esc)")
        self.boton_standings = self._agregar_nav(
            layout, "Clasificación", "trophy", "Clasificación de pilotos y equipos")
        self.boton_pilotos = self._agregar_nav(
            layout, "Pilotos", "users", "Pilotos y equipos de la temporada")
        self.boton_calendario.setChecked(True)

        layout.addStretch()

        self.boton_colapsar = QPushButton("Contraer")
        self.boton_colapsar.setObjectName("navLateral")
        self.boton_colapsar.setIcon(icono("panel-left-close", MUTED, 16))
        self.boton_colapsar.setIconSize(QSize(16, 16))
        self.boton_colapsar.setMinimumHeight(40)
        self.boton_colapsar.setCursor(Qt.PointingHandCursor)
        self.boton_colapsar.setToolTip("Contraer menú")
        self.boton_colapsar.clicked.connect(self.alternar_colapso)
        self._textos[self.boton_colapsar] = "Contraer"
        layout.addWidget(self.boton_colapsar)

        self.boton_calendario.clicked.connect(lambda: self.navegar.emit("calendario"))
        self.boton_standings.clicked.connect(lambda: self.navegar.emit("standings"))
        self.boton_pilotos.clicked.connect(lambda: self.navegar.emit("pilotos"))

        self._animacion = QVariantAnimation(self)
        self._animacion.setDuration(self.DURACION_COLAPSO)
        self._animacion.setEasingCurve(QEasingCurve.OutCubic)
        self._animacion.valueChanged.connect(self.setFixedWidth)
        self._animacion.finished.connect(self._aplicar_textos)

    def _agregar_etiqueta_grupo(self, layout, texto):
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("etiquetaGrupo")
        self._etiquetas_grupo.append(etiqueta)
        layout.addWidget(etiqueta)

    def _agregar_nav(self, layout, texto, nombre_icono, tooltip):
        boton = QPushButton(texto)
        boton.setObjectName("navLateral")
        boton.setIcon(icono(nombre_icono, MUTED, 16))
        boton.setIconSize(QSize(16, 16))
        boton.setCheckable(True)
        boton.setMinimumHeight(40)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setToolTip(tooltip)
        self.grupo.addButton(boton)
        self._textos[boton] = texto
        layout.addWidget(boton)
        return boton

    def marcar_calendario(self):
        self.boton_calendario.setChecked(True)

    def alternar_colapso(self):
        self._colapsada = not self._colapsada
        self._animacion.stop()
        self._animacion.setStartValue(self.width())
        self._animacion.setEndValue(self.ANCHO_COLAPSADA if self._colapsada else self.ANCHO)

        self.boton_colapsar.setIcon(icono(
            "panel-left-open" if self._colapsada else "panel-left-close", MUTED, 16))
        self.boton_colapsar.setToolTip("Expandir menú" if self._colapsada else "Contraer menú")
        self._textos[self.boton_colapsar] = "Expandir" if self._colapsada else "Contraer"

        # Al contraer, el texto se va antes de achicar (si no, se ve cortado
        # durante la animación); al expandir, vuelve recién cuando hay lugar.
        if self._colapsada:
            self._aplicar_textos()
        self._animacion.start()

    def _aplicar_textos(self):
        for boton, texto in self._textos.items():
            boton.setText("" if self._colapsada else texto)
        self.selector.setVisible(not self._colapsada)
        self.anio_mini.setVisible(self._colapsada)
        for etiqueta in self._etiquetas_grupo:
            etiqueta.setVisible(not self._colapsada)
