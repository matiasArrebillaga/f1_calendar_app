process.env.TZ = "America/Argentina/Buenos_Aires";

import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { calendario, sesionOpenF1 } from "../js/api.js";
import { render } from "../js/vistas/detalle.js";
import { COMUN, SINGAPUR } from "./datos.js";

// fetch falso: `rutas` es [[parte de la URL, respuesta | (url) => respuesta]].
// Una respuesta con `status` distinto de 200 es un error HTTP.
const fetchOriginal = globalThis.fetch;
const ahoraOriginal = Date.now;
let pedidos = [];
function falsear(rutas) {
  pedidos = [];
  globalThis.fetch = async (url) => {
    pedidos.push(url);
    const par = rutas.find(([parte]) => url.includes(parte));
    if (!par) throw new Error(`sin respuesta falsa para ${url}`);
    const r = typeof par[1] === "function" ? par[1](url) : par[1];
    const status = r?.status ?? 200;
    return { ok: status === 200, status, json: async () => r.cuerpo ?? r };
  };
}
afterEach(() => { globalThis.fetch = fetchOriginal; Date.now = ahoraOriginal; });

const calendarioDe = (races) => ({ MRData: { RaceTable: { Races: races } } });

test("OpenF1 responde 404 a una sesión sin resultados todavía: lista vacía, no error", async () => {
  falsear([
    ["sessions?year=2031", [{ session_name: "Practice 1", date_start: "2031-09-24T08:30:00+00:00", session_key: 7 }]],
    ["session_result?session_key=7", { status: 404, cuerpo: { detail: "No results found." } }],
    ["drivers?session_key=7", []],
  ]);
  assert.deepEqual(await sesionOpenF1(2031, "Practice 1", "2031-09-24"), { resultados: [], pilotos: [] });
});

test("las respuestas de las APIs vencen: pasado un rato se vuelven a pedir", async () => {
  falsear([["/2032.json", calendarioDe([])]]);
  const t0 = ahoraOriginal();
  Date.now = () => t0;
  await calendario(2032);
  await calendario(2032);
  assert.equal(pedidos.length, 1);              // dentro de la misma visita, del caché
  Date.now = () => t0 + 5 * 60 * 1000;
  await calendario(2032);
  assert.equal(pedidos.length, 2);              // la app quedó abierta: se pide de nuevo
});

test("si falla la sesión inicial, el detalle del GP igual se arma", async () => {
  falsear([
    ["/2026.json", calendarioDe([SINGAPUR])],
    ["sessions?year=2026", { status: 429 }],
  ]);
  // Viernes 9 de octubre, después del EL1: la sesión inicial es de OpenF1.
  Date.now = () => new Date("2026-10-09T08:00:00-03:00").getTime();
  const salida = String(await render({ vista: "gp", anio: 2026, ronda: 17, capa: null }, COMUN));
  assert.match(salida, /No se pudo cargar/);
  assert.match(salida, /CIRCUITO/);
});
