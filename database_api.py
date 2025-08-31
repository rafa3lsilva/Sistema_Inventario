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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


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
    """Lista todos os utilizadores do sistema usando os poderes de admin."""
    try:
        res = supabase_admin.auth.admin.list_users()
        # --- CORREÇÃO PRINCIPAL AQUI ---
        # A função agora retorna a lista de utilizadores diretamente.
        return res
    except Exception as e:
        st.error(f"Erro ao listar utilizadores: {e}")
        return []


def delete_user_by_id(user_id):
    """Apaga um utilizador pelo seu ID usando os poderes de admin."""
    try:
        # Usamos o cliente supabase_admin para esta operação
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
    """
    Função otimizada que insere ou atualiza produtos em massa no Supabase.
    """
    if df_csv.empty:
        print("Nenhum produto para atualizar.")
        return

    # Passo 1: Preparar a lista de produtos
    # Convertemos o DataFrame do pandas para uma lista de dicionários,
    # que é o formato que o Supabase espera.
    produtos_para_enviar = []
    for _, row in df_csv.iterrows():
        ean_limpo = sanitizar_ean(row.get("ean"))
        if ean_limpo:  # Só adiciona produtos com EAN válido
            produtos_para_enviar.append({
                'ean': ean_limpo,
                'descricao': str(row.get("descricao", "")).strip(),
                'emb': str(row.get("emb", "")).strip(),
                'secao': str(row.get("secao", "")).strip(),
                'grupo': str(row.get("grupo", "")).strip(),
            })

    if not produtos_para_enviar:
        print("Nenhum produto válido encontrado para enviar.")
        return

    try:
        # Passo 2: Enviar todos os produtos de uma só vez
        # O comando 'upsert' é muito poderoso:
        # - Se um produto com o mesmo 'ean' já existe, ele ATUALIZA os dados.
        # - Se não existe, ele INSERE um novo produto.
        # Tudo isto numa única chamada à API, evitando o erro de conexão.
        supabase.table("produtos").upsert(produtos_para_enviar).execute()

        print(
            f"Sucesso! {len(produtos_para_enviar)} produtos foram enviados em massa para o banco de dados.")

    except Exception as e:
        # Mostra um erro mais detalhado se a operação em massa falhar
        print(f"Erro ao tentar fazer o upsert em massa: {e}")
        # Para depuração, podemos re-tentar um a um para encontrar a linha problemática
        # st.error(f"Ocorreu um erro na atualização em massa: {e}")


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


def get_all_secoes():
    """Busca todas as seções únicas da nova visão 'distinct_secoes'."""
    try:
        res = supabase.table("distinct_secoes").select("secao").execute()
        return [item['secao'] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar seções: {e}")
        return []


def get_all_grupos():
    """Busca todos os grupos únicos da nova visão 'distinct_grupos'."""
    try:
        res = supabase.table("distinct_grupos").select("grupo").execute()
        return [item['grupo'] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar grupos: {e}")
        return []


def get_all_embs():
    """Busca todas as embalagens únicas da nova visão 'distinct_embs'."""
    try:
        res = supabase.table("distinct_embs").select("emb").execute()
        return [item['emb'] for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Erro ao buscar embalagens: {e}")
        return []


def update_count_by_id(count_id: int, new_quantity: int):
    """Atualiza a quantidade de uma contagem específica pelo seu ID."""
    try:
        supabase.table("contagens").update(
            {"quantidade": new_quantity}).eq("id", count_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar contagem: {e}")
        return False


def delete_count_by_id(count_id: int):
    """Deleta uma contagem específica pelo seu ID."""
    try:
        supabase.table("contagens").delete().eq("id", count_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar contagem: {e}")
        return False


def delete_all_counts_by_user(user_uid: str):
    """Deleta todas as contagens de um utilizador específico."""
    try:
        # Usamos o cliente admin para garantir a permissão
        supabase_admin.table("contagens").delete().eq(
            "usuario_uid", user_uid).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar contagens do usuário: {e}")
        return False


def delete_all_counts():
    """Deleta TODAS as contagens do banco de dados."""
    try:
        # Usamos o cliente admin para garantir a permissão
        supabase_admin.table("contagens").delete().gt("id", 0).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar todas as contagens: {e}")
        return False
