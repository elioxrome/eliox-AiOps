import streamlit as st

from frontend.client import BackendClient, BackendError
from frontend.nav import go_to_detail

_STATUS_ICON = {
    "SUCCESS": "✅",
    "FAILURE": "❌",
    "UNSTABLE": "⚠️",
    "ABORTED": "⏹️",
    "NOT_BUILT": "⏳",
}
_PROCESSING_LABEL = {
    "queued": "En cola",
    "processing": "Analizando…",
    "completed": "Completado",
    "failed": "Falló el análisis",
}


def render_build_card(client: BackendClient, build: dict) -> None:
    with st.container(border=True):
        status_col, job_col, diag_col, proc_col, rate_col, action_col = st.columns(
            [1, 2.2, 2.8, 1.2, 1.3, 1]
        )

        status = build["status"]
        status_col.markdown(
            f'<span class="badge badge-{status.lower()}">'
            f'{_STATUS_ICON.get(status, "•")} {status}</span>',
            unsafe_allow_html=True,
        )

        job_label = f"**{build['job_name']}** #{build['build_number']}"
        if build.get("build_url"):
            job_label = f"[{job_label}]({build['build_url']})"
        job_col.markdown(job_label)

        category = build.get("category") or "—"
        root_cause = build.get("root_cause") or "Sin diagnóstico todavía."
        diag_col.markdown(f"**{category}**  \n{root_cause}")

        processing = build["processing_status"]
        proc_col.markdown(
            f'<span class="chip">'
            f"{_PROCESSING_LABEL.get(processing, processing)}</span>",
            unsafe_allow_html=True,
        )

        up_col, down_col = rate_col.columns(2)
        if up_col.button("👍", key=f"up-{build['id']}"):
            _rate(client, build["id"], 1)
        if down_col.button("👎", key=f"down-{build['id']}"):
            _rate(client, build["id"], -1)

        if action_col.button("Ver detalle", key=f"detail-{build['id']}"):
            go_to_detail(build["id"])


def _rate(client: BackendClient, build_id: int, rating: int) -> None:
    try:
        client.rate_build(build_id, rating, None)
    except BackendError as exc:
        st.error(str(exc))
    else:
        st.rerun(scope="fragment")
