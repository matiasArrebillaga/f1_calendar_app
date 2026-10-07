import { test } from "node:test";
import assert from "node:assert/strict";
import { armarFichaEquipo, filasCaraACara, tiraMarcador } from "../js/vistas/ficha_equipo.js";
import { COMUN, EQUIPO_MER } from "./datos.js";

test("portada con auto y números grandes", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /CONSTRUCTORES 2026/);
  assert.match(salida, /<h2>Mercedes<\/h2>/);
  assert.match(salida, /Antonelli · Russell/);
  assert.match(salida, /<img class="auto" src="https:\/\/cdn\/mercedes-auto\.webp"/);
  assert.match(salida, /<small>POSICIÓN<\/small><b>1º<\/b>/);
  assert.match(salida, /<small>DOBLETES<\/small><b>3<\/b>/);
  assert.match(salida, /class="banda"/);
});

test("cara a cara: marcador, tira de rondas y barras en proporción", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /class="marcador mono"><b class="a">11<\/b>–<b>5<\/b>/);
  assert.match(salida, /class="marcas"[^>]*><i class="b"><\/i><i class="a"><\/i><\/div>/);
  assert.match(salida, /<b>11<\/b>[\s\S]*?width:68\.75%[\s\S]*?Carrera[\s\S]*?width:31\.25%[\s\S]*?<b class="der">5<\/b>/);
});

test("carrera por carrera: la más reciente primero, lleno el que llegó adelante", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.ok(salida.indexOf('href="#/gp/2026/2"') < salida.indexOf('href="#/gp/2026/1"'));
  assert.match(salida, /href="#\/gp\/2026\/2"[\s\S]*?<span class="caja mono gana">1<\/span><span class="caja mono">DNF<\/span>/);
  assert.match(salida, /href="#\/gp\/2026\/1"[\s\S]*?<span class="caja mono">2<\/span><span class="caja mono gana">1<\/span>/);
});

test("filas y tira del cara a cara", () => {
  const cara = EQUIPO_MER.cara_a_cara;
  const [r2, r1] = filasCaraACara(cara, COMUN);
  assert.deepEqual(r2.a, { texto: 1, gana: true });
  assert.deepEqual(r2.b, { texto: "DNF", gana: false });
  assert.equal(r1.ronda, 1);
  assert.deepEqual(tiraMarcador(cara), [1, 0]);
});

test("equipo sin dos pilotos en una misma carrera", () => {
  const salida = String(armarFichaEquipo({ ...EQUIPO_MER, cara_a_cara: null }, COMUN, 2026));
  assert.match(salida, /Este equipo no tuvo dos pilotos en una misma carrera/);
  assert.doesNotMatch(salida, /Antonelli · Russell|class="marcador/);
});

test("temporadas viejas sin el auto de este año", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 1988));
  assert.doesNotMatch(salida, /class="auto"/);
});
