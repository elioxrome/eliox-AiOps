import streamlit as st


def go_to_detail(build_id: int) -> None:
    st.session_state["view"] = "detail"
    st.session_state["selected_build_id"] = build_id
    st.query_params["build_id"] = str(build_id)
    st.rerun(scope="app")


def go_to_dashboard() -> None:
    st.session_state["view"] = "dashboard"
    st.session_state.pop("selected_build_id", None)
    st.query_params.clear()
    st.rerun(scope="app")
