process.env.TZ = "America/Argentina/Buenos_Aires";

import { test } from "node:test";
import assert from "node:assert/strict";
import { aEvento } from "../js/formato.js";
import { armarCalendario } from "../js/vistas/calendario.js";
import { COMUN, SINGAPUR, carrera } from "./datos.js";

const BAKU = carrera(15, "Azerbaijan Grand Prix", "Azerbaijan", "baku", "2026-09-26", "11:00:00Z");
const AUSTIN = carrera(18, "United States Grand Prix", "USA", "americas", "2026-10-25", "19:00:00Z");
const eventos = [BAKU, SINGAPUR, AUSTIN].map((r) => aEvento(r, COMUN));

test("temporada en curso: próxima arriba y las corridas plegadas", () => {
  const ahora = new Date("2026-10-06T19:40:00-03:00").getTime();
  const salida = String(armarCalendario(eventos, ahora));
  assert.match(salida, /PRÓXIMA · R17/);
  assert.match(salida, /href="#\/gp\/2026\/17"/);
  assert.match(salida, /<details class="plegado"><summary>Carreras anteriores · 1<\/summary>/);
  assert.match(salida, /dom 09:00/);                 // carrera de Singapur en hora local
  assert.match(salida, /class="tarjeta pasado"/);
  assert.match(salida, /class="tarjeta futuro"/);
  assert.match(salida, /<h3 class="mes">OCTUBRE<\/h3>/);
});

test("temporada terminada: sin próxima ni plegado", () => {
  const salida = String(armarCalendario(eventos, new Date("2027-01-10").getTime()));
  assert.doesNotMatch(salida, /PRÓXIMA/);
  assert.doesNotMatch(salida, /Carreras anteriores/);
  assert.equal(salida.match(/class="tarjeta pasado"/g).length, 3);
});

test("1950: carreras sin hora ni sesiones", () => {
  const viejas = [carrera(1, "British Grand Prix", "UK", "silverstone", "1950-05-13", null)]
    .map((r) => aEvento(r, COMUN));
  const salida = String(armarCalendario(viejas, Date.now()));
  assert.match(salida, /British Grand Prix/);
  assert.match(salida, /13 MAY/);
  assert.doesNotMatch(salida, /undefined|NaN/);
});

test("sin carreras publicadas", () => {
  assert.match(String(armarCalendario([], Date.now())), /Sin calendario/);
});
