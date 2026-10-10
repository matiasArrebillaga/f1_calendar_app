process.env.TZ = "America/Argentina/Buenos_Aires";

import { test } from "node:test";
import assert from "node:assert/strict";
import { aEvento } from "../js/formato.js";
import { armarIcs, nombreIcs } from "../js/ics.js";
import { COMUN, SINGAPUR, carrera } from "./datos.js";

const AHORA = new Date("2026-10-06T22:00:00Z").getTime();

test("un evento por sesión, en UTC, con duración y aviso", () => {
  const ics = armarIcs([aEvento(SINGAPUR, COMUN)], AHORA);
  assert.ok(ics.startsWith("BEGIN:VCALENDAR\r\n"));
  assert.ok(ics.endsWith("END:VCALENDAR\r\n"));
  assert.equal(ics.match(/BEGIN:VEVENT/g).length, 5);   // EL1, clasif. sprint, sprint, clasif., carrera
  assert.match(ics, /UID:2026-17-Race@f1-calendar\r\nDTSTAMP:20261006T220000Z\r\nSUMMARY:F1 · Carrera · Singapur/);
  assert.match(ics, /DTSTART:20261011T120000Z\r\nDTEND:20261011T140000Z/);   // la carrera dura 2 h
  assert.match(ics, /DTSTART:20261010T090000Z\r\nDTEND:20261010T094500Z/);   // el sprint, 45 min
  assert.equal(ics.match(/TRIGGER:-PT15M/g).length, 5);
  // La coma del lugar va escapada (RFC 5545).
  assert.match(ics, /LOCATION:marina_bay circuit\\, Singapur/);
});

test("sin horario publicado: evento de día completo y sin aviso", () => {
  const ev = aEvento(carrera(3, "Monaco Grand Prix", "Monaco", "monaco", "1988-05-15"), COMUN);
  const ics = armarIcs([ev], AHORA);
  assert.match(ics, /DTSTART;VALUE=DATE:19880515\r\n/);
  assert.doesNotMatch(ics, /VALARM|DTEND/);
});

test("nombre de archivo sin tildes ni espacios", () => {
  assert.equal(nombreIcs(2025, "Gran Premio de Japón"), "f1-2025-japon.ics");
  assert.equal(nombreIcs(2025, "Gran Premio de la Ciudad de México"), "f1-2025-ciudad-de-mexico.ics");
  assert.equal(nombreIcs(2025), "f1-2025.ics");
});
