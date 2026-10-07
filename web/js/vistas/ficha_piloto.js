import { html } from "../html.js";
import { edadEn, gpCorto, numero, sumarCarrera } from "../formato.js";
import { carrerasPrevias, temporada } from "../api.js";
import { bandera } from "./filas.js";
import { armarFoto, armarRetrato, cargarFotos, comprimirAlBajar } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Pilotos", volver: `#/pilotos/${ruta.anio}` });

const GRIS = "#3F4957";
const promedio = (v) => (v == null ? "—" : v.toFixed(1));
// positionText de Ergast cuando no hay posición: D descalificado, F no
// clasificó, W no largó; el resto, abandono.
const TEXTO_SIN_POSICION = { D: "DSQ", F: "DNQ", W: "NC" };

// ponytail: "sumó puntos" = top 10, como desde 2010; antes puntuaban menos
// puestos. Si molesta, exportar los puntos de cada carrera en la tira.
const claseCaja = (p) => (!p ? "fuera" : p === 1 ? "gano" : p <= 3 ? "podio" : p <= 10 ? "puntos" : "");

export function filasCarrera(tira, comun) {
  return [...tira].reverse().map((t) => {
    const p = t.posicion;
    // Largada 0 = desde boxes: no hay puestos ganados que contar.
    const g = p && t.largada ? t.largada - p : null;
    return {
      ronda: t.ronda,
      bandera: comun.banderas[t.pais] ?? null,
      gp: gpCorto(comun.eventos[t.gp] ?? t.gp),
      // W (no largó) y F (no clasificó) traen grilla 0: no es "desde boxes".
      largada: ["W", "F"].includes(t.posicion_texto) ? null : t.largada ?? null,
      texto: p ?? TEXTO_SIN_POSICION[t.posicion_texto] ?? "DNF",
      clase: claseCaja(p),
      delta: g == null ? "" : g > 0 ? `▲${g}` : g < 0 ? `▼${-g}` : "=",
      claseDelta: g > 0 ? "sube" : g < 0 ? "baja" : "",
    };
  });
}

const textoLargada = (largada) => (largada === 0 ? "Largó desde boxes" : largada ? `Largó ${largada}º` : "");

const armarFila = (f, anio) => html`<a class="carrera-fila" href="#/gp/${anio}/${f.ronda}">
    <span class="ronda mono">R${f.ronda}</span>${bandera(f.bandera)}
    <span class="nombre"><b>${f.gp}</b><small>${textoLargada(f.largada)}</small></span>
    <span class="caja mono ${f.clase}">${f.texto}</span><span class="delta mono ${f.claseDelta}">${f.delta}</span>
  </a>`;

function armarCarreraCompleta(carrera) {
  return html`<div class="carrera-fija"><span class="eti">CARRERA COMPLETA</span>${carrera
    ? html`<div class="cinco">${[
      ["Títulos", carrera.titulos], ["Victorias", carrera.victorias], ["Podios", carrera.podios],
      ["GPs", carrera.gps], ["Debut", carrera.debut ?? "—"],
    ].map(([etiqueta, valor]) => html`<div><b>${valor}</b><small>${etiqueta}</small></div>`)}</div>`
    : html`<p class="muted nota">Sin datos de carrera.</p>`}</div>`;
}

export function armarFichaPiloto(p, carrera, comun, anio) {
  const color = comun.colores[p.constructor_id] ?? GRIS;
  const logo = comun.logos[p.constructor_id];
  const equipo = [p.equipos.join(" / ") || p.equipo, p.numero ? `#${p.numero}` : ""].filter(Boolean).join(" · ");
  const meta = [
    comun.nacionalidades[p.nacionalidad] ?? p.nacionalidad,
    p.nacimiento ? `${edadEn(p.nacimiento, anio)} años en ${anio}` : "",
  ].filter(Boolean).join(" · ");
  const s = p.stats;
  const filas = filasCarrera(p.tira, comun);
  return html`<div class="banda" style="--eq:${color}" aria-hidden="true">
      ${armarFoto(p, color, "avatar chico")}<span class="banda-texto"><small>${p.nombre}</small><b>${p.apellido}</b></span>
    </div>
    <section class="portada" style="--eq:${color}">
      <span class="dorsal">${p.numero ?? ""}</span>
      ${p.foto_cuerpo ? armarRetrato(p, color) : armarFoto(p, color, "avatar grande")}
      <div class="portada-texto">
        <span class="sec meta">${logo ? html`<img class="logo-chico" src="${logo}" alt="" onerror="this.remove()">` : ""}${equipo}</span>
        <span class="nombre-chico">${p.nombre}</span>
        <h2>${p.apellido}</h2>
        <span class="muted meta">${meta}</span>
      </div>
    </section>
    <div class="cuerpo">
      <div class="grandes">
        <div><small>CAMPEONATO</small><b>${s.posicion ? `${s.posicion}º` : "—"}</b></div>
        <div><small>PUNTOS</small><b>${numero(s.puntos)}</b></div>
        <div><small>VICTORIAS</small><b>${s.victorias}</b></div>
      </div>
      <div class="stats">${[
        ["Podios", s.podios], ["Poles", s.poles], ["Abandonos", s.abandonos],
        ["Prom. llegada", promedio(s.prom_llegada)], ["Prom. largada", promedio(s.prom_largada)],
      ].map(([etiqueta, valor]) => html`<div><b>${valor}</b><small>${etiqueta}</small></div>`)}</div>
      <h3 class="mes">CARRERA POR CARRERA</h3>
      ${filas.length
        ? html`<div class="ultimas"><span class="muted nota">Últimas 5</span>${filas.slice(0, 5).map((f) =>
          html`<span class="caja mono ${f.clase}">${f.texto}</span>`)}</div>
          <div class="filas">${filas.map((f) => armarFila(f, anio))}</div>`
        : html`<p class="muted">Todavía no corrió en esta temporada.</p>`}
    </div>
    ${armarCarreraCompleta(carrera)}`;
}

export async function render(ruta, comun) {
  // La carrera completa es la misma mire el año que mire: previas + lo que
  // lleva en la temporada en curso.
  const [datos, previas, enCurso] = await Promise.all([
    temporada(ruta.anio, comun),
    carrerasPrevias().catch(() => ({})),
    temporada(comun.anio_actual, comun).catch(() => null),
  ]);
  const piloto = datos?.pilotos.find((p) => p.driver_id === ruta.id);
  if (!piloto) {
    return html`<div class="estado"><h3>Sin ficha</h3><p>No hay datos de este piloto en ${ruta.anio}.</p></div>`;
  }
  const actual = enCurso?.pilotos.find((p) => p.driver_id === ruta.id)?.carrera ?? null;
  return armarFichaPiloto(piloto, sumarCarrera(previas[ruta.id] ?? null, actual), comun, ruta.anio);
}

export function montar(main) {
  cargarFotos(main);
  return comprimirAlBajar(main);
}
