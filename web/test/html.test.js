import { test } from "node:test";
import assert from "node:assert/strict";
import { html } from "../js/html.js";

test("escapa lo interpolado", () => {
  assert.equal(String(html`<b>${'<img src=x onerror="a">'}</b>`),
    "<b>&lt;img src=x onerror=&quot;a&quot;&gt;</b>");
});

test("inserta tal cual otro html y las listas", () => {
  const items = ["a", "<b>"].map((x) => html`<li>${x}</li>`);
  assert.equal(String(html`<ul>${items}</ul>`), "<ul><li>a</li><li>&lt;b&gt;</li></ul>");
});

test("null, undefined y false no escriben nada; el 0 sí", () => {
  assert.equal(String(html`${null}${undefined}${false}${0}`), "0");
});
