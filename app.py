import streamlit as st
import pandas as pd
import hashlib
from database import (
    check_login, create_user, get_all_users,
    get_all_produtos, add_or_update_produto,
    get_all_contagens, add_or_update_contagem
)

st.set_page_config(page_title="Sistema de Inventário", layout="centered")
st.title("📦 Sistema de Inventário com Supabase")

# Utilitário para gerar hash de senha


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Controle de sessão
if "usuario" not in st.session_state:
    st.session_state.usuario = None

# TELA DE LOGIN
if not st.session_state.usuario:
    aba = st.sidebar.radio("Opções", ["Login", "Cadastrar"])

    if aba == "Login":
        st.subheader("🔐 Login")
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            user = check_login(username, hash_password(password))
            if user:
                st.session_state.usuario = user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    elif aba == "Cadastrar":
        st.subheader("👤 Criar Conta")
        new_user = st.text_input("Novo usuário")
        new_pass = st.text_input("Senha", type="password")

        if st.button("Cadastrar"):
            success = create_user(new_user, hash_password(new_pass))
            if success:
                st.success("Usuário criado com sucesso!")
            else:
                st.error("Usuário já existe.")

    st.stop()

# TELA PRINCIPAL
user = st.session_state.usuario
st.sidebar.success(f"Logado como: {user['username']} ({user['role']})")
if st.sidebar.button("Sair"):
    st.session_state.usuario = None
    st.rerun()

aba = st.sidebar.radio("Menu", ["Contagem", "Produtos", "Admin"]
                       if user['role'] == 'admin' else ["Contagem", "Produtos"])

if aba == "Contagem":
    st.subheader("🧮 Registrar Contagem")
    ean = st.text_input("Código de Barras (EAN)")
    qtd = st.number_input("Quantidade", step=1, min_value=1)

    if st.button("Registrar"):
        if ean and qtd:
            add_or_update_contagem(user['username'], ean, qtd)
            st.success("Contagem registrada!")

    st.subheader("📋 Suas contagens")
    df = get_all_contagens()
    df_user = df[df['username'] == user['username']]
    st.dataframe(df_user)

elif aba == "Produtos":
    st.subheader("📦 Lista de Produtos")
    produtos = get_all_produtos()
    st.dataframe(produtos)

    if user['role'] == 'admin':
        st.subheader("➕ Adicionar ou Atualizar Produto")
        ean_add = st.text_input("Novo EAN")
        desc_add = st.text_input("Descrição")

        if st.button("Salvar Produto"):
            if ean_add and desc_add:
                add_or_update_produto(ean_add, desc_add)
                st.success("Produto salvo com sucesso!")

elif aba == "Admin":
    st.subheader("👥 Todos os Usuários")
    users = get_all_users()
    st.table(users)

    st.subheader("📤 Importar Produtos via CSV")
    uploaded = st.file_uploader(
        "CSV com colunas [ean, descricao]", type=["csv"])
    if uploaded:
        df_csv = pd.read_csv(uploaded)
        st.write(df_csv)
        for _, row in df_csv.iterrows():
            add_or_update_produto(row['ean'], row['descricao'])
        st.success("Produtos importados/atualizados!")
