import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import bcrypt
import uuid
import re
import toml


# Carrega secrets do arquivo se rodando fora do Streamlit
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    secrets_path = os.path.join(
        os.path.dirname(__file__), ".streamlit", "secrets.toml"
    )
    if not os.path.exists(secrets_path):
        secrets_path = os.path.join(
            os.path.dirname(__file__), "..", ".streamlit", "secrets.toml"
        )
    if os.path.exists(secrets_path):
        secrets = toml.load(secrets_path)
        os.environ["SUPABASE_URL"] = secrets["SUPABASE_URL"]
        os.environ["SUPABASE_KEY"] = secrets["SUPABASE_KEY"]

# Conexão com Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- NOVAS FUNÇÕES DE AUTENTICAÇÃO OFICIAL ---
def sign_up(email, password, username, role='user'):
    """Registra um novo usuário usando o sistema oficial de Auth do Supabase."""
    try:
        res = supabase.auth.sign_up({
            "email": email, "password": password,
            "options": {"data": {"username": username, "role": role}}
        })
        return res
    except Exception as e:
        return e


def sign_in(email, password):
    """Autentica um usuário, criando uma sessão oficial que o Supabase reconhece."""
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": email, "password": password})
        # Esta linha é a mais importante: ela "carimba o pulso" do usuário.
        supabase.auth.set_session(
            res.session.access_token, res.session.refresh_token)
        return res.user
    except Exception:
        return None


def get_user_role(user):
    return user.user_metadata.get('role', 'user') if user and user.user_metadata else 'user'


def get_username(user):
    return user.user_metadata.get('username', '') if user and user.user_metadata else ''


def sign_out():
    supabase.auth.sign_out()

# --- FUNÇÕES DE USUÁRIOS (SIMPLIFICADAS) ---
def get_all_users():
    return []  # Requer privilégios de admin para ser implementado corretamente


def delete_user(username):
    st.warning(
        "A funcionalidade de apagar usuários precisa ser reimplementada com o novo sistema.")
    return False


# --- PRODUTOS ---
def sanitizar_ean(ean_raw):
    if ean_raw is None:
        return None
    ean = str(ean_raw).strip().replace("\n", "").replace(
        "\t", "").replace("\r", "").replace("'", "").replace('"', "")
    try:
        ean = ean.replace(",", ".")
        if "e" in ean.lower():
            ean = str(int(float(ean)))
    except ValueError:
        pass
    ean = re.sub(r"\D", "", ean)
    if len(ean) > 13:
        ean = ean[-13:]
    return ean if ean else None


def get_product_info(ean):
    ean_sanitized = sanitizar_ean(ean)
    res = supabase.table("produtos").select(
        "*").eq("ean", ean_sanitized).execute()
    if res.data:
        return res.data[0]
    return None


def add_product(ean, descricao, emb=None, secao=None, grupo=None):
    ean_sanitized = sanitizar_ean(ean)
    if not ean_sanitized:
        st.error("❌ EAN inválido ou ausente. Produto não inserido.")
        return
    try:
        res = supabase.table("produtos").select(
            "ean").eq("ean", ean_sanitized).execute()
        if not res.data:
            supabase.table("produtos").insert({
                "ean": ean_sanitized, "descricao": str(descricao).strip(),
                "emb": str(emb).strip(), "secao": str(secao).strip(), "grupo": str(grupo).strip()
            }).execute()
            st.success(f"✅ Produto adicionado: {ean_sanitized} - {descricao}")
        else:
            st.warning(f"🔄 Produto já existe: {ean_sanitized}")
    except Exception as e:
        st.error(f"❌ Erro ao adicionar produto {ean_sanitized}: {e}")


