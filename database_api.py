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


def atualizar_produtos_via_csv(df: pd.DataFrame) -> None:
    """
    Insere ou atualiza produtos no banco Supabase a partir de um DataFrame.
    O DataFrame deve conter as colunas: ean, descricao, emb, secao, grupo.
    """
    try:
        if df.empty:
            print("⚠️ Nenhum produto para atualizar.")
            return

        # Garante colunas necessárias
        colunas = ["ean", "descricao", "emb", "secao", "grupo"]
        for col in colunas:
            if col not in df.columns:
                df[col] = ""

        # Converte para lista de dicionários (payload para Supabase)
        registros = df[colunas].to_dict(orient="records")

        # UPSERT = insere novos ou atualiza se já existir (pela PK = ean)
        supabase.table("produtos").upsert(
            registros, on_conflict=["ean"]).execute()

        print(f"✅ {len(registros)} produtos inseridos/atualizados com sucesso.")

    except Exception as e:
        print(f"❌ Erro ao atualizar produtos no banco: {e}")



def get_all_produtos() -> pd.DataFrame:
    """
    Busca todos os produtos no banco Supabase e retorna como DataFrame
    com as colunas: ean, descricao, emb, secao, grupo
    """
    try:
        response = supabase.table("produtos").select(
            "ean, descricao, emb, secao, grupo"
        ).execute()

        if not response.data:
            return pd.DataFrame(columns=["ean", "descricao", "emb", "secao", "grupo"])

        df = pd.DataFrame(response.data)

        # Garantir que todas as colunas existam
        for col in ["ean", "descricao", "emb", "secao", "grupo"]:
            if col not in df.columns:
                df[col] = ""

        return df[["ean", "descricao", "emb", "secao", "grupo"]]

    except Exception as e:
        print(f"Erro ao buscar produtos no banco: {e}")
        return pd.DataFrame(columns=["ean", "descricao", "emb", "secao", "grupo"])

def comparar_produtos_com_banco(df_csv: pd.DataFrame) -> dict:
    """
    Compara os produtos do CSV com os produtos do banco.
    Retorna um dicionário com dataframes: 'novos', 'ausentes', 'divergentes'.
    """

    # 🔎 Normalização de EAN no CSV (mantém qualquer tamanho, só dígitos)
    df_csv = df_csv.copy()
    df_csv["ean"] = (
        df_csv["ean"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )

    # 1. Carregar produtos do banco
    # precisa retornar um DataFrame com colunas [ean, descricao, emb, secao, grupo]
    df_db = get_all_produtos()

    # 🔎 Normalização de EAN no banco
    df_db["ean"] = (
        df_db["ean"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )

    # 2. Garantir colunas necessárias
    colunas = ["ean", "descricao", "emb", "secao", "grupo"]
    df_csv = df_csv[colunas].drop_duplicates(subset=["ean"])
    df_db = df_db[colunas].drop_duplicates(subset=["ean"])

    # 3. Identificar produtos novos (presentes no CSV mas não no banco)
    novos = df_csv[~df_csv["ean"].isin(df_db["ean"])]

    # 4. Identificar produtos ausentes (presentes no banco mas não no CSV)
    ausentes = df_db[~df_db["ean"].isin(df_csv["ean"])]

    # 5. Identificar divergentes (mesmo EAN mas com diferença em pelo menos 1 campo)
    merged = pd.merge(df_csv, df_db, on="ean", how="inner",
                      suffixes=("_arquivo", "_banco"))
    divergentes = merged[
        (merged["descricao_arquivo"] != merged["descricao_banco"])
        | (merged["emb_arquivo"] != merged["emb_banco"])
        | (merged["secao_arquivo"] != merged["secao_banco"])
        | (merged["grupo_arquivo"] != merged["grupo_banco"])
    ]

    return {
        "novos": novos,
        "ausentes": ausentes,
        "divergentes": divergentes,
    }

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
