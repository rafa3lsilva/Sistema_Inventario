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

            /* --- MUDANÇA PRINCIPAL AQUI --- */
            /* Regra de CSS para ecrãs com largura máxima de 1024px (telemóveis e tablets) */
            @media (max-width: 1024px) {
                /* Esconde os elementos com a classe 'desktop-only' */
                .desktop-only {
                    display: none;
                }
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title("📦 Sistema de Inventário")
    col1, col2 = st.columns(2, gap="large")
    st.markdown('<div class="desktop-only">', unsafe_allow_html=True)
    with col1:
        img_col1, img_col2, img_col3 = st.columns([1, 4, 1])
        with img_col2:
            st.image("assets/admin_avatar.png", width=200)

        st.markdown(
            """
            <div style="text-align: center;">
            <h3>A forma mais fácil de gerir o seu inventário.</h3>
            <p>Faça a contagem de produtos de forma rápida e eficiente usando a câmara do seu telemóvel.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        #st.subheader("Aceda à sua conta")
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar", type="primary", use_container_width=True):
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
        st.write("Ainda não tem conta?")
        if st.button("➕ Criar nova conta"):
            set_page("cadastro")
