import sys
import fastf1
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from ui.calendar_view import CalendarView
from ui.event_detail_view import EventDetailView

fastf1.Cache.enable_cache('cache')
# agregar logo de f1, agrandar tarjetas, cambiar botones detailed view, agregar sidebar
#listar standings, pilotos, equipos
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Calendar App")
        self.resize(1200, 700)

        self.calendar_view = CalendarView()
        self.detail_view = EventDetailView()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.calendar_view)
        self.stack.addWidget(self.detail_view)
        self.setCentralWidget(self.stack)

        self.calendar_view.evento_seleccionado.connect(self.abrir_detalle)
        self.detail_view.volver.connect(self.volver_a_calendario)

    def abrir_detalle(self, fila):
        evento = self.calendar_view.calendario.iloc[fila]
        self.detail_view.mostrar_evento(evento)
        self.stack.setCurrentIndex(1)

    def volver_a_calendario(self):
        self.stack.setCurrentIndex(0)


app = QApplication(sys.argv)

with open("style.qss", "r") as f:
    app.setStyleSheet(f.read())

ventana = MainWindow()
ventana.show()
app.exec()
