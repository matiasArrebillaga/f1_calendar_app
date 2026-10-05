# Pestaña "Pilotos": pilotos, equipos y cara a cara

Fecha: 2026-10-05 · Estado: diseño aprobado, pendiente de plan de implementación

## Objetivo

Una pestaña nueva en la sidebar para conocer a los pilotos y equipos de la temporada elegida en el
selector, con fotos, estadísticas de la temporada y de toda la carrera, y un cara a cara entre
compañeros de equipo. Los resultados carrera por carrera que se guardan para esto son la base de
ideas futuras (predicción de ganador, batalla por el campeonato), que quedan fuera de esta spec.

Criterios de éxito:
- Funciona para cualquier temporada del selector (1950 a hoy), con o sin internet para las
  temporadas ya terminadas.
- Las temporadas terminadas se leen al instante desde una base local; sólo la temporada en curso
  (o una que falte) se baja de la API.
- Siempre se ve algo en el lugar de la foto: foto oficial, de Wikipedia o un placeholder.

Mockup de referencia (opción A elegida): https://claude.ai/artifact/6qpDzud8dXfjTKdMGJWrSS

## Experiencia

- Sidebar, grupo MENÚ: botón "Pilotos" debajo de "Clasificación".
- Encabezado igual a Clasificación: eyebrow "TEMPORADA {año}", título y solapas **Pilotos | Equipos**.
- **Solapa Pilotos → grilla de tarjetas**: foto, número, sigla, equipo (franja con su color) y
  puntos. Ordenadas por posición en el campeonato.
- **Ficha de piloto** (a pantalla completa, "← Pilotos" o Esc para volver):
  - Cabecera: foto grande, nombre, número, equipo, país, edad.
  - Temporada: posición, puntos, victorias, podios, poles, abandonos, promedio de llegada y de largada.
  - **Tira de resultados**: una celda por ronda con la posición de llegada (o "DNF") y debajo el
    delta contra la largada (▲N, ▼N, =). El tooltip muestra el nombre del GP. Las celdas de podio
    y de abandono se distinguen por estilo.
  - Carrera completa: títulos, victorias, podios, GPs disputados y año de debut.
- **Solapa Equipos → grilla de tarjetas de equipo** (nombre, color, posición y puntos en el
  campeonato de constructores).
- **Ficha de equipo**: sus dos pilotos frente a frente y el **cara a cara** de la temporada:
  clasificación, carrera, puntos, victorias y podios, cada fila con los dos números y una barra
  partida.
- Estados: cargando (spinner + texto), error y vacío, igual que el resto de las vistas.

## Datos

### Fuente

Ergast vía Jolpica (`https://api.jolpi.ca/ergast/f1/...`), con `urllib` + `json` de la stdlib.
Paginado con `limit=100`. Límites de Jolpica sin autenticación: 4 req/s y 500 req/h, así que las
descargas van pausadas. No se usa `fastf1.ergast` para esto: su limitador interno es más estricto
y devuelve DataFrames que no hacen falta.

### Base local: `historial_f1.db` (SQLite)

| Tabla | Columnas |
|---|---|
| `temporadas` | temporada, actualizada (qué temporadas ya están guardadas) |
| `carreras` | temporada, ronda, nombre, pais, fecha |
| `pilotos` | driver_id, codigo, numero, nombre, apellido, nacionalidad, nacimiento, url_wiki, headshot_url |
| `equipos` | constructor_id, nombre |
| `resultados` | temporada, ronda, driver_id, constructor_id, numero, largada, posicion, posicion_texto, puntos, estado |
| `clasificacion` | temporada, ronda, driver_id, posicion (Ergast la tiene desde 1994) |
| `campeonato_pilotos` | temporada, driver_id, constructor_id, posicion, puntos, victorias |
| `campeonato_equipos` | temporada, constructor_id, posicion, puntos |

`resultados` no tiene clave primaria: en los años 50 un piloto podía correr dos autos en la
misma carrera. `posicion` es NULL cuando `posicion_texto` no es un número.

Los campeonatos se guardan con su posición final en vez de recalcularse desde los resultados,
porque los sistemas de puntos viejos (con resultados descartados) no se pueden reconstruir bien.

Peso estimado: 4 a 5 MB para todo el historial.

### Ciclo de vida

- `precache_historial.py` (script local, como `precache.py`) llena la base de 1950 al año actual.
  Se puede cortar y reanudar porque saltea las temporadas ya guardadas. Son unas 550 consultas,
  entre 1 y 1,5 h la primera vez.
- El build empaqueta `cache_historial/historial_f1.db` (solo lectura).
- Al primer uso, la app copia la base a `data_path("cache_historial")` y desde ahí lee y escribe.
- Una temporada que falta en la base, o la temporada en curso (una vez por sesión de la app), se
  baja en segundo plano con `descargar_temporada(con, anio)`, que reemplaza esa temporada completa
  dentro de una transacción. Las temporadas pasadas no se vuelven a pedir.

### Reglas de cálculo

- **Largó**: `posicion_texto` no es "F" (no clasificó) ni "W" (se retiró antes de largar). Ergast
  incluye a los que no clasificaron en los resultados; no cuentan como GP ni como abandono.
- **Abandono**: largó y `posicion_texto` no es un número (R, D, E, N). Se usa `positionText` y no
  `status` porque los textos de estado cambiaron con los años ("+1 Lap", "Lapped").
- **Tira**: P{n} con delta ▲/▼/= contra la largada ("boxes" si largó desde boxes); DNF para R/N,
  DSQ para D/E, DNQ para F, DNS para W.
- **Pole**: posición 1 en `clasificacion`; antes de 1994 (sin datos de clasificación), `largada == 1`.
- **Podio**: posición 1 a 3.
- **Promedio de llegada**: sobre las carreras con posición clasificada. **Promedio de largada**:
  sobre largadas mayores a 0 (0 = largó desde boxes).
