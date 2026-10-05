from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.historial import mas_victorias
from ui.estado import aplicar_estado
from ui.icons import MUTED, PRIMARIO
from workers.ganadores_worker import GanadoresWorker


def filas_ficha(datos, completa=False):
    """(etiqueta, valor) de la ficha del circuito. La completa suma los datos
    que sólo entran en la vista ampliada."""
    if not datos:
        return []
    filas = [
        ("Longitud", f"{datos['longitud_km']} km"),
        ("Vueltas", datos['vueltas']),
        ("Distancia total", f"{datos['distancia_km']} km"),
        ("Curvas", datos['curvas']),
        ("Récord de vuelta", datos['record_vuelta']),
        ("Primer GP", datos['primer_gp']),
    ]
    if completa:
        filas += [("Tipo", datos['tipo']), ("Sentido de giro", datos['sentido'])]
    return filas


def ficha_html(nombre, filas, oficial=None, grande=False):
    tamano_nombre, tamano_texto, tamano_oficial = (21, 15, 13) if grande else (16, 14, 12)
    html = (f"<div style='font-size:{tamano_nombre}px; font-weight:600; color:{PRIMARIO}; "
            f"margin-bottom:8px;'>{nombre}</div>")
    if filas:
        html += (f"<table width='100%' cellspacing='0' cellpadding='{6 if grande else 3}' "
                 f"style='font-size:{tamano_texto}px;'>") + "".join(
            f"<tr><td style='color:{MUTED};'>{etiqueta}</td>"
            f"<td align='right' style='color:{PRIMARIO}; font-weight:600;'>{valor}</td></tr>"
            for etiqueta, valor in filas
        ) + "</table>"
    if oficial:
        html += (f"<div style='color:{MUTED}; font-size:{tamano_oficial}px; "
                 f"margin-top:10px;'>{oficial}</div>")
    return html


class PanelDatosCircuito(QWidget):
    """Lo que muestra "Más datos del circuito": la ficha completa a la
    izquierda y los ganadores de cada GP corrido ahí a la derecha."""

    def __init__(self, nombre, datos, oficial, workers_activos):
        super().__init__()
        self.setObjectName("panelDatos")
        self.setAttribute(Qt.WA_StyledBackground, True)

        ficha = QLabel(ficha_html(nombre, filas_ficha(datos, completa=True), oficial, grande=True))
        ficha.setWordWrap(True)
        ficha.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        ficha.setFixedWidth(380)

        titulo = QLabel("GANADORES EN ESTE CIRCUITO")
        titulo.setObjectName("subtitulo")
        self.resumen = QLabel()
        self.resumen.setObjectName("detalleKpi")
        self.estado = QLabel()
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Año", "Piloto", "Equipo"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecera.setSectionResizeMode(QHeaderView.Stretch)
        cabecera.setSectionResizeMode(0, QHeaderView.Fixed)
        self.tabla.setColumnWidth(0, 70)
        self.tabla.hide()

        derecha = QVBoxLayout()
        derecha.setSpacing(6)
        derecha.addWidget(titulo)
        derecha.addWidget(self.resumen)
        derecha.addWidget(self.estado)
        derecha.addWidget(self.tabla, 1)
        derecha.addStretch()   # mientras la tabla está oculta, todo queda arriba

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(28)
        layout.addWidget(ficha)
        layout.addLayout(derecha, 1)

        circuit_id = (datos or {}).get('circuit_id')
        if circuit_id is None:
            aplicar_estado(self.estado, "No hay ganadores registrados para este circuito.", "vacio")
            return
        aplicar_estado(self.estado, "Cargando ganadores…", "cargando")
        worker = GanadoresWorker(circuit_id)
        worker.terminado.connect(self._mostrar)
        worker.error.connect(self._error)
        # La vista de detalle los espera al cerrar la app (ver MainWindow.closeEvent).
        workers_activos.append(worker)
        worker.finished.connect(lambda: workers_activos.remove(worker))
        worker.start()

    def _mostrar(self, ganadores):
        if not ganadores:
            aplicar_estado(self.estado, "Todavía no se corrió ningún GP en este circuito.", "vacio")
            return
        aplicar_estado(self.estado, "")
        piloto, victorias = mas_victorias(ganadores)
        self.resumen.setText(f"{len(ganadores)} carreras   ·   Más victorias: "
                             f"{piloto} ({victorias})")
        fuente_anio = QFont("Consolas")
        self.tabla.setRowCount(len(ganadores))
        for fila, g in enumerate(ganadores):
            anio = QTableWidgetItem(str(g['anio']))
            anio.setFont(fuente_anio)
            anio.setToolTip(g['gp'])
            self.tabla.setItem(fila, 0, anio)
            self.tabla.setItem(fila, 1, QTableWidgetItem(g['piloto']))
            self.tabla.setItem(fila, 2, QTableWidgetItem(g['equipo']))
        self.tabla.show()

    def _error(self, mensaje):
        aplicar_estado(self.estado, "No se pudieron cargar los ganadores. Revisá la conexión "
                                    "y volvé a abrir los datos.", "error")
