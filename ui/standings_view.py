from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QLabel, QSizePolicy, QHeaderView
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from workers.standings_worker import StandingsWorker


class StandingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.year = None
        self._year_pedido = None
        self._cache_por_anio = {}   # {year: (pilotos, equipos)} | {year: None} si no hay datos
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_pilotos.setObjectName("tabHorizontalIzq")
        self.boton_equipos = QPushButton("Equipos")
        self.boton_equipos.setObjectName("tabHorizontalDer")
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setCheckable(True)
            boton.setMinimumHeight(38)
            boton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            boton.setCursor(Qt.PointingHandCursor)
        self.boton_pilotos.setChecked(True)
        self.boton_pilotos.setToolTip("Clasificación de pilotos")
        self.boton_equipos.setToolTip("Clasificación de constructores")

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
        self.tabla_pilotos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_pilotos.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_pilotos.setEditTriggers(QTableWidget.NoEditTriggers)
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
        self.tabla_equipos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_equipos.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_equipos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_equipos.horizontalHeader().setStretchLastSection(True)
        self.tabla_equipos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")

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

    def _set_estado(self, texto, tipo=""):
        # ponytail: mismas 4 líneas que EventDetailView._set_estado. Dos usos no
        # justifican un helper compartido; extraer si aparece una tercera vista.
        nombres = {"": "estadoVacio", "cargando": "estadoCargando",
                   "error": "estadoError", "vacio": "estadoVacio"}
        self.estado.setObjectName(nombres.get(tipo, "estadoVacio"))
        self.estado.setText(texto)
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)

    def pedir_anio(self, year):
        """Anota el año sin pedir nada a la red. La carga real ocurre en
        showEvent, cuando esta vista es la que se está mirando."""
        self._year_pedido = year
        if self.isVisible():
            self.cargar_datos(year)

    def showEvent(self, event):
        super().showEvent(event)
        if self._year_pedido is not None and self._year_pedido != self.year:
            self.cargar_datos(self._year_pedido)

    def cargar_datos(self, year):
        self.year = year

        if year in self._cache_por_anio:
            cacheado = self._cache_por_anio[year]
            if cacheado is None:
                self._mostrar_sin_datos(year)
            else:
                self._set_estado("")
                self._llenar_tabla_pilotos(cacheado[0])
                self._llenar_tabla_equipos(cacheado[1])
            return

        self._set_estado(f"Cargando clasificación {year}...", "cargando")
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

        self._cache_por_anio[worker.year] = (standings_pilotos, standings_equipos)
        self._set_estado("")
        self._llenar_tabla_pilotos(standings_pilotos)
        self._llenar_tabla_equipos(standings_equipos)

    def on_error(self, mensaje):
        worker = self.sender()
        # Cacheamos también el fallo: los años sin datos en Ergast (la década
        # del 50 no tiene constructores) si no, re-pegaban en cada visita.
        self._cache_por_anio[worker.year] = None
        if worker.year != self.year:
            return

        self._mostrar_sin_datos(self.year)

    def _mostrar_sin_datos(self, year):
        self._set_estado(f"No hay clasificación disponible para {year}.", "vacio")
        self.tabla_pilotos.setRowCount(0)
        self.tabla_equipos.setRowCount(0)

    def _llenar_tabla_pilotos(self, df):
        etiquetas = ['Pos', 'Cod', 'Piloto', 'Equipo', 'Pts', 'Victorias']

        self.tabla_pilotos.setColumnCount(len(etiquetas))
        self.tabla_pilotos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_pilotos.setRowCount(len(df))
        self.tabla_pilotos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

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
                item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item.setFont(QFont("Segoe UI", 12))
                item.setToolTip(texto)
                self.tabla_pilotos.setItem(fila, col, item)

        self.tabla_pilotos.resizeRowsToContents()

    def _llenar_tabla_equipos(self, df):
        columnas = ['position', 'constructorName', 'points', 'wins']
        etiquetas = ['Pos', 'Equipo', 'Pts', 'Victorias']

        self.tabla_equipos.setColumnCount(len(columnas))
        self.tabla_equipos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_equipos.setRowCount(len(df))
        self.tabla_equipos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for fila, (_, row) in enumerate(df.iterrows()):
            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                texto = str(int(valor)) if nombre_col in ('position', 'wins', 'points') else str(valor)
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item.setFont(QFont("Segoe UI", 12))
                item.setToolTip(texto)
                self.tabla_equipos.setItem(fila, col, item)

        self.tabla_equipos.resizeRowsToContents()