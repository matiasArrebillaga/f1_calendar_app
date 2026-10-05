import pandas as pd
from PySide6.QtWidgets import QFrame, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal, Qt, QTimer

from core.circuits import obtener_datos_circuito
from core.fechas import a_gmt_menos_3, dia_hora, largada, rango_fechas
from core.i18n import traducir_evento, traducir_pais, traducir_sesion
from core.track_map import obtener_ruta_mapa

TOTAL_SESIONES = 5


def _sesiones(evento):
    """[(nombre_es, fecha_gmt3)] de las sesiones con nombre, en orden."""
    sesiones = []
    for i in range(1, TOTAL_SESIONES + 1):
        nombre = evento.get(f'Session{i}')
        if nombre and str(nombre) != 'nan':
            sesiones.append((traducir_sesion(nombre), a_gmt_menos_3(evento.get(f'Session{i}Date'))))
    return sesiones


class ProximaCarrera(QFrame):
    """Bloque fijo arriba del calendario: la próxima carrera, cuánto falta y
    los horarios del fin de semana. Click o Enter abre el detalle."""
    clickeada = Signal(int)

    INTERVALO_CUENTA_MS = 60_000
    ANCHO_MAPA, ALTO_MAPA = 160, 120

    def __init__(self):
        super().__init__()
        self.setObjectName("bloqueProxima")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._fila = None
        self._largada = None

        # --- columna 1: qué y cuándo ---
        self.chip = QLabel()
        self.chip.setObjectName("etiquetaProxima")
        self.nombre = QLabel()
        self.nombre.setObjectName("nombreProxima")
        self.nombre.setWordWrap(True)
        self.lugar = QLabel()
        self.lugar.setObjectName("lugarProxima")
        self.lugar.setWordWrap(True)

        self._numeros = []
        cuenta = QHBoxLayout()
        cuenta.setSpacing(8)
        for unidad in ("DÍAS", "HORAS", "MIN"):
            caja = QFrame()
            caja.setObjectName("cajaCuenta")
            numero = QLabel("–")
            numero.setObjectName("numeroCuenta")
            texto = QLabel(unidad)
            texto.setObjectName("unidadCuenta")
            layout_caja = QVBoxLayout(caja)
            layout_caja.setContentsMargins(10, 6, 10, 6)
            layout_caja.setSpacing(0)
            layout_caja.addWidget(numero)
            layout_caja.addWidget(texto)
            cuenta.addWidget(caja)
            self._numeros.append(numero)
        cuenta.addStretch()

        fila_chip = QHBoxLayout()
        fila_chip.addWidget(self.chip)
        fila_chip.addStretch()

        columna_info = QWidget()
        layout_info = QVBoxLayout(columna_info)
        layout_info.setContentsMargins(20, 16, 20, 16)
        layout_info.setSpacing(4)
        layout_info.addLayout(fila_chip)
        layout_info.addSpacing(4)
        layout_info.addWidget(self.nombre)
        layout_info.addWidget(self.lugar)
        layout_info.addSpacing(10)
        layout_info.addLayout(cuenta)
        layout_info.addStretch()

        # --- columna 2: horarios ---
        self.columna_horarios = QWidget()
        self.columna_horarios.setObjectName("columnaProxima")
        self.columna_horarios.setAttribute(Qt.WA_StyledBackground, True)   # si no, el borde del QSS no se pinta
        self.grid_horarios = QGridLayout()
        self.grid_horarios.setHorizontalSpacing(16)
        self.grid_horarios.setVerticalSpacing(6)
        etiqueta_horarios = QLabel("HORARIOS (GMT-3)")
        etiqueta_horarios.setObjectName("etiquetaRonda")
        layout_horarios = QVBoxLayout(self.columna_horarios)
        layout_horarios.setContentsMargins(20, 16, 20, 16)
        layout_horarios.addWidget(etiqueta_horarios)
        layout_horarios.addSpacing(4)
        layout_horarios.addLayout(self.grid_horarios)
        layout_horarios.addStretch()

        # --- columna 3: mapa (sólo si ya está en caché) ---
        self.columna_mapa = QWidget()
        self.columna_mapa.setObjectName("columnaProxima")
        self.columna_mapa.setAttribute(Qt.WA_StyledBackground, True)
        self.mapa = QLabel()
        self.mapa.setAlignment(Qt.AlignCenter)
        self.dato_mapa = QLabel()
        self.dato_mapa.setObjectName("lugarProxima")
        self.dato_mapa.setAlignment(Qt.AlignCenter)
        layout_mapa = QVBoxLayout(self.columna_mapa)
        layout_mapa.setContentsMargins(16, 12, 16, 12)
        layout_mapa.addWidget(self.mapa, 1)
        layout_mapa.addWidget(self.dato_mapa)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(columna_info, 5)
        layout.addWidget(self.columna_horarios, 4)
        layout.addWidget(self.columna_mapa, 0)

        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVALO_CUENTA_MS)
        self._timer.timeout.connect(self._actualizar_cuenta)

    def mostrar(self, fila, evento):
        self._fila = fila
        ronda = evento.get('RoundNumber')
        self.chip.setText(f"PRÓXIMA · R{int(ronda)}" if pd.notna(ronda) else "PRÓXIMA")
        self.nombre.setText(traducir_evento(evento['EventName']))

        datos = obtener_datos_circuito(evento.get('Location'))
        partes = [datos['nombre_completo'] if datos else evento.get('Location'),
                  traducir_pais(evento.get('Country')), rango_fechas(evento)]
        self.lugar.setText(" · ".join(p for p in partes if p))

        while self.grid_horarios.count():
            self.grid_horarios.takeAt(0).widget().deleteLater()
        sesiones = _sesiones(evento)
        for i, (nombre, fecha) in enumerate(sesiones):
            es_carrera = i == len(sesiones) - 1
            etiqueta = QLabel(nombre)
            etiqueta.setObjectName("sesionCarrera" if es_carrera else "sesionHorario")
            hora = QLabel(dia_hora(fecha) if pd.notna(fecha) else "—")
            hora.setObjectName("horaSesion")
            self.grid_horarios.addWidget(etiqueta, i, 0)
            self.grid_horarios.addWidget(hora, i, 1, alignment=Qt.AlignRight)
        self.columna_horarios.setVisible(bool(sesiones))

        self._texto_chip = self.chip.text()
        self._largada = largada(evento)
        self._actualizar_cuenta()
        self._timer.start()

        # Sólo el mapa cacheado: generarlo baja la telemetría de una carrera
        # entera, y eso es trabajo del detalle, no de un bloque de resumen.
        ruta = obtener_ruta_mapa(evento.get('Location')) if evento.get('Location') else None
        pixmap = QPixmap(ruta) if ruta else QPixmap()
        if not pixmap.isNull():
            self.mapa.setPixmap(pixmap.scaled(
                self.ANCHO_MAPA, self.ALTO_MAPA, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.dato_mapa.setText(
                f"{datos['longitud_km']} km · {datos['vueltas']} vueltas" if datos else "")
        self.columna_mapa.setVisible(not pixmap.isNull())

    def ocultar(self):
        self._timer.stop()
        self.hide()

    def _actualizar_cuenta(self):
        if self._largada is None:
            return
        segundos = max(0, int((self._largada - pd.Timestamp.now()).total_seconds()))
        # Sigue siendo "la próxima" un rato después de largar (CalendarView.
        # DURACION_CARRERA): ahí la cuenta en cero se lee mejor como EN CURSO.
        self.chip.setText(self._texto_chip.replace("PRÓXIMA", "EN CURSO") if segundos == 0
                          else self._texto_chip)
        dias, resto = divmod(segundos, 86400)
        horas, resto = divmod(resto, 3600)
        for numero, valor in zip(self._numeros, (dias, horas, resto // 60)):
            numero.setText(f"{valor:02d}" if numero is not self._numeros[0] else str(valor))

    def mouseReleaseEvent(self, evento_mouse):
        if self._fila is not None and self.rect().contains(evento_mouse.position().toPoint()):
            self.clickeada.emit(self._fila)

    def keyPressEvent(self, evento_tecla):
        if evento_tecla.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) and self._fila is not None:
            self.clickeada.emit(self._fila)
            return
        super().keyPressEvent(evento_tecla)
