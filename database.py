import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Pega a string de conexão do secrets (segura para uso online)
DATABASE_URL = st.secrets["SUPABASE_URL"]

# Cria engine do SQLAlchemy
engine = create_engine(DATABASE_URL)


def get_all_produtos():
    return pd.read_sql("SELECT * FROM produtos", engine)


def add_or_update_produto(ean, descricao):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO produtos (ean, descricao)
            VALUES (:ean, :descricao)
            ON CONFLICT (ean) DO UPDATE SET descricao = :descricao
        """), {"ean": ean, "descricao": descricao})


def get_all_contagens():
    return pd.read_sql("""
        SELECT c.username, c.ean, p.descricao, c.quantidade, c.timestamp
        FROM contagens c
        JOIN produtos p ON c.ean = p.ean
        ORDER BY c.timestamp DESC
    """, engine)


def add_or_update_contagem(username, ean, quantidade):
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT quantidade FROM contagens
            WHERE username = :username AND ean = :ean
        """), {"username": username, "ean": ean}).fetchone()

        if result:
            nova_qtd = result[0] + quantidade
            conn.execute(text("""
                UPDATE contagens
                SET quantidade = :qtd, timestamp = CURRENT_TIMESTAMP
                WHERE username = :username AND ean = :ean
            """), {"qtd": nova_qtd, "username": username, "ean": ean})
        else:
            conn.execute(text("""
                INSERT INTO contagens (username, ean, quantidade)
                VALUES (:username, :ean, :quantidade)
            """), {"username": username, "ean": ean, "quantidade": quantidade})


def check_login(username, password_hash):
    result = engine.execute(text("""
        SELECT username, role FROM usuarios
        WHERE username = :u AND password = :p
    """), {"u": username, "p": password_hash}).fetchone()
    return dict(result) if result else None


def get_all_users():
    return pd.read_sql("SELECT username, role FROM usuarios", engine)


def create_user(username, password_hash, role="user"):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO usuarios (username, password, role)
                VALUES (:username, :password, :role)
            """), {"username": username, "password": password_hash, "role": role})
        return True
    except:
        return False
