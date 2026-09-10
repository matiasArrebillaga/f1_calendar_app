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
            necesita_vueltas = self.codigo_sesion in ('FP1', 'FP2', 'FP3', 'Q', 'SQ')
            sesion.load(laps=necesita_vueltas, telemetry=False, weather=False)
            if self.codigo_sesion in ('FP1', 'FP2', 'FP3'):
                self._agregar_datos_practica(sesion)
            elif self.codigo_sesion in ('Q', 'SQ'):
                self._agregar_datos_clasificacion(sesion)
            self.terminado.emit(sesion)
        except Exception as e:
            self.error.emit(str(e))

    @staticmethod
    def _agregar_datos_practica(sesion):
        resultados = sesion.results
        vueltas = sesion.laps
        vueltas_validas = vueltas[vueltas['LapTime'].notna()]

        mejores = vueltas_validas.groupby('Driver')['LapTime'].min()
        cantidad_vueltas = vueltas_validas.groupby('Driver').size()
        resultados['BestLapTime'] = resultados['Abbreviation'].map(mejores)
        resultados['Laps'] = resultados['Abbreviation'].map(cantidad_vueltas)
        resultados['Position'] = resultados['BestLapTime'].rank(
            method='min', ascending=True, na_option='keep'
        )
        resultados.sort_values(
            ['Position', 'BestLapTime'], na_position='last', inplace=True
        )

    @staticmethod
    def _agregar_datos_clasificacion(sesion):
        resultados = sesion.results
        tiempos = (
            resultados['Q3']
            .combine_first(resultados['Q2'])
            .combine_first(resultados['Q1'])
        )
        resultados['BestLapTime'] = tiempos
        resultados.sort_values('Position', na_position='last', inplace=True)
