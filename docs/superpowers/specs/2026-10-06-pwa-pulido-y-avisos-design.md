# PWA móvil: fotos oficiales, rediseño para celular y avisos antes de cada sesión

Fecha: 2026-10-06 · Estado: diseño aprobado, pendiente de plan de implementación

## Objetivo

Que la web móvil (`web/`) se sienta una app profesional y no una página: fotos oficiales de F1,
pantallas pensadas para el celular y un aviso en el teléfono antes de cada sesión. La app de
escritorio no se toca.

Lo que pidió el usuario:
- Foto oficial de pilotos y equipos.
- Sacar el desplegable "Carreras anteriores": abrir parado en la próxima y subir scrolleando para ver
  lo corrido, como escritorio.
- Rediseñar "carrera por carrera" de pilotos y equipos para el celular.
- Notificar al celular antes de cada sesión (todas: libres, clasificación sprint, sprint,
  clasificación y carrera). Sin conexión con F1 TV: el link a la app no abre la app sino la web.
- Además, las propuestas de pulido del canvas.

Mockups (canvas): https://claude.ai/artifact/HGgyMH6M1AgtzKyM72b6KK — pantallas 1 a 7.

Criterios de éxito:
- En la temporada en curso, todos los pilotos tienen foto oficial y los 11 equipos su logo.
- El calendario abre en la próxima carrera; scrollear para arriba muestra las corridas.
- Las fichas se leen sin hacer zoom ni scroll horizontal.
- Llega una sola notificación por sesión, entre ~15 y 35 min antes; tocarla abre el GP en la app.
- Lo que no tiene soporte (transiciones, vibración) degrada sin romper nada.

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Fotos de pilotos | OpenF1 `/drivers?session_key=latest`, cruzado por sigla, en `exportar_web.py` (stdlib). |
| Foto de cuerpo entero | CDN nuevo de F1 (`media.formula1.com/image/upload/…/common/f1/<año>/<equipo>/<codigo>/…`). |
| Logos y autos | Del mismo CDN, para los 11 equipos de 2026. Tablas en `exportar_web.py`, no en `core/`. |
| Temporadas viejas | Sin cambios: foto oficial desde 2018, Wikipedia antes, sigla si no hay nada. |
| Avisos | Web Push desde GitHub Actions cada 10 min. Repo público: gratis. |
| Un aviso por sesión | La última sesión avisada se recuerda en el caché de Actions. |
| Al tocar el aviso | Abre `#/gp/<año>/<ronda>` en la app. Sin F1 TV. |
| En vivo | Sólo con los horarios y duraciones fijas: no hay datos en vivo gratis dentro de la sesión. |
| Descartado | Volver deslizando desde el borde (Android ya lo hace) y título que se achica al scrollear. |

## Fotos y logos oficiales

`exportar_actual()` hoy no completa `headshot_url` (escritorio lo hace con FastF1, que no corre en el
deploy), por eso `actual.json` sale sin fotos.

Cambios en `exportar_web.py`:
- `fotos_openf1(pilotos, pedir)`: pide `/drivers?session_key=latest` a OpenF1 y, por cada piloto de
  la temporada cuyo `codigo` coincide con `name_acronym`, pone:
  - `headshot_url`: la URL de OpenF1 con `/1col/` → `/2col/` (busto, para avatares).
  - `foto_cuerpo`: cuerpo entero del CDN nuevo, armada con el código del piloto que trae la URL de
    OpenF1 (`…/ANDANT01_…/andant01.png…` → `andant01`) y el slug del equipo en ese CDN
    (`SLUG_CDN = {"mercedes": "mercedes", "red_bull": "redbullracing", …}`, verificado contra el
    CDN al implementar, uno por uno).
  - Un piloto sin coincidencia queda como hoy (Wikipedia/sigla).
  - Si OpenF1 falla, se exporta igual sin fotos: no puede tirar abajo el deploy.
- `datos_comunes()`: `logos` y un mapa nuevo `autos` salen del CDN 2026 para los equipos de
  `SLUG_CDN`; los que no están siguen con el logo viejo de `core.equipos.url_logo` o las iniciales.
- Se aplica a `pilotos` y a `cara_a_cara.a/b` de cada equipo (que también llevan `headshot_url`).

Web: `armarFoto` usa `foto_cuerpo` donde la vista lo pide (grilla, cabecera de la ficha) y
`headshot_url` para círculos; si no hay ninguna, sigue el camino de hoy.

## UI

