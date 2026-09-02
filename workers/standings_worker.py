from fastf1.ergast import Ergast
from PySide6.QtCore import QThread, Signal

class StandingsWorker(QThread):
    terminado = Signal(object, object)  # emite (standings_pilotos, standings_equipos)
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year
        self.ergast = Ergast()

    def run(self):
        try:
            standings_pilotos = self.ergast.get_driver_standings(season=self.year).content[0]
            standings_equipos = self.ergast.get_constructor_standings(season=self.year).content[0]
            self.terminado.emit(standings_pilotos, standings_equipos)
        except Exception as e:
            self.error.emit(str(e))