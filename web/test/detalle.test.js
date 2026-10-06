process.env.TZ = "America/Argentina/Buenos_Aires";

import { test } from "node:test";
import assert from "node:assert/strict";
import { aEvento } from "../js/formato.js";
import { armarHoja } from "../js/vistas/capas.js";
import {
  armarCircuito, armarPendiente, armarResultadosJolpica, armarResultadosOpenF1, sesionInicial,
} from "../js/vistas/detalle.js";
import { COMUN, SINGAPUR, carrera } from "./datos.js";

const piloto = (driverId, givenName, familyName, code) => ({ driverId, givenName, familyName, code });
const MER = { constructorId: "mercedes", name: "Mercedes" };
const RBR = { constructorId: "red_bull", name: "Red Bull" };
const BAKU = aEvento(carrera(15, "Azerbaijan Grand Prix", "Azerbaijan", "baku", "2026-09-26", "11:00:00Z"), COMUN);
const juntar = (filas) => filas.map(String).join("");

test("resultados de carrera: tiempo, diferencia, abandono, boxes y puntos", () => {
  const race = {
    season: "2026",
    Results: [
      { position: "1", points: "25", grid: "1", status: "Finished", Time: { time: "1:38:02.143" }, Driver: piloto("russell", "George", "Russell", "RUS"), Constructor: MER },
      { position: "2", points: "18", grid: "8", status: "Finished", Time: { time: "+0.196" }, Driver: piloto("max_verstappen", "Max", "Verstappen", "VER"), Constructor: RBR },
      { position: "3", points: "1", grid: "0", status: "Finished", Time: { time: "+40.1" }, Driver: piloto("perez", "Sergio", "Pérez", "PER"), Constructor: RBR },
      { position: "20", points: "0", grid: "5", status: "Engine", Driver: piloto("hulkenberg", "Nico", "Hülkenberg", "HUL"), Constructor: { constructorId: "audi", name: "Audi <F1>" } },
    ],
  };
  const salida = juntar(armarResultadosJolpica(race, "results", COMUN));
  assert.match(salida, /class="pos p1">1</);
  assert.match(salida, /1:38:02\.143/);
  assert.match(salida, /\+0\.196/);
  assert.match(salida, /Red Bull · largó 8º/);
  assert.match(salida, /largó desde boxes/);
  assert.match(salida, /1 pt</);
  assert.match(salida, /Engine/);
  assert.match(salida, /Sergio Pérez/);
  assert.match(salida, /Nico Hülkenberg/);
  assert.match(salida, /Audi &lt;F1&gt;/);               // escapado, no HTML
  assert.match(salida, /href="#\/piloto\/2026\/russell"/);
  assert.match(salida, /background:#00D7B6/);
});

test("Jolpica a veces manda Time con el tiempo vacío: se muestra el estado", () => {
  const race = {
    season: "2026",
    Results: [{ position: "16", points: "0", grid: "19", status: "Retired", Time: { millis: "5729837", time: "" },
      Driver: piloto("bottas", "Valtteri", "Bottas", "BOT"), Constructor: MER }],
  };
  assert.match(juntar(armarResultadosJolpica(race, "results", COMUN)), /<b>Retired<\/b>/);
});

test("clasificación: el mejor tiempo y en qué Q se hizo", () => {
  const race = {
    season: "2026",
    QualifyingResults: [
      { position: "1", Q1: "1:42.1", Q2: "1:41.8", Q3: "1:41.2", Driver: piloto("russell", "George", "Russell", "RUS"), Constructor: MER },
      { position: "16", Q1: "1:43.5", Driver: piloto("antonelli", "Andrea Kimi", "Antonelli", "ANT"), Constructor: MER },
    ],
  };
  const salida = juntar(armarResultadosJolpica(race, "qualifying", COMUN));
  assert.match(salida, /1:41\.2<\/b><small>Q3/);
  assert.match(salida, /1:43\.5<\/b><small>Q1/);
});

test("libres de OpenF1: ordenados, diferencia, vueltas y link sólo si hay ficha", () => {
  const datos = {
    resultados: [
      { position: 2, driver_number: 63, duration: 93.549, gap_to_leader: 0.255, number_of_laps: 24 },
      { position: 1, driver_number: 12, duration: 93.294, gap_to_leader: 0, number_of_laps: 23 },
      { position: null, driver_number: 99, duration: null, gap_to_leader: null, number_of_laps: 0 },
    ],
    pilotos: [
      { driver_number: 12, first_name: "Andrea Kimi", last_name: "Antonelli", name_acronym: "ANT", team_name: "Mercedes", team_colour: "00D7B6" },
      { driver_number: 63, first_name: "George", last_name: "Russell", name_acronym: "RUS", team_name: "Mercedes", team_colour: "00D7B6" },
    ],
  };
  const filas = armarResultadosOpenF1(datos, COMUN, new Map([["ANT", "antonelli"]]), 2026).map(String);
  assert.match(filas[0], /Andrea Kimi Antonelli/);
  assert.match(filas[0], /1:33\.294/);
  assert.match(filas[0], /href="#\/piloto\/2026\/antonelli"/);
  assert.match(filas[1], /\+0\.255/);
  assert.match(filas[1], /24 vueltas/);
  assert.match(filas[1], /^<div>/);                      // RUS no está en la temporada: sin link
  assert.match(filas[2], /#99/);
  assert.match(filas[2], /—/);
});

test("clasificación sprint de OpenF1: duraciones por Q", () => {
  const datos = {
    resultados: [{ position: 1, driver_number: 12, duration: [95.1, 94.6, null], gap_to_leader: [0, 0, null], number_of_laps: 15 }],
    pilotos: [{ driver_number: 12, first_name: "Andrea Kimi", last_name: "Antonelli", name_acronym: "ANT", team_name: "Mercedes", team_colour: "00D7B6" }],
  };
  const salida = String(armarResultadosOpenF1(datos, COMUN, new Map(), 2026)[0]);
  assert.match(salida, /1:34\.600/);
  assert.doesNotMatch(salida, /vueltas/);
});

test("arranca en la última sesión que ya empezó", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  assert.equal(sesionInicial(ev, new Date("2026-10-10T08:00:00-03:00").getTime()).corto, "Sprint");
  assert.equal(sesionInicial(ev, new Date("2026-10-01").getTime()).corto, "EL1");
});

test("sesión sin resultados: todavía no se corrió, o sin datos (libres antes de 2023)", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  const futura = String(armarPendiente(ev.sesiones[4], new Date("2026-10-06").getTime()));
  assert.match(futura, /Todavía no se corrió/);
  assert.match(futura, /dom 09:00/);
  const libres = String(armarPendiente(ev.sesiones[0], new Date("2026-12-01").getTime()));
  assert.match(libres, /Sin resultados/);
  assert.match(libres, /desde 2023/);
  const carreraVieja = String(armarPendiente(ev.sesiones[4], new Date("2026-12-01").getTime()));
  assert.doesNotMatch(carreraVieja, /desde 2023/);
});

