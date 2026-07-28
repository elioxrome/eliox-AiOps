from datetime import date

import streamlit as st

from frontend.client import BackendClient, BackendError
from frontend.nav import go_to_detail

_STATUSES = ["SUCCESS", "FAILURE", "UNSTABLE", "ABORTED", "NOT_BUILT"]
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


def render_dashboard(client: BackendClient) -> None:
    st.title("Jenkins AIOps")
    st.caption("Monitor de builds y diagnósticos · se actualiza cada 15 s")

    try:
        facets = client.get_facets()
    except BackendError as exc:
        st.error(str(exc))
        facets = {"jobs": [], "categories": []}

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        status_choice = st.selectbox("Estado", ["Todos", *_STATUSES])
    with col2:
        job_choice = st.selectbox("Job", ["Todos", *facets["jobs"]])
    with col3:
        category_choice = st.selectbox("Categoría", ["Todas", *facets["categories"]])
    with col4:
        date_from = st.date_input("Desde", value=None)
    with col5:
        date_to = st.date_input("Hasta", value=None)

    _render_build_list(
        client,
        status=None if status_choice == "Todos" else status_choice,
        job_name=None if job_choice == "Todos" else job_choice,
        category=None if category_choice == "Todas" else category_choice,
        date_from=date_from or None,
        date_to=date_to or None,
    )


@st.fragment(run_every="15s")
def _render_build_list(
    client: BackendClient,
    status: str | None,
    job_name: str | None,
    category: str | None,
    date_from: date | None,
    date_to: date | None,
) -> None:
    try:
        builds = client.list_builds(
            100,
            status=status,
            job_name=job_name,
            category=category,
            date_from=date_from,
            date_to=date_to,
        )
    except BackendError as exc:
        st.error(str(exc))
        return

    successes = sum(build["status"] == "SUCCESS" for build in builds)
    problems = sum(build["status"] in {"FAILURE", "UNSTABLE"} for build in builds)
    pending = sum(
        build["processing_status"] in {"queued", "processing"} for build in builds
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Correctas", successes)
    metric2.metric("Con problemas", problems)
    metric3.metric("Analizando", pending)

    if not builds:
        st.info("No hay builds que coincidan con los filtros.")
        return

    for build in builds:
        _render_card(client, build)


def _render_card(client: BackendClient, build: dict) -> None:
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
