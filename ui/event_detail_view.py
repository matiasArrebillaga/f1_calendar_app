from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QButtonGroup, QHeaderView,
    QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
import pandas as pd
from workers.session_worker import SessionWorker
from ui.spinner_widget import SpinnerWidget

class EventDetailView(QWidget):
    volver = Signal()

    # Colores de posición estilo overlay de transmisión.
    COLOR_PRIMERO = QColor("#8a6d0e")   # oro
    COLOR_SEGUNDO = QColor("#5c6068")   # plata
    COLOR_TERCERO = QColor("#7a4a1e")   # bronce
    COLOR_TOP10 = QColor("#1c2a63")     # azul puntos
    COLOR_Q1 = QColor("#5c1010")        # eliminado Q1
    COLOR_Q2 = QColor("#6e4a0f")        # eliminado Q2

    TOTAL_SLOTS_SESION = 5
    COL_SIDEBAR = 190

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # --- Grid raíz: columna 0 = sidebar de sesiones, columna 1 = contenido ---
        # Las pestañas de sesión arrancan en la misma fila que la tabla de
        # resultados (fila FILA_TABLA) y ocupan la misma cantidad de filas,
        # así su borde superior queda a la altura del encabezado "Pos, Cod...".
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

        # --- Encabezado: ronda + título + país ---
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
        self.spinner = SpinnerWidget(tamano=20)
        self.spinner.hide()

        layout_estado = QHBoxLayout()
        layout_estado.addWidget(self.spinner)
        layout_estado.addWidget(self.estado)
        layout_estado.addStretch()
        self.tabla_resultados = QTableWidget()
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.verticalHeader().setVisible(False)
        self.tabla_resultados.setSelectionMode(QTableWidget.NoSelection)
        self.tabla_resultados.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_resultados.setShowGrid(False)
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        boton_volver = QPushButton("← Volver")
        boton_volver.setFixedWidth(140)
        layout_volver = QHBoxLayout()
        layout_volver.addStretch()
        layout_volver.addWidget(boton_volver)

        grid_raiz.addLayout(fila_encabezado, 0, 1)
        grid_raiz.addWidget(linea_acento, 1, 1)
        grid_raiz.addLayout(layout_estado, 2, 1)
        grid_raiz.addWidget(
            self.tabla_resultados, FILA_TABLA, 1, self.TOTAL_SLOTS_SESION, 1
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

    def mostrar_evento(self, evento):
        self.titulo.setText(str(evento['EventName']))
        self.subtitulo.setText(str(evento['Country']))

        ronda = evento.get('RoundNumber')
        self.badge_ronda.setText(f"R{int(ronda)}" if pd.notna(ronda) else "")

        self.tabla_resultados.clear()
        self.tabla_resultados.setRowCount(0)
        self._set_estado("")

        codigos = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
                   'Qualifying': 'Q', 'Sprint': 'S', 'Sprint Qualifying': 'SQ',
                   'Race': 'R'}

        year = int(evento['EventDate'].year)
        gp = int(evento['RoundNumber'])

        for i in range(self.TOTAL_SLOTS_SESION):
            boton = self.sidebar_botones[i]
            nombre_sesion = evento.get(f'Session{i + 1}')

            try:
                boton.clicked.disconnect()
            except TypeError:
                pass  # no tenía ninguna conexión previa, no hay nada que desconectar

            boton.setChecked(False)

            if nombre_sesion and str(nombre_sesion) != 'nan':
                codigo = codigos.get(nombre_sesion, nombre_sesion)
                boton.setText(nombre_sesion)
                boton.setEnabled(True)
                boton.clicked.connect(
                    lambda checked, y=year, g=gp, c=codigo: self.cargar_sesion(y, g, c)
                )
            else:
                boton.setText("No disponible")
                boton.setEnabled(False)

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
            self._set_estado("Esta sesión todavía no tiene resultados.", tipo="vacio")
            return

        self._set_estado("")

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

    def on_error(self, mensaje):
        self.spinner.detener()
        self.estado.setText(f"Error al cargar: {mensaje}")

    def _set_estado(self, texto, tipo=""):
        """
        tipo: '' | 'cargando' | 'error' | 'vacio'
        Cambia el objectName para que style.qss aplique el color correcto
        (ámbar para cargando, rojo para error, gris para vacío).
        """
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
