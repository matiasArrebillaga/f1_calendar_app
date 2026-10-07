import { html } from "../html.js";

const MEDALLA = { 1: "p1", 2: "p2", 3: "p3" };

// Una fila de resultado o de clasificación: posición (medalla en el podio),
// color del equipo, nombre con una línea chica debajo y el dato en cian a la
// derecha. Con `href` es un link a la ficha.
export function filaResultado({ pos, color, nombre, sub, dato, extra, href }) {
  const contenido = html`<span class="pos ${MEDALLA[pos] ?? ""}">${pos ?? "—"}</span>
    <i class="barra-eq" style="background:${color ?? "transparent"}"></i>
    <span class="nombre"><b>${nombre}</b>${sub ? html`<small>${sub}</small>` : ""}</span>
    <span class="der"><b>${dato}</b>${extra ? html`<small>${extra}</small>` : ""}</span>`;
  return href ? html`<a href="${href}">${contenido}</a>` : html`<div>${contenido}</div>`;
}

// La bandera chica de un país (flagcdn). Sin código, un hueco del mismo tamaño
// para que las filas no se corran.
export const bandera = (codigo) => (codigo
  ? html`<img class="bandera" src="https://flagcdn.com/w40/${codigo}.png" alt="" loading="lazy" width="22" height="15">`
  : html`<span class="bandera"></span>`);
