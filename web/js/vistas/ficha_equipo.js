import { html } from "../html.js";
import { gpCorto, numero, sigla, textoPosicion } from "../formato.js";
import { temporada } from "../api.js";
import { bandera } from "./filas.js";
import { armarFoto, armarLogo, cargarFotos, comprimirAlBajar } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Equipos", volver: `#/pilotos/${ruta.anio}/equipos` });

// Las filas de ui/fichas_pilotos.FichaEquipo.
const FILAS_DUELO = [
  ["clasificacion", "Clasificación"], ["carrera", "Carrera"], ["puntos", "Puntos"],
  ["victorias", "Victorias"], ["podios", "Podios"], ["poles", "Poles"],
];

export function filasCaraACara(cara, comun) {
  return [...cara.por_carrera].reverse().map((c) => ({
    ronda: c.ronda,
    bandera: comun.banderas[c.pais] ?? null,
    gp: gpCorto(comun.eventos[c.gp] ?? c.gp),
    a: { texto: textoPosicion(c.a), gana: c.adelante === 0 },
    b: { texto: textoPosicion(c.b), gana: c.adelante === 1 },
  }));
}

// Quién llegó adelante en cada ronda (0 = a, 1 = b), de la primera a la última.
export const tiraMarcador = (cara) => [...cara.por_carrera].sort((x, y) => x.ronda - y.ronda).map((c) => c.adelante);

function armarDuelo(cara, color, comun, anio) {
  const [x, y] = cara.carrera;
  const tira = tiraMarcador(cara);
  const lado = (p, espejo) => html`<span class="lado ${espejo ? "espejo" : ""}">${armarFoto(p, color, "avatar chico")}
    <span><b>${sigla(p)}</b><small>${p.apellido}</small></span></span>`;
  return html`<div class="cara-a-cara">${lado(cara.a, false)}
      <span class="marcador mono"><b class="a">${x}</b>–<b>${y}</b></span>${lado(cara.b, true)}</div>
    <p class="muted nota centro">Quién llegó adelante, ronda por ronda</p>
    <div class="marcas" style="grid-template-columns:repeat(${tira.length}, minmax(0, 1fr))">${tira.map((q) =>
      html`<i class="${q === 0 ? "a" : q === 1 ? "b" : ""}"></i>`)}</div>
    <div class="duelos">${FILAS_DUELO.map(([clave, etiqueta]) => {
      const [va, vb] = cara[clave];
      const parteA = va + vb ? (va / (va + vb)) * 100 : 50;
      return html`<div class="duelo">
        <b>${numero(va)}</b>
        <span class="bar izq"><i style="width:${parteA}%;background:var(--eq)"></i></span>
        <span class="muted">${etiqueta}</span>
        <span class="bar"><i style="width:${100 - parteA}%"></i></span>
        <b class="der">${numero(vb)}</b>
      </div>`;
    })}</div>
    <h3 class="mes">CARRERA POR CARRERA</h3>
    <div class="filas-cab"><span>GP</span><span>${sigla(cara.a)}</span><span>${sigla(cara.b)}</span></div>
    <div class="filas">${filasCaraACara(cara, comun).map((f) => html`<a class="carrera-fila" href="#/gp/${anio}/${f.ronda}">
      <span class="ronda mono">R${f.ronda}</span>${bandera(f.bandera)}
      <span class="nombre"><b>${f.gp}</b></span>
      <span class="${f.a.gana ? "caja mono gana" : "caja mono"}">${f.a.texto}</span><span class="${f.b.gana ? "caja mono gana" : "caja mono"}">${f.b.texto}</span>
    </a>`)}</div>`;
}

export function armarFichaEquipo(e, comun, anio) {
  const cara = e.cara_a_cara;
  const color = comun.colores[e.constructor_id] ?? "var(--dato)";
  // El auto es el de este año: en otras temporadas no va.
  const auto = anio === comun.anio_actual ? comun.autos?.[e.constructor_id] : null;
  return html`<div class="banda" style="--eq:${color}" aria-hidden="true">
      ${armarLogo(e, comun, "avatar chico cuadrado")}<span class="banda-texto"><small>CONSTRUCTORES ${anio}</small><b>${e.nombre}</b></span>
    </div>
    <section class="portada equipo" style="--eq:${color}">
      <div class="portada-texto">
        <span class="eti">CONSTRUCTORES ${anio}</span>
        <h2>${e.nombre}</h2>
        ${cara ? html`<span class="sec meta">${cara.a.apellido} · ${cara.b.apellido}</span>` : ""}
      </div>
      ${armarLogo(e, comun, "logo-portada")}
      ${auto ? html`<img class="auto" src="${auto}" alt="" onerror="this.remove()">` : ""}
    </section>
    <div class="cuerpo" style="--eq:${color}">
      <div class="grandes cuatro">
        <div><small>POSICIÓN</small><b>${e.posicion ? `${e.posicion}º` : "—"}</b></div>
        <div><small>PUNTOS</small><b>${numero(e.puntos)}</b></div>
        <div><small>VICTORIAS</small><b>${e.stats.victorias}</b></div>
        <div><small>DOBLETES</small><b>${e.stats.dobletes}</b></div>
      </div>
      <h3 class="mes">CARA A CARA · QUIÉN TERMINÓ ADELANTE</h3>
      ${cara ? armarDuelo(cara, color, comun, anio) : html`<p class="muted">Este equipo no tuvo dos pilotos en una misma carrera.</p>`}
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

export function montar(main) {
  cargarFotos(main);
  return comprimirAlBajar(main);
}
