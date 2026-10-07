// Router por hash: así el botón "atrás" de Android funciona solo. Cada vista
// de vistas/ exporta encabezado(ruta), render(ruta, comun) y, si hace falta,
// montar(main, ruta, comun) y capa(main, ruta, comun).
import { html } from "./html.js";
import { ANIO_MIN, aEvento, hayEnVivo, parsearRuta, pestanaDe, rutaConAnio } from "./formato.js";
import { calendario as pedirCalendario, comun as pedirComun } from "./api.js";
import * as calendario from "./vistas/calendario.js";
import * as detalle from "./vistas/detalle.js";
import * as clasificacion from "./vistas/clasificacion.js";
import * as pilotos from "./vistas/pilotos.js";
import * as fichaPiloto from "./vistas/ficha_piloto.js";
import * as fichaEquipo from "./vistas/ficha_equipo.js";

const VISTAS = { calendario, gp: detalle, clasificacion, pilotos, piloto: fichaPiloto, equipo: fichaEquipo };

const ICONO_ATRAS = html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>`;
const ICONO_ANTERIOR = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>`;
const ICONO_SIGUIENTE = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>`;

// Si los datos tardan más de 150 ms, un esqueleto; si ya estaban en caché, se
// pasa directo y no parpadea.
const ESPERA_ESQUELETO_MS = 150;
const ESQUELETO = html`<div class="cuerpo esqueleto" aria-busy="true" aria-label="Cargando">
  <span class="sk bloque"></span>${Array.from({ length: 6 }, () => html`<span class="sk renglon"></span>`)}</div>`;

// Transición nativa de Chrome: la tarjeta tocada de la grilla se expande hasta
// la portada de la ficha (comparten view-transition-name). Sin soporte,
// cambio directo.
const transicion = (cambio) => (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches
  ? document.startViewTransition(cambio)
  : cambio());

const encabezado = document.getElementById("encabezado");
const main = document.getElementById("contenido");
let actual = null;   // { ruta, limpiar }
let turno = 0;       // si el usuario navega mientras carga, lo viejo se descarta

function armarEncabezado(ruta, info, anioActual) {
  if (info.volver) {
    return html`<button class="icono-btn" data-atras="${info.volver}" aria-label="Volver">${ICONO_ATRAS}</button>
      <h1 class="chico">${info.titulo}</h1><span class="muted anio">${ruta.anio}</span>`;
  }
  return html`<h1>${info.titulo}</h1>
    <div class="temporada">
      <a href="${rutaConAnio(ruta, ruta.anio - 1)}" class="${ruta.anio <= ANIO_MIN ? "oculto" : ""}" aria-label="Temporada anterior">${ICONO_ANTERIOR}</a>
      <span>${ruta.anio}</span>
      <a href="${rutaConAnio(ruta, ruta.anio + 1)}" class="${ruta.anio >= anioActual ? "oculto" : ""}" aria-label="Temporada siguiente">${ICONO_SIGUIENTE}</a>
    </div>`;
}

function marcarPestana(ruta) {
  const pestana = pestanaDe(ruta.vista);
  for (const a of document.querySelectorAll(".tabbar a")) {
    a.classList.toggle("activa", a.dataset.pestana === pestana);
    a.href = `#/${a.dataset.pestana}/${ruta.anio}`;
  }
  const pestanas = [...document.querySelectorAll(".tabbar a")];
  document.querySelector(".tabbar").style.setProperty("--i", pestanas.findIndex((a) => a.dataset.pestana === pestana));
}

const mismaPagina = (a, b) => a && a.vista === b.vista && a.anio === b.anio
  && a.ronda === b.ronda && a.id === b.id && a.solapa === b.solapa;

function mostrarError(mio) {
  if (mio !== turno) return;
  // Sin esto, "Reintentar" en un GP se tomaba como un cambio de capa y no
  // volvía a renderizar nada.
  actual = null;
  main.innerHTML = html`<div class="estado error"><p>No se pudo cargar. Revisá la conexión.</p>
    <button class="boton" data-reintentar>Reintentar</button></div>`;
}

async function mostrar() {
  const mio = ++turno;
  let datosComunes;
  try {
    datosComunes = await pedirComun();
  } catch {
    mostrarError(mio);
    return;
  }
  if (mio !== turno) return;
  const ruta = parsearRuta(location.hash, datosComunes.anio_actual);
  const vista = VISTAS[ruta.vista];

  // Sólo se abrió o se cerró una capa (hoja del circuito, mapa): no se vuelve
  // a renderizar, así no se pierde el scroll.
  if (vista.capa && mismaPagina(actual?.ruta, ruta)) {
    actual.ruta = ruta;
    vista.capa(main, ruta, datosComunes);
    return;
  }

  actual?.limpiar?.();
  actual = { ruta };
  marcarPestana(ruta);
  const pintarEncabezado = () => {
    encabezado.innerHTML = armarEncabezado(ruta, vista.encabezado(ruta), datosComunes.anio_actual);
  };
  const espera = setTimeout(() => {
    if (mio !== turno) return;
    pintarEncabezado();
    main.innerHTML = ESQUELETO;
    window.scrollTo(0, 0);
  }, ESPERA_ESQUELETO_MS);
  try {
    const contenido = await vista.render(ruta, datosComunes);
    clearTimeout(espera);
    if (mio !== turno) return;
    transicion(() => {
      if (mio !== turno) return;
      pintarEncabezado();
      main.innerHTML = contenido;
      window.scrollTo(0, 0);
      actual.limpiar = vista.montar?.(main, ruta, datosComunes);
    });
  } catch (error) {
    clearTimeout(espera);
    console.error(error);
    if (mio === turno) pintarEncabezado();
    mostrarError(mio);
  }
}

document.addEventListener("click", (evento) => {
  if (evento.target.closest(".tabbar a, .segmento a")) navigator.vibrate?.(8);
  // Sólo la tarjeta tocada lleva el nombre: con uno por tarjeta, la
  // transición dibujaría todas las fotos sin recortar.
  const tarjeta = evento.target.closest(".tpil");
  if (tarjeta) tarjeta.style.viewTransitionName = "portada";
  const atras = evento.target.closest("[data-atras]");
  if (atras) {
    // Dentro de la app, atrás vuelve a donde estaba (Clasificación, un GP…);
    // si la app se abrió directo en esta pantalla, va a la de arriba.
    if (history.length > 1) history.back();
    else location.hash = atras.dataset.atras;
    return;
  }
  if (evento.target.closest("[data-reintentar]")) mostrar();
});

window.addEventListener("hashchange", mostrar);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");

// Punto rojo en Calendario mientras se corre una sesión, mire la pestaña que
// mire. Si falla la red, simplemente no hay punto.
async function vigilarEnVivo() {
  try {
    const datosComunes = await pedirComun();
    const eventos = (await pedirCalendario(datosComunes.anio_actual)).map((r) => aEvento(r, datosComunes));
    const pestana = document.querySelector('.tabbar [data-pestana="calendario"]');
    const marcar = () => pestana.classList.toggle("vivo", hayEnVivo(eventos, Date.now()));
    marcar();
    setInterval(marcar, 30_000);
  } catch {
    // sin conexión: sin punto
  }
}
vigilarEnVivo();

const sinRed = document.getElementById("sin-red");
const marcarRed = () => { sinRed.hidden = navigator.onLine; };
window.addEventListener("online", marcarRed);
window.addEventListener("offline", marcarRed);
marcarRed();
mostrar();
