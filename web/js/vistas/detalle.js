import { html } from "../html.js";
import { aEvento, diaHora, formatoDiferencia, formatoVuelta } from "../formato.js";
import { calendario, ganadores, resultados, sesionOpenF1, temporada } from "../api.js";
import { FILAS_CORTAS, armarFicha, armarHoja, armarMapa } from "./capas.js";
import { filaResultado } from "./filas.js";
import { descargarIcs, nombreIcs } from "../ics.js";

export const encabezado = (ruta) => ({ titulo: "Calendario", volver: `#/calendario/${ruta.anio}` });

const puntos = (p) => (Number(p) === 1 ? "1 pt" : `${p} pts`);
const largo = (grid) => (grid === "0" ? "largó desde boxes" : `largó ${grid}º`);

export function armarResultadosJolpica(race, recurso, comun) {
  const comunes = (r) => ({
    pos: Number(r.position),
    color: comun.colores[r.Constructor.constructorId],
    nombre: `${r.Driver.givenName} ${r.Driver.familyName}`,
    href: `#/piloto/${race.season}/${r.Driver.driverId}`,
    tip: [r.number && `Nº ${r.number}`, comun.nacionalidades[r.Driver.nationality] ?? r.Driver.nationality]
      .filter(Boolean).join(" · "),
  });
  if (recurso === "qualifying") {
    return race.QualifyingResults.map((q) => filaResultado({
      ...comunes(q),
      sub: q.Constructor.name,
      dato: q.Q3 || q.Q2 || q.Q1 || "—",
      extra: q.Q3 ? "Q3" : q.Q2 ? "Q2" : q.Q1 ? "Q1" : "",
    }));
  }
  const filas = recurso === "sprint" ? race.SprintResults : race.Results;
  return filas.map((r) => filaResultado({
    ...comunes(r),
    sub: `${r.Constructor.name} · ${largo(r.grid)}`,
    // Sin tiempo (abandono o vueltas de menos), el estado. Jolpica a veces
    // manda Time con time vacío, por eso || y no ??.
    dato: r.Time?.time || r.status,
    extra: puntos(r.points),
  }));
}

// OpenF1 no tiene el driverId de Jolpica: la ficha se encuentra por la sigla
// entre los pilotos de la temporada (idsPorCodigo).
export function armarResultadosOpenF1({ resultados: filas, pilotos }, comun, idsPorCodigo, anio) {
  const porNumero = new Map(pilotos.map((p) => [p.driver_number, p]));
  return [...filas].sort((a, b) => (a.position ?? 99) - (b.position ?? 99)).map((r) => {
    const p = porNumero.get(r.driver_number) ?? {};
    const id = idsPorCodigo.get(p.name_acronym);
    // En las clasificaciones duration y gap vienen por Q: [Q1, Q2, Q3].
    const porQ = Array.isArray(r.duration);
    const mejor = porQ ? r.duration.filter(Boolean).at(-1) : r.duration;
    let dato = "—";
    if (mejor && (porQ || r.position === 1)) dato = formatoVuelta(mejor);
    else if (mejor) dato = typeof r.gap_to_leader === "number" ? formatoDiferencia(r.gap_to_leader) : r.gap_to_leader;
    return filaResultado({
      pos: r.position,
      color: p.team_colour ? `#${p.team_colour}` : null,
      nombre: p.first_name ? `${p.first_name} ${p.last_name}` : `#${r.driver_number}`,
      sub: p.team_name,
      dato,
      extra: porQ ? "" : `${r.number_of_laps} vueltas`,
      href: id ? `#/piloto/${anio}/${id}` : null,
    });
  });
}

export function armarPendiente(sesion, ahora) {
  const etiqueta = html`<span class="eti">${sesion.nombre.toUpperCase()}</span>`;
  if (sesion.fecha > ahora) {
    return html`<div class="estado">${etiqueta}<h3>Todavía no se corrió</h3><p>${diaHora(sesion.fecha)} · hora local</p></div>`;
  }
  return html`<div class="estado">${etiqueta}<h3>Sin resultados</h3><p>${sesion.openf1
    ? "Los resultados de los entrenamientos y de la clasificación sprint están desde 2023."
    : "Todavía no hay resultados publicados para esta sesión."}</p></div>`;
}

