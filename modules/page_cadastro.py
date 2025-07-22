import streamlit as st
import database_api as db
import re


def show_cadastro(set_page):
    st.subheader("📝 Criar nova conta")

    # Verifica se já existe um administrador no banco
    admin_existe = db.has_admin()  # ✅ função que retorna True/False

    # 🔤 Inputs
    username = st.text_input("Nome de usuário")
    password = st.text_input("Senha", type="password")
    confirm_password = st.text_input("Confirmar senha", type="password")

    # Sugere apenas tipo "user" se já houver admin
    if admin_existe:
        role_options = ["user"]
        st.info(
            "👤 Já existe um administrador cadastrado. Só é possível criar usuários comuns.")
    else:
        role_options = ["user", "admin"]

    role = st.selectbox("Tipo de acesso", role_options)

    # 🔎 Avaliação da força da senha (visual)
    def avaliar_forca_senha(senha):
        if len(senha) < 6:
            return "❌ Fraca: menos de 6 caracteres"
        elif not re.search(r"[A-Z]", senha):
            return "⚠️ Média: sem letra maiúscula"
        elif not re.search(r"[0-9]", senha):
            return "⚠️ Média: sem números"
        elif not re.search(r"[@$!%*#?&]", senha):
            return "⚠️ Média: sem símbolos especiais"
        else:
            return "✅ Forte"

    if password:
        st.markdown(f"**Força da senha:** {avaliar_forca_senha(password)}")

    # 🔐 Botão de cadastro
    if st.button("➕ Criar conta"):
        # 🚧 Validações
        if not username or not password or not confirm_password:
            st.error("Preencha todos os campos.")
            return

        if password != confirm_password:
            st.warning("As senhas não coincidem.")
            return

        if len(password) < 6:
            st.warning("A senha precisa ter pelo menos 6 caracteres.")
            return

        if username.lower() in ["admin", "root", "master"]:
            st.error("Este nome de usuário é reservado. Escolha outro.")
            return

        criado = db.create_user(username, password, role)
        if criado:
            st.success(f"Conta criada com sucesso para '{username}'!")
            set_page("login")
            st.rerun()
        else:
            st.error("Este nome de usuário já está em uso.")

    st.button("🔙 Voltar para o Login", on_click=set_page, args=("login",))
