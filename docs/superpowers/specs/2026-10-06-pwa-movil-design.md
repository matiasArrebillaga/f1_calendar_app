# Versión móvil (PWA): las funciones de escritorio adaptadas al celular

Fecha: 2026-10-06 · Estado: diseño aprobado (variantes recomendadas), pendiente de plan de implementación

## Objetivo

Llevar al celular las funciones de la app de escritorio (calendario, detalle del GP, clasificación,
pilotos y equipos) como la web instalable que ya vive en `web/` y se publica en GitHub Pages. La
app de escritorio no se toca: se reimplementa la interfaz en HTML/JS, adaptada al celular, con el
mismo look (paleta Telemetría, reglas de la casa de `style.qss`).

Criterios de éxito:
- Se puede hacer en el celular todo lo que se hace en escritorio, con las adaptaciones de abajo.
- Cualquier temporada de 1950 a hoy, como el selector de escritorio.
- Los datos de la temporada en curso se actualizan solos, sin que el usuario tenga que correr nada
  después de cada carrera.
- Se abre sin conexión con lo último que se vio.
- El botón/gesto "atrás" de Android funciona en todas las pantallas.

Mockups de referencia (variantes A elegidas): https://claude.ai/artifact/9AJW4DjVSquGBNjTfHnUxg

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Navegación | Barra de pestañas abajo: Calendario · Clasificación · Pilotos. Selector ‹ año › en el encabezado de cada pestaña. |
| Calendario | Variante A: próxima carrera arriba, carreras ya corridas plegadas en "Carreras anteriores · N", tarjetas en una columna. |
| Detalle del GP | Variante A: todo apilado (sesiones como chips → resultados → circuito). |
| Entrenamientos libres y clasificación sprint | Sólo desde 2023 (OpenF1). Antes: "Sin datos para esta sesión". |
| Fichas de pilotos y equipos | Desde JSON generados a partir de la base de `core/historial.py`, no desde la API en vivo. |
| Temporadas | Todas (1950 en adelante). |

## Experiencia

### Estructura común
- **Encabezado** (56 px, `#12161C`): título de la pestaña y selector de temporada ‹ 2026 ›.
  En pantallas de segundo nivel (detalle, fichas) el encabezado lleva "‹ Calendario" / "‹ Pilotos"
  para volver, y el año como texto.
- **Barra de pestañas** fija abajo (64 px), ícono + texto, la activa con el borde superior rojo de
  2 px (regla de la casa: el rojo sólo marca estado). El detalle del GP cuenta como Calendario y las
  fichas como Pilotos, igual que la sidebar de escritorio. Si la ficha se abrió desde Clasificación o
  desde un GP, "atrás" vuelve ahí (lo da el historial del navegador).
- Toques en lugar de doble clic: tocar un piloto/equipo en cualquier tabla abre su ficha.
- Áreas táctiles de 44 px como mínimo.

### Calendario
- Próxima carrera: chip PRÓXIMA · Rn (EN CURSO hasta 2 h después de la largada), nombre, circuito,
  país, fechas, cuenta regresiva días/horas/minutos y horarios del fin de semana en **hora local del
  celular**. Tocarla abre el detalle.
- Temporada en curso: las carreras ya corridas van plegadas en "Carreras anteriores · N" (al
  desplegarlas aparecen arriba de las que vienen). Temporadas pasadas: todo desplegado, sin bloque
  de próxima.
- Tarjetas agrupadas por mes: ronda, bandera, nombre, fechas. Estados pasado / próxima / futuro con
  los mismos colores que escritorio.

### Detalle del GP
- Cabecera: badge de ronda, nombre del GP, circuito · país · fechas.
- **Chips de sesión** deslizables en horizontal (EL1, EL2, EL3 / Clasif. sprint, Sprint, Clasif.,
  Carrera), con el día debajo. Arranca en la última sesión con resultados.
- **Resultados** en filas: posición (medalla en el podio), barra del color del equipo, nombre, y
  debajo "Equipo · largó Nº" en carrera/sprint. A la derecha el tiempo o la diferencia en cian y
  los puntos debajo. Abandonos: el estado en lugar del tiempo. Libres: mejor vuelta / diferencia y
  vueltas. Clasificación: el mejor tiempo.
