# Arquitectura

## Flujo principal

```text
Jenkins post/always
       |
       | POST /api/builds (estado + log)
       v
FastAPI -----> SQLite -----> respuesta HTTP 202
                   |
                   | FAILURE / UNSTABLE
                   v
             tarea de análisis -----> Ollama
                   |
                   v
             diagnóstico en SQLite -----> /dashboard

Jenkins API <---- monitor periódico
     |
     +---- captura fallos de compilación que nunca ejecutan post/always
```

`IngestBuildUseCase` decide si hace falta IA. `SUCCESS`, `ABORTED` y `NOT_BUILT`
se completan sin modelo. `FAILURE` y `UNSTABLE` se encolan como tarea de fondo.
El endpoint antiguo conserva la consulta directa a Jenkins para compatibilidad.
El monitor externo deduplica por nombre y número de build. Solo importa la última
build terminada de cada job en cada escaneo.

## Contratos

`BuildAnalysis` es el contrato interno y HTTP:

- `category`: categoría breve y no vacía.
- `root_cause`: causa explicada con evidencia del log.
- `confidence`: número entre 0 y 1.
- `recommendation`: siguiente acción concreta.

Ollama devuelve un sobre propio cuyo campo `response` contiene JSON. El adaptador
valida ese JSON antes de devolverlo a la aplicación. Una respuesta inválida o un
fallo de proveedor se convierte en `ExternalServiceError`; la API lo expone como
HTTP 502.

## Decisiones

### Configuración sin framework adicional

`Settings` usa `dataclass` y variables de entorno. El proyecto todavía tiene
pocas opciones y no necesita una dependencia de configuración adicional.

### Ruta síncrona

Los SDK usados son síncronos. FastAPI ejecuta una función de ruta normal en su
pool de hilos, evitando bloquear el event loop. Si los adaptadores migran a
clientes async, la ruta y el caso de uso deben migrar conjuntamente.

### Tramo final del log

Se conserva el final porque Jenkins suele colocar allí el error terminal y su
stack trace. Cambiar esta estrategia requiere una prueba que demuestre cómo se
preserva la señal relevante dentro del límite de contexto.

## Cómo extender

- Nuevo proveedor LLM: implementa `analyze(prompt) -> BuildAnalysis`.
- Nueva fuente CI: implementa
  `get_build_log(job_name, build_number) -> str`.
- Nuevo campo de salida: cambia `BuildAnalysis`, prompt, pruebas y README en una
  misma modificación.
