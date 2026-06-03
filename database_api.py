import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import re



# --- CONEXÃO COM SUPABASE ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_KEY"))

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


def reset_password_request(email):
    try:
        return supabase.auth.reset_password_for_email(email)
    except Exception as e:
        st.error(f"Erro ao solicitar redefinição: {e}")
        return None


def update_user_password(new_password):
    try:
        return supabase.auth.update_user({"password": new_password})
    except Exception as e:
        st.error(f"Erro ao atualizar a senha: {e}")
        return None


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


def carregar_relatorio_sistema(arquivo):
    """Lê e normaliza o CSV do sistema; valida colunas e consolida possíveis duplicidades no sistema."""
    colunas_necessarias = ['Código', 'Descrição', 'Estoque', 'Quebra 2']
    df = pd.read_csv(arquivo, sep=';', encoding='latin1', decimal=',')
    faltando = [c for c in colunas_necessarias if c not in df.columns]
    if faltando:
        raise KeyError(f"Colunas ausentes no relatório: {faltando}")

    coluna_de_dados = df['Quebra 2'].astype(str)
    df['secao'] = coluna_de_dados.str.extract(
        r'Seç[ãa]o:\s*\d+\s*-\s*(.*?)(?:Grupo:|$)', expand=False
    ).str.strip()
    df['grupo'] = coluna_de_dados.str.extract(
        r'Grupo:\s*\d+\s*-\s*(.*)', expand=False
    ).str.strip()

    df['grupo'].fillna('', inplace=True)
    df['secao'].fillna(method='ffill', inplace=True)
    df['grupo'].fillna(method='ffill', inplace=True)
    df.dropna(subset=['Código'], inplace=True)

    df.rename(columns={
        'Código': 'ean',
        'Descrição': 'descricao',
        'Estoque': 'estoque_sistema'
    }, inplace=True)
    df['ean'] = df['ean'].astype(str)

    # Se o sistema tiver mesmas linhas repetidas para um EAN, consolidamos somando o estoque.
    df_sistema = df.groupby('ean', as_index=False).agg({
        'descricao': 'first',
        'secao': 'first',
        'grupo': 'first',
        'estoque_sistema': 'sum'
    })

    return df_sistema


def carregar_contagens_consolidadas():
    """Lê as contagens do banco e consolida somando por EAN.
       Retorna (df_consolidado, n_linhas_originais, n_eans_unicos).
    """
    contagens_resultado = get_all_contagens_detalhado()
    df = pd.DataFrame(contagens_resultado.data)

    if df.empty:
        return pd.DataFrame(columns=['ean', 'estoque_contado']), 0, 0

    df.rename(columns={'quantidade': 'estoque_contado'}, inplace=True)
    # Mantemos só ean e quantidade (caso tenha mais colunas, ignoramos aqui)
    df = df[['ean', 'estoque_contado']].copy()
    n_linhas = len(df)
    df_group = df.groupby('ean', as_index=False)['estoque_contado'].sum()
    n_unicos = len(df_group)

    return df_group, n_linhas, n_unicos
