# Jenkins AIOps

Servicio que recibe resultados de Jenkins, registra los builds correctos y
analiza con un proveedor LLM configurable los builds `FAILURE` o `UNSTABLE`.
Antes de llamar al LLM busca en una base de errores conocidos (RAG con
`pgvector`); si un fallo ya fue diagnosticado antes, reusa ese diagnóstico. El
análisis corre en workers de Celery (Redis como cola), lo que acota cuántas
builds se analizan en paralelo. Incluye historial, diagnóstico, valoración,
log completo y chat sobre el log desde una interfaz web.

## Inicio rápido

```bash
cp .env.example .env
# Completa JENKINS_URL y, si aplica, las credenciales.
docker compose up --build -d
docker compose exec ollama ollama pull qwen3:1.7b
docker compose exec ollama ollama pull embeddinggemma
curl http://localhost:8000/health
```

`api` ejecuta las migraciones de Alembic automáticamente al arrancar. Abre el
panel en <http://localhost:5000/dashboard>. La documentación de la API queda
en <http://localhost:8000/docs>.

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
stack trace del fallo. PostgreSQL (con la extensión `pgvector`) persiste el
historial y la base de errores conocidos en el volumen `postgres-data`.

El endpoint antiguo `GET /analyze/{job}/{build}` se conserva para diagnóstico
manual, pero el envío desde Jenkins evita una segunda descarga del log y no
bloquea el pipeline mientras el proveedor LLM procesa.

## Proveedores de IA

La aplicación usa una interfaz común y actualmente incluye:

- `ollama`
- `openai-compatible`, válido para OpenAI y servidores compatibles como LM
  Studio, vLLM, LocalAI o LiteLLM.

Configuración local con Ollama:

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=qwen3:1.7b
LLM_API_KEY=
```

Configuración con una API compatible con OpenAI:

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=nombre-del-modelo
LLM_API_KEY=tu-api-key
LLM_JSON_MODE=true
```

Para Docker utiliza las variables equivalentes `DOCKER_LLM_*`. Si el proveedor
no implementa `response_format`, configura `LLM_JSON_MODE=false`.

## RAG de errores conocidos

Antes de llamar al LLM, `IngestBuildUseCase.process` prueba en este orden:

1. Reglas deterministas (`detect_known_failure`, sin coste).
2. Búsqueda semántica en `known_errors` (Postgres + `pgvector`): se normaliza
   el log (se recortan timestamps, números de build, rutas y hashes) y se
   embebe con un proveedor independiente del generativo:

   ```env
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_BASE_URL=http://127.0.0.1:11434
   EMBEDDING_MODEL=embeddinggemma
   EMBEDDING_API_KEY=
   EMBEDDING_DIMENSIONS=768
   RAG_ENABLED=true
   RAG_SIMILARITY_THRESHOLD=0.15
   ```

   Si hay una entrada con distancia coseno menor o igual al umbral (y
   `trust_score > 0`), se reusa su diagnóstico sin invocar al LLM.
3. Si no hay coincidencia, se llama al LLM como siempre y el diagnóstico se
   guarda en `known_errors` para futuras builds similares.

Cada vez que se valora una build (👍/👎) y esa build usó una entrada de
`known_errors`, su `trust_score` sube o baja; una entrada que llega a 0 deja
de usarse para futuros matches.

`EMBEDDING_DIMENSIONS` debe coincidir con la salida del modelo configurado; si
cambias de modelo de embeddings hace falta una migración nueva y volver a
indexar `known_errors`.

## Cola de análisis (Celery + Redis)

`POST /api/builds` guarda la build y encola su análisis en Redis; un worker de
Celery (`docker compose` levanta el servicio `worker`) lo procesa. La
concurrencia del worker (`CELERY_WORKER_CONCURRENCY`) es el límite real de
cuántas builds se analizan en paralelo, evitando saturar un Ollama local
cuando fallan varias builds a la vez. El monitor externo usa la misma cola
para reintentar builds que quedaron `queued`/`processing`.

`JENKINS_POLL_JOBS=*` monitoriza todos los jobs. Para limitarlo:

```env
JENKINS_POLL_JOBS=backend,frontend,folder/pipeline
```

## Log completo y chat sobre una build

Desde el panel, cada build tiene un enlace "Ver log completo" que abre
`/dashboard/builds/{id}`: log íntegro, diagnóstico y un chat para preguntar
sobre esa build concreta (`POST /api/builds/{id}/chat`). El chat reutiliza el
mismo proveedor generativo configurado en `LLM_*`, mantiene el log como
contenido no confiable en el prompt, y guarda el historial en Postgres.

## Desarrollo

```bash
uv sync
uv run pytest -q
uv run ruff check .
docker compose up -d postgres redis ollama
DATABASE_URL=postgresql://jenkins_aiops:jenkins_aiops@localhost:5432/jenkins_aiops \
  uv run alembic upgrade head
uv run uvicorn apps.api.main:app --reload
```

`uv sync` crea `.venv`, instala Python 3.12 si hace falta y sincroniza exactamente
las dependencias registradas en `uv.lock`. `uv run pytest -q` requiere Docker
disponible: los tests que tocan `BuildRepository`/`KnownErrorRepository`
levantan un Postgres+`pgvector` efímero con `testcontainers`.

Consulta `AGENTS.md` para las convenciones del repositorio y
`docs/architecture.md` para el diseño.
