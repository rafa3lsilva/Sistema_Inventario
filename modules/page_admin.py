import streamlit as st
import pandas as pd
import database_api as db
from sidebar_admin import admin_sidebar
from database_api import (
    atualizar_produtos_via_csv,
    get_all_contagens_detalhado,
)
from modules.contagem_utils import registrar_contagem
import modules.scanner as scanner
from database_api import get_all_products_df
from database_api import comparar_produtos_com_banco


def show_admin_page(username: str):
    admin_sidebar(username)
    if "pagina_admin" not in st.session_state:
        st.session_state["pagina_admin"] = "📦 Contagem de Inventário"

    # 📄 Exibe o conteúdo da página selecionada
    pagina = st.session_state["pagina_admin"]

    if pagina == "📦 Contagem de Inventário":
        exibir_aba_contagem(username)

    elif pagina == "📋 Relatório de Contagens":
        exibir_aba_relatorio()

    elif pagina == "📤 Atualizar Produtos":
        exibir_aba_csv()

    elif pagina == "👥 Gerenciar Usuários":
        exibir_aba_usuarios(username)


# 📦 Aba 0 — Registrar contagem
def exibir_aba_contagem(username):
    """
    Exibe aba de contagem de inventário para o administrador.
    """
    st.subheader("🛠️ Contagem de Inventário - Administrador")
    st.markdown("### 🧾 Etapa 1: Identificar produto")

    col1, col2 = st.columns([3, 1])
    with col1:
        ean = st.text_input("Código de barras", key="ean_input_admin")
    with col2:
        if st.button("📷", key="btn_scan_admin"):
            scanner.mostrar_scanner_ean(altura=350, tempo_limite=12)

    produto = None
    if ean:
        ean = ean.strip()
        ean = db.sanitizar_ean(ean)  # Garante sanitização
        produto = db.get_product_info(ean)
        if produto:
            st.success(f"🟢 Produto encontrado: **{produto['descricao']}**")

        else:
            st.warning("⚠️ Produto não cadastrado.")
            st.markdown("### 🆕 Etapa 2: Cadastrar novo produto")

            # 🔄 Listas suspensas para campos padronizados
            df_produtos = db.get_all_products_df()
            embs = (
                sorted(df_produtos["emb"].dropna().unique())
                if "emb" in df_produtos.columns else ["PCT", "KG", "UN","CX","SC","L","LT"]
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

    # Se o produto foi encontrado, exibe a etapa de contagem
    if produto:
        st.markdown("### 📦 Etapa 3: Registrar contagem")
        with st.form("form_contagem_admin"):
            quantidade = st.number_input(
                "Quantidade contada", min_value=1, step=1)
            contar = st.form_submit_button("Registrar")
            if contar:
                try:
                    db.add_or_update_count(username, ean, quantidade)
                    st.success("📊 Contagem registrada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao registrar contagem: {e}")
                    


# 📋 Aba 1 — Relatório de contagens
def exibir_aba_relatorio():
    st.subheader("📋 Relatório de Contagens")

    resultado = get_all_contagens_detalhado()
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
        # 📄 Lê conforme o tipo
        if arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)

        # ✅ Normaliza nomes das colunas
        df.columns = [col.lower().strip() for col in df.columns]

        # 📋 Verifica colunas obrigatórias
        colunas_esperadas = ['ean', 'descricao', 'emb', 'secao', 'grupo']
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]

        if colunas_faltando:
            st.error(
                f"⚠️ Arquivo incompleto. Faltando: {', '.join(colunas_faltando)}")
            return

        st.success("✅ Arquivo carregado com sucesso!")
        st.dataframe(df)

        # 📊 Comparar com banco

        diffs = comparar_produtos_com_banco(df)

        if not diffs["novos"].empty:
            st.warning("📦 Produtos no arquivo que não estão no banco:")
            st.dataframe(diffs["novos"])

        if not diffs["ausentes"].empty:
            st.info("📍 Produtos no banco que não estão no arquivo:")
            st.dataframe(diffs["ausentes"])

        if not diffs["divergentes"].empty:
            st.error("🔄 Produtos com diferenças entre arquivo e banco:")
            st.dataframe(diffs["divergentes"])

        # 🧠 Opção interativa
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
                atualizar_produtos_via_csv(diffs["no_excel_not_in_db"])
                st.success("🟢 Novos produtos inseridos!")

            elif opcao == "🔁 Atualizar apenas produtos divergentes":
                df_div = diffs["divergentes"][[
                    "ean", "descricao_arquivo", "emb_arquivo", "secao_arquivo", "grupo_arquivo"
                ]].rename(columns=lambda col: col.replace("_arquivo", ""))

                st.success("🔁 Produtos divergentes atualizados!")

            elif opcao == "📋 Atualizar todos os produtos do arquivo":
                atualizar_produtos_via_csv(df)
                st.success("📋 Banco atualizado com todos os produtos!")

            elif opcao == "🚫 Não atualizar produtos existentes":
                atualizar_produtos_via_csv(diffs["no_excel_not_in_db"])
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
            st.session_state.user_to_delete = None
            st.rerun()
            st.rerun()
