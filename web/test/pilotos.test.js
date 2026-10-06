import { test } from "node:test";
import assert from "node:assert/strict";
import { armarFichaPiloto, armarGrafico } from "../js/vistas/ficha_piloto.js";
import { armarPilotos } from "../js/vistas/pilotos.js";
import { COMUN, EQUIPO_MER, PILOTO_ANT } from "./datos.js";

const DATOS = { anio: 2026, ronda: 16, pilotos: [PILOTO_ANT], equipos: [EQUIPO_MER] };

test("grilla de pilotos: sigla mientras no hay foto, y la de Wikipedia pendiente", () => {
  const salida = String(armarPilotos(DATOS, "pilotos", 2026, COMUN));
  assert.match(salida, /href="#\/piloto\/2026\/antonelli"/);
  assert.match(salida, /Andrea Kimi Antonelli/);
  assert.match(salida, /Mercedes · 320 pts/);
  assert.match(salida, />\s*ANT\s*</);
  assert.match(salida, /data-wiki="https:\/\/en\.wikipedia\.org\/wiki\/Andrea_Kimi_Antonelli"/);
  assert.match(salida, /--eq:#00D7B6/);
});

test("con foto oficial no se pide la de Wikipedia", () => {
  const conFoto = { ...DATOS, pilotos: [{ ...PILOTO_ANT, headshot_url: "https://media.formula1.com/ant.png" }] };
  const salida = String(armarPilotos(conFoto, "pilotos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/ant\.png"/);
  assert.doesNotMatch(salida, /data-wiki/);
});

test("grilla de equipos: logo oficial o iniciales", () => {
  const sinLogo = { ...EQUIPO_MER, constructor_id: "brabham", nombre: "Brabham-Alfa Romeo" };
  const salida = String(armarPilotos({ ...DATOS, equipos: [EQUIPO_MER, sinLogo] }, "equipos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/mercedes\.png"/);
  assert.match(salida, /href="#\/equipo\/2026\/mercedes"/);
  assert.match(salida, /1º · 556 pts/);
  assert.match(salida, />BAR</);
});

test("temporada sin datos exportados", () => {
  assert.match(String(armarPilotos(null, "pilotos", 2027, COMUN)), /No hay datos de pilotos para 2027/);
});

test("ficha del piloto: cabecera, temporada y carrera completa", () => {
  const salida = String(armarFichaPiloto(PILOTO_ANT, PILOTO_ANT.carrera, COMUN, 2026));
  assert.match(salida, /Mercedes · #12 · Italia · 20 años en 2026/);
  assert.match(salida, /<small>CAMPEONATO<\/small><b>1º<\/b>/);
  assert.match(salida, /<b>4\.3<\/b><small>Prom\. largada/);   // 4.25 redondeado a un decimal
  assert.match(salida, /<b>16<\/b><small>GPs/);
  assert.match(salida, /<b>2026<\/b><small>Debut/);
});

test("ficha sin carrera previa ni promedios", () => {
  const sinStats = { ...PILOTO_ANT, stats: { ...PILOTO_ANT.stats, prom_llegada: null, prom_largada: null, posicion: null } };
  const salida = String(armarFichaPiloto(sinStats, null, COMUN, 2026));
  assert.match(salida, /<small>CAMPEONATO<\/small><b>—<\/b>/);
  assert.match(salida, /<b>—<\/b><small>Prom\. llegada/);
  assert.match(salida, /Sin datos de carrera/);
});

test("gráfico carrera por carrera: alto por posición, abandonos en rojo y link al GP", () => {
  const salida = String(armarGrafico(PILOTO_ANT.tira, 2026));
  assert.match(salida, /href="#\/gp\/2026\/1"/);
  assert.match(salida, /height:95%/);
  assert.match(salida, /class="barra dnf"/);
  assert.match(salida, />DNF</);
  assert.match(String(armarGrafico([], 2026)), /Todavía no corrió/);
});
