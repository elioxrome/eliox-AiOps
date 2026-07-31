# Jenkins AIOps: guía para agentes

Este archivo es la fuente de contexto principal para Claude code y otros agentes que
trabajen en el repositorio. Antes de modificar código, consulta también
`docs/architecture.md` y, para tareas operativas, `docs/runbook.md`.

## Objetivo

La API recibe el estado y log al terminar una build. Registra `SUCCESS` sin usar
IA y analiza `FAILURE`/`UNSTABLE` en segundo plano, en un worker de Celery
acotado por `CELERY_WORKER_CONCURRENCY`. Antes de invocar el LLM busca en una
base de errores conocidos (RAG con `pgvector`); si el fallo ya fue
diagnosticado antes, reusa ese diagnóstico. PostgreSQL guarda historial,
diagnóstico y feedback; un frontend separado (`frontend/`, app de Streamlit)
sirve el panel web, incluido el chat sobre el log de una build.

## Mapa rápido

- `apps/api/main.py`: creación de FastAPI, lifespan (monitor de Jenkins, cierre
  del pool) y endpoints operativos.
- `apps/api/dependencies.py`: fábricas de dependencias de FastAPI; delegan en
  `src/infrastructure/bootstrap.py`.
- `apps/api/routers/analysis.py`: endpoint legado `GET /analyze/{job}/{build}`.
- `apps/api/routers/builds.py`: ingestión, consulta (con filtros
  `status`/`job_name`/`category`/`date_from`/`date_to`), facets, resumen por
  job (`GET /api/builds/jobs`), log completo y feedback de builds.
- `apps/api/routers/chat.py`: chat sobre el log de una build.
- `src/infrastructure/bootstrap.py`: wiring agnóstico de framework,
  compartido por el proceso de FastAPI y el worker de Celery; cada proceso
  cachea (`lru_cache`) su propio pool/clientes.
- `src/application/use_cases/ingest_build.py`: decide si una build necesita
  IA y orquesta el flujo RAG: `detect_known_failure` (regex) ->
  `KnownErrorRepository.find_similar` (pgvector) -> LLM (que indexa el nuevo
  diagnóstico en `known_errors`).
- `src/application/use_cases/analyze_build.py`: endpoint legado, orquestación
  independiente de Jenkins, LLM y FastAPI.
- `src/application/use_cases/chat_with_build.py`: chat sobre el log de una
  build; persiste en `build_chat_messages`.
- `src/application/services/jenkins_monitor.py`: fallback externo para builds
  cuyo Jenkinsfile no llega a ejecutar `post`; también redespacha builds
  `queued`/`processing` pendientes.
- `src/application/services/analysis_dispatcher.py`: `Protocol` del
  despachador de análisis; `CeleryAnalysisDispatcher` (en
  `src/infrastructure/queue/`) es la única implementación de producción.
- `src/application/log_normalization.py`: normaliza el log (quita timestamps,
  números de build, rutas, IDs hex) antes de generar el embedding.
- `src/application/models.py`: contratos Pydantic de entrada/salida.
- `src/application/errors.py`: errores estables de la aplicación.
- `src/infrastructure/jenkins/client.py`: adaptador de `python-jenkins`.
- `src/infrastructure/llm/factory.py`: selección del proveedor LLM
  (`create_build_analyzer`/`create_embedder`/`create_chat_model`).
- `src/infrastructure/llm/ollama_client.py`: adaptador de generación/chat para
  Ollama.
- `src/infrastructure/llm/openai_compatible_client.py`: adaptador de Chat
  Completions compatible con OpenAI.
- `src/infrastructure/llm/embedding_client.py`: adaptadores de embeddings
  (Ollama y OpenAI-compatible).
- `src/infrastructure/llm/prompts.py`: prompts versionados junto al código.
- `src/infrastructure/persistence/{build_repository,known_error_repository,db}.py`:
  persistencia PostgreSQL vía `psycopg3` (pool sync); `known_errors` guarda un
  `trust_score` ajustado por feedback del usuario.
- `src/infrastructure/queue/`: `celery_app.py`, `dispatcher.py`
  (`CeleryAnalysisDispatcher`) y `tasks.py` (tarea `analyze_build`).
