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
        try:
            resp = self.client.auth.sign_in_with_password(
                {"email": email, "password": password})
            jwt_token = None
            if hasattr(resp, "session") and resp.session:
                jwt_token = resp.session.access_token
            return resp.user if resp.user else None, jwt_token
        except Exception as e:
            # Capturar erros específicos do Supabase
            error_message = str(e)
            if "Invalid login credentials" in error_message:
                raise Exception("Login ou senha incorretos")
            elif "Email not confirmed" in error_message:
                raise Exception(
                    "Email não confirmado. Verifique sua caixa de entrada.")
            elif "Too many requests" in error_message:
                raise Exception(
                    "Muitas tentativas. Aguarde um momento antes de tentar novamente.")
            else:
                raise Exception(f"Erro de conexão: {error_message}")

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

        # Debug: Log dos dados sendo enviados
        logging.info(f"Dados sendo enviados para Supabase: {busca_data}")

        # Verificar se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['marca', 'consultor_id',
                               'status_busca', 'dados_completos']
        for campo in campos_obrigatorios:
            if campo not in busca_data or not busca_data[campo]:
                st.error(
                    f"Campo obrigatório '{campo}' está faltando ou vazio!")
                return False

        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/buscas"
        headers = self._get_headers(jwt_token, content_type=True)

        # Debug: Log da URL e headers
        logging.info(f"URL: {url}")
        logging.info(f"Headers: {headers}")

        resp = requests.post(url, headers=headers, json=busca_data)

        # Debug: Log da resposta
        logging.info(f"Status Code: {resp.status_code}")
        logging.info(f"Response: {resp.text}")

        if resp.status_code != 201:
            st.warning(f"Erro ao inserir no Supabase: {resp.text}")
            logging.error(f"Erro ao inserir no Supabase: {resp.text}")
            return False

        st.success("✅ Busca inserida com sucesso no Supabase!")
        logging.info("Busca inserida com sucesso no Supabase")
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

    def upload_file_to_storage(self, file, file_name, jwt_token, bucket="patentepdf"):
        """
        Faz upload de um arquivo para o Supabase Storage via REST API autenticada com o JWT do usuário logado e retorna a URL pública.
        """
        try:
            # Log para debug
            logging.info(f"Iniciando upload para bucket: {bucket}")
            logging.info(f"JWT token presente: {bool(jwt_token)}")

            # Sanitiza o nome do arquivo
            sanitized_filename = self._sanitize_filename(file_name)

            # Verificar se o arquivo existe e tem conteúdo
            if not file or not hasattr(file, 'getvalue'):
                raise Exception("Arquivo inválido ou vazio")

            file_content = file.getvalue()
            if not file_content:
                raise Exception("Arquivo está vazio")

            # Determinar o content-type baseado na extensão do arquivo
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_name)
            if not content_type:
                content_type = "application/octet-stream"

            url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/{bucket}/{sanitized_filename}"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "apikey": os.getenv("SUPABASE_KEY"),
                "Content-Type": content_type
            }

            # Log para debug dos headers
            logging.info(f"Headers para upload: {headers}")
            logging.info(f"JWT token no header: {bool(jwt_token)}")

            # Log para debug
            logging.info(f"Fazendo upload para: {url}")
            logging.info(f"Tamanho do arquivo: {len(file_content)} bytes")
            logging.info(f"Nome do arquivo: {sanitized_filename}")
            logging.info(f"Content-Type: {content_type}")

            resp = requests.post(url, headers=headers,
                                 data=file_content, timeout=30)

            # Log da resposta
            logging.info(f"Status code: {resp.status_code}")
            logging.info(f"Response: {resp.text}")

            if resp.status_code not in (200, 201):
                error_msg = f"Erro ao fazer upload do arquivo: {resp.text}"
                st.warning(error_msg)
                logging.error(error_msg)
                raise Exception(error_msg)

            # Montar a URL pública conforme padrão do seu bucket
            public_url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{bucket}/{sanitized_filename}"
            logging.info(f"Upload bem-sucedido. URL: {public_url}")
            return public_url

        except requests.exceptions.Timeout:
            error_msg = "Timeout ao fazer upload do arquivo"
            st.warning(error_msg)
            logging.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro de conexão ao fazer upload: {str(e)}"
            st.warning(error_msg)
            logging.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Erro inesperado ao fazer upload: {str(e)}"
            st.warning(error_msg)
            logging.error(error_msg)
            raise Exception(error_msg)

    def upload_pdf_to_storage(self, file, file_name, jwt_token, bucket="patentepdf"):
        """
        Método legado para compatibilidade. Usa upload_file_to_storage internamente.
        """
        return self.upload_file_to_storage(file, file_name, jwt_token, bucket)

    def verificar_bucket_storage(self, bucket_name: str, jwt_token: str) -> bool:
        """
        Verifica se o bucket existe e está acessível.
        """
        try:
            import requests

            url = f"{os.getenv('SUPABASE_URL')}/storage/v1/bucket/{bucket_name}"
            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                logging.info(f"Bucket {bucket_name} está acessível")
                return True
            else:
                logging.warning(
                    f"Bucket {bucket_name} não está acessível: {resp.text}")
                return False

        except Exception as e:
            logging.error(f"Erro ao verificar bucket {bucket_name}: {str(e)}")
            return False

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

    def get_consultor_by_id(self, user_id: str):
        """
        Busca um consultor pelo ID na tabela perfil usando REST API com JWT token.
        Args:
            user_id (str): ID do consultor
        Returns:
            dict: Dados do consultor ou None se não encontrado
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

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/perfil?id=eq.{user_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data and len(data) > 0 else None
            else:
                st.warning(f"Erro ao buscar consultor: {resp.text}")
                return None

        except Exception as e:
            st.error(f"Erro ao buscar consultor: {str(e)}")
            return None

    def get_juridico_by_id(self, user_id: str):
        """
        Busca um usuário da tabela juridico_marca pelo ID.
        Args:
            user_id (str): ID do usuário
        Returns:
            dict: Dados do usuário ou None se não encontrado
        """
        try:
            import requests

            jwt_token = getattr(st.session_state, 'jwt_token', None)

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

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/juridico_marca?id=eq.{user_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data and len(data) > 0 else None
            else:
                st.warning(f"Erro ao buscar usuário jurídico: {resp.text}")
                return None

        except Exception as e:
            st.error(f"Erro ao buscar usuário jurídico: {str(e)}")
            return None

    def get_juridicos_admin(self):
        """
        Busca todos os usuários da tabela juridico_marca que são admin (is_admin = true).
        Returns:
            list: Lista de usuários jurídicos admin
        """
        try:
            import requests

            jwt_token = getattr(st.session_state, 'jwt_token', None)

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

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/juridico_marca?is_admin=eq.true"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(
                    f"Erro ao buscar usuários jurídicos admin: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar usuários jurídicos admin: {str(e)}")
            return []

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

    # ==================== MÉTODOS PARA OBJEÇÕES ====================

    def get_consultor_name_by_id(self, consultor_id: str, jwt_token: str) -> str:
        """
        Busca o nome do consultor pelo ID
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/perfil?id=eq.{consultor_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('name', 'N/A')
            return 'N/A'
        except Exception as e:
            st.error(f"Erro ao buscar nome do consultor: {str(e)}")
            return 'N/A'

    def get_juridico_name_by_id(self, juridico_id: str, jwt_token: str) -> str:
        """
        Busca o nome do usuário jurídico pelo ID
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/juridico_marca?id=eq.{juridico_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('name', 'N/A')
            return 'N/A'
        except Exception as e:
            st.error(f"Erro ao buscar nome do usuário jurídico: {str(e)}")
            return 'N/A'

    def get_consultor_email_by_id(self, consultor_id: str, jwt_token: str) -> str:
        """
        Busca o email do consultor pelo ID
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/perfil?id=eq.{consultor_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('email', 'N/A')
            return 'N/A'
        except Exception as e:
            st.error(f"Erro ao buscar email do consultor: {str(e)}")
            return 'N/A'

    def get_juridico_email_by_id(self, juridico_id: str, jwt_token: str) -> str:
        """
        Busca o email do usuário jurídico pelo ID
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/juridico_marca?id=eq.{juridico_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('email', 'N/A')
            return 'N/A'
        except Exception as e:
            st.error(f"Erro ao buscar email do usuário jurídico: {str(e)}")
            return 'N/A'

    def insert_objecao(self, objecao_data: dict, jwt_token: str) -> dict:
        """
        Insere um novo serviço jurídico na tabela 'objecao' via REST API do Supabase.
        Retorna o objeto criado ou None se falhar.
        """
        try:
            import requests

            # Buscar nomes e emails antes da inserção
            consultor_id = objecao_data.get('consultor_objecao')
            juridico_id = objecao_data.get('juridico_id')

            if consultor_id:
                name_consultor = self.get_consultor_name_by_id(
                    consultor_id, jwt_token)
                email_consultor = self.get_consultor_email_by_id(
                    consultor_id, jwt_token)
                objecao_data['name_consultor'] = name_consultor
                objecao_data['email_consultor'] = email_consultor

            if juridico_id:
                name_juridico = self.get_juridico_name_by_id(
                    juridico_id, jwt_token)
                email_juridico = self.get_juridico_email_by_id(
                    juridico_id, jwt_token)
                objecao_data['name_juridico_marca'] = name_juridico
                objecao_data['email_juridico_marca'] = email_juridico

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao"
            resp = requests.post(url, headers=headers, json=objecao_data)

            if resp.status_code == 201:
                try:
                    # Tentar parsear a resposta JSON
                    created_obj = resp.json()
                    if created_obj and len(created_obj) > 0:
                        return created_obj[0]
                except:
                    # Se não conseguir parsear, buscar a objeção recém-criada
                    return self._buscar_objecao_recém_criada(objecao_data, jwt_token)
            else:
                st.warning(f"Erro ao inserir objeção: {resp.text}")
                logging.error(f"Erro ao inserir objeção: {resp.text}")
                return None

        except Exception as e:
            st.error(f"Erro ao inserir objeção: {str(e)}")
            logging.error(f"Erro ao inserir objeção: {str(e)}")
            return None

    def _buscar_objecao_recém_criada(self, objecao_data: dict, jwt_token: str) -> dict:
        """
        Busca uma objeção recém-criada usando os dados principais
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            # Buscar pela marca, nomecliente, consultor e juridico_id
            marca = objecao_data.get('marca', '')
            nomecliente = objecao_data.get('nomecliente', '')
            consultor_objecao = objecao_data.get('consultor_objecao', '')
            juridico_id = objecao_data.get('juridico_id', '')

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?marca=eq.{marca}&nomecliente=eq.{nomecliente}&consultor_objecao=eq.{consultor_objecao}&juridico_id=eq.{juridico_id}&order=created_at.desc&limit=1"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]

            return None

        except Exception as e:
            st.error(f"Erro ao buscar objeção recém-criada: {str(e)}")
            return None

    def get_objecoes_by_consultor(self, consultor_id: str, jwt_token: str) -> list:
        """
        Busca objeções por consultor via REST API
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?consultor_objecao=eq.{consultor_id}&order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar objeções: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar objeções: {str(e)}")
            return []

    def get_objecoes_by_juridico(self, juridico_id: str, jwt_token: str) -> list:
        """
        Busca objeções criadas por um usuário jurídico via REST API
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?juridico_id=eq.{juridico_id}&order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar objeções: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar objeções: {str(e)}")
            return []

    def get_objecao_by_id(self, objecao_id: str, jwt_token: str) -> dict:
        """
        Busca uma objeção específica pelo ID
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?id=eq.{objecao_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
            return None

        except Exception as e:
            st.error(f"Erro ao buscar objeção: {str(e)}")
            return None

    def get_all_objecoes(self, jwt_token: str) -> list:
        """
        Busca todas as objeções (apenas para administradores)
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar objeções: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar objeções: {str(e)}")
            return []

    def update_objecao_status(self, objecao_id: str, status: str, jwt_token: str) -> bool:
        """
        Atualiza o status de uma objeção
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?id=eq.{objecao_id}"
            data = {"status_objecao": status}

            resp = requests.patch(url, headers=headers, json=data)

            if resp.status_code in (200, 204):
                return True
            else:
                st.warning(f"Erro ao atualizar status: {resp.text}")
                return False

        except Exception as e:
            st.error(f"Erro ao atualizar status: {str(e)}")
            return False

    def update_objecao_obejpdf(self, objecao_id, obejpdf_data, jwt_token=None):
        """
        Atualiza o campo obejpdf de uma objeção pelo ID via REST API do Supabase.
        Para documentos enviados por funcionários.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?id=eq.{objecao_id}"

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

        # Salvar dados dos documentos como JSON
        data = {"obejpdf": obejpdf_data}

        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code not in (200, 204):
                st.warning(f"Erro ao atualizar obejpdf: {resp.text}")
                logging.error(f"Erro ao atualizar obejpdf: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def update_objecao_peticaopdf(self, objecao_id, peticaopdf_data, jwt_token=None):
        """
        Atualiza o campo peticaopdf de uma objeção pelo ID via REST API do Supabase.
        Para petições enviadas por advogados.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?id=eq.{objecao_id}"

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

        # Salvar dados dos documentos como JSON
        data = {"peticaopdf": peticaopdf_data}

        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code not in (200, 204):
                st.warning(f"Erro ao atualizar peticaopdf: {resp.text}")
                logging.error(f"Erro ao atualizar peticaopdf: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def update_objecao_documentos(self, objecao_id, documentos_data, jwt_token=None):
        """
        Atualiza o campo documentos_objecao de uma objeção pelo ID via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/objecao?id=eq.{objecao_id}"

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

        # Salvar dados dos documentos como JSON
        data = {"documentos_objecao": documentos_data}

        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code not in (200, 204):
                st.warning(
                    f"Erro ao atualizar documentos_objecao: {resp.text}")
                logging.error(
                    f"Erro ao atualizar documentos_objecao: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def get_objecao_status_display(self, status: str) -> str:
        """Retorna o texto de exibição para cada status de objeção"""
        status_map = {
            "pendente": "Pendente",
            "recebido": "Recebido",
            "em_execucao": "Em Execução",
            "concluido": "Concluído"
        }
        return status_map.get(status, status)

    def get_objecao_status_icon(self, status: str) -> str:
        """Retorna o ícone para cada status de objeção"""
        icon_map = {
            "pendente": "⏳",
            "recebido": "📥",
            "em_execucao": "🔍",
            "concluido": "✅"
        }
        return icon_map.get(status, "❓")

    # ==================== MÉTODOS PARA PATENTES ====================

    def insert_deposito_patente(self, data: dict, jwt_token: str) -> bool:
        """
        Insere um novo depósito de patente na tabela 'deposito_patente' via REST API do Supabase.
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente"
            resp = requests.post(url, headers=headers, json=data)

            if resp.status_code == 201:
                return True
            else:
                st.warning(f"Erro ao inserir depósito de patente: {resp.text}")
                logging.error(
                    f"Erro ao inserir depósito de patente: {resp.text}")
                return False

        except Exception as e:
            st.error(f"Erro ao inserir depósito de patente: {str(e)}")
            logging.error(f"Erro ao inserir depósito de patente: {str(e)}")
            return False

    def get_depositos_patente_para_funcionario(self, funcionario_id: str, jwt_token: str = None):
        """
        Busca depósitos de patente para um funcionário específico
        """
        try:
            import requests

            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?funcionario_id=eq.{funcionario_id}&order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar depósitos de patente: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar depósitos de patente: {str(e)}")
            return []

    def get_depositos_patente_para_consultor(self, consultor_id: str, jwt_token: str = None):
        """
        Busca depósitos de patente para um consultor específico
        """
        try:
            import requests

            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?consultor=eq.{consultor_id}&order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar depósitos de patente: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar depósitos de patente: {str(e)}")
            return []

    def update_patente_status(self, patente_id: str, status: str, jwt_token: str) -> bool:
        """
        Atualiza o status de uma patente
        """
        try:
            import requests

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"
            data = {"status_patente": status}

            resp = requests.patch(url, headers=headers, json=data)

            if resp.status_code in (200, 204):
                return True
            else:
                st.warning(f"Erro ao atualizar status da patente: {resp.text}")
                return False

        except Exception as e:
            st.error(f"Erro ao atualizar status da patente: {str(e)}")
            return False

    def update_patente_relatorio(self, patente_id, relatorio_data, jwt_token=None):
        """
        Atualiza o campo relatorio de uma patente pelo ID via REST API do Supabase.
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
                st.warning(f"Erro ao atualizar relatório: {resp.text}")
                logging.error(f"Erro ao atualizar relatório: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def update_patente_pdf_url(self, patente_id, pdf_urls, jwt_token=None):
        """
        Atualiza a coluna pdf_patente de uma patente pelo ID via REST API do Supabase.
        Permite que tanto consultores quanto funcionários adicionem documentos na mesma coluna.
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

        # Primeiro, buscar os arquivos existentes
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                patente_data = resp.json()
                if patente_data:
                    existing_pdfs = patente_data[0].get('pdf_patente', [])
                    if isinstance(existing_pdfs, str):
                        try:
                            import json
                            existing_pdfs = json.loads(existing_pdfs)
                        except:
                            existing_pdfs = []
                    if not isinstance(existing_pdfs, list):
                        existing_pdfs = []
                else:
                    existing_pdfs = []
            else:
                st.warning(f"Erro ao buscar patente: {resp.text}")
                return False
        except Exception as e:
            st.error(f"Erro ao buscar patente: {str(e)}")
            return False

        # Combinar arquivos existentes com novos arquivos
        all_pdfs = existing_pdfs + pdf_urls

        # Atualizar a coluna pdf_patente
        data = {"pdf_patente": all_pdfs}

        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code not in (200, 204):
                st.warning(
                    f"Erro ao atualizar arquivos da patente: {resp.text}")
                logging.error(
                    f"Erro ao atualizar arquivos da patente: {resp.text}")
                return False
            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def update_patente_aguardando_info(self, patente_id, pdf_urls, jwt_token=None):
        """
        Atualiza a coluna aguardando_info de uma patente pelo ID via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"

        token = jwt_token or st.session_state.get('jwt_token')
        if not token:
            st.error("Token JWT não encontrado")
            return False

        headers = {
            "apikey": os.getenv("SUPABASE_KEY"),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Primeiro, buscar os PDFs existentes
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                patente_data = resp.json()
                if patente_data:
                    existing_pdfs = patente_data[0].get('aguardando_info', [])

                    # Tratar diferentes tipos de dados
                    if existing_pdfs is None:
                        existing_pdfs = []
                    elif isinstance(existing_pdfs, str):
                        try:
                            import json
                            existing_pdfs = json.loads(existing_pdfs)
                        except:
                            # Se não conseguir fazer parse JSON, tratar como string única
                            existing_pdfs = [existing_pdfs] if existing_pdfs.strip() else [
                            ]
                    elif not isinstance(existing_pdfs, list):
                        # Se não for lista, converter para lista
                        existing_pdfs = [
                            existing_pdfs] if existing_pdfs else []
                else:
                    existing_pdfs = []
            else:
                st.warning(f"Erro ao buscar patente: {resp.text}")
                return False
        except Exception as e:
            st.error(f"Erro ao buscar patente: {str(e)}")
            return False

        # Combinar PDFs existentes com novos PDFs
        all_pdfs = existing_pdfs + pdf_urls

        # Atualizar a coluna aguardando_info
        data = {"aguardando_info": all_pdfs}

        try:
            resp = requests.patch(url, headers=headers, json=data)

            if resp.status_code not in (200, 204):
                st.warning(
                    f"Erro ao atualizar aguardando_info da patente: {resp.text}")
                logging.error(
                    f"Erro ao atualizar aguardando_info da patente: {resp.text}")
                return False

            # Verificar se os dados foram realmente salvos
            verify_resp = requests.get(url, headers=headers)

            if verify_resp.status_code == 200:
                verify_data = verify_resp.json()
                if verify_data:
                    saved_pdfs = verify_data[0].get('aguardando_info', [])
                    if saved_pdfs and len(saved_pdfs) > 0:
                        st.success("✅ Documentos salvos com sucesso!")
                    else:
                        st.warning("⚠️ Atualização não confirmada.")
                        return False
                else:
                    st.warning("⚠️ Nenhum dado encontrado na verificação")
                    return False
            else:
                st.warning(
                    f"⚠️ DEBUG: Erro na verificação: {verify_resp.text}")
                return False

            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def update_patente_para_aprovacao(self, patente_id, pdf_urls, jwt_token=None):
        """
        Atualiza a coluna para_aprovacao de uma patente pelo ID via REST API do Supabase.
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"

        token = jwt_token or st.session_state.get('jwt_token')
        if not token:
            st.error("Token JWT não encontrado")
            return False

        headers = {
            "apikey": os.getenv("SUPABASE_KEY"),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Primeiro, buscar os PDFs existentes
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                patente_data = resp.json()
                if patente_data:
                    existing_pdfs = patente_data[0].get('para_aprovacao', [])

                    # Tratar diferentes tipos de dados
                    if existing_pdfs is None:
                        existing_pdfs = []
                    elif isinstance(existing_pdfs, str):
                        try:
                            import json
                            existing_pdfs = json.loads(existing_pdfs)
                        except:
                            # Se não conseguir fazer parse JSON, tratar como string única
                            existing_pdfs = [existing_pdfs] if existing_pdfs.strip() else [
                            ]
                    elif not isinstance(existing_pdfs, list):
                        # Se não for lista, converter para lista
                        existing_pdfs = [
                            existing_pdfs] if existing_pdfs else []
                else:
                    existing_pdfs = []
            else:
                st.warning(f"Erro ao buscar patente: {resp.text}")
                return False
        except Exception as e:
            st.error(f"Erro ao buscar patente: {str(e)}")
            return False

        # Combinar PDFs existentes com novos PDFs
        all_pdfs = existing_pdfs + pdf_urls

        # Atualizar a coluna para_aprovacao
        data = {"para_aprovacao": all_pdfs}

        try:
            resp = requests.patch(url, headers=headers, json=data)

            if resp.status_code not in (200, 204):
                st.warning(
                    f"Erro ao atualizar para_aprovacao da patente: {resp.text}")
                logging.error(
                    f"Erro ao atualizar para_aprovacao da patente: {resp.text}")
                return False

            # Verificar se os dados foram realmente salvos
            verify_resp = requests.get(url, headers=headers)

            if verify_resp.status_code == 200:
                verify_data = verify_resp.json()
                if verify_data:
                    saved_pdfs = verify_data[0].get('para_aprovacao', [])
                    if saved_pdfs and len(saved_pdfs) > 0:
                        st.success("✅ Documentos salvos com sucesso!")
                    else:
                        st.warning("⚠️ Atualização não confirmada.")
                        return False
                else:
                    st.warning("⚠️ Nenhum dado encontrado na verificação")
                    return False
            else:
                st.warning(f"⚠️ Erro na verificação: {verify_resp.text}")
                return False

            return True
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            logging.error(f"Erro na requisição: {str(e)}")
            return False

    def test_patente_update_permissions(self, patente_id, jwt_token=None):
        """
        Testa se conseguimos atualizar diferentes colunas da patente
        """
        import requests
        url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?id=eq.{patente_id}"

        token = jwt_token or st.session_state.get('jwt_token')
        if not token:
            st.error("Token JWT não encontrado")
            return False

        headers = {
            "apikey": os.getenv("SUPABASE_KEY"),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        st.info("🧪 TESTE: Verificando permissões de atualização...")

        # Teste 1: Tentar atualizar uma coluna que sabemos que funciona (pdf_patente)
        st.info("🧪 TESTE 1: Tentando atualizar pdf_patente...")
        test_data_pdf = {"pdf_patente": ["test_url_pdf"]}
        try:
            resp = requests.patch(url, headers=headers, json=test_data_pdf)
            st.info(f"🧪 TESTE 1 - Status: {resp.status_code}")
            if resp.status_code in (200, 204):
                st.success("🧪 TESTE 1: pdf_patente pode ser atualizada!")
            else:
                st.warning(f"🧪 TESTE 1: Erro - {resp.text}")
        except Exception as e:
            st.error(f"🧪 TESTE 1: Exceção - {str(e)}")

        # Teste 2: Tentar atualizar aguardando_info
        st.info("🧪 TESTE 2: Tentando atualizar aguardando_info...")
        test_data_aguardando = {"aguardando_info": ["test_url_aguardando"]}
        try:
            resp = requests.patch(url, headers=headers,
                                  json=test_data_aguardando)
            st.info(f"🧪 TESTE 2 - Status: {resp.status_code}")
            if resp.status_code in (200, 204):
                st.success("🧪 TESTE 2: aguardando_info pode ser atualizada!")
            else:
                st.warning(f"🧪 TESTE 2: Erro - {resp.text}")
        except Exception as e:
            st.error(f"🧪 TESTE 2: Exceção - {str(e)}")

        # Teste 3: Tentar atualizar para_aprovacao
        st.info("🧪 TESTE 3: Tentando atualizar para_aprovacao...")
        test_data_aprovacao = {"para_aprovacao": ["test_url_aprovacao"]}
        try:
            resp = requests.patch(url, headers=headers,
                                  json=test_data_aprovacao)
            st.info(f"🧪 TESTE 3 - Status: {resp.status_code}")
            if resp.status_code in (200, 204):
                st.success("🧪 TESTE 3: para_aprovacao pode ser atualizada!")
            else:
                st.warning(f"🧪 TESTE 3: Erro - {resp.text}")
        except Exception as e:
            st.error(f"🧪 TESTE 3: Exceção - {str(e)}")

        # Verificar dados atuais
        st.info("🧪 VERIFICAÇÃO: Dados atuais da patente...")
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    patente = data[0]
                    st.info(f"🧪 pdf_patente: {patente.get('pdf_patente')}")
                    st.info(
                        f"🧪 aguardando_info: {patente.get('aguardando_info')}")
                    st.info(
                        f"🧪 para_aprovacao: {patente.get('para_aprovacao')}")
        except Exception as e:
            st.error(f"🧪 VERIFICAÇÃO: Erro - {str(e)}")

        return True

    def get_patente_status_display(self, status: str) -> str:
        """Retorna o texto de exibição para cada status de patente"""
        status_map = {
            "pendente": "Pendente",
            "recebido": "Recebido",
            "aguardando_informacoes": "Aguardando Informações",
            "aguardando_elaboracao": "Aguardando Elaboração",
            "relatorio_sendo_elaborado": "Relatório Sendo Elaborado",
            "relatorio_enviado_aprovacao": "Relatório Enviado para Aprovação",
            "relatorio_aprovado": "Relatório Aprovado",
            "concluido": "Concluído"
        }
        return status_map.get(status, status)

    def get_patente_status_icon(self, status: str) -> str:
        """Retorna o ícone para cada status de patente"""
        icon_map = {
            "pendente": "⏳",
            "recebido": "📥",
            "aguardando_informacoes": "❓",
            "aguardando_elaboracao": "⏸️",
            "relatorio_sendo_elaborado": "📝",
            "relatorio_enviado_aprovacao": "📤",
            "relatorio_aprovado": "✅",
            "concluido": "🎉"
        }
        return icon_map.get(status, "❓")

    def get_all_depositos_patente(self, jwt_token: str = None):
        """
        Busca todos os depósitos de patente (apenas para administradores)
        """
        try:
            import requests

            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return []

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/deposito_patente?order=created_at.desc"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.json() if resp.json() else []
            else:
                st.warning(f"Erro ao buscar depósitos de patente: {resp.text}")
                return []

        except Exception as e:
            st.error(f"Erro ao buscar depósitos de patente: {str(e)}")
            return []

    def get_user_email_by_id(self, user_id: str, jwt_token: str = None):
        """
        Busca o e-mail de um usuário pelo ID
        """
        try:
            import requests

            token = jwt_token or st.session_state.get('jwt_token')
            if not token:
                st.error("Token JWT não encontrado")
                return None

            headers = {
                "apikey": os.getenv("SUPABASE_KEY"),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/funcionario?id=eq.{user_id}&select=email"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('email')
                else:
                    # Tentar na tabela de consultores
                    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/consultor?id=eq.{user_id}&select=email"
                    resp = requests.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and len(data) > 0:
                            return data[0].get('email')
            return None

        except Exception as e:
            st.error(f"Erro ao buscar e-mail do usuário: {str(e)}")
            return None
