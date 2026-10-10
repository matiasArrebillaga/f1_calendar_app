// "Agregar al calendario": los horarios de un GP o de la temporada como
// archivo .ics (RFC 5545), que abren Google Calendar, Outlook y el de Windows.
import { DURACION_MIN, gpCorto } from "./formato.js";

const AVISO_MIN = 15;

// 2025-04-06T05:00:00.000Z → 20250406T050000Z
const utc = (fecha) => fecha.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
const escapar = (texto) => texto.replace(/[\\;,]/g, (c) => `\\${c}`).replace(/\n/g, "\\n");

export function armarIcs(eventos, ahora) {
  const lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Calendario F1//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"];
  for (const ev of eventos) {
    for (const s of ev.sesiones) {
      const titulo = `F1 · ${s.nombre} · ${gpCorto(ev.nombre)}`;
      lineas.push("BEGIN:VEVENT",
        // UID estable: importar dos veces actualiza en vez de duplicar.
        `UID:${ev.anio}-${ev.ronda}-${s.clave}@f1-calendar`,
        `DTSTAMP:${utc(new Date(ahora))}`,
        `SUMMARY:${escapar(titulo)}`,
        `LOCATION:${escapar(`${ev.circuito}, ${ev.pais}`)}`);
      if (s.sinHora) {
        // Antes de 2005 Jolpica no tiene horarios: evento de día completo.
        lineas.push(`DTSTART;VALUE=DATE:${s.dia.replaceAll("-", "")}`);
      } else {
        lineas.push(`DTSTART:${utc(s.fecha)}`,
          `DTEND:${utc(new Date(s.fecha.getTime() + DURACION_MIN[s.clave] * 60_000))}`,
          "BEGIN:VALARM", "ACTION:DISPLAY", `DESCRIPTION:${escapar(titulo)}`,
          `TRIGGER:-PT${AVISO_MIN}M`, "END:VALARM");
      }
      lineas.push("END:VEVENT");
    }
  }
  lineas.push("END:VCALENDAR");
  return `${lineas.join("\r\n")}\r\n`;
}

// "Gran Premio de Japón" → "f1-2025-japon.ics"
export const nombreIcs = (anio, nombre) => `f1-${anio}${nombre ? `-${gpCorto(nombre)}` : ""}.ics`
  .normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9.]+/g, "-");

export function descargarIcs(eventos, nombreArchivo) {
  const url = URL.createObjectURL(new Blob([armarIcs(eventos, Date.now())], { type: "text/calendar" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: nombreArchivo });
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
