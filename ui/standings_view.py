from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QLabel, QSizePolicy, QHeaderView
)
from PySide6.QtGui import QFont
from workers.standings_worker import StandingsWorker


class StandingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.year = None
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_pilotos.setObjectName("tabHorizontalIzq")
        self.boton_equipos = QPushButton("Equipos")
        self.boton_equipos.setObjectName("tabHorizontalDer")
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setCheckable(True)
            boton.setMinimumHeight(38)
            boton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.boton_pilotos.setChecked(True)

        layout_tabs = QHBoxLayout()
        layout_tabs.setContentsMargins(12, 10, 12, 8)
        layout_tabs.addWidget(self.boton_pilotos)
        layout_tabs.addWidget(self.boton_equipos)
        layout_tabs.addStretch()

        self.tabla_pilotos = QTableWidget()
        self.tabla_pilotos.setObjectName("tablaStandings")
        self.tabla_pilotos.setAlternatingRowColors(True)
        self.tabla_pilotos.setShowGrid(True)
        self.tabla_pilotos.verticalHeader().setVisible(False)
        self.tabla_pilotos.setWordWrap(True)
        self.tabla_pilotos.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla_pilotos.setFont(QFont("Segoe UI", 12))
        self.tabla_pilotos.horizontalHeader().setStretchLastSection(True)
        self.tabla_pilotos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.tabla_equipos = QTableWidget()
        self.tabla_equipos.setObjectName("tablaStandings")
        self.tabla_equipos.setAlternatingRowColors(True)
        self.tabla_equipos.setShowGrid(True)
        self.tabla_equipos.verticalHeader().setVisible(False)
        self.tabla_equipos.setWordWrap(True)
        self.tabla_equipos.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla_equipos.setFont(QFont("Segoe UI", 12))
        self.tabla_equipos.horizontalHeader().setStretchLastSection(True)
        self.tabla_equipos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.estado = QLabel()

        self.stack_interno = QStackedWidget()
        self.stack_interno.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stack_interno.addWidget(self.tabla_pilotos)
        self.stack_interno.addWidget(self.tabla_equipos)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_tabs)
        layout.addWidget(self.estado)
        layout.addWidget(self.stack_interno, 1)
        self.setLayout(layout)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(0))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(1))

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == 0)
        self.boton_equipos.setChecked(indice == 1)
        self.stack_interno.setCurrentIndex(indice)

    def cargar_datos(self, year):
        self.year = year
        self.estado.setText("Cargando clasificación...")
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

        self.estado.setText(f"No hay clasificación disponible para {self.year}.")
        self.tabla_pilotos.setRowCount(0)
        self.tabla_equipos.setRowCount(0)

    def _llenar_tabla_pilotos(self, df):
        columnas = ['position', 'driverCode', 'givenName', 'familyName', 'constructorNames', 'points', 'wins']
        etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Pts', 'Victorias']

        self.tabla_pilotos.setColumnCount(len(columnas) - 1)
        self.tabla_pilotos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_pilotos.setRowCount(len(df))
        self.tabla_pilotos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_pilotos.setColumnWidth(0, 60)
        self.tabla_pilotos.setColumnWidth(1, 80)
        self.tabla_pilotos.setColumnWidth(3, 90)
        self.tabla_pilotos.setColumnWidth(4, 90)

        for fila, (_, row) in enumerate(df.iterrows()):
            fila_datos = [
                str(int(row['position'])),
                str(row['driverCode']),
                f"{row['givenName']} {row['familyName']}",
                " / ".join(row['constructorNames']),
                str(int(row['points'])),
                str(int(row['wins'])),
            ]

            for col, texto in enumerate(fila_datos):
                item = QTableWidgetItem(texto)
                item.setTextAlignment(0x0004 | 0x0080)
                item.setFont(QFont("Segoe UI", 12))
                self.tabla_pilotos.setItem(fila, col, item)

        self.tabla_pilotos.resizeRowsToContents()

    def _llenar_tabla_equipos(self, df):
        columnas = ['position', 'constructorName', 'points', 'wins']
        etiquetas = ['Pos', 'Equipo', 'Pts', 'Victorias']

        self.tabla_equipos.setColumnCount(len(columnas))
        self.tabla_equipos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_equipos.setRowCount(len(df))
        self.tabla_equipos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_equipos.setColumnWidth(0, 60)
        self.tabla_equipos.setColumnWidth(2, 90)
        self.tabla_equipos.setColumnWidth(3, 90)

        for fila, (_, row) in enumerate(df.iterrows()):
            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                texto = str(int(valor)) if nombre_col in ('position', 'wins', 'points') else str(valor)
                item = QTableWidgetItem(texto)
                item.setTextAlignment(0x0004 | 0x0080)
                item.setFont(QFont("Segoe UI", 12))
                self.tabla_equipos.setItem(fila, col, item)

        self.tabla_equipos.resizeRowsToContents()