SESIONES_ES = {
    "Practice 1": "Entrenamiento 1",
    "Practice 2": "Entrenamiento 2",
    "Practice 3": "Entrenamiento 3",
    "Qualifying": "Clasificación",
    "Sprint Qualifying": "Clasificación sprint",
    "Sprint": "Sprint",
    "Race": "Carrera",
}

PAISES_ES = {
    "Australia": "Australia",
    "Bahrain": "Baréin",
    "Saudi Arabia": "Arabia Saudita",
    "United Arab Emirates": "Emiratos Árabes Unidos",
    "Japan": "Japón",
    "China": "China",
    "United States": "Estados Unidos",
    "Canada": "Canadá",
    "Mexico": "México",
    "Brazil": "Brasil",
    "Monaco": "Mónaco",
    "Spain": "España",
    "Austria": "Austria",
    "United Kingdom": "Reino Unido",
    "Great Britain": "Gran Bretaña",
    "UK": "Reino Unido",
    "USA": "Estados Unidos",
    "Belgium": "Bélgica",
    "Netherlands": "Países Bajos",
    "Italy": "Italia",
    "Singapore": "Singapur",
    "Qatar": "Catar",
    "France": "Francia",
    "Hungary": "Hungría",
    "Azerbaijan": "Azerbaiyán",
    "Germany": "Alemania",
    "Portugal": "Portugal",
    "Switzerland": "Suiza",
    "Turkey": "Turquía",
    "Morocco": "Marruecos",
    "Argentina": "Argentina",
    "South Africa": "Sudáfrica",
    "Malaysia": "Malasia",
    "India": "India",
    "Korea": "Corea",
    "Russia": "Rusia",
    "Luxembourg": "Luxemburgo",
    "Abu Dhabi": "Abu Dabi",
    "UAE": "EAU",
    "San Marino": "San Marino",
    "Sweden": "Suecia",
}

EVENTOS_ES = {
    "Australian Grand Prix": "Gran Premio de Australia",
    "Bahrain Grand Prix": "Gran Premio de Baréin",
    "Saudi Arabian Grand Prix": "Gran Premio de Arabia Saudita",
    "Chinese Grand Prix": "Gran Premio de China",
    "Japanese Grand Prix": "Gran Premio de Japón",
    "Miami Grand Prix": "Gran Premio de Miami",
    "United States Grand Prix": "Gran Premio de los Estados Unidos",
    "Canadian Grand Prix": "Gran Premio de Canadá",
    "Mexican Grand Prix": "Gran Premio de México",
    "Brazilian Grand Prix": "Gran Premio de Brasil",
    "Monaco Grand Prix": "Gran Premio de Mónaco",
    "Spanish Grand Prix": "Gran Premio de España",
    "Austrian Grand Prix": "Gran Premio de Austria",
    "British Grand Prix": "Gran Premio de Gran Bretaña",
    "Hungarian Grand Prix": "Gran Premio de Hungría",
    "Belgian Grand Prix": "Gran Premio de Bélgica",
    "Dutch Grand Prix": "Gran Premio de Países Bajos",
    "Italian Grand Prix": "Gran Premio de Italia",
    "Singapore Grand Prix": "Gran Premio de Singapur",
    "Qatar Grand Prix": "Gran Premio de Catar",
    "Abu Dhabi Grand Prix": "Gran Premio de Abu Dabi",
    "French Grand Prix": "Gran Premio de Francia",
    "German Grand Prix": "Gran Premio de Alemania",
    "Azerbaijan Grand Prix": "Gran Premio de Azerbaiyán",
    "Las Vegas Grand Prix": "Gran Premio de Las Vegas",
    "São Paulo Grand Prix": "Gran Premio de São Paulo",
    "Mexico City Grand Prix": "Gran Premio de la Ciudad de México",
    "Barcelona Grand Prix": "Gran Premio de Barcelona",
    "Emilia Romagna Grand Prix": "Gran Premio de Emilia-Romaña",
    "Portuguese Grand Prix": "Gran Premio de Portugal",
    "Styrian Grand Prix": "Gran Premio de Estiria",
    "70th Anniversary Grand Prix": "Gran Premio del 70.º Aniversario",
    "Tuscan Grand Prix": "Gran Premio de la Toscana",
    "Eifel Grand Prix": "Gran Premio de Eifel",
    "Turkish Grand Prix": "Gran Premio de Turquía",
    "Sakhir Grand Prix": "Gran Premio de Sakhir",
    "Russian Grand Prix": "Gran Premio de Rusia",
    "Madrid Grand Prix": "Gran Premio de Madrid",
}


def traducir_sesion(texto):
    if texto is None:
        return ""
    return SESIONES_ES.get(str(texto), str(texto))


def traducir_pais(texto):
    if texto is None:
        return ""
    return PAISES_ES.get(str(texto), str(texto))


def traducir_evento(texto):
    if texto is None:
        return ""
    texto_str = str(texto)
    return EVENTOS_ES.get(texto_str, texto_str)


# Ergast da la nacionalidad como gentilicio en inglés ("British"); la ficha
# muestra el país.
NACIONALIDADES_ES = {
    "American": "Estados Unidos", "American-Italian": "Estados Unidos",
    "Argentine": "Argentina", "Argentine-Italian": "Argentina",
    "Australian": "Australia", "Austrian": "Austria", "Belgian": "Bélgica",
    "Brazilian": "Brasil", "British": "Reino Unido", "Canadian": "Canadá",
    "Chilean": "Chile", "Chinese": "China", "Colombian": "Colombia",
    "Czech": "República Checa", "Danish": "Dinamarca", "Dutch": "Países Bajos",
    "East German": "Alemania Oriental", "Finnish": "Finlandia", "French": "Francia",
    "German": "Alemania", "Hungarian": "Hungría", "Indian": "India",
    "Indonesian": "Indonesia", "Irish": "Irlanda", "Italian": "Italia",
    "Japanese": "Japón", "Liechtensteiner": "Liechtenstein", "Malaysian": "Malasia",
    "Mexican": "México", "Monegasque": "Mónaco", "New Zealander": "Nueva Zelanda",
    "Polish": "Polonia", "Portuguese": "Portugal", "Rhodesian": "Rodesia",
    "Russian": "Rusia", "South African": "Sudáfrica", "Spanish": "España",
    "Swedish": "Suecia", "Swiss": "Suiza", "Thai": "Tailandia",
    "Uruguayan": "Uruguay", "Venezuelan": "Venezuela",
}


def traducir_nacionalidad(texto):
    if texto is None:
        return ""
    return NACIONALIDADES_ES.get(str(texto), str(texto))
