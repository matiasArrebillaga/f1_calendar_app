import { html } from "../html.js";
import { aEvento, diaHora, formatoDiferencia, formatoVuelta } from "../formato.js";
import { calendario, ganadores, resultados, sesionOpenF1, temporada } from "../api.js";
import { FILAS_CORTAS, armarFicha, armarHoja, armarMapa } from "./capas.js";
import { filaResultado } from "./filas.js";

export const encabezado = (ruta) => ({ titulo: "Calendario", volver: `#/calendario/${ruta.anio}` });

const puntos = (p) => (Number(p) === 1 ? "1 pt" : `${p} pts`);
const largo = (grid) => (grid === "0" ? "largó desde boxes" : `largó ${grid}º`);

export function armarResultadosJolpica(race, recurso, comun) {
  const comunes = (r) => ({
    pos: Number(r.position),
    color: comun.colores[r.Constructor.constructorId],
    nombre: `${r.Driver.givenName} ${r.Driver.familyName}`,
    href: `#/piloto/${race.season}/${r.Driver.driverId}`,
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

function armarDetalle(ev, activa, contenido, comun) {
  return html`<div class="cab">
      <span class="badge">R${ev.ronda}</span>
      <h2>${ev.nombre}</h2>
      <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    </div>
    <div class="chips" role="tablist">${ev.sesiones.map((s) => html`<button role="tab" data-sesion="${s.clave}"
      class="${s === activa ? "activa" : ""}" aria-selected="${s === activa}">${s.corto}<small>${diaHora(s.fecha).slice(0, 3)}</small></button>`)}</div>
    <div id="sesion">${contenido}</div>
    <div class="cuerpo">${armarCircuito(ev, comun)}</div>`;
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
  capa(main, ruta, comun);
  return () => document.body.classList.remove("con-capa");
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
