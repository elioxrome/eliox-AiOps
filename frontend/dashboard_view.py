from datetime import date

import streamlit as st

from frontend.build_card import render_build_card
from frontend.client import BackendClient, BackendError
from frontend.nav import render_top_nav

_STATUSES = ["SUCCESS", "FAILURE", "UNSTABLE", "ABORTED", "NOT_BUILT"]


def render_dashboard(client: BackendClient) -> None:
    st.title("Jenkins AIOps")
    st.caption("Monitor de builds y diagnósticos · se actualiza cada 15 s")
    render_top_nav("dashboard")

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
        category_choice = st.selectbox(
            "Categoría", ["Todas", *facets["categories"]]
        )
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
    problems = sum(
        build["status"] in {"FAILURE", "UNSTABLE"} for build in builds
    )
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
        render_build_card(client, build)
