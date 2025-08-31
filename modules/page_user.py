import streamlit as st
import database_api as db
from modules.scanner import get_barcode
from modules.contagem_utils import render_contagem_interface


def fazer_logout():
    st.session_state.clear()
    st.session_state['page'] = 'login'


def show_user_page(username, user_uid):
    if st.session_state.get("count_successful", False):
        st.session_state.ean_digitado_user = ""
        st.session_state.count_successful = False

    # --- Cabeçalho e Logout ---
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            """
            <div style="background-color:#004B8D; padding:12px 20px; border-radius:8px 8px 8px 8px;">
                <h2 style="color:white; margin:0; text-align:center;">📊 Sistema de Contagem de Inventário</h2>
                <p style="color:#d9e6f2; margin:0; font-size:0.9em;text-align:center;">Controle rápido, preciso e sem complicação</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown("\n")
        st.button("🚪 Sair", on_click=fazer_logout)

    render_contagem_interface(user_uid, "ean_digitado_user")