- Sesión no corrida: "Todavía no se corrió" con día y hora local; sin datos: "Sin datos para esta
  sesión" (libres antes de 2023).
- **Circuito**, abajo: mapa, nombre y ficha corta (longitud, vueltas, distancia, curvas, récord,
  primer GP). Tocar el mapa lo abre a pantalla completa; el botón "Más datos y ganadores" abre una
  **hoja inferior** con la ficha completa (suma tipo y sentido de giro) y los ganadores de cada GP
  corrido ahí, con "Más victorias: …". Las dos capas se cierran con "atrás".
- Circuito sin datos o sin mapa: la sección muestra sólo el nombre.

### Clasificación
- Selector Pilotos | Equipos, "TRAS LA Rn · GP", tres indicadores (LÍDER, VENTAJA, EN JUEGO, con la
  misma cuenta que `standings_view.py`) y la lista: posición, color de equipo, nombre, equipo ·
  victorias, puntos en cian y la diferencia con el líder debajo.

### Pilotos
- Selector Pilotos | Equipos y grilla de 2 columnas: foto (oficial de F1, si no Wikipedia, si no la
  sigla sobre el color del equipo), nombre, equipo y puntos. Equipos: logo o iniciales, nombre,
  posición y puntos.
- **Ficha de piloto**, apilada: cabecera con foto/sigla, nombre, equipo, país y edad; posición,
  puntos y victorias en grande; podios, poles, abandonos, promedio de llegada y de largada; gráfico
  carrera por carrera (tocar una barra muestra el GP); carrera completa (títulos, victorias, podios,
  GPs, debut).
- **Ficha de equipo**, apilada: posición, puntos, victorias y dobletes; cara a cara (clasificación,
  carrera, puntos, victorias, podios, poles) con barras partidas; tira carrera por carrera en filas
  de 8, con borde en el que llegó adelante.

### Estados
Cada pantalla tiene cargando, error ("No se pudo cargar. Reintentar") y vacío, con los textos de
escritorio. Sin conexión se ve lo último guardado por el service worker; si no hay nada guardado,
el error.

## Datos

| Qué | De dónde | Cuándo se actualiza |
|---|---|---|
| Calendario, resultados de carrera, clasificación y sprint | Jolpica, en vivo desde el navegador | Al abrir |
| Campeonatos (pestaña Clasificación) | Jolpica, en vivo | Al abrir |
| Libres y clasificación sprint (2023+) | OpenF1 (`sessions`, `session_result`, `drivers`) | Al abrir |
| Fichas de pilotos y equipos | `web/datos/temporadas/{año}.json` | Pasadas: una vez. En curso: en cada deploy |
| Carrera completa de cada piloto | `web/datos/carreras_previas.json` + la temporada en curso | Ídem |
| Ganadores por circuito | `web/datos/ganadores.json` | En cada deploy |
| Traducciones, banderas, colores, datos de circuitos | `web/datos/comun.json`, generado de `core/` | En cada deploy |
| Mapas | `web/mapas/{circuit_id}.png`, copiados de `cache_tracks/` | Cuando se regeneran en escritorio |
| Fotos | Oficial de F1 si la base la tiene (`headshot_url`, la llena FastF1 en la PC, así que en la temporada en curso suele faltar); si no, Wikipedia REST en vivo | Al abrir |

Las dos APIs y Wikipedia aceptan pedidos desde el navegador (CORS verificado). Todo se busca por
`circuitId` / `driverId` / `constructorId` de Jolpica, no por nombres de lugar: así no hacen falta
los alias de `core/circuits.py` (y el GP de Baréin en Malasia cae en Sepang, no en Sakhir).

### `exportar_web.py` (raíz del repo, Python plano, sin dependencias)
Reusa `core/historial.py`, `core/i18n.py`, `core/flags.py`, `core/equipos.py` y `core/circuits.py`:
la lógica de las fichas no se reescribe en JS.

- `python exportar_web.py` (modo por defecto, lo corre el deploy y se usa en local):
  baja la temporada en curso a una base temporal con `descargar_temporada` (~10 pedidos) y escribe
  `temporadas/{año actual}.json`, `ganadores.json` (un pedido por cada uno de los 38 circuitos de `DATOS_CIRCUITOS`; ~50 pedidos en total, dentro del límite de Jolpica) y
  `comun.json`. Estos tres archivos no se versionan (`.gitignore`).
