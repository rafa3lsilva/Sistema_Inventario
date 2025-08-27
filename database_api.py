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


# --- AUTENTICAÇÃO E USUÁRIOS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_login(username, password):
    username_lower = username.lower()

    res = supabase.table("usuarios").select(
        "*").eq("username", username_lower).execute()
    data = res.data
    if data and len(data) > 0:
        try:
            hashed_db = data[0]["password"].encode()
            if bcrypt.checkpw(password.encode(), hashed_db):
                return {
                    "uid": data[0]["uid"],
                    "role": data[0]["role"],
                    "username": data[0]["username"]
                }
        except Exception as e:
            print(f"Erro no login: {e}")
    return None


def get_all_admins():
    res = supabase.table("usuarios").select(
        "username").eq("role", "admin").execute()
    return res.data


def has_admin():
    res = supabase.table("usuarios").select("id").eq("role", "admin").execute()
    return bool(res.data) and len(res.data) > 0


def create_user(username, password, role):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    username_lower = username.lower()

    try:
        if role == "admin":
            res = supabase.table("usuarios").select(
                "id").eq("role", "admin").execute()
            if res.data and len(res.data) >= 1:
                return False

        existing = supabase.table("usuarios").select(
            "username").eq("username", username_lower).execute()
        if existing.data and len(existing.data) > 0:
            return False

        uid_gerado = str(uuid.uuid4())
        supabase.table("usuarios").insert({
            "username": username_lower,
            "password": hashed,
            "role": role,
            "uid": uid_gerado
        }).execute()
        return True
    except Exception as e:
        print("Erro ao criar usuário:", e)
        return False


def get_all_users():
    try:
        res = supabase.table("usuarios").select("username").execute()
        return [u["username"] for u in res.data]
    except Exception as e:
        print("Erro ao buscar usuários:", e)
        return []


def delete_user(username):
    try:
        username_lower = username.lower()
        res = supabase.table("usuarios").delete().eq(
            "username", username_lower).execute()
        if res.data and len(res.data) > 0:
            print("Usuário deletado com sucesso!")
            return True
        else:
            print("Nenhum usuário encontrado com esse nome.")
            return False
    except Exception as e:
        print("Erro ao deletar usuário:", e)
        return False


# --- PRODUTOS ---
def sanitizar_ean(ean_raw):
    if ean_raw is None:
        return None
    ean = str(ean_raw).strip().replace(
        "\n", "").replace("\t", "").replace("\r", "")
    ean = ean.replace("'", "").replace(
        '"', "")
    try:
        ean = ean.replace(",", ".")
        if "e" in ean.lower():
            ean_num = float(ean)
            ean = str(int(ean_num))
    except ValueError:
        pass
    ean = re.sub(r"\D", "", ean)
    if len(ean) > 13:
        ean = ean[-13:]
    return ean if ean else None


def get_product_info(ean):
    ean = sanitizar_ean(ean)
    res = supabase.table("produtos").select("*").eq("ean", ean).execute()
    data = res.data
    if data:
        produto = data[0]
        return {
            "ean": str(produto.get("ean", "")),
            "descricao": str(produto.get("descricao", "")),
            "emb": str(produto.get("emb", "")),
            "secao": str(produto.get("secao", "")),
            "grupo": str(produto.get("grupo", ""))
        }
    return None


def add_product(ean, descricao, emb=None, secao=None, grupo=None):
    ean = sanitizar_ean(ean)
    if not ean:
        st.error("❌ EAN inválido ou ausente. Produto não inserido.")
        return

    descricao = str(descricao).strip() if descricao else ""
    emb = str(emb).strip() if emb else ""
    secao = str(secao).strip() if secao else ""
    grupo = str(grupo).strip() if grupo else ""

    try:
        res = supabase.table("produtos").select("ean").eq("ean", ean).execute()
        if not res.data:
            supabase.table("produtos").insert({
                "ean": ean,
                "descricao": descricao,
                "emb": emb,
                "secao": secao,
                "grupo": grupo
            }).execute()
            st.success(f"✅ Produto adicionado: {ean} - {descricao}")
        else:
            st.warning(f"🔄 Produto já existe: {ean}")
    except Exception as e:
        st.error(f"❌ Erro ao adicionar produto {ean}: {e}")


