import streamlit as st
from modules.page_auth import show_login, show_cadastro
from modules.page_admin import show_admin_page
from modules.page_user import show_user_page


def resolver_rotas(set_page):
    if not st.session_state.get('logged_in', False):
        if st.session_state.get('page') == 'login':
            show_login(set_page)
        elif st.session_state.get('page') == 'cadastro':
            show_cadastro(set_page)
    else:
        if not st.session_state['logged_in']:
            st.session_state['username'] = None
            st.session_state['role'] = None
            st.session_state['page'] = 'login'
            st.rerun()

        # Página conforme a role
        if st.session_state['role'] == 'admin':
            show_admin_page(st.session_state['username'])
        elif st.session_state['role'] == 'user':
            show_user_page(st.session_state['username'])
