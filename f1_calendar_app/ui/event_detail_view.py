from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Signal
from workers.session_worker import SessionWorker

class EventDetailView(QWidget):
    volver = Signal()

    def __init__(self):
        super().__init__()

        self.titulo = QLabel()
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

        columnas = ['Position', 'Abbreviation', 'TeamName']
        self.tabla_resultados.setColumnCount(len(columnas))
        self.tabla_resultados.setHorizontalHeaderLabels(columnas)
        self.tabla_resultados.setRowCount(len(resultados))

        for fila, (_, row) in enumerate(resultados.iterrows()):
            for col, nombre_col in enumerate(columnas):
                item = QTableWidgetItem(str(row[nombre_col]))
                self.tabla_resultados.setItem(fila, col, item)

        self.tabla_resultados.resizeColumnsToContents()

    def on_error(self, mensaje):
        self.estado.setText(f"Error al cargar: {mensaje}")