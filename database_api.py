import streamlit as st
import hashlib
import pandas as pd
from supabase import create_client, Client
import os

# Conexão com Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- AUTENTICAÇÃO E USUÁRIOS ---

# 🧂 Função para hashear senha
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 🔑 Verifica login


def check_login(username, password):
    hashed = hash_password(password)
    res = supabase.table("usuarios").select(
        "*").eq("username", username).eq("password", hashed).execute()
    data = res.data
    if data and len(data) > 0:
        return {
            "uid": data[0]["uid"],
            "role": data[0]["role"],
            "username": data[0]["username"]
        }
    return None

# 🧠 Verifica se existe um admin no sistema


def admin_exists():
    res = supabase.table("usuarios").select(
        "*").eq("role", "admin").limit(1).execute()
    return bool(res.data and len(res.data) > 0)

# 📝 Cria novo usuário, evitando duplicidade


def create_user(username, password, role):
    hashed = hash_password(password)
    try:
        existing = supabase.table("usuarios").select(
            "username").eq("username", username).execute()
        if existing.data and len(existing.data) > 0:
            return False  # Já existe
        supabase.table("usuarios").insert({
            "username": username,
            "password": hashed,
            "role": role
        }).execute()
        return True
    except Exception as e:
        print("Erro ao criar usuário:", e)
        return False

# 📦 Retorna lista de usernames


def get_all_users():
    try:
        res = supabase.table("usuarios").select("username").execute()
        return [u["username"] for u in res.data]
    except Exception as e:
        print("Erro ao buscar usuários:", e)
        return []

# ❌ Remove um usuário pelo nome


def delete_user(username):
    try:
        supabase.table("usuarios").delete().eq("username", username).execute()
        return True
    except Exception as e:
        print("Erro ao deletar usuário:", e)
        return False


# --- PRODUTOS ---
def get_product_info(ean):
    res = supabase.table("produtos").select("*").eq("ean", ean).execute()
    data = res.data
    if data:
        return {"ean": data[0]["ean"], "descricao": data[0]["descricao"]}
    return None


def add_product(ean, descricao):
    try:
        res = supabase.table("produtos").select("*").eq("ean", ean).execute()
        if not res.data:
            supabase.table("produtos").insert(
                {"ean": ean, "descricao": descricao}).execute()
    except Exception as e:
        print("Erro ao adicionar produto:", e)


def atualizar_produtos_via_csv(df_csv):
    for _, row in df_csv.iterrows():
        ean = str(row["ean"]).strip()
        descricao = str(row["descricao"]).strip()
        res = supabase.table("produtos").select(
            "descricao").eq("ean", ean).execute()
        if res.data:
            if res.data[0]["descricao"] != descricao:
                supabase.table("produtos").update(
                    {"descricao": descricao}).eq("ean", ean).execute()
        else:
            supabase.table("produtos").insert(
                {"ean": ean, "descricao": descricao}).execute()


def comparar_csv_com_banco(df_csv):
    res = supabase.table("produtos").select("ean, descricao").execute()
    df_db = pd.DataFrame(res.data)

    eans_csv = set(df_csv["ean"].astype(str))
    eans_db = set(df_db["ean"].astype(str))

    somente_csv = eans_csv - eans_db
    somente_db = eans_db - eans_csv

    return {
        "no_csv_not_in_db": df_csv[df_csv["ean"].astype(str).isin(somente_csv)],
        "no_db_not_in_csv": df_db[df_db["ean"].astype(str).isin(somente_db)]
    }


# --- CONTAGEM DE ESTOQUE ---
def add_or_update_count(username, ean, quantidade):
    res = supabase.table("contagens").select(
        "*").eq("username", username).eq("ean", ean).execute()
    if res.data:
        qtd_atual = res.data[0]["quantidade"]
        nova_qtd = qtd_atual + quantidade
        supabase.table("contagens").update({
            "quantidade": nova_qtd
        }).eq("username", username).eq("ean", ean).execute()
    else:
        supabase.table("contagens").insert({
            "username": username,
            "ean": ean,
            "quantidade": quantidade
        }).execute()


def get_total_count(ean):
    res = supabase.table("contagens").select(
        "quantidade").eq("ean", ean).execute()
    total = sum([item["quantidade"] for item in res.data])
    return total


def get_all_counts():
    contagens = supabase.table("contagens").select("*").execute().data
    produtos = supabase.table("produtos").select("*").execute().data
    df_cont = pd.DataFrame(contagens)
    df_prod = pd.DataFrame(produtos)

    if df_cont.empty or df_prod.empty:
        return pd.DataFrame()

    df = df_cont.merge(df_prod, on="ean", how="left")
    return df[["username", "ean", "descricao", "quantidade", "timestamp"]] if "timestamp" in df.columns else df
