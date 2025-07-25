import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import streamlit as st
import logging
import requests
import re
import unicodedata

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
        try:
            import requests

            # Usar REST API com JWT token da sessão ou None
            jwt_token = getattr(st.session_state, 'jwt_token', None)

            # Se não há JWT token, usar apenas apikey (para casos de inicialização)
            if jwt_token:
                headers = {
                    "apikey": os.getenv("SUPABASE_KEY"),
                    "Authorization": f"Bearer {jwt_token}",
                    "Content-Type": "application/json"
                }
            else:
                headers = {
                    "apikey": os.getenv("SUPABASE_KEY"),
                    "Content-Type": "application/json"
                }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/perfil?id=eq.{user_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data and len(data) > 0 else None
            else:
                st.warning(f"Erro ao buscar perfil: {resp.text}")
                return None

        except Exception as e:
            st.error(f"Erro ao buscar perfil: {str(e)}")
            return None

    def update_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Atualiza o perfil do usuário com os dados fornecidos.
        """
        resp = self.client.table('perfil').update(
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
        # Garante que status_busca está presente
        if "status_busca" not in busca_data:
            busca_data["status_busca"] = "pendente"
        # Remove analise_realizada se existir
        busca_data.pop("analise_realizada", None)
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
        # Garante que status_busca está presente
        if "status_busca" not in busca_data:
            busca_data["status_busca"] = "pendente"
        # Remove analise_realizada se existir
        busca_data.pop("analise_realizada", None)
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

    def update_busca_status(self, busca_id: str, status: str, jwt_token: str) -> bool:
        """
        Atualiza o campo status_busca de uma busca pelo ID via REST API do Supabase.
        Apenas usuários autorizados podem executar essa ação.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?id=eq.{busca_id}"
        headers = self._get_headers(jwt_token, content_type=True)
        data = {"status_busca": status}
        resp = requests.patch(url, headers=headers, json=data)
        if resp.status_code in (200, 204):
            return True
        else:
            st.warning(f"Erro ao atualizar status da busca: {resp.text}")
            logging.error(f"Erro ao atualizar status da busca: {resp.text}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza o nome do arquivo removendo caracteres inválidos para armazenamento.
        """
        # Remove acentos
        filename = unicodedata.normalize('NFD', filename)
        filename = ''.join(
            c for c in filename if unicodedata.category(c) != 'Mn')

        # Remove caracteres especiais e substitui por underscore
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Remove underscores múltiplos
        filename = re.sub(r'_+', '_', filename)

        # Remove underscores no início e fim
        filename = filename.strip('_')

        # Garante que o nome não está vazio
        if not filename:
            filename = "arquivo"

        return filename

    def upload_pdf_to_storage(self, file, file_name, jwt_token, bucket="patentepdf"):
        """
        Faz upload de um arquivo PDF para o Supabase Storage via REST API autenticada com o JWT do usuário logado e retorna a URL pública.
        """
        # Sanitiza o nome do arquivo
        sanitized_filename = self._sanitize_filename(file_name)

        url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/{bucket}/{sanitized_filename}"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "apikey": os.getenv("SUPABASE_KEY"),
            "Content-Type": "application/pdf"
        }
        resp = requests.post(url, headers=headers, data=file.getvalue())
        if resp.status_code not in (200, 201):
            st.warning(f"Erro ao fazer upload do PDF: {resp.text}")
            logging.error(f"Erro ao fazer upload do PDF: {resp.text}")
            raise Exception(f"Erro ao fazer upload: {resp.text}")
        # Montar a URL pública conforme padrão do seu bucket
        public_url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{bucket}/{sanitized_filename}"
        return public_url

    def update_busca_pdf_url(self, busca_id, pdf_urls):
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas?id=eq.{busca_id}"

        # Usar JWT token da sessão ou None
        jwt_token = getattr(st.session_state, 'jwt_token', None)

        # Se não há JWT token, usar apenas apikey
        if jwt_token:
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
        else:
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Content-Type": "application/json"
            }

        # Aceita lista de URLs ou string única
        if isinstance(pdf_urls, str):
            data = {"pdf_buscas": [pdf_urls]}
        else:
            data = {"pdf_buscas": pdf_urls}
        resp = requests.patch(url, headers=headers, json=data)
        if resp.status_code not in (200, 204):
            st.warning(f"Erro ao atualizar pdf_buscas: {resp.text}")
            return False
        return True

    def get_funcionario_by_id(self, user_id: str):
        """
        Busca um funcionário pelo ID no Supabase usando REST API com JWT token.
        Args:
            user_id (str): ID do funcionário
        Returns:
            dict: Dados do funcionário ou None se não encontrado
        """
        try:
            import requests

            # Usar REST API com JWT token da sessão ou None
            jwt_token = getattr(st.session_state, 'jwt_token', None)

            # Se não há JWT token, usar apenas apikey (para casos de inicialização)
            if jwt_token:
                headers = {
                    "apikey": os.getenv("SUPABASE_KEY"),
                    "Authorization": f"Bearer {jwt_token}",
                    "Content-Type": "application/json"
                }
            else:
                headers = {
                    "apikey": os.getenv("SUPABASE_KEY"),
                    "Content-Type": "application/json"
                }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/funcionario?id=eq.{user_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data and len(data) > 0 else None
            else:
                st.warning(f"Erro ao buscar funcionário: {resp.text}")
                return None

        except Exception as e:
            st.error(f"Erro ao buscar funcionário: {str(e)}")
            return None

    def get_all_consultores(self):
        resp = self.client.table('perfil').select('*').execute()
        return resp.data if resp.data else []

    def get_consultores_nao_admin(self):
        """
        Busca todos os consultores que não são admin (is_admin = false)
        Returns:
            list: Lista de consultores não-admin
        """
        resp = self.client.table('perfil').select(
            '*').eq('is_admin', False).execute()
        return resp.data if resp.data else []

    def get_consultores_filtrados(self, exclude_ids=None):
        """
        Busca consultores não-admin excluindo IDs específicos
        Args:
            exclude_ids (list): Lista de IDs de consultores a serem excluídos
        Returns:
            list: Lista de consultores filtrados
        """
        consultores = self.get_consultores_nao_admin()

        # Filtra consultores excluídos se a lista for fornecida
        if exclude_ids:
            consultores = [c for c in consultores if c.get(
                'id') not in exclude_ids]

        return consultores

    def get_consultores_por_cargo(self, cargo="consultor"):
        """
        Busca consultores por cargo específico
        Args:
            cargo (str): Cargo desejado (padrão: 'consultor')
        Returns:
            list: Lista de consultores com o cargo especificado
        """
        resp = self.client.table('perfil').select(
            '*').eq('cargo', cargo).execute()
        return resp.data if resp.data else []

    def get_consultores_ativos(self):
        """
        Busca consultores que não são admin e estão ativos (pode ser usado se houver um campo 'ativo' na tabela)
        Returns:
            list: Lista de consultores ativos
        """
        # Se você tiver um campo 'ativo' na tabela perfil, use:
        # resp = self.client.table('perfil').select('*').eq('is_admin', False).eq('ativo', True).execute()

        # Por enquanto, usa a função padrão
        return self.get_consultores_nao_admin()

    def verificar_usuario_funcionario_perfil(self, user_id: str) -> bool:
        """
        Verifica se o usuário existe tanto na tabela perfil quanto na tabela funcionario
        Args:
            user_id (str): ID do usuário
        Returns:
            bool: True se existe em ambas as tabelas, False caso contrário
        """
        perfil = self.get_profile(user_id)
        funcionario = self.get_funcionario_by_id(user_id)
        return perfil is not None and funcionario is not None

    def insert_deposito_patente(self, data: dict, jwt_token: str) -> bool:
        """
        Insere um novo depósito de patente usando REST API do Supabase com JWT token.
        Args:
            data (dict): Dados do depósito
            jwt_token (str): Token JWT do usuário autenticado
        Returns:
            bool: True se inserido com sucesso, False caso contrário
        """
        try:
            import requests

            # Remove campos que podem estar causando problemas
            data_clean = data.copy()

            # Garante que não há campos None ou vazios que possam causar problemas
            for key, value in data_clean.items():
                if value is None:
                    data_clean[key] = ""
                elif isinstance(value, str) and value.strip() == "":
                    data_clean[key] = ""

            # Definir status inicial como pendente
            data_clean["status_patente"] = "pendente"

            # Usar REST API com JWT token
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente"
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            resp = requests.post(url, headers=headers, json=data_clean)

            if resp.status_code not in (200, 201):
                st.error(f"Erro ao inserir depósito de patente: {resp.text}")
                logging.error(
                    f"Erro ao inserir depósito de patente: {resp.text}")
                return False

            return True
        except Exception as e:
            st.error(f"Erro ao inserir depósito de patente: {str(e)}")
            logging.error(f"Erro ao inserir depósito de patente: {str(e)}")
            return False

    def get_depositos_patente_para_funcionario(self, funcionario_id: str, jwt_token: str = None):
        """
        Busca todos os depósitos de patente feitos por um funcionário via REST API com JWT token.
        Args:
            funcionario_id (str): ID do funcionário
            jwt_token (str): Token JWT do usuário autenticado
        Returns:
            list: Lista de depósitos de patente
        """
        try:
            import requests

            # Usar JWT token passado como parâmetro ou da sessão
            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            # Usar REST API com JWT token
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?funcionario_id=eq.{funcionario_id}&order=created_at.desc"
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.warning(
                    f"Erro ao buscar patentes do funcionário: {resp.text}")
                logging.error(
                    f"Erro ao buscar patentes do funcionário: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar patentes do funcionário: {str(e)}")
            logging.error(f"Erro ao buscar patentes do funcionário: {str(e)}")
            return []

    def get_depositos_patente_para_consultor(self, consultor_id: str, jwt_token: str = None):
        """
        Busca todos os depósitos de patente associados a um consultor via REST API com JWT token.
        Args:
            consultor_id (str): ID do consultor
            jwt_token (str): Token JWT do usuário autenticado
        Returns:
            list: Lista de depósitos de patente
        """
        try:
            import requests

            # Usar JWT token passado como parâmetro ou da sessão
            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            # Usar REST API com JWT token
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?consultor=eq.{consultor_id}&order=created_at.desc"
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.warning(
                    f"Erro ao buscar patentes do consultor: {resp.text}")
                logging.error(
                    f"Erro ao buscar patentes do consultor: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar patentes do consultor: {str(e)}")
            logging.error(f"Erro ao buscar patentes do consultor: {str(e)}")
            return []

    def update_patente_status(self, patente_id: str, status: str, jwt_token: str) -> bool:
        """
        Atualiza o status de uma patente via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"
        headers = self._get_headers(jwt_token, content_type=True)
        data = {"status_patente": status}
        resp = requests.patch(url, headers=headers, json=data)
        if resp.status_code in (200, 204):
            return True
        else:
            st.warning(f"Erro ao atualizar status da patente: {resp.text}")
            logging.error(f"Erro ao atualizar status da patente: {resp.text}")
            return False

    def update_patente_relatorio(self, patente_id, relatorio_data, jwt_token=None):
        """
        Atualiza o campo relatorio_patente de uma patente pelo ID via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"

        # Usar JWT token passado como parâmetro ou da sessão
        token = jwt_token or st.session_state.get('jwt_token')
        if not token:
            st.error("Token JWT não encontrado")
            return False

        headers = {
            "apikey": os.getenv("SUPABASE_KEY"),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Salvar dados do relatório como JSON
        data = {"relatorio_patente": relatorio_data}

        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code not in (200, 204):
                st.warning(f"Erro ao atualizar relatorio_patente: {resp.text}")
                logging.error(
                    f"Erro ao atualizar relatorio_patente: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def get_patente_status_display(self, status: str) -> str:
        """Retorna o texto de exibição para cada status de patente"""
        status_map = {
            "pendente": "Pendente",
            "recebido": "Recebido",
            "fazendo_relatorio": "Fazendo Relatório",
            "relatorio_concluido": "Relatório Concluído"
        }
        return status_map.get(status, status)

    def get_patente_status_icon(self, status: str) -> str:
        """Retorna o ícone para cada status de patente"""
        icon_map = {
            "pendente": "⏳",
            "recebido": "📥",
            "fazendo_relatorio": "📝",
            "relatorio_concluido": "✅"
        }
        return icon_map.get(status, "❓")

    def get_all_depositos_patente(self, jwt_token: str = None):
        """
        Busca todos os depósitos de patente (para administradores) via REST API com JWT token.
        Args:
            jwt_token (str): Token JWT do usuário autenticado
        Returns:
            list: Lista de todos os depósitos de patente
        """
        try:
            import requests

            # Usar JWT token passado como parâmetro ou da sessão
            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            # Usar REST API com JWT token
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?order=created_at.desc"
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.warning(f"Erro ao buscar patentes: {resp.text}")
                logging.error(f"Erro ao buscar patentes: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar patentes: {str(e)}")
            logging.error(f"Erro ao buscar patentes: {str(e)}")
            return []


# Exemplo de uso:
# agent = SupabaseAgent()
# user = agent.login(email, password)
# perfil = agent.get_profile(user['id'])
