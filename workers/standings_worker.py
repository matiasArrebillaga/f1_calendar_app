from PySide6.QtCore import QThread, Signal

from core import historial
from core.calendario import obtener_calendario
from workers.pilotos_worker import cargar_temporada


class SinDatos(ValueError):
    """El año no tiene clasificación: no es un problema de red."""


class StandingsWorker(QThread):
    # emite {'pilotos': [dict], 'equipos': [dict], 'ronda', 'total_rondas',
    # 'sprints_restantes', 'actualizando'}; ronda y total_rondas pueden ser
    # None si no se pudieron averiguar. Con la temporada en curso emite dos
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
            'total_rondas': None,
            'sprints_restantes': 0,
        }
        if not datos['pilotos']:
            raise SinDatos(f"Sin clasificación para {self.year}")

        # Lo que sigue sólo alimenta "puntos en juego": si falla, la tabla se
        # muestra igual.
        try:
            # Ya lo bajó CalendarView: sale del caché.
            calendario = obtener_calendario(self.year)
            datos['total_rondas'] = len(calendario)
            if datos['ronda'] is not None:
                # EventFormat: 'sprint', 'sprint_shootout' o 'sprint_qualifying'
                # según el año; los fines de semana normales son 'conventional'.
                faltan = calendario[calendario['RoundNumber'] > datos['ronda']]
                datos['sprints_restantes'] = int(
                    faltan['EventFormat'].str.contains('sprint').sum())
        except Exception:
            pass
        return datos
