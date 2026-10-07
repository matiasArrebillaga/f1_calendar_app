// Funciones puras (sin DOM ni red): fechas, tiempos, cuentas y rutas.
// Se testean con `node --test "web/test/*.test.js"`.

export const MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
  "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"];
const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
export const ANIO_MIN = 1950;
// Sigue siendo "la próxima" un rato después de largar (calendar_view.py).
const DURACION_CARRERA_MS = 2 * 3600 * 1000;
const PUNTOS_CARRERA = { pilotos: 25, equipos: 25 + 18 };   // standings_view.py
const PUNTOS_SPRINT = { pilotos: 8, equipos: 8 + 7 };

// Sesiones de un fin de semana con la clave que usa Jolpica en el calendario.
// `jolpica`: el recurso que trae sus resultados. `openf1`: el nombre de la
// sesión en OpenF1, que sólo tiene datos desde 2023.
export const SESIONES = [
  { clave: "FirstPractice", nombre: "Entrenamiento 1", corto: "EL1", openf1: "Practice 1" },
  { clave: "SecondPractice", nombre: "Entrenamiento 2", corto: "EL2", openf1: "Practice 2" },
  { clave: "ThirdPractice", nombre: "Entrenamiento 3", corto: "EL3", openf1: "Practice 3" },
  // En 2023 Jolpica la llamaba SprintShootout; OpenF1 usa el mismo nombre siempre.
  { clave: "SprintShootout", nombre: "Clasificación sprint", corto: "Clasif. sprint", openf1: "Sprint Qualifying" },
  { clave: "SprintQualifying", nombre: "Clasificación sprint", corto: "Clasif. sprint", openf1: "Sprint Qualifying" },
  { clave: "Sprint", nombre: "Sprint", corto: "Sprint", jolpica: "sprint" },
  { clave: "Qualifying", nombre: "Clasificación", corto: "Clasif.", jolpica: "qualifying" },
  { clave: "Race", nombre: "Carrera", corto: "Carrera", jolpica: "results" },
];

export const dosDigitos = (n) => String(n).padStart(2, "0");
const mesCorto = (d) => MESES[d.getMonth()].slice(0, 3);

// Jolpica da fecha y hora en UTC. Sin hora publicada (antes de 2005), el día
// a las 00:00 locales.
export const fechaSesion = (s) => new Date(s.time ? `${s.date}T${s.time}` : `${s.date}T00:00`);

export const diaHora = (d) => `${DIAS[d.getDay()]} ${dosDigitos(d.getHours())}:${dosDigitos(d.getMinutes())}`;

export function rangoFechas(inicio, fin) {
  if (inicio.toDateString() === fin.toDateString()) return `${fin.getDate()} ${mesCorto(fin)}`;
  if (inicio.getMonth() === fin.getMonth()) return `${inicio.getDate()} – ${fin.getDate()} ${mesCorto(fin)}`;
  return `${inicio.getDate()} ${mesCorto(inicio)} – ${fin.getDate()} ${mesCorto(fin)}`;
}

export function aEvento(race, comun) {
  const largada = fechaSesion(race);
  const sesiones = SESIONES.filter((s) => s.clave === "Race" || race[s.clave])
    .map((s) => {
      const datos = s.clave === "Race" ? race : race[s.clave];
      return { ...s, dia: datos.date, fecha: fechaSesion(datos) };
    })
    .sort((a, b) => a.fecha - b.fecha);
  const lugar = race.Circuit.Location;
  return {
    anio: Number(race.season),
    ronda: Number(race.round),
    nombre: comun.eventos[race.raceName] ?? race.raceName,
    pais: comun.paises[lugar.country] ?? lugar.country,
    bandera: comun.banderas[lugar.country] ?? null,
    circuitId: race.Circuit.circuitId,
    circuito: race.Circuit.circuitName,
    largada,
    sesiones,
    rango: rangoFechas(sesiones[0].fecha, largada),
    conSprint: Boolean(race.Sprint),
  };
}

export function indiceProxima(eventos, ahora) {
  return eventos.findIndex((ev) => ev.largada.getTime() + DURACION_CARRERA_MS > ahora);
}

export function cuentaRegresiva(largada, ahora) {
  const s = Math.max(0, Math.floor((largada - ahora) / 1000));
  return {
    enCurso: s === 0,
    dias: Math.floor(s / 86400),
    horas: dosDigitos(Math.floor((s % 86400) / 3600)),
    minutos: dosDigitos(Math.floor((s % 3600) / 60)),
  };
}

// Duración típica de cada sesión, para el estado "en vivo": no hay datos en
// vivo gratis dentro de la sesión, así que se calcula con el horario.
const DURACION_MIN = {
  FirstPractice: 60, SecondPractice: 60, ThirdPractice: 60,
  SprintShootout: 45, SprintQualifying: 45, Sprint: 45, Qualifying: 60, Race: 120,
};

export function estadoSesiones(sesiones, ahora) {
  return sesiones.map((s) => {
    const inicio = s.fecha.getTime();
    const duracion = DURACION_MIN[s.clave] * 60_000;
    const estado = ahora >= inicio + duracion ? "hecha" : ahora >= inicio ? "vivo" : "proxima";
    const vivo = estado === "vivo";
    return {
      ...s, estado,
      avance: vivo ? (ahora - inicio) / duracion : null,
      minutos: vivo ? Math.floor((ahora - inicio) / 60_000) : null,
    };
  });
}

