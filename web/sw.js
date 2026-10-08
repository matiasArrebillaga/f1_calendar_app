// Red primero, caché si no hay conexión: así siempre se ve lo último que se
// pudo bajar. Sirve igual para la app (html/js/css) y para la API.
const CACHE = "f1-v1";
// Lo mínimo para abrir sin conexión desde la primera instalación: la página
// que instala el service worker bajó todo esto antes de que él existiera.
// web/test/sw.test.js verifica que estén todos los .js.
const PRECACHE = [
  "./", "index.html", "style.css", "manifest.json", "icon-192.png", "datos/comun.json",
  "js/api.js", "js/app.js", "js/avisos.js", "js/formato.js", "js/html.js",
  "js/vistas/calendario.js", "js/vistas/capas.js", "js/vistas/clasificacion.js",
  "js/vistas/detalle.js", "js/vistas/ficha_equipo.js", "js/vistas/ficha_piloto.js",
  "js/vistas/filas.js", "js/vistas/pilotos.js",
];
// Con una copia guardada, no se espera a una red que no contesta.
const ESPERA_RED_MS = 8000;

self.addEventListener("install", (e) => e.waitUntil(
  // De a uno: con addAll, un solo archivo que falle dejaba sin instalar.
  caches.open(CACHE).then((c) => Promise.allSettled(PRECACHE.map((url) => c.add(url))))
    .then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

const conTiempo = (promesa, ms) => new Promise((ok, mal) => {
  setTimeout(() => mal(new Error("timeout")), ms);
  promesa.then(ok, mal);
});

async function responder(e) {
  const red = fetch(e.request).then((respuesta) => {
    if (respuesta.ok) {
      const copia = respuesta.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copia));
    }
    return respuesta;
  });
  try {
    const respuesta = await conTiempo(red, ESPERA_RED_MS);
    // Un 429 o un 5xx de la API: mejor lo guardado que un error.
    return respuesta.ok ? respuesta : (await caches.match(e.request)) ?? respuesta;
  } catch {
    // Sin copia, se espera a la red igual (o falla como sin service worker).
    return (await caches.match(e.request)) ?? red;
  }
}

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(responder(e));
});

// Avisos antes de cada sesión (avisos/enviar.mjs). El tag es el id de la
// sesión: si llegara un duplicado, reemplaza al anterior en vez de sumar otro.
self.addEventListener("push", (e) => {
  let aviso = {};
  try {
    aviso = e.data?.json() ?? {};
  } catch {
    // un push que no es JSON: se muestra el aviso genérico
  }
  e.waitUntil(self.registration.showNotification(aviso.titulo ?? "Calendario F1", {
    body: aviso.cuerpo, tag: aviso.tag, icon: "icon-192.png", data: { url: aviso.url ?? "" },
  }));
});

// Tocar el aviso abre el GP: en la ventana de la app si ya estaba abierta.
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL(e.notification.data?.url ?? "", self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ventanas) => {
    const ventana = ventanas[0];
    if (!ventana) return self.clients.openWindow(url);
    // navigate() falla si la ventana no está controlada por este service worker.
    return ventana.focus().then((v) => v.navigate(url)).catch(() => self.clients.openWindow(url));
  }));
});
