process.env.TZ = "America/Argentina/Buenos_Aires";   // las horas de los tests son de GMT-3

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  aEvento, cuentaRegresiva, diaHora, edadEn, enJuego, fechaSesion, formatoDiferencia,
  formatoVuelta, indiceProxima, numero, parsearRuta, pestanaDe, rangoFechas, rutaConAnio,
  sigla, sumarCarrera, estadoSesiones, gpCorto, hayEnVivo,
} from "../js/formato.js";
import { COMUN, SINGAPUR, carrera } from "./datos.js";

test("la hora de Jolpica (UTC) se muestra en hora local", () => {
  assert.equal(diaHora(fechaSesion({ date: "2026-10-11", time: "12:00:00Z" })), "dom 09:00");
});

test("rango de fechas: mismo día, mismo mes y cruzando de mes", () => {
  const d = (s) => new Date(`${s}T12:00`);
  assert.equal(rangoFechas(d("2026-10-11"), d("2026-10-11")), "11 OCT");
  assert.equal(rangoFechas(d("2026-10-09"), d("2026-10-11")), "9 – 11 OCT");
  assert.equal(rangoFechas(d("2026-10-30"), d("2026-11-01")), "30 OCT – 1 NOV");
});

test("evento de un fin de semana sprint: sesiones en orden y traducidas", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  assert.equal(ev.nombre, "Gran Premio de Singapur");
  assert.equal(ev.pais, "Singapur");
  assert.equal(ev.bandera, "sg");
  assert.equal(ev.circuitId, "marina_bay");
  assert.equal(ev.rango, "9 – 11 OCT");
  assert.equal(ev.conSprint, true);
  assert.deepEqual(ev.sesiones.map((s) => s.corto), ["EL1", "Clasif. sprint", "Sprint", "Clasif.", "Carrera"]);
  assert.equal(ev.sesiones[1].openf1, "Sprint Qualifying");
  assert.equal(ev.sesiones[4].jolpica, "results");
  assert.equal(ev.sesiones[0].dia, "2026-10-09");
});

test("en 2023 la clasificación sprint se llamaba SprintShootout", () => {
  const ev = aEvento(carrera(4, "Azerbaijan Grand Prix", "Azerbaijan", "baku", "2023-04-30", "11:00:00Z", {
    SprintShootout: { date: "2023-04-29", time: "08:30:00Z" },
  }), COMUN);
  assert.deepEqual(ev.sesiones.map((s) => s.nombre), ["Clasificación sprint", "Carrera"]);
});

test("temporada vieja sin horarios ni sesiones: sólo la carrera", () => {
  const ev = aEvento(carrera(1, "British Grand Prix", "UK", "silverstone", "1950-05-13", null), COMUN);
  assert.equal(ev.nombre, "British Grand Prix");   // sin traducción: queda en inglés
  assert.equal(ev.bandera, null);
  assert.deepEqual(ev.sesiones.map((s) => s.nombre), ["Carrera"]);
  assert.equal(ev.rango, "13 MAY");
  assert.equal(ev.conSprint, false);
});

test("la próxima sigue siéndolo hasta 2 h después de largar", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  const largada = ev.largada.getTime();
  assert.equal(indiceProxima([ev], largada + 3600e3), 0);
  assert.equal(indiceProxima([ev], largada + 3 * 3600e3), -1);
});

test("cuenta regresiva y EN CURSO", () => {
  const largada = Date.UTC(2026, 9, 11, 12);
  assert.deepEqual(cuentaRegresiva(largada, largada - (4 * 86400 + 13 * 3600 + 20 * 60) * 1000),
    { enCurso: false, dias: 4, horas: "13", minutos: "20" });
  assert.equal(cuentaRegresiva(largada, largada + 1000).enCurso, true);
});

test("tiempos de vuelta y diferencias como en escritorio", () => {
  assert.equal(formatoVuelta(93.294), "1:33.294");
  assert.equal(formatoVuelta(59.5), "59.500");
  assert.equal(formatoDiferencia(0.108), "+0.108");
  assert.equal(formatoDiferencia(62.312), "+1:02.312");
});

test("puntos con medios no arrastran errores de coma flotante", () => {
  assert.equal(numero(10.5 - 10.2), 0.3);
  assert.equal(numero(320), 320);
  assert.equal(numero(null), "—");
});

test("puntos en juego, con los textos de standings_view.py", () => {
  const ev = (ronda, conSprint = false) => ({ ronda, conSprint });
  const eventos = [ev(16), ev(17, true), ev(18), ev(19), ev(20), ev(21), ev(22), ev(23)];
  assert.deepEqual(enJuego(16, eventos, "pilotos"), { valor: "183", detalle: "7 carreras y 1 sprint restantes" });
  assert.deepEqual(enJuego(16, eventos, "equipos"), { valor: String(7 * 43 + 15), detalle: "7 carreras y 1 sprint restantes" });
  assert.deepEqual(enJuego(22, eventos, "pilotos"), { valor: "25", detalle: "1 carrera restante" });
  assert.deepEqual(enJuego(23, eventos, "pilotos"), { valor: "—", detalle: "Temporada terminada" });
  assert.deepEqual(enJuego(null, eventos, "pilotos"), { valor: "—", detalle: "sin datos del calendario" });
});

