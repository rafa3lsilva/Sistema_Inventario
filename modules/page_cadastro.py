import streamlit as st
import database_api as db
import re

# 🔎 Validação simples de email
def email_valido(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# 🔐 Avaliação da força da senha
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

# 📝 Página de cadastro
def show_cadastro(set_page):
    st.subheader("📝 Criar nova conta")

    with st.form("cadastro_form"):
        email = st.text_input("Email")
        username = st.text_input("Nome de usuário (para exibição)")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar senha", type="password")

        if password:
            st.markdown(f"**Força da senha:** {avaliar_forca_senha(password)}")

        submitted = st.form_submit_button("➕ Criar conta")

        if submitted:
            if not email or not username or not password:
                st.error("Preencha todos os campos.")
            elif not email_valido(email):
                st.error("Email inválido! Exemplo: usuario@exemplo.com")
            elif password != confirm_password:
                st.error("As senhas não coincidem! Tente novamente.")
            elif len(password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                res = db.sign_up(email, password, username, 'user')
                if isinstance(res, Exception):
                    st.error(
                        "Erro inesperado no cadastro. Tente novamente mais tarde.")
                elif res and res.user:
                    st.success("Conta criada com sucesso! 🎉")
                    st.info(
                        "✉️ Verifique seu email para ativar a conta antes de fazer login.")
                    set_page("login")
                else:
                    st.error(
                        "Não foi possível criar a conta. O email pode já estar em uso.")

    st.button("🔙 Voltar para o Login", on_click=set_page, args=("login",))
