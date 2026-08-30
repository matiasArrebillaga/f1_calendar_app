from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
import pandas as pd
from workers.session_worker import SessionWorker

class EventDetailView(QWidget):
    volver = Signal()
    COLOR_PRIMERO = QColor("#EFBF04")   # gris claro
    COLOR_SEGUNDO = QColor("#c0c0c0") 
    COLOR_TERCERO = QColor("#815931") 
    COLOR_TOP10 = QColor("#394E88")
    COLOR_Q1 = QColor("#700909") 
    COLOR_Q2 = QColor("#805515")
    def __init__(self):
        super().__init__()
        
        self.titulo = QLabel()
        self.titulo.setObjectName("titulo")        
        self.layout_sesiones = QVBoxLayout()
        self.estado = QLabel()
        self.tabla_resultados = QTableWidget()
        boton_volver = QPushButton("← Volver al calendario")

        layout = QVBoxLayout()
        layout.addWidget(self.titulo)
        layout.addLayout(self.layout_sesiones)
        layout.addWidget(self.estado)
        layout.addWidget(self.tabla_resultados)
        layout.addWidget(boton_volver)
        self.setLayout(layout)

        boton_volver.clicked.connect(self.volver.emit)
        self.worker = None  # acá vamos a guardar el worker activo

    def mostrar_evento(self, evento):
        self.titulo.setText(f"{evento['EventName']} — {evento['Country']}")
        self.tabla_resultados.clear()
        self.tabla_resultados.setRowCount(0)
        self.estado.setText("")

        while self.layout_sesiones.count():
            item = self.layout_sesiones.takeAt(0)
            item.widget().deleteLater()

        codigos = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
                   'Qualifying': 'Q', 'Sprint': 'S', 'Sprint Qualifying': 'SQ',
                   'Race': 'R'}

        year = int(evento['EventDate'].year)
        gp = int(evento['RoundNumber'])

        for i in range(1, 6):
            nombre_sesion = evento.get(f'Session{i}')
            if nombre_sesion and str(nombre_sesion) != 'nan':
                codigo = codigos.get(nombre_sesion, nombre_sesion)
                boton = QPushButton(f"Ver {nombre_sesion}")
                boton.clicked.connect(
                    lambda checked, y=year, g=gp, c=codigo: self.cargar_sesion(y, g, c)
                )
                self.layout_sesiones.addWidget(boton)
    def cargar_sesion(self, year, gp, codigo_sesion):
        self.estado.setText("Cargando...")
        self.tabla_resultados.setRowCount(0)
        self.codigo_sesion = codigo_sesion

        self.worker = SessionWorker(year, gp, codigo_sesion)
        self.worker.terminado.connect(self.on_sesion_cargada)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    def on_sesion_cargada(self, sesion):
        self.estado.setText("")
        resultados = sesion.results
        
        if resultados is None or resultados.empty:
            self.estado.setText("Esta sesión todavía no tiene resultados.")
            return

        columnas = ['Position', 'Abbreviation', 'FullName', 'TeamName',
                    'GridPosition', 'Status', 'Points', 'Time']
        etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Largada', 'Estado', 'Pts', 'Tiempo']
    
        self.tabla_resultados.setColumnCount(len(columnas))
        self.tabla_resultados.setHorizontalHeaderLabels(etiquetas)
        self.tabla_resultados.setRowCount(len(resultados))

        es_clasificacion = self.codigo_sesion in ('Q', 'SQ')
        total_pilotos = len(resultados)

        for fila, (_, row) in enumerate(resultados.iterrows()):
            color = self._color_por_posicion(row.get('Position'), es_clasificacion, total_pilotos)

            for col, nombre_col in enumerate(columnas):
                valor = row.get(nombre_col)
                texto = self._formatear_valor(nombre_col, valor)
                item = QTableWidgetItem(texto)
                if color is not None:
                    item.setBackground(color)
                    item.setForeground(QColor("white"))  # legibilidad sobre fondos oscuros
                self.tabla_resultados.setItem(fila, col, item)

        self.tabla_resultados.resizeColumnsToContents()
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
        self.estado.setText(f"Error al cargar: {mensaje}")