const errorSesion = () => html`<div class="estado error"><p>No se pudo cargar. Revisá la conexión.</p></div>`;

export const sesionInicial = (ev, ahora) => ev.sesiones.filter((s) => s.fecha <= ahora).at(-1) ?? ev.sesiones[0];

async function armarSesion(ev, sesion, comun) {
  const ahora = Date.now();
  if (sesion.fecha > ahora) return armarPendiente(sesion, ahora);
  let filas = [];
  if (sesion.jolpica) {
    const race = await resultados(ev.anio, ev.ronda, sesion.jolpica);
    if (race) filas = armarResultadosJolpica(race, sesion.jolpica, comun);
  } else if (ev.anio >= 2023) {
    const datos = await sesionOpenF1(ev.anio, sesion.openf1, sesion.dia);
    if (datos?.resultados.length) {
      const deLaTemporada = await temporada(ev.anio, comun).catch(() => null);
      const ids = new Map((deLaTemporada?.pilotos ?? []).map((p) => [p.codigo, p.driver_id]));
      filas = armarResultadosOpenF1(datos, comun, ids, ev.anio);
    }
  }
  return filas.length ? html`<div class="res">${filas}</div>` : armarPendiente(sesion, ahora);
}

export function armarCircuito(ev, comun) {
  const datos = comun.circuitos[ev.circuitId];
  const base = `#/gp/${ev.anio}/${ev.ronda}`;
  return html`<h3 class="mes">CIRCUITO</h3>
    <div class="panel">
      ${datos?.mapa ? html`<a href="${base}/mapa" aria-label="Ver el mapa en grande"><img class="mapa" src="mapas/${ev.circuitId}.png" alt="Trazado de ${ev.circuito}"></a>` : ""}
      <p class="titulo-circuito">${datos?.nombre_completo ?? ev.circuito}</p>
      ${datos ? html`${armarFicha(datos, FILAS_CORTAS)}<a class="boton" href="${base}/circuito">Más datos y ganadores</a>` : ""}
    </div>`;
}

// En la PC .detalle es una grilla: resultados a la izquierda y el circuito a
// la derecha, como la app de escritorio. En el celular no tiene estilos.
function armarDetalle(ev, activa, contenido, comun) {
  return html`<div class="detalle"><div class="cab">
      <span class="badge">R${ev.ronda}</span>
      <h2>${ev.nombre}</h2>
      <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    </div>
    <div class="chips" role="tablist">${ev.sesiones.map((s) => html`<button role="tab" data-sesion="${s.clave}"
      class="${s === activa ? "activa" : ""}" aria-selected="${s === activa}">${s.corto}<small>${diaHora(s.fecha).slice(0, 3)}</small></button>`)}</div>
    <button class="boton ics" type="button" data-ics>Agregar a mi calendario</button>
    <div id="sesion">${contenido}</div>
    <div class="cuerpo">${armarCircuito(ev, comun)}</div></div>`;
}

async function evento(ruta, comun) {
  const race = (await calendario(ruta.anio)).find((r) => Number(r.round) === ruta.ronda);
  if (!race) throw new Error(`No hay ronda ${ruta.ronda} en ${ruta.anio}`);
  return aEvento(race, comun);
}

export async function render(ruta, comun) {
  const ev = await evento(ruta, comun);
  const activa = sesionInicial(ev, Date.now());
  // Si falla la sesión (OpenF1 caído o limitando pedidos), el resto del
  // detalle se ve igual y los otros chips siguen andando.
  return armarDetalle(ev, activa, await armarSesion(ev, activa, comun).catch(errorSesion), comun);
}

