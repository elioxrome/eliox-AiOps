# Runbook

## Variables

| Variable | Predeterminado | Uso |
|---|---:|---|
| `JENKINS_URL` | `http://jenkins:8080` | URL base de Jenkins |
| `JENKINS_USERNAME` | vacío | Usuario; vacío permite acceso anónimo |
| `JENKINS_TOKEN` | vacío | API token de Jenkins |
| `JENKINS_TIMEOUT_SECONDS` | `30` | Timeout del SDK de Jenkins |
| `LLM_PROVIDER` | `ollama` | `ollama`, `openai` u `openai-compatible` |
| `LLM_BASE_URL` | `http://ollama:11434` | URL base del proveedor |
| `LLM_MODEL` | `qwen3:1.7b` | Modelo generativo |
| `LLM_API_KEY` | vacío | Bearer token cuando aplique |
| `LLM_TIMEOUT_SECONDS` | `120` | Timeout de generación |
| `LLM_TEMPERATURE` | `0.1` | Variabilidad de la respuesta |
| `LLM_CONTEXT_TOKENS` | `4096` | Contexto para proveedores que lo soportan |
| `LLM_MAX_OUTPUT_TOKENS` | `400` | Máximo de salida |
| `LLM_JSON_MODE` | `true` | Envía `response_format` en Chat Completions |
| `EMBEDDING_PROVIDER` | `ollama` | Proveedor de embeddings para el RAG de errores conocidos |
| `EMBEDDING_BASE_URL` | `http://ollama:11434` | URL de embeddings |
| `EMBEDDING_MODEL` | `embeddinggemma` | Modelo de embeddings |
| `EMBEDDING_DIMENSIONS` | `768` | Dimensión del vector; debe coincidir con el modelo. Cambiarla exige una migración nueva y reindexar `known_errors` |
| `RAG_ENABLED` | `true` | Activa la búsqueda semántica de errores conocidos antes de llamar al LLM |
| `RAG_SIMILARITY_THRESHOLD` | `0.15` | Distancia coseno máxima aceptada para reusar un diagnóstico (0 = idéntico) |
| `MAX_LOG_CHARACTERS` | `10000` | Máximo de caracteres enviados |
| `DATABASE_URL` | `postgresql://jenkins_aiops:jenkins_aiops@postgres:5432/jenkins_aiops` | Cadena de conexión a PostgreSQL |
| `REDIS_URL` | `redis://redis:6379/0` | Broker/backend de Celery |
| `CELERY_WORKER_CONCURRENCY` | `2` | Builds analizadas en paralelo por el worker (límite real de llamadas simultáneas al LLM) |
| `DASHBOARD_LIMIT` | `100` | Builds visibles en el panel |
| `INGESTION_TOKEN` | vacío | Secreto para `POST /api/builds` |
| `JENKINS_POLL_ENABLED` | `false` | Activa el monitor externo |
| `JENKINS_POLL_INTERVAL_SECONDS` | `15` | Frecuencia del monitor |
| `JENKINS_POLL_JOBS` | `*` | Jobs, separados por coma, o todos |

Los timeouts y límites deben ser números positivos. No guardes `.env` en control
de versiones.

El servicio `api` carga `.env` mediante `env_file`. Las variables `DOCKER_LLM_*`,
`DOCKER_EMBEDDING_*`, `DOCKER_DATABASE_URL` y `DOCKER_REDIS_URL` permiten que
Docker use URLs distintas a la ejecución local con `uv`. El servicio `worker`
usa las mismas variables.

Ollama no publica el puerto `11434` en el host: la API accede mediante
`http://ollama:11434` dentro de la red de Compose. Esto evita conflictos con una
instalación local de Ollama que ya esté escuchando en ese puerto.

## Migraciones

El servicio `api` ejecuta `alembic upgrade head` automáticamente al arrancar
(ver `CMD` en `Dockerfile`). Para aplicarlas manualmente (por ejemplo en
desarrollo local sin Docker para la API):

```bash
DATABASE_URL=postgresql://jenkins_aiops:jenkins_aiops@localhost:5432/jenkins_aiops \
  uv run alembic upgrade head
```

Nuevas migraciones: `uv run alembic revision -m "descripción"` y completar
`upgrade()`/`downgrade()` con `op.execute(...)` (sin ORM, ver
`docs/architecture.md`).

## Verificación

```bash
docker compose config
docker compose up --build -d
docker compose ps
docker compose exec ollama ollama pull qwen3:1.7b
docker compose exec ollama ollama pull embeddinggemma
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/api/builds
```

Para confirmar que la cola de análisis funciona, revisa los logs del worker:

```bash
docker compose logs -f worker
```

Al enviar dos builds con el mismo error (mismo log normalizado), la segunda
debe completarse sin que el worker llame al LLM: revisa que
`GET /api/builds/{id}` traiga `matched_known_error_id` distinto de `null`.

El panel está en `http://localhost:5000/dashboard`. Para integrar Jenkins, crea
una credencial Secret text con el mismo valor que `INGESTION_TOKEN` y utiliza
`examples/Jenkinsfile`.

Para limpiar el historial sin volver a importar builds antiguas:

```bash
curl -X DELETE http://localhost:8000/api/builds \
  -H "X-AIOPS-Token: $INGESTION_TOKEN"
```

La limpieza conserva el cursor del monitor; solo aparecerán builds posteriores.

## Incidencias frecuentes

### HTTP 502: no se puede recuperar la build

Comprueba conectividad desde el contenedor, URL, nombre de job, número de build y
permisos del token. Jenkins puede requerir un API token en vez de contraseña.

### HTTP 502: fallo del proveedor LLM

Con Ollama, comprueba que el contenedor está saludable y que el modelo existe:

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:1.7b
```

### HTTP 502: respuesta no válida del modelo

El modelo produjo JSON que no cumple `BuildAnalysis`. Revisa logs de la API y
prueba el prompt con el mismo modelo. No elimines la validación como solución;
ajusta el prompt o el adaptador.

### Jenkins se ejecuta en la máquina anfitriona

En Docker Desktop puede usarse `host.docker.internal`. En Linux puede ser
necesario añadir un mapeo de host o usar una IP accesible desde la red de Docker.

### Las builds quedan en `queued`/`processing` indefinidamente

El worker de Celery no está corriendo o no puede conectar a Redis/Postgres.
Revisa `docker compose logs worker` y que `REDIS_URL`/`DATABASE_URL` sean
correctos en ambos servicios (`api` y `worker`).

### El RAG nunca encuentra coincidencias

Confirma que `EMBEDDING_DIMENSIONS` coincide con la salida real del modelo de
embeddings (por ejemplo `embeddinggemma` produce vectores de 768) y que
`RAG_SIMILARITY_THRESHOLD` no sea demasiado estricto (valores más bajos exigen
mayor similitud).
