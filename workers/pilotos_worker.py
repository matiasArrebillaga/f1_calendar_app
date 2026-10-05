from datetime import date

from PySide6.QtCore import QThread, Signal

from core import historial
from core.fotos import obtener_ruta_foto

# Temporadas en curso ya refrescadas en esta sesión de la app: la API se
# consulta una vez por arranque, no cada vez que se vuelve a la pestaña.
_ACTUALIZADAS = set()


def anio_actual():
    return date.today().year


class PilotosWorker(QThread):
    terminado = Signal(object)   # {'pilotos': [dict], 'equipos': [dict]}
    error = Signal(str)

    def __init__(self, year):
        super().__init__()
        self.year = year

    def run(self):
        try:
            con = historial.abrir_base()
        except Exception as e:
            self.error.emit(str(e))
            return
        try:
            self._actualizar(con)
            datos = {"pilotos": historial.pilotos_temporada(con, self.year),
                     "equipos": historial.equipos_temporada(con, self.year)}
        except Exception as e:
            self.error.emit(str(e))
            return
        finally:
            con.close()
        self.terminado.emit(datos)

    def _actualizar(self, con):
        guardada = historial.temporada_guardada(con, self.year)
        en_curso = self.year >= anio_actual()
        if guardada and (not en_curso or self.year in _ACTUALIZADAS):
            return
        try:
            historial.descargar_temporada(con, self.year)
        except Exception:
            if not guardada:
                raise     # no hay nada guardado que mostrar
            return        # sin red: se muestra lo último guardado
        _ACTUALIZADAS.add(self.year)
        if en_curso:
            try:
                historial.completar_headshots(con, self.year)
            except Exception:
                pass      # sin foto oficial quedan Wikipedia o el placeholder


class FotosWorker(QThread):
    foto_lista = Signal(str, str)   # driver_id, ruta local

    def __init__(self, pilotos):
        super().__init__()
        self.pilotos = pilotos

    def run(self):
        for piloto in self.pilotos:
            if self.isInterruptionRequested():
                return    # cambiaron de año: estas fotos ya no hacen falta
            ruta = obtener_ruta_foto(piloto["driver_id"], piloto.get("headshot_url"),
                                     piloto.get("url_wiki"))
            if ruta:
                self.foto_lista.emit(piloto["driver_id"], ruta)
