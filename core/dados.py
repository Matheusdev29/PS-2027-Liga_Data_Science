"""core/dados.py - Inscrições guardadas numa planilha do Google Sheets.

Duas funções públicas:

    salvar_inscricao(dicionario)   -> acrescenta uma linha no fim da planilha
    ler_inscricoes()               -> DataFrame com todas as inscrições

A planilha é acessada por uma Service Account. Nada de credencial fica no código:
tudo vem de `.streamlit/secrets.toml` (lido com `st.secrets`), neste formato:

    [gcp_service_account]          # conteúdo do JSON da chave, campo a campo
    type = "service_account"
    project_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
    client_email = "...@....iam.gserviceaccount.com"
    ...

    [planilha]
    id = "ID ou link da planilha"
    aba = "Inscricoes"             # opcional; sem isso usa a primeira aba

A planilha precisa estar COMPARTILHADA (como Editor) com o `client_email` da
Service Account. A linha 1 da aba é o cabeçalho; as chaves do dicionário devem
ser iguais aos nomes das colunas. Se a aba estiver vazia, o cabeçalho é criado
a partir das chaves da primeira inscrição.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

import gspread
import pandas as pd
import streamlit as st
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound

# Só o escopo de planilhas (não pede acesso a todo o Drive).
ESCOPOS = ["https://www.googleapis.com/auth/spreadsheets"]

SECRET_CONTA = "gcp_service_account"
SECRET_PLANILHA = "planilha"


# --------------------------------------------------------------------------- #
# Conexão (credenciais vêm de st.secrets)
# --------------------------------------------------------------------------- #

def _extrair_id(valor: str) -> str:
    """Aceita o ID puro ou o link completo da planilha."""
    achado = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", str(valor))
    return achado.group(1) if achado else str(valor).strip()


def _config() -> tuple[dict, dict]:
    """Lê (conta de serviço, config da planilha) de st.secrets, com erro claro."""
    try:
        conta = dict(st.secrets[SECRET_CONTA])
        planilha = dict(st.secrets[SECRET_PLANILHA])
        planilha["id"]
    except (KeyError, FileNotFoundError) as erro:
        raise RuntimeError(
            "Credenciais não encontradas. Crie .streamlit/secrets.toml com as seções "
            f"[{SECRET_CONTA}] (chave da Service Account) e [{SECRET_PLANILHA}] "
            "(com `id`). Veja .streamlit/secrets.toml.example."
        ) from erro
    return conta, planilha


@st.cache_resource(show_spinner=False)
def _aba():
    """Abre a aba da planilha uma vez e reaproveita a conexão entre execuções."""
    conta, planilha = _config()
    cliente = gspread.service_account_from_dict(conta, scopes=ESCOPOS)
    try:
        arquivo = cliente.open_by_key(_extrair_id(planilha["id"]))
    except SpreadsheetNotFound as erro:
        raise RuntimeError(
            "Planilha não encontrada. Confira o `id` em [planilha] e compartilhe-a "
            f"(como Editor) com {conta.get('client_email', 'a Service Account')}."
        ) from erro

    nome = planilha.get("aba")
    if not nome:
        return arquivo.sheet1
    try:
        return arquivo.worksheet(nome)
    except WorksheetNotFound as erro:
        raise RuntimeError(f"A aba '{nome}' não existe na planilha.") from erro


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #

def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor)


def cabecalho() -> list[str]:
    """Nomes das colunas (linha 1 da aba); lista vazia se a aba estiver vazia."""
    return [c.strip() for c in _aba().row_values(1)]


def salvar_inscricao(dicionario: Mapping[str, Any]) -> None:
    """Acrescenta uma inscrição no fim da planilha.

    Os valores são colocados na coluna de mesmo nome (a ordem do dicionário não
    importa); coluna sem valor fica vazia. Chave que não existe no cabeçalho gera
    ValueError e nada é gravado, para não perder dado em silêncio.

    Os valores entram como texto puro (RAW): "=1+1" ou "007" ficam como foram
    digitados, sem virar fórmula nem perder zeros à esquerda.
    """
    if not dicionario:
        raise ValueError("A inscrição está vazia.")

    aba = _aba()
    colunas = [c.strip() for c in aba.row_values(1)]
    if not any(colunas):  # aba vazia: cria o cabeçalho com as chaves recebidas
        colunas = [str(k) for k in dicionario]
        aba.append_row(colunas, value_input_option="RAW")

    desconhecidas = [str(k) for k in dicionario if k not in colunas]
    if desconhecidas:
        raise ValueError(
            f"Campos que não existem na planilha: {', '.join(desconhecidas)}. "
            f"Colunas disponíveis: {', '.join(c for c in colunas if c)}."
        )

    linha = [_texto(dicionario.get(c, "")) for c in colunas]
    aba.append_row(linha, value_input_option="RAW")
    ler_inscricoes.clear()  # a próxima leitura já traz a linha nova


@st.cache_data(ttl=30, show_spinner=False)
def ler_inscricoes() -> pd.DataFrame:
    """Todas as inscrições como DataFrame (colunas = cabeçalho da planilha).

    Tudo vem como texto, então CPF/telefone não perdem zeros à esquerda. O
    resultado fica em cache por 30 s (limite de leituras da API do Google) e é
    renovado na hora quando `salvar_inscricao` grava.
    """
    valores = _aba().get_all_values()
    if not valores:
        return pd.DataFrame()

    cab, *linhas = valores
    largura = len(cab)
    linhas = [(l + [""] * (largura - len(l)))[:largura] for l in linhas if any(l)]
    return pd.DataFrame(linhas, columns=cab)
