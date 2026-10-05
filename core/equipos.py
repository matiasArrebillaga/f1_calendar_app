# Color de cada equipo para la clasificación, por constructorId de Ergast (es
# estable entre temporadas; el nombre cambia con cada sponsor). En los
# resultados de una sesión no hace falta: fastf1 ya trae TeamColor.
#
# ponytail: tabla fija, se desactualiza con cada cambio de equipos o de
# colores. Los que no están (equipos viejos) quedan sin franja. Si molesta,
# sacar el color de session.results de la última carrera del año (TeamId de
# fastf1 == constructorId de Ergast).
COLORES_EQUIPO = {   # los de fastf1 (session.results.TeamColor) para 2026
    "mclaren": "#F47600",
    "ferrari": "#ED1131",
    "red_bull": "#4781D7",
    "mercedes": "#00D7B6",
    "aston_martin": "#229971",
    "alpine": "#00A1E8",
    "williams": "#1868DB",
    "rb": "#6C98FF",
    "haas": "#9C9FA2",
    "audi": "#F50537",
    "cadillac": "#909090",
    "sauber": "#52E252",
}


def color_equipo(constructor_id):
    return COLORES_EQUIPO.get(constructor_id)
