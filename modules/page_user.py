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
    st.markdown(
        f"""
        <div style="background-color:#004B8D; padding:10px; border-radius:8px;">
            <h2 style='color:white; margin-bottom:0;'>👋 Bem-vindo, {username}</h2>
            <p style='color:white; margin-top:0;'>Sistema de Contagem de Inventário</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.button("🚪 Sair", on_click=fazer_logout)
    st.markdown("---")

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
            # Etapa 2: Cadastrar Novo Produto
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Cadastrar novo produto")
            df_produtos = db.get_all_products_df()
            embs = (sorted(df_produtos["emb"].dropna().unique(
            )) if "emb" in df_produtos.columns else ["PCT", "KG", "UN", "CX", "SC", "L", "LT"])
            secoes = (sorted(df_produtos["secao"].dropna().unique(
            )) if "secao" in df_produtos.columns else ["MERCEARIA", "Açougue", "Padaria"])
            grupos = (sorted(df_produtos["grupo"].dropna().unique(
            )) if "grupo" in df_produtos.columns else ["Frutas", "Carnes", "Frios"])

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
