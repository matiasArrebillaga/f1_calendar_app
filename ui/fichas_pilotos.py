"""Piezas de la pestaña Pilotos: foto, tarjetas, grilla y fichas.

Los datos llegan como dicts planos de core/historial.py; acá sólo se pintan.
"""
import os
import re

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
)
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QToolTip, QVBoxLayout, QWidget
)

from core.flags import CACHE_DIR_NOMBRE, CODIGOS_PAIS
from core.i18n import traducir_evento, traducir_nacionalidad
from core.paths import ruta_cache
from ui.icons import ABANDONO, BORDE, DATO, MUTED, PANEL, PODIO, PRIMARIO, SUPERFICIE

ORO = PODIO[0][0]


def formato_celda(fila):
    """(texto, delta contra la largada, estado) de una celda de la tira."""
    posicion, texto = fila["posicion"], fila["posicion_texto"]
    if posicion is not None:
        largada = fila["largada"]
        if not largada:
            delta = "boxes"
        elif largada > posicion:
            delta = f"▲{largada - posicion}"
        elif largada < posicion:
            delta = f"▼{posicion - largada}"
        else:
            delta = "="
        return f"P{posicion}", delta, "podio" if posicion <= 3 else "normal"
    if texto in ("D", "E"):
        return "DSQ", "", "abandono"
    if texto == "F":
        return "DNQ", "", "ausente"
    if texto == "W":
        return "DNS", "", "ausente"
    return "DNF", "", "abandono"


def sigla(piloto):
    """Ergast no tiene siglas para los pilotos viejos: tres letras del apellido."""
    return piloto.get("codigo") or (piloto.get("apellido") or "?")[:3].upper()


def _numero(valor):
    return None if valor is None else f"{valor:g}"


def _promedio(valor):
    return None if valor is None else f"{valor:.1f}"


def _bandera(pais):
    """Sólo las banderas que ya están en disco (las baja el calendario): bajarlas
    acá trabaría la UI. None si no hay."""
    codigo = CODIGOS_PAIS.get(pais)
    if codigo is None:
        return None
    ruta, _ = ruta_cache(CACHE_DIR_NOMBRE, f"{codigo}.png")
    pixmap = QPixmap(ruta) if os.path.exists(ruta) else QPixmap()
    return None if pixmap.isNull() else pixmap


def _tooltip_carrera(fila):
    largada = f"P{fila['largada']}" if fila["largada"] else "boxes"
    texto, _, _ = formato_celda(fila)
    llegada = f"llegó {texto}" if fila["posicion"] is not None else texto
    return f"R{fila['ronda']} · {traducir_evento(fila['gp'])}\nLargó {largada} · {llegada}"


class FotoPiloto(QWidget):
    """Foto recortada en cuadrado sobre un degradé del color del equipo. Sin
    foto (todavía bajando, o no existe ninguna) muestra la sigla."""

    def __init__(self, lado, marco=True):
        super().__init__()
        self.setFixedSize(lado, lado)
        self._marco = marco   # False: sin degradé, para recortarla sobre CabeceraColor
        self.driver_id = None
        self._sigla = ""
        self._numero = ""
        self._color = QColor(MUTED)
        self._pixmap = None

    def set_piloto(self, driver_id, sigla_piloto, numero, color):
        self.driver_id = driver_id
        self._sigla = sigla_piloto
        self._numero = str(numero) if numero else ""
        self._color = QColor(color or MUTED)
        self._pixmap = None
        self.update()

    def set_foto(self, ruta):
        original = QPixmap(ruta)
        if original.isNull():
            return
        # Se escala una sola vez (el tamaño es fijo) y se recorta anclado
        # arriba, que es donde están las caras.
        dpr = self.devicePixelRatioF()
        lado = round(self.width() * dpr)
        escalado = original.scaled(lado, lado, Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
        self._pixmap = escalado.copy((escalado.width() - lado) // 2, 0, lado, lado)
        self._pixmap.setDevicePixelRatio(dpr)
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        borde = QPainterPath()
        borde.addRoundedRect(rect, 4, 4)
        pintor.setClipPath(borde)

        if self._marco:
            tono = QColor(self._color)
            tono.setAlpha(150)
            degrade = QLinearGradient(0, 0, 0, rect.height())
            degrade.setColorAt(0, tono)
            degrade.setColorAt(1, QColor(SUPERFICIE))
            pintor.fillRect(rect, degrade)

        if self._pixmap is not None:
            pintor.drawPixmap(0, 0, self._pixmap)
        else:
            # Titillium se pixela por debajo de 17 px: las fotos chicas (las
            # de las tarjetas de equipo) usan la letra de la interfaz.
            fuente = QFont("Titillium Web") if self.height() >= 68 else QFont()
            fuente.setPixelSize(max(17, self.height() // 4) if self.height() >= 68
                                else round(self.height() * 0.32))
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QColor(PRIMARIO))
            pintor.drawText(rect, Qt.AlignCenter, self._sigla)

        if self._numero and self.width() >= 100:
            fuente = QFont()
            fuente.setPixelSize(14)
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QColor(PRIMARIO))
            pintor.drawText(rect.adjusted(8, 6, -8, -6), Qt.AlignLeft | Qt.AlignTop, self._numero)


class _TarjetaClickeable(QFrame):
    """Click o Enter/Espacio emiten `clicked(clave)`."""
    clicked = Signal(str)

    def __init__(self, nombre_objeto, clave):
        super().__init__()
        self.setObjectName(nombre_objeto)
        self.clave = clave
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, evento):
        evento.accept()   # sin esto, el release no llega a la tarjeta

    def mouseReleaseEvent(self, evento):
        if evento.button() == Qt.LeftButton and self.rect().contains(evento.position().toPoint()):
            self.clicked.emit(self.clave)

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit(self.clave)
            return
        super().keyPressEvent(evento)


