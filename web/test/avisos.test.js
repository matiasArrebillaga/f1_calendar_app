import { test } from "node:test";
import assert from "node:assert/strict";
import { VAPID_PUBLICA, claveEnBytes } from "../js/avisos.js";

test("la clave pública VAPID es un punto P-256 sin comprimir", () => {
  const bytes = claveEnBytes(VAPID_PUBLICA);
  assert.equal(bytes.length, 65);
  assert.equal(bytes[0], 4);
});
