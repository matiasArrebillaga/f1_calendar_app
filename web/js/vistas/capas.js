import { html } from "../html.js";

// Las mismas filas que ui/datos_circuito.filas_ficha.
export const FILAS_CORTAS = [
  ["Longitud", (d) => `${d.longitud_km} km`],
  ["Vueltas", (d) => d.vueltas],
  ["Distancia total", (d) => `${d.distancia_km} km`],
  ["Curvas", (d) => d.curvas],
  ["Récord de vuelta", (d) => d.record_vuelta],
  ["Primer GP", (d) => d.primer_gp],
];
export const FILAS_COMPLETAS = [["Tipo", (d) => d.tipo], ["Sentido de giro", (d) => d.sentido], ...FILAS_CORTAS];

export const armarFicha = (datos, filas) =>
  html`<div class="ficha">${filas.map(([etiqueta, valor]) => html`<span>${etiqueta}</span><span>${valor(datos)}</span>`)}</div>`;

const CERRAR = html`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>`;

// Las capas son una pantalla más en el historial (#/gp/…/mapa o /circuito):
// tocar afuera, la X o "atrás" de Android vuelven al detalle.
export function armarMapa(ev) {
  const volver = `#/gp/${ev.anio}/${ev.ronda}`;
  return html`<div class="capa capa-mapa" data-atras="${volver}">
    <button class="icono-btn cerrar" data-atras="${volver}" aria-label="Cerrar">${CERRAR}</button>
    <img src="mapas/${ev.circuitId}.png" alt="Trazado de ${ev.circuito}">
  </div>`;
}

export function armarHoja(ev, datos, ganadores) {
  const volver = `#/gp/${ev.anio}/${ev.ronda}`;
  return html`<div class="capa">
    <div class="velo" data-atras="${volver}"></div>
    <section class="hoja" role="dialog" aria-label="Datos del circuito">
      <div class="asa"></div>
      <div class="fila">
        <h3 class="titulo-circuito">${datos?.nombre_completo ?? ev.circuito}</h3>
        <button class="icono-btn cerrar" data-atras="${volver}" aria-label="Cerrar">${CERRAR}</button>
      </div>
      ${datos ? armarFicha(datos, FILAS_COMPLETAS) : ""}
      ${ganadores?.lista.length
        ? html`<div class="fila"><span class="eti">GANADORES</span>${ganadores.mas
            ? html`<span class="muted mas">Más victorias: ${ganadores.mas[0]} (${ganadores.mas[1]})</span>` : ""}</div>
          <div class="tabla">${ganadores.lista.map((g) =>
            html`<span class="mono muted">${g.anio}</span><span>${g.piloto}</span><span class="muted">${g.equipo}</span>`)}</div>`
        : html`<p class="muted">Sin ganadores registrados.</p>`}
    </section>
  </div>`;
}
