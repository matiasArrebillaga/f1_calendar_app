import { html } from "../html.js";
import { MESES, aEvento, cuentaRegresiva, diaHora, estadoSesiones, gpCorto, indiceProxima, sigla } from "../formato.js";
import { calendario, temporada } from "../api.js";
import { bandera } from "./filas.js";

export const encabezado = () => ({ titulo: "Calendario", campana: true });

const DIA_MS = 86_400_000;
let proximaEnPantalla = null;   // la que dibujó el último render, para refrescarla
let eventosEnPantalla = [];

function armarProxima(ev, ahora) {
  const sesiones = estadoSesiones(ev.sesiones, ahora);
  const vivo = sesiones.find((s) => s.estado === "vivo");
  const c = cuentaRegresiva(ev.largada, ahora);
  const dato = (s) => (s.estado === "hecha" ? "✓ Resultados" : s.estado === "vivo" ? "EN VIVO" : diaHora(s.fecha));
  return html`<a class="hero ${vivo ? "en-vivo" : ""}" href="#/gp/${ev.anio}/${ev.ronda}" data-largada="${ev.largada.getTime()}">
    <div class="fila">${vivo
      ? html`<span class="chip vivo"><i class="punto"></i>EN VIVO · ${vivo.nombre.toUpperCase()}</span>`
      : html`<span class="chip">PRÓXIMA · R${ev.ronda}${ev.conSprint ? " · SPRINT" : ""}</span>`}${bandera(ev.bandera)}</div>
    <h2>${ev.nombre}</h2>
    <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    ${vivo
      ? html`<div class="avance"><i style="width:${Math.min(100, Math.round(vivo.avance * 100))}%"></i></div>
        <p class="muted nota">Empezó hace ${vivo.minutos} min</p>`
      : html`<div class="cuenta">
        <div><b>${c.dias}</b><small>DÍAS</small></div>
        <div><b>${c.horas}</b><small>HORAS</small></div>
        <div><b>${c.minutos}</b><small>MIN</small></div>
      </div>`}
    <h3 class="eti">HORARIOS · HORA LOCAL</h3>
    <dl class="horarios">${sesiones.map((s) =>
      html`<dt class="${s.clave === "Race" ? "carrera" : ""}">${s.nombre}</dt><dd class="${s.estado}">${dato(s)}</dd>`)}</dl>
  </a>`;
}

// Corrida: atenuada y con el ganador; futura: cuántos días faltan.
function armarFila(ev, estado, ganador, ahora) {
  const derecha = estado === "pasado"
    ? (ganador ? html`<span class="ganador mono"><i style="background:${ganador.color ?? "var(--futuro)"}"></i>${ganador.codigo}</span>` : "")
    : html`<span class="falta mono">en ${Math.max(1, Math.ceil((ev.largada - ahora) / DIA_MS))} d</span>`;
  return html`<a class="gp-fila ${estado}" href="#/gp/${ev.anio}/${ev.ronda}">
    <span class="ronda mono">R${ev.ronda}</span>${bandera(ev.bandera)}
    <span class="nombre"><b>${gpCorto(ev.nombre)}</b><small>${ev.rango}</small></span>${derecha}
  </a>`;
}

// Ronda → ganador, del JSON de la temporada (el que llegó 1º en su tira).
export function ganadoresPorRonda(datos, colores) {
  const ganadores = new Map();
  for (const p of datos?.pilotos ?? []) {
    for (const t of p.tira) {
      if (t.posicion === 1) ganadores.set(t.ronda, { codigo: sigla(p), color: colores[p.constructor_id] ?? null });
    }
  }
  return ganadores;
}

// Un solo listado por mes, como el grid de escritorio: lo corrido arriba, la
// próxima en su lugar y lo que viene abajo. Se abre parado en la próxima (montar).
export function armarCalendario(eventos, ahora, ganadores = new Map()) {
  if (!eventos.length) {
    return html`<div class="estado"><h3>Sin calendario</h3><p>No hay carreras publicadas para esta temporada.</p></div>`;
  }
  const i = indiceProxima(eventos, ahora);
  const estadoDe = (ev) => (ev === eventos[i] ? "proxima" : ev.largada < ahora ? "pasado" : "futuro");
  const grupos = [];
  for (const ev of eventos) {
    const mes = ev.largada.getMonth();
    if (grupos.at(-1)?.mes !== mes) grupos.push({ mes, eventos: [] });
    grupos.at(-1).eventos.push(ev);
  }
  const corridas = i > 0 ? i : 0;
  return html`<div class="cuerpo calendario">
    ${corridas ? html`<button class="pildora oculta" data-subir>↑ ${corridas} ${corridas === 1 ? "carrera corrida" : "carreras corridas"}</button>` : ""}
    ${grupos.map((g) => html`<h3 class="mes">${MESES[g.mes]}</h3>
      <div class="filas">${g.eventos.map((ev) => (estadoDe(ev) === "proxima"
        ? armarProxima(ev, ahora) : armarFila(ev, estadoDe(ev), ganadores.get(ev.ronda), ahora)))}</div>`)}
  </div>`;
}

export async function render(ruta, comun) {
  const [races, datos] = await Promise.all([
    calendario(ruta.anio),
    temporada(ruta.anio, comun).catch(() => null),   // sin ganadores, el calendario igual se ve
  ]);
  const eventos = races.map((race) => aEvento(race, comun));
  eventosEnPantalla = eventos;
  proximaEnPantalla = eventos[indiceProxima(eventos, Date.now())] ?? null;
  return armarCalendario(eventos, Date.now(), ganadoresPorRonda(datos, comun.colores));
}

export function montar(main) {
  const limpiezas = [];
  const hero = main.querySelector("[data-largada]");
  const ultimaCorrida = [...main.querySelectorAll(".gp-fila.pasado")].at(-1);
  const pildora = main.querySelector("[data-subir]");
  const alto = document.getElementById("encabezado").offsetHeight;
  if (hero && ultimaCorrida) {
    // Como escritorio: abre parado en la próxima; lo corrido queda arriba.
    // Asoma una franja de la última corrida, que es donde flota la píldora,
    // así no tapa la tarjeta.
    window.scrollTo(0, hero.getBoundingClientRect().top + window.scrollY - alto - 52);
  }
  if (pildora && ultimaCorrida) {
    // La píldora se ve mientras lo corrido quedó arriba, fuera de pantalla
    // (debajo del encabezado fijo también cuenta como fuera).
    const observador = new IntersectionObserver(([e]) =>
      pildora.classList.toggle("oculta", e.intersectionRatio === 1 || e.boundingClientRect.top > alto),
    { rootMargin: `-${alto}px 0px 0px 0px`, threshold: 1 });
    observador.observe(ultimaCorrida);
    pildora.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    limpiezas.push(() => observador.disconnect());
  }
  if (hero && proximaEnPantalla) {
    // Cada 30 s se redibuja la tarjeta: cuenta regresiva y estado en vivo.
    // Cuando la carrera termina, la próxima es otra: se redibuja todo.
    const ev = proximaEnPantalla;
    const id = setInterval(() => {
      if (eventosEnPantalla[indiceProxima(eventosEnPantalla, Date.now())] !== ev) {
        window.dispatchEvent(new HashChangeEvent("hashchange"));
        return;
      }
      main.querySelector("[data-largada]")?.replaceWith(
        document.createRange().createContextualFragment(String(armarProxima(ev, Date.now()))));
    }, 30_000);
    limpiezas.push(() => clearInterval(id));
  }
  return () => limpiezas.forEach((f) => f());
}
