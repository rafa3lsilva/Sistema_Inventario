import streamlit as st
import database_api as db

def show_mudar_senha():
    st.markdown("### 🔑 Mudar Senha")
    st.info("Digite a sua nova senha abaixo para atualizar a sua conta.")
    
    with st.form("form_mudar_senha"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
        
        submit = st.form_submit_button("Atualizar Senha", type="primary")
        
        if submit:
            if not nova_senha or len(nova_senha) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif nova_senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            else:
                res = db.update_user_password(nova_senha)
                if res is not None:
                    st.success("✅ Senha atualizada com sucesso! Você já pode usar a nova senha no próximo login.")
                else:
                    st.error("❌ Falha ao atualizar a senha. Tente novamente mais tarde.")
