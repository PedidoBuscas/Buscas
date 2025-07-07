import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import streamlit as st
import logging

# Carrega variáveis do .env (caso não tenha sido carregado no app principal)
load_dotenv()


class SupabaseAgent:
    """
    Agente responsável por autenticação, manipulação de perfis e buscas no Supabase.
    """

    def __init__(self):
        """
        Inicializa o cliente Supabase usando variáveis de ambiente.
        """
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL e SUPABASE_KEY devem estar definidos no .env")
        self.client: Client = create_client(url, key)

    def login(self, email: str, password: str):
        """
        Realiza login no Supabase e retorna o usuário e o JWT token se bem-sucedido.
        """
        resp = self.client.auth.sign_in_with_password(
            {"email": email, "password": password})
        jwt_token = None
        if hasattr(resp, "session") and resp.session:
            jwt_token = resp.session.access_token
        return resp.user if resp.user else None, jwt_token

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca o perfil do usuário pelo ID.
        """
        resp = self.client.table("profiles").select(
            "*").eq("id", user_id).single().execute()
        return resp.data if resp.data else None

    def update_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Atualiza o perfil do usuário com os dados fornecidos.
        """
        resp = self.client.table("profiles").update(
            data).eq("id", user_id).execute()
        if not resp.data:
            st.warning("Erro ao atualizar perfil: resposta vazia do Supabase.")
            logging.error(
                "Erro ao atualizar perfil: resposta vazia do Supabase.")
            return False
        return True

    def insert_busca(self, busca_data: Dict[str, Any]) -> bool:
        """
        Insere uma nova busca na tabela 'buscas' usando o SDK do Supabase.
        """
        # Diagnóstico: imprimir usuário autenticado
        st.write("Usuário autenticado pelo supabase-py:",
                 self.client.auth.get_user())
        resp = self.client.table("buscas").insert(busca_data).execute()
        if not resp.data:
            st.warning(
                "Erro ao inserir no Supabase: resposta vazia do Supabase.")
            logging.error(
                "Erro ao inserir no Supabase: resposta vazia do Supabase.")
            return False
        return True

    def _get_headers(self, jwt_token: str, content_type: bool = False) -> dict:
        """
        Gera os headers necessários para requisições REST ao Supabase.
        """
        headers = {
            "apikey": os.getenv("SUPABASE_KEY"),
            "Authorization": f"Bearer {jwt_token}",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def insert_busca_rest(self, busca_data: Dict[str, Any], jwt_token: str) -> bool:
        """
        Insere uma nova busca na tabela 'buscas' via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas"
        headers = self._get_headers(jwt_token, content_type=True)
        resp = requests.post(url, headers=headers, json=busca_data)
        if resp.status_code != 201:
            st.warning(f"Erro ao inserir no Supabase: {resp.text}")
            logging.error(f"Erro ao inserir no Supabase: {resp.text}")
            return False
        return True

    def get_buscas_by_consultor(self, consultor_id: str) -> List[Dict[str, Any]]:
        """
        Busca todas as buscas associadas a um consultor pelo ID.
        """
        resp = self.client.table("buscas").select(
            "*").eq("consultor_id", consultor_id).order("created_at", desc=True).execute()
        return resp.data if resp.data else []

    def get_all_buscas(self) -> List[Dict[str, Any]]:
        """
        Busca todas as buscas cadastradas na tabela 'buscas'.
        """
        resp = self.client.table("buscas").select(
            "*").order("created_at", desc=True).execute()
        return resp.data if resp.data else []

    def get_buscas_rest(self, consultor_id: str, jwt_token: str) -> list:
        """
        Busca todas as buscas associadas a um consultor via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?consultor_id=eq.{consultor_id}&order=created_at.desc"
        headers = self._get_headers(jwt_token)
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.warning(f"Erro ao buscar buscas: {resp.text}")
            logging.error(f"Erro ao buscar buscas: {resp.text}")
            return []

    def delete_busca_rest(self, busca_id: str, jwt_token: str) -> bool:
        """
        Deleta uma busca pelo ID via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?id=eq.{busca_id}"
        headers = self._get_headers(jwt_token)
        resp = requests.delete(url, headers=headers)
        if resp.status_code in (200, 204):
            return True
        else:
            st.warning(f"Erro ao deletar busca: {resp.text}")
            logging.error(f"Erro ao deletar busca: {resp.text}")
            return False

    def get_all_buscas_rest(self, jwt_token: str) -> list:
        """
        Busca todas as buscas cadastradas via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?order=created_at.desc"
        headers = self._get_headers(jwt_token)
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.warning(f"Erro ao buscar buscas: {resp.text}")
            logging.error(f"Erro ao buscar buscas: {resp.text}")
            return []

    def update_analise_status(self, busca_id: str, status: bool, jwt_token: str) -> bool:
        """
        Atualiza o campo analise_realizada de uma busca pelo ID via REST API do Supabase.
        Apenas o admin pode executar essa ação (controlado pela política RLS).
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?id=eq.{busca_id}"
        headers = self._get_headers(jwt_token, content_type=True)
        data = {"analise_realizada": status}
        resp = requests.patch(url, headers=headers, json=data)
        return resp.status_code in (200, 204)

# Exemplo de uso:
# agent = SupabaseAgent()
# user = agent.login(email, password)
# perfil = agent.get_profile(user['id'])
