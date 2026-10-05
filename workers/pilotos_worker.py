import threading
from datetime import date

from PySide6.QtCore import QThread, Signal

from core import historial
from core.fotos import obtener_ruta_foto, obtener_ruta_logo

# Temporadas incompletas ya refrescadas en esta sesión de la app: la API se
# consulta una vez por arranque, no cada vez que se vuelve a la pestaña.
_ACTUALIZADAS = set()
# Pilotos y Clasificación leen la misma base: sin esto, pasar rápido de una
# pestaña a la otra bajaba la misma temporada dos veces.
_LOCK_ACTUALIZAR = threading.Lock()


def anio_actual():
    return date.today().year


def actualizar_temporada(con, year):
    """Baja la temporada si le pueden faltar datos. Sin red, se queda con lo
    guardado; sólo falla si no hay nada guardado que mostrar."""
    with _LOCK_ACTUALIZAR:
        if historial.temporada_completa(con, year) or year in _ACTUALIZADAS:
            return
        guardada = historial.temporada_guardada(con, year)
        # En curso: sólo las rondas nuevas. Una que ya terminó se baja entera
        # una última vez, por si corrigieron resultados después de guardarla.
        desde = None
        if guardada and year >= anio_actual():
            desde = (historial.ultima_ronda(con, year) or 0) + 1
        try:
            historial.descargar_temporada(con, year, desde=desde)
        except Exception:
            if not guardada:
                raise
            return
        _ACTUALIZADAS.add(year)
        if year >= anio_actual():
            try:
                historial.completar_headshots(con, year)
            except Exception:
                pass      # sin foto oficial quedan Wikipedia o el placeholder


def cargar_temporada(con, year, leer, emitir):
    """Emite lo guardado al toque y, si la temporada puede estar desactualizada,
    la baja y vuelve a emitir: Jolpica a veces tarda más de un minuto.
    `leer(con)` arma los datos de la vista."""
    pendiente = not historial.temporada_completa(con, year) and year not in _ACTUALIZADAS
    if pendiente and historial.temporada_guardada(con, year):
        try:
            emitir({**leer(con), "actualizando": True})
        except Exception:
            pass          # lo guardado no alcanza para mostrar: se espera la descarga
    actualizar_temporada(con, year)
    # Se lee después del lock: si la descarga la hizo la otra pestaña, igual
    # llegan los datos nuevos.
    emitir({**leer(con), "actualizando": False})


class PilotosWorker(QThread):
    terminado = Signal(object)   # {'pilotos': [dict], 'equipos': [dict], 'actualizando'}
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
            cargar_temporada(con, self.year, self._leer, self.terminado.emit)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            con.close()

    def _leer(self, con):
        return {"pilotos": historial.pilotos_temporada(con, self.year),
                "equipos": historial.equipos_temporada(con, self.year)}



class FotosWorker(QThread):
    foto_lista = Signal(str, str)   # driver_id, ruta local
    logo_listo = Signal(str, str)   # constructor_id, ruta local

    def __init__(self, pilotos, equipos=()):
        super().__init__()
        self.pilotos = pilotos
        self.equipos = equipos

    def run(self):
        # Primero los logos: son pocos y chicos.
        for equipo in self.equipos:
            if self.isInterruptionRequested():
                return
            ruta = obtener_ruta_logo(equipo["constructor_id"])
            if ruta:
                self.logo_listo.emit(equipo["constructor_id"], ruta)
        for piloto in self.pilotos:
            if self.isInterruptionRequested():
                return    # cambiaron de año: estas fotos ya no hacen falta
            ruta = obtener_ruta_foto(piloto["driver_id"], piloto.get("headshot_url"),
                                     piloto.get("url_wiki"))
            if ruta:
                self.foto_lista.emit(piloto["driver_id"], ruta)
