// Router por hash: así el botón "atrás" de Android funciona solo. Cada vista
// de vistas/ exporta encabezado(ruta), render(ruta, comun) y, si hace falta,
// montar(main, ruta, comun) y capa(main, ruta, comun).
import { html } from "./html.js";
import { ANIO_MIN, aEvento, hayEnVivo, parsearRuta, pestanaDe, rutaConAnio } from "./formato.js";
import { calendario as pedirCalendario, comun as pedirComun } from "./api.js";
import { suscribir } from "./avisos.js";
import { abrirBuscador, cerrarBuscador } from "./buscador.js";
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

const ICONO_CAMPANA = html`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`;

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
let comunActual = null;   // comun.json de la última pantalla, para el buscador y los atajos

function armarEncabezado(ruta, info, anioActual) {
  if (info.volver) {
    return html`<button class="icono-btn" data-atras="${info.volver}" aria-label="Volver">${ICONO_ATRAS}</button>
      <h1 class="chico">${info.titulo}</h1><span class="muted anio">${ruta.anio}</span>`;
  }
  return html`<h1>${info.titulo}</h1>
    ${info.campana ? html`<button class="icono-btn campana" data-campana aria-label="Avisos antes de cada sesión">${ICONO_CAMPANA}</button>` : ""}
    <div class="temporada">
      <a href="${rutaConAnio(ruta, ruta.anio - 1)}" class="${ruta.anio <= ANIO_MIN ? "oculto" : ""}" aria-label="Temporada anterior">${ICONO_ANTERIOR}</a>
      <span>${ruta.anio}</span>
      <a href="${rutaConAnio(ruta, ruta.anio + 1)}" class="${ruta.anio >= anioActual ? "oculto" : ""}" aria-label="Temporada siguiente">${ICONO_SIGUIENTE}</a>
    </div>`;
}

// La sección de primer nivel de una ruta: la ficha de un equipo vuelve a
// Pilotos › Equipos, un GP al Calendario.
const rutaDePestana = (ruta) => ({
  vista: pestanaDe(ruta.vista),
  solapa: ruta.vista === "equipo" ? "equipos" : ruta.vista === "piloto" ? "pilotos" : ruta.solapa,
});

// Año de la ruta pedida corrido `paso` temporadas, o null si se pasa de rango.
function otroAnio(ruta, paso, anioActual) {
  const anio = ruta.anio + paso;
  return anio >= ANIO_MIN && anio <= anioActual ? rutaConAnio(rutaDePestana(ruta), anio) : null;
}

