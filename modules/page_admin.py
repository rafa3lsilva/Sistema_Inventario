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

    sb.admin_sidebar(username) 
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


def exibir_aba_contagem(user_uid: str):
    # A função da aba agora recebe o uid
    st.subheader("🛠️ Contagem de Inventário - Administrador")
    st.markdown("### 🧾 Identificar produto")

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
        emb = produto.get("emb", "").upper() if produto else ""
        if emb in ["KG", "L", "GR", "ML"]:
            min_val = 0.0
            step = 0.001
            fmt = "%.3f"
        else:
            min_val = 0
            step = 1
            fmt = "%d"

        with st.form("form_contagem_admin"):
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


# 📋 Aba 1 — Relatório de contagens
def exibir_aba_relatorio():
    st.subheader("📋 Gestão e Relatório de Contagens")

    # Usamos o session_state para guardar os dados e comparar com as edições
    # Carrega os dados do banco apenas uma vez para não perder as edições
    if 'dados_contagem' not in st.session_state:
        dados_brutos = db.get_relatorio_contagens_completo()
        if not dados_brutos:
            st.info("Nenhuma contagem registrada ainda.")
            # Limpa o estado se não houver dados
            if 'dados_contagem' in st.session_state:
                del st.session_state.dados_contagem
            return
        st.session_state.dados_contagem = pd.DataFrame(dados_brutos)

    # Se a sessão foi limpa, mas a página recarregou, sai
    if 'dados_contagem' not in st.session_state or st.session_state.dados_contagem.empty:
        st.info("Nenhuma contagem registrada ainda.")
        return

    contagens = st.session_state.dados_contagem.copy()

    # Processamento dos dados para exibição
    if "produtos" in contagens.columns and contagens["produtos"].notna().any():
        produtos_df = pd.json_normalize(contagens["produtos"].dropna())
        contagens_sem_produtos = contagens.drop(columns=["produtos"])
        contagens = pd.concat([contagens_sem_produtos.reset_index(
            drop=True), produtos_df.reset_index(drop=True)], axis=1)

    users_from_auth = db.get_all_users()
    user_map = {user.id: user.user_metadata.get(
        "username", user.email) for user in users_from_auth}
    contagens["usuario"] = contagens["usuario_uid"].map(
        user_map).fillna("Desconhecido")
    contagens["deletar"] = False

    # --- Filtros ---
    st.markdown("#### Filtros")


    col1, col2, col3 = st.columns(3)

    # O DataFrame base para os filtros é a tabela completa de contagens
    df_para_filtrar = contagens.copy()

    # Filtro de Usuário
    with col1:
        if 'usuario' in df_para_filtrar.columns:
            usuarios_disponiveis = ['Todos'] + sorted(
                [str(u) for u in df_para_filtrar['usuario'].dropna().unique() if str(u).strip() != ""]
            )
            usuario_selecionado = st.selectbox(
                "Filtrar por Usuário", usuarios_disponiveis)
            if usuario_selecionado != 'Todos':
                df_para_filtrar = df_para_filtrar[df_para_filtrar['usuario'] == usuario_selecionado]

    # Filtro de Seção
    with col2:
        if 'secao' in df_para_filtrar.columns:
            secoes_disponiveis = ['Todas'] + sorted(
                [str(s) for s in df_para_filtrar['secao'].dropna().unique() if str(s).strip() != ""]
            )
            secao_selecionada = st.selectbox(
                "Filtrar por Seção", secoes_disponiveis)
            if secao_selecionada != 'Todas':
                df_para_filtrar = df_para_filtrar[df_para_filtrar['secao'] == secao_selecionada]

    # Filtro de Grupo
    with col3:
        if 'grupo' in df_para_filtrar.columns:
            grupos_disponiveis = ['Todos'] + sorted(
                [str(g) for g in df_para_filtrar['grupo'].dropna().unique() if str(g).strip() != ""]
            )
            grupo_selecionado = st.selectbox(
                "Filtrar por Grupo", grupos_disponiveis)
            if grupo_selecionado != 'Todos':
                df_para_filtrar = df_para_filtrar[df_para_filtrar['grupo'] == grupo_selecionado]

    st.markdown("---")

    st.markdown("#### Gestão de Contagens")
    st.info("Clique duas vezes numa célula de 'Quantidade' para editar. Marque 'Deletar?' para remover.")
    
    colunas_necessarias = ["ean", "descricao", "usuario", "quantidade",
                           "secao", "grupo", "last_updated_at", "deletar", "id", "usuario_uid"]
    for col in colunas_necessarias:
        if col not in df_para_filtrar.columns:
            df_para_filtrar[col] = None

    edited_df = st.data_editor(
        df_para_filtrar,
        column_order=["ean", "descricao", "usuario", "quantidade",
                      "secao", "grupo", "last_updated_at", "deletar"],
        column_config={
            "id": None, "usuario_uid": None,
            "ean": st.column_config.TextColumn("EAN", disabled=True),
            "descricao": st.column_config.TextColumn("Descrição", disabled=True),
            "usuario": st.column_config.TextColumn("Usuário", disabled=True),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=0.001, format="%.3f"),
            "secao": st.column_config.TextColumn("Seção", disabled=True),
            "grupo": st.column_config.TextColumn("Grupo", disabled=True),
            "last_updated_at": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm", disabled=True),
            "deletar": st.column_config.CheckboxColumn("Deletar?")
        },
        use_container_width=True, hide_index=True, key="data_editor_contagens"
    )

    # --- Botões de Ação ---
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("💾 Salvar Alterações", use_container_width=True):
            alteracoes_sucesso = 0
            # Compara o DataFrame editado com o original para encontrar as mudanças
            for _, row in edited_df.iterrows():
                original_row = st.session_state.dados_contagem.loc[
                    st.session_state.dados_contagem['id'] == row['id']]
                if not original_row.empty and original_row.iloc[0]['quantidade'] != row['quantidade']:
                    if db.update_count(row['id'], row['quantidade'], admin=True):
                        alteracoes_sucesso += 1

            if alteracoes_sucesso > 0:
                st.success(
                    f"{alteracoes_sucesso} contagem(ns) atualizada(s) com sucesso!")
                del st.session_state.dados_contagem  # Força a recarga dos dados
                st.rerun()
            else:
                st.info("Nenhuma alteração de quantidade foi feita.")

    with col_b2:
        if st.button("🗑️ Deletar Registos Marcados", use_container_width=True):
            ids_para_deletar = edited_df[edited_df["deletar"]]["id"].tolist()
            if ids_para_deletar:
                if db.delete_contagens_by_ids(ids_para_deletar):
                    st.success(
                        f"{len(ids_para_deletar)} registo(s) apagado(s) com sucesso.")
                    del st.session_state.dados_contagem  # Força a recarga
                    st.rerun()
            else:
                st.warning("Nenhum registo selecionado para apagar.")

    st.markdown("---")

    # --- Zona de Perigo ---
    with st.expander("⚠️ Zona de Perigo (Ações em Massa)"):
        st.error(
            "As ações nesta secção são irreversíveis e apagarão grandes volumes de dados.")

        # Deletar por usuário
        st.subheader("Deletar todas as contagens de um usuário")
        # 1. Pegamos apenas os usuários que REALMENTE fizeram contagens
        usuarios_com_contagem = contagens.drop_duplicates(
            subset=['usuario_uid'])

        # 2. Criamos um dicionário para o selectbox: {Nome Amigável: UID}
        mapa_nomes_para_uid = pd.Series(
            usuarios_com_contagem.usuario_uid.values,
            index=usuarios_com_contagem.usuario
        ).to_dict()

        if mapa_nomes_para_uid:
            # 3. As opções do selectbox são os nomes amigáveis
            nome_selecionado = st.selectbox(
                "Selecione o usuário:", options=mapa_nomes_para_uid.keys())

            if st.button(f"Deletar TODAS as contagens de {nome_selecionado}", type="primary"):
                st.session_state.confirm_delete_user_counts = nome_selecionado

            if st.session_state.get("confirm_delete_user_counts") == nome_selecionado:
                if st.checkbox(f"**Confirmo que quero apagar TODAS as contagens de {nome_selecionado}.**"):
                    if st.button("EXECUTAR EXCLUSÃO DE USUÁRIO", type="primary"):
                        # Pegamos o UID correspondente ao nome selecionado
                        uid_para_deletar = mapa_nomes_para_uid[nome_selecionado]
                        if db.delete_all_counts_by_user(uid_para_deletar):
                            st.success(
                                "Contagens do usuário deletadas com sucesso.")
                            del st.session_state.confirm_delete_user_counts
                            st.rerun()
        else:
            st.info("Não há usuários com contagens para selecionar.")

        # Deletar TUDO
        st.subheader("Zerar todo o inventário contado")
        if st.button("Deletar TODAS as contagens existentes", type="primary"):
            st.session_state.confirm_delete_all = True

        if st.session_state.get("confirm_delete_all"):
            if st.checkbox("**Confirmo que quero apagar TODO o histórico de contagens da aplicação.**", key="confirm_all_delete_cb"):
                if st.button("EXECUTAR EXCLUSÃO GERAL", type="primary"):
                    if db.delete_todas_as_contagens():
                        st.success(
                            "Todas as contagens foram deletadas com sucesso.")
                        del st.session_state.confirm_delete_all
                        st.rerun()


