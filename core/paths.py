import sys
import os

# La carpeta del proyecto, no la de trabajo: correr desde otro lado creaba una
# base y cachés vacíos ahí.
PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(ruta_relativa):
    """Recursos empaquetados de SOLO LECTURA (siempre presentes, vengan
    del build o del proyecto en desarrollo)."""
    base_path = getattr(sys, '_MEIPASS', PROYECTO)
    return os.path.join(base_path, ruta_relativa)


def data_path(nombre_carpeta):
    """Carpeta de datos ESCRIBIBLE, generada en runtime: %LOCALAPPDATA% en el
    .exe (al lado del exe puede no haber permiso, p. ej. en Program Files) o
    el proyecto, si corrés como script."""
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
                            'F1CalendarApp')
    else:
        base = PROYECTO
    return os.path.join(base, nombre_carpeta)


def ruta_cache(nombre_carpeta, nombre_archivo):
    """Busca primero en los recursos empaquetados (solo lectura); si no
    está ahí, devuelve la ruta escribible (para descargar/generar ahí)."""
    ruta_empaquetada = resource_path(os.path.join(nombre_carpeta, nombre_archivo))
    if os.path.exists(ruta_empaquetada):
        return ruta_empaquetada, False  # (ruta, es_escribible)

    ruta_escribible = os.path.join(data_path(nombre_carpeta), nombre_archivo)
    return ruta_escribible, True