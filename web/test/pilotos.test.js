import { test } from "node:test";
import assert from "node:assert/strict";
import { armarFichaPiloto, filasCarrera } from "../js/vistas/ficha_piloto.js";
import { armarPilotos } from "../js/vistas/pilotos.js";
import { COMUN, EQUIPO_MER, PILOTO_ANT } from "./datos.js";

const DATOS = { anio: 2026, ronda: 16, pilotos: [PILOTO_ANT], equipos: [EQUIPO_MER] };

test("grilla de pilotos: tarjeta con número, posición y sigla mientras no hay foto", () => {
  const salida = String(armarPilotos(DATOS, "pilotos", 2026, COMUN));
  assert.match(salida, /href="#\/piloto\/2026\/antonelli"/);
  assert.match(salida, /<span class="num">12<\/span>/);
  assert.match(salida, /<span class="pos-chip mono">1º<\/span>/);
  assert.match(salida, /<b>Antonelli<\/b><small><span>Mercedes<\/span><span class="mono">320 pts<\/span>/);
  assert.match(salida, />\s*ANT\s*</);
  assert.match(salida, /data-wiki="https:\/\/en\.wikipedia\.org\/wiki\/Andrea_Kimi_Antonelli"/);
  assert.match(salida, /--eq:#00D7B6/);
});

test("con foto de cuerpo entero: va esa, sin nombre de transición propio, y se saca si no carga", () => {
  const conFoto = { ...DATOS, pilotos: [{ ...PILOTO_ANT, foto_cuerpo: "https://cdn/ant.webp" }] };
  const salida = String(armarPilotos(conFoto, "pilotos", 2026, COMUN));
  assert.match(salida, /<img class="cuerpo-foto" src="https:\/\/cdn\/ant\.webp"/);
  // El nombre de transición lo pone app.js sólo en la tarjeta tocada: con uno
  // por foto, la transición las dibuja a todas sin recortar.
  assert.doesNotMatch(salida, /view-transition-name/);
  assert.match(salida, /onerror="this\.remove\(\)"/);
  assert.doesNotMatch(salida, /data-wiki/);
});

test("con sólo la foto de busto (2018-2025) se usa esa", () => {
  const conFoto = { ...DATOS, pilotos: [{ ...PILOTO_ANT, headshot_url: "https://media.formula1.com/ant.png" }] };
  const salida = String(armarPilotos(conFoto, "pilotos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/ant\.png"/);
  assert.doesNotMatch(salida, /data-wiki|cuerpo-foto/);
});

test("grilla de equipos: logo, auto si hay, e iniciales si no hay logo", () => {
  const sinLogo = { ...EQUIPO_MER, constructor_id: "brabham", nombre: "Brabham-Alfa Romeo" };
  const salida = String(armarPilotos({ ...DATOS, equipos: [EQUIPO_MER, sinLogo] }, "equipos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/mercedes\.png"/);
  assert.match(salida, /<img class="auto" src="https:\/\/cdn\/mercedes-auto\.webp"/);
  assert.match(salida, /href="#\/equipo\/2026\/mercedes"/);
  assert.match(salida, /1º · 556 pts/);
  assert.match(salida, />BAR</);
  assert.equal(salida.match(/class="auto"/g).length, 1);
});

test("temporada sin datos exportados", () => {
  assert.match(String(armarPilotos(null, "pilotos", 2027, COMUN)), /No hay datos de pilotos para 2027/);
});

test("ficha del piloto: portada, temporada y carrera completa fija abajo", () => {
  const salida = String(armarFichaPiloto(PILOTO_ANT, PILOTO_ANT.carrera, COMUN, 2026));
  assert.match(salida, /Mercedes · #12/);
  assert.match(salida, /Italia · 20 años en 2026/);
  assert.match(salida, /<h2>Antonelli<\/h2>/);
  assert.match(salida, /<small>CAMPEONATO<\/small><b>1º<\/b>/);
  assert.match(salida, /<b>4\.3<\/b><small>Prom\. largada/);   // 4.25 redondeado a un decimal
  assert.match(salida, /class="carrera-fija"[\s\S]*<b>16<\/b><small>GPs[\s\S]*<b>2026<\/b><small>Debut/);
  assert.match(salida, /class="banda"[\s\S]*?ANT[\s\S]*?<b>Antonelli<\/b>/);   // sigla mientras no hay foto
});

test("ficha sin carrera previa ni promedios", () => {
  const sinStats = { ...PILOTO_ANT, stats: { ...PILOTO_ANT.stats, prom_llegada: null, prom_largada: null, posicion: null } };
  const salida = String(armarFichaPiloto(sinStats, null, COMUN, 2026));
  assert.match(salida, /<small>CAMPEONATO<\/small><b>—<\/b>/);
  assert.match(salida, /<b>—<\/b><small>Prom\. llegada/);
  assert.match(salida, /class="carrera-fija"[\s\S]*Sin datos de carrera/);
});

test("ficha con foto de cuerpo entero en la portada", () => {
  const salida = String(armarFichaPiloto({ ...PILOTO_ANT, foto_cuerpo: "https://cdn/ant.webp" }, null, COMUN, 2026));
  assert.match(salida, /<section class="portada"[\s\S]*?<img class="cuerpo-foto" src="https:\/\/cdn\/ant\.webp"/);
  assert.doesNotMatch(salida, /view-transition-name/);
});

test("carrera por carrera: la más reciente primero, con últimas 5 y links", () => {
  const salida = String(armarFichaPiloto(PILOTO_ANT, null, COMUN, 2026));
  assert.match(salida, /Últimas 5/);
  assert.ok(salida.indexOf('href="#/gp/2026/2"') < salida.indexOf('href="#/gp/2026/1"'));
  assert.match(salida, /href="#\/gp\/2026\/2"[\s\S]*?<span class="caja mono fuera">DNF<\/span>/);
  const vacia = String(armarFichaPiloto({ ...PILOTO_ANT, tira: [] }, null, COMUN, 2026));
  assert.match(vacia, /Todavía no corrió en esta temporada/);
  assert.doesNotMatch(vacia, /Últimas 5/);
});

test("filas de carrera por carrera: caja según el puesto y puestos ganados", () => {
  const tira = [
    { ronda: 1, gp: "Azerbaijan Grand Prix", pais: "Azerbaijan", largada: 2, posicion: 2, posicion_texto: "2" },
    { ronda: 2, gp: "X Grand Prix", pais: "Nowhere", largada: 19, posicion: 1, posicion_texto: "1" },
    { ronda: 3, gp: "X Grand Prix", pais: "Nowhere", largada: 1, posicion: 15, posicion_texto: "15" },
    { ronda: 4, gp: "X Grand Prix", pais: "Nowhere", largada: 0, posicion: 7, posicion_texto: "7" },
    { ronda: 5, gp: "X Grand Prix", pais: "Nowhere", largada: 3, posicion: null, posicion_texto: "D" },
  ];
  const [r5, r4, r3, r2, r1] = filasCarrera(tira, COMUN);
  assert.deepEqual(r1, { ronda: 1, bandera: "az", gp: "Azerbaiyán", largada: 2, texto: 2, clase: "podio", delta: "=", claseDelta: "" });
  assert.equal(r2.clase, "gano");
  assert.equal(r2.delta, "▲18");
  assert.equal(r2.claseDelta, "sube");
  assert.equal(r3.clase, "");
  assert.equal(r3.delta, "▼14");
  assert.equal(r4.clase, "puntos");
  assert.equal(r4.delta, "");                        // largó desde boxes: sin ▲/▼
  assert.equal(r4.largada, 0);
  assert.equal(r5.texto, "DSQ");
  assert.equal(r5.clase, "fuera");
  assert.equal(r5.delta, "");
  assert.equal(r2.bandera, null);
});

test("grilla de equipos de otra temporada: sin el auto de este año", () => {
  const salida = String(armarPilotos({ ...DATOS, equipos: [EQUIPO_MER] }, "equipos", 2010, COMUN));
  assert.doesNotMatch(salida, /class="auto"/);
});

test("logo que no carga (CDN sin publicar el año): quedan las iniciales", () => {
  const salida = String(armarPilotos({ ...DATOS, equipos: [EQUIPO_MER] }, "equipos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/mercedes\.png" alt="" loading="lazy" data-ini="M" onerror="this\.replaceWith\(this\.dataset\.ini\)">/);
});

test("filas: sin texto de largada si no largó (W/F), aunque la grilla diga 0", () => {
  const tira = [
    { ronda: 1, gp: "X Grand Prix", pais: "Nowhere", largada: 0, posicion: null, posicion_texto: "W" },
    { ronda: 2, gp: "X Grand Prix", pais: "Nowhere", largada: 0, posicion: null, posicion_texto: "F" },
  ];
  const salida = String(armarFichaPiloto({ ...PILOTO_ANT, tira }, null, COMUN, 2026));
  assert.doesNotMatch(salida, /Largó desde boxes/);
  assert.match(salida, />DNS</);
  assert.match(salida, />DNQ</);
});
