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
    "Belgium": "Bélgica",
    "Netherlands": "Países Bajos",
    "Italy": "Italia",
    "Singapore": "Singapur",
    "Japan": "Japón",
    "Qatar": "Catar",
    "United States": "Estados Unidos",
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
    "Mexico": "México",
    "Saudi Arabia": "Arabia Saudita",
    "Bahrain": "Baréin",
    "Belgium": "Bélgica",
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
    "Japanese Grand Prix": "Gran Premio de Japón",
    "Qatar Grand Prix": "Gran Premio de Catar",
    "Abu Dhabi Grand Prix": "Gran Premio de Abu Dabi",
    "French Grand Prix": "Gran Premio de Francia",
    "German Grand Prix": "Gran Premio de Alemania",
    "Azerbaijan Grand Prix": "Gran Premio de Azerbaiyán",
    "Las Vegas Grand Prix": "Gran Premio de Las Vegas",
    "São Paulo Grand Prix": "Gran Premio de São Paulo",
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
