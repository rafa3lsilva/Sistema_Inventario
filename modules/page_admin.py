import streamlit as st
import pandas as pd
import database_api as db
import sidebar_admin as sb
from modules.scanner import barcode_scanner_component


# A função agora recebe o uid
def show_admin_page(username: str, user_uid: str):
    if 'role' not in st.session_state or st.session_state['role'] != 'admin':
        st.warning("Acesso não autorizado.")
        st.session_state['page'] = 'login'
        st.rerun()
        return

    sb.admin_sidebar(username)
    if "pagina_admin" not in st.session_state:
        st.session_state["pagina_admin"] = "📦 Contagem de Inventário"

    pagina = st.session_state["pagina_admin"]

    if pagina == "📦 Contagem de Inventário":
        exibir_aba_contagem(user_uid)

    elif pagina == "📋 Relatório de Contagens":
        exibir_aba_relatorio()

    elif pagina == "📤 Atualizar Produtos":
        exibir_aba_csv()

    elif pagina == "👥 Gerenciar Usuários":
        exibir_aba_usuarios(username)


# A função da aba agora recebe o uid
def exibir_aba_contagem(user_uid: str):
    st.subheader("🛠️ Contagem de Inventário - Administrador")
    st.markdown("### 🧾 Etapa 1: Identificar produto")

    if st.session_state.get('show_scanner_user', False):
        st.markdown("#### Aponte a câmera para o código de barras")
        ean_lido = barcode_scanner_component()
        if st.button("Cancelar Leitura"):
            st.session_state['show_scanner_user'] = False
            st.rerun()
        if ean_lido:
            st.session_state['ean_digitado_user'] = ean_lido
            st.session_state['show_scanner_user'] = False
            st.rerun()
    else:
        if st.button("📷 Ler código de barras"):
            st.session_state['show_scanner_user'] = True
            st.rerun()

    ean = st.text_input(
        "Código de barras",
        key="ean_digitado_user",
        help="Pode digitar o código ou usar o leitor."
    )

    produto = None
    if ean:
        ean = ean.strip()
        ean = db.sanitizar_ean(ean)
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
        st.markdown("### 📦 Etapa 3: Registrar contagem")
        with st.form("form_contagem_admin"):
            quantidade = st.number_input(
                "Quantidade contada", min_value=1, step=1)
            contar = st.form_submit_button("Registrar")
            if contar:
                try:
                    db.add_or_update_count(user_uid, ean, quantidade)
                    st.success("📊 Contagem registrada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao registrar contagem: {e}")

# O resto do ficheiro (aba_relatorio, aba_csv, aba_usuarios) continua igual
# 📋 Aba 1 — Relatório de contagens
def exibir_aba_relatorio():
    st.subheader("📋 Relatório de Contagens")

    resultado = db.get_all_contagens_detalhado()
    contagens = pd.DataFrame(resultado.data)

    if contagens.empty:
        st.info("Nenhuma contagem registrada ainda.")
        return

    colunas = contagens.columns
    if "secao" in colunas and "grupo" in colunas:
        filtro_secao = st.selectbox(
            "Filtrar por seção", contagens["secao"].unique())
        filtro_grupo = st.selectbox(
            "Filtrar por grupo", contagens["grupo"].unique())

        filtro = contagens[
            (contagens["secao"] == filtro_secao) &
            (contagens["grupo"] == filtro_grupo)
        ]

        st.dataframe(filtro)

        st.download_button(
            label="📥 Exportar como CSV",
            data=filtro.to_csv(index=False).encode("utf-8"),
            file_name="relatorio_contagens.csv",
            mime="text/csv"
        )
    else:
        st.warning("Dados de 'secao' e 'grupo' não estão disponíveis no momento.")


