import streamlit as st
# import hashlib
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
    # Procura na pasta raiz do projeto
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

# 🧂 Função para bcrypt senha


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# 🔑 Verifica login


def check_login(username, password):
    res = supabase.table("usuarios").select(
        "*").eq("username", username).execute()
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

# 🧠 Verifica se existe um admin no sistema


def get_all_admins():
    res = supabase.table("usuarios").select(
        "username").eq("role", "admin").execute()
    return res.data


def has_admin():
    res = supabase.table("usuarios").select("id").eq("role", "admin").execute()
    return bool(res.data) and len(res.data) > 0


# 📝 Cria novo usuário, evitando duplicidade


def create_user(username, password, role):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        # Se for admin, verifica se já existe um
        if role == "admin":
            res = supabase.table("usuarios").select(
                "id").eq("role", "admin").execute()
            if res.data and len(res.data) >= 1:
                return False

        # Verifica se o usuário já existe
        existing = supabase.table("usuarios").select(
            "username").eq("username", username).execute()
        if existing.data and len(existing.data) > 0:
            return False  # Username já em uso

        uid_gerado = str(uuid.uuid4())
        supabase.table("usuarios").insert({
            "username": username,
            "password": hashed,
            "role": role,
            "uid": uid_gerado
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
        res = supabase.table("usuarios").delete().eq(
            "username", username).execute()
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
    """
    Sanitiza o código EAN, corrigindo notação científica, espaços, caracteres ocultos,
    aspas e convertendo para string limpa e segura.
    """
    if ean_raw is None:
        return None

    # 1. Converte para string e remove espaços invisíveis e aspas
    ean = str(ean_raw).strip().replace(
        "\n", "").replace("\t", "").replace("\r", "")
    ean = ean.replace("'", "").replace(
        '"', "")  # Remove aspas simples e duplas

    # 2. Corrige notação científica, se vier como float em string (ex: '7.89284e+12')
    try:
        # Remove vírgula do decimal brasileiro, se houver
        ean = ean.replace(",", ".")
        if "e" in ean.lower():
            ean_num = float(ean)
            ean = str(int(ean_num))
    except ValueError:
        pass  # Se falhar, ignora e mantém como string original

    # 3. Remove quaisquer caracteres não numéricos
    ean = re.sub(r"\D", "", ean)

    # 4. Garante que não ultrapasse 13 dígitos (EAN-13)
    if len(ean) > 13:
        ean = ean[-13:]

    # 5. Retorna EAN sanitizado ou None se vazio
    return ean if ean else None


def get_product_info(ean):
    """
    Consulta produto pelo EAN.
    """
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

        # 🔍 Verifica se já existe no banco
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

    # 🧾 Relatório final
    if eans_invalidos:
        print(f"\n🚨 EANs inválidos encontrados: {len(eans_invalidos)}")
        for item in eans_invalidos:
            print(f"❌ Linha inválida: {item}")


def comparar_produtos_com_banco(df_produtos):
    # 🧼 Normaliza colunas
    df_produtos.columns = [col.lower().strip() for col in df_produtos.columns]

    # 🧼 Aplica sanitização ao EAN
    df_produtos["ean"] = df_produtos["ean"].apply(sanitizar_ean)

    # 🔍 Busca do banco
    res = supabase.table("produtos").select(
        "ean", "descricao", "emb", "secao", "grupo").execute()

    df_banco = pd.DataFrame(res.data or [])
    df_banco.columns = [col.lower().strip() for col in df_banco.columns]
    df_banco["ean"] = df_banco["ean"].apply(sanitizar_ean)

    # 🆕 Produtos no arquivo que não estão no banco
    novos = df_produtos[~df_produtos["ean"].isin(df_banco["ean"])]

    # 📍 Produtos no banco que não estão no arquivo
    ausentes = df_banco[~df_banco["ean"].isin(df_produtos["ean"])]

    # 🔁 Normaliza texto para comparação de conteúdo
    for col in ["descricao", "emb", "secao", "grupo"]:
        df_produtos[col] = df_produtos[col].astype(str).str.lower().str.strip()
        df_banco[col] = df_banco[col].astype(str).str.lower().str.strip()

    # 🔄 Produtos com EAN em comum mas dados divergentes
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

    # ✅ Proteção contra valores inválidos
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

    # 🔍 Verifica se já existe contagem para esse usuário e EAN
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
    """
    Retorna todos os produtos como DataFrame.
    """
    response = supabase.table("produtos").select("*").execute()
    data = response.data
    return pd.DataFrame(data)
