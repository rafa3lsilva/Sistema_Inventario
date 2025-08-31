import streamlit as st
import database_api as db
from modules.scanner import get_barcode


def fazer_logout():
    st.session_state.clear()
    st.session_state['page'] = 'login'


def show_user_page(username, user_uid):
    if st.session_state.get("count_successful", False):
        st.session_state.ean_digitado_user = ""
        st.session_state.count_successful = False

    # --- Cabeçalho e Logout ---
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            """
            <div style="background-color:#004B8D; padding:12px 20px; border-radius:8px 8px 8px 8px;">
                <h2 style="color:white; margin:0; text-align:center;">📊 Sistema de Contagem de Inventário</h2>
                <p style="color:#d9e6f2; margin:0; font-size:0.9em;text-align:center;">Controle rápido, preciso e sem complicação</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown("\n")
        st.button("🚪 Sair", on_click=fazer_logout)

    # --- Etapa 1: Identificar o Produto ---
    st.markdown("### 📦 Identifique o produto")

    if st.button("📷 Ativar Leitor de Código de Barras"):
        st.session_state.scanner_active = True
        if "count_message" in st.session_state:
            del st.session_state.count_message

    if st.session_state.get("scanner_active", False):
        ean_lido = get_barcode()

        if st.button("✖️ Cancelar Leitura"):
            st.session_state.scanner_active = False
            st.rerun()

        if ean_lido:
            st.session_state.ean_digitado_user = ean_lido
            st.session_state.scanner_active = False
            if "count_message" in st.session_state:
                del st.session_state.count_message
            st.rerun()

    ean = st.text_input(
        "Código de barras",
        key="ean_digitado_user",
        help="Pode digitar o código ou usar o leitor."
    )

    # ✅ Mensagem de sucesso logo após o campo de EAN
    if "count_message" in st.session_state:
        st.success(st.session_state.count_message)
        del st.session_state.count_message
        
    # --- Lógica Principal da Página ---
    if ean:
        produto = db.get_product_info(ean)

        if produto:
            st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")

            # Etapa 2: Registrar Contagem
            with st.container():
                st.markdown("### 🧮 Registrar contagem")
                with st.form("form_contagem_user"):
                    quantidade = st.number_input(
                        "Quantidade contada", min_value=1, step=1)
                    contar = st.form_submit_button("Registrar")
                    if contar:
                        db.add_or_update_count(user_uid, ean, quantidade)
                        st.session_state.count_message = f"📊 Contagem de {quantidade} para '{produto['descricao']}' registrada!"
                        st.session_state.count_successful = True
                        st.rerun()
        
        else:
            # Se o produto NÃO EXISTE, mostramos o formulário de cadastro
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Cadastrar novo produto")

            # Usamos as novas funções otimizadas para buscar as opções
            embs = db.get_all_embs() or ["PCT", "KG", "UN"]
            secoes = db.get_all_secoes() or ["MERCEARIA", "Açougue"]
            grupos = db.get_all_grupos() or ["Frutas", "Carnes"]


            with st.form("form_cadastro_produto_user"):
                descricao = st.text_input("Descrição do produto")
                emb = st.selectbox("Embalagem", embs)
                secao = st.selectbox("Seção", secoes)
                grupo = st.selectbox("Grupo", grupos)
                cadastrar = st.form_submit_button("Cadastrar")
                if cadastrar and descricao:
                    db.add_product(ean, descricao, emb, secao, grupo)
                    st.session_state.success_message = f"✅ Produto '{descricao}' cadastrado com sucesso!"
                    st.session_state.count_successful = True  # Para limpar o campo EAN
                    st.rerun()
