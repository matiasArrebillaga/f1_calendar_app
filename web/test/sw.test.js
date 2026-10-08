import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

test("el service worker precachea todos los módulos de la app", () => {
  const sw = readFileSync(new URL("../sw.js", import.meta.url), "utf8");
  const modulos = readdirSync(new URL("../js/", import.meta.url), { recursive: true })
    .filter((f) => f.endsWith(".js"))
    .map((f) => `"js/${f.replaceAll("\\", "/")}"`);
  for (const m of modulos) assert.ok(sw.includes(m), `falta ${m} en PRECACHE de sw.js`);
});