- `python exportar_web.py --historico` (en la PC, cuando cambia algo del pasado, típicamente una
  vez al año): con la base local completa escribe `temporadas/{año}.json` de cada temporada
  terminada, `carreras_previas.json` (carrera completa contando sólo temporadas terminadas) y
  copia los mapas. Se versionan.
- Cada `temporadas/{año}.json`: `pilotos` (lo de `pilotos_temporada` + `stats_temporada` +
  `tira_resultados`) y `equipos` (lo de `equipos_temporada` + `stats_equipo` + `cara_a_cara`).
- Carrera completa en la ficha = `carreras_previas[id]` + lo de la temporada en curso (suma de
  victorias, podios y GPs; debut = el menor). Los títulos salen sólo de `carreras_previas`, igual
  que el criterio de escritorio (el que va primero a mitad de año todavía no es campeón).

### Deploy (`.github/workflows/pages.yaml`)
Se dispara con push a `web/**` o `exportar_web.py`, **todos los lunes a las 06:00 UTC** (después de
las carreras del fin de semana) y a mano. Pasos: checkout → Python → `python exportar_web.py` →
tests de JS con Node → subir `web/` → publicar. El deploy no hace commits: los datos de la
temporada en curso viven sólo en lo publicado.

## Arquitectura del front

Sin build ni dependencias: HTML, CSS y módulos ES servidos tal cual.

```
web/
├── index.html          esqueleto: encabezado, <main>, barra de pestañas
├── style.css           tokens Telemetría + componentes (lo que validó el mockup)
├── sw.js               red primero, caché si no hay conexión (como hoy)
├── manifest.json, íconos
├── js/
│   ├── app.js          router por hash, temporada elegida, barra de pestañas
│   ├── api.js          pedidos a Jolpica, OpenF1, Wikipedia y a datos/*.json
│   ├── formato.js      funciones puras: fechas, hora local, rangos, tiempos, próxima carrera
│   ├── html.js         template tag que escapa lo interpolado
│   └── vistas/
│       ├── calendario.js   detalle.js   clasificacion.js
│       ├── pilotos.js      ficha_piloto.js   ficha_equipo.js
│       └── capas.js        hoja inferior y mapa a pantalla completa
├── test/               node:test sobre formato.js y el parseo de rutas
├── datos/              generado por exportar_web.py
└── mapas/
```

- **Rutas** (hash, así "atrás" funciona solo): `#/calendario/2026`, `#/gp/2026/15`,
  `#/gp/2026/15/circuito` (hoja abierta), `#/clasificacion/2026/pilotos|equipos`,
  `#/pilotos/2026/pilotos|equipos`, `#/piloto/2026/antonelli`, `#/equipo/2026/mercedes`.
  Sin hash: calendario del año actual.
- Cada vista exporta `render(params)` y devuelve su HTML; `app.js` la monta en `<main>`, marca la
  pestaña y actualiza el encabezado. Las vistas no se conocen entre sí: navegan cambiando el hash.
- Todo texto que viene de una API pasa por `html.js` (escapado).
- `formato.js` no toca el DOM ni la red, para poder testearlo con Node.

## Pruebas

- `test_exportar_web.py` (pytest, corre en el CI de Python): con una base SQLite chica armada en el
  test, verifica la forma de `temporadas/{año}.json`, que `carreras_previas` no cuente la temporada
  en curso y que `comun.json` tenga las tablas de `core/`.
- `web/test/*.test.js` (`node --test`, en el deploy): hora local y rango de fechas, próxima
  carrera / EN CURSO, formato de tiempos y diferencias, parseo de rutas.
- A mano en cada etapa: captura con Edge headless a 390 px de ancho de cada pantalla, y prueba en
  el celular después del deploy.

## Fuera de alcance
- Avisos antes de la carrera / "Agregar a mi calendario".
- Cambios en la app de escritorio.
- Publicar en Play Store.
- Telemetría de vueltas o cualquier dato que hoy no muestra escritorio.
