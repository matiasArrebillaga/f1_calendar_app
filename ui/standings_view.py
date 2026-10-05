from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QFrame,
    QTableWidget, QTableWidgetItem, QLabel, QSizePolicy, QHeaderView
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt

from core.equipos import color_equipo
from ui.delegados import BarraPuntos, MedallaPosicion
from ui.icons import franja_equipo, DATO
from ui.estado import aplicar_estado
from workers.standings_worker import StandingsWorker

PUNTOS_POR_CARRERA = {0: 25, 1: 25 + 18}   # pilotos / equipos (1º + 2º)
PUNTOS_POR_SPRINT = {0: 8, 1: 8 + 7}


def _nombre_piloto(piloto):
    nombre = f"{piloto['nombre']} {piloto['apellido']}"
    # Ergast no tiene siglas antes de los 2000.
    return f"{piloto['codigo']}   {nombre}" if piloto['codigo'] else nombre


class StandingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.year = None
        self._year_pedido = None
        self._cache_por_anio = {}   # {year: datos del worker} | {year: None} si no hay datos
        self._datos = None
        self._workers_activos = []  # referencias vivas mientras corren, evita el crash

        # --- Encabezado: título + selector Pilotos/Equipos ---
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("etiquetaRonda")
        titulo = QLabel("Clasificación")
        titulo.setObjectName("titulo")
        columna_titulo = QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(self.eyebrow)
        columna_titulo.addWidget(titulo)

        self.boton_pilotos = QPushButton("Pilotos")
        self.boton_pilotos.setObjectName("tabHorizontalIzq")
        self.boton_equipos = QPushButton("Equipos")
        self.boton_equipos.setObjectName("tabHorizontalDer")
        for boton in (self.boton_pilotos, self.boton_equipos):
            boton.setCheckable(True)
            boton.setMinimumHeight(34)
            boton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            boton.setCursor(Qt.PointingHandCursor)
        self.boton_pilotos.setChecked(True)
        self.boton_pilotos.setToolTip("Clasificación de pilotos")
        self.boton_equipos.setToolTip("Clasificación de constructores")

        encabezado = QHBoxLayout()
        encabezado.setSpacing(0)   # los dos botones pegados: se leen como un solo control
        encabezado.addLayout(columna_titulo)
        encabezado.addStretch()
        encabezado.addWidget(self.boton_pilotos, alignment=Qt.AlignBottom)
        encabezado.addWidget(self.boton_equipos, alignment=Qt.AlignBottom)

        # --- Indicadores: líder, ventaja, puntos en juego ---
        self._kpis = []
        fila_kpis = QHBoxLayout()
        fila_kpis.setSpacing(10)
        for nombre in ("LÍDER", "VENTAJA", "EN JUEGO"):
            caja = QFrame()
            caja.setObjectName("kpi")
            etiqueta = QLabel(nombre)
            etiqueta.setObjectName("etiquetaRonda")
            valor = QLabel()
            valor.setObjectName("valorKpi")
            detalle = QLabel()
            detalle.setObjectName("detalleKpi")
            layout_caja = QVBoxLayout(caja)
            layout_caja.setContentsMargins(14, 10, 14, 10)
            layout_caja.setSpacing(2)
            layout_caja.addWidget(etiqueta)
            layout_caja.addWidget(valor)
            layout_caja.addWidget(detalle)
            fila_kpis.addWidget(caja, 1)
            self._kpis.append((caja, valor, detalle))

        self.tabla_pilotos = self._crear_tabla()
        self.tabla_equipos = self._crear_tabla()

        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")

        self.stack_interno = QStackedWidget()
        self.stack_interno.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stack_interno.addWidget(self.tabla_pilotos)
        self.stack_interno.addWidget(self.tabla_equipos)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(12)
        layout.addLayout(encabezado)
        layout.addLayout(fila_kpis)
        layout.addWidget(self.estado)
        layout.addWidget(self.stack_interno, 1)
        self.setLayout(layout)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(0))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(1))

    def _crear_tabla(self):
        tabla = QTableWidget()
        tabla.setObjectName("tablaStandings")
        tabla.setAlternatingRowColors(True)
        tabla.setShowGrid(False)   # sólo hairlines horizontales
        tabla.verticalHeader().setVisible(False)
        tabla.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        # Las columnas estiran para llenar el ancho: no hay nada que scrollear
        # en horizontal, y la barra igual aparecía porque la vertical se come
        # unos píxeles.
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Referencias vivas: setItemDelegate no le pasa la propiedad a la tabla.
        tabla._medalla = MedallaPosicion(tabla)
        tabla._barra = BarraPuntos(tabla)
        tabla.setItemDelegateForColumn(0, tabla._medalla)
        return tabla

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == 0)
        self.boton_equipos.setChecked(indice == 1)
        self.stack_interno.setCurrentIndex(indice)
        self._actualizar_kpis()

    def _set_estado(self, texto, tipo=""):
        aplicar_estado(self.estado, texto, tipo)

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
        self.eyebrow.setText(f"TEMPORADA {year}")

        if year in self._cache_por_anio:
            cacheado = self._cache_por_anio[year]
            if cacheado is None:
                self._mostrar_sin_datos(year)
            else:
                self._mostrar(cacheado)
            return

        self._set_estado(f"Cargando clasificación {year}...", "cargando")
        self._datos = None
        self._actualizar_kpis()
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

    def on_standings_cargados(self, datos):
        worker = self.sender()
        self._cache_por_anio[worker.year] = datos
        if worker.year != self.year:
            return  # llegó tarde: el usuario ya cambió de año, ignoramos este resultado

        self._mostrar(datos)

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
        self._datos = None
        self._actualizar_kpis()
        self.tabla_pilotos.setRowCount(0)
        self.tabla_equipos.setRowCount(0)

    def _mostrar(self, datos):
        self._datos = datos
        # Mientras baja lo nuevo se muestra lo guardado sin avisar: el aviso
        # quedaba mucho tiempo en pantalla y parecía colgado.
        self._set_estado("")
        if datos['ronda']:
            self.eyebrow.setText(f"TEMPORADA {self.year}   ·   TRAS R{datos['ronda']}")
        pilotos = [
            (_nombre_piloto(p),
             " / ".join(p['equipos']), color_equipo(p['constructor_id']),
             int(p['puntos'] or 0), int(p['victorias'] or 0))
            for p in datos['pilotos']
        ]
        equipos = [
            (e['nombre'], None, color_equipo(e['constructor_id']),
             int(e['puntos'] or 0), int(e['victorias'] or 0))
            for e in datos['equipos']
        ]
        self._llenar_tabla(self.tabla_pilotos, pilotos, ['Pos', 'Piloto', 'Equipo'])
        self._llenar_tabla(self.tabla_equipos, equipos, ['Pos', 'Equipo'])
        self._actualizar_kpis()

    def _llenar_tabla(self, tabla, filas, etiquetas_nombre):
        """`filas`: [(nombre, equipo | None, color | None, puntos, victorias)],
        ya en orden de posición."""
        con_equipo = len(etiquetas_nombre) == 3
        etiquetas = etiquetas_nombre + ['Puntos', 'Dif.', 'Vict.']
        col_puntos = len(etiquetas_nombre)
        tabla.setColumnCount(len(etiquetas))
        tabla.setHorizontalHeaderLabels(etiquetas)
        # Cada título alineado como su columna: Pos al centro, nombres a la
        # izquierda, números a la derecha.
        for col in range(len(etiquetas)):
            tabla.horizontalHeaderItem(col).setTextAlignment(
                Qt.AlignCenter if col == 0
                else (Qt.AlignRight if col >= col_puntos else Qt.AlignLeft) | Qt.AlignVCenter)
        tabla.setRowCount(len(filas))
        tabla.setItemDelegateForColumn(col_puntos, tabla._barra)

        fuente_datos = QFont("Consolas")
        fuente_datos.setStyleHint(QFont.Monospace)
        puntos_lider = max(filas[0][3], 1) if filas else 1

        for fila, (nombre, equipo, color, puntos, victorias) in enumerate(filas):
            celdas = [str(fila + 1), nombre]
            if con_equipo:
                celdas.append(equipo)
            celdas += [str(puntos), "—" if fila == 0 else f"−{filas[0][3] - puntos}", str(victorias)]

            for col, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                item.setToolTip(texto)
                if col == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setData(Qt.UserRole, fila + 1)   # medalla del podio
                elif col >= col_puntos:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setFont(fuente_datos)
                if col == col_puntos:
                    item.setData(Qt.UserRole, puntos / puntos_lider)
                if col == col_puntos + 1 and fila > 0:
                    item.setForeground(QColor(DATO))
                # La franja va en la columna del equipo (o del nombre, en la
                # tabla de equipos).
                if col == len(etiquetas_nombre) - 1:
                    franja = franja_equipo(color)
                    if franja is not None:
                        item.setIcon(franja)
                tabla.setItem(fila, col, item)

        cabecera = tabla.horizontalHeader()
        cabecera.setSectionResizeMode(QHeaderView.Stretch)
        for col, ancho in ((0, 60), (len(etiquetas) - 2, 90), (len(etiquetas) - 1, 80)):
            cabecera.setSectionResizeMode(col, QHeaderView.Fixed)
            tabla.setColumnWidth(col, ancho)

    def _actualizar_kpis(self):
        datos = self._datos
        for caja, _, _ in self._kpis:
            caja.setVisible(datos is not None)
        if datos is None:
            return

        es_equipos = self.stack_interno.currentIndex() == 1
        filas = datos['equipos'] if es_equipos else datos['pilotos']
        if not filas:
            return

        def nombre(fila):
            return fila['nombre'] if es_equipos else f"{fila['nombre']} {fila['apellido']}"

        lider = filas[0]
        (_, valor_lider, detalle_lider), (_, valor_ventaja, detalle_ventaja), \
            (_, valor_juego, detalle_juego) = self._kpis
        valor_lider.setText(nombre(lider))
        detalle_lider.setText(f"{int(lider['puntos'] or 0)} puntos")

        if len(filas) > 1:
            segundo = filas[1]
            ventaja = int((lider['puntos'] or 0) - (segundo['puntos'] or 0))
            valor_ventaja.setText(f"<span style='color:{DATO};'>+{ventaja}</span>")
            detalle_ventaja.setText(f"sobre {nombre(segundo)}")
        else:
            valor_ventaja.setText("—")
            detalle_ventaja.setText("")

        if datos['ronda'] is None or datos['total_rondas'] is None:
            valor_juego.setText("—")
            detalle_juego.setText("sin datos del calendario")
        elif datos['total_rondas'] - datos['ronda'] <= 0:
            valor_juego.setText("—")
            detalle_juego.setText("Temporada terminada")
        else:
            restantes = datos['total_rondas'] - datos['ronda']
            sprints = datos.get('sprints_restantes', 0)
            puntos = (restantes * PUNTOS_POR_CARRERA[int(es_equipos)]
                      + sprints * PUNTOS_POR_SPRINT[int(es_equipos)])
            valor_juego.setText(f"<span style='color:{DATO};'>{puntos}</span> pts")
            texto = f"{restantes} {'carrera' if restantes == 1 else 'carreras'}"
            if sprints:
                texto += f" y {sprints} {'sprint' if sprints == 1 else 'sprints'}"
            plural = restantes > 1 or sprints > 0
            detalle_juego.setText(f"{texto} {'restantes' if plural else 'restante'}")
