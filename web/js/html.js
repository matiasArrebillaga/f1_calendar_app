// Plantillas HTML con escape: todo lo interpolado es texto, salvo otro
// html`` (o una lista de ellos), que se inserta tal cual. Así ningún nombre
// que venga de una API puede meter HTML.
class Seguro {
  constructor(texto) { this.texto = texto; }
  toString() { return this.texto; }
}

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function valor(v) {
  if (v == null || v === false) return "";
  if (Array.isArray(v)) return v.map(valor).join("");
  if (v instanceof Seguro) return v.texto;
  return String(v).replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

export function html(partes, ...valores) {
  return new Seguro(partes.reduce((acc, parte, i) => acc + valor(valores[i - 1]) + parte));
}
