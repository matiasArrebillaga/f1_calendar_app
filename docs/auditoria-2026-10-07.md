# Auditoría del repo — 2026-10-07

Revisión por carpeta (core + exportador, ui + workers, web, avisos + CI), solo lectura.
Verificado a mano: cron en la API de GitHub, calendario guardado de 2010, `detalle.js`,
traducción de "USA", líneas de puntos truncados.

Tests al momento de la auditoría: pytest 79/79, `node --test web/test` 64/64 (también con otras TZ).

## P0: roto en uso normal

1. **Los avisos casi nunca llegan.** `.github/workflows/avisos.yaml:5`
   - El cron pide cada 10 min; GitHub lo corrió 4 veces en 22 h (huecos de 4 a 7 h).
   - Con ventana de 35 min, una sesión cae adentro solo por casualidad.
   - Fix: cron externo (p. ej. cron-job.org) que dispare `workflow_dispatch`, con token `actions:write`.
   - Cubre además que GitHub apaga los schedules tras 60 días sin commits (avisos y refresco de los lunes).
2. **El detalle de cualquier GP 1950–2017 no muestra resultados.** `ui/event_detail_view.py:240`
   - En el calendario guardado de 2010, `Session1Date..Session5Date` son `None` → `pasada` siempre False.
   - Muestra "Sin sesiones" y cada botón "Todavía no se corrió".
   - Fix: si la fecha es NaT, usar `EventDate < hoy`; habilitar solo Q y R antes de 2018.
3. **En enero desaparece la temporada que terminó.** `exportar_web.py:198,218`
   - El cron del lunes pasa a `today().year`; nadie genera `temporadas/{anio-1}.json` ni su parte en `carreras_previas.json`.
   - `--historico` saltea en silencio temporadas guardadas incompletas.
   - Efecto: Pilotos del año anterior "Sin datos", calendario sin ganadores, carreras completas sin esa temporada.
   - Fix: que `exportar_actual` escriba `anio-1` si falta, o que el deploy falle con mensaje claro.

## P1: fallas en casos plausibles o errores silenciosos

### Escritorio

4. **Respuesta tardía pisa la vista.** `ui/event_detail_view.py` (`_click_sesion`, `mostrar_evento`):
   `_sesion_pedida` no se resetea al pasar a sesión futura u otro GP. Fix: `_sesion_pedida = None` + `spinner.detener()`.
5. **Tarjetas duplicadas en el calendario** al ir A→B→A antes de que A cargue. `ui/calendar_view.py:159-210`.
   Fix: descartar si `worker.year in self._cache_por_anio`.
6. **Cerrar con un worker largo corriendo → exit anormal.** `main.py:199`: tras `wait(3000)` el QThread sigue vivo.
7. **Medios puntos truncados.** `ui/standings_view.py:225,230,320,324`, `ui/event_detail_view.py:648`.
   Prost 1984: 71 en vez de 71.5. Fix: `f"{x:g}"`.
8. **Clasificación cachea errores de red como "sin datos".** `ui/standings_view.py:202`.
9. **"Próxima carrera" clavada en EN CURSO con la app abierta.** `calendar_view._terminadas` se calcula una vez.
   Mismo bug en la web: `web/js/vistas/calendario.js:116`.
10. **Mapa de circuitos pre-2018:** error de fastf1 en inglés + requests en cada apertura. `ui/event_detail_view.py:587`.
11. **Sprint Shootout 2023 sin tiempos:** falta en `CODIGOS_SESION` (`ui/event_detail_view.py:36`). Fix: `'Sprint Shootout': 'SS'`.
12. **Ficha abierta desde un GP puede ser de otro año** si se cambió el año en la sidebar. `main.py:133,162`.
13. **`core/flags.py:38`:** `urlretrieve` sin timeout en el hilo de UI; un corte deja un PNG truncado para siempre.
    Fix: patrón de `fotos._bajar`.

### Web

14. **"Cargando…" eterno.** `web/js/vistas/detalle.js:145,159`: `await evento()` fuera del `.catch`;
    en la capa queda `con-capa` y la página sin scroll.
