import streamlit as st
import pandas as pd
import database_api as db
import sidebar_admin as sb
from modules.scanner import get_barcode


# A função agora recebe o uid
def show_admin_page(username: str, user_uid: str):
    if 'role' not in st.session_state or st.session_state['role'] != 'admin':
        st.warning("Acesso não autorizado.")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    if st.session_state.get("count_successful", False):
        st.session_state.ean_digitado_user = ""
        st.session_state.count_successful = False

    sb.admin_sidebar(username)  # <-- Chamada corrigida para o padrão
    if "pagina_admin" not in st.session_state:
        st.session_state["pagina_admin"] = "📦 Contagem de Inventário"

    pagina = st.session_state["pagina_admin"]

    if pagina == "📦 Contagem de Inventário":
        exibir_aba_contagem(user_uid)

    elif pagina == "📋 Relatório de Contagens":
        exibir_aba_relatorio()
    
    elif pagina == "📊 Auditoria de Estoque":
        exibir_aba_auditoria()

    elif pagina == "📤 Atualizar Produtos":
        exibir_aba_csv()

    elif pagina == "👥 Gerenciar Usuários":
        exibir_aba_usuarios(username)


# A função da aba agora recebe o uid
def exibir_aba_contagem(user_uid: str):
    st.subheader("🛠️ Contagem de Inventário - Administrador")
    st.markdown("### 🧾 Etapa 1: Identificar produto")

    st.write("Aponte a câmera para o código de barras.")
    if st.button("📷 Ativar Leitor de Código de Barras"):
        st.session_state.scanner_active = True

    # O scanner só é mostrado se o estado for ativo
    if st.session_state.get("scanner_active", False):
        st.write("Aponte a câmera para o código de barras...")
        ean_lido = get_barcode()

        # --- NOVO BOTÃO DE CANCELAR ---
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
                    st.session_state.count_message = f"📊 Contagem de {quantidade} para '{produto['descricao']}' registrada!"
                    st.session_state.count_successful = True
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
        # Garante que os valores únicos não contenham nulos para o selectbox
        secoes_unicas = contagens["secao"].dropna().unique()
        grupos_unicos = contagens["grupo"].dropna().unique()

        filtro_secao = st.selectbox(
            "Filtrar por seção", secoes_unicas)
        filtro_grupo = st.selectbox(
            "Filtrar por grupo", grupos_unicos)

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
        # Tenta ler o arquivo
        if arquivo.name.endswith(".csv"):
            arquivo.seek(0)  # Garante que começamos a ler do início do arquivo
            df = pd.read_csv(arquivo, sep=',', quotechar='"',
                             dtype=str, skipinitialspace=True)
        else:  # Para .xlsx ou .xls
            df = pd.read_excel(arquivo, dtype=str)

        # Normaliza nomes das colunas (remove espaços e aspas que possam ter sobrado)
        df.columns = [col.lower().strip().strip('"') for col in df.columns]

        # Verifica colunas obrigatórias
        colunas_esperadas = ['ean', 'descricao', 'emb', 'secao', 'grupo']
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]

        # Mostra uma mensagem de erro mais clara
        if colunas_faltando:
            st.error(
                f"⚠️ Arquivo incompleto ou mal formatado. Colunas esperadas: `{', '.join(colunas_esperadas)}`."
            )
            st.info(
                f"Colunas encontradas no seu arquivo: `{', '.join(df.columns)}`")
            st.warning(
                "Dica: Verifique se o nome das colunas no seu ficheiro está correto.")
            return

        st.success("✅ Arquivo carregado com sucesso!")
        st.dataframe(df)

        # O resto da lógica de comparação e atualização continua igual
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
                "📋 Atualizar todos os produtos do arquivo (insere novos e atualiza existentes)",
                "🚫 Não fazer nada"
            ]
        )

        if st.button("✅ Executar atualização"):
            if opcao == "📦 Inserir apenas novos produtos":
                db.atualizar_produtos_via_csv(diffs["novos"])
                st.success("🟢 Novos produtos inseridos!")

            elif opcao == "🔁 Atualizar apenas produtos divergentes":
                df_div = diffs["divergentes"][[
                    "ean", "descricao_arquivo", "emb_arquivo", "secao_arquivo", "grupo_arquivo"
                ]].rename(columns=lambda col: col.replace("_arquivo", ""))
                db.atualizar_produtos_via_csv(df_div)
                st.success("🔁 Produtos divergentes atualizados!")

            elif opcao.startswith("📋"):
                db.atualizar_produtos_via_csv(df)
                st.success(
                    "📋 Banco atualizado com todos os produtos do arquivo!")

            elif opcao == "🚫 Não fazer nada":
                st.info("Nenhuma alteração foi feita no banco de dados.")
                # st.rerun() não é necessário aqui para não limpar a tela
                return  # Sai da função

            # Apenas faz o rerun se uma ação foi executada
            st.rerun()

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
        st.info(
            "Verifique se o ficheiro não está corrompido e se o formato (CSV, XLSX) está correto.")


