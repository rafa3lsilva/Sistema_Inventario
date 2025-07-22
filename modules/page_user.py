import streamlit as st
import database_api as db
import modules.scanner as scanner


def show_user_page(username):
    # 🔷 Cabeçalho personalizado com tema logístico
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

    # 🔘 Botão de logout
    st.button("🚪 Sair", on_click=lambda: st.session_state.clear())

    st.markdown("---")

    # 📦 Card de contagem
    with st.container():
        st.markdown("### 📦 Etapa 1: Identifique o produto")

        col1, col2 = st.columns([3, 1])
        with col1:
            ean = st.text_input("Código de barras", key="ean_input_user")
        with col2:
            if st.button("📷", key="btn_scan_user"):
                scanner.mostrar_scanner_ean(altura=300, tempo_limite=10)

        produto = None
        if ean:
            produto = db.get_product_info(ean)

            if produto:
                st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")

            else:
                st.warning("⚠️ Produto não cadastrado.")
                st.markdown("### 🆕 Etapa 2: Cadastrar novo produto")

                # 🔄 Listas suspensas para campos padronizados
                df_produtos = db.get_all_products_df()
                embs = sorted(df_produtos["emb"].dropna().unique()) or [
                    "Pacote", "Bandeja", "Unidade"]
                secoes = sorted(df_produtos["secao"].dropna().unique()) or [
                    "Hortifruti", "Açougue", "Padaria"]
                grupos = sorted(df_produtos["grupo"].dropna().unique()) or [
                    "Frutas", "Carnes", "Frios"]

                with st.form("form_cadastro_produto_admin"):
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
                    db.add_or_update_count(username, ean, quantidade)
                    st.success("📊 Contagem registrada com sucesso!")
                    st.rerun()
