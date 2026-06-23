import re

from src.application.models import BuildAnalysis


def detect_known_failure(log: str) -> BuildAnalysis | None:
    if "WorkflowScript:" not in log:
        return None

    expected_step = re.search(
        r"WorkflowScript:\s*(\d+):\s*Expected a step",
        log,
    )
    if expected_step:
        line = expected_step.group(1)
        return BuildAnalysis(
            category="sintaxis_pipeline",
            root_cause=(
                "El Pipeline declarativo encontró sintaxis Groovy inválida "
                f"en la línea {line}: se esperaba un paso válido de Jenkins."
            ),
            confidence=1,
            recommendation=(
                f"Abre el Jenkinsfile en la línea {line} y elimina la expresión "
                "desconocida o sustitúyela por un paso válido como echo, sh, "
                "script o una directiva compatible del Pipeline."
            ),
        )

    compilation_error = re.search(
        r"WorkflowScript:\s*(\d+):\s*([^\n]+)",
        log,
    )
    if compilation_error:
        line, message = compilation_error.groups()
        return BuildAnalysis(
            category="sintaxis_pipeline",
            root_cause=(
                f"La compilación del Jenkinsfile falló en la línea {line}: "
                f"{message}"
            ),
            confidence=0.99,
            recommendation=(
                f"Valida la sintaxis del Jenkinsfile alrededor de la línea {line} "
                "antes de volver a ejecutar el Pipeline."
            ),
        )
    return None
