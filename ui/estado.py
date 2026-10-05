"""Etiqueta de estado (cargando / error / vacío) que comparten las vistas."""

_NOMBRES = {"": "estadoVacio", "cargando": "estadoCargando",
            "error": "estadoError", "vacio": "estadoVacio"}


def aplicar_estado(etiqueta, texto, tipo=""):
    """El objectName elige el estilo en style.qss; sin texto, se oculta."""
    etiqueta.setObjectName(_NOMBRES.get(tipo, "estadoVacio"))
    etiqueta.setText(texto)
    etiqueta.setVisible(bool(texto))
    etiqueta.style().unpolish(etiqueta)
    etiqueta.style().polish(etiqueta)
