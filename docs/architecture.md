# Arquitectura

## Flujo principal

```text
Jenkins post/always
       |
       | POST /api/builds (estado + log)
       v
FastAPI -----> PostgreSQL -----> respuesta HTTP 202
                   |
                   | FAILURE / UNSTABLE
                   v
        dispatcher.dispatch() -----> Redis (cola "analysis")
                                           |
                                           v
                                    worker de Celery
                                           |
              +----------------------------+-----------------------------+
              |                            |                             |
     detect_known_failure          known_errors (pgvector)          BuildAnalyzer
      (regex, sin coste)         búsqueda semántica del log      (si no hubo match)
              |                            |                             |
              +----------------------------+-----------------------------+
                                           |
                                           v
                          diagnóstico en PostgreSQL -----> /dashboard

Jenkins API <---- monitor periódico
     |
     +---- captura fallos de compilación que nunca ejecutan post/always
     +---- reintenta builds queued/processing vía el mismo dispatcher
```

`IngestBuildUseCase.receive` decide si hace falta IA. `SUCCESS`, `ABORTED` y
`NOT_BUILT` se completan sin modelo. `FAILURE` y `UNSTABLE` se guardan como
`queued` y se despachan a Redis mediante `AnalysisDispatcher`
(`CeleryAnalysisDispatcher` en producción); un worker de Celery ejecuta
`IngestBuildUseCase.process`. La concurrencia del worker
(`CELERY_WORKER_CONCURRENCY`) acota cuántas builds se analizan en paralelo, en
vez del `BackgroundTasks` sin límite que usaba la versión anterior.

`IngestBuildUseCase.process` prueba, en orden: reglas regex deterministas
(`detect_known_failure`), luego una búsqueda semántica en `known_errors`
(embedding del log normalizado + distancia coseno vía `pgvector`), y solo si
no hay coincidencia confiable, el LLM. Cada diagnóstico nuevo del LLM se
indexa en `known_errors` para acelerar fallos futuros similares; el feedback
del usuario (👍/👎) ajusta el `trust_score` de la entrada usada.

El endpoint antiguo conserva la consulta directa a Jenkins para compatibilidad.
El monitor externo deduplica por nombre y número de build. Solo importa la última
build terminada de cada job en cada escaneo, y reintenta builds atascadas en
`queued`/`processing` a través del mismo `AnalysisDispatcher` que usa el
endpoint de ingesta (un solo camino de análisis).

## Contratos

`BuildAnalysis` es el contrato interno común para todos los proveedores:

- `category`: categoría breve y no vacía.
- `root_cause`: causa explicada con evidencia del log.
- `confidence`: número entre 0 y 1.
- `recommendation`: siguiente acción concreta.

Cada adaptador traduce su protocolo a `BuildAnalysis` y valida el JSON antes de
devolverlo. Una respuesta inválida o un fallo de proveedor se convierte en
`ExternalServiceError`; la API lo expone como HTTP 502.

`create_build_analyzer` selecciona el adaptador mediante `LLM_PROVIDER`. Los
casos de uso no conocen URLs, autenticación ni formatos propios del proveedor.
La configuración `EMBEDDING_*` es independiente de `LLM_*`: `create_embedder`
(en la misma factoría) elige el proveedor de embeddings, que puede ser
distinto del generativo. El chat (`ChatClient.chat`) reutiliza el proveedor
generativo: no es una capacidad separada, es la misma conversación sobre el
mismo modelo.

## Decisiones

### Configuración sin framework adicional

`Settings` usa `dataclass` y variables de entorno. El proyecto todavía tiene
pocas opciones y no necesita una dependencia de configuración adicional para
leer variables de entorno. Alembic y `psycopg`/`pgvector` sí se incorporaron
como dependencias, pero son tooling de infraestructura (migraciones y driver
de base de datos), no un framework de configuración para la capa de
aplicación — la distinción que motivó la decisión original sigue vigente.

### Ruta síncrona

Los SDK usados son síncronos. FastAPI ejecuta una función de ruta normal en su
pool de hilos, evitando bloquear el event loop. `BuildRepository` y
`KnownErrorRepository` usan `psycopg_pool.ConnectionPool` (síncrono) por el
mismo motivo. Si los adaptadores migran a clientes async, la ruta y el caso de
uso deben migrar conjuntamente.

### Tramo final del log

Se conserva el final porque Jenkins suele colocar allí el error terminal y su
stack trace. Cambiar esta estrategia requiere una prueba que demuestre cómo se
preserva la señal relevante dentro del límite de contexto.

### Cola de análisis con Celery + Redis, no `asyncio.Queue` interno

Varias builds `FAILURE`/`UNSTABLE` pueden llegar a la vez; sin un límite de
concurrencia real, todas terminaban golpeando al proveedor LLM en paralelo.
Se eligió Celery + Redis (en vez de una cola en memoria) porque es el
mecanismo estándar del ecosistema Python para esto, sobrevive a un reinicio
del proceso `api`, y la concurrencia del worker (`CELERY_WORKER_CONCURRENCY`)
es un límite explícito y configurable. `AnalysisDispatcher` (Protocol) aísla
Celery de la capa de aplicación: `IngestBuildUseCase` y `JenkinsMonitor` solo
conocen `dispatch(build_id, status)`.

### PostgreSQL + pgvector en vez de un vector store separado

El RAG de errores conocidos necesita persistencia relacional (para filtrar,
paginar, relacionar con `builds`) y búsqueda por similitud vectorial. En vez
de sumar un servicio de vectores dedicado (Chroma, Qdrant), se usa la
extensión `pgvector` sobre la misma PostgreSQL que ya almacena `builds`: una
sola fuente de verdad, consistencia transaccional entre el diagnóstico y su
embedding, y filtrado por metadata con SQL normal.

### Firma normalizada en vez de embeber el log completo

`normalize_log_signature` recorta timestamps, números de build, rutas y IDs
hexadecimales antes de embeber. Sin esto, dos ejecuciones del mismo fallo
producen logs "distintos" por ruido irrelevante y el RAG nunca encontraría
coincidencias. La normalización es una heurística basada en regex; si un tipo
de log nuevo no normaliza bien, ajusta los patrones en
`src/application/log_normalization.py` en vez de bajar el umbral de similitud.

## Cómo extender

- Nuevo proveedor LLM o de chat: implementa `analyze(prompt) -> BuildAnalysis`
  y `chat(messages) -> str`.
- Nuevo proveedor de embeddings: implementa `embed(text) -> list[float]` y
  regístralo en `create_embedder`.
- Nueva fuente CI: implementa
  `get_build_log(job_name, build_number) -> str`.
- Nuevo campo de salida: cambia `BuildAnalysis`, prompt, pruebas y README en una
  misma modificación.
- Nueva tabla o columna: añade una migración de Alembic
  (`uv run alembic revision -m "..."`) con SQL crudo, no ORM.
