# import sqlite3
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib  # Adicionado para hash de senha
from sqlalchemy import create_engine, text

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

engine = create_engine(st.secrets["database"]["url"])


def get_db_connection():
    with engine.connect() as conn:
        return conn


def create_tables():
    conn = get_db_connection()
    # Tabela de produtos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            ean TEXT PRIMARY KEY,
            descricao TEXT NOT NULL
        )
    ''')
    # Tabela de usuários
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # Tabela de contagens
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ean TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES usuarios (username),
            FOREIGN KEY (ean) REFERENCES produtos (ean)
        )
    ''')
    conn.commit()
    conn.close()
    # Exemplo: popular com um usuário admin e carregar produtos
    populate_initial_data()


def populate_initial_data():
    # Adicionar usuários (agora usando hash de senha)
    '''try:
        conn = get_db_connection()
        admin_hash = hashlib.sha256('admin'.encode()).hexdigest()
        user1_hash = hashlib.sha256('123'.encode()).hexdigest()
        conn.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                     ('admin', admin_hash, 'admin'))
        conn.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)", ('user1', user1_hash, 'user'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Usuários já existem
    finally:
        conn.close()'''

    # Carregar produtos do CSV
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    if count == 0:
        try:
            df_produtos = pd.read_csv('produtos.csv')
            if not df_produtos.empty:
                df_produtos.to_sql(
                    'produtos', conn, if_exists='append', index=False)
            else:
                print("O arquivo produtos.csv está vazio. Nenhum produto foi carregado.")
        except FileNotFoundError:
            print(
                "Arquivo produtos.csv não encontrado. A tabela de produtos estará vazia.")
        except pd.errors.EmptyDataError:
            print(
                "Arquivo produtos.csv está vazio ou sem colunas. Nenhum produto foi carregado.")
    conn.close()


def get_product_info(ean):
    conn = get_db_connection()
    produto = conn.execute(
        "SELECT descricao FROM produtos WHERE ean = ?", (ean,)).fetchone()
    conn.close()
    return produto['descricao'] if produto else "Produto não encontrado"

'''
def add_or_update_count(username, ean, quantidade):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verifica se o item já foi contado por este usuário
    cursor.execute(
        "SELECT id, quantidade FROM contagens WHERE username = ? AND ean = ?", (username, ean))
    data = cursor.fetchone()

    if data:
        # Se existe, atualiza a quantidade
        id_contagem, qtd_existente = data
        nova_qtd = qtd_existente + quantidade
        cursor.execute(
            "UPDATE contagens SET quantidade = ? WHERE id = ?", (nova_qtd, id_contagem))
        resultado = f"Atualizado! Total agora: {nova_qtd}"
    else:
        # Se não existe, insere um novo registro
        cursor.execute(
            "INSERT INTO contagens (username, ean, quantidade) VALUES (?, ?, ?)", (username, ean, quantidade))
        resultado = f"Adicionado! Total: {quantidade}"

    conn.commit()
    conn.close()
    return resultado
'''

def get_all_counts():
    conn = get_db_connection()
    # Usamos JOIN para buscar a descrição do produto também
    query = """
        SELECT c.username, c.ean, p.descricao, c.quantidade, c.timestamp
        FROM contagens c
        JOIN produtos p ON c.ean = p.ean
        ORDER BY c.username, c.timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def create_user(username, hashed_password, role):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO usuarios (username, password, role)
                VALUES (:username, :password, :role)
            """), {"username": username, "password": hashed_password, "role": role})
        return True
    except:
        return False


def admin_exists():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM usuarios WHERE role = 'admin' LIMIT 1")).fetchone()
    return result is not None
    return result is not None

def get_all_users():
    with engine.connect() as conn:
        users = [row['username'] for row in conn.execute(text("SELECT username FROM usuarios")).fetchall()]
    return users

def delete_user(username):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM usuarios WHERE username = :username"), {"username": username})

def check_login(username, password):
    """
    Verifica se o usuário e senha estão corretos.
    Retorna um dicionário com os dados do usuário se válido, senão retorna None.
    """
    conn = get_db_connection()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    user = conn.execute(
        "SELECT username, role FROM usuarios WHERE username = ? AND password = ?",
        (username, hashed_password)
    ).fetchone()
    conn.close()
    if user:
        return {"username": user["username"], "role": user["role"]}
    else:
        return None
    
def get_product_info(ean):
    conn = get_db_connection()
    produto = conn.execute("SELECT * FROM produtos WHERE ean = ?", (ean,)).fetchone()
    conn.close()
    if produto:
        return {"ean": produto["ean"], "descricao": produto["descricao"]}
    return None


def add_product(ean, descricao):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO produtos (ean, descricao)
                VALUES (:ean, :descricao)
                ON CONFLICT (ean) DO NOTHING
            """), {"ean": ean, "descricao": descricao})
    except Exception as e:
        print(f"Erro ao adicionar produto: {e}")

def get_total_count(ean):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT SUM(quantidade) as total FROM contagens WHERE ean = :ean"), {"ean": ean}).fetchone()
    return result["total"] if result and result["total"] else 0

def add_or_update_count(username, ean, quantidade):
    with engine.connect() as conn:
        # Verifica se já existe contagem para esse user e produto
        result = conn.execute(text("SELECT quantidade FROM contagens WHERE username = :username AND ean = :ean"), {"username": username, "ean": ean}).fetchone()
        if result:
            nova_qtd = result["quantidade"] + quantidade
            conn.execute(text("UPDATE contagens SET quantidade = :quantidade, timestamp = CURRENT_TIMESTAMP WHERE username = :username AND ean = :ean"), {"quantidade": nova_qtd, "username": username, "ean": ean})
        else:
            conn.execute(text("INSERT INTO contagens (username, ean, quantidade) VALUES (:username, :ean, :quantidade)"), {"username": username, "ean": ean, "quantidade": quantidade})

def atualizar_produtos_via_csv(df_csv):
    """
    Atualiza a tabela produtos com base no DataFrame carregado do CSV.
    Evita duplicatas e atualiza descrições se necessário.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    for _, row in df_csv.iterrows():
        ean, descricao = row['ean'], row['descricao']
        existente = cursor.execute(
            "SELECT descricao FROM produtos WHERE ean = ?", (ean,)).fetchone()
        if existente:
            if existente['descricao'] != descricao:
                cursor.execute(
                    "UPDATE produtos SET descricao = ? WHERE ean = ?", (descricao, ean))
        else:
            cursor.execute(
                "INSERT INTO produtos (ean, descricao) VALUES (?, ?)", (ean, descricao))

    conn.commit()
    conn.close()


def comparar_csv_com_banco(df_csv):
    """
    Compara o conteúdo do CSV com o banco e retorna diferenças:
    - Produtos presentes no CSV e ausentes no banco
    - Produtos presentes no banco e ausentes no CSV
    """
    conn = get_db_connection()
    df_db = pd.read_sql_query("SELECT ean, descricao FROM produtos", conn)
    conn.close()

    eans_csv = set(df_csv['ean'].astype(str))
    eans_db = set(df_db['ean'].astype(str))

    somente_csv = eans_csv - eans_db
    somente_db = eans_db - eans_csv

    return {
        'no_csv_not_in_db': df_csv[df_csv['ean'].astype(str).isin(somente_csv)],
        'no_db_not_in_csv': df_db[df_db['ean'].astype(str).isin(somente_db)]
    }
