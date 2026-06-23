from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from apps.api.dependencies import get_repository, get_settings
from src.application.models import BuildRecord
from src.config import Settings
from src.infrastructure.persistence.build_repository import BuildRepository

router = APIRouter(tags=["dashboard"])


def _value(value: str | None, fallback: str = "—") -> str:
    return escape(value) if value else fallback


def _build_row(build: BuildRecord) -> str:
    rating = (
        "👍" if build.rating == 1 else "👎" if build.rating == -1 else "Sin valorar"
    )
    job = escape(build.job_name)
    build_link = (
        f'<a href="{escape(build.build_url)}" target="_blank">#{build.build_number}</a>'
        if build.build_url
        else f"#{build.build_number}"
    )
    return f"""
    <tr>
      <td><strong>{job}</strong><br>{build_link}</td>
      <td><span class="badge {build.status.value.lower()}">
        {build.status.value}</span></td>
      <td><span class="processing">{build.processing_status.value}</span></td>
      <td><strong>{_value(build.category)}</strong><br>
        {_value(build.root_cause)}</td>
      <td>{_value(build.recommendation)}</td>
      <td>{rating}<div class="rating">
        <button onclick="rate({build.id}, 1)">Útil</button>
        <button onclick="rate({build.id}, -1)">No útil</button>
      </div></td>
    </tr>
    """


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    repository: Annotated[BuildRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    builds = repository.list_recent(settings.dashboard_limit)
    successes = sum(build.status.value == "SUCCESS" for build in builds)
    problems = sum(
        build.status.value in {"FAILURE", "UNSTABLE"} for build in builds
    )
    pending = sum(
        build.processing_status.value in {"queued", "processing"} for build in builds
    )
    rows = "".join(_build_row(build) for build in builds)
    return HTMLResponse(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>Jenkins AIOps</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
    body {{ margin: 0; background: #0b1020; color: #e7ecf5; }}
    main {{ max-width: 1500px; margin: auto; padding: 28px; }}
    h1 {{ margin-bottom: 4px; }} .muted {{ color: #94a3b8; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr);
      gap: 16px; margin: 24px 0; }}
    .card {{ background: #151c30; border: 1px solid #26314d;
      border-radius: 12px; padding: 18px; }}
    .number {{ font-size: 30px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: #151c30;
      border-radius: 12px; overflow: hidden; }}
    th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid #26314d;
      vertical-align: top; }}
    th {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
    .badge {{ padding: 5px 8px; border-radius: 999px; font-size: 12px; }}
    .success {{ background: #14532d; }} .failure {{ background: #7f1d1d; }}
    .unstable {{ background: #854d0e; }} .aborted {{ background: #334155; }}
    .processing {{ color: #93c5fd; }} a {{ color: #60a5fa; }}
    button {{ margin: 6px 4px 0 0; padding: 6px 9px; color: #e7ecf5;
      background: #26314d; border: 0; border-radius: 6px; cursor: pointer; }}
    @media(max-width: 900px) {{ .stats {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }} }}
  </style>
</head>
<body><main>
  <h1>Jenkins AIOps</h1>
  <div class="muted">Monitor de builds y diagnósticos · actualiza cada 15 s</div>
  <section class="stats">
    <div class="card"><div class="number">{successes}</div>Correctas</div>
    <div class="card"><div class="number">{problems}</div>Con problemas</div>
    <div class="card"><div class="number">{pending}</div>Analizando</div>
  </section>
  <table><thead><tr>
    <th>Build</th><th>Estado</th><th>Proceso</th><th>Diagnóstico</th>
    <th>Recomendación</th><th>Valoración</th>
  </tr></thead><tbody>{rows}</tbody></table>
</main>
<script>
async function rate(id, rating) {{
  await fetch(`/api/builds/${{id}}/feedback`, {{
    method: "POST", headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{rating}})
  }});
  location.reload();
}}
</script></body></html>"""
    )
