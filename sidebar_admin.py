import streamlit as st
from datetime import datetime
from PIL import Image
from database_api import get_all_users

def admin_sidebar(username):
    user_list = get_all_users()
    total_usuarios = len(user_list)

def admin_sidebar(username):
    # Título
    st.sidebar.markdown("## 📦Painel do Administrador")

    # Avatar ou ícone (personalizável)
    try:
        st.sidebar.image("assets/admin_avatar.png", width=60)
    except:
        st.sidebar.markdown("🧑‍💼")

    # Informações do usuário
    st.sidebar.markdown(f"""
**👋 Bem-vindo, `{username}`**

🔐 Função: `Administrador`  
🕒 Sessão: `{datetime.now().strftime('%d/%m/%Y %H:%M')}`
""")

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🧭 Navegação")


    # Navegação via radio buttons (mais elegante)
    st.session_state["pagina_admin"] = st.sidebar.radio(
        label="Selecionar página",
        options=[
            "📦 Contagem de Inventário",
            "📋 Relatório de Contagens",
            "📤 Atualizar Produtos",
            "👥 Gerenciar Usuários"
        ]
    )

    st.sidebar.markdown("---")

    # Botão de logout com estilo
    if st.sidebar.button("🚪 Sair da conta"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['role'] = None
        st.session_state['page'] = 'login'
        st.rerun()
