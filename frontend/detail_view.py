import streamlit as st

from frontend.client import BackendClient, BackendError
from frontend.log_highlight import highlight_log
from frontend.nav import go_to_dashboard


def render_detail(client: BackendClient, build_id: int) -> None:
    if st.button("← Volver al panel"):
        go_to_dashboard()

    try:
        build = client.get_build(build_id)
    except BackendError as exc:
        st.error(str(exc))
        return

    if build is None:
        st.warning("Build no encontrada.")
        return

    st.title(f"{build['job_name']} #{build['build_number']}")
    st.caption(f"Estado: {build['status']} · Proceso: {build['processing_status']}")

    _render_analysis_panel(build)

    try:
        log = client.get_log(build_id)
    except BackendError as exc:
        st.error(str(exc))
        log = ""

    with st.container(border=True):
        st.subheader("Log completo")
        st.markdown(
            f'<div class="log-view">{highlight_log(log)}</div>',
            unsafe_allow_html=True,
        )

    _render_feedback(client, build)
    _render_chat(client, build_id)


def _render_analysis_panel(build: dict) -> None:
    with st.container(border=True):
        st.subheader("Diagnóstico de IA")
        confidence = build.get("confidence")

        metric_col, detail_col = st.columns([1, 3])
        with metric_col:
            label = f"{confidence:.0%}" if confidence is not None else "—"
            st.metric("Confianza", label)
        with detail_col:
            st.markdown(f"**Categoría:** {build.get('category') or '—'}")
            affected_file = build.get("affected_file") or "—"
            st.markdown(f"**Archivo afectado:** `{affected_file}`")

        st.markdown("**Causa raíz**")
        st.write(build.get("root_cause") or "Sin diagnóstico todavía.")
        st.markdown("**Recomendación**")
        st.info(build.get("recommendation") or "Sin recomendación todavía.")


def _render_feedback(client: BackendClient, build: dict) -> None:
    st.subheader("¿Fue útil este diagnóstico?")
    up_col, down_col, _ = st.columns([1, 1, 4])
    if up_col.button("👍 Útil"):
        _rate(client, build["id"], 1)
    if down_col.button("👎 No útil"):
        _rate(client, build["id"], -1)


def _rate(client: BackendClient, build_id: int, rating: int) -> None:
    try:
        client.rate_build(build_id, rating, None)
    except BackendError as exc:
        st.error(str(exc))
    else:
        st.rerun()


def _render_chat(client: BackendClient, build_id: int) -> None:
    st.subheader("Preguntar a la IA sobre este log")
    try:
        history = client.get_chat_history(build_id)["messages"]
    except BackendError as exc:
        st.error(str(exc))
        history = []

    for message in history:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("¿Por qué falló este paso?")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"), st.spinner("Pensando…"):
            try:
                client.post_chat_message(build_id, question)
            except BackendError as exc:
                st.error(f"No se pudo obtener respuesta: {exc}")
                return
        st.rerun()
