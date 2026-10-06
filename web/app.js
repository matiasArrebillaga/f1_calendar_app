// Calendario de la temporada actual y la próxima carrera, desde la API de
// Jolpica (la misma que usa core/historial.py en la app de escritorio).
const API = "https://api.jolpi.ca/ergast/f1/current.json";
// Sigue siendo "la próxima" un rato después de largar, como en calendar_view.py.
const DURACION_CARRERA_MS = 2 * 3600 * 1000;

// Traducciones y códigos de bandera: copiados de core/i18n.py y core/flags.py.
const EVENTOS_ES = {
  "Australian Grand Prix": "Gran Premio de Australia",
  "Bahrain Grand Prix": "Gran Premio de Baréin",
  "Bahrain Grand Prix in Malaysia": "Gran Premio de Baréin en Malasia",
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
  "Azerbaijan Grand Prix": "Gran Premio de Azerbaiyán",
  "Las Vegas Grand Prix": "Gran Premio de Las Vegas",
  "São Paulo Grand Prix": "Gran Premio de São Paulo",
  "Mexico City Grand Prix": "Gran Premio de la Ciudad de México",
  "Barcelona Grand Prix": "Gran Premio de Barcelona",
};
const PAISES_ES = {
  Bahrain: "Baréin", "Saudi Arabia": "Arabia Saudita", UAE: "Emiratos Árabes Unidos",
  Japan: "Japón", USA: "Estados Unidos", Canada: "Canadá", Mexico: "México",
  Brazil: "Brasil", Monaco: "Mónaco", Spain: "España", UK: "Reino Unido",
  Belgium: "Bélgica", Netherlands: "Países Bajos", Italy: "Italia",
  Singapore: "Singapur", Qatar: "Catar", Hungary: "Hungría",
  Azerbaijan: "Azerbaiyán", Malaysia: "Malasia",
};
const CODIGOS_PAIS = {
  UK: "gb", USA: "us", UAE: "ae", Monaco: "mc", Italy: "it", Belgium: "be",
  Netherlands: "nl", Spain: "es", Austria: "at", France: "fr", Germany: "de",
  Hungary: "hu", Azerbaijan: "az", Singapore: "sg", Japan: "jp", Qatar: "qa",
  Mexico: "mx", Brazil: "br", "Saudi Arabia": "sa", Bahrain: "bh",
  Australia: "au", China: "cn", Canada: "ca", Portugal: "pt", Malaysia: "my",
};
const SESIONES = [
  ["FirstPractice", "Entrenamiento 1"],
  ["SecondPractice", "Entrenamiento 2"],
  ["ThirdPractice", "Entrenamiento 3"],
  ["SprintQualifying", "Clasificación sprint"],
  ["Sprint", "Sprint"],
  ["Qualifying", "Clasificación"],
];
const MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
  "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"];
const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

// Sin hora publicada, Jolpica sólo trae el día: queda a las 00:00 locales.
const fecha = (s) => new Date(s.time ? `${s.date}T${s.time}` : `${s.date}T00:00`);
const mesCorto = (d) => MESES[d.getMonth()].slice(0, 3);
const dosDigitos = (n) => String(n).padStart(2, "0");
const diaHora = (d) => `${DIAS[d.getDay()]} ${dosDigitos(d.getHours())}:${dosDigitos(d.getMinutes())}`;

function rangoFechas(ev) {
  const inicio = ev.sesiones[0].fecha, fin = ev.largada;
  if (inicio.toDateString() === fin.toDateString()) return `${fin.getDate()} ${mesCorto(fin)}`;
  if (inicio.getMonth() === fin.getMonth()) return `${inicio.getDate()} – ${fin.getDate()} ${mesCorto(fin)}`;
  return `${inicio.getDate()} ${mesCorto(inicio)} – ${fin.getDate()} ${mesCorto(fin)}`;
}

