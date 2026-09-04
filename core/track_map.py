import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.paths import ruta_cache, data_path

CACHE_DIR_NOMBRE = "cache_tracks"

ALIAS_LOCATION = {
    "Monte Carlo": "Monaco",
    "Kuala Lumpur": "Sakhir",  # error de datos conocido en el calendario 2026 de FastF1 (debería ser Bahrein)
}


def normalizar_location(location):
    return ALIAS_LOCATION.get(location, location)


def _rotar(x, y, angulo_grados):
    angulo = math.radians(angulo_grados)
    x_rot = x * math.cos(angulo) - y * math.sin(angulo)
    y_rot = x * math.sin(angulo) + y * math.cos(angulo)
    return x_rot, y_rot


def generar_mapa_circuito(location, telemetria, circuito_info, ruta_salida):
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

    rotacion = circuito_info.rotation
    x, y = telemetria['X'].to_numpy(), telemetria['Y'].to_numpy()
    x_rot, y_rot = _rotar(x, y, rotacion)

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')

    ax.plot(x_rot, y_rot, color='#e10600', linewidth=3)

    for _, curva in circuito_info.corners.iterrows():
        cx, cy = _rotar(curva['X'], curva['Y'], rotacion)
        ax.scatter(cx, cy, color='#1e1e26', s=180, zorder=5, edgecolors='#e10600', linewidths=1.5)
        ax.text(cx, cy, str(int(curva['Number'])), color='white',
                ha='center', va='center', fontsize=8, fontweight='bold', zorder=6)

    ax.set_aspect('equal')
    ax.axis('off')

    fig.savefig(ruta_salida, transparent=True, bbox_inches='tight', dpi=150)
    plt.close(fig)

    return ruta_salida


def obtener_ruta_mapa(location):
    location_normalizado = normalizar_location(location)
    nombre_archivo = location_normalizado.lower().replace(" ", "_") + ".png"

    ruta, es_escribible = ruta_cache(CACHE_DIR_NOMBRE, nombre_archivo)

    if not es_escribible:
        return ruta  # viene empaquetado, ya sabemos que existe

    return ruta if os.path.exists(ruta) else None


def buscar_referencia(location, year_actual):
    import pandas as pd
    import fastf1

    location_normalizado = normalizar_location(location)

    for year in range(year_actual, year_actual - 6, -1):
        try:
            calendario = fastf1.get_event_schedule(year)
        except Exception:
            continue

        locations_normalizados = calendario['Location'].apply(normalizar_location)
        coincidencias = calendario[locations_normalizados == location_normalizado]
        if coincidencias.empty:
            continue

        hoy = pd.Timestamp.now()
        pasadas = coincidencias[coincidencias['EventDate'] < hoy]
        if not pasadas.empty:
            fila = pasadas.iloc[0]
            return int(fila['RoundNumber']), year

    return None, None


def generar_o_obtener_mapa(location, year_actual):
    """Devuelve la ruta del mapa cacheado (o empaquetado), generándolo
    primero si hace falta. Función síncrona: bloquea mientras genera,
    pensada para scripts o para llamarse desde dentro de un QThread."""
    ruta_existente = obtener_ruta_mapa(location)
    if ruta_existente:
        return ruta_existente

    import fastf1

    gp_referencia, year_referencia = buscar_referencia(location, year_actual)
    if gp_referencia is None:
        return None

    sesion = fastf1.get_session(year_referencia, gp_referencia, 'R')
    sesion.load(telemetry=True, laps=True, weather=False)

    vuelta_rapida = sesion.laps.pick_fastest()
    telemetria = vuelta_rapida.get_telemetry()
    circuito_info = sesion.get_circuit_info()

    location_normalizado = normalizar_location(location)
    nombre_archivo = location_normalizado.lower().replace(" ", "_") + ".png"
    ruta_salida = os.path.join(data_path(CACHE_DIR_NOMBRE), nombre_archivo)

    generar_mapa_circuito(location, telemetria, circuito_info, ruta_salida)
    return ruta_salida