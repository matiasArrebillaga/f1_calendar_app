from fastf1.ergast import Ergast
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QLabel, QButtonGroup, QHeaderView, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


class StandingsView(QWidget):
    COLOR_PRIMERO = QColor("#8a6d0e")   # oro
    COLOR_SEGUNDO = QColor("#5c6068")   # plata
    COLOR_TERCERO = QColor("#7a4a1e")   # bronce

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.year = None
        self.ergast = Ergast()

        titulo = QLabel("STANDINGS")
        titulo.setObjectName("titulo")

        linea_acento = QFrame()
        linea_acento.setObjectName("lineaAcento")

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_equipos = QPushButton("Equipos")
        self.grupo_tabs = QButtonGroup(self)
        self.grupo_tabs.setExclusive(True)
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setObjectName("tabHorizontal")
            boton.setCheckable(True)
            self.grupo_tabs.addButton(boton)
        self.boton_pilotos.setChecked(True)

        layout_tabs = QHBoxLayout()
        layout_tabs.setSpacing(8)
        layout_tabs.addWidget(self.boton_pilotos)
        layout_tabs.addWidget(self.boton_equipos)
        layout_tabs.addStretch()

        self.tabla_pilotos = self._crear_tabla()
        self.tabla_equipos = self._crear_tabla()
        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")

        self.stack_interno = QStackedWidget()
        self.stack_interno.addWidget(self.tabla_pilotos)
        self.stack_interno.addWidget(self.tabla_equipos)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(titulo)
        layout.addWidget(linea_acento)
        layout.addSpacing(10)
        layout.addLayout(layout_tabs)
        layout.addWidget(self.estado)
        layout.addWidget(self.stack_interno)
        self.setLayout(layout)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(0))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(1))

    def _crear_tabla(self):
        tabla = QTableWidget()
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setSelectionMode(QTableWidget.NoSelection)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setShowGrid(False)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return tabla

    def _cambiar_tab(self, indice):
        self.stack_interno.setCurrentIndex(indice)

    def cargar_datos(self, year):
        self.year = year
        self._set_estado("Cargando standings…", tipo="cargando")

        try:
            standings_pilotos = self.ergast.get_driver_standings(season=year).content[0]
            standings_equipos = self.ergast.get_constructor_standings(season=year).content[0]
        except Exception:
            self._set_estado(f"No hay standings disponibles para {year}.", tipo="vacio")
            self.tabla_pilotos.setRowCount(0)
            self.tabla_equipos.setRowCount(0)
            return

        self._set_estado("")
        self._llenar_tabla_pilotos(standings_pilotos)
        self._llenar_tabla_equipos(standings_equipos)

    def _llenar_tabla_pilotos(self, df):
        columnas = ['position', 'driverCode', 'givenName', 'familyName', 'constructorNames', 'points', 'wins']
        etiquetas = ['Pos', 'Cod', 'Nombre', 'Apellido', 'Equipo', 'Pts', 'Victorias']
        columnas_monoespaciadas = {'position', 'points', 'wins'}

        self.tabla_pilotos.setColumnCount(len(columnas))
        self.tabla_pilotos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_pilotos.setRowCount(len(df))

        fuente_datos = QFont("Consolas")
        fuente_datos.setStyleHint(QFont.Monospace)

        for fila, (_, row) in enumerate(df.iterrows()):
            color = self._color_por_posicion(int(row['position']))

            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                if nombre_col == 'constructorNames':
                    texto = " / ".join(valor)  # por si el piloto tuvo más de un equipo
                elif nombre_col in ('position', 'wins'):
                    texto = str(int(valor))
                else:
                    texto = str(valor)

                item = QTableWidgetItem(texto)
                if nombre_col in ('position', 'points'):
                    item.setTextAlignment(Qt.AlignCenter)
                if nombre_col in columnas_monoespaciadas:
                    item.setFont(fuente_datos)
                if color is not None:
                    item.setBackground(color)
                    item.setForeground(QColor("#f5f5f5"))
                self.tabla_pilotos.setItem(fila, col, item)

        self.tabla_pilotos.resizeColumnsToContents()
        for col in (2, 3, 4):
            self.tabla_pilotos.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

    def _llenar_tabla_equipos(self, df):
        columnas = ['position', 'constructorName', 'points', 'wins']
        etiquetas = ['Pos', 'Equipo', 'Pts', 'Victorias']
        columnas_monoespaciadas = {'position', 'points', 'wins'}

        self.tabla_equipos.setColumnCount(len(columnas))
        self.tabla_equipos.setHorizontalHeaderLabels(etiquetas)
        self.tabla_equipos.setRowCount(len(df))

        fuente_datos = QFont("Consolas")
        fuente_datos.setStyleHint(QFont.Monospace)

        for fila, (_, row) in enumerate(df.iterrows()):
            color = self._color_por_posicion(int(row['position']))

            for col, nombre_col in enumerate(columnas):
                valor = row[nombre_col]
                texto = str(int(valor)) if nombre_col in ('position', 'wins') else str(valor)
                item = QTableWidgetItem(texto)
                if nombre_col == 'position':
                    item.setTextAlignment(Qt.AlignCenter)
                if nombre_col in columnas_monoespaciadas:
                    item.setFont(fuente_datos)
                if color is not None:
                    item.setBackground(color)
                    item.setForeground(QColor("#f5f5f5"))
                self.tabla_equipos.setItem(fila, col, item)

        self.tabla_equipos.resizeColumnsToContents()
        self.tabla_equipos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _color_por_posicion(self, posicion):
        if posicion == 1:
            return self.COLOR_PRIMERO
        if posicion == 2:
            return self.COLOR_SEGUNDO
        if posicion == 3:
            return self.COLOR_TERCERO
        return None

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