# 📤 Aba 2 — Atualização via CSV
def exibir_aba_csv():
    st.subheader("📤 Upload de Arquivo de Produtos")

    arquivo = st.file_uploader(
        "Selecione um arquivo com colunas [ean, descricao, emb, secao, grupo]",
        type=["csv", "xlsx", "xls"]
    )

    if not arquivo:
        return

    try:
        if arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)

        df.columns = [col.lower().strip() for col in df.columns]

        colunas_esperadas = ['ean', 'descricao', 'emb', 'secao', 'grupo']
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]

        if colunas_faltando:
            st.error(
                f"⚠️ Arquivo incompleto. Faltando: {', '.join(colunas_faltando)}")
            return

        st.success("✅ Arquivo carregado com sucesso!")
        st.dataframe(df)

        diffs = db.comparar_produtos_com_banco(df)

        if not diffs["novos"].empty:
            st.warning("📦 Produtos no arquivo que não estão no banco:")
            st.dataframe(diffs["novos"])

        if not diffs["ausentes"].empty:
            st.info("📍 Produtos no banco que não estão no arquivo:")
            st.dataframe(diffs["ausentes"])

        if not diffs["divergentes"].empty:
            st.error("🔄 Produtos com diferenças entre arquivo e banco:")
            st.dataframe(diffs["divergentes"])

        st.markdown("### 🛠️ Como deseja atualizar o banco?")
        opcao = st.radio(
            "Selecione:",
            [
                "📦 Inserir apenas novos produtos",
                "🔁 Atualizar apenas produtos divergentes",
                "📋 Atualizar todos os produtos do arquivo",
                "🚫 Não atualizar produtos existentes"
            ]
        )

        if st.button("✅ Executar atualização"):
            if opcao == "📦 Inserir apenas novos produtos":
                db.atualizar_produtos_via_csv(diffs["no_excel_not_in_db"])
                st.success("🟢 Novos produtos inseridos!")

            elif opcao == "🔁 Atualizar apenas produtos divergentes":
                df_div = diffs["divergentes"][[
                    "ean", "descricao_arquivo", "emb_arquivo", "secao_arquivo", "grupo_arquivo"
                ]].rename(columns=lambda col: col.replace("_arquivo", ""))

                st.success("🔁 Produtos divergentes atualizados!")

            elif opcao == "📋 Atualizar todos os produtos do arquivo":
                db.atualizar_produtos_via_csv(df)
                st.success("📋 Banco atualizado com todos os produtos!")

            elif opcao == "🚫 Não atualizar produtos existentes":
                db.atualizar_produtos_via_csv(diffs["no_excel_not_in_db"])
                st.success("🛡️ Banco atualizado apenas com produtos novos!")

            st.rerun()

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")


# 👥 Aba 3 — Gerenciar usuários
def exibir_aba_usuarios(admin_username: str):
    st.subheader("Gerenciar Usuários")

    if 'confirming_delete' not in st.session_state:
        st.session_state.confirming_delete = False
        st.session_state.user_to_delete = None

    if st.session_state.confirming_delete:
        confirmar_exclusao_usuario()
    else:
        exibir_lista_usuarios(admin_username)


def exibir_lista_usuarios(admin_username: str):
    usuarios = db.get_all_users()
    usuarios = [u for u in usuarios if u != admin_username]

    if not usuarios:
        st.info("Nenhum outro usuário cadastrado para deletar.")
        return

    usuario_escolhido = st.selectbox(
        "Selecione um usuário para deletar:", usuarios, key="admin_del_user")

    if st.button("Deletar Usuário"):
        st.session_state.confirming_delete = True
        st.session_state.user_to_delete = usuario_escolhido
        st.rerun()


def confirmar_exclusao_usuario():
    usuario = st.session_state.user_to_delete

    st.warning(f"Tem certeza que deseja deletar o usuário **{usuario}**?")
    st.error(
        "Esta ação é irreversível. O usuário será removido, mas os dados de contagem permanecerão.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirmar Exclusão", type="primary"):
            db.delete_user(usuario)
            st.success(f"Usuário '{usuario}' deletado com sucesso!")
            st.session_state.confirming_delete = False
            st.session_state.user_to_delete = None
            st.rerun()

    with col2:
        if st.button("Cancelar"):
            st.session_state.confirming_delete = False
            st.session_state.user_to_delete = None
            st.rerun()
