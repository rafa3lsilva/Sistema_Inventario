import streamlit as st
import database_api as db


def show_login(set_page):
    st.markdown(
        """
        <style>
            /* Centraliza o título principal (h1) */
            h1 {
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title("📦 Sistema de Inventário")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            """
            <div style="text-align: center;">
            <br>
            <h3>A forma mais fácil de gerir o seu inventário.</h3>
            <br>
            <p>Faça a contagem de produtos de forma rápida e eficiente usando a câmara do seu telemóvel.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        # Coluna da direita com o formulário
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar", type="primary", use_container_width=True):
            # 1. A variável 'response' é criada AQUI para guardar o resultado do login.
            response = db.sign_in(email, password)

            # 2. Verificamos se o login foi bem-sucedido antes de usar 'response'.
            if response and response.user and response.session:
                st.success(f"Bem-vindo, {db.get_username(response.user)}!")
                st.session_state['logged_in'] = True
                st.session_state['username'] = db.get_username(response.user)
                st.session_state['role'] = db.get_user_role(response.user)
                st.session_state['uid'] = response.user.id

                # 3. A variável 'response' é usada AQUI, de forma segura.
                st.session_state['session'] = response.session

                st.rerun()
            else:
                st.error("Email ou senha inválidos.")

        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔑 Esqueci a senha", use_container_width=True):
                set_page("recuperar_senha")
                st.rerun()
        with col_btn2:
            if st.button("➕ Criar nova conta", use_container_width=True):
                set_page("cadastro")
                st.rerun()
