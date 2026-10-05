import glob
import sys
import fastf1
from PySide6.QtCore import QLocale, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QHBoxLayout,
    QGraphicsOpacityEffect
)

from ui.sidebar import Sidebar
from ui.calendar_view import CalendarView
from ui.event_detail_view import EventDetailView
from ui.standings_view import StandingsView
from ui.pilotos_view import PilotosView
from core.paths import resource_path, data_path


fastf1.Cache.enable_cache(data_path('cache'))
QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))

# Qt NO hace cascada como CSS: si se le pide una familia que no está instalada
# cae a Tahoma, así que se elige a mano la primera presente. Va en Python y no
# en el .qss porque acá se puede verificar contra las familias que el sistema
# realmente tiene.
#
# Ésta es la fuente del texto común, que en la app es casi todo de 9 a 13 px:
# ahí manda la nitidez. Titillium Web (la de los títulos, en el .qss) se pixela
# a esos tamaños; Segoe UI Variable Text es la variante de Windows 11 dibujada
# justamente para texto chico en pantalla.
FAMILIAS_PREFERIDAS = (
    "Segoe UI Variable Text",      # viene con Windows 11
    "Segoe UI",
    "Helvetica Neue",
    "Arial",
)


def _familia_disponible():
    instaladas = set(QFontDatabase.families())
    return next((f for f in FAMILIAS_PREFERIDAS if f in instaladas), None)


class MainWindow(QMainWindow):
    DURACION_FADE = 220
    TIMEOUT_CIERRE_MS = 3000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendario F1")
        self.resize(1300, 750)
        self.setMinimumSize(1100, 650)
        self.sidebar = Sidebar()
        self.selector = self.sidebar.selector

        self.calendar_view = CalendarView()
        self.detail_view = EventDetailView()
        self.standings_view = StandingsView()
        self.pilotos_view = PilotosView()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.calendar_view)   # índice 0
        self.stack.addWidget(self.detail_view)      # índice 1
        self.stack.addWidget(self.standings_view)   # índice 2
        self.stack.addWidget(self.pilotos_view)     # índice 3

        # Sin barra superior: el logo y la temporada viven en la sidebar, y
        # cada vista arma su propio encabezado.
        contenedor_central = QWidget()
        layout_principal = QHBoxLayout(contenedor_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        layout_principal.addWidget(self.sidebar)
        layout_principal.addWidget(self.stack)
        self.setCentralWidget(contenedor_central)

        self.calendar_view.evento_seleccionado.connect(self.abrir_detalle)
        self.detail_view.volver.connect(self.volver_a_calendario)
        self.selector.anio_cambiado.connect(self.on_anio_cambiado)
        self.sidebar.logo_clickeado.connect(self.ir_a_calendario)
        self.sidebar.navegar.connect(self.on_navegar_sidebar)
        # carga inicial
        self.on_anio_cambiado(self.selector.anio_actual)

    def _mostrar_vista(self, indice):
        """Cambia de página del stack con un fade de entrada.

        El efecto va sobre la página entrante y se saca al terminar: Qt admite
        un solo QGraphicsEffect por widget y, mientras está puesto, pinta todo
        el subárbol por software.
        """
        if self.stack.currentIndex() == indice:
            return

        self.stack.setCurrentIndex(indice)
        vista = self.stack.widget(indice)

        efecto = QGraphicsOpacityEffect(vista)
        vista.setGraphicsEffect(efecto)

        animacion = QPropertyAnimation(efecto, b"opacity", self)
        animacion.setDuration(self.DURACION_FADE)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        # La animación ya es hija de self (3er argumento), así que sobrevive sin
        # guardarla a mano; lo que hace falta es liberarla, porque si no cada
        # cambio de vista deja una colgada del árbol para siempre. Del efecto se
        # encarga setGraphicsEffect(None): Qt es su dueño y lo borra ahí mismo
        # (tocarlo después tira "Internal C++ object already deleted").
        animacion.finished.connect(
            lambda: self._terminar_fade(vista, animacion)
        )
        animacion.start()

    @staticmethod
    def _terminar_fade(vista, animacion):
        vista.setGraphicsEffect(None)
        animacion.deleteLater()

    def abrir_detalle(self, fila):
        evento = self.calendar_view.calendario.iloc[fila]
        self.detail_view.mostrar_evento(evento)
        self._mostrar_vista(1)

    def volver_a_calendario(self):
        self.ir_a_calendario()

    def ir_a_calendario(self):
        self._mostrar_vista(0)
        self.sidebar.marcar_calendario()

    def on_navegar_sidebar(self, destino):
        if destino == "calendario":
            self._mostrar_vista(0)
        elif destino == "standings":
            self._mostrar_vista(2)
        elif destino == "pilotos":
            self._mostrar_vista(3)

    def on_anio_cambiado(self, year):
        self.calendar_view.cargar_calendario(year)
        # La clasificación se pide recién cuando se la mira: antes, cada año que
        # pasaba con las flechas era una request a Ergast (que limita a 4/s y
        # 200/h) aunque la vista estuviera oculta.
        self.standings_view.pedir_anio(year)
        self.pilotos_view.pedir_anio(year)

    def keyPressEvent(self, evento_tecla):
        tecla = evento_tecla.key()

        # Esc dentro de una ficha de piloto o equipo vuelve a su grilla; desde
        # la grilla, al calendario como en el resto de las vistas.
        if (tecla == Qt.Key_Escape and self.stack.currentWidget() is self.pilotos_view
                and self.pilotos_view.volver_a_grilla()):
            return

        if tecla == Qt.Key_Escape and self.stack.currentIndex() != 0:
            self.ir_a_calendario()
            return

        # Las flechas cambian de año, salvo mientras se está escribiendo uno.
        if tecla in (Qt.Key_Left, Qt.Key_Right) and not self.selector.campo_anio.hasFocus():
            paso = -1 if tecla == Qt.Key_Left else 1
            self.selector.ir_a_anio(self.selector.anio_actual + paso)
            return

        super().keyPressEvent(evento_tecla)

    def closeEvent(self, evento_cierre):
        """Espera a los workers antes de salir: un QThread vivo al destruirse
        la ventana da 'QThread: Destroyed while thread is still running' y a
        veces crashea (TrackMapWorker puede estar bajando telemetría)."""
        for vista in (self.calendar_view, self.detail_view, self.standings_view,
                      self.pilotos_view):
            for worker in list(getattr(vista, '_workers_activos', [])):
                worker.requestInterruption()   # FotosWorker corta entre foto y foto
                worker.wait(self.TIMEOUT_CIERRE_MS)
        super().closeEvent(evento_cierre)


app = QApplication(sys.argv)
app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

# Titillium Web, para los títulos. Empaquetada (licencia OFL,
# assets/fonts/OFL.txt): así se ve igual en una PC que no la tiene instalada.
for archivo_fuente in glob.glob(resource_path("assets/fonts/*.ttf")):
    QFontDatabase.addApplicationFont(archivo_fuente)

familia = _familia_disponible()
if familia is not None:
    fuente = app.font()
    fuente.setFamily(familia)
    app.setFont(fuente)
with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())
ventana = MainWindow()
ventana.show()
app.exec()