15. **`web/sw.js`:** 429/5xx no cae a la copia guardada; sin precache (primera instalación no anda offline); `fetch` sin timeout.
16. **"Reintentar" no hace nada en una página de GP.** `web/js/app.js:178`. Fix: `actual = null` antes de `mostrar()`.

### Avisos y deploy

17. **Suscripción vencida (404/410) → exit 1 en cada corrida.** `avisos/enviar.mjs:74-88`.
    Fix: contar 404/410 como atendidos para guardar `ultima`.
18. **Un timeout de Jolpica tira el deploy.** `core/historial.py:63` (`pedir_json`): solo reintenta 429, y con `reintentos=1` por defecto ni eso.
    Fix: reintentar también `URLError`/`TimeoutError`/5xx.

## P2: inconsistencias y bordes

- Sesión sin hora (`web/js/formato.js:33`) → falso "EN VIVO" y aviso falso ~23:30 UTC del día anterior.
- `core/i18n.py`: falta "USA"; 10 nombres de GP 2020–2026 en inglés (Emilia Romagna, Portuguese, Styrian, etc.).
- `core/fechas.py:30` usa `EventDate`, la web usa la largada: Las Vegas 20–22 NOV vs 23.
- `ficha_equipo.js:15` muestra DNF para DSQ; `ficha_piloto.js:13` W→"NC" (debería "DNS"); `clasificacion.js:83` texto equivocado en Equipos antes de 1958.
- CI: `pages.yaml` no corre pytest; nada prueba `enviar.mjs`; `cancel-in-progress: true` puede cortar un deploy.
- Escritorio no recibe correcciones post-carrera: nunca re-baja la última ronda (`historial.ultima_ronda`).
- Caché de ganadores escrito no atómico (`core/historial.py`, `ganadores_circuito`).
- `core/paths.py` usa `abspath(".")`: correr desde otra carpeta crea una base vacía.
- `completar_fotos` (`exportar_web.py:71`) usa `session_key=latest`: titulares sin foto tras un EL1 con novatos.
- `sw.js`: `e.data.json()` sin try; `navigate()` sin fallback a `openWindow`.
- Hoja de avisos no se cierra con "atrás"; faltan catch en `clipboard`, `register`, `ready`; `vigilarEnVivo` no reintenta.
- `theme-color` distinto entre `index.html` y `manifest.json`.
- `ui/selector_temporada.py:83`: texto inválido deja el campo desincronizado.
- `.vscode/settings.json` versionado aunque `.vscode/` está en `.gitignore`.
- Dos sesiones a menos de 35 min → los avisos se alternan (improbable en F1).

## Código muerto

- `core/core__init__.py`: `__init__` mal nombrado → `git mv core/core__init__.py core/__init__.py`.
- `core/i18n.py`: claves duplicadas (Japan, United States, Mexico, Saudi Arabia, Bahrain, Belgium, "Japanese Grand Prix").
- Web: `SESIONES`, `dosDigitos`, `idSesion` (formato.js), `FILAS_COMPLETAS` (capas.js), `armarDetalle` (detalle.js) exportados sin uso.
- `ui/calendar_view.py`: `_animaciones_entrada` sin leer, `RESERVA_LATERAL = 0`.
- `main.py`: `volver_a_calendario` solo envuelve a `ir_a_calendario`.
- `ui/fichas_pilotos.py`: parámetro `parent` de `FotoPiloto` sin uso; `tarjetas()`, `carreras()`, `celdas()` solo los usan los tests.
- `ui/selector_temporada.py`: rama `if not texto` inalcanzable.
- `web/js/avisos.js`: comentario dice "un solo celular".
- JSON: `anio`/`ronda` de primer nivel y otros campos que la web no lee (conservar `ronda`, sirve para el fix de `clasificacion.js`).

## Revisado y sin problemas

- Claves que escribe `exportar_web.py` = claves que lee el JS (76 JSON de temporadas).
- El deploy usa solo stdlib, también transitivamente.
- Firmas y señales entre core, ui y workers coinciden.
- Sin XSS: todo pasa por `html`.
- Payload push coincide con `sw.js`; misma VAPID en web y `enviar.mjs`.
- No se loguean secretos; permisos de workflows mínimos.
- `style.qss` sin selectores huérfanos.
