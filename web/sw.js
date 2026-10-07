// Red primero, caché si no hay conexión: así siempre se ve lo último que se
// pudo bajar. Sirve igual para la app (html/js/css) y para la API.
const CACHE = "f1-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then((respuesta) => {
        if (respuesta.ok) {
          const copia = respuesta.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copia));
        }
        return respuesta;
      })
      .catch(() => caches.match(e.request))
  );
});

// Avisos antes de cada sesión (avisos/enviar.mjs). El tag es el id de la
// sesión: si llegara un duplicado, reemplaza al anterior en vez de sumar otro.
self.addEventListener("push", (e) => {
  const aviso = e.data?.json() ?? {};
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
    return ventana.focus().then((v) => v.navigate(url));
  }));
});
