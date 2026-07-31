import streamlit as st


def go_to_detail(build_id: int) -> None:
    st.session_state["view"] = "detail"
    st.session_state["selected_build_id"] = build_id
    st.query_params.clear()
    st.query_params["build_id"] = str(build_id)
    st.rerun(scope="app")


def go_to_dashboard() -> None:
    st.session_state["view"] = "dashboard"
    st.session_state.pop("selected_build_id", None)
    st.session_state.pop("selected_job_name", None)
    st.query_params.clear()
    st.rerun(scope="app")


def go_to_jobs() -> None:
    st.session_state["view"] = "jobs"
    st.session_state.pop("selected_build_id", None)
    st.session_state.pop("selected_job_name", None)
    st.query_params.clear()
    st.rerun(scope="app")


def go_to_job_detail(job_name: str) -> None:
    st.session_state["view"] = "job_detail"
    st.session_state["selected_job_name"] = job_name
    st.query_params.clear()
    st.query_params["job"] = job_name
    st.rerun(scope="app")


def render_top_nav(active: str) -> None:
    dashboard_col, jobs_col = st.columns(2)
    if dashboard_col.button(
        "📋 Panel de builds",
        disabled=active == "dashboard",
        use_container_width=True,
    ):
        go_to_dashboard()
    if jobs_col.button(
        "🗂️ Jobs", disabled=active == "jobs", use_container_width=True
    ):
        go_to_jobs()
