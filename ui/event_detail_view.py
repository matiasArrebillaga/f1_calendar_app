from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QButtonGroup, QHeaderView,
    QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
import pandas as pd
from workers.session_worker import SessionWorker
from ui.spinner_widget import SpinnerWidget
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

        self.panel_info = QLabel()
        self.panel_info.setObjectName("panelInfoEvento")
        self.panel_info.setWordWrap(True)
        self.panel_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)

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

        for i in range(self.TOTAL_SLOTS_SESION):
            boton = self.sidebar_botones[i]
            nombre_sesion = evento.get(f'Session{i + 1}')
            fecha_sesion = evento.get(f'Session{i + 1}Date')

            try:
                boton.clicked.disconnect()
            except TypeError:
                pass

            boton.setChecked(False)

            if nombre_sesion and str(nombre_sesion) != 'nan':
                codigo = codigos.get(nombre_sesion, nombre_sesion)
                boton.setText(nombre_sesion)
                boton.setEnabled(True)
                boton.clicked.connect(
                    lambda checked, y=year, g=gp, c=codigo, b=boton: self._click_sesion(y, g, c, b)
                )
                self.sesiones_info[codigo] = {'nombre': nombre_sesion, 'fecha': fecha_sesion}

                if nombre_sesion == 'Race':
                    boton_race = boton
                    codigo_race = codigo
            else:
                boton.setText("No disponible")
                boton.setEnabled(False)

        # Auto-selección: si la carrera ya se corrió, mostramos sus resultados de una.
        hoy = pd.Timestamp.now()
        if codigo_race and pd.notna(self.sesiones_info[codigo_race]['fecha']):
            fecha_race = self._convertir_a_gmt_menos_3(self.sesiones_info[codigo_race]['fecha'])
            if fecha_race < hoy:
                boton_race.setChecked(True)
                self.cargar_sesion(year, gp, codigo_race)
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
            self._mostrar_panel_info()
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

    def _mostrar_panel_info(self):
        info = self.sesiones_info.get(self.codigo_sesion, {})
        nombre_sesion = info.get('nombre', self.codigo_sesion)
        fecha = self._convertir_a_gmt_menos_3(info.get('fecha'))

        lineas = [
            f"<b>{nombre_sesion}</b> todavía no se corrió.",
            "",
            f"<b>Circuito:</b> {self.evento_actual.get('Location', '—')}",
            f"<b>País:</b> {self.evento_actual.get('Country', '—')}",
            f"<b>Nombre oficial:</b> {self.evento_actual.get('OfficialEventName', '—')}",
        ]

        if pd.notna(fecha):
            hoy = pd.Timestamp.now()
            dias_restantes = (fecha.normalize() - hoy.normalize()).days

            lineas.append(f"<b>Fecha (GMT-3):</b> {fecha.strftime('%d/%m/%Y %H:%M')}")

            if dias_restantes > 0:
                lineas.append(f"<b>Faltan:</b> {dias_restantes} día(s)")
            elif dias_restantes == 0:
                lineas.append("<b>¡Es hoy!</b>")
            else:
                lineas.append("Todavía no hay resultados cargados para esta sesión.")

        self.panel_info.setText("<br>".join(lineas))
        self.stack_contenido.setCurrentIndex(1)

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