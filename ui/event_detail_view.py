from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QButtonGroup, QHeaderView, QSizePolicy, QStackedWidget,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QSize, QEvent
from PySide6.QtGui import QColor, QFont, QPixmap
import pandas as pd

from core import historial
from core.circuits import obtener_datos_circuito
from core.fechas import a_gmt_menos_3, dia_hora, rango_fechas
from core.i18n import traducir_evento, traducir_pais, traducir_sesion
from core.track_map import obtener_ruta_mapa
from ui.datos_circuito import PanelDatosCircuito, ficha_html, filas_ficha
from ui.delegados import MedallaPosicion, ficha_de, marcar_ficha
from ui.icons import icono, franja_equipo, MUTED, PRIMARIO, DATO
from ui.spinner_widget import SpinnerWidget
from ui.vista_ampliada import VistaAmpliada
from ui.estado import aplicar_estado
from workers.session_worker import SessionWorker
from workers.track_map_worker import TrackMapWorker


class EventDetailView(QWidget):
    """Detalle de un GP: sesiones en una tira arriba, resultados a la izquierda
    y el circuito (mapa + datos) siempre visible a la derecha."""
    volver = Signal()
    abrir_ficha = Signal(str, str)   # ("piloto" | "equipo", id)

    TOTAL_SLOTS_SESION = 5
    ANCHO_COLUMNA_CIRCUITO = 300
    PADDING_IMAGEN = 32   # el padding:16px de #imagenCircuito, a los dos lados
    ALTO_MAPA = 240

    CODIGOS_SESION = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
                      'Qualifying': 'Q', 'Sprint': 'S', 'Sprint Qualifying': 'SQ',
                      'Race': 'R'}

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # --- Miga: reemplaza al botón "Volver" ---
        boton_volver = QPushButton("Calendario")
        boton_volver.setObjectName("migaVolver")
        boton_volver.setIcon(icono("chevron-left", MUTED, 14))
        boton_volver.setIconSize(QSize(14, 14))
        boton_volver.setCursor(Qt.PointingHandCursor)
        boton_volver.setToolTip("Volver al calendario (Esc)")
        boton_volver.clicked.connect(self.volver.emit)
        separador = QLabel("/")
        separador.setObjectName("migaSeparador")
        self.miga_evento = QLabel()
        self.miga_evento.setObjectName("migaSeparador")
        atajo = QLabel("Esc  volver")
        atajo.setObjectName("migaSeparador")

        fila_miga = QHBoxLayout()
        fila_miga.setSpacing(8)
        fila_miga.addWidget(boton_volver)
        fila_miga.addWidget(separador)
        fila_miga.addWidget(self.miga_evento)
        fila_miga.addStretch()
        fila_miga.addWidget(atajo)

        # --- Encabezado ---
        self.badge_ronda = QLabel()
        self.badge_ronda.setObjectName("badgeRonda")
        self.titulo = QLabel()
        self.titulo.setObjectName("titulo")
        self.subtitulo = QLabel()
        self.subtitulo.setObjectName("subtitulo")
        columna_titulo = QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(self.titulo)
        columna_titulo.addWidget(self.subtitulo)
        fila_encabezado = QHBoxLayout()
        fila_encabezado.setSpacing(12)
        fila_encabezado.addWidget(self.badge_ronda, alignment=Qt.AlignTop)
        fila_encabezado.addLayout(columna_titulo)
        fila_encabezado.addStretch()

        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")
        self.spinner = SpinnerWidget(tamano=18)
        self.spinner.hide()
        layout_estado = QHBoxLayout()
        layout_estado.addWidget(self.spinner)
        layout_estado.addWidget(self.estado)
        layout_estado.addStretch()

        # --- Tira de sesiones ---
        self.botones_sesion = []
        self.grupo_sesiones = QButtonGroup(self)
        self.grupo_sesiones.setExclusive(True)
        tira = QHBoxLayout()
        tira.setSpacing(0)
        for _ in range(self.TOTAL_SLOTS_SESION):
            boton = QPushButton("")
            boton.setObjectName("tabSesion")
            boton.setCheckable(True)
            boton.setEnabled(False)
            boton.setMinimumHeight(54)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.grupo_sesiones.addButton(boton)
            tira.addWidget(boton)
            self.botones_sesion.append(boton)

        # --- Izquierda: resultados, o el aviso de que la sesión no se corrió ---
        self.tabla_resultados = QTableWidget()
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.verticalHeader().setVisible(False)
        self.tabla_resultados.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_resultados.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_resultados.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_resultados.setShowGrid(False)
        self._medalla = MedallaPosicion(self.tabla_resultados)   # referencia viva
        self.tabla_resultados.setItemDelegateForColumn(0, self._medalla)
        # activated: doble clic o Enter sobre la fila.
        self.tabla_resultados.activated.connect(self._activar)

        self.panel_pendiente = QWidget()
        self.panel_pendiente.setObjectName("panelPendiente")
        self.panel_pendiente.setAttribute(Qt.WA_StyledBackground, True)
        self.etiqueta_pendiente = QLabel()
        self.etiqueta_pendiente.setObjectName("etiquetaRonda")
        self.titulo_pendiente = QLabel()
        self.titulo_pendiente.setObjectName("tituloPendiente")
        self.texto_pendiente = QLabel()
        self.texto_pendiente.setObjectName("textoPendiente")
        self.texto_pendiente.setWordWrap(True)
        layout_pendiente = QVBoxLayout(self.panel_pendiente)
        layout_pendiente.setContentsMargins(28, 24, 28, 24)
        layout_pendiente.setSpacing(6)
        layout_pendiente.addWidget(self.etiqueta_pendiente)
        layout_pendiente.addWidget(self.titulo_pendiente)
        layout_pendiente.addWidget(self.texto_pendiente)
        layout_pendiente.addStretch()

        self.stack_contenido = QStackedWidget()
        self.stack_contenido.addWidget(self.tabla_resultados)  # índice 0
        self.stack_contenido.addWidget(self.panel_pendiente)   # índice 1

        # --- Derecha: el circuito, siempre a la vista ---
        self.panel_info = QWidget()
        self.panel_info.setObjectName("panelInfoCircuito")
        self.panel_info.setFixedWidth(self.ANCHO_COLUMNA_CIRCUITO)
        self.imagen_circuito = QLabel()
        self.imagen_circuito.setObjectName("imagenCircuito")
        self.imagen_circuito.setAlignment(Qt.AlignCenter)
        # Sin esto el minimumSizeHint del QLabel es el tamaño del pixmap.
        self.imagen_circuito.setMinimumSize(1, 1)
        self._hacer_clickeable(self.imagen_circuito, "Ampliar mapa")
        # Pista de que el mapa se amplía, fija en la esquina (la columna es de ancho fijo).
        pista_mapa = QLabel(self.imagen_circuito)
        pista_mapa.setPixmap(icono("maximize-2", MUTED, 16).pixmap(16, 16))
        pista_mapa.setStyleSheet("background: transparent; border: none; padding: 0;")
        pista_mapa.move(self.ANCHO_COLUMNA_CIRCUITO - 28, 12)
        self._pixmap_mapa = None   # original sin escalar
        self._tamano_mapa_pintado = None   # (ancho, alto) del último scaled()
        self._location_mapa = None         # circuito cuyo mapa estamos esperando
        self._ficha_actual = (None, None, None)   # (nombre, datos, oficial) del circuito abierto
        sombra_imagen = QGraphicsDropShadowEffect()
        sombra_imagen.setColor(QColor(0, 0, 0, 160))
        sombra_imagen.setOffset(0, 4)
        sombra_imagen.setBlurRadius(25)
        self.imagen_circuito.setGraphicsEffect(sombra_imagen)
        self.texto_info = QLabel()
        self.texto_info.setObjectName("textoInfoCircuito")
        self.texto_info.setWordWrap(True)
        self.texto_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._hacer_clickeable(self.texto_info, "Ficha completa y ganadores en este circuito")
        layout_panel_info = QVBoxLayout(self.panel_info)
        layout_panel_info.setContentsMargins(0, 0, 0, 0)
        layout_panel_info.setSpacing(12)
        layout_panel_info.addWidget(self.imagen_circuito)
        layout_panel_info.addWidget(self.texto_info)
        layout_panel_info.addStretch()

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self.stack_contenido, 1)
        cuerpo.addWidget(self.panel_info)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(12)
        layout.addLayout(fila_miga)
        layout.addLayout(fila_encabezado)
        layout.addLayout(tira)
        layout.addLayout(layout_estado)
        layout.addLayout(cuerpo, 1)

        self._workers_activos = []  # referencias vivas mientras corren, evita el crash
        self.codigo_sesion = None
        self._sesion_pedida = None   # (year, gp, codigo) de la última sesión pedida
        self._con_historial = None   # se abre con la primera tabla de resultados
        self.evento_actual = None
        self.sesiones_info = {}  # {codigo: {'nombre': str, 'fecha': Timestamp, 'pasada': bool}}

    def mostrar_evento(self, evento):
        self.evento_actual = evento
        nombre_evento = traducir_evento(evento['EventName'])
        self.titulo.setText(nombre_evento)
        self.miga_evento.setText(nombre_evento)
        pais = traducir_pais(evento['Country']) or ""
        self.subtitulo.setText(f"{pais.upper()}   ·   {rango_fechas(evento)}")

        ronda = evento.get('RoundNumber')
        self.badge_ronda.setText(f"R{int(ronda)}" if pd.notna(ronda) else "")
        self.badge_ronda.setToolTip(
            f"Ronda {int(ronda)} de la temporada" if pd.notna(ronda) else ""
        )

        self.tabla_resultados.clear()
        self.tabla_resultados.setRowCount(0)
        self._set_estado("")

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
                fecha_sin_tz = a_gmt_menos_3(fecha_sesion)
                info_sesiones_ordenada.append({
                    'indice': i,
                    'nombre': nombre_sesion,
                    'fecha': fecha_sin_tz,
                    'pasada': pd.notna(fecha_sin_tz) and fecha_sin_tz < hoy,
                })

        # Buscamos cuál es la próxima sesión sin correr (la más cercana en el tiempo).
        futuras = [s for s in info_sesiones_ordenada if not s['pasada'] and pd.notna(s['fecha'])]
        indice_proxima = min(futuras, key=lambda s: s['fecha'])['indice'] if futuras else None

        for i, boton in enumerate(self.botones_sesion):
            # Llevamos el estado de conexión a mano: desconectar "a ciegas" hace
            # que libpyside emita un RuntimeWarning (que el except TypeError no
            # atrapa) cada vez que se abre un evento.
            if getattr(boton, "_sesion_conectada", False):
                boton.clicked.disconnect()
                boton._sesion_conectada = False

            boton.setChecked(False)
            boton.setProperty("estadoSesion", "")
            boton._codigo = None

            match = next((s for s in info_sesiones_ordenada if s['indice'] == i), None)
            if match is None:
                boton.setText("No disponible")
                boton.setToolTip("")
                boton.setEnabled(False)
                boton.style().unpolish(boton)
                boton.style().polish(boton)
                continue

            codigo = self.CODIGOS_SESION.get(match['nombre'], match['nombre'])
            nombre_es = traducir_sesion(match['nombre'])
            self.sesiones_info[codigo] = {
                'nombre': nombre_es, 'fecha': match['fecha'], 'pasada': match['pasada'],
            }

            boton.setEnabled(True)
            boton._codigo = codigo
            boton.clicked.connect(
                lambda checked, y=year, g=gp, c=codigo, b=boton: self._click_sesion(y, g, c, b)
            )
            boton._sesion_conectada = True

            fecha_txt = dia_hora(match['fecha']) if pd.notna(match['fecha']) else "sin fecha"
            fecha_completa = (
                match['fecha'].strftime('%d/%m/%Y %H:%M') if pd.notna(match['fecha']) else "sin fecha"
            )

            if match['pasada']:
                boton.setText(f"{nombre_es}\n{fecha_txt}")
                boton.setProperty("estadoSesion", "pasada")
                boton.setToolTip(f"{nombre_es} — {fecha_completa} (GMT-3) · ver resultados")
            elif i == indice_proxima:
                boton.setText(f"{nombre_es}\nPRÓXIMA · {fecha_txt}")
                boton.setProperty("estadoSesion", "proxima")
                boton.setToolTip(f"{nombre_es} — próxima sesión, {fecha_completa} (GMT-3)")
            else:
                boton.setText(f"{nombre_es}\n{fecha_txt}")
                boton.setProperty("estadoSesion", "futura")
                boton.setToolTip(f"{nombre_es} — {fecha_completa} (GMT-3), todavía no se corrió")

            boton.style().unpolish(boton)
            boton.style().polish(boton)

        self._mostrar_info_circuito()

        # Abre en la sesión que más interesa: la última que se corrió (sus
        # resultados) o, si no se corrió ninguna, la próxima.
        pasadas = [s['indice'] for s in info_sesiones_ordenada if s['pasada']]
        inicial = pasadas[-1] if pasadas else indice_proxima
        if inicial is not None:
            self.botones_sesion[inicial].click()
        else:
            self._mostrar_pendiente(None)

    def _click_sesion(self, year, gp, codigo, boton):
        boton.setChecked(True)
        if self.sesiones_info.get(codigo, {}).get('pasada'):
            self.cargar_sesion(year, gp, codigo)
        else:
            # Una sesión futura no tiene nada que bajar: no hay request que hacer.
            self.codigo_sesion = codigo
            self.spinner.detener()
            self._set_estado("")
            self._mostrar_pendiente(codigo)

    def cargar_sesion(self, year, gp, codigo_sesion):
        nombre = self.sesiones_info.get(codigo_sesion, {}).get('nombre', codigo_sesion)
        self._set_estado(f"Cargando {nombre}...", "cargando")
        self.spinner.iniciar()
        self.tabla_resultados.setRowCount(0)
        self.stack_contenido.setCurrentIndex(0)
        self.codigo_sesion = codigo_sesion
        self._sesion_pedida = (year, gp, codigo_sesion)

        worker = SessionWorker(year, gp, codigo_sesion)
        worker.terminado.connect(self.on_sesion_cargada)
        worker.error.connect(self.on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _es_vieja(self, worker):
        """El código solo no alcanza: la carrera del GP anterior también es 'R'."""
        return (worker.year, worker.gp, worker.codigo_sesion) != self._sesion_pedida

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def on_sesion_cargada(self, sesion):
        worker = self.sender()
        if self._es_vieja(worker):
            return  # llegó tarde: el usuario ya clickeó otra sesión u otro GP

        self.spinner.detener()
        self._set_estado("")
        resultados = sesion.results

        if resultados is None or resultados.empty:
            self._mostrar_pendiente(self.codigo_sesion)
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
                # En clasificación cada uno marca su tiempo en un segmento
                # distinto (Q3/Q2/Q1): restarlos daría diferencias que no
                # crecen con la posición. Ahí va el tiempo a secas.
                etiquetas.append('Tiempo' if es_clasificacion else 'Mejor vuelta / dif.')
            elif 'Time' in resultados.columns:
                columnas.append('Time')
                etiquetas.append('Tiempo / dif.')
            if 'Laps' in resultados.columns and resultados['Laps'].notna().any():
                columnas.append('Laps')
                etiquetas.append('Vueltas')
        else:
            columnas = ['Position', 'Abbreviation', 'FullName', 'TeamName',
                        'GridPosition', 'Status', 'Points', 'Time']
            etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Largada', 'Estado', 'Pts',
                         'Tiempo / dif.']

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
        mejor_vuelta = (resultados['BestLapTime'].min()
                        if 'BestLapTime' in resultados.columns and not es_clasificacion
                        else None)
        color_dato, color_primario = QColor(DATO), QColor(PRIMARIO)
        con_ficha = self._ids_con_ficha(worker.year)

        for fila, (_, row) in enumerate(resultados.iterrows()):
            posicion = row.get('Position')

            for col, nombre_col in enumerate(columnas):
                valor = row.get(nombre_col)
                texto = self._formatear_valor(nombre_col, valor)
                # Del 2º para abajo, la diferencia con el 1º: en carrera fastf1
                # ya la trae en Time; en práctica/clasificación se calcula.
                if fila > 0 and pd.notna(valor):
                    if nombre_col == 'Time':
                        texto = self._formatear_dif(valor)
                    elif nombre_col == 'BestLapTime' and mejor_vuelta is not None and pd.notna(mejor_vuelta):
                        texto = self._formatear_dif(valor - mejor_vuelta)
                item = QTableWidgetItem(texto)

                if nombre_col in ('Position', 'Points', 'Laps', 'GridPosition'):
                    item.setTextAlignment(Qt.AlignCenter)
                if nombre_col in columnas_monoespaciadas:
                    item.setFont(fuente_datos)
                # Los nombres de piloto y equipo se cortan cuando la columna es
                # angosta; el tooltip es la única forma de leerlos completos.
                item.setToolTip(texto)

                if nombre_col == 'Position' and pd.notna(posicion):
                    item.setData(Qt.UserRole, int(posicion))   # medalla del podio
                if nombre_col == 'TeamName':
                    franja = franja_equipo(row.get('TeamColor'))
                    if franja is not None:
                        item.setIcon(franja)
                # El equipo abre su ficha; el resto de la fila, la del piloto.
                tipo, id_ = (('equipo', row.get('TeamId')) if nombre_col == 'TeamName'
                             else ('piloto', row.get('DriverId')))
                if id_ in con_ficha[tipo]:
                    marcar_ficha(item, tipo, id_)
                if nombre_col in ('Time', 'BestLapTime'):
                    item.setForeground(color_primario if fila == 0 else color_dato)
                self.tabla_resultados.setItem(fila, col, item)

        # Todo al ancho de su contenido, y lo que sobra para piloto y equipo:
        # estirar las 8 columnas por igual cortaba los nombres ("George ...").
        cabecera = self.tabla_resultados.horizontalHeader()
        cabecera.setSectionResizeMode(QHeaderView.ResizeToContents)
        for col, nombre_col in enumerate(columnas):
            if nombre_col in ('FullName', 'TeamName'):
                cabecera.setSectionResizeMode(col, QHeaderView.Stretch)
            # El título alineado como sus celdas (el header centra por defecto).
            self.tabla_resultados.horizontalHeaderItem(col).setTextAlignment(
                Qt.AlignCenter if nombre_col in ('Position', 'Points', 'Laps', 'GridPosition')
                else Qt.AlignLeft | Qt.AlignVCenter)

    def _ids_con_ficha(self, anio):
        """Pilotos y equipos del campeonato de ese año: los únicos que tienen
        ficha. Un reserva que sólo corrió una FP1 no está."""
        if self._con_historial is None:
            self._con_historial = historial.abrir_base()
        return {"piloto": {p['driver_id'] for p in historial.pilotos_temporada(self._con_historial, anio)},
                "equipo": {e['constructor_id'] for e in historial.equipos_temporada(self._con_historial, anio)}}

    def _activar(self, indice):
        ficha = ficha_de(indice)
        if ficha:
            self.abrir_ficha.emit(*ficha)

    def _mostrar_info_circuito(self):
        """Ficha del circuito en la columna derecha + su mapa."""
        location = self.evento_actual.get('Location')
        datos = obtener_datos_circuito(location)

        nombre = datos['nombre_completo'] if datos else (location or "—")
        oficial = self.evento_actual.get('OfficialEventName')
        oficial = oficial if oficial and str(oficial) != 'nan' else None
        self.texto_info.setText(
            ficha_html(nombre, filas_ficha(datos), oficial)
            + f"<div style='color:{PRIMARIO}; font-weight:600; margin-top:12px;'>"
              "Más datos del circuito&nbsp;&nbsp;›</div>")
        self._ficha_actual = (nombre, datos, oficial)

        self._cargar_mapa(location)

    def _ampliar_mapa(self):
        if self._pixmap_mapa is None or self._pixmap_mapa.isNull():
            return
        ventana = self.window()
        mapa = QLabel()
        mapa.setObjectName("imagenCircuito")   # mismo panel que el mapa chico
        mapa.setPixmap(self._pixmap_mapa.scaled(
            int(ventana.width() * 0.85), int(ventana.height() * 0.78),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))
        VistaAmpliada(self._ficha_actual[0], mapa, self).open()

    def _ampliar_datos(self):
        nombre, datos, oficial = self._ficha_actual
        panel = PanelDatosCircuito(nombre, datos, oficial, self._workers_activos)
        panel.setFixedSize(min(980, int(self.window().width() * 0.85)),
                           int(self.window().height() * 0.75))
        VistaAmpliada("Datos del circuito", panel, self).open()

    def _hacer_clickeable(self, etiqueta, tooltip):
        """Mapa y ficha se abren en grande: cursor de mano, foco con Tab y la
        propiedad `clickeable`, que en style.qss les da hover, foco y presionado."""
        etiqueta.setProperty("clickeable", True)
        etiqueta.setProperty("presionada", False)
        etiqueta.setAttribute(Qt.WA_Hover, True)
        etiqueta.setCursor(Qt.PointingHandCursor)
        etiqueta.setFocusPolicy(Qt.StrongFocus)
        etiqueta.setToolTip(tooltip)
        etiqueta.installEventFilter(self)

    def eventFilter(self, obj, evento):
        # Se abren con un clic, o con Enter / espacio si tienen el foco.
        # getattr: el mapa ya recibe eventos mientras se arma la ficha.
        if obj is self.imagen_circuito:
            accion = self._ampliar_mapa
        elif obj is getattr(self, "texto_info", None):
            accion = self._ampliar_datos
        else:
            return super().eventFilter(obj, evento)
        tipo = evento.type()
        if tipo in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            obj.setProperty("presionada", tipo == QEvent.MouseButtonPress)
            obj.style().unpolish(obj)
            obj.style().polish(obj)
        if tipo == QEvent.MouseButtonRelease or (
                tipo == QEvent.KeyPress
                and evento.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space)):
            accion()
            return True
        return super().eventFilter(obj, evento)

    def _mostrar_pendiente(self, codigo_sesion):
        """Panel de la izquierda cuando no hay resultados que mostrar."""
        info = self.sesiones_info.get(codigo_sesion, {})
        nombre = info.get('nombre', "")
        fecha = info.get('fecha')
        self.etiqueta_pendiente.setText(nombre.upper())

        if codigo_sesion is None:
            self.titulo_pendiente.setText("Sin sesiones")
            self.texto_pendiente.setText("Este evento no tiene sesiones publicadas.")
        elif info.get('pasada'):
            self.titulo_pendiente.setText("Sin resultados todavía")
            self.texto_pendiente.setText(
                f"{nombre} ya se corrió, pero los resultados todavía no están publicados.")
        else:
            self.titulo_pendiente.setText("Todavía no se corrió")
            lineas = []
            if pd.notna(fecha):
                lineas.append(f"{dia_hora(fecha)} (GMT-3) · {fecha:%d/%m/%Y}")
                dias_restantes = (fecha.normalize() - pd.Timestamp.now().normalize()).days
                if dias_restantes > 0:
                    lineas.append(f"Faltan {dias_restantes} día(s).")
                elif dias_restantes == 0:
                    lineas.append("¡Es hoy!")
            lineas.append("Los resultados aparecen acá cuando termine la sesión.")
            self.texto_pendiente.setText("\n".join(lineas))

        self.stack_contenido.setCurrentIndex(1)

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
        """Escala el mapa al ancho de la columna del circuito.

        La columna es de ancho fijo, así que el tamaño destino no depende del
        resize de la ventana. Guarda el pixmap original sin escalar; llamar sin
        `ruta` re-escala el que ya está.
        """
        if ruta is not None:
            self._pixmap_mapa = QPixmap(ruta)
            self._tamano_mapa_pintado = None   # pixmap nuevo: hay que re-escalar
        if self._pixmap_mapa is None or self._pixmap_mapa.isNull():
            return

        # Nunca agrandar más allá del PNG original: ampliarlo sólo lo pixela.
        ancho = min(self.ANCHO_COLUMNA_CIRCUITO - self.PADDING_IMAGEN, self._pixmap_mapa.width())
        alto = min(self.ALTO_MAPA, self._pixmap_mapa.height())

        # Los PNG de cache_tracks llegan a 2275x2400: si el destino no cambió,
        # no hay nada que rehacer.
        if (ancho, alto) != self._tamano_mapa_pintado:
            self._tamano_mapa_pintado = (ancho, alto)
            self.imagen_circuito.setPixmap(self._pixmap_mapa.scaled(
                ancho, alto, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        self.imagen_circuito.show()

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

    @staticmethod
    def _formatear_dif(diferencia):
        """'+0.108', o '+1:02.312' si pasa del minuto."""
        segundos = diferencia.total_seconds()
        if segundos >= 60:
            return f"+{int(segundos // 60)}:{segundos % 60:06.3f}"
        return f"+{segundos:.3f}"

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

    def on_error(self, mensaje):
        worker = self.sender()
        if worker is not None and self._es_vieja(worker):
            return

        self.spinner.detener()
        self._set_estado(f"Error al cargar: {mensaje}", "error")

    def _set_estado(self, texto, tipo=""):
        aplicar_estado(self.estado, texto, tipo)
