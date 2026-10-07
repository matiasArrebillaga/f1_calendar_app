process.env.TZ = "America/Argentina/Buenos_Aires";

import { test } from "node:test";
import assert from "node:assert/strict";
import { aEvento } from "../js/formato.js";
import { armarCalendario, ganadoresPorRonda } from "../js/vistas/calendario.js";
import { COMUN, PILOTO_ANT, SINGAPUR, carrera } from "./datos.js";

const BAKU = carrera(15, "Azerbaijan Grand Prix", "Azerbaijan", "baku", "2026-09-26", "11:00:00Z");
const AUSTIN = carrera(18, "United States Grand Prix", "USA", "americas", "2026-10-25", "19:00:00Z");
const eventos = [BAKU, SINGAPUR, AUSTIN].map((r) => aEvento(r, COMUN));

const AHORA = new Date("2026-10-06T19:40:00-03:00").getTime();
const GANADORES = new Map([[15, { codigo: "RUS", color: "#00D7B6" }]]);

test("temporada en curso: un solo listado con la próxima en su lugar", () => {
  const salida = String(armarCalendario(eventos, AHORA, GANADORES));
  assert.doesNotMatch(salida, /<details/);
  assert.match(salida, /data-subir>↑ 1 carrera corrida</);
  assert.match(salida, /class="gp-fila pasado"[\s\S]*?R15[\s\S]*?<b>Azerbaiyán<\/b>[\s\S]*?background:#00D7B6"><\/i>RUS/);
  assert.match(salida, /PRÓXIMA · R17/);
  assert.match(salida, /dom 09:00/);                 // carrera de Singapur en hora local
  assert.match(salida, /class="gp-fila futuro"[\s\S]*?<b>United States<\/b>[\s\S]*?en 19 d/);
  assert.ok(salida.indexOf("R15") < salida.indexOf("PRÓXIMA"));
  assert.ok(salida.indexOf("PRÓXIMA") < salida.indexOf("R18"));
  assert.match(salida, /<h3 class="mes">OCTUBRE<\/h3>/);
});

test("temporada terminada: todo corrido, sin próxima ni píldora", () => {
  const salida = String(armarCalendario(eventos, new Date("2027-01-10").getTime()));
  assert.doesNotMatch(salida, /PRÓXIMA|data-subir/);
  assert.equal(salida.match(/class="gp-fila pasado"/g).length, 3);
  assert.doesNotMatch(salida, /class="ganador/);     // sin datos de ganadores
});

test("1950: carreras sin hora ni sesiones", () => {
  const viejas = [carrera(1, "British Grand Prix", "UK", "silverstone", "1950-05-13", null)]
    .map((r) => aEvento(r, COMUN));
  const salida = String(armarCalendario(viejas, Date.now()));
  assert.match(salida, /<b>British<\/b>/);
  assert.match(salida, /13 MAY/);
  assert.doesNotMatch(salida, /undefined|NaN/);
});

test("ganadores por ronda, desde la tira de cada piloto", () => {
  const datos = { pilotos: [{ ...PILOTO_ANT, tira: [{ ronda: 3, posicion: 1 }, { ronda: 4, posicion: 2 }] }] };
  const ganadores = ganadoresPorRonda(datos, COMUN.colores);
  assert.deepEqual([...ganadores], [[3, { codigo: "ANT", color: "#00D7B6" }]]);
  assert.equal(ganadoresPorRonda(null, COMUN.colores).size, 0);
});

test("sin carreras publicadas", () => {
  assert.match(String(armarCalendario([], Date.now())), /Sin calendario/);
});
