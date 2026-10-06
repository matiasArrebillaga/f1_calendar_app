import { test } from "node:test";
import assert from "node:assert/strict";
import {
  armarClasificacion, equiposDeTemporada, normalizarEquipos, normalizarPilotos,
} from "../js/vistas/clasificacion.js";
import { COMUN } from "./datos.js";

const piloto = (pos, id, nombre, apellido, puntos, wins, constructores) => ({
  position: String(pos), points: String(puntos), wins: String(wins),
  Driver: { driverId: id, givenName: nombre, familyName: apellido }, Constructors: constructores,
});
const MER = { constructorId: "mercedes", name: "Mercedes" };
const JUEGO = { valor: "183", detalle: "7 carreras y 1 sprint restantes" };

test("pilotos: líder, ventaja, puntos en juego y filas con link", () => {
  const filas = normalizarPilotos([
    piloto(1, "antonelli", "Andrea Kimi", "Antonelli", 320, 8, [MER]),
    piloto(2, "russell", "George", "Russell", 236, 1, [MER]),
  ], COMUN);
  assert.deepEqual(filas[0], { pos: 1, id: "antonelli", nombre: "Andrea Kimi Antonelli", corto: "Antonelli",
    equipo: "Mercedes", color: "#00D7B6", puntos: 320, victorias: 8 });
  const salida = String(armarClasificacion({ filas, solapa: "pilotos", anio: 2026, tras: "TRAS LA R16 · MALASIA", juego: JUEGO }));
  assert.match(salida, /TRAS LA R16 · MALASIA/);
  assert.match(salida, /<b class="txt">Antonelli<\/b><small>320 puntos/);
  assert.match(salida, /<b>\+84<\/b><small>sobre Russell/);
  assert.match(salida, /<b>183<\/b><small>7 carreras y 1 sprint restantes/);
  assert.match(salida, /Mercedes · 8 victorias/);
  assert.match(salida, /Mercedes · 1 victoria</);
  assert.match(salida, /−84/);
  assert.match(salida, /href="#\/piloto\/2026\/russell"/);
  assert.match(salida, /href="#\/clasificacion\/2026\/equipos"/);
});

test("un piloto que cambió de equipo muestra los dos", () => {
  const [fila] = normalizarPilotos([piloto(9, "lawson", "Liam", "Lawson", 65, 0, [
    { constructorId: "red_bull", name: "Red Bull" }, { constructorId: "rb", name: "RB F1 Team" }])], COMUN);
  assert.equal(fila.equipo, "Red Bull / RB F1 Team");
});

test("medios puntos de los años 50 sin errores de coma flotante", () => {
  const filas = normalizarPilotos([
    piloto(1, "farina", "Nino", "Farina", 30, 3, [{ constructorId: "alfa", name: "Alfa Romeo" }]),
    piloto(2, "fangio", "Juan", "Fangio", 27.7, 3, [{ constructorId: "alfa", name: "Alfa Romeo" }]),
  ], COMUN);
  const salida = String(armarClasificacion({ filas, solapa: "pilotos", anio: 1950, tras: "", juego: JUEGO }));
  assert.match(salida, /\+2\.3</);
  assert.doesNotMatch(salida, /0000000/);
});

test("equipos: de Jolpica o, antes de 1958, de la temporada exportada", () => {
  const [mer] = normalizarEquipos([{ position: "1", points: "556", wins: "11", Constructor: MER }], COMUN);
  assert.equal(mer.href, undefined);
  assert.deepEqual(mer, { pos: 1, id: "mercedes", nombre: "Mercedes", corto: "Mercedes", equipo: null,
    color: "#00D7B6", puntos: 556, victorias: 11 });
  const [alfa] = equiposDeTemporada([{ constructor_id: "alfa", nombre: "Alfa Romeo", posicion: null, puntos: 89, victorias: 6 }], COMUN);
  assert.equal(alfa.pos, null);
  assert.equal(alfa.nombre, "Alfa Romeo");
});

test("sin clasificación", () => {
  const salida = String(armarClasificacion({ filas: [], solapa: "equipos", anio: 1950, tras: "", juego: JUEGO }));
  assert.match(salida, /No hay clasificación disponible para 1950/);
});
