import { html } from "../html.js";
import { numero, sigla } from "../formato.js";
import { fotoWikipedia, temporada } from "../api.js";

export const encabezado = () => ({ titulo: "Pilotos" });

const GRIS = "#3F4957";

// Siempre se ve algo en el lugar de la foto: la oficial de F1 si la base la
// tiene, la de Wikipedia cuando llega (cargarFotos) y mientras tanto la sigla.
export function armarFoto(p, color, clase = "foto") {
  if (p.headshot_url) {
    return html`<span class="${clase}" style="--eq:${color ?? GRIS}"><img src="${p.headshot_url}" alt="" loading="lazy"></span>`;
  }
  return html`<span class="${clase}" style="--eq:${color ?? GRIS}" data-wiki="${p.url_wiki ?? ""}">${sigla(p)}</span>`;
}

// Iniciales como ui/fichas_pilotos.LogoEquipo: sin "F1" ni "Team".
const iniciales = (nombre) => nombre.split(/[\s-]+/)
  .filter((w) => w && !["F1", "F", "Team"].includes(w)).map((w) => w[0]).join("").slice(0, 3).toUpperCase();

export function armarLogo(e, comun, clase = "logo-eq") {
  const logo = comun.logos[e.constructor_id];
  return html`<span class="${clase}" style="--eq:${comun.colores[e.constructor_id] ?? GRIS}">${logo
    ? html`<img src="${logo}" alt="" loading="lazy">` : iniciales(e.nombre)}</span>`;
}

export function armarPilotos(datos, solapa, anio, comun) {
  const base = `#/pilotos/${anio}`;
  const segmento = html`<div class="segmento">
    <a href="${base}" class="${solapa === "pilotos" ? "activa" : ""}">Pilotos</a>
    <a href="${base}/equipos" class="${solapa === "equipos" ? "activa" : ""}">Equipos</a>
  </div>`;
  const lista = solapa === "equipos" ? datos?.equipos : datos?.pilotos;
  if (!lista?.length) {
    return html`${segmento}<div class="estado"><h3>Sin datos</h3><p>No hay datos de pilotos para ${anio}.</p></div>`;
  }
  const tarjetas = solapa === "equipos"
    ? lista.map((e) => html`<a class="tpil" href="#/equipo/${anio}/${e.constructor_id}">
        ${armarLogo(e, comun)}
        <span class="info"><b>${e.nombre}</b><small>${e.posicion ? `${e.posicion}º · ` : ""}${numero(e.puntos)} pts</small></span>
      </a>`)
    : lista.map((p) => html`<a class="tpil" href="#/piloto/${anio}/${p.driver_id}">
        ${armarFoto(p, comun.colores[p.constructor_id])}
        <span class="info"><b>${p.nombre} ${p.apellido}</b><small>${p.equipo} · ${numero(p.puntos)} pts</small></span>
      </a>`);
  return html`${segmento}<div class="cuerpo"><div class="grilla">${tarjetas}</div></div>`;
}

export function cargarFotos(main) {
  for (const caja of main.querySelectorAll("[data-wiki]")) {
    if (!caja.dataset.wiki) continue;
    fotoWikipedia(caja.dataset.wiki).then((src) => {
      if (!src) return;
      const img = new Image();
      img.alt = "";
      img.onload = () => caja.replaceChildren(img);   // si no carga, queda la sigla
      img.src = src;
    }).catch(() => {});
  }
}

export async function render(ruta, comun) {
  return armarPilotos(await temporada(ruta.anio, comun), ruta.solapa, ruta.anio, comun);
}

export const montar = (main) => cargarFotos(main);