def atualizar_produtos_via_csv(df_csv):
    eans_invalidos = []
    for _, row in df_csv.iterrows():
        ean = sanitizar_ean(row.get("ean"))
        descricao = str(row.get("descricao", "")).strip()
        emb = str(row.get("emb", "")).strip()
        secao = str(row.get("secao", "")).strip()
        grupo = str(row.get("grupo", "")).strip()
        if not ean:
            print(f"❌ EAN inválido na linha: {row.to_dict()}")
            eans_invalidos.append(row.to_dict())
            continue
        res = supabase.table("produtos").select(
            "descricao", "emb", "secao", "grupo").eq("ean", ean).execute()
        if res.data:
            existente = res.data[0]
            precisa_atualizar = (
                str(existente.get("descricao", "")).strip() != descricao or
                str(existente.get("emb", "")).strip() != emb or
                str(existente.get("secao", "")).strip() != secao or
                str(existente.get("grupo", "")).strip() != grupo
            )
            if precisa_atualizar:
                supabase.table("produtos").update({
                    "descricao": descricao,
                    "emb": emb,
                    "secao": secao,
                    "grupo": grupo
                }).eq("ean", ean).execute()
                print(f"🔄 Produto atualizado: {ean} - {descricao}")
            else:
                print(f"⏸️ Produto já está atualizado: {ean}")
        else:
            supabase.table("produtos").insert({
                "ean": ean,
                "descricao": descricao,
                "emb": emb,
                "secao": secao,
                "grupo": grupo
            }).execute()
            print(f"🆕 Produto novo adicionado: {ean} - {descricao}")
    if eans_invalidos:
        print(f"\n🚨 EANs inválidos encontrados: {len(eans_invalidos)}")
        for item in eans_invalidos:
            print(f"❌ Linha inválida: {item}")


def comparar_produtos_com_banco(df_produtos):
    # Normaliza colunas do arquivo de entrada
    df_produtos.columns = [col.lower().strip() for col in df_produtos.columns]
    df_produtos["ean"] = df_produtos["ean"].apply(sanitizar_ean)

    # Busca dados do banco
    res = supabase.table("produtos").select(
        "ean", "descricao", "emb", "secao", "grupo").execute()
    df_banco = pd.DataFrame(res.data or [])

    # --- INÍCIO DA CORREÇÃO ---
    # Se o banco de dados estiver VAZIO, o df_banco não terá colunas.
    # Isso causa o erro 'ean'. Vamos corrigir isso.
    if df_banco.empty:
        # Se o banco está vazio, TODOS os produtos do arquivo são "novos".
        # Os "ausentes" e "divergentes" são DataFrames vazios com as colunas certas.
        colunas_resultado = ['ean', 'descricao_banco',
                             'emb_banco', 'secao_banco', 'grupo_banco']
        return {
            "novos": df_produtos,
            "ausentes": pd.DataFrame(columns=['ean', 'descricao', 'emb', 'secao', 'grupo']),
            "divergentes": pd.DataFrame(columns=colunas_resultado)
        }
    # --- FIM DA CORREÇÃO ---

    # Se o banco não estiver vazio, o código continua como antes.
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

    return {
        "novos": novos,
        "ausentes": ausentes,
        "divergentes": divergentes
    }


# --- CONTAGEM DE ESTOQUE --- 
def add_or_update_count(usuario_uid, ean, quantidade):
    ean = sanitizar_ean(ean)
    try:
        quantidade = int(quantidade)
        if quantidade < 0:
            print(f"❌ Quantidade negativa ignorada para {ean}")
            return
    except ValueError:
        print(f"❌ Quantidade inválida para {ean}: {quantidade}")
        return
    if not ean:
        print("❌ EAN inválido na contagem. Operação ignorada.")
        return
    res = supabase.table("contagens").select(
        "*").eq("usuario_uid", usuario_uid).eq("ean", ean).execute()
    if res.data:
        qtd_atual = res.data[0]["quantidade"]
        nova_qtd = qtd_atual + quantidade
        supabase.table("contagens").update({
            "quantidade": nova_qtd
        }).eq("usuario_uid", usuario_uid).eq("ean", ean).execute()
        print(
            f"🔄 Contagem atualizada: {ean} → +{quantidade} (total: {nova_qtd})")
    else:
        supabase.table("contagens").insert({
            "usuario_uid": usuario_uid,
            "ean": ean,
            "quantidade": quantidade
        }).execute()
        print(f"🆕 Nova contagem registrada: {ean} → {quantidade}")


def get_total_count(ean):
    ean = sanitizar_ean(ean)
    if not ean:
        print("❌ EAN inválido ao consultar total.")
        return 0
    res = supabase.table("contagens").select(
        "quantidade").eq("ean", ean).execute()
    if res.data:
        total = sum([int(item["quantidade"]) for item in res.data])
        print(f"📦 Contagem total para {ean}: {total}")
        return total
    else:
        print(f"📭 Nenhuma contagem para {ean}")
        return 0


def get_all_contagens_detalhado():
    return supabase.table("contagens_detalhadas").select("*").execute()


def produto_existe(ean):
    ean = sanitizar_ean(ean)
    if not ean:
        return False
    res = supabase.table("produtos").select("ean").eq("ean", ean).execute()
    return bool(res.data)


def get_all_products_df():
    response = supabase.table("produtos").select("*").execute()
    data = response.data
    return pd.DataFrame(data)