export const hayEnVivo = (eventos, ahora) =>
  eventos.some((ev) => estadoSesiones(ev.sesiones, ahora).some((s) => s.estado === "vivo"));

// Avisos (avisos/enviar.mjs): la primera sesión que arranca en los próximos
// 35 min y no es la última avisada. Con el workflow cada 10 min (que GitHub
// atrasa a veces), llega entre ~15 y 35 min antes, una sola vez.
const VENTANA_AVISO_MS = 35 * 60_000;
export const idSesion = (ev, s) => `${ev.anio}-${ev.ronda}-${s.clave}`;

export function sesionAAvisar(eventos, ahora, ultimaAvisada) {
  for (const ev of eventos) {
    for (const s of ev.sesiones) {
      const falta = s.fecha.getTime() - ahora;
      const id = idSesion(ev, s);
      if (falta > 0 && falta <= VENTANA_AVISO_MS && id !== ultimaAvisada) {
        return { ev, sesion: s, minutos: Math.round(falta / 60_000), id };
      }
    }
  }
  return null;
}

// "Gran Premio de Azerbaiyán" → "Azerbaiyán"; los que no tienen traducción
// vienen en inglés ("United States Grand Prix" → "United States").
export const gpCorto = (nombre) => nombre.replace(/^Gran Premio de (la |los )?/, "").replace(/ Grand Prix$/, "");

export function formatoVuelta(seg) {
  const minutos = Math.floor(seg / 60);
  return minutos ? `${minutos}:${(seg - minutos * 60).toFixed(3).padStart(6, "0")}` : seg.toFixed(3);
}

export const formatoDiferencia = (seg) => `+${formatoVuelta(seg)}`;

// Antes de 1991 había medios puntos: sin redondear, 10.5 - 10.2 da 0.30000000000000027.
export const numero = (v) => (v == null ? "—" : Math.round(v * 10) / 10);

// "EN JUEGO" de la clasificación, con la cuenta y los textos de standings_view.py.
export function enJuego(ronda, eventos, solapa) {
  if (ronda == null || !eventos.length) return { valor: "—", detalle: "sin datos del calendario" };
  const faltan = eventos.filter((ev) => ev.ronda > ronda);
  if (!faltan.length) return { valor: "—", detalle: "Temporada terminada" };
  const restantes = faltan.length;
  const sprints = faltan.filter((ev) => ev.conSprint).length;
  let texto = `${restantes} ${restantes === 1 ? "carrera" : "carreras"}`;
  if (sprints) texto += ` y ${sprints} ${sprints === 1 ? "sprint" : "sprints"}`;
  const plural = restantes > 1 || sprints > 0;
  return {
    valor: String(restantes * PUNTOS_CARRERA[solapa] + sprints * PUNTOS_SPRINT[solapa]),
    detalle: `${texto} ${plural ? "restantes" : "restante"}`,
  };
}

// El detalle del GP cuenta como Calendario y las fichas como Pilotos, igual
// que en la sidebar de escritorio.
const PESTANAS = {
  calendario: "calendario", gp: "calendario", clasificacion: "clasificacion",
  pilotos: "pilotos", piloto: "pilotos", equipo: "pilotos",
};
export const pestanaDe = (vista) => PESTANAS[vista];

// #/calendario/2026 · #/gp/2026/15[/circuito|/mapa] · #/clasificacion/2026[/equipos]
// #/pilotos/2026[/equipos] · #/piloto/2026/antonelli · #/equipo/2026/mercedes
export function parsearRuta(hash, anioActual) {
  const [vista, anioTexto, a, b] = hash.replace(/^#\/?/, "").split("/");
  const n = Number(anioTexto);
  const anio = n >= ANIO_MIN && n <= anioActual ? n : anioActual;
  if (vista === "gp" && Number(a) > 0) {
    return { vista, anio, ronda: Number(a), capa: b === "circuito" || b === "mapa" ? b : null };
  }
  if (vista === "clasificacion" || vista === "pilotos") {
    return { vista, anio, solapa: a === "equipos" ? "equipos" : "pilotos" };
  }
  if ((vista === "piloto" || vista === "equipo") && a) return { vista, anio, id: a };
  return { vista: "calendario", anio };
}

// Para el selector de temporada, que sólo está en las vistas de primer nivel.
export function rutaConAnio(ruta, anio) {
  return `#/${ruta.vista}/${anio}${ruta.solapa === "equipos" ? "/equipos" : ""}`;
}

export const edadEn = (nacimiento, anio) => anio - Number(nacimiento.slice(0, 4));

// Carrera completa = temporadas terminadas + la que está en curso. Los títulos
// salen sólo de las terminadas: el que va primero a mitad de año todavía no
// es campeón (historial.carrera_completa).
export function sumarCarrera(previa, actual) {
  if (!previa && !actual) return null;
  const p = previa ?? { titulos: 0, victorias: 0, podios: 0, gps: 0, debut: null };
  const a = actual ?? { victorias: 0, podios: 0, gps: 0, debut: null };
  const debuts = [p.debut, a.debut].filter((d) => d != null);
  return {
    titulos: p.titulos,
    victorias: p.victorias + a.victorias,
    podios: p.podios + a.podios,
    gps: p.gps + a.gps,
    debut: debuts.length ? Math.min(...debuts) : null,
  };
}

// Ergast no tiene siglas antes de los 2000.
export const sigla = (p) => p.codigo || p.apellido.slice(0, 3).toUpperCase();
