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


# ponytail: tabla fija como la de colores. F1 sólo publica en esta ruta los
# logos de los 10 equipos de 2025; los demás (Audi, Cadillac, equipos viejos)
# quedan con las iniciales. Si F1 publica los de 2026, sumar el año a la ruta.
SLUG_LOGO = {
    "mclaren": "mclaren", "mercedes": "mercedes", "red_bull": "red-bull-racing",
    "ferrari": "ferrari", "williams": "williams", "rb": "racing-bulls",
    "aston_martin": "aston-martin", "haas": "haas", "sauber": "kick-sauber",
    "alpine": "alpine",
}
URL_LOGO = ("https://media.formula1.com/content/dam/fom-website/teams/2025/"
            "{}-logo.png.transform/2col/image.png")


def color_equipo(constructor_id):
    return COLORES_EQUIPO.get(constructor_id)


def url_logo(constructor_id):
    slug = SLUG_LOGO.get(constructor_id)
    return URL_LOGO.format(slug) if slug else None
