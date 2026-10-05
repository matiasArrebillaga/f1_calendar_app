from PySide6.QtCore import QThread, Signal
from core.historial import ganadores_circuito


class GanadoresWorker(QThread):
    terminado = Signal(list)
    error = Signal(str)

    def __init__(self, circuit_id):
        super().__init__()
        self.circuit_id = circuit_id

    def run(self):
        try:
            self.terminado.emit(ganadores_circuito(self.circuit_id))
        except Exception as e:
            self.error.emit(str(e))
