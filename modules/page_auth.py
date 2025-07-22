import streamlit as st
from database_api import check_login, create_user


def show_login(set_page):
    st.title("🔐 Login")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        dados = check_login(username, password)
        if dados:
            st.session_state['logged_in'] = True
            st.session_state['username'] = dados['username']
            st.session_state['role'] = dados['role']
        else:
            st.error("Credenciais inválidas")

    if st.button("Criar nova conta"):
        set_page("cadastro")


def show_cadastro(set_page):
    st.title("📝 Cadastro")

    novo_usuario = st.text_input("Novo usuário")
    nova_senha = st.text_input("Nova senha", type="password")

    if st.button("Cadastrar"):
        if not novo_usuario or not nova_senha:
            st.warning("Preencha todos os campos.")
        else:
            criado = create_user(novo_usuario, nova_senha, "user")
            if criado:
                st.success("Conta criada com sucesso!")
                set_page("login")
            else:
                st.error("Usuário já existe.")
