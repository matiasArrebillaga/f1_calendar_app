import fastf1
from fastf1.ergast import Ergast
from PySide6.QtCore import QThread, Signal

class StandingsWorker(QThread):
    # emite {'pilotos', 'equipos', 'ronda', 'total_rondas'}; ronda y
    # total_rondas pueden ser None si no se pudieron averiguar
    terminado = Signal(object)
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year
        self.ergast = Ergast()

    def run(self):
        try:
            respuesta_pilotos = self.ergast.get_driver_standings(season=self.year)
            respuesta_equipos = self.ergast.get_constructor_standings(season=self.year)
            datos = {
                'pilotos': respuesta_pilotos.content[0],
                'equipos': respuesta_equipos.content[0],
                'ronda': None,
                'total_rondas': None,
            }
        except Exception as e:
            self.error.emit(str(e))
            return

        # Lo que sigue sólo alimenta los indicadores ("tras R17", puntos en
        # juego): si falla, la tabla se muestra igual.
        try:
            datos['ronda'] = int(respuesta_pilotos.description['round'].iloc[0])
        except Exception:
            pass
        try:
            # Sale del caché de fastf1: el calendario ya lo bajó CalendarView.
            datos['total_rondas'] = len(
                fastf1.get_event_schedule(self.year, include_testing=False))
        except Exception:
            pass
        self.terminado.emit(datos)
