import streamlit as st
import database_api as db


def show_login(set_page):
    st.subheader("🔐 Login no Sistema de Inventário")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        dados = db.check_login(username, password)

        if dados:
            st.success(f"Bem-vindo, {dados['username']}!")

            # Atualiza sessão
            st.session_state['logged_in'] = True
            st.session_state['username'] = dados['username']
            st.session_state['role'] = dados['role']

            st.rerun()
        else:
            st.error("Credenciais inválidas. Tente novamente ou cadastre-se.")
            st.session_state['username'] = ""
            st.session_state['password'] = ""
            st.rerun()
            
# 🆕 Botão para cadastro
    st.markdown("---")
    st.markdown("👤 Ainda não tem conta?")
    if st.button("➕ Criar nova conta"):
        set_page("cadastro")
