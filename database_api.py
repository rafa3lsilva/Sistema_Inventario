import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import re
import toml


# --- CONEXÃO COM SUPABASE ---
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    secrets_path = os.path.join(os.path.dirname(
        __file__), ".streamlit", "secrets.toml")
    if not os.path.exists(secrets_path):
        secrets_path = os.path.join(os.path.dirname(
            __file__), "..", ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        secrets = toml.load(secrets_path)
        os.environ["SUPABASE_URL"] = secrets["SUPABASE_URL"]
        os.environ["SUPABASE_KEY"] = secrets["SUPABASE_KEY"]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# --- AUTENTICAÇÃO ---
def sign_up(email, password, username, role="user"):
    try:
        return supabase.auth.sign_up({
            "email": email, "password": password,
            "options": {"data": {"username": username, "role": role}}
        })
    except Exception as e:
        return e


def sign_in(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return None


def sign_out():
    supabase.auth.sign_out()


def get_user_role(user):
    return user.user_metadata.get("role", "user") if user and user.user_metadata else "user"


def get_username(user):
    return user.user_metadata.get("username", "") if user and user.user_metadata else ""


def get_all_users():
    try:
        return supabase_admin.auth.admin.list_users()
    except Exception as e:
        st.error(f"Erro ao listar utilizadores: {e}")
        return []


def delete_user_by_id(user_id):
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        return True
    except Exception as e:
        st.error(f"Erro ao apagar utilizador: {e}")
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
    return ean[-13:] if ean and len(ean) > 13 else ean or None


def get_product_info(ean):
    ean_sanitized = sanitizar_ean(ean)
    res = supabase.table("produtos").select(
        "*").eq("ean", ean_sanitized).execute()
    return res.data[0] if res.data else None


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
                "ean": ean_sanitized,
                "descricao": str(descricao).strip(),
                "emb": str(emb or "").strip(),
                "secao": str(secao or "").strip(),
                "grupo": str(grupo or "").strip()
            }).execute()
            st.success(f"✅ Produto adicionado: {ean_sanitized} - {descricao}")
        else:
            st.warning(f"🔄 Produto já existe: {ean_sanitized}")
    except Exception as e:
        st.error(f"❌ Erro ao adicionar produto {ean_sanitized}: {e}")


def atualizar_produtos_via_csv(df_csv):
    if df_csv.empty:
        return
    produtos_para_enviar = []
    for _, row in df_csv.iterrows():
        ean_limpo = sanitizar_ean(row.get("ean"))
        if ean_limpo:
            produtos_para_enviar.append({
                "ean": ean_limpo,
                "descricao": str(row.get("descricao", "")).strip(),
                "emb": str(row.get("emb", "")).strip(),
                "secao": str(row.get("secao", "")).strip(),
                "grupo": str(row.get("grupo", "")).strip(),
            })
    if not produtos_para_enviar:
        return
    try:
        supabase.table("produtos").upsert(produtos_para_enviar).execute()
    except Exception as e:
        print(f"Erro ao atualizar produtos em massa: {e}")


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


# --- CONTAGENS ---
def add_or_update_count(usuario_uid, ean, quantidade: float):
    ean_sanitized = sanitizar_ean(ean)
    if not ean_sanitized:
        st.error("EAN inválido na contagem.")
        return
    try:
        qty_float = float(quantidade)
        if qty_float < 0:
            st.warning("Quantidade não pode ser negativa.")
            return
    except (ValueError, TypeError):
        st.error(f"Quantidade inválida: {quantidade}")
        return

    try:
        res = supabase.table("contagens").select("id, quantidade").eq(
            "usuario_uid", usuario_uid).eq("ean", ean_sanitized).execute()
        if res.data:
            registro_existente = res.data[0]
            nova_qtd = float(registro_existente["quantidade"]) + qty_float
            supabase.table("contagens").update({"quantidade": nova_qtd}).eq(
                "id", registro_existente["id"]).execute()
        else:
            supabase.table("contagens").insert({
                "usuario_uid": usuario_uid,
                "ean": ean_sanitized,
                "quantidade": qty_float
            }).execute()
    except Exception as e:
        st.error(f"Erro ao registrar contagem: {e}")


def get_all_contagens_detalhado():
    return supabase.table("contagens_detalhadas").select("*").execute()


def get_raw_contagens_with_id():
    try:
        result = supabase.table("contagens").select(
            "id, usuario_uid, ean, quantidade, last_updated_at, produtos (ean, descricao, emb, secao, grupo)"
        ).order("last_updated_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"Erro em get_raw_contagens_with_id: {e}")
        return []


def get_relatorio_contagens_completo():
    try:
        res = supabase_admin.table("contagens").select(
            "id, ean, quantidade, last_updated_at, usuario_uid, produtos(descricao, emb, secao, grupo)"
        ).execute()
        return res.data
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return []


def update_count(count_id: int, new_quantity: float, admin: bool = False) -> bool:
    try:
        client = supabase_admin if admin else supabase
        client.table("contagens").update(
            {"quantidade": float(new_quantity)}
        ).eq("id", count_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar contagem: {e}")
        return False

def delete_count_by_id(count_id: int):
    try:
        supabase.table("contagens").delete().eq("id", count_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar contagem: {e}")
        return False


def delete_all_counts_by_user(user_uid: str):
    try:
        supabase_admin.table("contagens").delete().eq(
            "usuario_uid", user_uid).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar contagens do usuário: {e}")
        return False


def delete_all_counts():
    try:
        supabase_admin.table("contagens").delete().neq("id", 0).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar todas as contagens: {e}")
        return False


def delete_contagens_by_ids(ids_list):
    try:
        supabase_admin.table("contagens").delete().in_(
            "id", ids_list).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao apagar registros: {e}")
        return False


# --- CONSULTAS AUXILIARES ---
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


def get_all_secoes():
    try:
        res = supabase.table("distinct_secoes").select("secao").execute()
        return [item["secao"] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar seções: {e}")
        return []


def get_all_grupos():
    try:
        res = supabase.table("distinct_grupos").select("grupo").execute()
        return [item["grupo"] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar grupos: {e}")
        return []


def get_all_embs():
    try:
        res = supabase.table("distinct_embs").select("emb").execute()
        return [item["emb"] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar embalagens: {e}")
        return []

def get_contagens_por_usuario(user_uid: str):
    """
    Busca todos os produtos contados por um utilizador específico,
    juntamente com os detalhes do produto.
    """
    try:
        # Usamos o cliente admin para garantir que a consulta funcione
        # mesmo que as regras de segurança (RLS) fossem mais restritivas.
        res = supabase_admin.table("contagens").select(
            "quantidade, produtos(ean, descricao, emb, secao, grupo)"
        ).eq("usuario_uid", user_uid).execute()

        return res.data
    except Exception as e:
        st.error(f"Erro ao buscar contagens do usuário: {e}")
        return []
