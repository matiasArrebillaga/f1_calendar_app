from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget
)

from core import historial
from core.equipos import color_equipo
from ui.estado import aplicar_estado
from ui.fichas_pilotos import (
    FichaEquipo, FichaPiloto, FotoPiloto, GrillaTarjetas, LogoEquipo, ScrollSinFlechas,
    TarjetaEquipo, TarjetaPiloto
)
from ui.icons import PRIMARIO, icono
from ui.spinner_widget import SpinnerWidget
from workers.pilotos_worker import FotosWorker, PilotosWorker

GRILLA_PILOTOS, FICHA_PILOTO, GRILLA_EQUIPOS, FICHA_EQUIPO = range(4)


class PilotosView(QWidget):
    """Pilotos y equipos de la temporada: grillas de tarjetas y sus fichas.

    Mismo esquema que StandingsView: el año se anota con pedir_anio y se carga
    recién cuando la vista se muestra. Las fichas leen la base local desde el
    hilo de la UI, porque son consultas de milisegundos.
    """
    # "Volver" desde una ficha que se abrió desde otra vista (Clasificación o
    # un GP): MainWindow vuelve a esa vista en vez de a la grilla.
    volver_origen = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("vistaPrincipal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.year = None
        self._year_pedido = None
        self._cache_por_anio = {}   # {year: datos}; los errores no: la red puede volver
        self._datos = None
        self._fotos = {}            # {driver_id: ruta}; la foto no depende del año
        self._logos = {}            # {constructor_id: ruta}
        self._con = None            # conexión de la UI, se abre con la primera ficha
        self._workers_activos = []  # referencias vivas mientras corren
        self._worker_fotos = None
        self._ficha_pendiente = None   # (tipo, id) pedida antes de que lleguen los datos
        self._ficha_externa = False    # la ficha abierta vino de otra vista

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
        self.stack_interno.setObjectName("transparente")
        self.stack_interno.addWidget(self.grilla_pilotos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_piloto))
        self.stack_interno.addWidget(self.grilla_equipos)
        self.stack_interno.addWidget(self._pagina_ficha(self.ficha_equipo))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(12)
        layout.addLayout(encabezado)
        layout.addLayout(fila_estado)
        layout.addWidget(self.stack_interno, 1)

        self.boton_pilotos.clicked.connect(lambda: self._cambiar_tab(GRILLA_PILOTOS))
        self.boton_equipos.clicked.connect(lambda: self._cambiar_tab(GRILLA_EQUIPOS))

    def _pagina_ficha(self, ficha):
        volver = QPushButton("Volver")
        volver.setObjectName("botonVolver")
        volver.setIcon(icono("arrow-left", PRIMARIO, 18))
        volver.setIconSize(QSize(18, 18))
        volver.setCursor(Qt.PointingHandCursor)
        volver.clicked.connect(self.volver_a_grilla)
        atajo = QLabel("Esc")
        atajo.setObjectName("atajoVolver")
        fila_volver = QHBoxLayout()
        fila_volver.setSpacing(10)
        fila_volver.addWidget(volver)
        fila_volver.addWidget(atajo)
        fila_volver.addStretch()
        contenido = QWidget()
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 8, 16)
        columna.setSpacing(14)
        columna.addLayout(fila_volver)
        columna.addWidget(ficha)
        columna.addStretch()
        scroll = ScrollSinFlechas()
        scroll.setWidget(contenido)
        return scroll

    def _cambiar_tab(self, indice):
        self.boton_pilotos.setChecked(indice == GRILLA_PILOTOS)
        self.boton_equipos.setChecked(indice == GRILLA_EQUIPOS)
        self.stack_interno.setCurrentIndex(indice)

    def volver_a_grilla(self):
        """Volver (o Esc) desde una ficha: a su grilla, y si la ficha se abrió
        desde otra vista, además avisa para volver ahí. False si no había ficha."""
        actual = self.stack_interno.currentIndex()
        if actual not in (FICHA_PILOTO, FICHA_EQUIPO):
            return False
        self.stack_interno.setCurrentIndex(
            GRILLA_PILOTOS if actual == FICHA_PILOTO else GRILLA_EQUIPOS)
        if self._ficha_externa:
            self._ficha_externa = False
            self.volver_origen.emit()
        return True

    def abrir_ficha_externa(self, tipo, id_):
        """Ficha pedida desde Clasificación o un GP. Llamar con la vista ya
        mostrada: si los datos del año todavía no llegaron, queda pendiente y la
        abre _mostrar."""
        if self._datos is None:
            self._ficha_pendiente = (tipo, id_)
            return
        self._abrir(tipo, id_)

    def _abrir(self, tipo, id_):
        clave, lista = (("driver_id", "pilotos") if tipo == "piloto"
                        else ("constructor_id", "equipos"))
        if not any(x[clave] == id_ for x in self._datos[lista]):
            return   # no corrió el campeonato de este año: no tiene ficha
        self.boton_pilotos.setChecked(tipo == "piloto")
        self.boton_equipos.setChecked(tipo == "equipo")
        (self.abrir_piloto if tipo == "piloto" else self.abrir_equipo)(id_)
        self._ficha_externa = True

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
        # Mientras baja lo nuevo se muestra lo guardado sin avisar: el aviso
        # quedaba mucho tiempo en pantalla y parecía colgado.
        if datos["pilotos"] or datos.get("actualizando"):
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
        con = self._conexion()
        lider = max((e["puntos"] or 0 for e in datos["equipos"]), default=0)
        for equipo in datos["equipos"]:
            cid = equipo["constructor_id"]
            tarjeta = TarjetaEquipo(
                equipo, color_equipo(cid),
                [p for p in datos["pilotos"] if p["constructor_id"] == cid],
                historial.stats_equipo(con, self.year, cid)["victorias"], lider)
            tarjeta.clicked.connect(self.abrir_equipo)
            for foto in tarjeta.fotos:
                self._poner_foto(foto)
            if cid in self._logos:
                tarjeta.logo.set_logo(self._logos[cid])
            tarjetas.append(tarjeta)
        self.grilla_equipos.set_tarjetas(tarjetas)

        self._pedir_fotos(datos["pilotos"], datos["equipos"])

        if self._ficha_pendiente:
            pendiente, self._ficha_pendiente = self._ficha_pendiente, None
            self._abrir(*pendiente)

    # --- Fotos ---

    def _poner_foto(self, foto):
        ruta = self._fotos.get(foto.driver_id)
        if ruta:
            foto.set_foto(ruta)

    def _pedir_fotos(self, pilotos, equipos):
        if self._worker_fotos is not None:
            self._worker_fotos.requestInterruption()   # las del año anterior ya no hacen falta
            self._worker_fotos = None
        faltan = [p for p in pilotos if p["driver_id"] not in self._fotos]
        faltan_logos = [e for e in equipos if e["constructor_id"] not in self._logos]
        if not faltan and not faltan_logos:
            return
        worker = FotosWorker(faltan, faltan_logos)
        worker.foto_lista.connect(self._on_foto_lista)
        worker.logo_listo.connect(self._on_logo_listo)
        worker.finished.connect(lambda: self._limpiar_worker(worker))
        self._workers_activos.append(worker)
        self._worker_fotos = worker
        worker.start()

    def _on_foto_lista(self, driver_id, ruta):
        self._fotos[driver_id] = ruta
        for foto in self.findChildren(FotoPiloto):
            if foto.driver_id == driver_id:
                foto.set_foto(ruta)

    def _on_logo_listo(self, constructor_id, ruta):
        self._logos[constructor_id] = ruta
        for logo in self.findChildren(LogoEquipo):
            if logo.constructor_id == constructor_id:
                logo.set_logo(ruta)

    # --- Fichas ---

    def _conexion(self):
        if self._con is None:
            self._con = historial.abrir_base()
        return self._con

    def abrir_piloto(self, driver_id):
        self._ficha_externa = False   # desde la grilla; _abrir lo marca si vino de afuera
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
        self._ficha_externa = False
        equipo = next(e for e in self._datos["equipos"] if e["constructor_id"] == constructor_id)
        con = self._conexion()
        self.ficha_equipo.mostrar(equipo, color_equipo(constructor_id), self.year,
                                  historial.cara_a_cara(con, self.year, constructor_id),
                                  historial.stats_equipo(con, self.year, constructor_id))
        self._poner_foto(self.ficha_equipo.foto_a)
        self._poner_foto(self.ficha_equipo.foto_b)
        self.stack_interno.setCurrentIndex(FICHA_EQUIPO)
