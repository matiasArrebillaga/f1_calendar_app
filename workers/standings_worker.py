from core.calendario import en_juego, obtener_calendario, rondas_y_sprints
from workers.pilotos_worker import PilotosWorker, SinDatos


class StandingsWorker(PilotosWorker):
    """Lo mismo que PilotosWorker (la misma base, las temporadas terminadas
    sin pedir nada a la red) más 'en_juego': {'pilotos', 'equipos'} de
    calendario.en_juego. Un año sin clasificación da error con sin_datos."""

    def _leer(self, con):
        datos = super()._leer(con)
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
