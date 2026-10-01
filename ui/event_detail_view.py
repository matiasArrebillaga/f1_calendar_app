from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QButtonGroup, QHeaderView,
    QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor
from PySide6.QtGui import QColor, QFont
import pandas as pd
from workers.session_worker import SessionWorker
from ui.spinner_widget import SpinnerWidget
from PySide6.QtGui import QPixmap
from core.circuits import obtener_datos_circuito
from workers.track_map_worker import TrackMapWorker
from core.track_map import obtener_ruta_mapa
from core.i18n import traducir_evento, traducir_pais, traducir_sesion
class EventDetailView(QWidget):
    volver = Signal()

    COLOR_PRIMERO = QColor("#8a6d0e")
    COLOR_SEGUNDO = QColor("#5c6068")
    COLOR_TERCERO = QColor("#7a4a1e")
    COLOR_TOP10 = QColor("#1c2a63")
    COLOR_Q1 = QColor("#5c1010")
    COLOR_Q2 = QColor("#6e4a0f")

    TOTAL_SLOTS_SESION = 5
    COL_SIDEBAR = 190

    PADDING_IMAGEN = 28           # el padding:14px de #imagenCircuito, a los dos lados
    ANCHO_MAPA_FALLBACK = 480     # sólo mientras el panel no está dispuesto todavía
    ALTO_MAPA_FALLBACK = 260

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        grid_raiz = QGridLayout()
        grid_raiz.setContentsMargins(0, 0, 0, 0)
        grid_raiz.setHorizontalSpacing(16)
        grid_raiz.setVerticalSpacing(6)
        grid_raiz.setColumnMinimumWidth(0, self.COL_SIDEBAR)
        grid_raiz.setColumnStretch(1, 1)

        FILA_TABLA = 3

        etiqueta_sesiones = QLabel("SESIONES")
        etiqueta_sesiones.setObjectName("etiquetaRonda")
        grid_raiz.addWidget(etiqueta_sesiones, 0, 0, alignment=Qt.AlignTop)

        self.sidebar_botones = []
        self.grupo_sesiones = QButtonGroup(self)
        self.grupo_sesiones.setExclusive(True)

        for i in range(self.TOTAL_SLOTS_SESION):
            boton = QPushButton("")
            boton.setObjectName("tabSesion")
            boton.setCheckable(True)
            boton.setEnabled(False)
            boton.setMinimumHeight(48)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.grupo_sesiones.addButton(boton)
            grid_raiz.addWidget(boton, FILA_TABLA + i, 0)
            grid_raiz.setRowStretch(FILA_TABLA + i, 1)
            self.sidebar_botones.append(boton)

        fila_encabezado = QHBoxLayout()
        fila_encabezado.setSpacing(10)

        self.badge_ronda = QLabel()
        self.badge_ronda.setObjectName("badgeRonda")

        columna_titulo = QVBoxLayout()
        columna_titulo.setSpacing(0)
        self.titulo = QLabel()
        self.titulo.setObjectName("titulo")
        self.subtitulo = QLabel()
        self.subtitulo.setObjectName("subtitulo")
        columna_titulo.addWidget(self.titulo)
        columna_titulo.addWidget(self.subtitulo)

        fila_encabezado.addWidget(self.badge_ronda, alignment=Qt.AlignTop)
        fila_encabezado.addLayout(columna_titulo)
        fila_encabezado.addStretch()

        linea_acento = QFrame()
        linea_acento.setObjectName("lineaAcento")

        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")

        self.spinner = SpinnerWidget(tamano=18)
        self.spinner.hide()
        layout_estado = QHBoxLayout()
        layout_estado.addWidget(self.spinner)
        layout_estado.addWidget(self.estado)
        layout_estado.addStretch()

        # --- Tabla de resultados y panel informativo, alternados con un stack ---
        self.tabla_resultados = QTableWidget()
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.verticalHeader().setVisible(False)
        self.tabla_resultados.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_resultados.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_resultados.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_resultados.setShowGrid(False)
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.panel_info = QWidget()
        
        self._efecto_opacidad = QGraphicsOpacityEffect(self.panel_info)
        self.panel_info.setGraphicsEffect(self._efecto_opacidad)

        self._animacion_fade = QPropertyAnimation(self._efecto_opacidad, b"opacity")
        self._animacion_fade.setDuration(350)
        self._animacion_fade.setStartValue(0)
        self._animacion_fade.setEndValue(1)
        self._animacion_fade.setEasingCurve(QEasingCurve.OutCubic)        
        layout_panel_info = QVBoxLayout(self.panel_info)
        layout_panel_info.setContentsMargins(20, 20, 20, 20)
        self.imagen_circuito = QLabel()
        self.imagen_circuito.setObjectName("imagenCircuito")
        self.imagen_circuito.setAlignment(Qt.AlignCenter)
        # Sin esto el minimumSizeHint del QLabel es el tamaño del pixmap, y el
        # panel no puede encogerse por más que escalemos la imagen.
        self.imagen_circuito.setMinimumSize(1, 1)
        self._pixmap_mapa = None   # original sin escalar, para re-escalar al resize
        self._tamano_mapa_pintado = None   # (ancho, alto) del último scaled()
        self._location_mapa = None         # circuito cuyo mapa estamos esperando
        sombra_imagen = QGraphicsDropShadowEffect()
        sombra_imagen.setColor(QColor(0, 0, 0, 160))
        sombra_imagen.setOffset(0, 4)
        sombra_imagen.setBlurRadius(25)
        self.imagen_circuito.setGraphicsEffect(sombra_imagen)
        self.texto_info = QLabel()
        self.texto_info.setWordWrap(True)
        self.texto_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        layout_panel_info.addWidget(self.imagen_circuito, alignment=Qt.AlignHCenter)
        layout_panel_info.addWidget(self.texto_info)
        layout_panel_info.addStretch()

        self.stack_contenido = QStackedWidget()
        self.stack_contenido.addWidget(self.tabla_resultados)  # índice 0
        self.stack_contenido.addWidget(self.panel_info)         # índice 1

        boton_volver = QPushButton("← Volver")
        boton_volver.setFixedWidth(140)
        boton_volver.setCursor(Qt.PointingHandCursor)
        boton_volver.setToolTip("Volver al calendario (Esc)")
        layout_volver = QHBoxLayout()
        layout_volver.addStretch()
        layout_volver.addWidget(boton_volver)

        grid_raiz.addLayout(fila_encabezado, 0, 1)
        grid_raiz.addWidget(linea_acento, 1, 1)
        grid_raiz.addLayout(layout_estado, 2, 1)
        grid_raiz.addWidget(
            self.stack_contenido, FILA_TABLA, 1, self.TOTAL_SLOTS_SESION, 1
        )
        grid_raiz.addLayout(
            layout_volver, FILA_TABLA + self.TOTAL_SLOTS_SESION, 0, 1, 2
        )

        margen_layout = QVBoxLayout()
        margen_layout.setContentsMargins(16, 14, 16, 14)
        margen_layout.addLayout(grid_raiz)
        self.setLayout(margen_layout)

        boton_volver.clicked.connect(self.volver.emit)
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash
        self.codigo_sesion = None
        self.evento_actual = None
        self.sesiones_info = {}  # {codigo: {'nombre': str, 'fecha': Timestamp}}

    def mostrar_evento(self, evento):
        self.evento_actual = evento
        self.titulo.setText(traducir_evento(evento['EventName']))
        self.subtitulo.setText(traducir_pais(evento['Country']))

        ronda = evento.get('RoundNumber')
        self.badge_ronda.setText(f"R{int(ronda)}" if pd.notna(ronda) else "")
        self.badge_ronda.setToolTip(
            f"Ronda {int(ronda)} de la temporada" if pd.notna(ronda) else ""
        )

        self.tabla_resultados.clear()
        self.tabla_resultados.setRowCount(0)
        self.stack_contenido.setCurrentIndex(0)
        self._set_estado("")

        codigos = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
                   'Qualifying': 'Q', 'Sprint': 'S', 'Sprint Qualifying': 'SQ',
                   'Race': 'R'}

        year = int(evento['EventDate'].year)
        gp = int(evento['RoundNumber'])

        self.sesiones_info = {}
        hoy = pd.Timestamp.now()

        # Primero armamos toda la info de fechas/nombres, sin tocar botones todavía.
        info_sesiones_ordenada = []
        for i in range(self.TOTAL_SLOTS_SESION):
            nombre_sesion = evento.get(f'Session{i + 1}')
            fecha_sesion = evento.get(f'Session{i + 1}Date')

            if nombre_sesion and str(nombre_sesion) != 'nan':
                fecha_sin_tz = self._convertir_a_gmt_menos_3(fecha_sesion)
                info_sesiones_ordenada.append({
                    'indice': i,
                    'nombre': nombre_sesion,
                    'fecha': fecha_sin_tz,
                    'pasada': pd.notna(fecha_sin_tz) and fecha_sin_tz < hoy,
                })

        # Buscamos cuál es la próxima sesión sin correr (la más cercana en el tiempo).
        futuras = [s for s in info_sesiones_ordenada if not s['pasada'] and pd.notna(s['fecha'])]
        indice_proxima = min(futuras, key=lambda s: s['fecha'])['indice'] if futuras else None

        for i in range(self.TOTAL_SLOTS_SESION):
            boton = self.sidebar_botones[i]

            # Llevamos el estado de conexión a mano: desconectar "a ciegas" hace
            # que libpyside emita un RuntimeWarning (que el except TypeError no
            # atrapa) cada vez que se abre un evento.
            if getattr(boton, "_sesion_conectada", False):
                boton.clicked.disconnect()
                boton._sesion_conectada = False

            boton.setChecked(False)
            boton.setProperty("estadoSesion", "")

            match = next((s for s in info_sesiones_ordenada if s['indice'] == i), None)
            if match is None:
                boton.setText("No disponible")
                boton.setToolTip("")
                boton.setEnabled(False)
                boton.style().unpolish(boton)
                boton.style().polish(boton)
                continue

            codigo = codigos.get(match['nombre'], match['nombre'])
            nombre_es = traducir_sesion(match['nombre'])
            self.sesiones_info[codigo] = {'nombre': nombre_es, 'fecha': match['fecha']}

            boton.setEnabled(True)
            boton.clicked.connect(
                lambda checked, y=year, g=gp, c=codigo, b=boton: self._click_sesion(y, g, c, b)
            )
            boton._sesion_conectada = True

            fecha_txt = (
                match['fecha'].strftime('%d/%m %H:%M') if pd.notna(match['fecha']) else ""
            )
            fecha_completa = (
                match['fecha'].strftime('%d/%m/%Y %H:%M') if pd.notna(match['fecha']) else "sin fecha"
            )

            if match['pasada']:
                boton.setText(nombre_es)
                boton.setProperty("estadoSesion", "pasada")
                boton.setToolTip(f"{nombre_es} — {fecha_completa} (GMT-3) · ver resultados")
            elif i == indice_proxima:
                boton.setText(f"{nombre_es}\n{fecha_txt} — PRÓXIMA")
                boton.setProperty("estadoSesion", "proxima")
                boton.setToolTip(f"{nombre_es} — próxima sesión, {fecha_completa} (GMT-3)")
            else:
                boton.setText(f"{nombre_es}\n{fecha_txt}")
                boton.setProperty("estadoSesion", "futura")
                boton.setToolTip(f"{nombre_es} — {fecha_completa} (GMT-3), todavía no se corrió")

            boton.style().unpolish(boton)
            boton.style().polish(boton)

        self._mostrar_info_circuito()
    def _click_sesion(self, year, gp, codigo, boton):
        boton.setChecked(True)
        self.cargar_sesion(year, gp, codigo)

    def cargar_sesion(self, year, gp, codigo_sesion):
        nombre = self.sesiones_info.get(codigo_sesion, {}).get('nombre', codigo_sesion)
        self._set_estado(f"Cargando {nombre}...", "cargando")
        self.spinner.iniciar()
        self.tabla_resultados.setRowCount(0)
        self.codigo_sesion = codigo_sesion

        worker = SessionWorker(year, gp, codigo_sesion)
        worker.terminado.connect(self.on_sesion_cargada)
        worker.error.connect(self.on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def on_sesion_cargada(self, sesion):
        worker = self.sender()
        if worker.codigo_sesion != self.codigo_sesion:
            return  # llegó tarde: el usuario ya clickeó otra sesión

        self.spinner.detener()
        self._set_estado("")
        resultados = sesion.results

        if resultados is None or resultados.empty:
            self._mostrar_info_circuito(codigo_sesion=self.codigo_sesion)
            return
        self.stack_contenido.setCurrentIndex(0)

        self.tabla_resultados.setRowCount(len(resultados))

        fuente_datos = QFont("Consolas")
        fuente_datos.setStyleHint(QFont.Monospace)

        es_clasificacion = self.codigo_sesion in ('Q', 'SQ')
        es_practica_o_clasificacion = es_clasificacion or self.codigo_sesion in (
            'FP1', 'FP2', 'FP3'
        )
        if es_practica_o_clasificacion:
            columnas = ['Position', 'Abbreviation', 'FullName', 'TeamName']
            etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo']
            if 'BestLapTime' in resultados.columns:
                columnas.append('BestLapTime')
                etiquetas.append('Tiempo de vuelta')
            elif 'Time' in resultados.columns:
                columnas.append('Time')
                etiquetas.append('Tiempo de vuelta')
            if 'Laps' in resultados.columns and resultados['Laps'].notna().any():
                columnas.append('Laps')
                etiquetas.append('Vueltas')
        else:
            columnas = ['Position', 'Abbreviation', 'FullName', 'TeamName',
                        'GridPosition', 'Status', 'Points', 'Time']
            etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Largada', 'Estado', 'Pts', 'Tiempo']

        columnas_disponibles = [
            (columna, etiqueta)
            for columna, etiqueta in zip(columnas, etiquetas)
            if columna in resultados.columns
        ]
        columnas = [columna for columna, _ in columnas_disponibles]
        etiquetas = [etiqueta for _, etiqueta in columnas_disponibles]
        self.tabla_resultados.setColumnCount(len(columnas))
        self.tabla_resultados.setHorizontalHeaderLabels(etiquetas)
        columnas_monoespaciadas = {
            'Position', 'GridPosition', 'Time', 'BestLapTime', 'Points', 'Laps'
        }
        total_pilotos = len(resultados)

        for fila, (_, row) in enumerate(resultados.iterrows()):
            color = self._color_por_posicion(row.get('Position'), es_clasificacion, total_pilotos)

            for col, nombre_col in enumerate(columnas):
                valor = row.get(nombre_col)
                texto = self._formatear_valor(nombre_col, valor)
                item = QTableWidgetItem(texto)

                if nombre_col in ('Position', 'Points', 'Laps'):
                    item.setTextAlignment(Qt.AlignCenter)
                if nombre_col in columnas_monoespaciadas:
                    item.setFont(fuente_datos)
                # Los nombres de piloto y equipo se cortan cuando la columna es
                # angosta; el tooltip es la única forma de leerlos completos.
                item.setToolTip(texto)

                if color is not None:
                    item.setBackground(color)
                    item.setForeground(QColor("#f5f5f5"))
                self.tabla_resultados.setItem(fila, col, item)

        self.tabla_resultados.resizeColumnsToContents()
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

    def _mostrar_info_circuito(self, codigo_sesion=None):
        location = self.evento_actual.get('Location')
        lineas = []
        datos_circuito = obtener_datos_circuito(location)

        if datos_circuito:
            lineas.append(
                f"<div style='font-size:18px; font-weight:800; color:#ffffff; "
                f"margin-bottom:10px;'>{datos_circuito['nombre_completo']}</div>"
            )
            lineas.append(self._fila_dato("Longitud", f"{datos_circuito['longitud_km']} km"))
            lineas.append(self._fila_dato("Vueltas", datos_circuito['vueltas']))
            lineas.append(self._fila_dato("Distancia total", f"{datos_circuito['distancia_km']} km"))
            lineas.append(self._fila_dato("Curvas", datos_circuito['curvas']))
            lineas.append(self._fila_dato("Récord de vuelta", datos_circuito['record_vuelta']))
            lineas.append(self._fila_dato("Primer GP", datos_circuito['primer_gp']))
        else:
            lineas.append(self._fila_dato("Circuito", location or "—"))

        lineas.append(self._separador())
        lineas.append(self._fila_dato(
            "País", traducir_pais(self.evento_actual.get('Country')) or "—"
        ))
        lineas.append(self._fila_dato(
            "Nombre oficial del evento",
            self.evento_actual.get('OfficialEventName', '—')
        ))

        if codigo_sesion:
            info = self.sesiones_info.get(codigo_sesion, {})
            nombre_sesion = info.get('nombre', codigo_sesion)
            fecha = info.get('fecha')

            lineas.append(self._separador())
            lineas.append(f"<div>{nombre_sesion} todavía no se corrió.</div>")

            if pd.notna(fecha):
                hoy = pd.Timestamp.now()
                dias_restantes = (fecha.normalize() - hoy.normalize()).days

                lineas.append(self._fila_dato(
                    "Fecha (GMT-3)", fecha.strftime('%d/%m/%Y %H:%M')
                ))

                if dias_restantes > 0:
                    lineas.append(self._fila_dato("Faltan", f"{dias_restantes} día(s)"))
                elif dias_restantes == 0:
                    lineas.append("<div><b>¡Es hoy!</b></div>")

        # Sin "<br>": cada línea ya es un <div>, que es un elemento de bloque y
        # salta solo. Unirlos con <br> duplicaba el alto del panel (389 px en vez
        # de 172 px) y era lo que empujaba la imagen fuera de la vista.
        self.texto_info.setText("".join(lineas))

        # El texto va PRIMERO porque el alto disponible para el mapa es lo que
        # sobra después de él.
        self._cargar_mapa(location)

        self.stack_contenido.setCurrentIndex(1)
        # Al abrir el detalle, la página del stack todavía no está dispuesta y
        # panel_info informa su tamaño por defecto (640x480), así que el mapa
        # sale más chico de lo que cabe. Un re-pintado en el próximo ciclo del
        # event loop lo escala con las medidas reales.
        QTimer.singleShot(0, self._pintar_mapa)

        self._animacion_fade.stop()
        self._animacion_fade.start()

    @staticmethod
    def _separador():
        return "<div style='height:8px;'></div>"

    def _cargar_mapa(self, location):
        """Pinta el mapa si ya está en caché; si no, lo manda a generar."""
        self._location_mapa = location

        ruta_mapa = obtener_ruta_mapa(location)
        if ruta_mapa:
            self._pintar_mapa(ruta_mapa)
            return

        self._pixmap_mapa = None
        self.imagen_circuito.hide()

        # Un worker por circuito, no uno global: serializarlos dejaba sin mapa
        # para siempre al segundo circuito que se abriera mientras el primero
        # generaba (nunca se le volvía a pedir).
        if any(getattr(w, 'location', None) == location and w.isRunning()
               for w in self._workers_activos):
            return

        worker = TrackMapWorker(location, int(self.evento_actual['EventDate'].year))
        worker.terminado.connect(self._on_mapa_generado)
        worker.error.connect(self._on_error_mapa)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _pintar_mapa(self, ruta=None):
        """Escala el mapa al espacio que queda libre en el panel.

        Guarda el pixmap original sin escalar: re-escalar uno ya escalado en cada
        resize degradaría la imagen. Llamar sin `ruta` re-escala el que ya está.
        """
        if ruta is not None:
            self._pixmap_mapa = QPixmap(ruta)
            self._tamano_mapa_pintado = None   # pixmap nuevo: hay que re-escalar
        if self._pixmap_mapa is None or self._pixmap_mapa.isNull():
            return

        margenes = self.panel_info.layout().contentsMargins()
        ancho_disp = (self.panel_info.width() - margenes.left() - margenes.right()
                      - self.PADDING_IMAGEN)
        alto_disp = (self.panel_info.height() - margenes.top() - margenes.bottom()
                     - self.texto_info.heightForWidth(max(1, ancho_disp))
                     - self.PADDING_IMAGEN)

        # Durante mostrar_evento el panel todavía no está dispuesto y mide 0; el
        # resizeEvent vuelve a entrar acá con las medidas reales.
        if ancho_disp < 50 or alto_disp < 50:
            ancho_disp, alto_disp = self.ANCHO_MAPA_FALLBACK, self.ALTO_MAPA_FALLBACK

        # Nunca agrandar más allá del PNG original: ampliarlo sólo lo pixela.
        ancho_disp = min(ancho_disp, self._pixmap_mapa.width())
        alto_disp = min(alto_disp, self._pixmap_mapa.height())

        # Los PNG de cache_tracks llegan a 2275x2400: un scaled() con
        # SmoothTransformation por cada resizeEvent (y con el drop shadow del
        # QLabel encima, que fuerza render por software) tironea al arrastrar el
        # borde de la ventana. Si el destino no cambió, no hay nada que rehacer.
        if (ancho_disp, alto_disp) != self._tamano_mapa_pintado:
            self._tamano_mapa_pintado = (ancho_disp, alto_disp)
            self.imagen_circuito.setPixmap(self._pixmap_mapa.scaled(
                ancho_disp, alto_disp, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        self.imagen_circuito.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Sólo si el panel informativo es lo que se está viendo: con la tabla de
        # resultados en pantalla, re-escalar el mapa es trabajo 100% tirado.
        if self.stack_contenido.currentIndex() == 1:
            self._pintar_mapa()

    def _on_mapa_generado(self, ruta_mapa):
        if self.sender().location != self._location_mapa:
            return  # llegó tarde: el usuario ya abrió otro circuito

        self._pintar_mapa(ruta_mapa)

        self.panel_info.layout().activate()
        self.panel_info.updateGeometry()
        self.panel_info.update()

    def _on_error_mapa(self, mensaje):
        if self.sender().location != self._location_mapa:
            return
        self._set_estado(f"No se pudo generar el mapa: {mensaje}", "error")

    def _color_por_posicion(self, posicion, es_clasificacion, total_pilotos):
        if pd.isna(posicion):
            return None
        posicion = int(posicion)

        if posicion == 1:
            return self.COLOR_PRIMERO
        if posicion == 2:
            return self.COLOR_SEGUNDO
        if posicion == 3:
            return self.COLOR_TERCERO
        if posicion <= 10:
            return self.COLOR_TOP10

        if es_clasificacion:
            limite_q2 = 16 if total_pilotos >= 22 else 15
            if posicion <= limite_q2:
                return self.COLOR_Q2
            return self.COLOR_Q1

        return None

    def _formatear_valor(self, nombre_col, valor):
        if pd.isna(valor):
            return "—"

        if nombre_col in ('Position', 'GridPosition', 'Points', 'Laps'):
            return str(int(valor))

        if nombre_col in ('Time', 'BestLapTime'):
            total_segundos = valor.total_seconds()
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)
            segundos = total_segundos % 60
            if horas > 0:
                return f"{horas}:{minutos:02d}:{segundos:06.3f}"
            return f"{minutos}:{segundos:06.3f}"

        return str(valor)
    def _convertir_a_gmt_menos_3(self, timestamp):
        if pd.isna(timestamp):
            return timestamp

        if timestamp.tzinfo is None:
            return timestamp

        timestamp_gmt3 = timestamp.tz_convert('Etc/GMT+3')
        return timestamp_gmt3.tz_localize(None)   
    def on_error(self, mensaje):
        worker = self.sender()
        if worker is not None and worker.codigo_sesion != self.codigo_sesion:
            return

        self.spinner.detener()
        self._set_estado(f"Error al cargar: {mensaje}", "error")

    def _set_estado(self, texto, tipo=""):
        nombres = {
            "": "estadoVacio",
            "cargando": "estadoCargando",
            "error": "estadoError",
            "vacio": "estadoVacio",
        }
        self.estado.setObjectName(nombres.get(tipo, "estadoVacio"))
        self.estado.setText(texto)
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)
    def _fila_dato(self, etiqueta, valor):
        """Línea de datos técnicos: etiqueta muda + valor bien blanco y en negrita."""
        return (
            f"<div style='font-size:13px; margin-bottom:3px;'>"
            f"<span style='color:#9a9aa5;'>{etiqueta}:</span> "
            f"<span style='color:#f5f5f5; font-weight:700;'>{valor}</span></div>"
        )        