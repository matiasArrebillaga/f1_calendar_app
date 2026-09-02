from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor


class SpinnerWidget(QWidget):
    def __init__(self, tamano=24, grosor=3):
        super().__init__()
        self.tamano = tamano
        self.grosor = grosor
        self.angulo = 0

        self.setFixedSize(tamano, tamano)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._avanzar)
        self.timer.setInterval(30)  # ~33 cuadros por segundo

    def _avanzar(self):
        self.angulo = (self.angulo + 15) % 360
        self.update()  # pide a Qt que vuelva a dibujar este widget

    def iniciar(self):
        self.show()
        self.timer.start()

    def detener(self):
        self.timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor("#e10600"))
        pen.setWidth(self.grosor)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        margen = self.grosor
        rect = self.rect().adjusted(margen, margen, -margen, -margen)

        painter.drawArc(rect, self.angulo * 16, 270 * 16)