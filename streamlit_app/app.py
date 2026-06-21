"""
DocuMind — Streamlit frontend
Mirrors the original React app's flow: App.jsx -> LoginPage.jsx / Dashboard.jsx
"""
import streamlit as st

from api_client import ApiError
import auth_view
import dashboard_view

st.set_page_config(
    page_title="DocuMind — Ask Your Documents Anything",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Session state init (equivalent to React's useState + localStorage) ----
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None


def handle_login(token_data: dict):
    """Equivalent to App.jsx's handleLogin."""
    st.session_state.token = token_data["access_token"]
    st.session_state.user = {
        "id": token_data["user_id"],
        "username": token_data["username"],
    }


def handle_logout():
    """Equivalent to App.jsx's handleLogout."""
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.pop("messages", None)
    st.rerun()


# ---- Route between Login and Dashboard, just like App.jsx ----
if not st.session_state.token:
    auth_view.render(on_login=handle_login)
else:
    dashboard_view.render(
        user=st.session_state.user,
        token=st.session_state.token,
        on_logout=handle_logout,
    )
