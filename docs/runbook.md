# Runbook

## Variables

| Variable | Predeterminado | Uso |
|---|---:|---|
| `JENKINS_URL` | `http://jenkins:8080` | URL base de Jenkins |
| `JENKINS_USERNAME` | vacío | Usuario; vacío permite acceso anónimo |
| `JENKINS_TOKEN` | vacío | API token de Jenkins |
| `JENKINS_TIMEOUT_SECONDS` | `30` | Timeout del SDK de Jenkins |
| `OLLAMA_URL` | `http://ollama:11434` | URL de Ollama |
| `OLLAMA_MODEL` | `qwen3:8b` | Modelo usado para el análisis |
| `DOCKER_OLLAMA_MODEL` | `qwen3:1.7b` | Modelo rápido del Ollama de Compose |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Timeout de generación |
| `MAX_LOG_CHARACTERS` | `10000` | Máximo de caracteres enviados |
| `DATABASE_PATH` | `data/jenkins-aiops.db` | Archivo SQLite |
| `DASHBOARD_LIMIT` | `100` | Builds visibles en el panel |
| `INGESTION_TOKEN` | vacío | Secreto para `POST /api/builds` |
| `JENKINS_POLL_ENABLED` | `false` | Activa el monitor externo |
| `JENKINS_POLL_INTERVAL_SECONDS` | `15` | Frecuencia del monitor |
| `JENKINS_POLL_JOBS` | `*` | Jobs, separados por coma, o todos |

Los timeouts y límites deben ser números positivos. No guardes `.env` en control
de versiones.

El servicio `api` carga `.env` mediante `env_file`. Así, variables exportadas en
la terminal no reemplazan accidentalmente la URL o las credenciales de Jenkins
al recrear los contenedores. Compose fija `OLLAMA_URL` a su red interna y usa
`DOCKER_OLLAMA_MODEL`; esto permite usar otro modelo en la ejecución local con
`uv` mediante `OLLAMA_MODEL`.

Ollama no publica el puerto `11434` en el host: la API accede mediante
`http://ollama:11434` dentro de la red de Compose. Esto evita conflictos con una
instalación local de Ollama que ya esté escuchando en ese puerto.

## Verificación

```bash
docker compose config
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/api/builds
```

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

### HTTP 502: fallo de Ollama

Comprueba que el contenedor está saludable y que el modelo existe:

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
