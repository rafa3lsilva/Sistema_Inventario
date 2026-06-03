import streamlit as st
import pandas as pd
import database_api as db
from modules.scanner import get_barcode, get_barcode_from_image


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
    
    st.markdown("---")
    st.markdown("### 🧾 Identificar produto")

    tipo_leitura = st.radio("Escolha o método de leitura da câmera:", 
                            ["📹 Leitor ao Vivo (Android/PC)", "📸 Tirar Foto (Ideal para iPhone)"], 
                            horizontal=True)

    if st.button("📷 Ativar Câmera / Leitor"):
        st.session_state.scanner_active = True

    # O scanner só é mostrado se o estado for ativo
    if st.session_state.get("scanner_active", False):
        ean_lido = None
        if "Tirar Foto" in tipo_leitura:
            st.info("Tire uma foto bem nítida e focada do código de barras.")
            foto = st.camera_input("Foto do Código")
            if foto:
                ean_lido = get_barcode_from_image(foto)
                if not ean_lido:
                    st.error("❌ Não foi possível ler o código na foto. Tente novamente com mais foco e iluminação.")
        else:
            st.write("Aponte a câmera para o código de barras...")
            ean_lido = get_barcode()

        # --- NOVO BOTÃO DE CANCELAR ---
        if st.button("✖️ Cancelar Câmera"):
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

    # ✅ Mensagem de sucesso logo após o campo de EAN
    if "count_message" in st.session_state:
        st.success(st.session_state.count_message)
        del st.session_state.count_message

    produto = None
    if ean:
        ean = ean.strip()
        ean = db.sanitizar_ean(ean)
        produto = db.get_product_info(ean)
        if produto:
            st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")
        else:
            # Se o produto NÃO EXISTE, mostramos o formulário de cadastro
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Cadastrar novo produto")

            # Usamos as novas funções otimizadas para buscar as opções
            embs = db.get_all_embs() or ["PCT", "KG", "UN"]
            secoes = db.get_all_secoes() or ["MERCEARIA", "Açougue"]
            grupos = db.get_all_grupos() or ["Frutas", "Carnes"]

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
        st.markdown("### 📦 Registrar contagem")
        # --- Ajuste automático de step e formato ---
        emb = produto.get("emb", "").upper() if produto else ""
        if emb in ["KG", "L", "GR", "ML"]:
            min_val = 0.0
            step = 0.001
            fmt = "%.3f"
        else:
            min_val = 0
            step = 1
            fmt = "%d"

        with st.form("form_contagem_user"):
            quantidade = st.number_input(
                "Quantidade contada",
                min_value=min_val,
                step=step,
                format=fmt
            )

            contar = st.form_submit_button("Registrar")
            if contar:
                try:
                    db.add_or_update_count(user_uid, ean, quantidade)
                    st.session_state.count_message = f"📊 Contagem de {quantidade} para '{produto['descricao']}' registrada!"
                    st.session_state.count_successful = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao registrar contagem: {e}")
    
    with st.expander("Ver minhas contagens registadas"):
        # 1. Chamamos a nossa nova função, passando o UID do utilizador logado
        minhas_contagens = db.get_contagens_por_usuario(user_uid)

        if not minhas_contagens:
            st.info("Você ainda não registou nenhuma contagem.")
        else:
            # 2. Processamos os dados para uma exibição amigável
            dados_para_tabela = []
            for contagem in minhas_contagens:
                # O produto vem "aninhado", então precisamos de o extrair
                produto = contagem.get('produtos', {})
                if produto:  # Garante que o produto não é nulo
                    dados_para_tabela.append({
                        "EAN": produto.get('ean', 'N/A'),
                        "Descrição": produto.get('descricao', 'N/A'),
                        "Quantidade": contagem.get('quantidade', 0)
                    })

            # 3. Exibimos a tabela
            df_minhas_contagens = pd.DataFrame(dados_para_tabela)
            st.dataframe(df_minhas_contagens,
                         use_container_width=True, hide_index=True)

    st.markdown("---")
    with st.expander("⚙️ Configurações de Conta (Mudar Senha)"):
        from modules.page_mudar_senha import show_mudar_senha
        show_mudar_senha()
