import fastf1
from PySide6.QtCore import QThread, Signal
from core.track_map import generar_mapa_circuito, CACHE_DIR
import os


class TrackMapWorker(QThread):
    terminado = Signal(str)  # emite la ruta del PNG generado
    error = Signal(str)

    def __init__(self, location, year_referencia, gp_referencia):
        super().__init__()
        self.location = location
        self.year_referencia = year_referencia
        self.gp_referencia = gp_referencia

    def run(self):
        try:
            sesion = fastf1.get_session(self.year_referencia, self.gp_referencia, 'R')
            sesion.load(telemetry=True, laps=True, weather=False)

            vuelta_rapida = sesion.laps.pick_fastest()
            telemetria = vuelta_rapida.get_telemetry()
            circuito_info = sesion.get_circuit_info()

            nombre_archivo = self.location.lower().replace(" ", "_") + ".png"
            ruta_salida = os.path.join(CACHE_DIR, nombre_archivo)

            generar_mapa_circuito(self.location, telemetria, circuito_info, ruta_salida)
            self.terminado.emit(ruta_salida)
        except Exception as e:
            self.error.emit(str(e))