import { html } from "../html.js";
import { numero, sigla } from "../formato.js";
import { temporada } from "../api.js";
import { armarLogo } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Equipos", volver: `#/pilotos/${ruta.anio}/equipos` });

// Las filas de ui/fichas_pilotos.FichaEquipo.
const FILAS_DUELO = [
  ["clasificacion", "Clasificación"], ["carrera", "Carrera"], ["puntos", "Puntos"],
  ["victorias", "Victorias"], ["podios", "Podios"], ["poles", "Poles"],
];

const posicion = (fila) => fila.posicion ?? "DNF";

function armarDuelo(cara, anio) {
  return html`<div class="duelo-cab"><span>${sigla(cara.a)}</span><span>${sigla(cara.b)}</span></div>
    <div class="duelos">${FILAS_DUELO.map(([clave, etiqueta]) => {
      const [x, y] = cara[clave];
      const parteA = x + y ? (x / (x + y)) * 100 : 50;
      return html`<div class="duelo">
        <b>${numero(x)}</b>
        <span class="bar izq"><i style="width:${parteA}%;background:var(--eq)"></i></span>
        <span class="muted">${etiqueta}</span>
        <span class="bar"><i style="width:${100 - parteA}%"></i></span>
        <b class="der">${numero(y)}</b>
      </div>`;
    })}</div>
    <h3 class="mes">CARRERA POR CARRERA</h3>
    <p class="muted nota">Arriba ${cara.a.apellido}, abajo ${cara.b.apellido}. Con borde, el que llegó adelante.</p>
    <div class="tira">${cara.por_carrera.map((c) => html`<a href="#/gp/${anio}/${c.ronda}" title="${c.gp}">R${c.ronda}<b class="${c.adelante === 0 ? "w" : ""}">${posicion(c.a)}</b><b class="${c.adelante === 1 ? "w" : ""}">${posicion(c.b)}</b></a>`)}</div>`;
}

export function armarFichaEquipo(e, comun, anio) {
  const cara = e.cara_a_cara;
  return html`<div class="cabcolor" style="--eq:${comun.colores[e.constructor_id] ?? "var(--dato)"}">
      ${armarLogo(e, comun, "avatar cuadrado")}
      <div class="cabcolor-texto">
        <span class="eti">CONSTRUCTORES ${anio}</span>
        <h2>${e.nombre}</h2>
        ${cara ? html`<span class="sec meta">${cara.a.apellido} · ${cara.b.apellido}</span>` : ""}
      </div>
    </div>
    <div class="cuerpo" style="--eq:${comun.colores[e.constructor_id] ?? "var(--dato)"}">
      <div class="grandes cuatro">
        <div><small>POSICIÓN</small><b>${e.posicion ? `${e.posicion}º` : "—"}</b></div>
        <div><small>PUNTOS</small><b>${numero(e.puntos)}</b></div>
        <div><small>VICTORIAS</small><b>${e.stats.victorias}</b></div>
        <div><small>DOBLETES</small><b>${e.stats.dobletes}</b></div>
      </div>
      <h3 class="mes">CARA A CARA · QUIÉN TERMINÓ ADELANTE</h3>
      ${cara ? armarDuelo(cara, anio) : html`<p class="muted">Este equipo no tuvo dos pilotos en una misma carrera.</p>`}
    </div>`;
}

export async function render(ruta, comun) {
  const datos = await temporada(ruta.anio, comun);
  const equipo = datos?.equipos.find((e) => e.constructor_id === ruta.id);
  if (!equipo) {
    return html`<div class="estado"><h3>Sin ficha</h3><p>No hay datos de este equipo en ${ruta.anio}.</p></div>`;
  }
  return armarFichaEquipo(equipo, comun, ruta.anio);
}
