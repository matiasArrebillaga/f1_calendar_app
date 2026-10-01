import fastf1
from PySide6.QtCore import QThread, Signal


class CalendarWorker(QThread):
    terminado = Signal(object)  # emite el calendario (DataFrame) del año
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year

    def run(self):
        try:
            # Sin include_testing=False el calendario trae los tests de
            # pretemporada con RoundNumber 0, y get_session(year, 0, ...) tira
            # "Cannot get testing event by round number!" al clickear cualquier
            # sesión de esas tarjetas.
            self.terminado.emit(
                fastf1.get_event_schedule(self.year, include_testing=False)
            )
        except Exception as e:
            self.error.emit(str(e))
