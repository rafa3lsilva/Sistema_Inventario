import streamlit as st
import database_api as db
from modules.scanner import mostrar_scanner_ean
from database_api import add_product, add_or_update_count, produto_existe


def registrar_contagem(username, role="user"):
    st.caption(f"Perfil: {role.capitalize()} — Usuário: {username}")
    st.subheader("🔢 Registrar Contagem com Leitor de Código de Barras")

    mostrar_scanner_ean(largura="90%", altura=320, tempo_limite=15)

    ean = st.text_input("Código de barras (EAN)")

    # ✅ Verifica se o EAN é válido antes de mostrar o restante
    if ean and len(ean) >= 8 and len(ean) <= 13 and ean.isdigit():
        produto_ja_existe = produto_existe(ean)

        if not produto_ja_existe:
            st.info("Produto não encontrado. Preencha os dados para cadastro:")
            descricao = st.text_input("Descrição do produto")
            emb = st.text_input("Tipo de embalagem")
            secao = st.selectbox(
                "Seção", ["Hortifruti", "Limpeza", "Bebidas", "Laticínios", "Outros"])
            grupo = st.selectbox(
                "Grupo", ["Perecível", "Não Perecível", "Importado", "Promoção", "Outros"])
        else:
            descricao, emb, secao, grupo = None, None, None, None
            st.success("✅ Produto cadastrado. Você pode seguir para contagem.")

        quantidade = st.number_input("Quantidade contada", min_value=1)

        if st.button("📦 Confirmar contagem"):
            if not produto_ja_existe and not descricao:
                st.warning("Preencha os dados do novo produto.")
                return

            if not produto_ja_existe:
                add_product(ean, descricao, emb, secao, grupo)
                st.success(f"Produto '{descricao}' cadastrado com sucesso ✅")

            username = st.session_state.get("username")
            if not username:
                st.error("Usuário não identificado.")
                return

            add_or_update_count(username, ean, quantidade)
            st.success(f"Contagem registrada para EAN {ean} ✅")
