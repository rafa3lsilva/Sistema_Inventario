import streamlit as st
import database_api as db
from modules.scanner import get_barcode


def fazer_logout():
    """Reinicia o estado da sessão para o logout de forma segura."""
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
    st.session_state['uid'] = None 
    st.session_state['page'] = 'login'


# A função agora recebe o uid
def show_user_page(username, user_uid):
    if st.session_state.get("count_successful", False):
        st.session_state.ean_digitado_user = ""
        st.session_state.count_successful = False

    st.markdown(
        f"""
        <div style="background-color:#004B8D; padding:10px; border-radius:8px;">
            <h2 style='color:white; margin-bottom:0;'>👋 Bem-vindo, {username}</h2>
            <p style='color:white; margin-top:0;'>Sistema de Contagem de Inventário</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("")
    st.button("🚪 Sair", on_click=fazer_logout)
    st.markdown("---")

    st.markdown("### 📦 Etapa 1: Identifique o produto")

    # --- LÓGICA DO SCANNER ATUALIZADA ---
    st.write("Aponte a câmera para o código de barras.")
    # Botão para ativar a câmera
    if st.button("📷 Ativar Leitor de Código de Barras"):
        st.session_state.scanner_active = True

    # O scanner só é mostrado se o estado for ativo
    if st.session_state.get("scanner_active", False):
        st.write("Aponte a câmera para o código de barras...")
        ean_lido = get_barcode()

        if st.button("✖️ Cancelar Leitura"):
            st.session_state.scanner_active = False
            st.rerun()

        if ean_lido:
            st.session_state.ean_digitado_user = ean_lido
            st.session_state.scanner_active = False
            st.rerun()

    ean = st.text_input(
        "Código de barras",
        key="ean_digitado_user",
        help="Pode digitar o código ou usar o leitor."
    )

    produto = None
    if ean:
        produto = db.get_product_info(ean)

        if produto:
            st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")
        else:
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Etapa 2: Cadastrar novo produto")

            df_produtos = db.get_all_products_df()
            embs = (
                sorted(df_produtos["emb"].dropna().unique())
                if "emb" in df_produtos.columns else ["PCT", "KG", "UN", "CX", "SC", "L", "LT"]
            )
            secoes = (
                sorted(df_produtos["secao"].dropna().unique())
                if "secao" in df_produtos.columns else ["MERCEARIA", "Açougue", "Padaria"]
            )
            grupos = (
                sorted(df_produtos["grupo"].dropna().unique())
                if "grupo" in df_produtos.columns else ["Frutas", "Carnes", "Frios"]
            )

            with st.form("form_cadastro_produto_user"):
                descricao = st.text_input("Descrição do produto")
                emb = st.selectbox("Embalagem", embs)
                secao = st.selectbox("Seção", secoes)
                grupo = st.selectbox("Grupo", grupos)
                cadastrar = st.form_submit_button("Cadastrar")

                if cadastrar and descricao:
                    try:
                        db.add_product(ean, descricao, emb, secao, grupo)
                        st.success("✅ Produto cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar produto: {e}")

    if produto:
        with st.container():
            st.markdown("### 🧮 Etapa 3: Registrar contagem")

            with st.form("form_contagem_user"):
                quantidade = st.number_input(
                    "Quantidade contada", min_value=1, step=1)
                contar = st.form_submit_button("Registrar")
                if contar:
                    db.add_or_update_count(user_uid, ean, quantidade)
                    st.success("📊 Contagem registrada com sucesso!")
                    st.session_state.count_successful = True
                    st.rerun()