def atualizar_produtos_via_csv(df_csv):
    for _, row in df_csv.iterrows():
        ean = sanitizar_ean(row.get("ean"))
        if not ean:
            continue
        descricao = str(row.get("descricao", "")).strip()
        emb = str(row.get("emb", "")).strip()
        secao = str(row.get("secao", "")).strip()
        grupo = str(row.get("grupo", "")).strip()

        res = supabase.table("produtos").select(
            "descricao", "emb", "secao", "grupo").eq("ean", ean).execute()
        if res.data:
            existente = res.data[0]
            if (str(existente.get("descricao", "")).strip() != descricao or
                str(existente.get("emb", "")).strip() != emb or
                str(existente.get("secao", "")).strip() != secao or
                    str(existente.get("grupo", "")).strip() != grupo):
                supabase.table("produtos").update({
                    "descricao": descricao, "emb": emb, "secao": secao, "grupo": grupo
                }).eq("ean", ean).execute()
        else:
            supabase.table("produtos").insert({
                "ean": ean, "descricao": descricao, "emb": emb, "secao": secao, "grupo": grupo
            }).execute()


def comparar_produtos_com_banco(df_produtos):
    df_produtos.columns = [col.lower().strip() for col in df_produtos.columns]
    df_produtos["ean"] = df_produtos["ean"].apply(sanitizar_ean)
    res = supabase.table("produtos").select(
        "ean", "descricao", "emb", "secao", "grupo").execute()
    df_banco = pd.DataFrame(res.data or [])
    if df_banco.empty:
        return {"novos": df_produtos, "ausentes": pd.DataFrame(), "divergentes": pd.DataFrame()}

    df_banco.columns = [col.lower().strip() for col in df_banco.columns]
    df_banco["ean"] = df_banco["ean"].apply(sanitizar_ean)
    novos = df_produtos[~df_produtos["ean"].isin(df_banco["ean"])]
    ausentes = df_banco[~df_banco["ean"].isin(df_produtos["ean"])]

    for col in ["descricao", "emb", "secao", "grupo"]:
        df_produtos[col] = df_produtos[col].astype(str).str.lower().str.strip()
        df_banco[col] = df_banco[col].astype(str).str.lower().str.strip()

    df_merged = pd.merge(df_produtos, df_banco, on="ean",
                         suffixes=("_arquivo", "_banco"))
    divergentes = df_merged[
        (df_merged["descricao_arquivo"] != df_merged["descricao_banco"]) |
        (df_merged["emb_arquivo"] != df_merged["emb_banco"]) |
        (df_merged["secao_arquivo"] != df_merged["secao_banco"]) |
        (df_merged["grupo_arquivo"] != df_merged["grupo_banco"])
    ]
    return {"novos": novos, "ausentes": ausentes, "divergentes": divergentes}


def add_or_update_count(usuario_uid, ean, quantidade):
    ean_sanitized = sanitizar_ean(ean)
    try:
        qty = int(quantidade)
        if qty < 0:
            return
    except (ValueError, TypeError):
        return
    if not ean_sanitized:
        return

    res = supabase.table("contagens").select(
        "*").eq("usuario_uid", usuario_uid).eq("ean", ean_sanitized).execute()
    if res.data:
        nova_qtd = res.data[0]["quantidade"] + qty
        supabase.table("contagens").update({"quantidade": nova_qtd}).eq(
            "usuario_uid", usuario_uid).eq("ean", ean_sanitized).execute()
    else:
        supabase.table("contagens").insert(
            {"usuario_uid": usuario_uid, "ean": ean_sanitized, "quantidade": qty}).execute()


def get_all_contagens_detalhado():
    return supabase.table("contagens_detalhadas").select("*").execute()


def produto_existe(ean):
    ean_sanitized = sanitizar_ean(ean)
    if not ean_sanitized:
        return False
    res = supabase.table("produtos").select(
        "ean").eq("ean", ean_sanitized).execute()
    return bool(res.data)


def get_all_products_df():
    response = supabase.table("produtos").select("*").execute()
    return pd.DataFrame(response.data or [])
