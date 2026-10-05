from PySide6.QtCore import QThread, Signal

from core.calendario import obtener_calendario


class CalendarWorker(QThread):
    terminado = Signal(object)  # emite el calendario (DataFrame) del año
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year

    def run(self):
        try:
            self.terminado.emit(obtener_calendario(self.year))
        except Exception as e:
            self.error.emit(str(e))
