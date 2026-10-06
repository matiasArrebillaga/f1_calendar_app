import { html } from "../html.js";
import { edadEn, numero, sumarCarrera } from "../formato.js";
import { carrerasPrevias, temporada } from "../api.js";
import { armarFoto, cargarFotos } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Pilotos", volver: `#/pilotos/${ruta.anio}` });

const promedio = (v) => (v == null ? "—" : v.toFixed(1));
// positionText de Ergast cuando no hay posición: D descalificado, F no
// clasificó, W no largó; el resto, abandono.
const TEXTO_SIN_POSICION = { D: "DSQ", F: "DNQ", W: "NC" };

export function armarGrafico(tira, anio) {
  if (!tira.length) return html`<p class="muted">Todavía no corrió en esta temporada.</p>`;
  return html`<div class="grafico">${tira.map((t) => {
    // 1º = barra llena; del 20º para atrás, casi nada.
    const alto = t.posicion ? ((21 - Math.min(t.posicion, 20)) / 20) * 100 : 6;
    const texto = t.posicion ?? TEXTO_SIN_POSICION[t.posicion_texto] ?? "DNF";
    return html`<a href="#/gp/${anio}/${t.ronda}" class="barra ${t.posicion ? "" : "dnf"}" title="${t.gp}" aria-label="R${t.ronda} ${t.gp}: ${texto}">
      <span class="col"><i style="height:${alto}%"></i></span><span class="num">${texto}</span></a>`;
  })}</div>
  <p class="muted nota">Posición de llegada en cada ronda. Tocar una barra abre el GP.</p>`;
}

export function armarFichaPiloto(p, carrera, comun, anio) {
  const color = comun.colores[p.constructor_id];
  const meta = [
    p.equipos.join(" / ") || p.equipo,
    p.numero ? `#${p.numero}` : "",
    comun.nacionalidades[p.nacionalidad] ?? p.nacionalidad,
    p.nacimiento ? `${edadEn(p.nacimiento, anio)} años en ${anio}` : "",
  ].filter(Boolean).join(" · ");
  const s = p.stats;
  return html`<div class="cabcolor" style="--eq:${color ?? "#3F4957"}">
      ${armarFoto(p, color, "avatar")}
      <div class="cabcolor-texto">
        <span class="eti">PILOTOS ${anio}</span>
        <h2>${p.nombre} ${p.apellido}</h2>
        <span class="sec meta">${meta}</span>
      </div>
    </div>
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
      ${armarGrafico(p.tira, anio)}
      <h3 class="mes">CARRERA COMPLETA</h3>
      ${carrera ? html`<div class="stats">${[
        ["Títulos", carrera.titulos], ["Victorias", carrera.victorias], ["Podios", carrera.podios],
        ["GPs", carrera.gps], ["Debut", carrera.debut ?? "—"],
      ].map(([etiqueta, valor]) => html`<div><b>${valor}</b><small>${etiqueta}</small></div>`)}</div>`
        : html`<p class="muted">Sin datos de carrera.</p>`}
    </div>`;
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

export const montar = (main) => cargarFotos(main);
