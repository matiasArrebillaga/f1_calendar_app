import { html } from "../html.js";
import { MESES, aEvento, cuentaRegresiva, diaHora, indiceProxima } from "../formato.js";
import { calendario } from "../api.js";

export const encabezado = () => ({ titulo: "Calendario" });

const bandera = (codigo) =>
  codigo ? html`<img class="bandera" src="https://flagcdn.com/w40/${codigo}.png" alt="" loading="lazy">` : "";

function armarProxima(ev, ahora) {
  const c = cuentaRegresiva(ev.largada, ahora);
  return html`<a class="hero" href="#/gp/${ev.anio}/${ev.ronda}" data-largada="${ev.largada.getTime()}" data-ronda="${ev.ronda}">
    <div class="fila"><span class="chip" data-chip>${c.enCurso ? "EN CURSO" : "PRÓXIMA"} · R${ev.ronda}</span>${bandera(ev.bandera)}</div>
    <h2>${ev.nombre}</h2>
    <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    <div class="cuenta">
      <div><b data-dias>${c.dias}</b><small>DÍAS</small></div>
      <div><b data-horas>${c.horas}</b><small>HORAS</small></div>
      <div><b data-minutos>${c.minutos}</b><small>MIN</small></div>
    </div>
    <h3 class="eti">HORARIOS · HORA LOCAL</h3>
    <dl class="horarios">${ev.sesiones.map((s) =>
      html`<dt class="${s.clave === "Race" ? "carrera" : ""}">${s.nombre}</dt><dd>${diaHora(s.fecha)}</dd>`)}</dl>
  </a>`;
}

function armarTarjeta(ev, estado) {
  return html`<a class="tarjeta ${estado}" href="#/gp/${ev.anio}/${ev.ronda}">
    <div class="fila"><span class="eti">R${ev.ronda}</span>${estado === "proxima" ? html`<span class="chip">PRÓXIMA</span>` : ""}${bandera(ev.bandera)}</div>
    <h4>${ev.nombre}</h4>
    <span class="fecha">${ev.rango}</span>
  </a>`;
}

// Agrupadas por el mes de la carrera, como el grid de escritorio.
function armarMeses(eventos, estadoDe) {
  const grupos = [];
  for (const ev of eventos) {
    const mes = ev.largada.getMonth();
    if (grupos.at(-1)?.mes !== mes) grupos.push({ mes, eventos: [] });
    grupos.at(-1).eventos.push(ev);
  }
  return grupos.map((g) => html`<h3 class="mes">${MESES[g.mes]}</h3>
    <div class="lista">${g.eventos.map((ev) => armarTarjeta(ev, estadoDe(ev)))}</div>`);
}

export function armarCalendario(eventos, ahora) {
  if (!eventos.length) {
    return html`<div class="estado"><h3>Sin calendario</h3><p>No hay carreras publicadas para esta temporada.</p></div>`;
  }
  const i = indiceProxima(eventos, ahora);
  const estadoDe = (ev) => (ev === eventos[i] ? "proxima" : ev.largada < ahora ? "pasado" : "futuro");
  // Plegar las corridas sólo tiene sentido con una próxima: en un año
  // terminado todas son "anteriores".
  const corridas = i > 0 ? eventos.slice(0, i) : [];
  const siguientes = i > 0 ? eventos.slice(i) : eventos;
  return html`<div class="cuerpo">
    ${i >= 0 ? armarProxima(eventos[i], ahora) : ""}
    ${corridas.length ? html`<details class="plegado"><summary>Carreras anteriores · ${corridas.length}</summary>${armarMeses(corridas, estadoDe)}</details>` : ""}
    ${armarMeses(siguientes, estadoDe)}
  </div>`;
}

export async function render(ruta, comun) {
  const eventos = (await calendario(ruta.anio)).map((race) => aEvento(race, comun));
  return armarCalendario(eventos, Date.now());
}

// La cuenta regresiva se refresca cada 30 s, como el QTimer de escritorio.
export function montar(main) {
  const hero = main.querySelector("[data-largada]");
  if (!hero) return undefined;
  const largada = Number(hero.dataset.largada);
  const actualizar = () => {
    const c = cuentaRegresiva(largada, Date.now());
    hero.querySelector("[data-dias]").textContent = c.dias;
    hero.querySelector("[data-horas]").textContent = c.horas;
    hero.querySelector("[data-minutos]").textContent = c.minutos;
    hero.querySelector("[data-chip]").textContent = `${c.enCurso ? "EN CURSO" : "PRÓXIMA"} · R${hero.dataset.ronda}`;
  };
  const id = setInterval(actualizar, 30_000);
  return () => clearInterval(id);
}
