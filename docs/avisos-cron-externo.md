# Avisos: disparo externo cada 10 min

El `schedule` de GitHub Actions no sirve para avisar 30 min antes: en la
práctica corre cada 4 a 7 h, y se apaga solo tras 60 días sin commits. El
workflow se dispara desde afuera con `workflow_dispatch`.

1. **Token**: GitHub › Settings › Developer settings › Fine-grained tokens ›
   Generate. Solo el repo `f1_calendar_app`, permiso **Actions: Read and write**
   (nada más). Vencimiento: el máximo; anotar cuándo vence.
2. **cron-job.org** (gratis): Create cronjob.
   - URL: `https://api.github.com/repos/matiasArrebillaga/f1_calendar_app/actions/workflows/avisos.yaml/dispatches`
   - Schedule: every 10 minutes.
   - Advanced › Request method: `POST`.
   - Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
     `X-GitHub-Api-Version: 2022-11-28`.
   - Body: `{"ref":"master"}`.
   - Respuesta esperada: `204`.
3. **Deploy de los lunes** (opcional, mismo token): otro job a
   `.../actions/workflows/pages.yaml/dispatches`, los lunes 06:00 UTC, mismo
   body. Así el refresco semanal no depende de que haya commits.

Si el token vence, cron-job.org muestra 401 y manda un mail.
