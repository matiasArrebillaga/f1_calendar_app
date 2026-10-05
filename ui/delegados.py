from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtCore import Qt, QRect, QRectF

from ui.icons import BORDE, DATO, PODIO


class MedallaPosicion(QStyledItemDelegate):
    """Columna Pos: el 1º, 2º y 3º van como una medalla metálica (chip con
    degradé y el número oscuro); el resto, texto normal. La posición viaja en
    Qt.UserRole.

    Va pintada a mano y no con item.setBackground(): con cualquier regla
    QTableWidget::item en el .qss, Qt ignora el BackgroundRole del item.
    """
    ANCHO, ALTO, RADIO = 26, 20, 4

    def paint(self, pintor, opcion, indice):
        posicion = indice.data(Qt.UserRole)
        if posicion not in (1, 2, 3):
            super().paint(pintor, opcion, indice)
            return

        # El fondo de la celda (hover / selección / fila alterna) sin el texto:
        # el número lo dibuja la medalla.
        celda = QStyleOptionViewItem(opcion)
        self.initStyleOption(celda, indice)
        celda.text = ""
        celda.widget.style().drawControl(QStyle.CE_ItemViewItem, celda, pintor, celda.widget)

        arriba, abajo, texto = PODIO[posicion - 1]
        chip = QRectF(0, 0, self.ANCHO, self.ALTO)
        chip.moveCenter(QRectF(opcion.rect).center())
        degrade = QLinearGradient(chip.topLeft(), chip.bottomLeft())
        degrade.setColorAt(0, QColor(arriba))
        degrade.setColorAt(1, QColor(abajo))

        pintor.save()
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(degrade)
        pintor.drawRoundedRect(chip, self.RADIO, self.RADIO)
        fuente = opcion.font
        fuente.setBold(True)
        pintor.setFont(fuente)
        pintor.setPen(QColor(texto))
        pintor.drawText(chip, Qt.AlignCenter, str(posicion))
        pintor.restore()


class BarraPuntos(QStyledItemDelegate):
    """Celda de puntos: barra relativa al líder a la izquierda, número a la
    derecha. La fracción viaja en Qt.UserRole."""
    ANCHO_NUMERO = 56

    def paint(self, pintor, opcion, indice):
        super().paint(pintor, opcion, indice)
        fraccion = indice.data(Qt.UserRole)
        area = opcion.rect.adjusted(12, 0, -self.ANCHO_NUMERO, 0)
        if fraccion is None or area.width() <= 0:
            return
        y = area.center().y() - 2
        pintor.fillRect(QRect(area.left(), y, area.width(), 4), QColor(BORDE))
        pintor.fillRect(QRect(area.left(), y, round(area.width() * fraccion), 4), QColor(DATO))