- **Títulos**: temporadas con posición 1 en `campeonato_pilotos`.
- **GPs**: carreras distintas con un resultado del piloto. **Debut**: temporada mínima.
- **Cara a cara**: los dos pilotos del equipo con más carreras juntos en la temporada.
  - Clasificación: gana el mejor puesto en `clasificacion` (o en la largada antes de 1994).
  - Carrera: gana el mejor clasificado; si uno abandonó y el otro no, gana el que terminó; si
    abandonaron los dos, la carrera no cuenta.

## Fotos

`core/fotos.py` → `obtener_ruta_foto(driver_id, headshot_url, url_wiki)` devuelve una ruta local o `None`:
1. **Oficial F1**: `headshot_url`, que viene de `session.results["HeadshotUrl"]` de FastF1
   (2018 en adelante, cuando está: en 2018 viene vacía, en 2024 sí). Se guarda con `/2col/` en
   vez de `/1col/` en la URL, que da 206 px en vez de 93. La completa el script de build y, para la temporada en curso,
   el worker.
2. **Wikipedia**: miniatura de `https://en.wikipedia.org/api/rest_v1/page/summary/<título>`, con
   el título sacado de `url_wiki` y un User-Agent propio.
3. **Placeholder**: si las dos fallan, la UI dibuja sigla + degradé del color del equipo.

Caché en `data_path("cache_fotos")` mediante `ruta_cache()`, igual que las banderas
(`core/flags.py`). Se bajan a demanda en segundo plano; el build precarga sólo la grilla actual.

## Componentes

| Archivo | Responsabilidad |
|---|---|
| `core/historial.py` (nuevo) | Esquema, descarga de una temporada y consultas: `pilotos_temporada`, `equipos_temporada`, `stats_temporada`, `tira_resultados`, `carrera_completa`, `cara_a_cara`. Devuelve dicts y listas, sin Qt. |
| `core/fotos.py` (nuevo) | Cadena de fotos y caché. |
| `core/i18n.py` | Sumar `NACIONALIDADES_ES` (gentilicio de Ergast en inglés → país en español). |
| `workers/pilotos_worker.py` (nuevo) | `PilotosWorker(year)`: asegura la temporada en la base y emite `terminado({'pilotos', 'equipos'})` / `error(str)`. `FotosWorker(lista)`: emite `foto_lista(driver_id, ruta)` por cada foto. |
| `ui/pilotos_view.py` (nuevo) | `PilotosView`: encabezado, solapas, `QStackedWidget` con grilla de pilotos, ficha de piloto, grilla de equipos y ficha de equipo. |
| `ui/fichas_pilotos.py` (nuevo) | `FotoPiloto`, `TarjetaPiloto`, `TarjetaEquipo`, `FichaPiloto`, `TiraResultados`, `FichaEquipo`. |
| `style.qss` | Reglas para los objectNames nuevos (`tarjetaPiloto`, `fichaPiloto`, `celdaResultado[estado=...]`, `filaCaraACara`, …). |
| `ui/sidebar.py`, `main.py` | Botón "Pilotos" (ícono Lucide `users`), índice 3 del stack, ruta `"pilotos"`, `pedir_anio` en el cambio de año y la vista en `closeEvent`. |
| `precache_historial.py` (nuevo) | Llenado inicial de la base, headshots desde 2018 y fotos de la grilla actual. |
| `F1CalendarApp.spec` | `datas` += `cache_historial` y `cache_fotos`. |

`PilotosView` copia los patrones de `ui/standings_view.py`:
- carga diferida con `pedir_anio` + `showEvent`;
- `_set_estado` con `SpinnerWidget`;
- caché por año;
- `_workers_activos`;
- descarte de resultados de un año viejo comparando `sender().year`.

Las fichas leen SQLite directo en el hilo de la UI (consultas locales de milisegundos).

Colores: `color_equipo()` de `core/equipos.py`; para equipos sin color (los viejos) se usa `MUTED`.
Números en `DATO` y Consolas, como en Clasificación.

## Errores

- Sin internet y la temporada está en la base: se muestra igual. Para la temporada en curso se usa
  lo último guardado.
- Sin internet y la temporada no está: estado de error con el mensaje, sin romper el resto de la app.
  El error no se cachea: al volver a abrir la pestaña se reintenta.
- Falla una foto: placeholder, sin reintentar en la misma sesión.
- Respuesta parcial de la API (se cortó a mitad de la paginación): la transacción no se confirma y
  la base queda como estaba.

## Fuera de alcance

Sprints en la tira de resultados, fotos de equipos o autos, cara a cara entre pilotos de equipos
distintos, predicción del ganador y batalla por el campeonato.

## Pruebas

- `test_historial.py` (nuevo, asserts planos como `test_ui.py`, corre con `pytest` y con `python`):
  base SQLite en memoria con una temporada inventada mínima. Cubre abandonos, poles antes y
  después de 1994, las reglas de carrera del cara a cara, títulos y debut, y que
  `descargar_temporada` reemplaza en vez de duplicar (con una respuesta JSON falsa).
- `test_ui.py`: `PilotosView` con un worker falso (patrón `_WorkerFalso`); muestra tarjetas y abrir
  una ficha sin datos no crashea. El test de reglas QSS muertas ya cubre los objectNames nuevos.
- Manual:
  - correr `precache_historial.py` para 2 o 3 temporadas;
  - abrir la pestaña en 2025, 1988 (foto de Wikipedia, sin clasificación) y 1955 (placeholder y
    equipos sin color);
  - revisar el cara a cara de McLaren;
  - cambiar de año rápido y confirmar que no se mezclan datos.