Paleta y reglas de la casa de siempre (Telemetría; rojo sólo para estado, cian para datos; 1 px de
borde). Áreas táctiles de 44 px.

### 1. Calendario (`vistas/calendario.js`)
- Sale el `<details>`: un solo listado por mes con la próxima (hero) en su lugar cronológico.
- Carrera corrida: fila compacta atenuada (ronda, bandera, nombre, fechas) con el ganador como
  sigla y una barrita del color de su equipo. El ganador sale del JSON de la temporada
  (`temporada()`, ya cacheado): el piloto con `posicion === 1` en la ronda de su `tira`. Si no hay
  datos, la fila va sin ganador.
- Carrera futura: fila con "en N d" en cian.
- `montar`: si hay hero, la ventana se ubica en él al abrir (descontando el encabezado). Una píldora
  "↑ N carreras corridas" flota arriba mientras la primera fila corrida está fuera de pantalla
  (IntersectionObserver); tocarla sube con scroll suave.
- Temporadas pasadas: sin hero, abre arriba.

### 2. En vivo (hero del calendario)
- Duraciones fijas: libres 60 min, clasificación sprint 45, sprint 45, clasificación 60, carrera
  120. Una sesión está "en vivo" entre su inicio y inicio + duración.
- Mientras hay una en vivo: chip "● EN VIVO · <SESIÓN>" con el punto rojo latiendo, barra de avance
  (tiempo transcurrido / duración), "empezó hace N min".
- Lista de sesiones del fin de semana con estado: hecha (✓ y "Resultados ›" al detalle del GP),
  en vivo ("Seguir ›"), próxima (hora o cuenta regresiva si es la siguiente).
- Punto rojo sobre el ícono de Calendario en la barra de pestañas mientras hay sesión en vivo.
- Se recalcula con el mismo intervalo de 30 s de hoy.
- Lógica pura y testeable en `formato.js`: `estadoSesiones(sesiones, ahora)` →
  `[{ ...sesion, estado: "hecha" | "vivo" | "proxima", avance }]`.

### 3. Grilla (`vistas/pilotos.js`)
- Pilotos: tarjetas de 2 columnas con foto de cuerpo entero recortada arriba, número grande de
  fondo, posición, apellido, equipo y puntos, fondo teñido y franja inferior del color del equipo.
- Equipos: tarjeta con logo y, si hay, el auto.

### 4. Ficha del piloto (`vistas/ficha_piloto.js`)
- Cabecera: color del equipo, número gigante de fondo, foto de cuerpo entero, logo del equipo,
  nombre y apellido grande, nacionalidad y edad.
- KPIs (campeonato, puntos, victorias) y fila de stats (podios, poles, abandonos, promedios).
- "Carrera por carrera" reemplaza el gráfico de barras: arriba las últimas 5 como cajitas; abajo
  una fila por ronda, de la más reciente a la más vieja: ronda, bandera, GP, "Largó Nº", caja con
  la llegada (llena si ganó, gris si podio, con borde si sumó puntos, sin caja fuera de los
  puntos, texto DNF/DSQ/DNQ/NC como hoy) y ▲/▼ puestos ganados o perdidos. Toca → GP.
- "Carrera completa" (títulos, victorias, podios, GPs, debut) va en una barra fija abajo, pegada
  arriba de la barra de pestañas (`position: sticky; bottom: var(--alto-tabbar)` + safe area): se
  ve siempre mientras se scrollea la lista. El contenido lleva un margen inferior del alto de la
  barra para que la última fila no quede tapada. Sin datos de carrera, la barra dice "Sin datos de
  carrera".

### 5. Ficha del equipo (`vistas/ficha_equipo.js`)
- Cabecera con logo, nombre, pilotos y el auto; KPIs como hoy.
- Cara a cara: caras de los dos pilotos, marcador grande (carreras adelante, p. ej. 11–5) y una
  tira de un cuadrito por ronda pintada con el color del equipo o gris claro según quién llegó
  adelante.
- Barras de duelo (clasificación, carrera, puntos, victorias, podios, poles) como hoy, restyle.
- "Carrera por carrera": una fila por ronda, más reciente primero, con las dos posiciones lado a
  lado; la del que llegó adelante va llena con el color del equipo.

### 6. Esqueletos (`app.js`)
- En lugar de "Cargando…", un esqueleto genérico con brillo (bloque grande + filas), mostrado sólo
  si la carga tarda más de 150 ms.

