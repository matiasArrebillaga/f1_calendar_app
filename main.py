import sys
import fastf1
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout

from ui.topbar import TopBar
from ui.sidebar import Sidebar
from ui.calendar_view import CalendarView
from ui.event_detail_view import EventDetailView
from ui.standings_view import StandingsView
import sys
import os
from core.paths import data_path
from PySide6.QtGui import QIcon


fastf1.Cache.enable_cache(data_path('cache'))
QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))


def resource_path(ruta_relativa):
    """Devuelve la ruta correcta a un recurso, tanto corriendo como script
    normal como empaquetado en un .exe con PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, ruta_relativa)
def data_path(nombre_carpeta):
    """Carpeta de datos generados en runtime (caché), siempre al lado del
    .exe o del script — a diferencia de resource_path, que apunta a los
    recursos empaquetados de solo lectura."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")
    return os.path.join(base, nombre_carpeta)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendario F1")
        self.resize(1300, 750)
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
        

    def abrir_detalle(self, fila):
        evento = self.calendar_view.calendario.iloc[fila]
        self.detail_view.mostrar_evento(evento)
        self.stack.setCurrentIndex(1)

    def volver_a_calendario(self):
        self.ir_a_calendario()

    def ir_a_calendario(self):
        self.stack.setCurrentIndex(0)
        self.sidebar.marcar_calendario()

    def on_navegar_sidebar(self, destino):
        if destino == "calendario":
            self.stack.setCurrentIndex(0)
        elif destino == "standings":
            self.stack.setCurrentIndex(2)

    def on_anio_cambiado(self, year):
        self.calendar_view.cargar_calendario(year)
        self.standings_view.cargar_datos(year)


app = QApplication(sys.argv)
app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())
ventana = MainWindow()
ventana.show()
app.exec()
