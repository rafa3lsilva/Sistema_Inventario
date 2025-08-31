import streamlit as st
import database_api as db
from modules.scanner import get_barcode


def render_contagem_interface(user_uid: str, session_state_key: str):
    """
    Função centralizada que renderiza toda a interface de contagem.
    Isto evita a duplicação de código entre as páginas de admin e de user.
    """
    st.markdown("### 📦 Identifique o produto")

    if st.button("📷 Ativar Leitor de Código de Barras", key=f"btn_scan_{session_state_key}"):
        st.session_state[f'scanner_active_{session_state_key}'] = True

    if st.session_state.get(f'scanner_active_{session_state_key}', False):
        ean_lido = get_barcode()

        if st.button("✖️ Cancelar Leitura", key=f"btn_cancel_{session_state_key}"):
            st.session_state[f'scanner_active_{session_state_key}'] = False
            st.rerun()

        if ean_lido:
            st.session_state[session_state_key] = ean_lido
            st.session_state[f'scanner_active_{session_state_key}'] = False
            st.rerun()

    ean = st.text_input(
        "Código de barras",
        key=session_state_key,
        help="Pode digitar o código ou usar o leitor."
    )

    if "success_message" in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message

    if ean:
        produto = db.get_product_info(ean)

        if produto:
            st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")

            with st.container():
                st.markdown("### 🧮 Registrar contagem")
                with st.form(f"form_contagem_{session_state_key}"):
                    quantidade = st.number_input(
                        "Quantidade contada", min_value=1, step=1)
                    contar = st.form_submit_button("Registrar")
                    if contar:
                        db.add_or_update_count(user_uid, ean, quantidade)
                        st.session_state.success_message = f"📊 Contagem de {quantidade} para '{produto['descricao']}' registrada!"
                        st.session_state.count_successful = True
                        st.rerun()
        else:
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Cadastrar novo produto")

            embs = db.get_all_embs() or ["PCT", "KG", "UN"]
            secoes = db.get_all_secoes() or ["MERCEARIA", "Açougue"]
            grupos = db.get_all_grupos() or ["Frutas", "Carnes"]

            with st.form(f"form_cadastro_{session_state_key}"):
                descricao = st.text_input("Descrição do produto")
                emb = st.selectbox("Embalagem", embs)
                secao = st.selectbox("Seção", secoes)
                grupo = st.selectbox("Grupo", grupos)
                cadastrar = st.form_submit_button("Cadastrar")
                if cadastrar and descricao:
                    db.add_product(ean, descricao, emb, secao, grupo)
                    st.session_state.success_message = f"✅ Produto '{descricao}' cadastrado com sucesso!"
                    st.session_state.count_successful = True
                    st.rerun()
