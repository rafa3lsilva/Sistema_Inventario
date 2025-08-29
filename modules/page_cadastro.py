import streamlit as st
import database_api as db


def show_cadastro(set_page):
    st.subheader("📝 Criar nova conta")
    email = st.text_input("Email")
    username = st.text_input("Nome de usuário (para exibição)")
    password = st.text_input("Senha", type="password")

    if st.button("➕ Criar conta"):
        if not email or not password or not username:
            st.error("Preencha todos os campos.")
        else:
            res = db.sign_up(email, password, username, 'user')
            if isinstance(res, Exception):
                st.error(f"Erro no cadastro: {res}")
            elif res and res.user:
                st.success("Conta criada! Por favor, faça o login.")
                st.info(
                    "✉️ Por favor, verifique a sua caixa de entrada (e spam) " \
                    "para ativar a sua conta antes de fazer o login.")
                set_page("login")
            else:
                st.error(
                    "Não foi possível criar a conta. O email pode já estar em uso.")

    st.button("🔙 Voltar para o Login", on_click=set_page, args=("login",))
