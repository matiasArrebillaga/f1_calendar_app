"""Iconos Lucide (ISC) rasterizados para Qt.

Dos cosas que Qt no hace solo y por eso existe este módulo:

- Los SVG de Lucide traen `stroke="currentColor"`, que es una convención de CSS:
  Qt no la resuelve y el icono sale sin color. Hay que sustituirla por el color
  concreto antes de renderizar.
- Un QIcon construido desde el SVG se rasteriza a 1x, así que en pantallas HiDPI
  sale borroso. Se renderiza a `tamano * devicePixelRatio` y se le marca el dpr,
  que es lo que le dice a Qt que lo dibuje en su tamaño lógico pero con todos
  los píxeles.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from core.paths import resource_path

# De la paleta de style.qss. El .qss no puede alimentar a Python, así que los
# pocos tonos que se pintan desde código viven acá y no repetidos en cada widget.
MUTED = "#A4AEBC"
PRIMARIO = "#F3F6F9"
DATO = "#52DEEC"       # tiempos, diferencias, cuenta regresiva, barras
BORDE = "#2D3541"
# Medallas del 1º, 2º y 3º: (degradé arriba, degradé abajo, número). El número
# oscuro tiene que pasar AA contra el tono de abajo, que es el más oscuro.
PODIO = (
    ("#F3D27A", "#C99A2E", "#1C1405"),   # oro
    ("#E6EBF0", "#A9B4BF", "#12161C"),   # plata
    ("#E8AE7C", "#B9763E", "#1C0F05"),   # bronce
)

# Mismo criterio que CalendarEventCard._cache_pixmaps: rasterizar es caro y los
# iconos se piden una vez por botón, pero con los mismos pocos argumentos.
_cache = {}


def _rasterizar(nombre, color, tamano, dpr):
    ruta = resource_path(os.path.join("assets", "icons", f"{nombre}.svg"))
    with open(ruta, encoding="utf-8") as archivo:
        svg = archivo.read().replace("currentColor", color)

    lado = round(tamano * dpr)
    imagen = QImage(lado, lado, QImage.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.transparent)

    pintor = QPainter(imagen)
    QSvgRenderer(svg.encode("utf-8")).render(pintor)
    pintor.end()

    imagen.setDevicePixelRatio(dpr)
    return QPixmap.fromImage(imagen)


def icono(nombre, color, tamano=16):
    """QIcon de un icono de Lucide, pintado en `color` y nítido en HiDPI.

    `nombre` es el del archivo en assets/icons/ sin extensión.
    """
    pantalla = QGuiApplication.primaryScreen()
    dpr = pantalla.devicePixelRatio() if pantalla is not None else 1.0

    clave = (nombre, color, tamano, dpr)
    if clave not in _cache:
        _cache[clave] = QIcon(_rasterizar(nombre, color, tamano, dpr))
    return _cache[clave]


def franja_equipo(color):
    """Franja vertical con el color del equipo, para usar como icono de celda.

    Con un icono alcanza: un QStyledItemDelegate sólo para pintar 3 px de color
    sería bastante más código. `color` es '#RRGGBB' o 'RRGGBB' (como viene en
    session.results['TeamColor']); vacío o inválido → None, sin franja.
    """
    if not color or not isinstance(color, str):
        return None
    color = color if color.startswith("#") else f"#{color}"
    if not QColor(color).isValid():
        return None
    clave = ("franja", color)
    if clave not in _cache:
        pixmap = QPixmap(4, 16)
        pixmap.fill(Qt.transparent)
        pintor = QPainter(pixmap)
        pintor.fillRect(0, 1, 3, 14, QColor(color))
        pintor.end()
        _cache[clave] = QIcon(pixmap)
    return _cache[clave]
