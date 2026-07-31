import streamlit as st

from frontend.build_card import render_build_card
from frontend.client import BackendClient, BackendError
from frontend.nav import go_to_job_detail, go_to_jobs, render_top_nav

_FAILED_STATUSES = {"FAILURE", "UNSTABLE"}


def render_jobs(client: BackendClient) -> None:
    st.title("Jobs")
    st.caption("Resumen de éxitos y fallos por job")
    render_top_nav("jobs")

    try:
        summaries = client.get_job_summaries()
    except BackendError as exc:
        st.error(str(exc))
        return

    if not summaries:
        st.info("No hay jobs registrados todavía.")
        return

    for summary in summaries:
        _render_job_card(summary)


def _render_job_card(summary: dict) -> None:
    with st.container(border=True):
        name_col, success_col, failure_col, other_col, action_col = st.columns(
            [3, 1, 1, 1, 1.2]
        )
        name_col.markdown(f"**{summary['job_name']}**")
        name_col.caption(f"{summary['total_builds']} builds en total")
        success_col.metric("✅ Éxitos", summary["success_count"])
        failure_col.metric("❌ Fallos", summary["failure_count"])
        other_col.metric("• Otros", summary["other_count"])
        if action_col.button(
            "Ver builds", key=f"job-{summary['job_name']}", use_container_width=True
        ):
            go_to_job_detail(summary["job_name"])


def render_job_detail(client: BackendClient, job_name: str) -> None:
    if st.button("← Volver a Jobs"):
        go_to_jobs()

    st.title(job_name)
    _render_job_builds(client, job_name)


@st.fragment(run_every="15s")
def _render_job_builds(client: BackendClient, job_name: str) -> None:
    try:
        builds = client.list_builds(500, job_name=job_name)
    except BackendError as exc:
        st.error(str(exc))
        return

    builds = [build for build in builds if build["job_name"] == job_name]
    failed = [build for build in builds if build["status"] in _FAILED_STATUSES]
    success = [build for build in builds if build["status"] == "SUCCESS"]
    other = [
        build for build in builds if build["status"] not in _FAILED_STATUSES
        and build["status"] != "SUCCESS"
    ]

    if not builds:
        st.info("No hay builds registradas para este job.")
        return

    st.subheader(f"❌ Fallidos ({len(failed)})")
    if not failed:
        st.caption("Sin builds fallidos.")
    for build in failed:
        render_build_card(client, build)

    st.subheader(f"✅ Exitosos ({len(success)})")
    if not success:
        st.caption("Sin builds exitosos.")
    for build in success:
        render_build_card(client, build)

    if other:
        st.subheader(f"• Otros ({len(other)})")
        for build in other:
            render_build_card(client, build)