test("rutas", () => {
  assert.deepEqual(parsearRuta("", 2026), { vista: "calendario", anio: 2026 });
  assert.deepEqual(parsearRuta("#/calendario/1988", 2026), { vista: "calendario", anio: 1988 });
  assert.deepEqual(parsearRuta("#/calendario/1900", 2026), { vista: "calendario", anio: 2026 });
  assert.deepEqual(parsearRuta("#/gp/2026/15", 2026), { vista: "gp", anio: 2026, ronda: 15, capa: null });
  assert.deepEqual(parsearRuta("#/gp/2026/15/circuito", 2026), { vista: "gp", anio: 2026, ronda: 15, capa: "circuito" });
  assert.deepEqual(parsearRuta("#/gp/2026/15/mapa", 2026), { vista: "gp", anio: 2026, ronda: 15, capa: "mapa" });
  assert.deepEqual(parsearRuta("#/gp/2026/x", 2026), { vista: "calendario", anio: 2026 });
  assert.deepEqual(parsearRuta("#/clasificacion/2025/equipos", 2026), { vista: "clasificacion", anio: 2025, solapa: "equipos" });
  assert.deepEqual(parsearRuta("#/pilotos/2025", 2026), { vista: "pilotos", anio: 2025, solapa: "pilotos" });
  assert.deepEqual(parsearRuta("#/piloto/2026/antonelli", 2026), { vista: "piloto", anio: 2026, id: "antonelli" });
  assert.deepEqual(parsearRuta("#/cualquiera", 2026), { vista: "calendario", anio: 2026 });
  assert.equal(pestanaDe("gp"), "calendario");
  assert.equal(pestanaDe("equipo"), "pilotos");
  assert.equal(rutaConAnio({ vista: "clasificacion", anio: 2026, solapa: "equipos" }, 2025), "#/clasificacion/2025/equipos");
  assert.equal(rutaConAnio({ vista: "calendario", anio: 2026 }, 2025), "#/calendario/2025");
});

test("carrera completa: suma la temporada en curso pero no sus títulos", () => {
  assert.deepEqual(
    sumarCarrera({ titulos: 1, victorias: 10, podios: 20, gps: 40, debut: 2019 },
                 { titulos: 0, victorias: 2, podios: 5, gps: 16, debut: 2019 }),
    { titulos: 1, victorias: 12, podios: 25, gps: 56, debut: 2019 });
  assert.deepEqual(sumarCarrera(null, { titulos: 0, victorias: 8, podios: 13, gps: 16, debut: 2026 }),
    { titulos: 0, victorias: 8, podios: 13, gps: 16, debut: 2026 });
  assert.equal(sumarCarrera(null, null), null);
});

test("edad y sigla", () => {
  assert.equal(edadEn("2006-08-25", 2026), 20);
  assert.equal(sigla({ codigo: "ANT", apellido: "Antonelli" }), "ANT");
  assert.equal(sigla({ codigo: null, apellido: "Fangio" }), "FAN");
});

test("nombre corto del GP: sin 'Gran Premio de' ni 'Grand Prix'", () => {
  assert.equal(gpCorto("Gran Premio de Azerbaiyán"), "Azerbaiyán");
  assert.equal(gpCorto("Gran Premio de los Países Bajos"), "Países Bajos");
  assert.equal(gpCorto("United States Grand Prix"), "United States");
  assert.equal(gpCorto("Bahrain Grand Prix in Malaysia"), "Bahrain Grand Prix in Malaysia");
});

test("estado de las sesiones: próxima, en vivo con avance y hecha", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  const libres = estadoSesiones(ev.sesiones, Date.parse("2026-10-09T08:50:00Z"));
  assert.equal(libres[0].estado, "vivo");
  assert.equal(libres[0].minutos, 20);
  assert.ok(Math.abs(libres[0].avance - 20 / 60) < 1e-9);
  assert.ok(libres.slice(1).every((s) => s.estado === "proxima" && s.avance === null));

  const qualy = estadoSesiones(ev.sesiones, Date.parse("2026-10-10T13:38:00Z"));
  assert.deepEqual(qualy.map((s) => s.estado), ["hecha", "hecha", "hecha", "vivo", "proxima"]);
  assert.equal(qualy[3].nombre, "Clasificación");

  // La carrera se da por terminada a las 2 h, igual que indiceProxima.
  const fin = estadoSesiones(ev.sesiones, Date.parse("2026-10-11T14:01:00Z"));
  assert.ok(fin.every((s) => s.estado === "hecha"));
});

test("hay sesión en vivo en algún evento", () => {
  const evs = [aEvento(SINGAPUR, COMUN)];
  assert.equal(hayEnVivo(evs, Date.parse("2026-10-10T13:10:00Z")), true);
  assert.equal(hayEnVivo(evs, Date.parse("2026-10-10T11:00:00Z")), false);
  assert.equal(hayEnVivo([], Date.now()), false);
});
