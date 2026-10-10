process.env.TZ = "America/Argentina/Buenos_Aires";

import { test } from "node:test";
import assert from "node:assert/strict";
import { aEvento } from "../js/formato.js";
import { armarIndice, filtrar } from "../js/buscador.js";
import { COMUN, PILOTO_ANT, SINGAPUR } from "./datos.js";

const HISTORICO = {
  pilotos: [
    { id: "antonelli", nombre: "Andrea Kimi Antonelli", anio: 2025 },
    { id: "senna", nombre: "Ayrton Senna", anio: 1994 },
    { id: "hill", nombre: "Graham Hill", anio: 1975 },
    { id: "hamilton", nombre: "Lewis Hamilton", anio: 2025 },
  ],
  equipos: [{ id: "lotus", nombre: "Team Lotus", anio: 1994 }],
};
const INDICE = armarIndice({
  eventos: [aEvento(SINGAPUR, COMUN)],
  datos: { pilotos: [{ ...PILOTO_ANT, equipo: "Mercedes" }], equipos: [{ constructor_id: "mercedes", nombre: "Mercedes" }] },
  historico: HISTORICO,
  anio: 2026,
  anioActual: 2026,
});
const hrefs = (consulta) => filtrar(INDICE, consulta).map((i) => i.href);

test("GP, piloto y equipo de la temporada mirada", () => {
  assert.deepEqual(hrefs("singapur"), ["#/gp/2026/17"]);
  assert.deepEqual(hrefs("mercedes"), ["#/equipo/2026/mercedes"]);
  // Antonelli está en la temporada: no se repite el del índice histórico.
  assert.deepEqual(hrefs("antonelli"), ["#/piloto/2026/antonelli"]);
});

test("pilotos y equipos de otros años llevan a su última temporada", () => {
  assert.deepEqual(hrefs("senna"), ["#/piloto/1994/senna"]);
  assert.deepEqual(hrefs("lotus"), ["#/equipo/1994/lotus"]);
});

test("sin tildes, varias palabras y primero lo que empieza con lo escrito", () => {
  assert.deepEqual(hrefs("AYRTON sen"), ["#/piloto/1994/senna"]);
  assert.deepEqual(hrefs("ham"), ["#/piloto/2025/hamilton", "#/piloto/1975/hill"]);   // Graham sólo lo contiene
  assert.deepEqual(hrefs("1988"), ["#/calendario/1988"]);
  assert.deepEqual(hrefs("zzz"), []);
});

test("sin consulta muestra los primeros, con tope", () => {
  assert.equal(filtrar(INDICE, "  ").length, 8);
  assert.equal(filtrar(INDICE, "  ")[0].href, "#/gp/2026/17");
});
