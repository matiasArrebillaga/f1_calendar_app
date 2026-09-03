from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QButtonGroup, QHeaderView,
    QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtGui import QColor, QFont
import pandas as pd
from workers.session_worker import SessionWorker
from ui.spinner_widget import SpinnerWidget
from PySide6.QtGui import QPixmap
from core.circuits import obtener_datos_circuito, obtener_ruta_imagen_circuito
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
        self.tabla_resultados.setSelectionMode(QTableWidget.NoSelection)
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
        self.imagen_circuito.setAlignment(Qt.AlignCenter)
        self.imagen_circuito.setStyleSheet(
            "background-color: #f5f5f5; border-radius: 10px; padding: 14px;"
        )
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
        self.worker = None
        self.codigo_sesion = None
        self.evento_actual = None
        self.sesiones_info = {}  # {codigo: {'nombre': str, 'fecha': Timestamp}}

    def mostrar_evento(self, evento):
        self.evento_actual = evento
        self.titulo.setText(str(evento['EventName']))
        self.subtitulo.setText(str(evento['Country']))

        ronda = evento.get('RoundNumber')
        self.badge_ronda.setText(f"R{int(ronda)}" if pd.notna(ronda) else "")

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
        boton_race = None
        codigo_race = None
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

            try:
                boton.clicked.disconnect()
            except TypeError:
                pass

            boton.setChecked(False)
            boton.setProperty("estadoSesion", "")

            match = next((s for s in info_sesiones_ordenada if s['indice'] == i), None)
            if match is None:
                boton.setText("No disponible")
                boton.setEnabled(False)
                boton.style().unpolish(boton)
                boton.style().polish(boton)
                continue

            codigos = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
                       'Qualifying': 'Q', 'Sprint': 'S', 'Sprint Qualifying': 'SQ',
                       'Race': 'R'}
            codigo = codigos.get(match['nombre'], match['nombre'])
            self.sesiones_info[codigo] = {'nombre': match['nombre'], 'fecha': match['fecha']}

            year = int(evento['EventDate'].year)
            gp = int(evento['RoundNumber'])
            boton.setEnabled(True)
            boton.clicked.connect(
                lambda checked, y=year, g=gp, c=codigo, b=boton: self._click_sesion(y, g, c, b)
            )

            if match['pasada']:
                boton.setText(match['nombre'])
                boton.setProperty("estadoSesion", "pasada")
            elif i == indice_proxima:
                fecha_txt = match['fecha'].strftime('%d/%m %H:%M') if pd.notna(match['fecha']) else ""
                boton.setText(f"{match['nombre']}\n{fecha_txt} — PRÓXIMA")
                boton.setProperty("estadoSesion", "proxima")
            else:
                fecha_txt = match['fecha'].strftime('%d/%m %H:%M') if pd.notna(match['fecha']) else ""
                boton.setText(f"{match['nombre']}\n{fecha_txt}")
                boton.setProperty("estadoSesion", "futura")

            boton.style().unpolish(boton)
            boton.style().polish(boton)

            if match['nombre'] == 'Race':
                boton_race = boton
                codigo_race = codigo

        self._mostrar_info_circuito()
    def _click_sesion(self, year, gp, codigo, boton):
        boton.setChecked(True)
        self.cargar_sesion(year, gp, codigo)

    def cargar_sesion(self, year, gp, codigo_sesion):
        self.estado.setText("Cargando resultados...")
        self.spinner.iniciar()
        self.tabla_resultados.setRowCount(0)
        self.codigo_sesion = codigo_sesion

        self.worker = SessionWorker(year, gp, codigo_sesion)
        self.worker.terminado.connect(self.on_sesion_cargada)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_sesion_cargada(self, sesion):
        self.spinner.detener()
        self.estado.setText("")
        resultados = sesion.results

        if resultados is None or resultados.empty:
            self._mostrar_info_circuito(codigo_sesion=self.codigo_sesion)
            return
        self.stack_contenido.setCurrentIndex(0)

        self.stack_contenido.setCurrentIndex(0)

        columnas = ['Position', 'Abbreviation', 'FullName', 'TeamName',
                    'GridPosition', 'Status', 'Points', 'Time']
        etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Largada', 'Estado', 'Pts', 'Tiempo']
        columnas_monoespaciadas = {'Position', 'GridPosition', 'Time', 'Points'}

        self.tabla_resultados.setColumnCount(len(columnas))
        self.tabla_resultados.setHorizontalHeaderLabels(etiquetas)
        self.tabla_resultados.setRowCount(len(resultados))

        fuente_datos = QFont("Consolas")
        fuente_datos.setStyleHint(QFont.Monospace)

        es_clasificacion = self.codigo_sesion in ('Q', 'SQ')
        total_pilotos = len(resultados)

        for fila, (_, row) in enumerate(resultados.iterrows()):
            color = self._color_por_posicion(row.get('Position'), es_clasificacion, total_pilotos)

            for col, nombre_col in enumerate(columnas):
                valor = row.get(nombre_col)
                texto = self._formatear_valor(nombre_col, valor)
                item = QTableWidgetItem(texto)

                if nombre_col in ('Position', 'Points'):
                    item.setTextAlignment(Qt.AlignCenter)
                if nombre_col in columnas_monoespaciadas:
                    item.setFont(fuente_datos)

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

        ruta_imagen = obtener_ruta_imagen_circuito(location)
        if ruta_imagen:
            pixmap = QPixmap(ruta_imagen).scaledToWidth(620, Qt.SmoothTransformation)
            self.imagen_circuito.setPixmap(pixmap)
            self.imagen_circuito.show()
        else:
            self.imagen_circuito.hide()

        lineas = []
        datos_circuito = obtener_datos_circuito(location)

        if datos_circuito:
            lineas.append(f"<b>{datos_circuito['nombre_completo']}</b>")
            lineas.append(f"Longitud: {datos_circuito['longitud_km']} km")
            lineas.append(f"Vueltas: {datos_circuito['vueltas']}")
            lineas.append(f"Distancia total: {datos_circuito['distancia_km']} km")
            lineas.append(f"Curvas: {datos_circuito['curvas']}")
            lineas.append(f"Récord de vuelta: {datos_circuito['record_vuelta']}")
            lineas.append(f"Primer GP: {datos_circuito['primer_gp']}")
        else:
            lineas.append(f"<b>Circuito:</b> {location or '—'}")

        lineas.append("")
        lineas.append(f"<b>País:</b> {self.evento_actual.get('Country', '—')}")
        lineas.append(f"<b>Nombre oficial del evento:</b> {self.evento_actual.get('OfficialEventName', '—')}")

        if codigo_sesion:
            info = self.sesiones_info.get(codigo_sesion, {})
            nombre_sesion = info.get('nombre', codigo_sesion)
            fecha = info.get('fecha')

            lineas.append("")
            lineas.append(f"<b>{nombre_sesion}</b> todavía no se corrió.")

            if pd.notna(fecha):
                hoy = pd.Timestamp.now()
                dias_restantes = (fecha.normalize() - hoy.normalize()).days

                lineas.append(f"<b>Fecha (GMT-3):</b> {fecha.strftime('%d/%m/%Y %H:%M')}")

                if dias_restantes > 0:
                    lineas.append(f"<b>Faltan:</b> {dias_restantes} día(s)")
                elif dias_restantes == 0:
                    lineas.append("<b>¡Es hoy!</b>")

        self.texto_info.setText("<br>".join(lineas))
        self.stack_contenido.setCurrentIndex(1)
        self._animacion_fade.stop()
        self._animacion_fade.start()        
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

        if nombre_col in ('Position', 'GridPosition', 'Points'):
            return str(int(valor))

        if nombre_col == 'Time':
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
        self.spinner.detener()
        self.estado.setText(f"Error al cargar: {mensaje}")

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