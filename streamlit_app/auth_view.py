"""
Login / Register screen — mirrors frontend/src/pages/LoginPage.jsx
"""
import streamlit as st
from api_client import login, register, ApiError


def render(on_login):
    # Center the card on the page using columns, similar to the flexbox
    # centering in LoginPage.jsx's `styles.page`.
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown(
            "<div style='text-align:center; font-size:48px; margin-bottom:0;'>🧠</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h1 style='text-align:center; margin-bottom:0;'>DocuMind</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; color:gray;'>Ask your documents anything</p>",
            unsafe_allow_html=True,
        )

        # Tabs replace the mode-switch buttons in LoginPage.jsx
        tab_login, tab_register = st.tabs(["Sign In", "Sign Up"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        with st.spinner("Please wait..."):
                            data = login(email, password)
                        on_login(data)
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Could not reach the server: {e}")

        with tab_register:
            with st.form("register_form"):
                email = st.text_input("Email", key="register_email")
                username = st.text_input("Username", key="register_username")
                password = st.text_input("Password", type="password", key="register_password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                if not email or not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        with st.spinner("Please wait..."):
                            data = register(email, username, password)
                        on_login(data)
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Could not reach the server: {e}")
