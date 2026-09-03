import os
import math
import matplotlib
matplotlib.use('Agg')  # backend sin ventana, para generar imágenes desde un hilo secundario
import matplotlib.pyplot as plt
import numpy as np

CACHE_DIR = "cache_tracks"


def _rotar(x, y, angulo_grados):
    angulo = math.radians(angulo_grados)
    x_rot = x * math.cos(angulo) - y * math.sin(angulo)
    y_rot = x * math.sin(angulo) + y * math.cos(angulo)
    return x_rot, y_rot


def generar_mapa_circuito(location, telemetria, circuito_info, ruta_salida):
    """Genera un PNG del trazado con los números de curva, en los colores del tema."""
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

    rotacion = circuito_info.rotation
    x, y = telemetria['X'].to_numpy(), telemetria['Y'].to_numpy()
    x_rot, y_rot = _rotar(x, y, rotacion)

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_alpha(0)   # fondo de la figura transparente
    ax.set_facecolor('none')  # fondo del área de dibujo transparente

    ax.plot(x_rot, y_rot, color='#e10600', linewidth=3)

    for _, curva in circuito_info.corners.iterrows():
        cx, cy = _rotar(curva['X'], curva['Y'], rotacion)
        ax.scatter(cx, cy, color='#1e1e26', s=280, zorder=5, edgecolors='#e10600', linewidths=1.5)
        ax.text(cx, cy, str(int(curva['Number'])), color='white',
                ha='center', va='center', fontsize=9, fontweight='bold', zorder=6)

    ax.set_aspect('equal')
    ax.axis('off')

    fig.savefig(ruta_salida, transparent=True, bbox_inches='tight', dpi=150)
    plt.close(fig)

    return ruta_salida


def obtener_ruta_mapa(location):
    """Devuelve la ruta al mapa cacheado si ya existe, o None si falta generarlo."""
    nombre_archivo = location.lower().replace(" ", "_") + ".png"
    ruta_local = os.path.join(CACHE_DIR, nombre_archivo)
    return ruta_local if os.path.exists(ruta_local) else None