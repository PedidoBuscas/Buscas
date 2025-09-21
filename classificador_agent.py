import re
import PyPDF2
import streamlit as st
import json
from typing import List, Dict
import unicodedata


@st.cache_resource(ttl=3600)  # Cache por 1 hora
def carregar_classificador_inpi_json(json_path: str = "classificador_inpi_corrigido.json") -> List[Dict[str, str]]:
    """Carrega o classificador INPI com cache otimizado"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar classificador: {e}")
        return []


def remover_acentos(texto: str) -> str:
    """Remove acentos de um texto"""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


@st.cache_data(ttl=300)  # Cache por 5 minutos
def buscar_no_classificador(termo: str, especificacoes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Busca um termo nas especificações do classificador INPI.
    Retorna uma lista de dicionários [{classe, especificacao}] com o texto exato do JSON.
    Agora ignora acentos e maiúsculas/minúsculas.
    """
    if not termo or len(termo) < 1:
        return []

    termo_normalizado = remover_acentos(termo.lower())
    resultados = []

    for item in especificacoes:
        especificacao_normalizada = remover_acentos(
            item["especificacao"].lower())

        # Se o termo é um número, buscar por "número - " ou "número " no início
        if termo.isdigit():
            if especificacao_normalizada.startswith(f"{termo_normalizado} - ") or especificacao_normalizada.startswith(f"{termo_normalizado} "):
                resultados.append(item)
        else:
            # Para outros termos, buscar normalmente (incluindo classes de 1 dígito)
            if termo_normalizado in especificacao_normalizada:
                resultados.append(item)

    return resultados
