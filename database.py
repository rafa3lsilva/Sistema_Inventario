# import sqlite3
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib  # Adicionado para hash de senha
from sqlalchemy import create_engine, text

# Pega a URL do banco do secrets.toml
database_url = st.secrets["DATABASE_URL"]

engine = create_engine(database_url)
conn = engine.connect()


def get_db_connection():
    return engine.connect()


def get_product_info(ean):
    with get_db_connection() as conn:
        produto = conn.execute(
            text("SELECT descricao FROM produtos WHERE ean = :ean"), {
                "ean": ean}
        ).fetchone()
    return produto[0] if produto else "Produto não encontrado"


def get_all_counts():
    query = """
        SELECT c.username, c.ean, p.descricao, c.quantidade, c.timestamp
        FROM contagens c
        JOIN produtos p ON c.ean = p.ean
        ORDER BY c.username, c.timestamp DESC
    """
    df = pd.read_sql_query(
        text(query), con=engine)  # Use 'text' para segurança
    return df



def create_user(username, hashed_password, role):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO usuarios (username, password, role)
                VALUES (:username, :password, :role)
            """), {"username": username, "password": hashed_password, "role": role})

        # Verificando se o usuário foi realmente inserido
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT username FROM usuarios WHERE username = :username
            """), {"username": username}).fetchone()
            print(f"Usuário inserido: {result}")

        return True
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        return False


def admin_exists():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM usuarios WHERE role = 'admin' LIMIT 1")).fetchone()
    return result is not None

def get_all_users():
    with engine.connect() as conn:
        users = [row['username'] for row in conn.execute(
            text("SELECT username FROM usuarios")).mappings().all()]
    return users


def delete_user(username):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM usuarios WHERE username = :username"),
            {"username": username}
        )



def check_login(username, password):
    """
    Verifica se o usuário e senha estão corretos.
    Retorna um dicionário com os dados do usuário se válido, senão retorna None.
    """
    conn = get_db_connection()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    query = text(
        "SELECT username, role FROM usuarios WHERE username = :username AND password = :password")
    user = conn.execute(
        query, {"username": username, "password": hashed_password}).fetchone()
    conn.close()
    if user:
        return {"username": user[0], "role": user[1]}
    else:
        return None
    
def get_product_info(ean):
    conn = get_db_connection()
    produto = conn.execute(text("SELECT * FROM produtos WHERE ean = :ean"), {"ean": ean}).fetchone()
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
    with get_db_connection() as conn:
        for _, row in df_csv.iterrows():
            ean = str(row['ean']).strip()
            descricao = str(row['descricao']).strip()

            existente = conn.execute(
                text("SELECT descricao FROM produtos WHERE ean = :ean"),
                {"ean": ean}
            ).fetchone()

            if existente:
                if existente['descricao'] != descricao:
                    conn.execute(
                        text(
                            "UPDATE produtos SET descricao = :descricao WHERE ean = :ean"),
                        {"descricao": descricao, "ean": ean}
                    )
            else:
                conn.execute(
                    text(
                        "INSERT INTO produtos (ean, descricao) VALUES (:ean, :descricao)"),
                    {"ean": ean, "descricao": descricao}
                )



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
