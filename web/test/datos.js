// Datos de prueba compartidos: un comun.json chico, carreras como las de
// Jolpica y un piloto/equipo como los de datos/actual.json.
export const COMUN = {
  anio_actual: 2026,
  eventos: { "Singapore Grand Prix": "Gran Premio de Singapur", "Azerbaijan Grand Prix": "Gran Premio de Azerbaiyán" },
  paises: { Singapore: "Singapur", Azerbaijan: "Azerbaiyán", Malaysia: "Malasia" },
  nacionalidades: { Italian: "Italia", British: "Reino Unido" },
  banderas: { Singapore: "sg", Azerbaijan: "az" },
  colores: { mercedes: "#00D7B6", red_bull: "#4781D7" },
  logos: { mercedes: "https://media.formula1.com/mercedes.png" },
  autos: { mercedes: "https://cdn/mercedes-auto.webp" },
  circuitos: {
    baku: {
      nombre_completo: "Baku City Circuit", circuit_id: "baku", tipo: "Callejero", sentido: "Antihorario",
      longitud_km: 6.003, vueltas: 51, distancia_km: 306.049, curvas: 20,
      record_vuelta: "1:43.009 — Charles Leclerc (2019)", primer_gp: 2016, mapa: true,
    },
  },
};

// Una carrera como las de /{año}.json de Jolpica. `extra` suma las sesiones.
export function carrera(ronda, nombre, pais, circuitId, fecha, hora, extra = {}) {
  return {
    season: fecha.slice(0, 4), round: String(ronda), raceName: nombre, date: fecha,
    ...(hora ? { time: hora } : {}),
    Circuit: { circuitId, circuitName: `${circuitId} circuit`, Location: { country: pais } },
    ...extra,
  };
}

export const SINGAPUR = carrera(17, "Singapore Grand Prix", "Singapore", "marina_bay", "2026-10-11", "12:00:00Z", {
  FirstPractice: { date: "2026-10-09", time: "08:30:00Z" },
  SprintQualifying: { date: "2026-10-09", time: "12:30:00Z" },
  Sprint: { date: "2026-10-10", time: "09:00:00Z" },
  Qualifying: { date: "2026-10-10", time: "13:00:00Z" },
});

export const PILOTO_ANT = {
  driver_id: "antonelli", codigo: "ANT", nombre: "Andrea Kimi", apellido: "Antonelli",
  nacionalidad: "Italian", nacimiento: "2006-08-25",
  url_wiki: "https://en.wikipedia.org/wiki/Andrea_Kimi_Antonelli", headshot_url: null,
  constructor_id: "mercedes", equipo: "Mercedes", equipos: ["Mercedes"], numero: "12",
  posicion: 1, puntos: 320, victorias: 8,
  stats: { victorias: 8, podios: 13, abandonos: 1, prom_llegada: 3.5, prom_largada: 4.25, poles: 6, posicion: 1, puntos: 320 },
  tira: [
    { ronda: 1, gp: "Australian Grand Prix", pais: "Australia", largada: 2, posicion: 2, posicion_texto: "2" },
    { ronda: 2, gp: "Chinese Grand Prix", pais: "China", largada: 1, posicion: null, posicion_texto: "R" },
  ],
  carrera: { victorias: 8, podios: 13, gps: 16, debut: 2026, titulos: 0 },
};

export const EQUIPO_MER = {
  constructor_id: "mercedes", nombre: "Mercedes", posicion: 1, puntos: 556, victorias: 11,
  stats: { victorias: 11, dobletes: 3 },
  cara_a_cara: {
    a: { driver_id: "antonelli", codigo: "ANT", nombre: "Andrea Kimi", apellido: "Antonelli" },
    b: { driver_id: "russell", codigo: "RUS", nombre: "George", apellido: "Russell" },
    clasificacion: [9, 7], carrera: [11, 5], puntos: [320, 236], victorias: [8, 3], podios: [13, 8], poles: [6, 5],
    por_carrera: [
      { ronda: 1, gp: "Australian Grand Prix", pais: "Australia", a: { posicion: 2 }, b: { posicion: 1 }, adelante: 1 },
      { ronda: 2, gp: "Chinese Grand Prix", pais: "China", a: { posicion: 1 }, b: { posicion: null }, adelante: 0 },
    ],
  },
};
