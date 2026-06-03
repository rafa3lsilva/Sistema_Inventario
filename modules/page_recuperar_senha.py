import streamlit as st
import database_api as db

def show_recuperar_senha(set_page):
    st.title("🔑 Recuperar Senha")
    st.write("Digite o seu e-mail abaixo. Se houver uma conta associada a ele, enviaremos um link mágico para você entrar e redefinir sua senha.")
    
    email = st.text_input("E-mail para recuperação")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔙 Voltar ao Login", use_container_width=True):
            set_page("login")
            st.rerun()
            
    with col2:
        if st.button("📧 Enviar Link de Recuperação", type="primary", use_container_width=True):
            if email:
                db.reset_password_request(email)
                st.success("✅ Se este e-mail estiver cadastrado, você receberá um link de recuperação em instantes.")
                st.info("Abra o e-mail, clique no link mágico para entrar na sua conta e, em seguida, procure a opção 'Mudar Senha' no sistema.")
            else:
                st.error("Por favor, digite um e-mail válido.")
