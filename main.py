import sys
import fastf1
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout

from ui.topbar import TopBar
from ui.sidebar import Sidebar
from ui.calendar_view import CalendarView
from ui.event_detail_view import EventDetailView
from ui.standings_view import StandingsView

fastf1.Cache.enable_cache('cache')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Calendar App")
        self.resize(1100, 700)

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
        layout_cuerpo.addWidget(self.sidebar)
        layout_cuerpo.addWidget(self.stack)

        contenedor_central = QWidget()
        layout_principal = QVBoxLayout()
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

with open("style.qss", "r") as f:
    app.setStyleSheet(f.read())

ventana = MainWindow()
ventana.show()
app.exec()