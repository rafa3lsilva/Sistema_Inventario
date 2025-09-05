import streamlit as st
from datetime import datetime
import pytz

def admin_sidebar(username):
    if 'role' not in st.session_state or st.session_state['role'] != 'admin':
        st.warning("Acesso não autorizado.")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    # Título
    st.sidebar.markdown("## 📦Painel do Administrador")

    # Avatar ou ícone (personalizável)
    try:
        st.sidebar.image("assets/admin_avatar.png", width=60)
    except:
        st.sidebar.markdown("🧑‍💼")

    # 2. Definimos o fuso horário de São Paulo (que representa o horário de Brasília)
    sao_paulo_tz = pytz.timezone("America/Sao_Paulo")

    # 3. Obtemos a hora atual JÁ com o fuso horário correto
    hora_local = datetime.now(sao_paulo_tz)
    # Informações do usuário
    st.sidebar.markdown(f"""
**👋 Bem-vindo, `{username}`**

🔐 Função: `Administrador`  
🕒 Sessão: `{hora_local.strftime('%d/%m/%Y %H:%M')}`
""")

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🧭 Navegação")


    # Navegação via radio buttons (mais elegante)
    st.session_state["pagina_admin"] = st.sidebar.radio(
        label="Selecionar página",
        options=[
            "📦 Contagem de Inventário",
            "📋 Relatório de Contagens",
            "📊 Auditoria de Estoque",
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
        st.session_state['uid'] = None
        st.session_state['page'] = 'login'
