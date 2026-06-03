import streamlit as st
import database_api as db
import re

def show_recuperar_senha(set_page):
    st.title("🔑 Recuperar Senha")

    if not st.session_state.get('link_enviado', False):
        st.write("Passo 1: Digite o seu e-mail abaixo. Se houver uma conta associada, enviaremos um e-mail com um link seguro de recuperação.")
        
        email = st.text_input("E-mail para recuperação")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Voltar ao Login", use_container_width=True):
                set_page("login")
                st.rerun()
                
        with col2:
            if st.button("📧 Enviar E-mail", type="primary", use_container_width=True):
                if email:
                    db.reset_password_request(email)
                    st.session_state['link_enviado'] = True
                    st.rerun()
                else:
                    st.error("Por favor, digite um e-mail válido.")
    else:
        st.success("✅ E-mail de recuperação enviado (verifique a caixa de Spam também)!")
        st.markdown("### Passo 2: Validar Código")
        st.info("Abra o seu e-mail. **Não clique no link!** Em vez disso, clique com o botão direito no link ou botão recebido e escolha **'Copiar Link'**. Cole o link completo abaixo:")
        
        link_colado = st.text_input("Cole o link aqui:", help="Exemplo: https://seudominio.com/#access_token=abcd...")
        
        if st.button("🔑 Validar e Entrar", type="primary", use_container_width=True):
            if link_colado:
                # Extrair access_token e refresh_token via regex
                access_match = re.search(r"access_token=([^&]+)", link_colado)
                refresh_match = re.search(r"refresh_token=([^&]+)", link_colado)
                
                if access_match and refresh_match:
                    access_token = access_match.group(1)
                    refresh_token = refresh_match.group(1)
                    
                    try:
                        # Forçar o login usando os tokens do link
                        response = db.supabase.auth.set_session(access_token, refresh_token)
                        if response.user and response.session:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = db.get_username(response.user)
                            st.session_state['role'] = db.get_user_role(response.user)
                            st.session_state['uid'] = response.user.id
                            st.session_state['session'] = response.session
                            
                            # Redireciona o administrador direto para a aba de mudar senha
                            if st.session_state['role'] == 'admin':
                                st.session_state["pagina_admin"] = "🔑 Mudar Senha"
                            
                            st.session_state['link_enviado'] = False
                            st.success("Sessão validada com sucesso! Redirecionando...")
                            st.rerun()
                        else:
                            st.error("Falha ao criar sessão. O link pode estar expirado.")
                    except Exception as e:
                        st.error(f"Erro ao validar tokens: Link inválido ou expirado.")
                else:
                    st.error("Link inválido. Certifique-se de copiar o link completo do e-mail que contém o código de acesso.")
            else:
                st.warning("Por favor, cole o link primeiro.")
                
        if st.button("🔙 Cancelar e Voltar", use_container_width=True):
            st.session_state['link_enviado'] = False
            set_page("login")
            st.rerun()
