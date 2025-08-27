import streamlit as st
import database_api as db


def show_login(set_page):
    st.subheader("🔐 Login no Sistema de Inventário")
    email = st.text_input("Email")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        user = db.sign_in(email, password)
        if user:
            st.success(f"Bem-vindo, {db.get_username(user)}!")
            st.session_state['logged_in'] = True
            st.session_state['username'] = db.get_username(user)
            st.session_state['role'] = db.get_user_role(user)
            st.session_state['uid'] = user.id
            st.rerun()
        else:
            st.error("Email ou senha inválidos.")

    st.markdown("---")
    st.markdown("👤 Ainda não tem conta?")
    if st.button("➕ Criar nova conta"):
        set_page("cadastro")
