"""Piezas de la pestaña Pilotos: foto, tarjetas, grilla y fichas.

Los datos llegan como dicts planos de core/historial.py; acá sólo se pintan.
"""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
)

from core.i18n import traducir_evento, traducir_nacionalidad
from ui.icons import BORDE, DATO, MUTED, PRIMARIO, SUPERFICIE


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


class FotoPiloto(QWidget):
    """Foto recortada en cuadrado sobre un degradé del color del equipo. Sin
    foto (todavía bajando, o no existe ninguna) muestra la sigla."""

    def __init__(self, lado, parent=None):
        super().__init__(parent)
        self.setFixedSize(lado, lado)
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

        tono = QColor(self._color)
        tono.setAlpha(150)
        degrade = QLinearGradient(0, 0, 0, rect.height())
        degrade.setColorAt(0, tono)
        degrade.setColorAt(1, QColor(SUPERFICIE))
        pintor.fillRect(rect, degrade)

        if self._pixmap is not None:
            pintor.drawPixmap(0, 0, self._pixmap)
        else:
            fuente = QFont("Titillium Web")
            fuente.setPixelSize(max(17, self.height() // 4))
            fuente.setBold(True)
            pintor.setFont(fuente)
            pintor.setPen(QColor(PRIMARIO))
            pintor.drawText(rect, Qt.AlignCenter, self._sigla)

        if self._numero and self.width() >= 100:
            fuente = QFont()
            fuente.setPixelSize(13)
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


class TarjetaEquipo(_TarjetaClickeable):
    ANCHO = 220

    def __init__(self, equipo, color):
        super().__init__("tarjetaEquipo", equipo["constructor_id"])
        self.setFixedWidth(self.ANCHO)

        franja = QFrame()
        franja.setFixedWidth(4)
        franja.setStyleSheet(f"background-color: {color or MUTED}; border-radius: 2px;")
        nombre = QLabel(equipo["nombre"])
        nombre.setObjectName("nombreTarjeta")
        partes = [f"P{equipo['posicion']}"] if equipo["posicion"] else []
        partes.append(f"{_numero(equipo['puntos'] or 0)} pts")
        detalle = QLabel("  ·  ".join(partes))
        detalle.setObjectName("detalleTarjeta")

        columna = QVBoxLayout()
        columna.setSpacing(2)
        columna.addWidget(nombre)
        columna.addWidget(detalle)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(franja)
        layout.addLayout(columna, 1)


class ScrollSinFlechas(QScrollArea):
    """QScrollArea que deja pasar ←/→ hasta MainWindow, que cambia de año con
    ellas. Apagar el scroll horizontal no alcanza: QAbstractScrollArea se queda
    con esas teclas igual."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Left, Qt.Key_Right):
            evento.ignore()
            return
        super().keyPressEvent(evento)


class GrillaTarjetas(ScrollSinFlechas):
    """Tarjetas de ancho fijo en tantas columnas como entren a lo ancho."""
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
        paso = self._tarjetas[0].maximumWidth() + self.ESPACIO
        columnas = max(1, (self.viewport().width() + self.ESPACIO) // paso)
        if columnas == self._columnas:
            return
        self._columnas = columnas
        for tarjeta in self._tarjetas:
            self._grilla.removeWidget(tarjeta)
        for i, tarjeta in enumerate(self._tarjetas):
            self._grilla.addWidget(tarjeta, i // columnas, i % columnas)
            tarjeta.show()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._acomodar()


class FilaStats(QWidget):
    """Cajas KPI (mismo estilo que Clasificación) en una grilla de `columnas`."""

    def __init__(self, etiquetas, columnas, dato=False):
        super().__init__()
        self._dato = dato
        self._valores = []
        grilla = QGridLayout(self)
        grilla.setContentsMargins(0, 0, 0, 0)
        grilla.setSpacing(8)
        for i, texto in enumerate(etiquetas):
            caja = QFrame()
            caja.setObjectName("kpi")
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


def _celda(fila):
    texto, delta, estado = formato_celda(fila)
    celda = QFrame()
    celda.setObjectName("celdaResultado")
    celda.setProperty("estado", estado)
    celda.setFixedWidth(46)
    celda.setToolTip(f"R{fila['ronda']} · {traducir_evento(fila['gp'])}")
    arriba = QLabel(texto)
    arriba.setObjectName("textoCelda")
    arriba.setAlignment(Qt.AlignCenter)
    abajo = QLabel(delta or " ")
    abajo.setObjectName("deltaCelda")
    abajo.setAlignment(Qt.AlignCenter)
    abajo.setProperty("sentido", "sube" if delta.startswith("▲") else "otro")
    columna = QVBoxLayout(celda)
    columna.setContentsMargins(2, 4, 2, 4)
    columna.setSpacing(0)
    columna.addWidget(arriba)
    columna.addWidget(abajo)
    return celda


class TiraResultados(QWidget):
    """Una celda por carrera: llegada (o DNF/DSQ/DNQ/DNS) y delta contra la largada."""
    POR_FILA = 12

    def __init__(self):
        super().__init__()
        self._grilla = QGridLayout(self)
        self._grilla.setContentsMargins(0, 0, 0, 0)
        self._grilla.setSpacing(4)
        self._grilla.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._celdas = []

    def celdas(self):
        return list(self._celdas)

    def set_resultados(self, filas):
        while self._grilla.count():
            item = self._grilla.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()   # deleteLater tarda: sin esto sigue pintada
                item.widget().deleteLater()
        self._celdas = [_celda(fila) for fila in filas]
        for i, celda in enumerate(self._celdas):
            self._grilla.addWidget(celda, i // self.POR_FILA, i % self.POR_FILA)
        if not filas:
            vacio = QLabel("Sin carreras disputadas.")
            vacio.setObjectName("estadoVacio")
            self._grilla.addWidget(vacio, 0, 0, 1, self.POR_FILA)


class FichaPiloto(QWidget):
    def __init__(self):
        super().__init__()
        self.foto = FotoPiloto(180)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreFicha")
        self.meta = QLabel()
        self.meta.setObjectName("metaFicha")
        self.titulo_temporada = QLabel()
        self.titulo_temporada.setObjectName("etiquetaRonda")
        self.stats_temporada = FilaStats(
            ["Posición", "Puntos", "Victorias", "Podios", "Poles", "Abandonos",
             "Prom. llegada", "Prom. largada"], columnas=4)
        titulo_tira = QLabel("CARRERA POR CARRERA")
        titulo_tira.setObjectName("etiquetaRonda")
        self.tira = TiraResultados()
        titulo_carrera = QLabel("CARRERA COMPLETA")
        titulo_carrera.setObjectName("etiquetaRonda")
        self.stats_carrera = FilaStats(["Títulos", "Victorias", "Podios", "GPs", "Debut"],
                                       columnas=5, dato=True)

        columna = QVBoxLayout()
        columna.setSpacing(8)
        columna.addWidget(self.nombre)
        columna.addWidget(self.meta)
        columna.addSpacing(8)
        for widget in (self.titulo_temporada, self.stats_temporada, titulo_tira, self.tira,
                       titulo_carrera, self.stats_carrera):
            columna.addWidget(widget)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self.foto, alignment=Qt.AlignTop)
        layout.addLayout(columna, 1)

    def mostrar(self, piloto, color, anio, stats, tira, carrera):
        self.foto.set_piloto(piloto["driver_id"], sigla(piloto), piloto.get("numero"), color)
        self.nombre.setText(f"{piloto['nombre']} {piloto['apellido']}")
        partes = []
        if piloto.get("numero"):
            partes.append(f"#{piloto['numero']}")
        if piloto.get("equipo"):
            partes.append(piloto["equipo"])
        if piloto.get("nacionalidad"):
            partes.append(traducir_nacionalidad(piloto["nacionalidad"]))
        if piloto.get("nacimiento"):
            partes.append(f"{anio - int(piloto['nacimiento'][:4])} años en {anio}")
        self.meta.setText("  ·  ".join(partes))

        self.titulo_temporada.setText(f"TEMPORADA {anio}")
        self.stats_temporada.set_valores([
            f"P{stats['posicion']}" if stats["posicion"] else None,
            _numero(stats["puntos"]), stats["victorias"], stats["podios"], stats["poles"],
            stats["abandonos"], _promedio(stats["prom_llegada"]),
            _promedio(stats["prom_largada"])])
        self.tira.set_resultados(tira)
        self.stats_carrera.set_valores([carrera["titulos"], carrera["victorias"],
                                        carrera["podios"], carrera["gps"], carrera["debut"]])


class BarraPartida(QWidget):
    """Barra repartida en proporción a (a, b): a en DATO, b en gris."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(8)
        self._a = self._b = 0

    def set_proporcion(self, a, b):
        self._a, self._b = a, b
        self.update()

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        ancho, alto = self.width(), self.height()
        total = self._a + self._b
        if total <= 0:
            pintor.setBrush(QColor(BORDE))
            pintor.drawRoundedRect(QRectF(0, 0, ancho, alto), 4, 4)
            return
        corte = round(ancho * self._a / total)
        pintor.setBrush(QColor(DATO))
        pintor.drawRoundedRect(QRectF(0, 0, corte, alto), 4, 4)
        pintor.setBrush(QColor(BORDE))
        pintor.drawRoundedRect(QRectF(corte + 2, 0, max(0, ancho - corte - 2), alto), 4, 4)


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
        self.barra = BarraPartida()

        centro = QVBoxLayout()
        centro.setSpacing(4)
        centro.addWidget(etiqueta)
        centro.addWidget(self.barra)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.valor_a)
        layout.addLayout(centro, 1)
        layout.addWidget(self.valor_b)

    def set_valores(self, a, b):
        self.valor_a.setText(f"{a:g}")
        self.valor_b.setText(f"{b:g}")
        for etiqueta, gana in ((self.valor_a, a > b), (self.valor_b, b > a)):
            etiqueta.setProperty("gana", gana)
            etiqueta.style().unpolish(etiqueta)
            etiqueta.style().polish(etiqueta)
        self.barra.set_proporcion(a, b)


class FichaEquipo(QWidget):
    FILAS = (("clasificacion", "Clasificación"), ("carrera", "Carrera"),
             ("puntos", "Puntos"), ("victorias", "Victorias"), ("podios", "Podios"))

    def __init__(self):
        super().__init__()
        self.franja = QFrame()
        self.franja.setFixedWidth(6)
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreFicha")
        self.meta = QLabel()
        self.meta.setObjectName("metaFicha")
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(self.nombre)
        textos.addWidget(self.meta)
        cabeza = QHBoxLayout()
        cabeza.setSpacing(12)
        cabeza.addWidget(self.franja)
        cabeza.addLayout(textos, 1)

        self.foto_a = FotoPiloto(72)
        self.foto_b = FotoPiloto(72)
        self.nombre_a = QLabel()
        self.nombre_a.setObjectName("nombreDuelo")
        self.nombre_b = QLabel()
        self.nombre_b.setObjectName("nombreDuelo")
        self.nombre_b.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        duelo = QHBoxLayout()
        duelo.setSpacing(10)
        duelo.addWidget(self.foto_a)
        duelo.addWidget(self.nombre_a, 1)
        duelo.addWidget(self.nombre_b, 1)
        duelo.addWidget(self.foto_b)

        self.titulo_duelo = QLabel()
        self.titulo_duelo.setObjectName("etiquetaRonda")
        self.filas = {clave: FilaCaraACara(texto) for clave, texto in self.FILAS}
        self.bloque_duelo = QWidget()
        columna = QVBoxLayout(self.bloque_duelo)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(10)
        columna.addLayout(duelo)
        columna.addWidget(self.titulo_duelo)
        for fila in self.filas.values():
            columna.addWidget(fila)

        self.sin_duelo = QLabel("Este equipo no tuvo dos pilotos en una misma carrera.")
        self.sin_duelo.setObjectName("estadoVacio")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(cabeza)
        layout.addWidget(self.bloque_duelo)
        layout.addWidget(self.sin_duelo)

    def mostrar(self, equipo, color, anio, h2h):
        color = color or MUTED
        self.franja.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        self.nombre.setText(equipo["nombre"])
        partes = [f"P{equipo['posicion']} en constructores"] if equipo["posicion"] else []
        partes.append(f"{_numero(equipo['puntos'] or 0)} puntos en {anio}")
        self.meta.setText("  ·  ".join(partes))

        self.bloque_duelo.setVisible(h2h is not None)
        self.sin_duelo.setVisible(h2h is None)
        if h2h is None:
            return
        for foto, nombre, piloto in ((self.foto_a, self.nombre_a, h2h["a"]),
                                     (self.foto_b, self.nombre_b, h2h["b"])):
            foto.set_piloto(piloto["driver_id"], sigla(piloto), None, color)
            nombre.setText(f"{piloto['nombre']} {piloto['apellido']}")
        self.titulo_duelo.setText(f"CARA A CARA {anio}  ·  QUIÉN TERMINÓ ADELANTE")
        for clave, fila in self.filas.items():
            fila.set_valores(*h2h[clave])
