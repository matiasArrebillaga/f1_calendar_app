import { test } from "node:test";
import assert from "node:assert/strict";
import { armarFichaEquipo } from "../js/vistas/ficha_equipo.js";
import { COMUN, EQUIPO_MER } from "./datos.js";

test("cabecera y números grandes", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /CONSTRUCTORES 2026/);
  assert.match(salida, /Antonelli · Russell/);
  assert.match(salida, /<small>POSICIÓN<\/small><b>1º<\/b>/);
  assert.match(salida, /<small>DOBLETES<\/small><b>3<\/b>/);
});

test("cara a cara: barras partidas en proporción", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /<div class="duelo-cab"><span>ANT<\/span><span>RUS<\/span><\/div>/);
  assert.match(salida, /<b>11<\/b>[\s\S]*?width:68\.75%[\s\S]*?Carrera[\s\S]*?width:31\.25%[\s\S]*?<b class="der">5<\/b>/);
});

test("tira carrera por carrera: borde en el que llegó adelante y DNF", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /href="#\/gp\/2026\/1" title="Australian Grand Prix">R1<b class="">2<\/b><b class="w">1<\/b>/);
  assert.match(salida, /R2<b class="w">1<\/b><b class="">DNF<\/b>/);
});

test("equipo sin dos pilotos en una misma carrera", () => {
  const salida = String(armarFichaEquipo({ ...EQUIPO_MER, cara_a_cara: null }, COMUN, 2026));
  assert.match(salida, /Este equipo no tuvo dos pilotos en una misma carrera/);
  assert.doesNotMatch(salida, /Antonelli · Russell/);
});