class TarjetaPiloto(_TarjetaClickeable):
    ANCHO = 140

    def __init__(self, piloto, color):
        super().__init__("tarjetaPiloto", piloto["driver_id"])
        self.setFixedWidth(self.ANCHO)
        self.setToolTip(f"{piloto['nombre']} {piloto['apellido']}")

        self.foto = FotoPiloto(self.ANCHO - 2)   # 1 px de borde por lado
        self.foto.set_piloto(piloto["driver_id"], sigla(piloto), piloto.get("numero"), color)
        franja = QFrame()
        franja.setFixedHeight(3)
        franja.setStyleSheet(f"background-color: {color or MUTED};")

        codigo = QLabel(sigla(piloto))
        codigo.setObjectName("siglaTarjeta")
        equipo = QLabel(piloto.get("equipo") or "")
        equipo.setObjectName("detalleTarjeta")
        puntos = QLabel(_numero(piloto.get("puntos")) or "")
        puntos.setObjectName("puntosTarjeta")

        fila = QHBoxLayout()
        fila.setSpacing(6)
        fila.addWidget(equipo, 1)
        fila.addWidget(puntos)
        pie = QVBoxLayout()
        pie.setContentsMargins(10, 6, 10, 8)
        pie.setSpacing(0)
        pie.addWidget(codigo)
        pie.addLayout(fila)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.foto)
        layout.addWidget(franja)
        layout.addLayout(pie)


class LogoEquipo(QWidget):
    """Logo oficial sobre el cuadrado blanco con el que lo publica F1. Sin logo
    (equipos viejos, o todavía bajando) muestra las iniciales."""

    def __init__(self, lado, constructor_id, nombre):
        super().__init__()
        self.setFixedSize(lado, lado)
        self.constructor_id = constructor_id
        # "Cadillac F1 Team" → CAD, no CFT.
        palabras = [p for p in re.findall(r"[^\W\d_]+", nombre) if p not in ("F", "Team")]
        if len(palabras) > 1:
            self.iniciales = "".join(p[0] for p in palabras[:3]).upper()
        else:
            self.iniciales = (palabras[0] if palabras else nombre)[:3].upper()
        self._pixmap = None

    def set_logo(self, ruta):
        original = QPixmap(ruta)
        if original.isNull():
            return
        dpr = self.devicePixelRatioF()
        lado = round(self.width() * dpr)
        self._pixmap = original.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap.setDevicePixelRatio(dpr)
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        borde = QPainterPath()
        borde.addRoundedRect(rect, 8, 8)
        if self._pixmap is not None:
            pintor.fillPath(borde, QColor("#FFFFFF"))
            pintor.setClipPath(borde)
            ancho = self._pixmap.width() / self._pixmap.devicePixelRatio()
            alto = self._pixmap.height() / self._pixmap.devicePixelRatio()
            pintor.drawPixmap(QPointF((self.width() - ancho) / 2, (self.height() - alto) / 2),
                              self._pixmap)
            return
        pintor.fillPath(borde, QColor(SUPERFICIE))
        pintor.setPen(QPen(QColor(BORDE), 1))
        pintor.drawPath(borde)
        fuente = QFont()
        fuente.setPixelSize(15)
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setPen(QColor(PRIMARIO))
        pintor.drawText(rect, Qt.AlignCenter, self.iniciales)


