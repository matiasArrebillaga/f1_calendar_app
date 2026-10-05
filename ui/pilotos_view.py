from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget
)

from core import historial
from core.equipos import color_equipo
from ui.estado import aplicar_estado
from ui.fichas_pilotos import (
    FichaEquipo, FichaPiloto, FotoPiloto, GrillaTarjetas, TarjetaEquipo, TarjetaPiloto
)
from ui.spinner_widget import SpinnerWidget
from workers.pilotos_worker import FotosWorker, PilotosWorker

GRILLA_PILOTOS, FICHA_PILOTO, GRILLA_EQUIPOS, FICHA_EQUIPO = range(4)


class PilotosView(QWidget):
    """Pilotos y equipos de la temporada: grillas de tarjetas y sus fichas.

    Mismo esquema que StandingsView: el año se anota con pedir_anio y se carga
    recién cuando la vista se muestra. Las fichas leen la base local desde el
    hilo de la UI, porque son consultas de milisegundos.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.year = None
        self._year_pedido = None
        self._cache_por_anio = {}   # {year: datos}; los errores no: la red puede volver
        self._datos = None
        self._fotos = {}            # {driver_id: ruta}; la foto no depende del año
        self._con = None            # conexión de la UI, se abre con la primera ficha
        self._workers_activos = []  # referencias vivas mientras corren
        self._worker_fotos = None

        # --- Encabezado: título + solapas Pilotos/Equipos ---
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("etiquetaRonda")
        titulo = QLabel("Pilotos")
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

        encabezado = QHBoxLayout()
        encabezado.setSpacing(0)
        encabezado.addLayout(columna_titulo)
        encabezado.addStretch()
        encabezado.addWidget(self.boton_pilotos, alignment=Qt.AlignBottom)
        encabezado.addWidget(self.boton_equipos, alignment=Qt.AlignBottom)

        self.spinner = SpinnerWidget(tamano=18)
        self.spinner.hide()
        self.estado = QLabel()
        self.estado.setObjectName("estadoVacio")
        fila_estado = QHBoxLayout()
        fila_estado.setContentsMargins(0, 0, 0, 0)
        fila_estado.addWidget(self.spinner)
        fila_estado.addWidget(self.estado)
        fila_estado.addStretch()

        self.grilla_pilotos = GrillaTarjetas()
        self.grilla_equipos = GrillaTarjetas()
        self.ficha_piloto = FichaPiloto()
        self.ficha_equipo = FichaEquipo()
        self.stack_interno = QStackedWidget()
        self.stack_interno.addWidget(self.grilla_pilotos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_piloto, "Pilotos", GRILLA_PILOTOS))
        self.stack_interno.addWidget(self.grilla_equipos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_equipo, "Equipos", GRILLA_EQUIPOS))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(12)
        layout.addLayout(encabezado)
        layout.addLayout(fila_estado)
        layout.addWidget(self.stack_interno, 1)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(GRILLA_PILOTOS))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(GRILLA_EQUIPOS))

    def _pagina_ficha(self, ficha, volver_a, indice_grilla):
        miga = QPushButton(f"← {volver_a}")
        miga.setObjectName("migaVolver")
        miga.setCursor(Qt.PointingHandCursor)
        miga.clicked.connect(lambda: self.stack_interno.setCurrentIndex(indice_grilla))
        contenido = QWidget()
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 8, 16)
        columna.setSpacing(12)
        columna.addWidget(miga, alignment=Qt.AlignLeft)
        columna.addWidget(ficha)
        columna.addStretch()
        scroll = QScrollArea()
        scroll.setWidget(contenido)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == GRILLA_PILOTOS)
        self.boton_equipos.setChecked(indice == GRILLA_EQUIPOS)
        self.stack_interno.setCurrentIndex(indice)

    def volver_a_grilla(self):
        """Esc desde una ficha vuelve a su grilla. False si ya estaba en una."""
        actual = self.stack_interno.currentIndex()
        if actual == FICHA_PILOTO:
            self.stack_interno.setCurrentIndex(GRILLA_PILOTOS)
            return True
        if actual == FICHA_EQUIPO:
            self.stack_interno.setCurrentIndex(GRILLA_EQUIPOS)
            return True
        return False

    def _set_estado(self, texto, tipo=""):
        aplicar_estado(self.estado, texto, tipo)
        if tipo == "cargando":
            self.spinner.iniciar()
        else:
            self.spinner.detener()

    # --- Carga por año ---

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
        self._cambiar_tab(GRILLA_EQUIPOS if self.boton_equipos.isChecked() else GRILLA_PILOTOS)

        if year in self._cache_por_anio:
            self._mostrar(self._cache_por_anio[year])
            return

        self._set_estado(f"Cargando pilotos {year}...", "cargando")
        self._datos = None
        self.grilla_pilotos.set_tarjetas([])
        self.grilla_equipos.set_tarjetas([])

        worker = PilotosWorker(year)
        worker.terminado.connect(self.on_datos_cargados)
        worker.error.connect(self.on_error)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        worker.start()

    def _limpiar_worker(self, worker):
        if worker in self._workers_activos:
            self._workers_activos.remove(worker)

    def on_datos_cargados(self, datos):
        worker = self.sender()
        self._cache_por_anio[worker.year] = datos
        if worker.year != self.year:
            return   # llegó tarde: el usuario ya cambió de año
        self._mostrar(datos)

    def on_error(self, mensaje):
        worker = self.sender()
        if worker.year != self.year:
            return
        self._set_estado(f"No se pudieron cargar los pilotos de {self.year}. "
                         "Revisá la conexión y volvé a abrir la pestaña.", "error")
        self.year = None   # así showEvent lo vuelve a pedir

    def _mostrar(self, datos):
        self._datos = datos
        if datos["pilotos"]:
            self._set_estado("")
        else:
            self._set_estado(f"Todavía no hay resultados de {self.year}.", "vacio")

        tarjetas = []
        for piloto in datos["pilotos"]:
            tarjeta = TarjetaPiloto(piloto, color_equipo(piloto["constructor_id"]))
            tarjeta.clicked.connect(self.abrir_piloto)
            self._poner_foto(tarjeta.foto)
            tarjetas.append(tarjeta)
        self.grilla_pilotos.set_tarjetas(tarjetas)

        tarjetas = []
        for equipo in datos["equipos"]:
            tarjeta = TarjetaEquipo(equipo, color_equipo(equipo["constructor_id"]))
            tarjeta.clicked.connect(self.abrir_equipo)
            tarjetas.append(tarjeta)
        self.grilla_equipos.set_tarjetas(tarjetas)

        self._pedir_fotos(datos["pilotos"])

    # --- Fotos ---

    def _poner_foto(self, foto):
        ruta = self._fotos.get(foto.driver_id)
        if ruta:
            foto.set_foto(ruta)

    def _pedir_fotos(self, pilotos):
        if self._worker_fotos is not None:
            self._worker_fotos.requestInterruption()   # las del año anterior ya no hacen falta
            self._worker_fotos = None
        faltan = [p for p in pilotos if p["driver_id"] not in self._fotos]
        if not faltan:
            return
        worker = FotosWorker(faltan)
        worker.foto_lista.connect(self._on_foto_lista)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        self._worker_fotos = worker
        worker.start()

    def _on_foto_lista(self, driver_id, ruta):
        self._fotos[driver_id] = ruta
        for foto in self.findChildren(FotoPiloto):
            if foto.driver_id == driver_id:
                foto.set_foto(ruta)

    # --- Fichas ---

    def _conexion(self):
        if self._con is None:
            self._con = historial.abrir_base()
        return self._con

    def abrir_piloto(self, driver_id):
        piloto = next(p for p in self._datos["pilotos"] if p["driver_id"] == driver_id)
        con = self._conexion()
        self.ficha_piloto.mostrar(
            piloto, color_equipo(piloto["constructor_id"]), self.year,
            historial.stats_temporada(con, self.year, driver_id),
            historial.tira_resultados(con, self.year, driver_id),
            historial.carrera_completa(con, driver_id))
        self._poner_foto(self.ficha_piloto.foto)
        self.stack_interno.setCurrentIndex(FICHA_PILOTO)

    def abrir_equipo(self, constructor_id):
        equipo = next(e for e in self._datos["equipos"] if e["constructor_id"] == constructor_id)
        duelo = historial.cara_a_cara(self._conexion(), self.year, constructor_id)
        self.ficha_equipo.mostrar(equipo, color_equipo(constructor_id), self.year, duelo)
        self._poner_foto(self.ficha_equipo.foto_a)
        self._poner_foto(self.ficha_equipo.foto_b)
        self.stack_interno.setCurrentIndex(FICHA_EQUIPO)
