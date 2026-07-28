# Esquema de base de datos

Generado a partir de las migraciones de Alembic en `migrations/versions/`
(orden: `ab1386998fbf` → `934c32287d37` → `bdcb1487656c` → `0871849c2c2e` →
`b76b27eff5b5`).
PostgreSQL + extensión `vector` (pgvector).

```mermaid
erDiagram
    BUILDS ||--o{ KNOWN_ERRORS : "source_build_id"
    KNOWN_ERRORS ||--o{ BUILDS : "matched_known_error_id"
    BUILDS ||--o{ BUILD_CHAT_MESSAGES : "build_id"

    BUILDS {
        bigint id PK
        text job_name "UNIQUE con build_number"
        int build_number
        text status
        text build_url
        text log
        text processing_status
        text category
        text root_cause
        double confidence
        text recommendation
        text affected_file
        text error
        int rating
        text feedback_comment
        bigint matched_known_error_id FK
        timestamptz created_at
        timestamptz updated_at
    }

    MONITOR_STATE {
        text job_name PK
        int last_build_number
        timestamptz updated_at
    }

    KNOWN_ERRORS {
        bigint id PK
        text signature
        vector embedding "VECTOR(EMBEDDING_DIMENSIONS), índice hnsw"
        text category
        text root_cause
        text recommendation
        text affected_file
        double confidence
        double trust_score "default 1.0, rango 0..2"
        int hit_count
        timestamptz last_matched_at
        bigint source_build_id FK
        timestamptz created_at
        timestamptz updated_at
    }

    BUILD_CHAT_MESSAGES {
        bigint id PK
        bigint build_id FK
        text role
        text content
        timestamptz created_at
    }
```

## Notas

- `monitor_state` no tiene claves foráneas; se relaciona con `builds` solo por
  `job_name` a nivel de aplicación (estado del poller de Jenkins en
  `JenkinsMonitor`).
- `known_errors.source_build_id` → `builds.id` (`ON DELETE SET NULL`): la
  build que originó el diagnóstico indexado.
- `builds.matched_known_error_id` → `known_errors.id` (`ON DELETE SET NULL`):
  qué entrada RAG resolvió la build, usada para ajustar `trust_score` con el
  feedback del usuario.
- `build_chat_messages.build_id` → `builds.id` (`ON DELETE CASCADE`): historial
  de chat por build.
- `builds.affected_file` y `known_errors.affected_file` son opcionales
  (`NULL` si el LLM no lo identifica); los diagnósticos previos a la
  migración `b76b27eff5b5` siempre lo tienen `NULL`.
- La dimensión de `known_errors.embedding` se fija en tiempo de migración
  desde `EMBEDDING_DIMENSIONS` (por defecto 768); cambiarla requiere una
  nueva migración que recree la columna/índice.