class TarjetaEquipo(_TarjetaClickeable):
    """Logo, nombre y posición arriba; los dos pilotos principales abajo; una
    barra con los puntos contra los del líder."""
    ANCHO_MIN = 320

    def __init__(self, equipo, color, pilotos, victorias, puntos_lider):
        super().__init__("tarjetaEquipo", equipo["constructor_id"])
        self.setMinimumWidth(self.ANCHO_MIN)
        color = color or MUTED

        franja = QFrame()
        franja.setFixedHeight(3)
        franja.setStyleSheet(f"background-color: {color};")

        self.logo = LogoEquipo(52, equipo["constructor_id"], equipo["nombre"])
        nombre = QLabel(equipo["nombre"])
        nombre.setObjectName("nombreTarjetaEquipo")
        puntos = equipo["puntos"] or 0
        partes = [f"{_numero(puntos)} pts"]
        if victorias:
            partes.append("1 victoria" if victorias == 1 else f"{victorias} victorias")
        detalle = QLabel("  ·  ".join(partes))
        detalle.setObjectName("detalleTarjeta")
        posicion = QLabel(f"P{equipo['posicion']}" if equipo["posicion"] else "")
        posicion.setObjectName("posTarjeta")
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(nombre)
        textos.addWidget(detalle)
        arriba = QHBoxLayout()
        arriba.setContentsMargins(15, 12, 15, 10)
        arriba.setSpacing(14)
        arriba.addWidget(self.logo)
        arriba.addLayout(textos, 1)
        arriba.addWidget(posicion)

        self.fotos = []
        caja_pilotos = QFrame()
        caja_pilotos.setObjectName("pilotosTarjeta")
        fila_pilotos = QHBoxLayout(caja_pilotos)
        fila_pilotos.setContentsMargins(0, 0, 0, 0)
        fila_pilotos.setSpacing(0)
        for i, piloto in enumerate(pilotos[:2]):
            celda = QFrame()
            celda.setObjectName("pilotoTarjeta")
            celda.setProperty("primera", i == 0)
            foto = FotoPiloto(34)
            foto.set_piloto(piloto["driver_id"], sigla(piloto), None, color)
            self.fotos.append(foto)
            codigo = QLabel(sigla(piloto))
            codigo.setObjectName("siglaMini")
            pts = QLabel(f"{_numero(piloto['puntos'] or 0)} pts")
            pts.setObjectName("detalleTarjeta")
            fila = QHBoxLayout(celda)
            fila.setContentsMargins(11, 7, 12, 7)
            fila.setSpacing(8)
            fila.addWidget(foto)
            fila.addWidget(codigo)
            fila.addStretch()
            fila.addWidget(pts)
            fila_pilotos.addWidget(celda, 1)

        barra = BarraMedia(hacia_izquierda=False)
        barra.setFixedHeight(4)
        barra.set_valor(puntos / puntos_lider if puntos_lider else 0, color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(franja)
        layout.addLayout(arriba)
        if pilotos:
            layout.addWidget(caja_pilotos)
        layout.addWidget(barra)


class ScrollSinFlechas(QScrollArea):
    """QScrollArea que deja pasar ←/→ hasta MainWindow, que cambia de año con
    ellas. Apagar el scroll horizontal no alcanza: QAbstractScrollArea se queda
    con esas teclas igual."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setWidget(self, widget):
        # "transparente" en style.qss: si no, la regla global de QWidget pinta
        # una franja más oscura que el degradé de la vista.
        widget.setObjectName("transparente")
        super().setWidget(widget)

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Left, Qt.Key_Right):
            evento.ignore()
            return
        super().keyPressEvent(evento)


class GrillaTarjetas(ScrollSinFlechas):
    """Tantas columnas como entren a lo ancho. Las tarjetas de ancho fijo
    (pilotos) se alinean a la izquierda; las que pueden crecer (equipos) se
    reparten todo el ancho."""
    ESPACIO = 10

    def __init__(self):
        super().__init__()
        contenedor = QWidget()
        self._grilla = QGridLayout(contenedor)
        self._grilla.setContentsMargins(0, 0, 0, 16)
        self._grilla.setSpacing(self.ESPACIO)
        self._grilla.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setWidget(contenedor)
        self._tarjetas = []
        self._columnas = 0

    def tarjetas(self):
        return list(self._tarjetas)

    def set_tarjetas(self, tarjetas):
        for vieja in self._tarjetas:
            self._grilla.removeWidget(vieja)
            vieja.hide()   # deleteLater tarda: sin esto sigue pintada fuera del layout
            vieja.deleteLater()
        self._tarjetas = list(tarjetas)
        for tarjeta in self._tarjetas:
            # Con padre antes de mostrarse: si no, show() la vuelve una ventana suelta.
            tarjeta.setParent(self.widget())
        self._columnas = 0
        self._acomodar()

    def _acomodar(self):
        if not self._tarjetas:
            return
        primera = self._tarjetas[0]
        paso = primera.minimumWidth() + self.ESPACIO
        columnas = max(1, (self.viewport().width() + self.ESPACIO) // paso)
        if columnas == self._columnas:
            return
        self._columnas = columnas
        estiran = primera.maximumWidth() > primera.minimumWidth()
        self._grilla.setAlignment(Qt.AlignTop if estiran else Qt.AlignTop | Qt.AlignLeft)
        for columna in range(self._grilla.columnCount()):
            self._grilla.setColumnStretch(columna, 1 if estiran and columna < columnas else 0)
        for columna in range(self._grilla.columnCount(), columnas if estiran else 0):
            self._grilla.setColumnStretch(columna, 1)
        for tarjeta in self._tarjetas:
            self._grilla.removeWidget(tarjeta)
        for i, tarjeta in enumerate(self._tarjetas):
            self._grilla.addWidget(tarjeta, i // columnas, i % columnas)
            tarjeta.show()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._acomodar()


class FilaStats(QWidget):
    """Cajas KPI (mismo estilo que Clasificación) en una grilla de `columnas`.
    Con `tira`, un solo panel dividido por líneas en vez de cajas sueltas."""

    def __init__(self, etiquetas, columnas, dato=False, tira=False):
        super().__init__()
        self._dato = dato
        self._valores = []
        grilla = QGridLayout(self)
        grilla.setContentsMargins(0, 0, 0, 0)
        grilla.setSpacing(0 if tira else 8)
        if tira:
            self.setObjectName("tiraStats")
            self.setAttribute(Qt.WA_StyledBackground, True)
        for i, texto in enumerate(etiquetas):
            caja = QFrame()
            caja.setObjectName("celdaTira" if tira else "kpi")
            caja.setProperty("primera", i % columnas == 0)
            etiqueta = QLabel(texto.upper())
            etiqueta.setObjectName("etiquetaRonda")
            valor = QLabel("—")
            valor.setObjectName("valorKpi")
            columna = QVBoxLayout(caja)
            columna.setContentsMargins(12, 8, 12, 8)
            columna.setSpacing(2)
            columna.addWidget(etiqueta)
            columna.addWidget(valor)
            grilla.addWidget(caja, i // columnas, i % columnas)
            self._valores.append(valor)

    def set_valores(self, valores):
        for etiqueta, valor in zip(self._valores, valores):
            texto = "—" if valor is None else str(valor)
            etiqueta.setText(f"<span style='color:{DATO};'>{texto}</span>" if self._dato else texto)


class CabeceraColor(QWidget):
    """Panel con el color del equipo degradado de izquierda a derecha y, si se
    le pasa, el dorsal de fondo en contorno."""

    def __init__(self):
        super().__init__()
        self._color = QColor(MUTED)
        self._dorsal = ""

    def set_color(self, color, dorsal=None):
        self._color = QColor(color or MUTED)
        self._dorsal = str(dorsal) if dorsal else ""
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        borde = QPainterPath()
        borde.addRoundedRect(rect, 6, 6)
        pintor.fillPath(borde, QColor(PANEL))
        degrade = QLinearGradient(0, 0, rect.width(), 0)
        for parada, alfa in ((0, 140), (0.38, 46), (0.72, 0)):
            tono = QColor(self._color)
            tono.setAlpha(alfa)
            degrade.setColorAt(parada, tono)
        pintor.fillPath(borde, degrade)

        if self._dorsal:
            fuente = QFont("Titillium Web")
            fuente.setPixelSize(round(self.height() * 1.15))
            fuente.setWeight(QFont.Black)
            ancho = QFontMetrics(fuente).horizontalAdvance(self._dorsal)
            texto = QPainterPath()
            texto.addText(rect.width() - 330 - ancho, self.height() * 0.98, fuente, self._dorsal)
            pintor.setClipPath(borde)
            pintor.strokePath(texto, QPen(QColor(255, 255, 255, 24), 1))
            pintor.setClipping(False)

        pintor.setPen(QPen(QColor(BORDE), 1))
        pintor.drawPath(borde)


class FilaGrandes(QWidget):
    """Los pocos números que importan, grandes y separados por líneas."""

    def __init__(self, etiquetas):
        super().__init__()
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)
        self._valores = []
        for texto in etiquetas:
            caja = QFrame()
            caja.setObjectName("grande")
            etiqueta = QLabel(texto.upper())
            etiqueta.setObjectName("etiquetaRonda")
            valor = QLabel("—")
            valor.setObjectName("valorGrande")
            columna = QVBoxLayout(caja)
            columna.setContentsMargins(22, 0, 22, 0)
            columna.setSpacing(0)
            columna.addWidget(etiqueta)
            columna.addWidget(valor)
            fila.addWidget(caja)
            self._valores.append(valor)

    def set_valores(self, valores):
        for etiqueta, valor in zip(self._valores, valores):
            etiqueta.setText("—" if valor is None else str(valor))


class GraficoPosiciones(QWidget):
    """Una columna por carrera: dónde largó (círculo hueco) y dónde llegó (punto,
    oro si fue podio). Sin llegada, el motivo (DNF, DSQ...) abajo de todo."""
    IZQ, ARRIBA, ABAJO = 34, 12, 46

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(260)
        self.setMouseTracking(True)
        self._filas = []
        self._banderas = {}

    def carreras(self):
        return list(self._filas)

    def set_resultados(self, filas):
        self._filas = list(filas)
        self._banderas = {f.get("pais"): _bandera(f.get("pais")) for f in self._filas}
        self.update()

    def _escala(self):
        # Hasta 20 siempre; más si la grilla fue más larga (años 50 a 90).
        fondo = max([20] + [f["largada"] or 0 for f in self._filas]
                    + [f["posicion"] or 0 for f in self._filas])
        ancho_col = (self.width() - self.IZQ) / max(1, len(self._filas))
        alto = self.height() - self.ARRIBA - self.ABAJO
        return fondo, ancho_col, lambda p: self.ARRIBA + (p - 1) * alto / (fondo - 1)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        fuente = QFont()
        fuente.setPixelSize(12)
        pintor.setFont(fuente)
        if not self._filas:
            pintor.setPen(QColor(MUTED))
            pintor.drawText(self.rect(), Qt.AlignLeft | Qt.AlignTop, "Sin carreras disputadas.")
            return

        fondo, ancho_col, y = self._escala()
        for p in [1] + list(range(5, fondo + 1, 5)):
            pluma = QPen(QColor(BORDE), 1)
            if p != 1:
                pluma.setDashPattern([2, 4])
            pintor.setPen(pluma)
            pintor.drawLine(QPointF(self.IZQ, y(p)), QPointF(self.width(), y(p)))
            pintor.setPen(QColor(MUTED))
            pintor.drawText(QRectF(0, y(p) - 8, self.IZQ - 8, 16),
                            Qt.AlignRight | Qt.AlignVCenter, f"P{p}")

        base = self.height() - self.ABAJO
        for i, fila in enumerate(self._filas):
            x = self.IZQ + ancho_col * (i + 0.5)
            texto, _, estado = formato_celda(fila)
            largada, llegada = fila["largada"], fila["posicion"]
            y_largada = y(largada) if largada else None
            y_llegada = y(llegada) if llegada is not None else base

            if llegada is None:
                color_linea = QColor(ABANDONO)
            elif largada and largada > llegada:
                color_linea = QColor(DATO)
            else:
                color_linea = QColor(MUTED)
            if y_largada is not None and (llegada is None or largada != llegada):
                color_linea.setAlpha(180)
                pintor.setPen(QPen(color_linea, 2))
                pintor.drawLine(QPointF(x, y_largada), QPointF(x, y_llegada))
            if y_largada is not None:
                pintor.setPen(QPen(QColor(MUTED), 1.5))
                pintor.setBrush(QColor(PANEL))
                pintor.drawEllipse(QPointF(x, y_largada), 4, 4)

            if llegada is not None:
                pintor.setPen(Qt.NoPen)
                pintor.setBrush(QColor(ORO if llegada <= 3 else PRIMARIO))
                pintor.drawEllipse(QPointF(x, y_llegada), 5.5, 5.5)
            else:
                fuerte = QFont(fuente)
                fuerte.setBold(True)
                pintor.setFont(fuerte)
                pintor.setPen(QColor(ABANDONO if estado == "abandono" else MUTED))
                pintor.drawText(QRectF(x - 20, base + 2, 40, 14), Qt.AlignCenter, texto)
                pintor.setFont(fuente)

            bandera = self._banderas.get(fila.get("pais"))
            if bandera is not None:
                pintor.drawPixmap(QRectF(x - 8, self.height() - 18, 16, 12), bandera,
                                  QRectF(bandera.rect()))
            else:
                pintor.setPen(QColor(MUTED))
                pintor.drawText(QRectF(x - 20, self.height() - 20, 40, 16), Qt.AlignCenter,
                                (fila.get("pais") or "?")[:3].upper())

    def mouseMoveEvent(self, evento):
        if not self._filas:
            return
        _, ancho_col, _ = self._escala()
        i = int((evento.position().x() - self.IZQ) // ancho_col)
        if 0 <= i < len(self._filas):
            QToolTip.showText(evento.globalPosition().toPoint(), _tooltip_carrera(self._filas[i]), self)
        else:
            QToolTip.hideText()


class FichaPiloto(QWidget):
    def __init__(self):
        super().__init__()
        self.cabecera = CabeceraColor()
        self.cabecera.setFixedHeight(224)
        self.foto = FotoPiloto(214, marco=False)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombrePila")
        self.apellido = QLabel()
        self.apellido.setObjectName("apellidoFicha")
        self.meta = QLabel()
        self.meta.setObjectName("metaFicha")
        self.grandes = FilaGrandes(["Campeonato", "Puntos", "Victorias"])

        identidad = QVBoxLayout()
        identidad.setSpacing(0)
        identidad.addStretch()
        identidad.addWidget(self.nombre)
        identidad.addWidget(self.apellido)
        identidad.addSpacing(8)
        identidad.addWidget(self.meta)
        identidad.addSpacing(24)
        columna_grandes = QVBoxLayout()
        columna_grandes.addStretch()
        columna_grandes.addWidget(self.grandes)
        columna_grandes.addSpacing(24)
        fila = QHBoxLayout(self.cabecera)
        fila.setContentsMargins(10, 10, 4, 0)
        fila.setSpacing(14)
        fila.addWidget(self.foto, alignment=Qt.AlignBottom)
        fila.addLayout(identidad, 1)
        fila.addLayout(columna_grandes)

        self.stats_temporada = FilaStats(
            ["Podios", "Poles", "Abandonos", "Prom. llegada", "Prom. largada"],
            columnas=5, tira=True)
        self.titulo_grafico = QLabel()
        self.titulo_grafico.setObjectName("etiquetaRonda")
        self.grafico = GraficoPosiciones()
        titulo_carrera = QLabel("CARRERA COMPLETA")
        titulo_carrera.setObjectName("etiquetaRonda")
        self.stats_carrera = FilaStats(["Títulos", "Victorias", "Podios", "GPs", "Debut"],
                                       columnas=5, dato=True, tira=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.cabecera)
        layout.addSpacing(4)
        layout.addWidget(self.stats_temporada)
        layout.addSpacing(10)
        layout.addWidget(self.titulo_grafico)
        layout.addWidget(self.grafico)
        layout.addSpacing(6)
        layout.addWidget(titulo_carrera)
        layout.addWidget(self.stats_carrera)

    def mostrar(self, piloto, color, anio, stats, tira, carrera):
        self.cabecera.set_color(color, piloto.get("numero"))
        self.foto.set_piloto(piloto["driver_id"], sigla(piloto), None, color)
        self.nombre.setText(piloto["nombre"])
        self.apellido.setText(piloto["apellido"].upper())
        partes = []
        if piloto.get("equipo"):
            partes.append(f"<span style='color:{color or MUTED};'>●</span>&nbsp;{piloto['equipo']}")
        if piloto.get("numero"):
            partes.append(f"#{piloto['numero']}")
        if piloto.get("nacionalidad"):
            partes.append(traducir_nacionalidad(piloto["nacionalidad"]))
        if piloto.get("nacimiento"):
            partes.append(f"{anio - int(piloto['nacimiento'][:4])} años en {anio}")
        self.meta.setText("&nbsp;&nbsp;·&nbsp;&nbsp;".join(partes))

        self.grandes.set_valores([
            f"P{stats['posicion']}" if stats["posicion"] else None,
            _numero(stats["puntos"]), stats["victorias"]])
        self.stats_temporada.set_valores([
            stats["podios"], stats["poles"], stats["abandonos"],
            _promedio(stats["prom_llegada"]), _promedio(stats["prom_largada"])])
        self.titulo_grafico.setText(f"CARRERA POR CARRERA  ·  TEMPORADA {anio}")
        self.grafico.set_resultados(tira)
        self.stats_carrera.set_valores([carrera["titulos"], carrera["victorias"],
                                        carrera["podios"], carrera["gps"], carrera["debut"]])


class BarraMedia(QWidget):
    """Media barra del cara a cara: crece desde el centro hacia afuera. En el
    color del equipo si ese lado gana, gris si no."""

    def __init__(self, hacia_izquierda):
        super().__init__()
        self.setFixedHeight(10)
        self._izquierda = hacia_izquierda
        self._fraccion = 0
        self._color = None

    def set_valor(self, fraccion, color):
        self._fraccion, self._color = fraccion, color
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        ancho, alto = self.width(), self.height()
        pintor.setBrush(QColor(SUPERFICIE))
        pintor.drawRoundedRect(QRectF(0, 0, ancho, alto), 2, 2)
        largo = ancho * self._fraccion
        if largo <= 0:
            return
        if self._color:
            pintor.setBrush(QColor(self._color))
        else:
            gris = QColor(MUTED)
            gris.setAlpha(90)
            pintor.setBrush(gris)
        x = ancho - largo if self._izquierda else 0
        pintor.drawRoundedRect(QRectF(x, 0, largo, alto), 2, 2)


class FilaCaraACara(QWidget):
    def __init__(self, nombre):
        super().__init__()
        self.valor_a = QLabel()
        self.valor_a.setObjectName("valorDuelo")
        self.valor_a.setFixedWidth(56)
        self.valor_b = QLabel()
        self.valor_b.setObjectName("valorDuelo")
        self.valor_b.setFixedWidth(56)
        self.valor_b.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        etiqueta = QLabel(nombre.upper())
        etiqueta.setObjectName("etiquetaRonda")
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setFixedWidth(110)
        self.barra_a = BarraMedia(hacia_izquierda=True)
        self.barra_b = BarraMedia(hacia_izquierda=False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.valor_a)
        layout.addWidget(self.barra_a, 1)
        layout.addWidget(etiqueta)
        layout.addWidget(self.barra_b, 1)
        layout.addWidget(self.valor_b)

    def set_valores(self, a, b, color):
        self.valor_a.setText(f"{a:g}")
        self.valor_b.setText(f"{b:g}")
        for etiqueta, gana in ((self.valor_a, a > b), (self.valor_b, b > a)):
            etiqueta.setProperty("gana", gana)
            etiqueta.style().unpolish(etiqueta)
            etiqueta.style().polish(etiqueta)
        total = (a + b) or 1
        self.barra_a.set_valor(a / total, color if a > b else None)
        self.barra_b.set_valor(b / total, color if b > a else None)


class TiraDuelo(QWidget):
    """Un renglón por piloto y una columna por carrera: resaltada la celda del
    que llegó adelante."""

    def __init__(self):
        super().__init__()
        self._grilla = QGridLayout(self)
        self._grilla.setContentsMargins(0, 0, 0, 0)
        self._grilla.setSpacing(3)
        self._celdas = []

    def celdas(self):
        return list(self._celdas)

    def set_duelo(self, sigla_a, sigla_b, por_carrera, color):
        while self._grilla.count():
            item = self._grilla.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()   # deleteLater tarda: sin esto sigue pintada
                item.widget().deleteLater()
        for columna in range(self._grilla.columnCount()):
            self._grilla.setColumnStretch(columna, 0)
        self._celdas = []

        tono = QColor(color or MUTED)
        resaltado = (f"background-color: rgba({tono.red()}, {tono.green()}, {tono.blue()}, 80);"
                     f" color: {PRIMARIO};")
        for fila, texto in ((1, sigla_a), (2, sigla_b)):
            etiqueta = QLabel(texto)
            etiqueta.setObjectName("siglaDuelo")
            self._grilla.addWidget(etiqueta, fila, 0)
        for columna, carrera in enumerate(por_carrera, start=1):
            self._grilla.setColumnStretch(columna, 1)
            tooltip = f"R{carrera['ronda']} · {traducir_evento(carrera['gp'])}"
            cabeza = QLabel()
            cabeza.setObjectName("gpDuelo")
            cabeza.setAlignment(Qt.AlignCenter)
            cabeza.setToolTip(tooltip)
            bandera = _bandera(carrera["pais"])
            if bandera is not None:
                dpr = self.devicePixelRatioF()
                bandera = bandera.scaled(round(16 * dpr), round(12 * dpr),
                                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                bandera.setDevicePixelRatio(dpr)
                cabeza.setPixmap(bandera)
            else:
                cabeza.setText((carrera["pais"] or "?")[:3].upper())
            self._grilla.addWidget(cabeza, 0, columna)
            for fila, (clave, indice) in enumerate((("a", 0), ("b", 1)), start=1):
                texto, _, estado = formato_celda(carrera[clave])
                celda = QLabel(texto)
                celda.setObjectName("celdaDuelo")
                celda.setAlignment(Qt.AlignCenter)
                celda.setProperty("estado", estado)
                celda.setToolTip(tooltip)
                if carrera["adelante"] == indice:
                    celda.setStyleSheet(resaltado)
                self._grilla.addWidget(celda, fila, columna)
                self._celdas.append(celda)


def _lado_duelo(foto):
    nombre = QLabel()
    nombre.setObjectName("nombrePilaDuelo")
    nombre.setAlignment(Qt.AlignCenter)
    apellido = QLabel()
    apellido.setObjectName("apellidoDuelo")
    apellido.setAlignment(Qt.AlignCenter)
    columna = QVBoxLayout()
    columna.setSpacing(2)
    columna.addWidget(foto, alignment=Qt.AlignHCenter)
    columna.addSpacing(6)
    columna.addWidget(nombre)
    columna.addWidget(apellido)
    columna.addStretch()
    return columna, nombre, apellido


class FichaEquipo(QWidget):
    FILAS = (("clasificacion", "Clasificación"), ("carrera", "Carrera"),
             ("puntos", "Puntos"), ("victorias", "Victorias"), ("podios", "Podios"),
             ("poles", "Poles"))

    def __init__(self):
        super().__init__()
        self.cabecera = CabeceraColor()
        self.cabecera.setFixedHeight(118)
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("etiquetaRonda")
        self.nombre = QLabel()
        self.nombre.setObjectName("apellidoFicha")
        self.grandes = FilaGrandes(["Posición", "Puntos", "Victorias", "Dobletes"])
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addStretch()
        textos.addWidget(self.eyebrow)
        textos.addWidget(self.nombre)
        fila = QHBoxLayout(self.cabecera)
        fila.setContentsMargins(26, 16, 4, 20)
        fila.addLayout(textos, 1)
        fila.addWidget(self.grandes, alignment=Qt.AlignBottom)

        self.foto_a = FotoPiloto(170)
        self.foto_b = FotoPiloto(170)
        lado_a, self.nombre_a, self.apellido_a = _lado_duelo(self.foto_a)
        lado_b, self.nombre_b, self.apellido_b = _lado_duelo(self.foto_b)
        titulo_duelo = QLabel("CARA A CARA  ·  QUIÉN TERMINÓ ADELANTE")
        titulo_duelo.setObjectName("etiquetaRonda")
        titulo_duelo.setAlignment(Qt.AlignCenter)
        self.filas = {clave: FilaCaraACara(texto) for clave, texto in self.FILAS}
        centro = QVBoxLayout()
        centro.setSpacing(12)
        centro.addWidget(titulo_duelo)
        for fila_duelo in self.filas.values():
            centro.addWidget(fila_duelo)
        duelo = QHBoxLayout()
        duelo.setSpacing(24)
        duelo.addLayout(lado_a)
        duelo.addLayout(centro, 1)
        duelo.addLayout(lado_b)

        titulo_tira = QLabel("CARRERA POR CARRERA  ·  RESALTADO EL QUE LLEGÓ ADELANTE")
        titulo_tira.setObjectName("etiquetaRonda")
        self.tira = TiraDuelo()

        self.bloque_duelo = QWidget()
        columna = QVBoxLayout(self.bloque_duelo)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(8)
        columna.addLayout(duelo)
        columna.addSpacing(14)
        columna.addWidget(titulo_tira)
        columna.addWidget(self.tira)

        self.sin_duelo = QLabel("Este equipo no tuvo dos pilotos en una misma carrera.")
        self.sin_duelo.setObjectName("estadoVacio")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self.cabecera)
        layout.addWidget(self.bloque_duelo)
        layout.addWidget(self.sin_duelo)

    def mostrar(self, equipo, color, anio, h2h, stats):
        color = color or MUTED
        self.cabecera.set_color(color)
        self.eyebrow.setText(f"CONSTRUCTORES {anio}")
        self.nombre.setText(equipo["nombre"].upper())
        self.grandes.set_valores([
            f"P{equipo['posicion']}" if equipo["posicion"] else None,
            _numero(equipo["puntos"] or 0), stats["victorias"], stats["dobletes"]])

        self.bloque_duelo.setVisible(h2h is not None)
        self.sin_duelo.setVisible(h2h is None)
        if h2h is None:
            return
        for foto, nombre, apellido, piloto in (
                (self.foto_a, self.nombre_a, self.apellido_a, h2h["a"]),
                (self.foto_b, self.nombre_b, self.apellido_b, h2h["b"])):
            foto.set_piloto(piloto["driver_id"], sigla(piloto), None, color)
            nombre.setText(piloto["nombre"])
            apellido.setText(piloto["apellido"].upper())
        for clave, fila in self.filas.items():
            fila.set_valores(*h2h[clave], color)
        self.tira.set_duelo(sigla(h2h["a"]), sigla(h2h["b"]), h2h["por_carrera"], color)