# 📤 Aba 2 — Atualização via CSV
def exibir_aba_csv():
    st.subheader("📤 Atualizar Produtos a partir de Relatório")
    st.info("Faça o upload do relatório de cadastro do sistema. A aplicação fará a limpeza automaticamente.")

    arquivo = st.file_uploader(
        "Selecione o relatório de cadastro do seu sistema", type=["csv"]
    )
    if not arquivo:
        return

    try:
        # 1. Ler o relatório
        df_bruto = pd.read_csv(arquivo, sep=";", encoding="latin1")

        # 2. Validação de colunas
        colunas_esperadas = {"Código", "Descrição", "EMB", "Quebra 2"}
        if not colunas_esperadas.issubset(df_bruto.columns):
            st.error(
                f"Arquivo inválido. Esperado: {colunas_esperadas}, mas encontrou: {set(df_bruto.columns)}"
            )
            return

        # 3. Extrair seção e grupo
        coluna_de_dados = df_bruto["Quebra 2"].astype(str)
        df_bruto["secao"] = coluna_de_dados.str.extract(
            r"Seção: \d+ - (.*?)(?:Grupo:|$)"
        )[0].str.strip()
        df_bruto["grupo"] = coluna_de_dados.str.extract(
            r"Grupo: \d+- (.*)"
        )[0].str.strip()

        # Corrigir valores nulos
        df_bruto["grupo"] = df_bruto["grupo"].fillna("")
        df_bruto["secao"] = df_bruto["secao"].ffill()
        df_bruto["grupo"] = df_bruto["grupo"].ffill()

        # 4. Limpeza e renomeação
        df_bruto.dropna(subset=["Código"], inplace=True)
        df_bruto.rename(
            columns={"Código": "ean", "Descrição": "descricao", "EMB": "emb"},
            inplace=True,
        )

        df = df_bruto[["ean", "descricao", "emb", "secao", "grupo"]].copy()

        # 🔎 Normalização do EAN (mantém qualquer tamanho, apenas dígitos)
        df["ean"] = (
            df["ean"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)  # mantém só números
            .str.strip()
        )

        if df.empty:
            st.warning("Nenhum produto válido encontrado no arquivo.")
            return

        st.success(
            f"✅ Relatório processado com sucesso! ({df.shape[0]} linhas)")
        st.dataframe(df.head())

        # 5. Comparação com banco de dados
        diffs = db.comparar_produtos_com_banco(df)

        if not diffs["novos"].empty:
            st.warning(
                f"📦 Produtos no relatório que não estão no banco: ({len(diffs['novos'])})"
            )
            st.dataframe(diffs["novos"])

        if not diffs["ausentes"].empty:
            st.info(
                f"📍 Produtos no banco que não estão no relatório: ({len(diffs['ausentes'])})"
            )
            st.dataframe(diffs["ausentes"])

        if not diffs["divergentes"].empty:
            st.error(
                f"🔄 Produtos com diferenças entre relatório e banco: ({len(diffs['divergentes'])})"
            )
            st.dataframe(diffs["divergentes"])

        # 6. Seletor de ação
        qtd_novos = len(diffs["novos"])
        qtd_div = len(diffs["divergentes"])
        qtd_total = len(df)

        st.markdown("### 🛠️ Como deseja atualizar o banco?")
        opcao = st.radio(
            "Selecione:",
            [
                f"📦 Inserir apenas novos produtos ({qtd_novos})",
                f"🔁 Atualizar apenas produtos divergentes ({qtd_div})",
                f"📋 Atualizar todos os produtos do relatório ({qtd_total})",
                "🚫 Não fazer nada",
            ],
        )

        tem_algo_para_fazer = not (
            (opcao.startswith("📦") and qtd_novos == 0)
            or (opcao.startswith("🔁") and qtd_div == 0)
        )

        if st.button("✅ Executar atualização", disabled=not tem_algo_para_fazer):
            if opcao.startswith("📦"):
                db.atualizar_produtos_via_csv(diffs["novos"])
                st.success(f"🟢 {qtd_novos} novos produtos inseridos!")
            elif opcao.startswith("🔁"):
                df_div = diffs["divergentes"][
                    ["ean", "descricao_arquivo", "emb_arquivo",
                        "secao_arquivo", "grupo_arquivo"]
                ].rename(columns=lambda col: col.replace("_arquivo", ""))
                db.atualizar_produtos_via_csv(df_div)
                st.success(f"🔁 {qtd_div} produtos divergentes atualizados!")
            elif opcao.startswith("📋"):
                db.atualizar_produtos_via_csv(df)
                st.success(
                    f"📋 Banco atualizado com {qtd_total} produtos do relatório!")
            else:
                st.info("Nenhuma alteração foi feita no banco de dados.")
                st.stop()

            st.rerun()

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
        st.warning("Verifique se o arquivo é o relatório correto do sistema.")

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
        # Carregar e normalizar
        df_sistema = db.carregar_relatorio_sistema(arquivo_sistema)
        df_contado, n_linhas_contagens, n_unicos_contagens = db.carregar_contagens_consolidadas()

        # Aviso sobre consolidação das contagens (se houver)
        if n_linhas_contagens > n_unicos_contagens:
            st.info(
                f"ℹ️ Consolidadas {n_linhas_contagens - n_unicos_contagens} linhas de contagem em {n_unicos_contagens} EANs únicos.")

        # Merge (sistema é a base)
        df_final = pd.merge(df_sistema, df_contado, on='ean', how='left')
        df_final['estoque_contado'] = df_final['estoque_contado'].fillna(0)
        df_final['estoque_sistema'] = pd.to_numeric(
            df_final['estoque_sistema'], errors='coerce').fillna(0)
        df_final['diferenca'] = df_final['estoque_contado'] - \
            df_final['estoque_sistema']

        df_final = df_final[['ean', 'descricao', 'secao', 'grupo',
                             'estoque_sistema', 'estoque_contado', 'diferenca']]

        if df_final.empty:
            st.info("Não há produtos no relatório do sistema após o processamento.")
            return

        # --------------------------
        # Quadro resumo
        # --------------------------
        total_produtos = len(df_final)
        produtos_contados = (df_final['estoque_contado'] > 0).sum()
        produtos_com_diferenca = (df_final['diferenca'] != 0).sum()
        diferencas_positivas = (df_final['diferenca'] > 0).sum()
        diferencas_negativas = (df_final['diferenca'] < 0).sum()
        soma_diferencas = df_final['diferenca'].sum()

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r4, col_r5, col_r6 = st.columns(3)

        col_r1.metric("📦 Total de Produtos", total_produtos)
        col_r2.metric("✅ Produtos Contados", produtos_contados)
        col_r3.metric("⚠️ Com Diferença", produtos_com_diferenca)
        col_r4.metric("🔼 Diferenças Positivas", diferencas_positivas)
        col_r5.metric("🔽 Diferenças Negativas", diferencas_negativas)
        col_r6.metric("Σ Soma das Diferenças", soma_diferencas)

        st.markdown("---")
        st.subheader("Relatório Comparativo")

        # --------------------------
        # Filtros: seção -> grupo -> tipo diferença -> apenas contados
        # --------------------------
        # Preparar opções removendo vazios/NaN e ordenando
        secoes = sorted([s for s in df_final['secao'].unique()
                        if pd.notna(s) and str(s).strip() != ''])
        secoes_options = ['Todas'] + secoes

        secao_selecionada = st.selectbox(
            "Filtrar por Seção:", options=secoes_options)

        if secao_selecionada != 'Todas':
            df_filtrado = df_final[df_final['secao']
                                   == secao_selecionada].copy()
        else:
            df_filtrado = df_final.copy()

        # Grupo com base na seção atual (dinâmico)
        grupos = sorted([g for g in df_filtrado['grupo'].unique()
                        if pd.notna(g) and str(g).strip() != ''])
        grupos_options = ['Todos'] + grupos
        grupo_selecionado = st.selectbox(
            "Filtrar por Grupo:", options=grupos_options)

        if grupo_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['grupo']
                                      == grupo_selecionado].copy()

        # Tipo de diferença (radio)
        col1, col2 = st.columns([2, 1])
        with col1:
            tipo_de_diferenca = st.radio(
                "Filtrar por tipo de diferença:",
                options=["Mostrar Todos", "Apenas com Diferença",
                         "Diferença Positiva", "Diferença Negativa", "Sem Diferença (Zerados)"],
                horizontal=True
            )

        if tipo_de_diferenca == "Apenas com Diferença":
            df_filtrado = df_filtrado[df_filtrado['diferenca'] != 0]
        elif tipo_de_diferenca == "Diferença Positiva":
            df_filtrado = df_filtrado[df_filtrado['diferenca'] > 0]
        elif tipo_de_diferenca == "Diferença Negativa":
            df_filtrado = df_filtrado[df_filtrado['diferenca'] < 0]
        elif tipo_de_diferenca == "Sem Diferença (Zerados)":
            df_filtrado = df_filtrado[df_filtrado['diferenca'] == 0]

        with col2:
            mostrar_apenas_contados = st.checkbox(
                "Mostrar apenas produtos contados")
            if mostrar_apenas_contados:
                df_filtrado = df_filtrado[df_filtrado['estoque_contado'] != 0]

        # --------------------------
        # Ordenar A → Z pela descricao (case-insensitive)
        # --------------------------
        df_display = df_filtrado.sort_values(
            by='descricao', key=lambda s: s.str.lower()).reset_index(drop=True)

        # --------------------------
        # Formatação apenas para exibição (não altera df_display usado para CSV)
        # --------------------------
        def formatar_numero(valor):
            import math
            if pd.isna(valor):
                return ""
            try:
                f = float(valor)
                if math.isclose(f, int(f)):
                    return str(int(round(f)))
                # trocar ponto por vírgula para exibição
                return str(f).replace('.', ',')
            except Exception:
                return str(valor)

        df_display_fmt = df_display.copy()
        for col in ['estoque_sistema', 'estoque_contado', 'diferenca']:
            if col in df_display_fmt.columns:
                df_display_fmt[col] = df_display_fmt[col].apply(
                    formatar_numero)

        st.dataframe(df_display_fmt, use_container_width=True, hide_index=True)

        # --------------------------
        # Download (CSV) - usa os valores numéricos originais
        # --------------------------
        csv = df_display.to_csv(index=False, sep=';',
                                encoding='latin1').encode('latin1')
        st.download_button(
            label="📥 Descarregar Relatório de Auditoria",
            data=csv,
            file_name='auditoria_de_estoque.csv',
            mime='text/csv',
        )

    except KeyError as e:
        st.error(f"❌ Coluna ausente no relatório: {e}")
    except pd.errors.ParserError:
        st.error("❌ Erro ao ler o CSV. Verifique separador, encoding ou formatação.")
    except Exception as e:
        st.error(f"❌ Erro inesperado: {e}")
