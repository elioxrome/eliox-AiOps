import streamlit as st

from frontend.client import BackendClient
from frontend.config import FrontendSettings
from frontend.dashboard_view import render_dashboard
from frontend.detail_view import render_detail

st.set_page_config(page_title="Jenkins AIOps", page_icon="🛠️", layout="wide")

_CUSTOM_CSS = """
<style>
.badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px;
  font-weight:600; text-transform:uppercase; letter-spacing:.03em; }
.badge-success { background:#14532d; color:#bbf7d0; }
.badge-failure { background:#7f1d1d; color:#fecaca; }
.badge-unstable { background:#854d0e; color:#fde68a; }
.badge-aborted, .badge-not_built { background:#334155; color:#cbd5e1; }
.chip { display:inline-block; padding:2px 8px; border-radius:6px; font-size:11px;
  background:#1d3a63; color:#93c5fd; }
.log-view { background:#0b1020; border:1px solid #26314d; border-radius:8px;
  padding:14px; max-height:520px; overflow-y:auto; font-family:ui-monospace,monospace;
  font-size:13px; line-height:1.5; white-space:pre-wrap; word-break:break-word; }
.log-view .log-error { color:#fca5a5; font-weight:600; }
.log-view .log-warn { color:#fde68a; }
.log-view .log-exception { color:#fdba74; font-weight:600; }
.log-view .log-caused-by { color:#f9a8d4; font-weight:600; }
</style>
"""


@st.cache_resource
def get_settings() -> FrontendSettings:
    return FrontendSettings.from_env()


@st.cache_resource
def get_backend_client() -> BackendClient:
    settings = get_settings()
    return BackendClient(settings.api_base_url, settings.request_timeout_seconds)


def main() -> None:
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    if "view" not in st.session_state:
        query_build_id = st.query_params.get("build_id")
        if query_build_id:
            st.session_state["view"] = "detail"
            st.session_state["selected_build_id"] = int(query_build_id)
        else:
            st.session_state["view"] = "dashboard"

    client = get_backend_client()

    if st.session_state["view"] == "detail":
        render_detail(client, st.session_state["selected_build_id"])
    else:
        render_dashboard(client)


main()
