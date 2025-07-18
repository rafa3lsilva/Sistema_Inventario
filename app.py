import streamlit as st
import database as db
import hashlib
import pandas as pd
from database import atualizar_produtos_via_csv, comparar_csv_com_banco


# Inicializa o banco de dados e as tabelas se não existirem
#db.create_tables()

# Inicializa variáveis de sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None

if 'page' not in st.session_state:
    st.session_state['page'] = 'login'  # Página inicial


def set_page(page):
    st.session_state['page'] = page


# --- FLUXO DE LOGIN E CADASTRO ---
if not st.session_state['logged_in']:
    if st.session_state['page'] == 'login':
        st.title("📦Sistema de Inventário📦")
        st.write("Por favor, faça login para continuar!")
        username_input = st.text_input("Usuário")
        password_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user = db.check_login(username_input, password_input)


            if user:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user['username']
                st.session_state['role'] = user['role']
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
        st.write("---")
        st.write("Não tem uma conta?")
        st.button("Cadastre-se aqui", on_click=set_page, args=('cadastro',))

    elif st.session_state['page'] == 'cadastro':
        st.title("Cadastro de Novo Usuário")

        # Verifica se já existe algum admin cadastrado
        admins_existem = db.admin_exists()  # Função que você vai criar no database.py

        with st.form("cadastro_form"):
            new_username = st.text_input("Escolha um nome de usuário")
            new_password = st.text_input("Escolha uma senha", type="password")
            # Só mostra a opção de admin se não houver nenhum admin cadastrado
            if not admins_existem:
                role = st.selectbox("Tipo de usuário", ["user", "admin"])
            else:
                role = "user"
            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                if new_username and new_password:
                    hashed_password = hashlib.sha256(
                        new_password.encode()).hexdigest()
                    if db.create_user(new_username, hashed_password, role):
                        st.success(
                            "Usuário criado com sucesso! Agora você pode fazer o login.")
                        set_page('login')
                        st.rerun()
                    else:
                        st.error("Este nome de usuário já existe.")
                else:
                    st.error("Por favor, preencha todos os campos.")
        st.button("Voltar para o Login", on_click=set_page, args=('login',))

