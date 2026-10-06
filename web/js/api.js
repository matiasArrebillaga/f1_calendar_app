// Pedidos a las APIs y a los JSON de datos/. Un caché en memoria por URL
// evita repetir pedidos dentro de la misma visita; entre visitas y sin
// conexión responde el service worker (sw.js).
const JOLPICA = "https://api.jolpi.ca/ergast/f1";
const OPENF1 = "https://api.openf1.org/v1";
const memoria = new Map();

function pedir(url) {
  if (!memoria.has(url)) {
    const promesa = fetch(url).then((respuesta) => {
      if (!respuesta.ok) {
        const error = new Error(`${respuesta.status} ${url}`);
        error.status = respuesta.status;
        throw error;
      }
      return respuesta.json();
    });
    // Un error no se guarda: "Reintentar" tiene que volver a pedir.
    promesa.catch(() => memoria.delete(url));
    memoria.set(url, promesa);
  }
  return memoria.get(url);
}

export const comun = () => pedir("datos/comun.json");
export const carrerasPrevias = () => pedir("datos/carreras_previas.json");
export const ganadores = () => pedir("datos/ganadores.json");

export async function calendario(anio) {
  return (await pedir(`${JOLPICA}/${anio}.json?limit=100`)).MRData.RaceTable.Races;
}

export async function resultados(anio, ronda, recurso) {
  return (await pedir(`${JOLPICA}/${anio}/${ronda}/${recurso}.json?limit=100`)).MRData.RaceTable.Races[0] ?? null;
}

export async function campeonato(anio, tipo) {
  return (await pedir(`${JOLPICA}/${anio}/${tipo}.json?limit=100`)).MRData.StandingsTable.StandingsLists[0] ?? null;
}

// Libres y clasificación sprint. La sesión se busca por nombre y por día
// (UTC en las dos APIs); null si OpenF1 no la tiene.
export async function sesionOpenF1(anio, nombre, dia) {
  const sesiones = await pedir(`${OPENF1}/sessions?year=${anio}`);
  const sesion = sesiones.find((s) => s.session_name === nombre && s.date_start.slice(0, 10) === dia);
  if (!sesion) return null;
  const [res, pilotos] = await Promise.all([
    pedir(`${OPENF1}/session_result?session_key=${sesion.session_key}`),
    pedir(`${OPENF1}/drivers?session_key=${sesion.session_key}`),
  ]);
  return { resultados: res, pilotos };
}

// null si ese año no está exportado (404); cualquier otro error sube.
export async function temporada(anio, datosComunes) {
  const url = anio === datosComunes.anio_actual ? "datos/actual.json" : `datos/temporadas/${anio}.json`;
  try {
    return await pedir(url);
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

// La miniatura del artículo, como core/fotos.py.
export async function fotoWikipedia(urlWiki) {
  const titulo = decodeURIComponent(urlWiki.split("/wiki/")[1] ?? "");
  if (!titulo) return null;
  const datos = await pedir(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(titulo)}`);
  return datos.thumbnail?.source ?? null;
}
