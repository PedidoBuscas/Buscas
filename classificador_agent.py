import re
import PyPDF2
import streamlit as st
import json
from typing import List, Dict
import unicodedata


@st.cache_resource
def carregar_classificador_inpi_json(json_path: str = "classificador_inpi_corrigido.json") -> List[Dict[str, str]]:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def remover_acentos(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def buscar_no_classificador(termo: str, especificacoes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Busca um termo nas especificações do classificador INPI.
    Retorna uma lista de dicionários [{classe, especificacao}] com o texto exato do JSON.
    Agora ignora acentos e maiúsculas/minúsculas.
    """
    termo_normalizado = remover_acentos(termo.lower())
    resultados = [
        item for item in especificacoes if termo_normalizado in remover_acentos(item["especificacao"].lower())]
    return resultados