- `migrations/`: migraciones Alembic (SQL crudo vía `op.execute()`), aplicadas
  automáticamente al arrancar el contenedor `api`.
- `frontend/`: panel web independiente en Streamlit (`app.py` es el
  entrypoint; `dashboard_view.py`, `jobs_view.py` y `detail_view.py`
  renderizan las vistas; `build_card.py` es la tarjeta de build compartida
  entre dashboard y detalle de job; `nav.py` controla la navegación vía
  `st.session_state`/`st.query_params`; `log_highlight.py` resalta
  `ERROR`/`WARN`/`Exception`/`Caused by`; `client.py` habla con la API HTTP,
  nunca con Postgres/Redis directamente).
- `src/config.py`: única fuente de configuración por entorno.
- `tests/`: pruebas unitarias sin servicios externos (Postgres+pgvector se
  levanta efímero vía `testcontainers` para las que sí tocan la base).

## Reglas de diseño

1. Mantén la dirección de dependencias:
   `API -> aplicación <- infraestructura`. El caso de uso trabaja contra
   protocolos, no contra SDK concretos.
2. No añadas credenciales, URLs de entornos reales ni logs de clientes al
   repositorio. Toda configuración variable entra por `Settings`.
3. Toda llamada de red debe tener timeout y convertir errores del proveedor a
   un error definido en `src/application/errors.py`.
4. Ninguna respuesta del LLM se considera fiable hasta validarla con Pydantic.
   Todo proveedor debe devolver el contrato común `BuildAnalysis`.
5. El log de Jenkins es contenido no confiable. Conserva la defensa contra
   instrucciones incluidas en el log al cambiar prompts.
6. El endpoint público existente `GET /analyze/{job}/{build}` es compatible hacia
   atrás. Si cambia su contrato, actualiza pruebas, README y OpenAPI.
7. Prefiere pruebas unitarias con dobles sobre pruebas que requieran Jenkins u
   Ollama. Las integraciones reales pertenecen a una suite separada.
8. `SUCCESS` nunca debe invocar el LLM. La ingestión debe responder antes de que
   termine el análisis de `FAILURE`/`UNSTABLE`.
9. El monitor debe deduplicar por `job_name + build_number`; nunca debe analizar
   repetidamente la misma build.
10. No leas variables de proveedor dentro de los casos de uso. Añade proveedores
    mediante `create_build_analyzer` y conserva separadas generación y embeddings.
11. No reintroduzcas SQLite ni un modo sin Docker: Postgres, Redis y el worker
    de Celery corren siempre vía `docker compose`, incluso para desarrollo
    local con `--reload`.

## Comandos de trabajo

```bash
uv sync
uv run pytest -q  # necesita Docker: levanta Postgres+pgvector vía testcontainers
uv run ruff check .
uv run uvicorn apps.api.main:app --reload
```

Con contenedores:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec ollama ollama pull qwen3:1.7b
docker compose exec ollama ollama pull embeddinggemma
curl http://localhost:8000/health
```

## Criterio de terminado

- La lógica nueva tiene pruebas del camino correcto y del error relevante.
- `uv run pytest -q`, `uv run ruff check .` y `docker compose config` pasan.
- La configuración nueva aparece en `.env.example` y `docs/runbook.md`.
- Cualquier cambio arquitectónico queda reflejado en `docs/architecture.md`.

## Límites conocidos

- Los nombres de jobs con carpetas (`folder/job`) no caben en la ruta actual.
  Diseña una ruta o parámetro explícito antes de añadir soporte.
- Ollama no descarga el modelo al arrancar; debe prepararse con `ollama pull`.
- Jenkins no forma parte del `docker-compose.yml`; se configura como servicio
  externo mediante `JENKINS_URL`.
- `streamlit run frontend/app.py` agrega `/app/frontend` a `sys.path`, no
  `/app`; los imports absolutos `from frontend.xxx import ...` solo resuelven
  porque el servicio `frontend` fija `PYTHONPATH=/app` en `docker-compose.yml`.
  No lo quites.