function marcarPestana(ruta, anioActual) {
  const pestana = pestanaDe(ruta.vista);
  const pestanas = [...document.querySelectorAll(".tabbar [data-pestana]")];
  for (const a of pestanas) {
    a.classList.toggle("activa", a.dataset.pestana === pestana);
    a.href = `#/${a.dataset.pestana}/${ruta.anio}`;
  }
  document.querySelector(".tabbar").style.setProperty("--i", pestanas.findIndex((a) => a.dataset.pestana === pestana));
  // Selector de temporada de la barra lateral (sólo se ve en la PC).
  const anterior = otroAnio(ruta, -1, anioActual);
  const siguiente = otroAnio(ruta, 1, anioActual);
  document.getElementById("lat-anio").innerHTML = html`<div class="temporada">
    <a href="${anterior ?? "#"}" class="${anterior ? "" : "oculto"}" aria-label="Temporada anterior">${ICONO_ANTERIOR}</a>
    <span>${ruta.anio}</span>
    <a href="${siguiente ?? "#"}" class="${siguiente ? "" : "oculto"}" aria-label="Temporada siguiente">${ICONO_SIGUIENTE}</a>
  </div>`;
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
  comunActual = datosComunes;
  cerrarBuscador();
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
  marcarPestana(ruta, datosComunes.anio_actual);
  const pintarEncabezado = () => {
    encabezado.innerHTML = armarEncabezado(ruta, vista.encabezado(ruta), datosComunes.anio_actual);
    // Campana en cian si este celular ya está suscripto.
    const campana = encabezado.querySelector("[data-campana]");
    navigator.serviceWorker?.ready.then((r) => r.pushManager?.getSubscription())
      .then((s) => campana?.classList.toggle("activa", Boolean(s))).catch(() => {});
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

function cerrarAvisos() {
  const capa = document.querySelector(".capa-avisos");
  if (!capa) return;
  capa.remove();
  document.body.classList.remove("con-capa");
}

// Hoja con la suscripción para copiar como secreto del repo.
async function abrirAvisos() {
  const r = await suscribir().catch((error) => ({ error: `No se pudo activar: ${error.message}` }));
  const capa = document.createElement("div");
  capa.className = "capa capa-avisos";
  capa.innerHTML = html`<div class="velo" data-cerrar-avisos></div><div class="hoja">
    <span class="asa"></span>
    <h3 class="titulo-circuito">Avisos antes de cada sesión</h3>
    ${r.error ? html`<p class="muted">${r.error}</p>` : html`<p class="muted">Copiá este texto y pegalo en GitHub › Settings › Secrets and variables › Actions, como el secreto <b>PUSH_SUBSCRIPTION</b>. Se hace una sola vez.</p>
      <p class="muted nota">¿Otro celular? En el secreto van todos juntos, entre corchetes y separados por coma: <span class="mono">[texto1, texto2]</span>.</p>
      <textarea class="suscripcion mono" readonly rows="6">${r.texto}</textarea>
      <button class="boton" data-copiar>Copiar</button>`}
    <button class="boton" data-cerrar-avisos>Cerrar</button>
  </div>`;
  document.body.append(capa);
  document.body.classList.add("con-capa");
  // Una entrada en el historial: "atrás" de Android cierra la hoja (popstate).
  history.pushState({ avisos: true }, "");
  encabezado.querySelector("[data-campana]")?.classList.toggle("activa", !r.error);
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
  if (evento.target.closest("[data-campana]")) { abrirAvisos(); return; }
  if (evento.target.closest("[data-buscar]")) { buscar(); return; }
  if (evento.target.closest("[data-cerrar-avisos]")) {
    history.back();   // saca la entrada de la hoja; popstate la cierra
    return;
  }
  const copiar = evento.target.closest("[data-copiar]");
  if (copiar) {
    const texto = copiar.parentElement.querySelector("textarea");
    navigator.clipboard.writeText(texto.value)
      .then(() => { copiar.textContent = "Copiado ✓"; })
      .catch(() => { texto.select(); copiar.textContent = "Copialo a mano"; });
    return;
  }
  if (evento.target.closest("[data-reintentar]")) mostrar();
});

function buscar() {
  if (comunActual && actual) abrirBuscador(actual.ruta.anio, comunActual);
}

// Atajos de la app de escritorio (main.py): ← → cambian de temporada, Esc
// vuelve; más Ctrl+K para el buscador. En el celular no hay teclado: no molestan.
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    buscar();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || !actual || !comunActual) return;
  if (e.key === "Escape") {
    if (document.querySelector(".capa-buscar")) { cerrarBuscador(); return; }
    // Lo de más arriba primero: la hoja de avisos, una capa, el "volver".
    const cerrar = document.querySelector("[data-cerrar-avisos], .capa [data-atras], #encabezado [data-atras]");
    if (cerrar) cerrar.click();
    else if (actual.ruta.vista !== "calendario") location.hash = `#/calendario/${actual.ruta.anio}`;
    return;
  }
  if (e.target.closest("input, textarea, select") || document.querySelector(".capa")) return;
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    const destino = otroAnio(actual.ruta, e.key === "ArrowLeft" ? -1 : 1, comunActual.anio_actual);
    if (destino) location.hash = destino;
  }
});

// Carteles al apoyar el mouse sobre algo con data-tip (sólo PC): un único
// elemento fijo, así no lo recorta el overflow de las tarjetas.
const cartel = Object.assign(document.createElement("div"), { className: "cartel", hidden: true });
document.body.append(cartel);
if (matchMedia("(hover: hover)").matches) {
  document.addEventListener("mouseover", (e) => {
    const con = e.target.closest?.("[data-tip]");
    if (!con || !matchMedia("(min-width: 1024px)").matches) { cartel.hidden = true; return; }
    cartel.textContent = con.dataset.tip;
    cartel.hidden = false;
    const r = con.getBoundingClientRect();
    const ancho = cartel.offsetWidth;
    cartel.style.left = `${Math.min(innerWidth - ancho - 8, Math.max(8, r.left + r.width / 2 - ancho / 2))}px`;
    cartel.style.top = `${r.top - cartel.offsetHeight - 8 < 8 ? r.bottom + 8 : r.top - cartel.offsetHeight - 8}px`;
  });
  window.addEventListener("scroll", () => { cartel.hidden = true; }, { passive: true });
}

window.addEventListener("hashchange", mostrar);
window.addEventListener("popstate", cerrarAvisos);
// Sin service worker la app anda igual, sólo que sin modo offline ni avisos.
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(console.error);

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
    setTimeout(vigilarEnVivo, 60_000);   // sin conexión: sin punto, y se reintenta
  }
}
vigilarEnVivo();

const sinRed = document.getElementById("sin-red");
const marcarRed = () => { sinRed.hidden = navigator.onLine; };
window.addEventListener("online", marcarRed);
window.addEventListener("offline", marcarRed);
marcarRed();
mostrar();
