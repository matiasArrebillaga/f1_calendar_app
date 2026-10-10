// Buscador (Ctrl+K): salta a un GP, piloto, equipo o temporada escribiendo.
// Busca en la temporada que se está mirando y, para pilotos y equipos de
// otros años, en datos/indice.json (lleva a su última temporada).
import { html } from "./html.js";
import { ANIO_MIN, aEvento } from "./formato.js";
import { calendario, indiceHistorico, temporada } from "./api.js";

const MAX_RESULTADOS = 8;
const plano = (texto) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// Ítems: { texto, sub, tipo, href }. Lo de la temporada primero; los
// históricos sólo si no están ya en ella.
export function armarIndice({ eventos = [], datos = null, historico = null, anio, anioActual }) {
  const items = eventos.map((ev) => ({
    texto: ev.nombre, sub: `R${ev.ronda} · ${ev.rango}`, tipo: `GP ${anio}`, href: `#/gp/${anio}/${ev.ronda}`,
  }));
  const pilotos = new Set();
  const equipos = new Set();
  for (const p of datos?.pilotos ?? []) {
    pilotos.add(p.driver_id);
    items.push({ texto: `${p.nombre} ${p.apellido}`, sub: p.equipo, tipo: "Piloto", href: `#/piloto/${anio}/${p.driver_id}` });
  }
  for (const e of datos?.equipos ?? []) {
    equipos.add(e.constructor_id);
    items.push({ texto: e.nombre, sub: `Temporada ${anio}`, tipo: "Equipo", href: `#/equipo/${anio}/${e.constructor_id}` });
  }
  for (let a = anioActual; a >= ANIO_MIN; a--) {
    items.push({ texto: `Temporada ${a}`, sub: "Calendario", tipo: "Temporada", href: `#/calendario/${a}`, clave: String(a) });
  }
  for (const p of historico?.pilotos ?? []) {
    if (!pilotos.has(p.id)) items.push({ texto: p.nombre, sub: `Última temporada: ${p.anio}`, tipo: "Piloto", href: `#/piloto/${p.anio}/${p.id}` });
  }
  for (const e of historico?.equipos ?? []) {
    if (!equipos.has(e.id)) items.push({ texto: e.nombre, sub: `Última temporada: ${e.anio}`, tipo: "Equipo", href: `#/equipo/${e.anio}/${e.id}` });
  }
  return items;
}

// Todas las palabras tienen que estar; primero los que tienen una palabra que
// empieza con lo escrito ("ham" → Hamilton antes que Graham Hill).
export function filtrar(items, consulta) {
  const palabras = plano(consulta).split(/\s+/).filter(Boolean);
  if (!palabras.length) return items.slice(0, MAX_RESULTADOS);
  const puntuados = [];
  for (const item of items) {
    const texto = plano(`${item.texto} ${item.clave ?? ""}`);
    if (!palabras.every((p) => texto.includes(p))) continue;
    const alInicio = palabras.every((p) => texto.split(/[\s-]+/).some((w) => w.startsWith(p)));
    puntuados.push({ item, puntos: alInicio ? 0 : 1 });
  }
  // sort es estable: a igual puntaje queda el orden del índice.
  return puntuados.sort((a, b) => a.puntos - b.puntos).slice(0, MAX_RESULTADOS).map((p) => p.item);
}

const fila = (item, i, elegida) => html`<a class="rk ${i === elegida ? "sel" : ""}" href="${item.href}" role="option"
  aria-selected="${i === elegida}" data-i="${i}"><span class="nombre"><b>${item.texto}</b><small>${item.sub}</small></span>
  <span class="eti">${item.tipo}</span></a>`;

let abierto = null;   // la capa, para no abrir dos

export function cerrarBuscador() {
  abierto?.remove();
  abierto = null;
}

export async function abrirBuscador(anio, comun) {
  if (abierto) return;
  const capa = document.createElement("div");
  capa.className = "capa capa-buscar";
  capa.innerHTML = html`<div class="velo" data-cerrar-buscar></div>
    <div class="paleta" role="dialog" aria-label="Buscar">
      <input type="search" placeholder="Buscar GP, piloto, equipo o temporada…" aria-label="Buscar" autocomplete="off" spellcheck="false">
      <div class="lista-k" role="listbox"><p class="vacio-k">Cargando…</p></div>
      <p class="pie-k"><span><kbd>↑</kbd> <kbd>↓</kbd> elegir</span><span><kbd>Enter</kbd> ir</span><span><kbd>Esc</kbd> cerrar</span></p>
    </div>`;
  document.body.append(capa);
  abierto = capa;
  const entrada = capa.querySelector("input");
  const lista = capa.querySelector(".lista-k");
  entrada.focus();

  const [races, datos, historico] = await Promise.all([
    calendario(anio).catch(() => []),
    temporada(anio, comun).catch(() => null),
    indiceHistorico().catch(() => null),
  ]);
  const items = armarIndice({
    eventos: races.map((r) => aEvento(r, comun)), datos, historico, anio, anioActual: comun.anio_actual,
  });
  let resultados = [];
  let elegida = 0;
  const pintar = () => {
    lista.innerHTML = resultados.length
      ? resultados.map((item, i) => fila(item, i, elegida)).join("")
      : html`<p class="vacio-k">Nada con "${entrada.value}"</p>`;
    lista.querySelector(".sel")?.scrollIntoView({ block: "nearest" });
  };
  const buscar = () => {
    resultados = filtrar(items, entrada.value);
    elegida = 0;
    pintar();
  };
  entrada.addEventListener("input", buscar);
  entrada.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!resultados.length) return;
      elegida = (elegida + (e.key === "ArrowDown" ? 1 : -1) + resultados.length) % resultados.length;
      pintar();
    } else if (e.key === "Enter" && resultados[elegida]) {
      location.hash = resultados[elegida].href;
      cerrarBuscador();
    }
  });
  lista.addEventListener("mousemove", (e) => {
    const i = Number(e.target.closest(".rk")?.dataset.i ?? elegida);
    if (i !== elegida) { elegida = i; pintar(); }
  });
  lista.addEventListener("click", (e) => { if (e.target.closest(".rk")) cerrarBuscador(); });
  capa.querySelector("[data-cerrar-buscar]").addEventListener("click", cerrarBuscador);
  buscar();
}