function aEvento(race) {
  const largada = fecha(race);
  const sesiones = SESIONES.filter(([clave]) => race[clave])
    .map(([clave, nombre]) => ({ nombre, fecha: fecha(race[clave]) }))
    .concat({ nombre: "Carrera", fecha: largada })
    .sort((a, b) => a.fecha - b.fecha);
  const loc = race.Circuit.Location;
  return {
    ronda: race.round,
    nombre: EVENTOS_ES[race.raceName] ?? race.raceName,
    pais: loc.country,
    circuito: race.Circuit.circuitName,
    largada,
    sesiones,
  };
}

function el(tag, clase, texto) {
  const nodo = document.createElement(tag);
  if (clase) nodo.className = clase;
  if (texto != null) nodo.textContent = texto;
  return nodo;
}

function bandera(img, pais) {
  const codigo = CODIGOS_PAIS[pais];
  if (!codigo) return img.remove();
  img.src = `https://flagcdn.com/w40/${codigo}.png`;
  img.onerror = () => img.remove();
}

function mostrarProxima(ev) {
  document.getElementById("proxima").hidden = false;
  document.getElementById("proxima-nombre").textContent = ev.nombre;
  document.getElementById("proxima-lugar").textContent =
    [ev.circuito, PAISES_ES[ev.pais] ?? ev.pais, rangoFechas(ev)].join(" · ");
  bandera(document.getElementById("proxima-bandera"), ev.pais);

  const horarios = document.getElementById("horarios");
  horarios.replaceChildren();
  ev.sesiones.forEach((s, i) => {
    const esCarrera = i === ev.sesiones.length - 1;
    horarios.append(el("dt", esCarrera ? "carrera" : "", s.nombre), el("dd", "", diaHora(s.fecha)));
  });

  const actualizar = () => {
    const segundos = Math.max(0, Math.floor((ev.largada - Date.now()) / 1000));
    document.getElementById("chip").textContent = `${segundos ? "PRÓXIMA" : "EN CURSO"} · R${ev.ronda}`;
    document.getElementById("dias").textContent = Math.floor(segundos / 86400);
    document.getElementById("horas").textContent = dosDigitos(Math.floor(segundos % 86400 / 3600));
    document.getElementById("minutos").textContent = dosDigitos(Math.floor(segundos % 3600 / 60));
  };
  actualizar();
  setInterval(actualizar, 30_000);
}

function mostrarCalendario(eventos, proxima) {
  const contenedor = document.getElementById("calendario");
  contenedor.replaceChildren();
  let mes = null, grilla;
  for (const ev of eventos) {
    if (ev.largada.getMonth() !== mes) {
      mes = ev.largada.getMonth();
      contenedor.append(el("h3", "mes", MESES[mes]));
      grilla = contenedor.appendChild(el("div", "grilla"));
    }
    const estado = ev === proxima ? "proxima" : ev.largada < Date.now() ? "pasado" : "futuro";
    const tarjeta = el("article", `tarjeta ${estado}`);
    const arriba = el("div", "tarjeta-arriba");
    arriba.append(el("span", "etiqueta", `R${ev.ronda}`));
    if (estado === "proxima") arriba.append(el("span", "chip", "PRÓXIMA"));
    const img = el("img", "bandera");
    img.alt = "";
    bandera(img, ev.pais);
    arriba.append(img);
    tarjeta.append(arriba, el("h4", "", ev.nombre), el("p", "fecha", rangoFechas(ev)));
    grilla.append(tarjeta);
  }
}

async function main() {
  const estado = document.getElementById("estado");
  try {
    const datos = await (await fetch(API)).json();
    const tabla = datos.MRData.RaceTable;
    const eventos = tabla.Races.map(aEvento);
    const ahora = Date.now();
    const proxima = eventos.find((ev) => ev.largada.getTime() + DURACION_CARRERA_MS > ahora);
    document.getElementById("temporada").textContent = tabla.season;
    if (proxima) mostrarProxima(proxima);
    mostrarCalendario(eventos, proxima);
    estado.hidden = true;
  } catch (e) {
    estado.textContent = "No se pudo cargar el calendario. Revisá la conexión.";
    estado.classList.add("error");
  }
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
main();