# --- APLICAÇÃO PRINCIPAL (APÓS LOGIN) ---
else:
    st.sidebar.write(
        f"Bem-vindo, {st.session_state['username']} ({st.session_state['role']})")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['role'] = None
        st.session_state['page'] = 'login'
        st.rerun()

    # Só mostra para usuário comum
    if st.session_state['role'] == 'user':
        st.title("Contagem de Inventário")
        with st.form("form_inventario"):
            ean = st.text_input("Código de barras (EAN)")
            buscar = st.form_submit_button("Buscar produto")

        if ean:
            produto = db.get_product_info(ean)
            if produto:
                st.success(f"Produto encontrado: {produto['descricao']}")
            else:
                st.warning("Produto não cadastrado.")
                with st.form("form_cadastro_produto"):
                    descricao = st.text_input("Descrição do produto")
                    cadastrar = st.form_submit_button("Cadastrar produto")
                    if cadastrar and descricao:
                        db.add_product(ean, descricao)
                        st.success("Produto cadastrado com sucesso!")
                        st.rerun()
            with st.form("form_contagem"):
                quantidade = st.number_input(
                    "Quantidade contada", min_value=1, step=1)
                contar = st.form_submit_button("Registrar contagem")
                if contar:
                    db.add_or_update_count(
                        st.session_state['username'], ean, quantidade)
                    st.success("Contagem registrada/somada com sucesso!")
                    st.rerun()

    elif st.session_state['role'] == 'admin':
        st.title("Dashboard do Administrador")

        aba = st.tabs(["Contagem de Inventário",
                    "Visão Geral", "Update Produtos","Gerenciar Usuários"])

        # Aba 1: Contagem de Inventário (igual ao user)
        with aba[0]:
            st.subheader("Contagem de Inventário")

            with st.form("form_inventario_admin"):
                ean = st.text_input("Código de barras (EAN)", key="admin_ean")
                buscar = st.form_submit_button("Buscar produto")
            if ean:
                produto = db.get_product_info(ean)
                if produto:
                    st.success(f"Produto encontrado: {produto['descricao']}")
                    total_contado = db.get_total_count(ean)
                    st.info(f"Total já contado por todos: {total_contado}")
                else:
                    st.warning("Produto não cadastrado.")
                    with st.form("form_cadastro_produto_admin"):
                        descricao = st.text_input(
                            "Descrição do produto", key="admin_desc")
                        cadastrar = st.form_submit_button(
                            "Cadastrar produto")
                        if cadastrar and descricao:
                            db.add_product(ean, descricao)
                            st.success("Produto cadastrado com sucesso!")
                with st.form("form_contagem_admin"):
                    quantidade = st.number_input(
                        "Quantidade contada", min_value=1, step=1, key="admin_qtd")
                    contar = st.form_submit_button(
                        "Registrar contagem")
                    if contar:
                        db.add_or_update_count(
                            st.session_state['username'], ean, quantidade)
                        st.success("Contagem registrada/somada com sucesso!")
                        st.rerun()

        # Aba 2: Visão Geral das Contagens
        with aba[1]:
            st.subheader("Visão Geral de Todas as Contagens")
            todas_as_contagens = db.get_all_counts()
            if todas_as_contagens.empty:
                st.info("Nenhuma contagem registrada no sistema ainda.")
            else:
                lista_usuarios = ['Todos'] + \
                    list(todas_as_contagens['username'].unique())
                usuario_selecionado = st.selectbox(
                    "Filtrar por usuário:", lista_usuarios, key="admin_filtro_user")
                if usuario_selecionado == 'Todos':
                    st.dataframe(todas_as_contagens)
                else:
                    st.dataframe(
                        todas_as_contagens[todas_as_contagens['username'] == usuario_selecionado])
        
        # Aba 3: Update Produtos
        with aba[2]:
            st.subheader("📤 Upload de Novo Arquivo de Produtos")
            uploaded_file = st.file_uploader(
                "Selecione um arquivo CSV com colunas [ean, descricao]", type=["csv"])

            if uploaded_file:
                try:
                    df_csv = pd.read_csv(uploaded_file)

                    # Verificação das colunas obrigatórias
                    if 'ean' not in df_csv.columns or 'descricao' not in df_csv.columns:
                        st.error(
                            "O arquivo CSV deve conter as colunas 'ean' e 'descricao'.")
                    else:
                        st.success("Arquivo carregado com sucesso!")
                        st.write(df_csv)

                        # Botão para atualizar o banco
                        if st.button("✅ Atualizar Banco de Dados com este CSV"):
                            atualizar_produtos_via_csv(df_csv)
                            st.success("Banco de dados atualizado com sucesso!")

                        # Mostrar diferenças
                        st.subheader("🔍 Diferenças entre Banco e CSV")
                        diffs = comparar_csv_com_banco(df_csv)

                        if not diffs['no_csv_not_in_db'].empty:
                            st.warning("Produtos no CSV que não estão no banco:")
                            st.dataframe(diffs['no_csv_not_in_db'])

                        if not diffs['no_db_not_in_csv'].empty:
                            st.info("Produtos no banco que não estão no CSV:")
                            st.dataframe(diffs['no_db_not_in_csv'])

                except Exception as e:
                    st.error(f"Erro ao ler o CSV: {e}")

        # Aba 4: Gerenciar Usuários
        with aba[3]:
            st.subheader("Gerenciar Usuários")

            # Inicializa o estado de confirmação se ele não existir
            if 'confirming_delete' not in st.session_state:
                st.session_state.confirming_delete = False
                st.session_state.user_to_delete = None

            # ETAPA 2: Se estamos no modo de confirmação, mostra a tela de aviso.
            if st.session_state.confirming_delete:
                st.warning(
                    f"Você tem certeza que deseja deletar o usuário **{st.session_state.user_to_delete}**?")
                st.error("Esta ação é irreversível e todos os dados de contagem deste usuário serão mantidos, mas o usuário não poderá mais fazer login.")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Sim, confirmar exclusão", type="primary"):
                        db.delete_user(st.session_state.user_to_delete)
                        st.success(
                            f"Usuário '{st.session_state.user_to_delete}' deletado com sucesso!")
                        # Reseta o estado e recarrega a página
                        st.session_state.confirming_delete = False
                        st.session_state.user_to_delete = None
                        st.rerun()

                with col2:
                    if st.button("Cancelar"):
                        # Apenas reseta o estado e recarrega a página
                        st.session_state.confirming_delete = False
                        st.session_state.user_to_delete = None
                        st.rerun()

            # ETAPA 1: Se não estamos confirmando, mostra a lista normal de usuários.
            else:
                usuarios = db.get_all_users()
                # Remove o próprio admin da lista de usuários que podem ser deletados
                usuarios = [u for u in usuarios if u != st.session_state['username']]
                

                if usuarios:
                    usuario_para_deletar = st.selectbox(
                        "Selecione um usuário para deletar:", usuarios, key="admin_del_user"
                    )

                    if st.button("Deletar Usuário"):
                        # Define o estado de confirmação para entrar na ETAPA 2 na próxima recarga
                        st.session_state.confirming_delete = True
                        st.session_state.user_to_delete = usuario_para_deletar
                        st.rerun()
                else:
                    st.info("Nenhum outro usuário cadastrado para deletar.")
