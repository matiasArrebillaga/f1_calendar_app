// Suscripción a los avisos antes de cada sesión. La manda .github/workflows/
// avisos.yaml (avisos/enviar.mjs) con la clave privada, que es un secreto del
// repo. Sin servidor, la suscripción se copia a mano como secreto
// PUSH_SUBSCRIPTION: es una app personal, un solo celular.
export const VAPID_PUBLICA = "BD4OYGytp3yuBh9faHs_Bs22_ttn1FGWzQ7V8P3yibu7lqH6s-nGPH8786mrJUIKWWaEdyR7dCPbOJXxmHZfDck";

export const claveEnBytes = (b64url) =>
  Uint8Array.from(atob(b64url.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

export async function suscribir() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return { error: "Este navegador no puede recibir avisos. Instalá la app desde Chrome en Android." };
  }
  if ((await Notification.requestPermission()) !== "granted") {
    return { error: "Sin permiso para mostrar notificaciones. Activalo en los ajustes de la app." };
  }
  const registro = await navigator.serviceWorker.ready;
  const suscripcion = (await registro.pushManager.getSubscription())
    ?? (await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: claveEnBytes(VAPID_PUBLICA) }));
  return { texto: JSON.stringify(suscripcion) };
}
