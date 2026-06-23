# Jenkins AIOps

Servicio que recibe resultados de Jenkins, registra los builds correctos y
analiza con Ollama los builds `FAILURE` o `UNSTABLE`. Incluye historial,
diagnóstico y valoración desde una interfaz web.

## Inicio rápido

```bash
cp .env.example .env
# Completa JENKINS_URL y, si aplica, las credenciales.
docker compose up --build -d
docker compose exec ollama ollama pull qwen3:1.7b
curl http://localhost:8000/health
```

Abre el panel en <http://localhost:5000/dashboard>. La documentación de la API
queda en <http://localhost:8000/docs>.

## Integración recomendada con Jenkins

Configura un secreto compartido:

```env
INGESTION_TOKEN=genera-un-secreto-largo
```

Crea en Jenkins una credencial de tipo **Secret text**, con ID
`jenkins-aiops-token`, que contenga el mismo valor. Después incorpora el bloque
`post` de [examples/Jenkinsfile](examples/Jenkinsfile) a tu pipeline.

Jenkins enviará una petición al terminar:

```http
POST /api/builds
X-AIOPS-Token: ...
```

El endpoint responde `202` rápidamente. Un resultado `SUCCESS` se guarda sin
invocar el modelo; `FAILURE` y `UNSTABLE` se analizan en segundo plano.

La API también monitoriza Jenkins externamente cada 15 segundos. Esto cubre
errores de sintaxis del `Jenkinsfile`: como el Pipeline no llega a compilar, su
bloque `post` tampoco puede ejecutarse. El monitor consulta Jenkins, recupera la
consola y registra ese fallo sin depender del Pipeline.

Prueba manual:

```bash
curl -X POST http://localhost:8000/api/builds \
  -H 'Content-Type: application/json' \
  -H 'X-AIOPS-Token: genera-un-secreto-largo' \
  -d '{
    "job_name": "test111",
    "build_number": 4,
    "status": "FAILURE",
    "build_url": "http://jenkins/job/test111/4/",
    "log": "ERROR: repository does not exist"
  }'
```

El diagnóstico terminado puede consultarse en el panel o mediante:

```bash
curl http://localhost:8000/api/builds
```

## Configuración

Todas las opciones están documentadas en `.env.example`. Las credenciales son
opcionales para instancias Jenkins con lectura anónima. `MAX_LOG_CHARACTERS`
limita el tramo final enviado al modelo, donde suelen aparecer la causa y el
stack trace del fallo. SQLite persiste el historial en el volumen `api-data`.

El endpoint antiguo `GET /analyze/{job}/{build}` se conserva para diagnóstico
manual, pero el envío desde Jenkins evita una segunda descarga del log y no
bloquea el pipeline mientras Ollama procesa.

`JENKINS_POLL_JOBS=*` monitoriza todos los jobs. Para limitarlo:

```env
JENKINS_POLL_JOBS=backend,frontend,folder/pipeline
```

## Desarrollo

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run uvicorn apps.api.main:app --reload
```

`uv sync` crea `.venv`, instala Python 3.12 si hace falta y sincroniza exactamente
las dependencias registradas en `uv.lock`.

Consulta `AGENTS.md` para las convenciones del repositorio y
`docs/architecture.md` para el diseño.