export function montar(main, ruta, comun) {
  const chips = main.querySelector(".chips");
  let pedido = 0;   // si se tocan dos chips seguidos, gana el último
  chips.addEventListener("click", async (e) => {
    const boton = e.target.closest("[data-sesion]");
    if (!boton) return;
    for (const b of chips.children) {
      b.classList.toggle("activa", b === boton);
      b.setAttribute("aria-selected", String(b === boton));
    }
    const mio = ++pedido;
    const caja = main.querySelector("#sesion");
    caja.innerHTML = html`<p class="estado">Cargando…</p>`;
    const contenido = await evento(ruta, comun)
      .then((ev) => armarSesion(ev, ev.sesiones.find((s) => s.clave === boton.dataset.sesion), comun))
      .catch(errorSesion);
    if (mio === pedido) caja.innerHTML = contenido;
  });
  main.querySelector("[data-ics]")?.addEventListener("click", () => evento(ruta, comun)
    .then((ev) => descargarIcs([ev], nombreIcs(ev.anio, ev.nombre))).catch(() => {}));
  const soltarZoom = matchMedia("(min-width: 1024px)").matches ? zoomMapa(main) : null;
  capa(main, ruta, comun);
  return () => {
    soltarZoom?.();
    document.body.classList.remove("con-capa");
  };
}

// En la PC el mapa del panel no abre la capa: se amplía ahí mismo con la
// rueda (hacia el cursor) y se mueve arrastrándolo.
// ponytail: se decide al montar; si se achica la ventana sigue siendo visor
// hasta la próxima pantalla.
const ZOOM_MAX = 6;
function zoomMapa(main) {
  const link = main.querySelector(".panel a:has(> .mapa)");
  if (!link) return null;
  const visor = document.createElement("div");
  visor.className = "visor";
  visor.innerHTML = html`<div class="controles">
      <button type="button" data-zoom="1.4" aria-label="Acercar">+</button>
      <button type="button" data-zoom="0.714" aria-label="Alejar">−</button>
      <button type="button" data-zoom="0" aria-label="Tamaño original">⟲</button>
    </div><span class="zoom-txt mono">100%</span>`;
  const img = link.querySelector(".mapa");
  visor.prepend(img);
  link.replaceWith(visor);
  const texto = visor.querySelector(".zoom-txt");
  let escala = 1, x = 0, y = 0, arrastre = null;
  const aplicar = () => {
    if (escala === 1) { x = 0; y = 0; }
    img.style.transform = `translate(${x}px, ${y}px) scale(${escala})`;
    texto.textContent = `${Math.round(escala * 100)}%`;
    visor.classList.toggle("ampliado", escala > 1);
  };
  // Zoom manteniendo fijo el punto (cx, cy), medido desde el centro del visor.
  const zoom = (factor, cx = 0, cy = 0) => {
    const nueva = Math.min(ZOOM_MAX, Math.max(1, escala * factor));
    x = cx - (cx - x) * (nueva / escala);
    y = cy - (cy - y) * (nueva / escala);
    escala = nueva;
    aplicar();
  };
  visor.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = visor.getBoundingClientRect();
    zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2);
  }, { passive: false });
  visor.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-zoom]");
    if (!boton) return;
    if (boton.dataset.zoom === "0") { escala = 1; aplicar(); } else zoom(Number(boton.dataset.zoom));
  });
  visor.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button") || escala === 1) return;
    arrastre = { px: e.clientX, py: e.clientY, x, y };
    visor.setPointerCapture(e.pointerId);
    visor.classList.add("arrastrando");
  });
  visor.addEventListener("pointermove", (e) => {
    if (!arrastre) return;
    x = arrastre.x + e.clientX - arrastre.px;
    y = arrastre.y + e.clientY - arrastre.py;
    aplicar();
  });
  const soltar = () => { arrastre = null; visor.classList.remove("arrastrando"); };
  visor.addEventListener("pointerup", soltar);
  visor.addEventListener("pointercancel", soltar);
  return soltar;
}

export async function capa(main, ruta, comun) {
  main.querySelector(".capa")?.remove();
  document.body.classList.toggle("con-capa", Boolean(ruta.capa));
  if (!ruta.capa) return;
  const hash = location.hash;
  let ev;
  try {
    ev = await evento(ruta, comun);
  } catch {
    // Sin red: la capa no se abre, pero la página no queda trabada sin scroll.
    document.body.classList.remove("con-capa");
    return;
  }
  const contenido = ruta.capa === "mapa"
    ? armarMapa(ev)
    : armarHoja(ev, comun.circuitos[ev.circuitId], (await ganadores().catch(() => ({})))[ev.circuitId]);
  if (location.hash !== hash) return;   // se cerró mientras cargaba
  main.insertAdjacentHTML("beforeend", String(contenido));
}
