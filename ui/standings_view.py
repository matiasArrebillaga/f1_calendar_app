from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QLabel
)
from workers.standings_worker import StandingsWorker


class StandingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.year = None
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_equipos = QPushButton("Equipos")
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setCheckable(True)
        self.boton_pilotos.setChecked(True)

        layout_tabs = QHBoxLayout()
        layout_tabs.addWidget(self.boton_pilotos)
        layout_tabs.addWidget(self.boton_equipos)
        layout_tabs.addStretch()

        self.tabla_pilotos = QTableWidget()
        self.tabla_equipos = QTableWidget()
        self.estado = QLabel()

        self.stack_interno = QStackedWidget()
        self.stack_interno.addWidget(self.tabla_pilotos)
        self.stack_interno.addWidget(self.tabla_equipos)

        layout = QVBoxLayout()
        layout.addLayout(layout_tabs)
        layout.addWidget(self.estado)
        layout.addWidget(self.stack_interno)
        self.setLayout(layout)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(0))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(1))

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == 0)
        self.boton_equipos.setChecked(indice == 1)
        self.stack_interno.setCurrentIndex(indice)

    def cargar_datos(self, year):
        self.year = year
        self.estado.setText("Cargando standings...")
        self.tabla_pilotos.setRowCount(0)
        self.tabla_equipos.setRowCount(0)

        worker = StandingsWorker(year)
        worker.terminado.connect(self.on_standings_cargados)
        worker.error.connect(self.on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))

        self._workers_activos.append(worker)
        worker.start()

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def on_standings_cargados(self, standings_pilotos, standings_equipos):
        worker = self.sender()
        if worker.year != self.year:
            return  # llegó tarde: el usuario ya cambió de año, ignoramos este resultado

        self.estado.setText("")
        self._llenar_tabla_pilotos(standings_pilotos)
        self._llenar_tabla_equipos(standings_equipos)

    def on_error(self, mensaje):
        worker = self.sender()
        if worker.year != self.year:
            return

        self.estado.setText(f"No hay standings disponibles para {self.year}.")
        self.tabla_pilotos.setRowCount(0)
        self.tabla_equipos.setRowCount(0)

    def _llenar_tabla_pilotos(self, df):
        columnas = ['position', 'driverCode', 'givenName', 'familyName', 'constructorNames', 'points', 'wins']
        etiquetas = ['Pos', 'Cod', 'Nombre', 'Apellido', 'Equipo', 'Pts', 'Victorias']

        self.tabla_pilotos.setColumnCount(len(columnas))
        self.tabla_pilotos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_pilotos.setRowCount(len(df))

        for fila, (_, row) in enumerate(df.iterrows()):
            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                if nombre_col == 'constructorNames':
                    texto = " / ".join(valor)
                elif nombre_col in ('position', 'wins'):
                    texto = str(int(valor))
                else:
                    texto = str(valor)
                item = QTableWidgetItem(texto)
                self.tabla_pilotos.setItem(fila, col, item)

        self.tabla_pilotos.resizeColumnsToContents()

    def _llenar_tabla_equipos(self, df):
        columnas = ['position', 'constructorName', 'points', 'wins']
        etiquetas = ['Pos', 'Equipo', 'Pts', 'Victorias']

        self.tabla_equipos.setColumnCount(len(columnas))
        self.tabla_equipos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_equipos.setRowCount(len(df))

        for fila, (_, row) in enumerate(df.iterrows()):
            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                texto = str(int(valor)) if nombre_col in ('position', 'wins') else str(valor)
                item = QTableWidgetItem(texto)
                self.tabla_equipos.setItem(fila, col, item)

        self.tabla_equipos.resizeColumnsToContents()