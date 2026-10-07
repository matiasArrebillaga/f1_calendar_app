// Manda el aviso de la próxima sesión, una sola vez por sesión. Lo corre
// .github/workflows/avisos.yaml cada 10 min; la última sesión avisada viaja
// en el caché de Actions como avisos/ultima.txt.
//
// AHORA=<fecha ISO> simula otro momento (prueba a mano con workflow_dispatch):
// en ese caso no se guarda como avisada, así no se pierde el aviso real.
import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import webpush from "web-push";
import { aEvento, sesionAAvisar } from "../web/js/formato.js";
import { VAPID_PUBLICA } from "../web/js/avisos.js";

const PAGINA = "https://matiasarrebillaga.github.io/f1_calendar_app/";
const ULTIMA = new URL("ultima.txt", import.meta.url);
// trim: al pegar la fecha en el formulario de GitHub suele venir con espacios,
// y Date.parse da NaN con cualquier espacio alrededor.
const textoAhora = process.env.AHORA?.trim();
const prueba = Boolean(textoAhora);
const ahora = prueba ? Date.parse(textoAhora) : Date.now();
if (Number.isNaN(ahora)) {
  console.error(`"ahora" no es una fecha: ${JSON.stringify(textoAhora)}. Usá el formato 2026-10-09T08:05:00Z (UTC).`);
  process.exit(1);
}

async function pedir(url) {
  const respuesta = await fetch(url);
  if (!respuesta.ok) throw new Error(`${respuesta.status} ${url}`);
  return respuesta.json();
}

const anio = new Date(ahora).getUTCFullYear();
// Jolpica caído: se reintenta en 10 min. Sin exit 1, así un corte no manda un
// mail de falla por cada corrida; el único error que avisa es el del push.
const races = await pedir(`https://api.jolpi.ca/ergast/f1/${anio}.json?limit=100`)
  .then((datos) => datos.MRData.RaceTable.Races)
  .catch((error) => {
    console.log(`Sin calendario de Jolpica (${error.message}): se reintenta en la próxima corrida`);
    process.exit(0);
  });
// Los nombres en castellano salen del comun.json publicado; si no está, en inglés.
const comun = await pedir(`${PAGINA}datos/comun.json`).catch(() => ({ eventos: {}, paises: {}, banderas: {} }));
const ultima = existsSync(ULTIMA) ? readFileSync(ULTIMA, "utf8").trim() : null;
const aviso = sesionAAvisar(races.map((r) => aEvento(r, comun)), ahora, ultima);

if (!aviso) {
  console.log("Nada que avisar");
  process.exit(0);
}
if (!process.env.VAPID_PRIVATE || !process.env.PUSH_SUBSCRIPTION) {
  console.log(`Sin secretos configurados: no se avisa ${aviso.id}`);
  process.exit(0);
}

const { ev, sesion, minutos, id } = aviso;
webpush.setVapidDetails("https://github.com/matiasArrebillaga/f1_calendar_app", VAPID_PUBLICA, process.env.VAPID_PRIVATE);
try {
  await webpush.sendNotification(JSON.parse(process.env.PUSH_SUBSCRIPTION), JSON.stringify({
    titulo: `${sesion.nombre} · ${ev.nombre}`,
    cuerpo: `Empieza en ${minutos} min`,
    tag: id,
    url: `#/gp/${ev.anio}/${ev.ronda}`,
  }), { TTL: 1800, urgency: "high" });
} catch (error) {
  // Nunca imprimir el error entero: trae el endpoint de la suscripción y los
  // logs de un repo público son públicos. 404/410 = suscripción vencida:
  // volver a tocar la campana y copiar el texto nuevo.
  console.error(`Falló el envío de ${id}: ${error.statusCode ?? error.name}`);
  process.exit(1);
}
console.log(`Avisado: ${id}`);
if (!prueba) {
  writeFileSync(ULTIMA, id);
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `id=${id}\n`);
}
