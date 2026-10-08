from PySide6.QtCore import QThread, Signal
from core.track_map import generar_o_obtener_mapa


class TrackMapWorker(QThread):
    terminado = Signal(str)
    error = Signal(str)

    def __init__(self, location, year_actual):
        super().__init__()
        self.location = location
        self.year_actual = year_actual

    def run(self):
        try:
            ruta = generar_o_obtener_mapa(self.location, self.year_actual)
            if ruta is None:
                self.error.emit(f"no hay una carrera desde 2018 en {self.location}.")
                return
            self.terminado.emit(ruta)
        except Exception:
            # Lo que tira FastF1 viene en inglés y no le dice nada al usuario.
            self.error.emit("faltan los datos de FastF1 o no hay conexión.")