import streamlit as st
import database_api as db
from modules.page_admin import show_admin_page
from modules.page_login import show_login
from modules.page_user import show_user_page
from modules.page_cadastro import show_cadastro
from modules.page_recuperar_senha import show_recuperar_senha


# 🧭 Configurações iniciais
st.set_page_config(
    page_title="Sistema de Inventário",
    page_icon="📦",
    initial_sidebar_state="expanded"
)

# 🔧 Definir função de navegação
def set_page(page):
    st.session_state['page'] = page

# 🔐 Inicialização do estado de sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
    st.session_state['uid'] = None
    st.session_state.original_contagens = None

# 🟢 AQUI: restaurar sessão se já existir e o usuário estiver logado
if st.session_state.get('logged_in') and st.session_state.get('session'):
    try:
        session_info = st.session_state['session']
        # Renova o token se necessário
        db.supabase.auth.set_session(
            session_info.access_token, session_info.refresh_token
        )
    except Exception:
        # Se falhar (ex: refresh_token expirou), limpa o estado
        st.session_state.clear()
        st.session_state['logged_in'] = False

# Se não houver página definida, volta para login
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'


# --- FLUXO DE LOGIN E CADASTRO ---
if not st.session_state['logged_in']:
    if st.session_state['page'] == 'login':
        show_login(set_page)

    elif st.session_state['page'] == 'cadastro':
        show_cadastro(set_page)

    elif st.session_state['page'] == 'recuperar_senha':
        show_recuperar_senha(set_page)

# --- APLICAÇÃO PRINCIPAL (APÓS LOGIN) ---
else:
    # Exibe página conforme o papel do usuário
    if st.session_state['role'] == 'admin':
        # Passamos o uid para a página do admin
        show_admin_page(st.session_state['username'], st.session_state['uid'])

    elif st.session_state['role'] == 'user':
        # Passamos o uid para a página do usuário
        show_user_page(st.session_state['username'], st.session_state['uid'])
