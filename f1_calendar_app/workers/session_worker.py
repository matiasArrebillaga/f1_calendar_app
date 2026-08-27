import fastf1
from PySide6.QtCore import QThread, Signal

class SessionWorker(QThread):
    terminado = Signal(object)  # emite la sesión cargada
    error = Signal(str)         # emite un mensaje si algo falla

    def __init__(self, year, gp, codigo_sesion):
        super().__init__()
        self.year = year
        self.gp = gp
        self.codigo_sesion = codigo_sesion

    def run(self):
        try:
            sesion = fastf1.get_session(self.year, self.gp, self.codigo_sesion)
            sesion.load(laps=False, telemetry=False, weather=False)
            self.terminado.emit(sesion)
        except Exception as e:
            self.error.emit(str(e))