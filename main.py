import sys
import fastf1
from PySide6.QtCore import QLocale, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGraphicsOpacityEffect
)

from ui.topbar import TopBar
from ui.sidebar import Sidebar
from ui.calendar_view import CalendarView
from ui.event_detail_view import EventDetailView
from ui.standings_view import StandingsView
from core.paths import resource_path, data_path


fastf1.Cache.enable_cache(data_path('cache'))
QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))


class MainWindow(QMainWindow):
    DURACION_FADE = 220
    TIMEOUT_CIERRE_MS = 3000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendario F1")
        self.resize(1300, 750)
        self.setMinimumSize(1100, 650)
        self.top_bar = TopBar()
        self.sidebar = Sidebar()

        self.calendar_view = CalendarView()
        self.detail_view = EventDetailView()
        self.standings_view = StandingsView()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.calendar_view)   # índice 0
        self.stack.addWidget(self.detail_view)      # índice 1
        self.stack.addWidget(self.standings_view)   # índice 2

        layout_cuerpo = QHBoxLayout()
        layout_cuerpo.setContentsMargins(0, 0, 0, 0)
        layout_cuerpo.setSpacing(0)
        layout_cuerpo.addWidget(self.sidebar)
        layout_cuerpo.addWidget(self.stack)

        contenedor_central = QWidget()
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        layout_principal.addWidget(self.top_bar)
        layout_principal.addLayout(layout_cuerpo)
        contenedor_central.setLayout(layout_principal)
        self.setCentralWidget(contenedor_central)

        self.calendar_view.evento_seleccionado.connect(self.abrir_detalle)
        self.detail_view.volver.connect(self.volver_a_calendario)
        self.top_bar.anio_cambiado.connect(self.on_anio_cambiado)
        self.top_bar.logo_clickeado.connect(self.ir_a_calendario)
        self.sidebar.navegar.connect(self.on_navegar_sidebar)
        # carga inicial
        self.on_anio_cambiado(self.top_bar.anio_actual)

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

    def on_anio_cambiado(self, year):
        self.calendar_view.cargar_calendario(year)
        # La clasificación se pide recién cuando se la mira: antes, cada año que
        # pasaba con las flechas era una request a Ergast (que limita a 4/s y
        # 200/h) aunque la vista estuviera oculta.
        self.standings_view.pedir_anio(year)

    def keyPressEvent(self, evento_tecla):
        tecla = evento_tecla.key()

        if tecla == Qt.Key_Escape and self.stack.currentIndex() != 0:
            self.ir_a_calendario()
            return

        # Las flechas cambian de año, salvo mientras se está escribiendo uno.
        if tecla in (Qt.Key_Left, Qt.Key_Right) and not self.top_bar.campo_anio.hasFocus():
            paso = -1 if tecla == Qt.Key_Left else 1
            self.top_bar.ir_a_anio(self.top_bar.anio_actual + paso)
            return

        super().keyPressEvent(evento_tecla)

    def closeEvent(self, evento_cierre):
        """Espera a los workers antes de salir: un QThread vivo al destruirse
        la ventana da 'QThread: Destroyed while thread is still running' y a
        veces crashea (TrackMapWorker puede estar bajando telemetría)."""
        for vista in (self.calendar_view, self.detail_view, self.standings_view):
            for worker in list(getattr(vista, '_workers_activos', [])):
                worker.wait(self.TIMEOUT_CIERRE_MS)
        super().closeEvent(evento_cierre)


app = QApplication(sys.argv)
app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())
ventana = MainWindow()
ventana.show()
app.exec()
