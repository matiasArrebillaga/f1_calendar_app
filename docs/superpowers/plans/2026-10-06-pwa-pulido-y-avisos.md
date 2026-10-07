# PWA móvil: fotos oficiales, rediseño para celular y avisos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fotos y logos oficiales en la temporada en curso, calendario sin desplegable, fichas con "carrera por carrera" en lista, pulido de app (en vivo, esqueletos, toques, transiciones, sin conexión) y una notificación push antes de cada sesión.

**Architecture:** Todo en `web/` (HTML/JS sin build, vistas que devuelven `html```), salvo dos piezas fuera: `exportar_web.py` completa fotos desde OpenF1 en el deploy, y `avisos/` + `.github/workflows/avisos.yaml` mandan el push cada 10 min desde GitHub Actions con `web-push`. La lógica nueva va en funciones puras testeables (`formato.js` y funciones `filas…` exportadas por cada vista); el DOM sólo se toca en `montar()` y `app.js`.

**Tech Stack:** JS ES modules en el navegador (Chrome Android), `node --test` (Node 22), Python 3 stdlib + pytest, GitHub Actions, Web Push (VAPID) con el paquete npm `web-push`.

**Spec:** `docs/superpowers/specs/2026-10-06-pwa-pulido-y-avisos-design.md` · Mockups: https://claude.ai/artifact/HGgyMH6M1AgtzKyM72b6KK (pantallas 1–8).

## Global Constraints

- No tocar la app de escritorio: nada en `core/`, `ui/`, `workers/`, `main.py`, `style.qss`.
- Paleta Telemetría con los tokens de `web/style.css` (`--app`, `--panel`, `--surface`, `--hover`, `--borde`, `--texto`, `--texto2`, `--muted`, `--rojo`, `--dato`, `--error`, `--futuro`). Rojo sólo para estado/foco; cian (`--dato`) para datos. Líneas de 1 px.
- Titillium Web (`var(--titulo)`) sólo para textos grandes (≥17 px).
- Áreas táctiles de 44 px como mínimo.
- La web no suma dependencias: `web-push` vive sólo en `avisos/package.json`.
- `exportar_web.py` sigue usando sólo la stdlib (el deploy no instala nada).
- Textos en español rioplatense.
- Tests: `node --test "web/test/*.test.js"` (desde la raíz del repo) y `python -m pytest test_exportar_web.py -q`.
- Commits en español, estilo del repo ("Web: …", "Exportador: …"), terminando con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Trabajar en una rama (`pwa-pulido-avisos`), no en `master`.

## Review Focus

- Temporadas viejas (1950–2017): sin `foto_cuerpo`, sin `headshot_url` y a veces sin ganador por ronda — grilla, fichas y calendario tienen que verse completos (sigla/Wikipedia, fila sin ganador), sin `undefined`/`NaN`.
- Imagen del CDN que da 404 (p. ej. en enero, antes de que F1 publique el año nuevo): la `<img>` se saca sola (`onerror`) y el layout queda entero.
- Piloto que todavía no corrió en la temporada (`tira` vacía): ficha con "Todavía no corrió", sin "Últimas 5" ni filas.
- Largada desde boxes (`largada: 0`) y posiciones sin número (DSQ/DNQ/NC/DNF): ni ▲/▼ inventados ni "Largó 0º".
- Notificación tocada con la app cerrada vs. abierta en otra pantalla: en los dos casos termina en `#/gp/<año>/<ronda>`.

---

### Task 1: Exportador — fotos de OpenF1, logos y autos 2026

**Files:**
- Modify: `exportar_web.py` (imports, constantes nuevas, `datos_comunes`, `exportar_actual`, función nueva `completar_fotos`)
- Test: `test_exportar_web.py`

**Interfaces:**
- Produces: en `web/datos/actual.json`, cada piloto puede traer `headshot_url` (busto, `/2col/`) y `foto_cuerpo` (cuerpo entero, `.webp`); `cara_a_cara.a/b.headshot_url` copiado del piloto. En `comun.json`: `logos` incluye los 11 equipos 2026 y aparece `autos: {constructor_id: url}`.
- Produces (Python): `completar_fotos(datos, anio, pedir=pedir_openf1) -> None`, `url_cdn(anio, ruta, ancho) -> str`, `SLUG_CDN: dict`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_exportar_web.py`:

```python
URL_ANT = ("https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/"
           "drivers/K/ANDANT01_Kimi_Antonelli/andant01.png.transform/1col/image.png")


def _datos_fotos():
    return {
        "pilotos": [
            {"driver_id": "antonelli", "codigo": "ANT", "constructor_id": "mercedes", "headshot_url": None},
            {"driver_id": "tsunoda", "codigo": "TSU", "constructor_id": "red_bull", "headshot_url": None},
        ],
        "equipos": [{"constructor_id": "mercedes", "cara_a_cara": {
            "a": {"driver_id": "antonelli", "headshot_url": None},
            "b": {"driver_id": "russell", "headshot_url": None}}}],
    }


def test_completar_fotos_cruza_openf1_por_sigla():
    datos = _datos_fotos()
    exportar_web.completar_fotos(datos, 2026, lambda ruta: [
        {"name_acronym": "ANT", "headshot_url": URL_ANT},
        {"name_acronym": "RUS", "headshot_url": None},
    ])
    ant, tsu = datos["pilotos"]
    assert ant["headshot_url"] == URL_ANT.replace("/1col/", "/2col/")
    assert ant["foto_cuerpo"] == ("https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/"
                                  "common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp")
    # Sin coincidencia en OpenF1: queda como antes (Wikipedia o sigla).
    assert tsu["headshot_url"] is None and "foto_cuerpo" not in tsu
    cara = datos["equipos"][0]["cara_a_cara"]
    assert cara["a"]["headshot_url"] == ant["headshot_url"]
    assert cara["b"]["headshot_url"] is None


def test_completar_fotos_sin_openf1_no_rompe_el_deploy():
    def caido(ruta):
        raise OSError("sin red")
    datos = _datos_fotos()
    exportar_web.completar_fotos(datos, 2026, caido)
    assert datos["pilotos"][0]["headshot_url"] is None
```

Y en `test_datos_comunes_salen_de_core_y_marcan_los_mapas`, después de la línea de `logos["mclaren"]`, agregar:

```python
    assert comun["logos"]["audi"].endswith("/2026/audi/2026audilogowhite.webp")
    assert comun["autos"]["cadillac"].endswith("/2026/cadillac/2026cadillaccarright.webp")
```

- [ ] **Step 2: Correr los tests y ver que fallan**

Run: `python -m pytest test_exportar_web.py -q`
Expected: FAIL — `AttributeError: module 'exportar_web' has no attribute 'completar_fotos'` y `KeyError: 'audi'`/`'autos'`.

- [ ] **Step 3: Implementar**

En `exportar_web.py`, sumar a los imports `import re` y `import urllib.request`, y debajo de `REINTENTOS = 5`:

```python
OPENF1 = "https://api.openf1.org/v1"
# Slug de cada equipo en el CDN nuevo de F1 (verificados contra el CDN el
# 2026-10-06). ponytail: tabla fija como las de core/equipos.py; cada año el
# CDN usa la carpeta del año, y si F1 todavía no la publicó (enero) las
# imágenes dan 404 y la web las saca (onerror).
SLUG_CDN = {
    "mercedes": "mercedes", "ferrari": "ferrari", "mclaren": "mclaren",
    "red_bull": "redbullracing", "rb": "racingbulls", "aston_martin": "astonmartin",
    "alpine": "alpine", "williams": "williams", "haas": "haasf1team",
    "audi": "audi", "cadillac": "cadillac",
}
CDN = "https://media.formula1.com/image/upload/c_lfill,w_{ancho}/q_auto/v1740000000/common/f1/{anio}/{ruta}.webp"
# El código de la foto en la URL de OpenF1: .../ANDANT01_Kimi_Antonelli/andant01.png...
CODIGO_FOTO = re.compile(r"/([a-z]{6}\d{2})\.png")


def url_cdn(anio, ruta, ancho):
    return CDN.format(anio=anio, ruta=ruta, ancho=ancho)