### 7. Toques y transiciones
- `:active` en filas y tarjetas (fondo + escala leve).
- Indicador de la pestaña activa y del segmento Pilotos/Equipos que se desliza (CSS transitions).
- `navigator.vibrate(8)` al cambiar de pestaña o de segmento, si existe.
- Cambio de pantalla con `document.startViewTransition` si existe; la foto del piloto tocado en la
  grilla y la de la cabecera de la ficha comparten `view-transition-name`, así "viaja". Sin
  soporte: cambio directo.
- Respeta `prefers-reduced-motion`.

### 8. Sin conexión
- Al disparar `offline`, aviso abajo "Sin conexión · mostrando lo último guardado" con
  "Reintentar"; se va con `online`.

### 9. Campana de avisos
- Botón con campana en el encabezado del Calendario (ver Avisos).

## Avisos antes de cada sesión

### En la app (una vez)
- La campana pide permiso de notificaciones, suscribe al service worker con
  `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: <VAPID público> })` y muestra
  la suscripción en JSON con un botón **Copiar**.
- El usuario la pega como secreto `PUSH_SUBSCRIPTION` del repo. (Sin servidor no hay otra forma de
  guardarla; es una app personal, un solo celular.)
- Si ya hay suscripción, la campana se ve activa y vuelve a mostrar el texto para copiar.
- `sw.js` suma:
  - `push`: muestra la notificación con `title`, `body`, `tag` = id de la sesión y `data.url`.
  - `notificationclick`: enfoca una ventana abierta de la app y navega a `data.url`, o abre una.

### En GitHub (`.github/workflows/avisos.yaml`)
- `schedule: "*/10 * * * *"` + `workflow_dispatch`.
- Pasos: checkout → `actions/cache/restore` (prefijo `aviso-`) → `node avisos/enviar.mjs` →
  `actions/cache/save` con clave `aviso-<id de sesión>` si se mandó algo.
- `enviar.mjs`:
  1. Baja el calendario de la temporada de Jolpica y arma las sesiones con las mismas funciones de
     `formato.js` (`aEvento`), sin duplicar lógica.
  2. `sesionAAvisar(sesiones, ahora, ultimaAvisada)`: la primera sesión que empieza en
     `(ahora, ahora + 35 min]` y no es la última avisada; si no hay, termina.
  3. Manda con `web-push` (VAPID): "Clasificación · GP de Singapur" / "Empieza en 27 min", `tag`
     y `url` del GP. Los minutos son los reales al momento de mandar.
  4. Escribe el id avisado para que el paso de caché lo guarde.
- Secretos: `VAPID_PRIVATE`, `PUSH_SUBSCRIPTION`. La clave pública va en el código de la web. Las
  claves se generan una vez (`npx web-push generate-vapid-keys`).
- `web-push` sólo se instala en este workflow (`avisos/package.json`, fuera de `web/` para que no se publique); la web no lo usa.
- Nunca imprime la suscripción: los logs de un repo público son públicos.
- Si el servicio push contesta 404/410 (suscripción vencida), el script sale con error → GitHub
  manda un mail → se reactiva con la campana y se vuelve a copiar.
- Si GitHub pausa los schedules por 60 días sin actividad, avisa por mail y se reactiva a mano.

## Errores y bordes
- OpenF1 caído en el deploy: se exporta sin fotos, como hoy.
- Imagen que no carga: queda la sigla (como `cargarFotos`).
- Sesión ya empezada cuando corre el aviso (GitHub atrasado): no se avisa.
- Cambio de año: el script usa el año en curso; el 1 de enero no hay sesiones cerca y no manda
  nada.
- Sin permiso de notificaciones o navegador sin Push: la campana explica que no se puede y no hace
  nada más.

## Pruebas
- JS (`node --test "web/test/*.test.js"`):
  - Filas del calendario: orden, ganador por ronda, "en N d", sin hero en temporadas pasadas.
  - `estadoSesiones`: antes, durante (avance), después, fin de semana sprint.
  - Filas de carrera por carrera del piloto (caja según puesto, ▲/▼, textos sin posición) y del
    equipo (quién adelante, tira de cuadritos, marcador).
  - `sesionAAvisar`: ventana de 35 min, sesión ya empezada, misma sesión ya avisada, sin sesiones.
- Python (`test_exportar_web.py`): cruce de OpenF1 por sigla, armado de `foto_cuerpo`, piloto sin
  coincidencia, OpenF1 caído.
- A mano en el celular: instalar, activar la campana, disparar el workflow con `workflow_dispatch`
  cerca de una sesión (o con una sesión de prueba) y tocar la notificación.