test("circuito con ficha y mapa, y circuito sin datos", () => {
  const conDatos = String(armarCircuito(BAKU, COMUN));
  assert.match(conDatos, /src="mapas\/baku\.png"/);
  assert.match(conDatos, /href="#\/gp\/2026\/15\/mapa"/);
  assert.match(conDatos, /6\.003 km/);
  assert.match(conDatos, /href="#\/gp\/2026\/15\/circuito"/);
  const sepang = aEvento(carrera(16, "Bahrain Grand Prix in Malaysia", "Malaysia", "sepang", "2026-10-04", "07:00:00Z"), COMUN);
  const sinDatos = String(armarCircuito(sepang, COMUN));
  assert.match(sinDatos, /sepang circuit/);
  assert.doesNotMatch(sinDatos, /mapas\/|Más datos/);
});

test("hoja del circuito: ficha completa y ganadores", () => {
  const ganadores = {
    lista: [
      { anio: 2026, ronda: 15, gp: "Azerbaijan Grand Prix", piloto: "George Russell", equipo: "Mercedes" },
      { anio: 2025, ronda: 17, gp: "Azerbaijan Grand Prix", piloto: "Max Verstappen", equipo: "Red Bull" },
    ],
    mas: ["Sergio Pérez, Max Verstappen", 2],
  };
  const salida = String(armarHoja(BAKU, COMUN.circuitos.baku, ganadores));
  assert.match(salida, /Sentido de giro/);
  assert.match(salida, /Antihorario/);
  assert.match(salida, /George Russell/);
  assert.match(salida, /Más victorias: Sergio Pérez, Max Verstappen \(2\)/);
  assert.match(salida, /data-atras="#\/gp\/2026\/15"/);
  assert.match(String(armarHoja(BAKU, undefined, undefined)), /Sin ganadores registrados/);
});