# 👥 Aba 3 — Gerenciar usuários
def exibir_aba_usuarios(admin_username: str):
    st.subheader("👥 Gerenciar Usuários")

    # Obtém o UID do admin logado
    admin_uid = st.session_state.get('uid')

    # Busca todos os usuários do Supabase Auth
    lista_de_usuarios = db.get_all_users()

    if not lista_de_usuarios:
        st.info("Nenhum outro usuário cadastrado.")
        return

    # Prepara os dados para exibição numa tabela
    dados_para_tabela = []
    for user in lista_de_usuarios:
        # Não mostra o próprio admin na lista
        if user.id != admin_uid:
            dados_para_tabela.append({
                "UID": user.id,
                "Email": user.email,
                "Nome de Usuário": user.user_metadata.get('username', 'N/A'),
                "Perfil": user.user_metadata.get('role', 'user'),
                "Último Login": user.last_sign_in_at.strftime('%d/%m/%Y %H:%M') if user.last_sign_in_at else "Nunca"
            })

    if not dados_para_tabela:
        st.info("Nenhum outro usuário cadastrado.")
        return

    # Usa o st.dataframe para uma visualização melhor
    df_usuarios = pd.DataFrame(dados_para_tabela)
    st.dataframe(df_usuarios, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Deletar um usuário")

    # Cria uma lista de opções para o selectbox no formato "Nome (Email)"
    opcoes_usuarios = {
        f"{user['Nome de Usuário']} ({user['Email']})": user['UID'] for user in dados_para_tabela}

    if not opcoes_usuarios:
        return

    usuario_selecionado = st.selectbox(
        "Selecione um usuário para deletar:",
        options=opcoes_usuarios.keys()
    )

    if st.button("Deletar Usuário", type="primary"):
        uid_para_deletar = opcoes_usuarios[usuario_selecionado]

        # Guardamos as informações para a confirmação
        st.session_state.user_to_delete = {
            "uid": uid_para_deletar,
            "display_name": usuario_selecionado
        }
        st.rerun()

    # Lógica de confirmação
    if "user_to_delete" in st.session_state:
        user_info = st.session_state.user_to_delete

        st.warning(
            f"Tem certeza que deseja deletar o usuário **{user_info['display_name']}**?")
        st.error("Esta ação é irreversível e não pode ser desfeita.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sim, deletar", use_container_width=True):
                if db.delete_user_by_id(user_info["uid"]):
                    st.success(
                        f"Usuário '{user_info['display_name']}' deletado com sucesso!")
                    del st.session_state.user_to_delete
                    st.rerun()
        with col2:
            if st.button("Cancelar", use_container_width=True):
                del st.session_state.user_to_delete
                st.rerun()

# 📊 Aba 4 — Auditoria de Estoque
def exibir_aba_auditoria():
    st.subheader("📊 Auditoria de Estoque")
    st.markdown(
        "Compare o estoque contado na aplicação com o relatório do seu sistema.")

    arquivo_sistema = st.file_uploader(
        "Faça o upload do seu relatório de estoque do sistema (CSV)",
        type=["csv"]
    )

    if not arquivo_sistema:
        st.info("Aguardando o upload do relatório de estoque.")
        return

    try:
        df_sistema = pd.read_csv(
            arquivo_sistema, sep=';', encoding='latin1', decimal=',')

        coluna_de_dados = df_sistema['Quebra 2'].astype(str)
        df_sistema['secao'] = coluna_de_dados.str.extract(
            r'Seção: \d+ - (.*?)(?:Grupo:|$)')[0].str.strip()
        df_sistema['grupo'] = coluna_de_dados.str.extract(
            r'Grupo: \d+- (.*)')[0].str.strip()
        df_sistema['grupo'].fillna('', inplace=True)
        df_sistema['secao'].fillna(method='ffill', inplace=True)
        df_sistema['grupo'].fillna(method='ffill', inplace=True)
        df_sistema.dropna(subset=['Código'], inplace=True)

        df_sistema.rename(columns={
                          'Código': 'ean', 'Descrição': 'descricao', 'Estoque': 'estoque_sistema'}, inplace=True)
        df_sistema['ean'] = df_sistema['ean'].astype(str)
        df_sistema = df_sistema[['ean', 'descricao',
                                 'secao', 'grupo', 'estoque_sistema']]

        contagens_resultado = db.get_all_contagens_detalhado()
        df_contado = pd.DataFrame(contagens_resultado.data)
        if not df_contado.empty:
            df_contado.rename(
                columns={'quantidade': 'estoque_contado'}, inplace=True)
            df_contado = df_contado[['ean', 'estoque_contado']]
        else:
            df_contado = pd.DataFrame(columns=['ean', 'estoque_contado'])

        df_final = pd.merge(df_sistema, df_contado, on='ean', how='left')

        df_final['estoque_contado'] = df_final['estoque_contado'].fillna(0)
        df_final['estoque_sistema'] = pd.to_numeric(
            df_final['estoque_sistema'], errors='coerce').fillna(0)
        df_final['diferenca'] = df_final['estoque_contado'] - \
            df_final['estoque_sistema']

        df_final = df_final[['ean', 'descricao', 'secao', 'grupo',
                             'estoque_sistema', 'estoque_contado', 'diferenca']]

        st.markdown("---")
        st.subheader("Relatório Comparativo")

        secao_selecionada = st.selectbox("Filtrar por Seção:", options=[
                                         'Todas'] + sorted(df_final['secao'].unique()))

        if secao_selecionada != 'Todas':
            df_filtrado = df_final[df_final['secao'] == secao_selecionada]
            grupo_selecionado = st.selectbox("Filtrar por Grupo:", options=[
                                             'Todos'] + sorted(df_filtrado['grupo'].unique()))
            if grupo_selecionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['grupo']
                                          == grupo_selecionado]
        else:
            df_filtrado = df_final

        mostrar_apenas_diferencas = st.checkbox(
            "Produtos com diferença de estoque")
        if mostrar_apenas_diferencas:

            df_display = df_filtrado[df_filtrado['diferenca'] != 0].copy()
        else:
            df_display = df_filtrado.copy() 

        mostrar_apenas_contados = st.checkbox(
            "Produtos contados")
        if mostrar_apenas_contados:
            df_display = df_display[df_display['estoque_contado'] != 0].copy()
        else:
            df_display = df_display.copy()

        mostrar_apenas_zerados = st.checkbox(
            "Produtos zerados")
        if mostrar_apenas_zerados:
            df_display = df_display[df_display['diferenca'] == 0].copy()
        else:
            df_display = df_display.copy()
        
        mostrar_apenas_positivos = st.checkbox(
            "Produtos positivos")
        if mostrar_apenas_positivos:
            df_display = df_display[df_display['diferenca'] > 0].copy()
        else:
            df_display = df_display.copy()

        mostrar_apenas_negativos = st.checkbox(
            "Produtos negativos")
        if mostrar_apenas_negativos:
            df_display = df_display[df_display['diferenca'] < 0].copy()
        else:
            df_display = df_display.copy()

        # 1. Definimos a função de formatação
        def formatar_numero(valor):
            if valor == int(valor):
                return str(int(valor))
            else:
                return str(valor).replace('.', ',')

        # 2. Aplicamos a formatação às colunas numéricas
        colunas_para_formatar = ['estoque_sistema',
                                 'estoque_contado', 'diferenca']
        for col in colunas_para_formatar:
            df_display[col] = df_display[col].apply(formatar_numero)

        # 3. Exibimos a tabela já formatada
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv = df_display.to_csv(index=False, sep=';').encode('latin1')
        st.download_button(
            label="📥 Descarregar Relatório de Auditoria",
            data=csv,
            file_name='auditoria_de_estoque.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"❌ Erro ao processar o relatório: {e}")
        st.warning(
            "Verifique se o relatório do sistema tem as colunas 'Código', 'Estoque' e 'Quebra 2'.")