def pedir_openf1(ruta):
    pedido = urllib.request.Request(f"{OPENF1}/{ruta}", headers={"User-Agent": historial.USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=30) as respuesta:
        return json.load(respuesta)


def completar_fotos(datos, anio, pedir=pedir_openf1):
    """Foto oficial de los pilotos de la temporada en curso, desde los pilotos
    de la última sesión de OpenF1 cruzados por sigla. En escritorio la pone
    FastF1, que no corre en el deploy. Si OpenF1 falla, se exporta sin fotos:
    la web cae en Wikipedia o la sigla, como antes."""
    try:
        de_openf1 = {d["name_acronym"]: d.get("headshot_url") for d in pedir("drivers?session_key=latest")}
    except (OSError, ValueError) as error:
        print(f"OpenF1 sin fotos: {error}")
        return
    for p in datos["pilotos"]:
        url = de_openf1.get(p.get("codigo"))
        if not url:
            continue
        # /1col/ son 93 px; /2col/ son 206, que alcanzan para los avatares.
        p["headshot_url"] = url.replace("/1col/", "/2col/")
        codigo = CODIGO_FOTO.search(url)
        slug = SLUG_CDN.get(p.get("constructor_id"))
        if codigo and slug:
            c = codigo[1]
            p["foto_cuerpo"] = url_cdn(anio, f"{slug}/{c}/{anio}{slug}{c}right", 440)
    por_id = {p["driver_id"]: p for p in datos["pilotos"]}
    for e in datos["equipos"]:
        cara = e.get("cara_a_cara")
        for lado in ("a", "b") if cara else ():
            piloto = por_id.get(cara[lado]["driver_id"])
            if piloto:
                cara[lado]["headshot_url"] = piloto.get("headshot_url")
```

En `datos_comunes(anio_actual)`, reemplazar la línea de `"logos"` por:

```python
        # Los 11 equipos actuales del CDN nuevo; los viejos, con la ruta de 2025 de core.
        "logos": {**{constructor_id: url_logo(constructor_id) for constructor_id in SLUG_LOGO},
                  **{cid: url_cdn(anio_actual, f"{slug}/{anio_actual}{slug}logowhite", 200)
                     for cid, slug in SLUG_CDN.items()}},
        "autos": {cid: url_cdn(anio_actual, f"{slug}/{anio_actual}{slug}carright", 640)
                  for cid, slug in SLUG_CDN.items()},
```

En `exportar_actual(anio)`, después del `for p in datos["pilotos"]: ... carrera_completa(...)`:

```python
    completar_fotos(datos, anio)
```

- [ ] **Step 4: Correr los tests y ver que pasan**

Run: `python -m pytest test_exportar_web.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Probar contra la red real**

Run: `python exportar_web.py`
Expected: termina con `2026: 23 pilotos, ronda 16` (o la ronda que toque). Después:
`python -c "import json;d=json.load(open('web/datos/actual.json',encoding='utf-8'));print(sum(1 for p in d['pilotos'] if p.get('foto_cuerpo')),'de',len(d['pilotos']))"`
Expected: `22 de 23` (Tsunoda no está en OpenF1).

- [ ] **Step 6: Commit**

```bash
git add exportar_web.py test_exportar_web.py
git commit -m "Exportador: fotos oficiales desde OpenF1 y logos y autos 2026 del CDN de F1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Funciones puras de tiempo y nombres (`formato.js`)

**Files:**
- Modify: `web/js/formato.js`
- Test: `web/test/formato.test.js`

**Interfaces:**
- Produces:
  - `gpCorto(nombre: string) -> string` — saca "Gran Premio de (la |los )?" del principio y " Grand Prix" del final.
  - `estadoSesiones(sesiones, ahora: number) -> Array<sesion & { estado: "hecha"|"vivo"|"proxima", avance: number|null, minutos: number|null }>` — `sesiones` son las de `aEvento` (`{ clave, nombre, fecha: Date, … }`).
  - `hayEnVivo(eventos, ahora) -> boolean`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `web/test/formato.test.js` (ya importa `test`, `assert`, `COMUN`, `SINGAPUR`; sumar `estadoSesiones, gpCorto, hayEnVivo` al import de `../js/formato.js`, y `aEvento` si no está):

```js
test("nombre corto del GP: sin 'Gran Premio de' ni 'Grand Prix'", () => {
  assert.equal(gpCorto("Gran Premio de Azerbaiyán"), "Azerbaiyán");
  assert.equal(gpCorto("Gran Premio de los Países Bajos"), "Países Bajos");
  assert.equal(gpCorto("United States Grand Prix"), "United States");
  assert.equal(gpCorto("Bahrain Grand Prix in Malaysia"), "Bahrain Grand Prix in Malaysia");
});

test("estado de las sesiones: próxima, en vivo con avance y hecha", () => {
  const ev = aEvento(SINGAPUR, COMUN);
  const libres = estadoSesiones(ev.sesiones, Date.parse("2026-10-09T08:50:00Z"));
  assert.equal(libres[0].estado, "vivo");
  assert.equal(libres[0].minutos, 20);
  assert.ok(Math.abs(libres[0].avance - 20 / 60) < 1e-9);
  assert.ok(libres.slice(1).every((s) => s.estado === "proxima" && s.avance === null));

  const qualy = estadoSesiones(ev.sesiones, Date.parse("2026-10-10T13:38:00Z"));
  assert.deepEqual(qualy.map((s) => s.estado), ["hecha", "hecha", "hecha", "vivo", "proxima"]);
  assert.equal(qualy[3].nombre, "Clasificación");

  // La carrera se da por terminada a las 2 h, igual que indiceProxima.
  const fin = estadoSesiones(ev.sesiones, Date.parse("2026-10-11T14:01:00Z"));
  assert.ok(fin.every((s) => s.estado === "hecha"));
});

test("hay sesión en vivo en algún evento", () => {
  const evs = [aEvento(SINGAPUR, COMUN)];
  assert.equal(hayEnVivo(evs, Date.parse("2026-10-10T13:10:00Z")), true);
  assert.equal(hayEnVivo(evs, Date.parse("2026-10-10T11:00:00Z")), false);
  assert.equal(hayEnVivo([], Date.now()), false);
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `node --test "web/test/formato.test.js"`
Expected: FAIL — `SyntaxError: The requested module '../js/formato.js' does not provide an export named 'estadoSesiones'`.

- [ ] **Step 3: Implementar**

En `web/js/formato.js`, debajo de `cuentaRegresiva`:

```js
// Duración típica de cada sesión, para el estado "en vivo": no hay datos en
// vivo gratis dentro de la sesión, así que se calcula con el horario.
const DURACION_MIN = {
  FirstPractice: 60, SecondPractice: 60, ThirdPractice: 60,
  SprintShootout: 45, SprintQualifying: 45, Sprint: 45, Qualifying: 60, Race: 120,
};

export function estadoSesiones(sesiones, ahora) {
  return sesiones.map((s) => {
    const inicio = s.fecha.getTime();
    const duracion = DURACION_MIN[s.clave] * 60_000;
    const estado = ahora >= inicio + duracion ? "hecha" : ahora >= inicio ? "vivo" : "proxima";
    const vivo = estado === "vivo";
    return {
      ...s, estado,
      avance: vivo ? (ahora - inicio) / duracion : null,
      minutos: vivo ? Math.floor((ahora - inicio) / 60_000) : null,
    };
  });
}

export const hayEnVivo = (eventos, ahora) =>
  eventos.some((ev) => estadoSesiones(ev.sesiones, ahora).some((s) => s.estado === "vivo"));

// "Gran Premio de Azerbaiyán" → "Azerbaiyán"; los que no tienen traducción
// vienen en inglés ("United States Grand Prix" → "United States").
export const gpCorto = (nombre) => nombre.replace(/^Gran Premio de (la |los )?/, "").replace(/ Grand Prix$/, "");
```

- [ ] **Step 4: Correr y ver que pasan**

Run: `node --test "web/test/*.test.js"`
Expected: PASS (todos, incluidos los viejos).

- [ ] **Step 5: Commit**

```bash
git add web/js/formato.js web/test/formato.test.js
git commit -m "Web: estado en vivo de las sesiones y nombre corto del GP

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Calendario en un solo listado, abierto en la próxima

**Files:**
- Modify: `web/js/vistas/calendario.js` (reescritura de `armarCalendario`, `render`, `montar`; filas nuevas)
- Modify: `web/js/vistas/filas.js` (exportar `bandera`)
- Modify: `web/style.css` (sección Calendario)
- Test: `web/test/calendario.test.js`

**Interfaces:**
- Consumes: `gpCorto`, `sigla`, `indiceProxima`, `aEvento` de `formato.js`; `temporada(anio, comun)` de `api.js`.
- Produces:
  - `ganadoresPorRonda(datos, colores) -> Map<ronda:number, { codigo: string, color: string|null }>`.
  - `armarCalendario(eventos, ahora, ganadores = new Map())` (tercer parámetro nuevo).
  - `bandera(codigo)` en `filas.js` (la usan también las fichas).
  - Clases: `.gp-fila.pasado` / `.gp-fila.futuro`, `.ganador`, `.falta`, `.pildora[data-subir]`.

- [ ] **Step 1: Escribir los tests que fallan**

Reemplazar los dos primeros tests de `web/test/calendario.test.js` y el de 1950 por estos (el de "sin carreras" queda). Sumar al import `ganadoresPorRonda` y `PILOTO_ANT`:

```js
import { armarCalendario, ganadoresPorRonda } from "../js/vistas/calendario.js";
import { COMUN, PILOTO_ANT, SINGAPUR, carrera } from "./datos.js";

const AHORA = new Date("2026-10-06T19:40:00-03:00").getTime();
const GANADORES = new Map([[15, { codigo: "RUS", color: "#00D7B6" }]]);

test("temporada en curso: un solo listado con la próxima en su lugar", () => {
  const salida = String(armarCalendario(eventos, AHORA, GANADORES));
  assert.doesNotMatch(salida, /<details/);
  assert.match(salida, /data-subir>↑ 1 carrera corrida</);
  assert.match(salida, /class="gp-fila pasado"[\s\S]*?R15[\s\S]*?<b>Azerbaiyán<\/b>[\s\S]*?background:#00D7B6"><\/i>RUS/);
  assert.match(salida, /PRÓXIMA · R17/);
  assert.match(salida, /dom 09:00/);                 // carrera de Singapur en hora local
  assert.match(salida, /class="gp-fila futuro"[\s\S]*?<b>United States<\/b>[\s\S]*?en 19 d/);
  assert.ok(salida.indexOf("R15") < salida.indexOf("PRÓXIMA"));
  assert.ok(salida.indexOf("PRÓXIMA") < salida.indexOf("R18"));
  assert.match(salida, /<h3 class="mes">OCTUBRE<\/h3>/);
});

test("temporada terminada: todo corrido, sin próxima ni píldora", () => {
  const salida = String(armarCalendario(eventos, new Date("2027-01-10").getTime()));
  assert.doesNotMatch(salida, /PRÓXIMA|data-subir/);
  assert.equal(salida.match(/class="gp-fila pasado"/g).length, 3);
  assert.doesNotMatch(salida, /class="ganador"/);     // sin datos de ganadores
});

test("1950: carreras sin hora ni sesiones", () => {
  const viejas = [carrera(1, "British Grand Prix", "UK", "silverstone", "1950-05-13", null)]
    .map((r) => aEvento(r, COMUN));
  const salida = String(armarCalendario(viejas, Date.now()));
  assert.match(salida, /<b>British<\/b>/);
  assert.match(salida, /13 MAY/);
  assert.doesNotMatch(salida, /undefined|NaN/);
});

test("ganadores por ronda, desde la tira de cada piloto", () => {
  const datos = { pilotos: [{ ...PILOTO_ANT, tira: [{ ronda: 3, posicion: 1 }, { ronda: 4, posicion: 2 }] }] };
  const ganadores = ganadoresPorRonda(datos, COMUN.colores);
  assert.deepEqual([...ganadores], [[3, { codigo: "ANT", color: "#00D7B6" }]]);
  assert.equal(ganadoresPorRonda(null, COMUN.colores).size, 0);
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `node --test "web/test/calendario.test.js"`
Expected: FAIL — no existe el export `ganadoresPorRonda`.

- [ ] **Step 3: Exportar `bandera` desde `filas.js`**

Agregar al final de `web/js/vistas/filas.js`:

```js
// La bandera chica de un país (flagcdn). Sin código, un hueco del mismo tamaño
// para que las filas no se corran.
export const bandera = (codigo) => (codigo
  ? html`<img class="bandera" src="https://flagcdn.com/w40/${codigo}.png" alt="" loading="lazy" width="22" height="15">`
  : html`<span class="bandera"></span>`);
```

- [ ] **Step 4: Reescribir `calendario.js`**

Reemplazar el archivo entero por:

```js
import { html } from "../html.js";
import { MESES, aEvento, cuentaRegresiva, diaHora, gpCorto, indiceProxima, sigla } from "../formato.js";
import { calendario, temporada } from "../api.js";
import { bandera } from "./filas.js";

export const encabezado = () => ({ titulo: "Calendario" });

const DIA_MS = 86_400_000;

function armarProxima(ev, ahora) {
  const c = cuentaRegresiva(ev.largada, ahora);
  return html`<a class="hero" href="#/gp/${ev.anio}/${ev.ronda}" data-largada="${ev.largada.getTime()}" data-ronda="${ev.ronda}">
    <div class="fila"><span class="chip" data-chip>${c.enCurso ? "EN CURSO" : "PRÓXIMA"} · R${ev.ronda}</span>${bandera(ev.bandera)}</div>
    <h2>${ev.nombre}</h2>
    <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    <div class="cuenta">
      <div><b data-dias>${c.dias}</b><small>DÍAS</small></div>
      <div><b data-horas>${c.horas}</b><small>HORAS</small></div>
      <div><b data-minutos>${c.minutos}</b><small>MIN</small></div>
    </div>
    <h3 class="eti">HORARIOS · HORA LOCAL</h3>
    <dl class="horarios">${ev.sesiones.map((s) =>
      html`<dt class="${s.clave === "Race" ? "carrera" : ""}">${s.nombre}</dt><dd>${diaHora(s.fecha)}</dd>`)}</dl>
  </a>`;
}

// Corrida: atenuada y con el ganador; futura: cuántos días faltan.
function armarFila(ev, estado, ganador, ahora) {
  const derecha = estado === "pasado"
    ? (ganador ? html`<span class="ganador mono"><i style="background:${ganador.color ?? "var(--futuro)"}"></i>${ganador.codigo}</span>` : "")
    : html`<span class="falta mono">en ${Math.max(1, Math.ceil((ev.largada - ahora) / DIA_MS))} d</span>`;
  return html`<a class="gp-fila ${estado}" href="#/gp/${ev.anio}/${ev.ronda}">
    <span class="ronda mono">R${ev.ronda}</span>${bandera(ev.bandera)}
    <span class="nombre"><b>${gpCorto(ev.nombre)}</b><small>${ev.rango}</small></span>${derecha}
  </a>`;
}

// Ronda → ganador, del JSON de la temporada (el que llegó 1º en su tira).
export function ganadoresPorRonda(datos, colores) {
  const ganadores = new Map();
  for (const p of datos?.pilotos ?? []) {
    for (const t of p.tira) {
      if (t.posicion === 1) ganadores.set(t.ronda, { codigo: sigla(p), color: colores[p.constructor_id] ?? null });
    }
  }
  return ganadores;
}

// Un solo listado por mes, como el grid de escritorio: lo corrido arriba, la
// próxima en su lugar y lo que viene abajo. Se abre parado en la próxima (montar).
export function armarCalendario(eventos, ahora, ganadores = new Map()) {
  if (!eventos.length) {
    return html`<div class="estado"><h3>Sin calendario</h3><p>No hay carreras publicadas para esta temporada.</p></div>`;
  }
  const i = indiceProxima(eventos, ahora);
  const estadoDe = (ev) => (ev === eventos[i] ? "proxima" : ev.largada < ahora ? "pasado" : "futuro");
  const grupos = [];
  for (const ev of eventos) {
    const mes = ev.largada.getMonth();
    if (grupos.at(-1)?.mes !== mes) grupos.push({ mes, eventos: [] });
    grupos.at(-1).eventos.push(ev);
  }
  const corridas = i > 0 ? i : 0;
  return html`<div class="cuerpo calendario">
    ${corridas ? html`<button class="pildora oculta" data-subir>↑ ${corridas} ${corridas === 1 ? "carrera corrida" : "carreras corridas"}</button>` : ""}
    ${grupos.map((g) => html`<h3 class="mes">${MESES[g.mes]}</h3>
      <div class="filas">${g.eventos.map((ev) => (estadoDe(ev) === "proxima"
        ? armarProxima(ev, ahora) : armarFila(ev, estadoDe(ev), ganadores.get(ev.ronda), ahora)))}</div>`)}
  </div>`;
}

export async function render(ruta, comun) {
  const [races, datos] = await Promise.all([
    calendario(ruta.anio),
    temporada(ruta.anio, comun).catch(() => null),   // sin ganadores, el calendario igual se ve
  ]);
  const eventos = races.map((race) => aEvento(race, comun));
  return armarCalendario(eventos, Date.now(), ganadoresPorRonda(datos, comun.colores));
}

export function montar(main) {
  const limpiezas = [];
  const hero = main.querySelector("[data-largada]");
  const ultimaCorrida = [...main.querySelectorAll(".gp-fila.pasado")].at(-1);
  const pildora = main.querySelector("[data-subir]");
  if (hero && ultimaCorrida) {
    // Como escritorio: abre parado en la próxima; lo corrido queda arriba.
    const alto = document.getElementById("encabezado").offsetHeight;
    window.scrollTo(0, hero.getBoundingClientRect().top + window.scrollY - alto - 12);
  }
  if (pildora && ultimaCorrida) {
    // La píldora se ve mientras lo corrido quedó arriba, fuera de pantalla.
    const observador = new IntersectionObserver(([e]) =>
      pildora.classList.toggle("oculta", e.isIntersecting || e.boundingClientRect.top > 0));
    observador.observe(ultimaCorrida);
    pildora.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    limpiezas.push(() => observador.disconnect());
  }
  if (hero) {
    // La cuenta regresiva se refresca cada 30 s, como el QTimer de escritorio.
    const largada = Number(hero.dataset.largada);
    const actualizar = () => {
      const c = cuentaRegresiva(largada, Date.now());
      hero.querySelector("[data-dias]").textContent = c.dias;
      hero.querySelector("[data-horas]").textContent = c.horas;
      hero.querySelector("[data-minutos]").textContent = c.minutos;
      hero.querySelector("[data-chip]").textContent = `${c.enCurso ? "EN CURSO" : "PRÓXIMA"} · R${hero.dataset.ronda}`;
    };
    const id = setInterval(actualizar, 30_000);
    limpiezas.push(() => clearInterval(id));
  }
  return () => limpiezas.forEach((f) => f());
}
```

- [ ] **Step 5: CSS del calendario**

En `web/style.css`, sección `/* ---------- Calendario ---------- */`: borrar las reglas `.plegado …` (4), `.lista`, `.tarjeta …` (5) y `.fecha`. Agregar al final de esa sección:

```css
.calendario .filas { display: flex; flex-direction: column; }
.calendario .hero { margin: 8px 0; }
.gp-fila {
  display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 0 4px;
  border-bottom: 1px solid var(--borde-suave); transition: background .12s;
}
.gp-fila:active { background: var(--hover); }
.gp-fila .ronda { width: 30px; flex: none; font-size: 12px; color: var(--muted); }
.gp-fila .bandera, .carrera-fila .bandera { width: 22px; height: 15px; flex: none; margin: 0; object-fit: cover; }
.gp-fila.pasado .nombre b { color: var(--texto2); font-weight: 400; }
.gp-fila.pasado .bandera { opacity: .75; }
.ganador {
  display: flex; align-items: center; gap: 6px; padding: 3px 8px 3px 6px; font-size: 12px; font-weight: 600;
  color: var(--texto2); background: var(--panel); border: 1px solid var(--borde); border-radius: 6px;
}
.ganador i { display: block; width: 3px; height: 14px; border-radius: 2px; }
.falta { font-size: 12px; color: var(--dato); }
.pildora {
  position: fixed; z-index: 2; left: 50%; top: calc(66px + env(safe-area-inset-top));
  transform: translateX(-50%); height: 36px; padding: 0 16px; border-radius: 18px;
  font-size: 13px; font-weight: 600; background: rgba(27, 32, 41, .94); border: 1px solid var(--borde-fuerte);
  box-shadow: 0 6px 18px rgba(0, 0, 0, .45); transition: opacity .2s, transform .2s;
}
.pildora.oculta { opacity: 0; pointer-events: none; transform: translate(-50%, -8px); }
```

- [ ] **Step 6: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 7: Verlo andar**

Run (en segundo plano): `python -m http.server 8000 -d web`
Abrir http://localhost:8000/#/calendario/2026 con las DevTools de Chrome en modo celular (390×844). Expected: abre con la tarjeta de la próxima arriba; al scrollear un poco para abajo y volver, la píldora "↑ 16 carreras corridas" aparece mientras lo corrido está arriba fuera de pantalla y tocarla sube al principio; cada corrida muestra el ganador con su color; las futuras "en N d". `#/calendario/2025`: abre arriba, sin píldora.

- [ ] **Step 8: Commit**

```bash
git add web/js/vistas/calendario.js web/js/vistas/filas.js web/style.css web/test/calendario.test.js
git commit -m "Web: calendario en un solo listado abierto en la próxima, con ganadores

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Estado en vivo en la próxima y punto en la pestaña

**Files:**
- Modify: `web/js/vistas/calendario.js` (`armarProxima`, `render`, `montar`)
- Modify: `web/js/app.js` (vigía del punto en la pestaña)
- Modify: `web/style.css`
- Test: `web/test/calendario.test.js`

**Interfaces:**
- Consumes: `estadoSesiones`, `hayEnVivo` (Task 2); `armarCalendario(eventos, ahora, ganadores)` (Task 3).
- Produces: clase `.tabbar a.vivo`; el hero tiene clase `en-vivo` mientras hay sesión en curso.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `web/test/calendario.test.js`:

```js
test("fin de semana en vivo: chip, avance y estado de cada sesión", () => {
  const salida = String(armarCalendario(eventos, Date.parse("2026-10-10T13:38:00Z")));
  assert.match(salida, /class="hero en-vivo"/);
  assert.match(salida, /EN VIVO · CLASIFICACIÓN/);
  assert.match(salida, /width:63%/);                  // 38 de 60 min
  assert.match(salida, /Empezó hace 38 min/);
  assert.equal(salida.match(/✓ Resultados/g).length, 3);   // libres, clasif. sprint y sprint
  assert.match(salida, /<dd class="vivo">EN VIVO<\/dd>/);
  assert.match(salida, /dom 09:00/);                  // la carrera, todavía próxima
  assert.doesNotMatch(salida, /DÍAS/);
});

test("fuera de sesión: cuenta regresiva y sprint marcado", () => {
  const salida = String(armarCalendario(eventos, AHORA));
  assert.match(salida, /PRÓXIMA · R17 · SPRINT/);
  assert.match(salida, /DÍAS/);
  assert.doesNotMatch(salida, /en-vivo|✓ Resultados/);
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `node --test "web/test/calendario.test.js"`
Expected: FAIL — no aparece `class="hero en-vivo"`.

- [ ] **Step 3: Implementar el hero en vivo**

En `calendario.js`, sumar `estadoSesiones` al import de `../formato.js` y reemplazar `armarProxima` por:

```js
function armarProxima(ev, ahora) {
  const sesiones = estadoSesiones(ev.sesiones, ahora);
  const vivo = sesiones.find((s) => s.estado === "vivo");
  const c = cuentaRegresiva(ev.largada, ahora);
  const dato = (s) => (s.estado === "hecha" ? "✓ Resultados" : s.estado === "vivo" ? "EN VIVO" : diaHora(s.fecha));
  return html`<a class="hero ${vivo ? "en-vivo" : ""}" href="#/gp/${ev.anio}/${ev.ronda}" data-largada="${ev.largada.getTime()}">
    <div class="fila">${vivo
      ? html`<span class="chip vivo"><i class="punto"></i>EN VIVO · ${vivo.nombre.toUpperCase()}</span>`
      : html`<span class="chip">PRÓXIMA · R${ev.ronda}${ev.conSprint ? " · SPRINT" : ""}</span>`}${bandera(ev.bandera)}</div>
    <h2>${ev.nombre}</h2>
    <p class="lugar">${ev.circuito} · ${ev.pais} · ${ev.rango}</p>
    ${vivo
      ? html`<div class="avance"><i style="width:${Math.min(100, Math.round(vivo.avance * 100))}%"></i></div>
        <p class="muted nota">Empezó hace ${vivo.minutos} min</p>`
      : html`<div class="cuenta">
        <div><b>${c.dias}</b><small>DÍAS</small></div>
        <div><b>${c.horas}</b><small>HORAS</small></div>
        <div><b>${c.minutos}</b><small>MIN</small></div>
      </div>`}
    <h3 class="eti">HORARIOS · HORA LOCAL</h3>
    <dl class="horarios">${sesiones.map((s) =>
      html`<dt class="${s.clave === "Race" ? "carrera" : ""}">${s.nombre}</dt><dd class="${s.estado}">${dato(s)}</dd>`)}</dl>
  </a>`;
}
```

Guardar la próxima para que `montar` la pueda redibujar. Debajo de `const DIA_MS`:

```js
let proximaEnPantalla = null;   // la que dibujó el último render, para refrescarla
```

En `render`, antes del `return`:

```js
  proximaEnPantalla = eventos[indiceProxima(eventos, Date.now())] ?? null;
```

En `montar`, reemplazar todo el bloque `if (hero) { … }` de la cuenta regresiva por:

```js
  if (hero && proximaEnPantalla) {
    // Cada 30 s se redibuja la tarjeta: cuenta regresiva y estado en vivo.
    const ev = proximaEnPantalla;
    const id = setInterval(() => {
      main.querySelector("[data-largada]")?.replaceWith(
        document.createRange().createContextualFragment(String(armarProxima(ev, Date.now()))));
    }, 30_000);
    limpiezas.push(() => clearInterval(id));
  }
```

- [ ] **Step 4: Punto rojo en la pestaña (`app.js`)**

En `web/js/app.js`, sumar a los imports `aEvento, hayEnVivo` (de `./formato.js`) y `calendario as pedirCalendario` (de `./api.js`). Antes de `mostrar();` al final:

```js
// Punto rojo en Calendario mientras se corre una sesión, mire la pestaña que
// mire. Si falla la red, simplemente no hay punto.
async function vigilarEnVivo() {
  try {
    const datosComunes = await pedirComun();
    const eventos = (await pedirCalendario(datosComunes.anio_actual)).map((r) => aEvento(r, datosComunes));
    const pestana = document.querySelector('.tabbar [data-pestana="calendario"]');
    const marcar = () => pestana.classList.toggle("vivo", hayEnVivo(eventos, Date.now()));
    marcar();
    setInterval(marcar, 30_000);
  } catch {
    // sin conexión: sin punto
  }
}
vigilarEnVivo();
```

- [ ] **Step 5: CSS**

Agregar a la sección Calendario de `web/style.css`:

```css
@keyframes latido { 0% { box-shadow: 0 0 0 0 rgba(255, 255, 255, .7); } 70%, 100% { box-shadow: 0 0 0 7px rgba(255, 255, 255, 0); } }
.chip.vivo { display: inline-flex; align-items: center; gap: 6px; }
.punto { display: block; width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: latido 1.6s infinite; }
.hero.en-vivo { border-color: var(--rojo); }
.avance { height: 4px; margin: 12px 0 4px; overflow: hidden; border-radius: 2px; background: var(--sunken); }
.avance i { display: block; height: 100%; background: var(--rojo); }
.horarios dd.hecha { color: var(--dato); }
.horarios dd.vivo { color: var(--rojo); font-weight: 700; }
.tabbar a { position: relative; }
.tabbar a.vivo::after {
  content: ""; position: absolute; top: 9px; left: calc(50% + 6px); width: 8px; height: 8px;
  border-radius: 50%; background: var(--rojo); border: 2px solid var(--panel);
}
```

- [ ] **Step 6: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 7: Verlo andar**

Con el server de la Task 3, en la consola de DevTools: `Date.now = () => Date.parse("2026-10-10T13:38:00Z"); location.reload()` no sirve (recarga). En su lugar, en la consola: `const real = Date.now; Date.now = () => Date.parse("2026-10-10T13:38:00Z"); dispatchEvent(new HashChangeEvent("hashchange"));`
Expected: la tarjeta pasa a "● EN VIVO · CLASIFICACIÓN" con la barra roja; a los 30 s aparece el punto rojo en la pestaña. Volver con `Date.now = real`.

- [ ] **Step 8: Commit**

```bash
git add web/js/vistas/calendario.js web/js/app.js web/style.css web/test/calendario.test.js
git commit -m "Web: estado en vivo del fin de semana y punto rojo en la pestaña

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Grilla de pilotos y equipos con fotos oficiales

**Files:**
- Modify: `web/js/vistas/pilotos.js`
- Modify: `web/style.css` (sección Pilotos y equipos)
- Modify: `web/test/datos.js` (`COMUN.autos`)
- Test: `web/test/pilotos.test.js`

**Interfaces:**
- Consumes: `p.foto_cuerpo`, `comun.autos` (Task 1).
- Produces: `armarRetrato(p, color)` (foto de cuerpo entero con `view-transition-name: foto-<driver_id>`, o `armarFoto(p, color, "foto")` si no hay). `armarFoto` y `armarLogo` siguen igual.

- [ ] **Step 1: Datos de prueba**

En `web/test/datos.js`, dentro de `COMUN`, debajo de `logos`:

```js
  autos: { mercedes: "https://cdn/mercedes-auto.webp" },
```

- [ ] **Step 2: Escribir los tests que fallan**

En `web/test/pilotos.test.js`, reemplazar los tests "grilla de pilotos…", "con foto oficial…" y "grilla de equipos…" por:

```js
test("grilla de pilotos: tarjeta con número, posición y sigla mientras no hay foto", () => {
  const salida = String(armarPilotos(DATOS, "pilotos", 2026, COMUN));
  assert.match(salida, /href="#\/piloto\/2026\/antonelli"/);
  assert.match(salida, /<span class="num">12<\/span>/);
  assert.match(salida, /<span class="pos-chip mono">1º<\/span>/);
  assert.match(salida, /<b>Antonelli<\/b><small><span>Mercedes<\/span><span class="mono">320 pts<\/span>/);
  assert.match(salida, />\s*ANT\s*</);
  assert.match(salida, /data-wiki="https:\/\/en\.wikipedia\.org\/wiki\/Andrea_Kimi_Antonelli"/);
  assert.match(salida, /--eq:#00D7B6/);
});

test("con foto de cuerpo entero: va esa, comparte nombre de transición y se saca si no carga", () => {
  const conFoto = { ...DATOS, pilotos: [{ ...PILOTO_ANT, foto_cuerpo: "https://cdn/ant.webp" }] };
  const salida = String(armarPilotos(conFoto, "pilotos", 2026, COMUN));
  assert.match(salida, /<img class="cuerpo-foto" src="https:\/\/cdn\/ant\.webp"/);
  assert.match(salida, /view-transition-name:foto-antonelli/);
  assert.match(salida, /onerror="this\.remove\(\)"/);
  assert.doesNotMatch(salida, /data-wiki/);
});

test("con sólo la foto de busto (2018-2025) se usa esa", () => {
  const conFoto = { ...DATOS, pilotos: [{ ...PILOTO_ANT, headshot_url: "https://media.formula1.com/ant.png" }] };
  const salida = String(armarPilotos(conFoto, "pilotos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/ant\.png"/);
  assert.doesNotMatch(salida, /data-wiki|cuerpo-foto/);
});

test("grilla de equipos: logo, auto si hay, e iniciales si no hay logo", () => {
  const sinLogo = { ...EQUIPO_MER, constructor_id: "brabham", nombre: "Brabham-Alfa Romeo" };
  const salida = String(armarPilotos({ ...DATOS, equipos: [EQUIPO_MER, sinLogo] }, "equipos", 2026, COMUN));
  assert.match(salida, /<img src="https:\/\/media\.formula1\.com\/mercedes\.png"/);
  assert.match(salida, /<img class="auto" src="https:\/\/cdn\/mercedes-auto\.webp"/);
  assert.match(salida, /href="#\/equipo\/2026\/mercedes"/);
  assert.match(salida, /1º · 556 pts/);
  assert.match(salida, />BAR</);
  assert.equal(salida.match(/class="auto"/g).length, 1);
});
```

- [ ] **Step 3: Correr y ver que fallan**

Run: `node --test "web/test/pilotos.test.js"`
Expected: FAIL — no aparece `<span class="num">12</span>`.

- [ ] **Step 4: Implementar**

En `web/js/vistas/pilotos.js`, debajo de `armarFoto`:

```js
// Foto de cuerpo entero (temporada en curso) para la grilla y la portada de
// la ficha; comparten view-transition-name, así la foto "viaja" de una a otra.
// Si la imagen no carga (404 del CDN), se saca y queda el fondo de color.
export function armarRetrato(p, color) {
  if (p.foto_cuerpo) {
    return html`<img class="cuerpo-foto" src="${p.foto_cuerpo}" alt="" loading="lazy" onerror="this.remove()" style="view-transition-name:foto-${p.driver_id}">`;
  }
  return armarFoto(p, color, "foto");
}
```

Y en `armarPilotos`, reemplazar el bloque `const tarjetas = …;` por:

```js
  const tarjetas = solapa === "equipos"
    ? lista.map((e) => {
      const auto = comun.autos?.[e.constructor_id];
      return html`<a class="tpil equipo" href="#/equipo/${anio}/${e.constructor_id}" style="--eq:${comun.colores[e.constructor_id] ?? GRIS}">
        ${armarLogo(e, comun)}
        ${auto ? html`<img class="auto" src="${auto}" alt="" loading="lazy" onerror="this.remove()">` : ""}
        <span class="info"><b>${e.nombre}</b><small>${e.posicion ? `${e.posicion}º · ` : ""}${numero(e.puntos)} pts</small></span>
      </a>`;
    })
    : lista.map((p) => {
      const color = comun.colores[p.constructor_id];
      return html`<a class="tpil piloto" href="#/piloto/${anio}/${p.driver_id}" style="--eq:${color ?? GRIS}">
        <span class="num">${p.numero ?? ""}</span>
        ${p.posicion ? html`<span class="pos-chip mono">${p.posicion}º</span>` : ""}
        ${armarRetrato(p, color)}
        <span class="info"><b>${p.apellido}</b><small><span>${p.equipo}</span><span class="mono">${numero(p.puntos)} pts</span></small></span>
      </a>`;
    });
```

- [ ] **Step 5: CSS**

En `web/style.css`, sección Pilotos y equipos: reemplazar `.grilla` y las tres reglas `.tpil …` por:

```css
.grilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
.tpil {
  position: relative; display: flex; flex-direction: column; overflow: hidden;
  background: var(--surface); border: 1px solid var(--borde); border-radius: 14px;
  transition: transform .12s;
}
.tpil:active { transform: scale(.97); }
.tpil .info { display: flex; flex-direction: column; gap: 1px; padding: 8px 10px 10px; }
.tpil b { font-size: 14px; font-weight: 600; }
.tpil small { font-size: 12px; color: var(--muted); }
.tpil.piloto { height: 236px; background: color-mix(in srgb, var(--eq) 34%, var(--panel)); box-shadow: inset 0 -3px var(--eq); }
.tpil.piloto .num { position: absolute; left: 10px; top: 4px; font: 700 64px/1 var(--titulo); color: rgba(255, 255, 255, .14); }
.tpil.piloto .pos-chip { position: absolute; z-index: 1; right: 8px; top: 8px; padding: 3px 6px; font-size: 11px; font-weight: 600; background: rgba(9, 10, 13, .7); border-radius: 6px; }
.tpil.piloto .cuerpo-foto { position: absolute; right: -6px; top: 14px; width: 78%; }
.tpil.piloto .foto { position: absolute; inset: 0 0 auto; height: 170px; background: none; }
.tpil.piloto .info {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 28px 12px 12px;
  background: linear-gradient(transparent, rgba(9, 10, 13, .92) 40%);
}
.tpil.piloto .info b { font: 700 18px/1.1 var(--titulo); text-transform: uppercase; }
.tpil.piloto .info small { display: flex; justify-content: space-between; color: var(--texto2); }
.tpil.equipo .auto { display: block; width: 100%; padding: 0 8px; margin-top: -12px; }
```

- [ ] **Step 6: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 7: Verlo andar**

Con el server, `#/pilotos/2026` (después de correr la Task 1 hay `foto_cuerpo`), `#/pilotos/2026/equipos`, `#/pilotos/2010` (fotos de busto) y `#/pilotos/1985` (siglas o Wikipedia). Expected: tarjetas como la pantalla 2 del canvas; nada roto en los años viejos.

- [ ] **Step 8: Commit**

```bash
git add web/js/vistas/pilotos.js web/style.css web/test/pilotos.test.js web/test/datos.js
git commit -m "Web: grilla de pilotos y equipos con fotos oficiales y autos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Ficha del piloto — portada, carrera por carrera en lista, banda y carrera completa fijas

**Files:**
- Modify: `web/js/vistas/ficha_piloto.js` (reescritura)
- Modify: `web/js/vistas/pilotos.js` (sumar `comprimirAlBajar`)
- Modify: `web/style.css` (sacar `.grafico …`, sumar portada/banda/filas/carrera fija)
- Test: `web/test/pilotos.test.js`

**Interfaces:**
- Consumes: `gpCorto` (Task 2), `bandera` de `filas.js` (Task 3), `armarRetrato`/`armarFoto`/`cargarFotos` de `pilotos.js` (Task 5).
- Produces:
  - `filasCarrera(tira, comun) -> Array<{ ronda, bandera, gp, largada, texto, clase: "gano"|"podio"|"puntos"|""|"fuera", delta, claseDelta: "sube"|"baja"|"" }>`, de la ronda más reciente a la más vieja.
  - `comprimirAlBajar(main) -> (() => void) | undefined` en `pilotos.js`: necesita en la vista un `.banda` y un `.portada h2`. La usa también la Task 7.
  - Clases compartidas con la Task 7: `.banda`, `.portada`, `.portada-texto`, `.carrera-fila`, `.caja`.
  - Se borra `armarGrafico`.

- [ ] **Step 1: Escribir los tests que fallan**

En `web/test/pilotos.test.js`: cambiar el import a `import { armarFichaPiloto, filasCarrera } from "../js/vistas/ficha_piloto.js";`, borrar el test "gráfico carrera por carrera…" y reemplazar los dos tests de la ficha por:

```js
test("ficha del piloto: portada, temporada y carrera completa fija abajo", () => {
  const salida = String(armarFichaPiloto(PILOTO_ANT, PILOTO_ANT.carrera, COMUN, 2026));
  assert.match(salida, /Mercedes · #12/);
  assert.match(salida, /Italia · 20 años en 2026/);
  assert.match(salida, /<h2>Antonelli<\/h2>/);
  assert.match(salida, /<small>CAMPEONATO<\/small><b>1º<\/b>/);
  assert.match(salida, /<b>4\.3<\/b><small>Prom\. largada/);   // 4.25 redondeado a un decimal
  assert.match(salida, /class="carrera-fija"[\s\S]*<b>16<\/b><small>GPs[\s\S]*<b>2026<\/b><small>Debut/);
  assert.match(salida, /class="banda"[\s\S]*?ANT[\s\S]*?<b>Antonelli<\/b>/);   // sigla mientras no hay foto
});

test("ficha sin carrera previa ni promedios", () => {
  const sinStats = { ...PILOTO_ANT, stats: { ...PILOTO_ANT.stats, prom_llegada: null, prom_largada: null, posicion: null } };
  const salida = String(armarFichaPiloto(sinStats, null, COMUN, 2026));
  assert.match(salida, /<small>CAMPEONATO<\/small><b>—<\/b>/);
  assert.match(salida, /<b>—<\/b><small>Prom\. llegada/);
  assert.match(salida, /class="carrera-fija"[\s\S]*Sin datos de carrera/);
});

test("ficha con foto de cuerpo entero: misma transición que la grilla", () => {
  const salida = String(armarFichaPiloto({ ...PILOTO_ANT, foto_cuerpo: "https://cdn/ant.webp" }, null, COMUN, 2026));
  assert.match(salida, /<img class="cuerpo-foto" src="https:\/\/cdn\/ant\.webp"[^>]*view-transition-name:foto-antonelli/);
});

test("carrera por carrera: la más reciente primero, con últimas 5 y links", () => {
  const salida = String(armarFichaPiloto(PILOTO_ANT, null, COMUN, 2026));
  assert.match(salida, /Últimas 5/);
  assert.ok(salida.indexOf('href="#/gp/2026/2"') < salida.indexOf('href="#/gp/2026/1"'));
  assert.match(salida, /href="#\/gp\/2026\/2"[\s\S]*?<span class="caja mono fuera">DNF<\/span>/);
  const vacia = String(armarFichaPiloto({ ...PILOTO_ANT, tira: [] }, null, COMUN, 2026));
  assert.match(vacia, /Todavía no corrió en esta temporada/);
  assert.doesNotMatch(vacia, /Últimas 5/);
});

test("filas de carrera por carrera: caja según el puesto y puestos ganados", () => {
  const tira = [
    { ronda: 1, gp: "Azerbaijan Grand Prix", pais: "Azerbaijan", largada: 2, posicion: 2, posicion_texto: "2" },
    { ronda: 2, gp: "X Grand Prix", pais: "Nowhere", largada: 19, posicion: 1, posicion_texto: "1" },
    { ronda: 3, gp: "X Grand Prix", pais: "Nowhere", largada: 1, posicion: 15, posicion_texto: "15" },
    { ronda: 4, gp: "X Grand Prix", pais: "Nowhere", largada: 0, posicion: 7, posicion_texto: "7" },
    { ronda: 5, gp: "X Grand Prix", pais: "Nowhere", largada: 3, posicion: null, posicion_texto: "D" },
  ];
  const [r5, r4, r3, r2, r1] = filasCarrera(tira, COMUN);
  assert.deepEqual(r1, { ronda: 1, bandera: "az", gp: "Azerbaiyán", largada: 2, texto: 2, clase: "podio", delta: "=", claseDelta: "" });
  assert.equal(r2.clase, "gano");
  assert.equal(r2.delta, "▲18");
  assert.equal(r2.claseDelta, "sube");
  assert.equal(r3.clase, "");
  assert.equal(r3.delta, "▼14");
  assert.equal(r4.clase, "puntos");
  assert.equal(r4.delta, "");                        // largó desde boxes: sin ▲/▼
  assert.equal(r4.largada, 0);
  assert.equal(r5.texto, "DSQ");
  assert.equal(r5.clase, "fuera");
  assert.equal(r5.delta, "");
  assert.equal(r2.bandera, null);
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `node --test "web/test/pilotos.test.js"`
Expected: FAIL — no existe el export `filasCarrera`.

- [ ] **Step 3: `comprimirAlBajar` en `pilotos.js`**

Agregar al final de `web/js/vistas/pilotos.js`:

```js
// Fichas: cuando el nombre grande de la portada sale de pantalla, entra la
// banda chica (foto/logo + nombre) pegada debajo del encabezado.
export function comprimirAlBajar(main) {
  const banda = main.querySelector(".banda");
  const nombre = main.querySelector(".portada h2");
  if (!banda || !nombre) return undefined;
  const alto = document.getElementById("encabezado").offsetHeight;
  banda.style.top = `${alto}px`;
  const observador = new IntersectionObserver(([e]) =>
    banda.classList.toggle("visible", !e.isIntersecting && e.boundingClientRect.top < alto),
  { rootMargin: `-${alto}px 0px 0px 0px` });
  observador.observe(nombre);
  return () => observador.disconnect();
}
```

- [ ] **Step 4: Reescribir `ficha_piloto.js`**

Reemplazar el archivo entero por:

```js
import { html } from "../html.js";
import { edadEn, gpCorto, numero, sumarCarrera } from "../formato.js";
import { carrerasPrevias, temporada } from "../api.js";
import { bandera } from "./filas.js";
import { armarFoto, armarRetrato, cargarFotos, comprimirAlBajar } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Pilotos", volver: `#/pilotos/${ruta.anio}` });

const GRIS = "#3F4957";
const promedio = (v) => (v == null ? "—" : v.toFixed(1));
// positionText de Ergast cuando no hay posición: D descalificado, F no
// clasificó, W no largó; el resto, abandono.
const TEXTO_SIN_POSICION = { D: "DSQ", F: "DNQ", W: "NC" };

// ponytail: "sumó puntos" = top 10, como desde 2010; antes puntuaban menos
// puestos. Si molesta, exportar los puntos de cada carrera en la tira.
const claseCaja = (p) => (!p ? "fuera" : p === 1 ? "gano" : p <= 3 ? "podio" : p <= 10 ? "puntos" : "");

export function filasCarrera(tira, comun) {
  return [...tira].reverse().map((t) => {
    const p = t.posicion;
    // Largada 0 = desde boxes: no hay puestos ganados que contar.
    const g = p && t.largada ? t.largada - p : null;
    return {
      ronda: t.ronda,
      bandera: comun.banderas[t.pais] ?? null,
      gp: gpCorto(comun.eventos[t.gp] ?? t.gp),
      largada: t.largada ?? null,
      texto: p ?? TEXTO_SIN_POSICION[t.posicion_texto] ?? "DNF",
      clase: claseCaja(p),
      delta: g == null ? "" : g > 0 ? `▲${g}` : g < 0 ? `▼${-g}` : "=",
      claseDelta: g > 0 ? "sube" : g < 0 ? "baja" : "",
    };
  });
}

const textoLargada = (largada) => (largada === 0 ? "Largó desde boxes" : largada ? `Largó ${largada}º` : "");

const armarFila = (f, anio) => html`<a class="carrera-fila" href="#/gp/${anio}/${f.ronda}">
    <span class="ronda mono">R${f.ronda}</span>${bandera(f.bandera)}
    <span class="nombre"><b>${f.gp}</b><small>${textoLargada(f.largada)}</small></span>
    <span class="caja mono ${f.clase}">${f.texto}</span><span class="delta mono ${f.claseDelta}">${f.delta}</span>
  </a>`;

function armarCarreraCompleta(carrera) {
  return html`<div class="carrera-fija"><span class="eti">CARRERA COMPLETA</span>${carrera
    ? html`<div class="cinco">${[
      ["Títulos", carrera.titulos], ["Victorias", carrera.victorias], ["Podios", carrera.podios],
      ["GPs", carrera.gps], ["Debut", carrera.debut ?? "—"],
    ].map(([etiqueta, valor]) => html`<div><b>${valor}</b><small>${etiqueta}</small></div>`)}</div>`
    : html`<p class="muted nota">Sin datos de carrera.</p>`}</div>`;
}

export function armarFichaPiloto(p, carrera, comun, anio) {
  const color = comun.colores[p.constructor_id] ?? GRIS;
  const logo = comun.logos[p.constructor_id];
  const equipo = [p.equipos.join(" / ") || p.equipo, p.numero ? `#${p.numero}` : ""].filter(Boolean).join(" · ");
  const meta = [
    comun.nacionalidades[p.nacionalidad] ?? p.nacionalidad,
    p.nacimiento ? `${edadEn(p.nacimiento, anio)} años en ${anio}` : "",
  ].filter(Boolean).join(" · ");
  const s = p.stats;
  const filas = filasCarrera(p.tira, comun);
  return html`<div class="banda" style="--eq:${color}" aria-hidden="true">
      ${armarFoto(p, color, "avatar chico")}<span class="banda-texto"><small>${p.nombre}</small><b>${p.apellido}</b></span>
    </div>
    <section class="portada" style="--eq:${color}">
      <span class="dorsal">${p.numero ?? ""}</span>
      ${p.foto_cuerpo ? armarRetrato(p, color) : armarFoto(p, color, "avatar grande")}
      <div class="portada-texto">
        <span class="sec meta">${logo ? html`<img class="logo-chico" src="${logo}" alt="" onerror="this.remove()">` : ""}${equipo}</span>
        <span class="nombre-chico">${p.nombre}</span>
        <h2>${p.apellido}</h2>
        <span class="muted meta">${meta}</span>
      </div>
    </section>
    <div class="cuerpo">
      <div class="grandes">
        <div><small>CAMPEONATO</small><b>${s.posicion ? `${s.posicion}º` : "—"}</b></div>
        <div><small>PUNTOS</small><b>${numero(s.puntos)}</b></div>
        <div><small>VICTORIAS</small><b>${s.victorias}</b></div>
      </div>
      <div class="stats">${[
        ["Podios", s.podios], ["Poles", s.poles], ["Abandonos", s.abandonos],
        ["Prom. llegada", promedio(s.prom_llegada)], ["Prom. largada", promedio(s.prom_largada)],
      ].map(([etiqueta, valor]) => html`<div><b>${valor}</b><small>${etiqueta}</small></div>`)}</div>
      <h3 class="mes">CARRERA POR CARRERA</h3>
      ${filas.length
        ? html`<div class="ultimas"><span class="muted nota">Últimas 5</span>${filas.slice(0, 5).map((f) =>
          html`<span class="caja mono ${f.clase}">${f.texto}</span>`)}</div>
          <div class="filas">${filas.map((f) => armarFila(f, anio))}</div>`
        : html`<p class="muted">Todavía no corrió en esta temporada.</p>`}
    </div>
    ${armarCarreraCompleta(carrera)}`;
}

export async function render(ruta, comun) {
  // La carrera completa es la misma mire el año que mire: previas + lo que
  // lleva en la temporada en curso.
  const [datos, previas, enCurso] = await Promise.all([
    temporada(ruta.anio, comun),
    carrerasPrevias().catch(() => ({})),
    temporada(comun.anio_actual, comun).catch(() => null),
  ]);
  const piloto = datos?.pilotos.find((p) => p.driver_id === ruta.id);
  if (!piloto) {
    return html`<div class="estado"><h3>Sin ficha</h3><p>No hay datos de este piloto en ${ruta.anio}.</p></div>`;
  }
  const actual = enCurso?.pilotos.find((p) => p.driver_id === ruta.id)?.carrera ?? null;
  return armarFichaPiloto(piloto, sumarCarrera(previas[ruta.id] ?? null, actual), comun, ruta.anio);
}

export function montar(main) {
  cargarFotos(main);
  return comprimirAlBajar(main);
}
```

- [ ] **Step 5: CSS**

En `web/style.css`: borrar las 6 reglas `.grafico …`. Agregar al final de la sección Pilotos y equipos:

```css
/* Fichas: portada grande, banda que la reemplaza al bajar y filas. */
.portada {
  position: relative; height: 340px; overflow: hidden;
  background: color-mix(in srgb, var(--eq) 30%, var(--sunken)); box-shadow: inset 0 -3px var(--eq);
}
.portada .dorsal { position: absolute; left: -6px; top: -36px; font: 700 260px/1 var(--titulo); color: rgba(255, 255, 255, .08); }
.portada .cuerpo-foto { position: absolute; right: -8px; top: 18px; width: 210px; }
.portada .avatar.grande { position: absolute; right: 24px; top: 40px; width: 120px; height: 120px; font-size: 40px; }
.portada::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 170px; background: linear-gradient(transparent, rgba(9, 10, 13, .95)); }
.portada-texto { position: absolute; z-index: 1; left: 16px; right: 16px; bottom: 18px; display: flex; flex-direction: column; gap: 2px; }
.portada-texto .meta { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.logo-chico { height: 18px; }
.nombre-chico { font-size: 18px; color: var(--texto2); }
.portada h2 { font: 700 44px/.95 var(--titulo); text-transform: uppercase; }
.banda {
  position: fixed; z-index: 1; left: 0; right: 0; height: 56px; display: flex; align-items: center; gap: 10px; padding: 0 16px;
  background: color-mix(in srgb, var(--eq) 30%, var(--sunken)); border-bottom: 2px solid var(--eq);
  box-shadow: 0 8px 20px rgba(0, 0, 0, .4);
  opacity: 0; transform: translateY(-8px); pointer-events: none; transition: opacity .2s, transform .2s;
}
.banda.visible { opacity: 1; transform: none; }
.banda-texto { display: flex; flex-direction: column; line-height: 1.1; }
.banda-texto small { font-size: 12px; color: var(--texto2); }
.banda-texto b { font: 700 20px var(--titulo); text-transform: uppercase; }
.avatar.chico { width: 38px; height: 38px; font-size: 14px; border: 2px solid var(--eq); }
.ultimas { display: flex; align-items: center; gap: 6px; }
.ultimas .nota { margin-right: 4px; }
.carrera-fila {
  display: flex; align-items: center; gap: 10px; min-height: 52px; padding: 0 4px;
  border-bottom: 1px solid var(--borde-suave); transition: background .12s;
}
.carrera-fila:active { background: var(--hover); }
.carrera-fila .ronda { width: 28px; flex: none; font-size: 12px; color: var(--muted); }
.caja {
  width: 38px; height: 30px; flex: none; display: grid; place-items: center; border-radius: 7px;
  font-size: 15px; font-weight: 700; border: 1px solid transparent; color: var(--muted);
}
.ultimas .caja { width: 30px; height: 26px; font-size: 13px; }
.caja.gano { background: var(--texto); color: var(--app); }
.caja.podio { background: var(--borde-fuerte); color: var(--texto); }
.caja.puntos { border-color: var(--borde-fuerte); color: var(--texto); }
.caja.fuera { color: var(--error); }
.delta { width: 40px; flex: none; text-align: right; font-size: 12px; font-weight: 600; color: var(--futuro); }
.delta.sube { color: var(--dato); }
.delta.baja { color: var(--error); }
.carrera-fija {
  position: sticky; z-index: 1; bottom: calc(var(--alto-tabbar) + env(safe-area-inset-bottom));
  display: flex; flex-direction: column; gap: 6px; padding: 8px 16px 10px;
  background: var(--panel); border-top: 1px solid var(--borde);
}
.carrera-fija .eti { font-size: 10px; }
.cinco { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 4px; text-align: center; }
.cinco b { display: block; font: 600 16px var(--mono); }
.cinco small { font-size: 10px; color: var(--muted); }
```

- [ ] **Step 6: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 7: Verlo andar**

Con el server, `#/piloto/2026/antonelli` en modo celular. Expected: igual a la pantalla 8 del canvas — al bajar entra la banda con foto y nombre; "Carrera completa" queda fija sobre las pestañas; la última fila no queda tapada al llegar abajo. Probar `#/piloto/1988/senna` (sin foto oficial: avatar con sigla/Wikipedia en portada y banda).

- [ ] **Step 8: Commit**

```bash
git add web/js/vistas/ficha_piloto.js web/js/vistas/pilotos.js web/style.css web/test/pilotos.test.js
git commit -m "Web: ficha del piloto con carrera por carrera en lista, banda al bajar y carrera completa fija

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Ficha del equipo — portada con auto, marcador y cara a cara en lista

**Files:**
- Modify: `web/js/vistas/ficha_equipo.js` (reescritura)
- Modify: `web/style.css` (sacar `.tira …` y `.duelo-cab`; sumar marcador/filas)
- Test: `web/test/ficha_equipo.test.js`

**Interfaces:**
- Consumes: `comprimirAlBajar`, `armarFoto`, `armarLogo`, `cargarFotos` (`pilotos.js`); `bandera` (`filas.js`); `gpCorto`, `sigla`, `numero` (`formato.js`); clases `.banda`, `.portada`, `.carrera-fila`, `.caja` (Task 6).
- Produces: `filasCaraACara(cara, comun) -> Array<{ ronda, bandera, gp, a: { texto, gana }, b: { texto, gana } }>` (más reciente primero); `tiraMarcador(cara) -> Array<0|1|null>` (por ronda, de la 1 en adelante).

- [ ] **Step 1: Escribir los tests que fallan**

Reemplazar `web/test/ficha_equipo.test.js` entero por:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { armarFichaEquipo, filasCaraACara, tiraMarcador } from "../js/vistas/ficha_equipo.js";
import { COMUN, EQUIPO_MER } from "./datos.js";

test("portada con auto y números grandes", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /CONSTRUCTORES 2026/);
  assert.match(salida, /<h2>Mercedes<\/h2>/);
  assert.match(salida, /Antonelli · Russell/);
  assert.match(salida, /<img class="auto" src="https:\/\/cdn\/mercedes-auto\.webp"/);
  assert.match(salida, /<small>POSICIÓN<\/small><b>1º<\/b>/);
  assert.match(salida, /<small>DOBLETES<\/small><b>3<\/b>/);
  assert.match(salida, /class="banda"/);
});

test("cara a cara: marcador, tira de rondas y barras en proporción", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.match(salida, /class="marcador mono"><b class="a">11<\/b>–<b>5<\/b>/);
  assert.match(salida, /class="marcas"[^>]*><i class="b"><\/i><i class="a"><\/i><\/div>/);
  assert.match(salida, /<b>11<\/b>[\s\S]*?width:68\.75%[\s\S]*?Carrera[\s\S]*?width:31\.25%[\s\S]*?<b class="der">5<\/b>/);
});

test("carrera por carrera: la más reciente primero, lleno el que llegó adelante", () => {
  const salida = String(armarFichaEquipo(EQUIPO_MER, COMUN, 2026));
  assert.ok(salida.indexOf('href="#/gp/2026/2"') < salida.indexOf('href="#/gp/2026/1"'));
  assert.match(salida, /href="#\/gp\/2026\/2"[\s\S]*?<span class="caja mono gana">1<\/span><span class="caja mono">DNF<\/span>/);
  assert.match(salida, /href="#\/gp\/2026\/1"[\s\S]*?<span class="caja mono">2<\/span><span class="caja mono gana">1<\/span>/);
});

test("filas y tira del cara a cara", () => {
  const cara = EQUIPO_MER.cara_a_cara;
  const [r2, r1] = filasCaraACara(cara, COMUN);
  assert.deepEqual(r2.a, { texto: 1, gana: true });
  assert.deepEqual(r2.b, { texto: "DNF", gana: false });
  assert.equal(r1.ronda, 1);
  assert.deepEqual(tiraMarcador(cara), [1, 0]);
});

test("equipo sin dos pilotos en una misma carrera", () => {
  const salida = String(armarFichaEquipo({ ...EQUIPO_MER, cara_a_cara: null }, COMUN, 2026));
  assert.match(salida, /Este equipo no tuvo dos pilotos en una misma carrera/);
  assert.doesNotMatch(salida, /Antonelli · Russell|class="marcador/);
});
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `node --test "web/test/ficha_equipo.test.js"`
Expected: FAIL — no existe el export `filasCaraACara`.

- [ ] **Step 3: Reescribir `ficha_equipo.js`**

Reemplazar el archivo entero por:

```js
import { html } from "../html.js";
import { gpCorto, numero, sigla } from "../formato.js";
import { temporada } from "../api.js";
import { bandera } from "./filas.js";
import { armarFoto, armarLogo, cargarFotos, comprimirAlBajar } from "./pilotos.js";

export const encabezado = (ruta) => ({ titulo: "Equipos", volver: `#/pilotos/${ruta.anio}/equipos` });

// Las filas de ui/fichas_pilotos.FichaEquipo.
const FILAS_DUELO = [
  ["clasificacion", "Clasificación"], ["carrera", "Carrera"], ["puntos", "Puntos"],
  ["victorias", "Victorias"], ["podios", "Podios"], ["poles", "Poles"],
];

const posicion = (fila) => fila.posicion ?? "DNF";

export function filasCaraACara(cara, comun) {
  return [...cara.por_carrera].reverse().map((c) => ({
    ronda: c.ronda,
    bandera: comun.banderas[c.pais] ?? null,
    gp: gpCorto(comun.eventos[c.gp] ?? c.gp),
    a: { texto: posicion(c.a), gana: c.adelante === 0 },
    b: { texto: posicion(c.b), gana: c.adelante === 1 },
  }));
}

// Quién llegó adelante en cada ronda (0 = a, 1 = b), de la primera a la última.
export const tiraMarcador = (cara) => [...cara.por_carrera].sort((x, y) => x.ronda - y.ronda).map((c) => c.adelante);

function armarDuelo(cara, color, comun, anio) {
  const [x, y] = cara.carrera;
  const tira = tiraMarcador(cara);
  const lado = (p, der) => html`<span class="lado ${der ? "der" : ""}">${armarFoto(p, color, "avatar chico")}
    <span><b>${sigla(p)}</b><small>${p.apellido}</small></span></span>`;
  return html`<div class="cara-a-cara">${lado(cara.a, false)}
      <span class="marcador mono"><b class="a">${x}</b>–<b>${y}</b></span>${lado(cara.b, true)}</div>
    <p class="muted nota centro">Quién llegó adelante, ronda por ronda</p>
    <div class="marcas" style="grid-template-columns:repeat(${tira.length}, minmax(0, 1fr))">${tira.map((q) =>
      html`<i class="${q === 0 ? "a" : q === 1 ? "b" : ""}"></i>`)}</div>
    <div class="duelos">${FILAS_DUELO.map(([clave, etiqueta]) => {
      const [va, vb] = cara[clave];
      const parteA = va + vb ? (va / (va + vb)) * 100 : 50;
      return html`<div class="duelo">
        <b>${numero(va)}</b>
        <span class="bar izq"><i style="width:${parteA}%;background:var(--eq)"></i></span>
        <span class="muted">${etiqueta}</span>
        <span class="bar"><i style="width:${100 - parteA}%"></i></span>
        <b class="der">${numero(vb)}</b>
      </div>`;
    })}</div>
    <h3 class="mes">CARRERA POR CARRERA</h3>
    <div class="filas-cab"><span>GP</span><span>${sigla(cara.a)}</span><span>${sigla(cara.b)}</span></div>
    <div class="filas">${filasCaraACara(cara, comun).map((f) => html`<a class="carrera-fila" href="#/gp/${anio}/${f.ronda}">
      <span class="ronda mono">R${f.ronda}</span>${bandera(f.bandera)}
      <span class="nombre"><b>${f.gp}</b></span>
      <span class="${f.a.gana ? "caja mono gana" : "caja mono"}">${f.a.texto}</span><span class="${f.b.gana ? "caja mono gana" : "caja mono"}">${f.b.texto}</span>
    </a>`)}</div>`;
}

export function armarFichaEquipo(e, comun, anio) {
  const cara = e.cara_a_cara;
  const color = comun.colores[e.constructor_id] ?? "var(--dato)";
  const auto = comun.autos?.[e.constructor_id];
  return html`<div class="banda" style="--eq:${color}" aria-hidden="true">
      ${armarLogo(e, comun, "avatar chico cuadrado")}<span class="banda-texto"><small>CONSTRUCTORES ${anio}</small><b>${e.nombre}</b></span>
    </div>
    <section class="portada equipo" style="--eq:${color}">
      <div class="portada-texto">
        <span class="eti">CONSTRUCTORES ${anio}</span>
        <h2>${e.nombre}</h2>
        ${cara ? html`<span class="sec meta">${cara.a.apellido} · ${cara.b.apellido}</span>` : ""}
      </div>
      ${armarLogo(e, comun, "logo-portada")}
      ${auto ? html`<img class="auto" src="${auto}" alt="" onerror="this.remove()">` : ""}
    </section>
    <div class="cuerpo" style="--eq:${color}">
      <div class="grandes cuatro">
        <div><small>POSICIÓN</small><b>${e.posicion ? `${e.posicion}º` : "—"}</b></div>
        <div><small>PUNTOS</small><b>${numero(e.puntos)}</b></div>
        <div><small>VICTORIAS</small><b>${e.stats.victorias}</b></div>
        <div><small>DOBLETES</small><b>${e.stats.dobletes}</b></div>
      </div>
      <h3 class="mes">CARA A CARA · QUIÉN TERMINÓ ADELANTE</h3>
      ${cara ? armarDuelo(cara, color, comun, anio) : html`<p class="muted">Este equipo no tuvo dos pilotos en una misma carrera.</p>`}
    </div>`;
}

export async function render(ruta, comun) {
  const datos = await temporada(ruta.anio, comun);
  const equipo = datos?.equipos.find((e) => e.constructor_id === ruta.id);
  if (!equipo) {
    return html`<div class="estado"><h3>Sin ficha</h3><p>No hay datos de este equipo en ${ruta.anio}.</p></div>`;
  }
  return armarFichaEquipo(equipo, comun, ruta.anio);
}

export function montar(main) {
  cargarFotos(main);
  return comprimirAlBajar(main);
}
```

- [ ] **Step 4: CSS**

En `web/style.css`: borrar `.duelo-cab`, las tres reglas `.tira …` y las de `.cabcolor` / `.cabcolor-texto` (ya no las usa ninguna vista). Agregar al final de la sección Pilotos y equipos:

```css
.portada.equipo { height: 240px; }
.portada.equipo .portada-texto { top: 18px; bottom: auto; }
.portada.equipo .portada-texto h2 { font-size: 40px; }
.portada.equipo .logo-portada { position: absolute; z-index: 1; right: 16px; top: 18px; height: 30px; display: grid; place-items: center; font: 700 18px var(--titulo); }
.portada.equipo .logo-portada img { max-height: 30px; }
.portada.equipo .auto { position: absolute; z-index: 1; left: 12px; right: 12px; bottom: 14px; width: calc(100% - 24px); }
.portada.equipo::after { display: none; }
.cara-a-cara { display: flex; align-items: center; justify-content: space-between; }
.cara-a-cara .lado { display: flex; align-items: center; gap: 10px; }
.cara-a-cara .lado.der { flex-direction: row-reverse; text-align: right; }
.cara-a-cara .lado b { display: block; font: 700 20px/1 var(--titulo); }
.cara-a-cara .lado small { font-size: 12px; color: var(--muted); }
.marcador { font-size: 34px; font-weight: 700; color: var(--futuro); }
.marcador b { color: var(--texto2); }
.marcador b.a { color: var(--eq); }
.centro { text-align: center; }
.marcas { display: grid; gap: 3px; }
.marcas i { height: 22px; border-radius: 3px; background: var(--surface); }
.marcas i.a { background: var(--eq); }
.marcas i.b { background: var(--texto2); }
.filas-cab { display: flex; gap: 10px; padding: 0 4px 6px; font-size: 11px; letter-spacing: 1px; color: var(--muted); border-bottom: 1px solid var(--borde); }
.filas-cab span:first-child { flex: 1; }
.filas-cab span:not(:first-child) { width: 38px; text-align: center; }
.caja.gana { background: var(--eq); color: var(--app); }
```

- [ ] **Step 5: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 6: Verlo andar**

`#/equipo/2026/mercedes` y `#/equipo/1988/mclaren`. Expected: como la pantalla 4 del canvas; al bajar entra la banda con el logo; en 1988 sin auto ni logo nuevo, con iniciales.

- [ ] **Step 7: Commit**

```bash
git add web/js/vistas/ficha_equipo.js web/style.css web/test/ficha_equipo.test.js
git commit -m "Web: ficha del equipo con auto, marcador y cara a cara en lista

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Esqueleto al cargar, sin conexión, indicador de pestaña y vibración

**Files:**
- Modify: `web/js/app.js` (`mostrar`, `marcarPestana`, click, red)
- Modify: `web/index.html` (indicador en la barra, aviso sin red)
- Modify: `web/style.css`

**Interfaces:**
- Produces: `mostrar()` ya no borra la pantalla anterior hasta que llegan los datos (o pasan 150 ms): la Task 9 envuelve ese cambio en una transición. Variable CSS `--i` en `.tabbar`.

Sin tests automáticos: es DOM puro de `app.js` (el repo no testea `app.js`). Se verifica en el navegador.

- [ ] **Step 1: `index.html`**

Dentro de `<nav class="tabbar" …>`, como primer hijo:

```html
    <span class="indicador" aria-hidden="true"></span>
```

Y después de `</nav>`:

```html
  <div id="sin-red" class="sin-red" role="status" hidden>
    <span>Sin conexión · mostrando lo último guardado</span>
    <button data-reintentar>Reintentar</button>
  </div>
```

- [ ] **Step 2: `app.js` — esqueleto diferido**

Debajo de `const ICONO_SIGUIENTE = …`:

```js
// Si los datos tardan más de 150 ms, un esqueleto; si ya estaban en caché, se
// pasa directo y no parpadea.
const ESPERA_ESQUELETO_MS = 150;
const ESQUELETO = html`<div class="cuerpo esqueleto" aria-busy="true" aria-label="Cargando">
  <span class="sk bloque"></span>${Array.from({ length: 6 }, () => html`<span class="sk renglon"></span>`)}</div>`;
```

En `mostrar()`, reemplazar desde `actual?.limpiar?.();` hasta el final de la función por:

```js
  actual?.limpiar?.();
  actual = { ruta };
  marcarPestana(ruta);
  const pintarEncabezado = () => {
    encabezado.innerHTML = armarEncabezado(ruta, vista.encabezado(ruta), datosComunes.anio_actual);
  };
  const espera = setTimeout(() => {
    if (mio !== turno) return;
    pintarEncabezado();
    main.innerHTML = ESQUELETO;
    window.scrollTo(0, 0);
  }, ESPERA_ESQUELETO_MS);
  try {
    const contenido = await vista.render(ruta, datosComunes);
    clearTimeout(espera);
    if (mio !== turno) return;
    pintarEncabezado();
    main.innerHTML = contenido;
    window.scrollTo(0, 0);
    actual.limpiar = vista.montar?.(main, ruta, datosComunes);
  } catch (error) {
    clearTimeout(espera);
    console.error(error);
    if (mio === turno) pintarEncabezado();
    mostrarError(mio);
  }
}
```

- [ ] **Step 3: `app.js` — indicador de pestaña, vibración y red**

En `marcarPestana`, al final:

```js
  const pestanas = [...document.querySelectorAll(".tabbar a")];
  document.querySelector(".tabbar").style.setProperty("--i", pestanas.findIndex((a) => a.dataset.pestana === pestana));
```

En el listener de `click`, como primera línea:

```js
  if (evento.target.closest(".tabbar a, .segmento a")) navigator.vibrate?.(8);
```

Antes de `mostrar();` al final del archivo:

```js
const sinRed = document.getElementById("sin-red");
const marcarRed = () => { sinRed.hidden = navigator.onLine; };
window.addEventListener("online", marcarRed);
window.addEventListener("offline", marcarRed);
marcarRed();
```

- [ ] **Step 4: CSS**

En `web/style.css`: en `.tabbar a` sacar `border-top: 2px solid transparent; margin-top: -1px;` y cambiar `.tabbar a.activa` a sólo `{ color: var(--texto); }`. Agregar al final del archivo:

```css
/* ---------- Pulido: indicador, esqueleto, sin red, movimiento ---------- */
.tabbar .indicador {
  position: absolute; top: -1px; height: 2px; width: calc(100% / 3 * .36);
  left: calc((var(--i, 0) + .32) * 100% / 3); background: var(--rojo); border-radius: 0 0 2px 2px;
  transition: left .3s cubic-bezier(.3, .7, .2, 1);
}
@keyframes brillo { from { background-position: -400px 0; } to { background-position: 400px 0; } }
.sk {
  display: block; border-radius: 6px; background: var(--surface) linear-gradient(90deg, var(--surface) 0, var(--hover) 120px, var(--surface) 240px) no-repeat;
  background-size: 400px 100%; animation: brillo 1.3s linear infinite;
}
.sk.bloque { height: 220px; border-radius: 12px; }
.sk.renglon { height: 48px; }
.sin-red {
  position: fixed; z-index: 3; left: 12px; right: 12px; bottom: calc(var(--alto-tabbar) + env(safe-area-inset-bottom) + 12px);
  display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 0 6px 0 14px; min-height: 48px;
  font-size: 13px; background: var(--surface); border: 1px solid var(--borde-fuerte); border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, .5);
}
.sin-red[hidden] { display: none; }
.sin-red button { min-height: 44px; padding: 0 10px; font-weight: 600; color: var(--dato); }
.res > a { transition: background .12s; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
```

- [ ] **Step 5: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS (nada cambió en las funciones puras).

- [ ] **Step 6: Verlo andar**

Con el server, en DevTools › Network › "Slow 3G": navegar entre pestañas → aparece el esqueleto con brillo, sin parpadeo cuando vuelve a una pantalla ya cargada; la línea roja se desliza a la pestaña nueva. Network › "Offline" → aparece "Sin conexión · mostrando lo último guardado"; "Online" → se va.

- [ ] **Step 7: Commit**

```bash
git add web/js/app.js web/index.html web/style.css
git commit -m "Web: esqueleto al cargar, aviso sin conexión, indicador de pestaña y vibración

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Transiciones entre pantallas (la foto viaja)

**Files:**
- Modify: `web/js/app.js` (el cambio de contenido en `mostrar`)
- Modify: `web/style.css`

**Interfaces:**
- Consumes: el `view-transition-name:foto-<driver_id>` de `armarRetrato` (Task 5/6); `mostrar()` de la Task 8.

- [ ] **Step 1: Envolver el cambio en una transición**

En `app.js`, debajo de `ESQUELETO`:

```js
// Transición nativa de Chrome: la foto del piloto "viaja" de la grilla a la
// ficha (comparten view-transition-name). Sin soporte, cambio directo.
const transicion = (cambio) => (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches
  ? document.startViewTransition(cambio)
  : cambio());
```

En `mostrar()`, reemplazar el bloque del `try` que pinta el contenido:

```js
    pintarEncabezado();
    main.innerHTML = contenido;
    window.scrollTo(0, 0);
    actual.limpiar = vista.montar?.(main, ruta, datosComunes);
```

por:

```js
    transicion(() => {
      if (mio !== turno) return;
      pintarEncabezado();
      main.innerHTML = contenido;
      window.scrollTo(0, 0);
      actual.limpiar = vista.montar?.(main, ruta, datosComunes);
    });
```

- [ ] **Step 2: CSS**

Agregar al final de `web/style.css`:

```css
::view-transition-old(root), ::view-transition-new(root) { animation-duration: .18s; }
.tabbar { view-transition-name: tabbar; }
.segmento a.activa { view-transition-name: segmento; }
```

- [ ] **Step 3: Correr los tests**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 4: Verlo andar**

Con el server, en `#/pilotos/2026` tocar Antonelli. Expected: la foto se agranda y se mueve hasta la portada de la ficha; "atrás" la devuelve. Pilotos ↔ Equipos: el resaltado del segmento se desliza. La barra de pestañas no parpadea. En el calendario, abrir un GP y volver: la pantalla vuelve a abrir en la próxima (montar corre dentro de la transición).

- [ ] **Step 5: Commit**

```bash
git add web/js/app.js web/style.css
git commit -m "Web: transiciones entre pantallas con la foto que viaja de la grilla a la ficha

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Campana de avisos y push en el service worker

**Files:**
- Create: `web/js/avisos.js`
- Modify: `web/js/app.js` (campana en el encabezado, hoja con la suscripción)
- Modify: `web/js/vistas/calendario.js` (`encabezado` con `campana: true`)
- Modify: `web/sw.js` (`push`, `notificationclick`)
- Modify: `web/style.css`
- Test: `web/test/avisos.test.js`

**Interfaces:**
- Produces: `VAPID_PUBLICA: string` y `claveEnBytes(b64url) -> Uint8Array` en `web/js/avisos.js` (los usa la Task 11 desde Node); `suscribir() -> Promise<{ texto } | { error }>`.
- Payload que espera el service worker (lo manda la Task 11): `{ titulo, cuerpo, tag, url }` en JSON.

- [ ] **Step 1: Generar las claves VAPID (lo hace el usuario)**

Pedirle al usuario que corra `! npx --yes web-push generate-vapid-keys` en esta sesión, que guarde la **Private Key** como secreto `VAPID_PRIVATE` en GitHub (Settings › Secrets and variables › Actions › New repository secret) y que pase la **Public Key** (empieza con `B`, ~87 caracteres). La privada nunca va al repo ni al chat.

- [ ] **Step 2: Escribir el test que falla**

Crear `web/test/avisos.test.js`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { VAPID_PUBLICA, claveEnBytes } from "../js/avisos.js";

test("la clave pública VAPID es un punto P-256 sin comprimir", () => {
  const bytes = claveEnBytes(VAPID_PUBLICA);
  assert.equal(bytes.length, 65);
  assert.equal(bytes[0], 4);
});
```

- [ ] **Step 3: Correr y ver que falla**

Run: `node --test "web/test/avisos.test.js"`
Expected: FAIL — `Cannot find module …/web/js/avisos.js`.

- [ ] **Step 4: Crear `web/js/avisos.js`**

```js
// Suscripción a los avisos antes de cada sesión. La manda .github/workflows/
// avisos.yaml (avisos/enviar.mjs) con la clave privada, que es un secreto del
// repo. Sin servidor, la suscripción se copia a mano como secreto
// PUSH_SUBSCRIPTION: es una app personal, un solo celular.
export const VAPID_PUBLICA = "<PEGAR LA PUBLIC KEY DEL STEP 1>";

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
```

(Reemplazar el texto entre comillas por la Public Key real antes de seguir.)

- [ ] **Step 5: Correr y ver que pasa**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 6: Campana en el encabezado (`calendario.js` y `app.js`)**

En `calendario.js`: `export const encabezado = () => ({ titulo: "Calendario", campana: true });`

En `app.js`, import `import { suscribir } from "./avisos.js";` y un ícono debajo de `ICONO_SIGUIENTE`:

```js
const ICONO_CAMPANA = html`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`;
```

En `armarEncabezado`, en el `return` de primer nivel, entre el `<h1>` y `<div class="temporada">`:

```js
    ${info.campana ? html`<button class="icono-btn campana" data-campana aria-label="Avisos antes de cada sesión">${ICONO_CAMPANA}</button>` : ""}
```

En `mostrar()`, dentro de `pintarEncabezado` después del `innerHTML`, marcar la campana si ya hay suscripción:

```js
    const campana = encabezado.querySelector("[data-campana]");
    navigator.serviceWorker?.ready.then((r) => r.pushManager?.getSubscription())
      .then((s) => campana?.classList.toggle("activa", Boolean(s))).catch(() => {});
```

Agregar la hoja:

```js
// Hoja con la suscripción para copiar como secreto del repo.
async function abrirAvisos() {
  const r = await suscribir().catch((error) => ({ error: `No se pudo activar: ${error.message}` }));
  const capa = document.createElement("div");
  capa.className = "capa";
  capa.innerHTML = html`<div class="velo" data-cerrar-avisos></div><div class="hoja">
    <span class="asa"></span>
    <h3 class="titulo-circuito">Avisos antes de cada sesión</h3>
    ${r.error ? html`<p class="muted">${r.error}</p>` : html`<p class="muted">Copiá este texto y pegalo en GitHub › Settings › Secrets and variables › Actions, como el secreto <b>PUSH_SUBSCRIPTION</b>. Se hace una sola vez.</p>
      <textarea class="suscripcion mono" readonly rows="6">${r.texto}</textarea>
      <button class="boton" data-copiar>Copiar</button>`}
    <button class="boton" data-cerrar-avisos>Cerrar</button>
  </div>`;
  document.body.append(capa);
  document.body.classList.add("con-capa");
  encabezado.querySelector("[data-campana]")?.classList.toggle("activa", !r.error);
}
```

En el listener de `click`, antes de `if (evento.target.closest("[data-reintentar]"))`:

```js
  if (evento.target.closest("[data-campana]")) { abrirAvisos(); return; }
  if (evento.target.closest("[data-cerrar-avisos]")) {
    evento.target.closest(".capa").remove();
    document.body.classList.remove("con-capa");
    return;
  }
  const copiar = evento.target.closest("[data-copiar]");
  if (copiar) {
    navigator.clipboard.writeText(copiar.parentElement.querySelector("textarea").value)
      .then(() => { copiar.textContent = "Copiado ✓"; });
    return;
  }
```

- [ ] **Step 7: `sw.js`**

Agregar al final de `web/sw.js`:

```js
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
```

- [ ] **Step 8: CSS**

Agregar al final de `web/style.css`:

```css
.icono-btn.campana { margin-left: 0; }
.icono-btn.campana.activa { color: var(--dato); }
.suscripcion {
  width: 100%; padding: 10px; resize: none; font-size: 11px; color: var(--texto2);
  background: var(--sunken); border: 1px solid var(--borde); border-radius: 8px;
}
```

- [ ] **Step 9: Verlo andar**

Con el server (localhost cuenta como origen seguro): tocar la campana → Chrome pide permiso → aparece la hoja con un JSON que empieza con `{"endpoint":"https://fcm.googleapis.com/…`; "Copiar" lo copia; la campana queda en cian. En DevTools › Application › Service Workers › "Push" con el texto `{"titulo":"Prueba","cuerpo":"Empieza en 27 min","tag":"x","url":"#/gp/2026/17"}` → aparece la notificación; tocarla abre `#/gp/2026/17`.

- [ ] **Step 10: Commit**

```bash
git add web/js/avisos.js web/js/app.js web/js/vistas/calendario.js web/sw.js web/style.css web/test/avisos.test.js
git commit -m "Web: campana para activar los avisos y push en el service worker

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Envío de los avisos desde GitHub Actions

**Files:**
- Modify: `web/js/formato.js` (`sesionAAvisar`, `idSesion`)
- Test: `web/test/formato.test.js`
- Create: `avisos/package.json`, `avisos/package-lock.json` (generado), `avisos/enviar.mjs`
- Create: `.github/workflows/avisos.yaml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `aEvento` (`formato.js`), `VAPID_PUBLICA` (Task 10), el payload `{ titulo, cuerpo, tag, url }` que lee `sw.js`.
- Produces: `idSesion(ev, sesion) -> "<anio>-<ronda>-<clave>"`; `sesionAAvisar(eventos, ahora, ultimaAvisada) -> { ev, sesion, minutos, id } | null`.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `web/test/formato.test.js` (sumar `sesionAAvisar` al import):

```js
test("aviso: la sesión que empieza en los próximos 35 min, una sola vez", () => {
  const evs = [aEvento(SINGAPUR, COMUN)];
  const antesQualy = Date.parse("2026-10-10T12:33:00Z");          // 27 min antes de las 13:00Z
  const aviso = sesionAAvisar(evs, antesQualy, null);
  assert.equal(aviso.id, "2026-17-Qualifying");
  assert.equal(aviso.minutos, 27);
  assert.equal(aviso.sesion.nombre, "Clasificación");
  assert.equal(aviso.ev.ronda, 17);
  assert.equal(sesionAAvisar(evs, antesQualy, "2026-17-Qualifying"), null);       // ya avisada
  assert.equal(sesionAAvisar(evs, Date.parse("2026-10-10T12:20:00Z"), null), null); // falta 40 min
  assert.equal(sesionAAvisar(evs, Date.parse("2026-10-10T13:05:00Z"), null), null); // ya empezó
  assert.equal(sesionAAvisar([], antesQualy, null), null);
});
```

- [ ] **Step 2: Correr y ver que falla**

Run: `node --test "web/test/formato.test.js"`
Expected: FAIL — no existe el export `sesionAAvisar`.

- [ ] **Step 3: Implementar en `formato.js`**

Debajo de `hayEnVivo`:

```js
// Avisos (avisos/enviar.mjs): la primera sesión que arranca en los próximos
// 35 min y no es la última avisada. Con el workflow cada 10 min (que GitHub
// atrasa a veces), llega entre ~15 y 35 min antes, una sola vez.
const VENTANA_AVISO_MS = 35 * 60_000;
export const idSesion = (ev, s) => `${ev.anio}-${ev.ronda}-${s.clave}`;

export function sesionAAvisar(eventos, ahora, ultimaAvisada) {
  for (const ev of eventos) {
    for (const s of ev.sesiones) {
      const falta = s.fecha.getTime() - ahora;
      const id = idSesion(ev, s);
      if (falta > 0 && falta <= VENTANA_AVISO_MS && id !== ultimaAvisada) {
        return { ev, sesion: s, minutos: Math.round(falta / 60_000), id };
      }
    }
  }
  return null;
}
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `node --test "web/test/*.test.js"`
Expected: PASS.

- [ ] **Step 5: `avisos/package.json` y dependencia**

Crear `avisos/package.json`:

```json
{
  "private": true,
  "type": "module",
  "description": "Manda el push antes de cada sesión (lo corre .github/workflows/avisos.yaml)."
}
```

Run: `npm install web-push --prefix avisos`
Expected: crea `avisos/package-lock.json` y `avisos/node_modules/`, y suma `"dependencies": { "web-push": "^3.x" }` a `avisos/package.json`.

Agregar a `.gitignore`: `avisos/node_modules/` y `avisos/ultima.txt`.

- [ ] **Step 6: `avisos/enviar.mjs`**

```js
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
const prueba = Boolean(process.env.AHORA);
const ahora = prueba ? Date.parse(process.env.AHORA) : Date.now();

async function pedir(url) {
  const respuesta = await fetch(url);
  if (!respuesta.ok) throw new Error(`${respuesta.status} ${url}`);
  return respuesta.json();
}

const anio = new Date(ahora).getUTCFullYear();
const races = (await pedir(`https://api.jolpi.ca/ergast/f1/${anio}.json?limit=100`)).MRData.RaceTable.Races;
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
```

- [ ] **Step 7: Probarlo local, sin secretos**

Run: `node avisos/enviar.mjs`
Expected: `Nada que avisar` (o `Sin secretos configurados: …` si justo hay una sesión cerca).

Run (PowerShell): `$env:AHORA = "2026-10-10T12:33:00Z"; node avisos/enviar.mjs; Remove-Item Env:AHORA`
Expected: `Sin secretos configurados: no se avisa 2026-17-Qualifying`.

- [ ] **Step 8: Workflow**

Crear `.github/workflows/avisos.yaml`:

```yaml
name: Avisos de sesiones
on:
  schedule:
    # Cada 10 min. GitHub a veces lo atrasa: por eso la ventana es de 35 min.
    - cron: "*/10 * * * *"
  workflow_dispatch:
    inputs:
      ahora:
        description: "Simular este momento (ISO, p. ej. 2026-10-10T12:33:00Z). Vacío = ahora."
        required: false

permissions:
  contents: read

concurrency:
  group: avisos

jobs:
  avisar:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "22"
    - name: Última sesión avisada
      uses: actions/cache/restore@v4
      with:
        path: avisos/ultima.txt
        key: aviso-${{ github.run_id }}
        restore-keys: aviso-
    - run: npm ci --omit=dev
      working-directory: avisos
    - id: enviar
      run: node avisos/enviar.mjs
      env:
        AHORA: ${{ inputs.ahora }}
        VAPID_PRIVATE: ${{ secrets.VAPID_PRIVATE }}
        PUSH_SUBSCRIPTION: ${{ secrets.PUSH_SUBSCRIPTION }}
    - name: Recordar la sesión avisada
      if: steps.enviar.outputs.id != ''
      uses: actions/cache/save@v4
      with:
        path: avisos/ultima.txt
        key: aviso-${{ steps.enviar.outputs.id }}
```

- [ ] **Step 9: Commit**

```bash
git add web/js/formato.js web/test/formato.test.js avisos/package.json avisos/package-lock.json avisos/enviar.mjs .github/workflows/avisos.yaml .gitignore
git commit -m "Avisos: push antes de cada sesión desde GitHub Actions, uno por sesión

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Puesta en marcha y prueba en el celular

**Files:** ninguno (pasos del usuario y verificación final).

- [ ] **Step 1: Suite completa**

Run: `node --test "web/test/*.test.js"` y `python -m pytest test_exportar_web.py -q`
Expected: PASS los dos.

- [ ] **Step 2: Integrar y publicar**

Con el OK del usuario, mergear la rama a `master` y pushear (dispara "Publicar web"). Expected: el workflow termina verde y la página publicada muestra fotos oficiales en `#/pilotos/2026`.

- [ ] **Step 3: Activar en el celular (usuario)**

En la app instalada: Calendario › campana › permitir › "Copiar". En GitHub: Settings › Secrets and variables › Actions › New repository secret › `PUSH_SUBSCRIPTION` = el texto copiado. (`VAPID_PRIVATE` ya se cargó en la Task 10.)

- [ ] **Step 4: Prueba de punta a punta**

En GitHub › Actions › "Avisos de sesiones" › Run workflow, con `ahora` = 25 min antes de la próxima sesión real (en UTC). Expected: el job termina verde con "Avisado: …", llega la notificación "<Sesión> · Gran Premio de …" / "Empieza en 25 min", y tocarla abre el GP en la app (probar con la app cerrada y con la app abierta en Pilotos). Como fue una prueba (`ahora` cargado), el aviso real igual va a llegar.

- [ ] **Step 5: Revisar los clics en el celular**

Pendiente desde la PWA anterior: chips de sesión, hoja del circuito, atrás, Reintentar. Más lo nuevo: píldora del calendario, banda de las fichas, carrera completa fija, transición de la foto.
