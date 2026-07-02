from html import escape


def _value(value: str | None, fallback: str = "—") -> str:
    return escape(value) if value else fallback


def _build_row(build: dict) -> str:
    rating = build.get("rating")
    rating_label = "👍" if rating == 1 else "👎" if rating == -1 else "Sin valorar"
    job = escape(build["job_name"])
    build_url = build.get("build_url")
    build_link = (
        f'<a href="{escape(build_url)}" target="_blank">#{build["build_number"]}</a>'
        if build_url
        else f"#{build['build_number']}"
    )
    return f"""
    <tr>
      <td><strong>{job}</strong><br>{build_link}</td>
      <td><span class="badge {build['status'].lower()}">
        {build['status']}</span></td>
      <td><span class="processing">{build['processing_status']}</span></td>
      <td><strong>{_value(build.get('category'))}</strong><br>
        {_value(build.get('root_cause'))}</td>
      <td>{_value(build.get('recommendation'))}</td>
      <td>{rating_label}<div class="rating">
        <button onclick="rate({build['id']}, 1)">Útil</button>
        <button onclick="rate({build['id']}, -1)">No útil</button>
      </div></td>
      <td><a href="/dashboard/builds/{build['id']}">Ver log completo</a></td>
    </tr>
    """


def dashboard_page(builds: list[dict]) -> str:
    successes = sum(build["status"] == "SUCCESS" for build in builds)
    problems = sum(build["status"] in {"FAILURE", "UNSTABLE"} for build in builds)
    pending = sum(
        build["processing_status"] in {"queued", "processing"} for build in builds
    )
    rows = "".join(_build_row(build) for build in builds)
    return f"""<!doctype html>
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
    <th>Recomendación</th><th>Valoración</th><th>Acciones</th>
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


def build_detail_page(build: dict, log: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Jenkins AIOps · {escape(build['job_name'])} #{build['build_number']}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
    body {{ margin: 0; background: #0b1020; color: #e7ecf5; }}
    main {{ max-width: 1100px; margin: auto; padding: 28px; }}
    h1 {{ margin-bottom: 4px; }} .muted {{ color: #94a3b8; }}
    a.back {{ color: #60a5fa; display: inline-block; margin-bottom: 16px; }}
    .card {{ background: #151c30; border: 1px solid #26314d;
      border-radius: 12px; padding: 18px; margin-bottom: 20px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; max-height: 480px;
      overflow-y: auto; background: #0b1020; padding: 14px; border-radius: 8px;
      border: 1px solid #26314d; }}
    .chat-log {{ display: flex; flex-direction: column; gap: 10px;
      max-height: 400px; overflow-y: auto; margin-bottom: 14px; }}
    .msg {{ padding: 10px 12px; border-radius: 8px; max-width: 85%; }}
    .msg.user {{ background: #1d3a63; align-self: flex-end; }}
    .msg.assistant {{ background: #26314d; align-self: flex-start; }}
    .chat-form {{ display: flex; gap: 8px; }}
    textarea {{ flex: 1; resize: vertical; min-height: 44px; background: #0b1020;
      color: #e7ecf5; border: 1px solid #26314d; border-radius: 8px; padding: 10px; }}
    button {{ padding: 8px 14px; color: #e7ecf5; background: #26314d;
      border: 0; border-radius: 6px; cursor: pointer; }}
  </style>
</head>
<body><main>
  <a class="back" href="/dashboard">&larr; Volver al panel</a>
  <h1>{escape(build['job_name'])} #{build['build_number']}</h1>
  <div class="muted">Estado: {build['status']} ·
    Proceso: {build['processing_status']}</div>

  <section class="card">
    <h3>Diagnóstico</h3>
    <p><strong>{_value(build.get('category'))}</strong></p>
    <p>{_value(build.get('root_cause'))}</p>
    <p>{_value(build.get('recommendation'))}</p>
  </section>

  <section class="card">
    <h3>Log completo</h3>
    <pre>{escape(log)}</pre>
  </section>

  <section class="card">
    <h3>Preguntar a la IA sobre este log</h3>
    <div id="chat-log" class="chat-log"></div>
    <form id="chat-form" class="chat-form">
      <textarea id="chat-input" placeholder="¿Por qué falló este paso?"></textarea>
      <button type="submit">Enviar</button>
    </form>
  </section>
</main>
<script>
const buildId = {build['id']};
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

function renderMessages(messages) {{
  chatLog.innerHTML = "";
  for (const message of messages) {{
    if (message.role === "system") continue;
    const bubble = document.createElement("div");
    bubble.className = `msg ${{message.role}}`;
    bubble.textContent = message.content;
    chatLog.appendChild(bubble);
  }}
  chatLog.scrollTop = chatLog.scrollHeight;
}}

async function loadHistory() {{
  const response = await fetch(`/api/builds/${{buildId}}/chat`);
  if (!response.ok) return;
  const data = await response.json();
  renderMessages(data.messages);
}}

chatForm.addEventListener("submit", async (event) => {{
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  chatInput.value = "";
  chatInput.disabled = true;
  try {{
    const response = await fetch(`/api/builds/${{buildId}}/chat`, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{message}}),
    }});
    if (!response.ok) {{
      throw new Error("chat request failed");
    }}
    const data = await response.json();
    renderMessages(data.messages);
  }} finally {{
    chatInput.disabled = false;
    chatInput.focus();
  }}
}});

loadHistory();
</script></body></html>"""
