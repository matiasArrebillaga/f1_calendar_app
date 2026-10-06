import { html } from "../html.js";
import { aEvento, enJuego, numero } from "../formato.js";
import { calendario, campeonato, temporada } from "../api.js";
import { filaResultado } from "./filas.js";

export const encabezado = () => ({ titulo: "Clasificación" });

export const normalizarPilotos = (lista, comun) => lista.map((s) => ({
  pos: Number(s.position) || null,
  id: s.Driver.driverId,
  nombre: `${s.Driver.givenName} ${s.Driver.familyName}`,
  corto: s.Driver.familyName,
  equipo: s.Constructors.map((c) => c.name).join(" / "),
  color: comun.colores[s.Constructors.at(-1)?.constructorId] ?? null,
  puntos: Number(s.points),
  victorias: Number(s.wins),
}));

export const normalizarEquipos = (lista, comun) => lista.map((s) => ({
  pos: Number(s.position) || null,
  id: s.Constructor.constructorId,
  nombre: s.Constructor.name,
  corto: s.Constructor.name,
  equipo: null,
  color: comun.colores[s.Constructor.constructorId] ?? null,
  puntos: Number(s.points),
  victorias: Number(s.wins),
}));

// Antes de 1958 no hay campeonato de constructores: la temporada exportada
// los arma sumando resultados (historial.equipos_temporada).
export const equiposDeTemporada = (equipos, comun) => equipos.map((e) => ({
  pos: e.posicion, id: e.constructor_id, nombre: e.nombre, corto: e.nombre, equipo: null,
  color: comun.colores[e.constructor_id] ?? null, puntos: e.puntos, victorias: e.victorias,
}));

const victorias = (n) => (n ? `${n} ${n === 1 ? "victoria" : "victorias"}` : "");

export function armarClasificacion({ filas, solapa, anio, tras, juego }) {
  const base = `#/clasificacion/${anio}`;
  const segmento = html`<div class="segmento">
    <a href="${base}" class="${solapa === "pilotos" ? "activa" : ""}">Pilotos</a>
    <a href="${base}/equipos" class="${solapa === "equipos" ? "activa" : ""}">Equipos</a>
  </div>`;
  if (!filas.length) {
    return html`${segmento}<div class="estado"><h3>Sin clasificación</h3><p>No hay clasificación disponible para ${anio}.</p></div>`;
  }
  const [lider, segundo] = filas;
  const tipo = solapa === "pilotos" ? "piloto" : "equipo";
  return html`${segmento}
    <div class="cuerpo">
      ${tras ? html`<p class="eti">${tras}</p>` : ""}
      <div class="kpis">
        <div class="kpi"><span class="eti">LÍDER</span><b class="txt">${lider.corto}</b><small>${numero(lider.puntos)} puntos</small></div>
        <div class="kpi"><span class="eti">VENTAJA</span><b>${segundo ? `+${numero(lider.puntos - segundo.puntos)}` : "—"}</b><small>${segundo ? `sobre ${segundo.corto}` : ""}</small></div>
        <div class="kpi"><span class="eti">EN JUEGO</span><b>${juego.valor}</b><small>${juego.detalle}</small></div>
      </div>
    </div>
    <div class="res">${filas.map((f) => filaResultado({
      pos: f.pos,
      color: f.color,
      nombre: f.nombre,
      sub: [f.equipo, victorias(f.victorias)].filter(Boolean).join(" · "),
      dato: numero(f.puntos),
      extra: f === lider ? "líder" : `−${numero(lider.puntos - f.puntos)}`,
      href: `#/${tipo}/${anio}/${f.id}`,
    }))}</div>`;
}

export async function render(ruta, comun) {
  const tipo = ruta.solapa === "pilotos" ? "driverStandings" : "constructorStandings";
  const [lista, races] = await Promise.all([campeonato(ruta.anio, tipo), calendario(ruta.anio)]);
  const eventos = races.map((race) => aEvento(race, comun));
  let filas = [];
  if (lista) {
    filas = ruta.solapa === "pilotos"
      ? normalizarPilotos(lista.DriverStandings, comun)
      : normalizarEquipos(lista.ConstructorStandings, comun);
  } else if (ruta.solapa === "equipos") {
    const deLaTemporada = await temporada(ruta.anio, comun).catch(() => null);
    filas = equiposDeTemporada(deLaTemporada?.equipos ?? [], comun);
  }
  const ronda = lista ? Number(lista.round) : null;
  const gp = eventos.find((ev) => ev.ronda === ronda);
  return armarClasificacion({
    filas,
    solapa: ruta.solapa,
    anio: ruta.anio,
    tras: gp ? `TRAS LA R${ronda} · ${gp.pais.toUpperCase()}` : "",
    juego: enJuego(ronda, eventos, ruta.solapa),
  });
}
