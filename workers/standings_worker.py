from PySide6.QtCore import QThread, Signal

from core import historial
from core.calendario import en_juego, obtener_calendario, rondas_y_sprints
from workers.pilotos_worker import cargar_temporada


class SinDatos(ValueError):
    """El año no tiene clasificación: no es un problema de red."""


class StandingsWorker(QThread):
    # emite {'pilotos': [dict], 'equipos': [dict], 'ronda', 'en_juego',
    # 'actualizando'}; ronda es None si todavía no se corrió ninguna y
    # en_juego trae {'pilotos', 'equipos'} de calendario.en_juego. Con la temporada en curso emite dos
    # veces: lo guardado (actualizando=True) y lo recién bajado.
    terminado = Signal(object)
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year
        self.sin_datos = False

    def run(self):
        # Sale de la base del historial (la misma de la pestaña Pilotos): las
        # temporadas terminadas vienen en el build y no piden nada a la red.
        try:
            con = historial.abrir_base()
        except Exception as e:
            self.error.emit(str(e))
            return
        try:
            cargar_temporada(con, self.year, self._leer, self.terminado.emit)
        except Exception as e:
            self.sin_datos = isinstance(e, SinDatos)
            self.error.emit(str(e))
        finally:
            con.close()

    def _leer(self, con):
        datos = {
            'pilotos': historial.pilotos_temporada(con, self.year),
            'equipos': historial.equipos_temporada(con, self.year),
            'ronda': historial.ultima_ronda(con, self.year),
        }
        if not datos['pilotos']:
            raise SinDatos(f"Sin clasificación para {self.year}")

        # El calendario sólo alimenta "puntos en juego": si falla, la tabla se
        # muestra igual.
        try:
            # Ya lo bajó CalendarView: sale del caché.
            rondas = rondas_y_sprints(obtener_calendario(self.year))
        except Exception:
            rondas = []
        datos['en_juego'] = {solapa: en_juego(datos['ronda'], rondas, solapa)
                             for solapa in ("pilotos", "equipos")}
        return datos
