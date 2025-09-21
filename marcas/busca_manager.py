import streamlit as st
import json
import re
import logging
from typing import List, Dict, Any, Optional
from pdf_generator import gerar_pdf_busca
from ui_components import exibir_especificacoes_card

import unicodedata
from datetime import datetime


def get_user_attr(user, attr, default=None):
    if isinstance(user, dict):
        return user.get(attr, default)
    return getattr(user, attr, default)


def get_user_id(user):
    if isinstance(user, dict):
        return user.get('id')
    return getattr(user, 'id', None)


def clean_id(val):
    return val.strip() if isinstance(val, str) else val


class BuscaManager:
    """Gerencia operações relacionadas às buscas"""

    # Status possíveis para as buscas
    STATUS_PENDENTE = "pendente"
    STATUS_RECEBIDA = "recebida"
    STATUS_EM_EXECUCAO = "em_execucao"
    STATUS_CONCLUIDA = "concluida"

    def __init__(self, supabase_agent, email_agent):
        self.supabase_agent = supabase_agent
        self.email_agent = email_agent

    def verificar_acesso_admin(self, user):
        """Verifica se o usuário tem acesso administrativo"""
        return get_user_attr(user, 'is_admin', False)

    def processar_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa os dados do formulário para salvar no banco de dados.

        Args:
            form_data: Dados do formulário

        Returns:
            Dict com dados processados para salvar
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()

        # Verificação de segurança: garantir que form_data não contenha objetos não serializáveis
        def validate_serializable(data, path=""):
            """Valida se todos os dados são serializáveis em JSON"""
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                        raise ValueError(
                            f"Objeto não serializável encontrado em: {current_path}")
                    validate_serializable(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    current_path = f"{path}[{i}]"
                    if hasattr(item, 'getvalue') or hasattr(item, 'read'):
                        raise ValueError(
                            f"Objeto não serializável encontrado em: {current_path}")
                    validate_serializable(item, current_path)

        # Criar cópia limpa dos dados para processamento
        busca_data = dict(form_data)

        # Remover uploaded_file imediatamente para evitar problemas de serialização
        busca_data.pop("uploaded_file", None)

        busca_data["nome_consultor"] = form_data.get("consultor", "")
        busca_data.pop("consultor", None)

        if "marcas" in busca_data and busca_data["marcas"]:
            busca_data["marca"] = busca_data["marcas"][0]["marca"]

            # Filtrar apenas classes que foram preenchidas
            classes_preenchidas = []
            especificacoes_preenchidas = []

            for classe in busca_data["marcas"][0]["classes"]:
                classe_val = classe.get("classe", "").strip()
                especificacao_val = classe.get("especificacao", "").strip()

                # Incluir apenas se tanto a classe quanto a especificação foram preenchidas
                if classe_val and especificacao_val:
                    classes_preenchidas.append(classe_val)
                    especificacoes_preenchidas.append(especificacao_val)

            # Salvar apenas as classes e especificações preenchidas
            busca_data["classes"] = json.dumps(classes_preenchidas)
            busca_data["especificacoes"] = ", ".join(
                especificacoes_preenchidas)

        # Processar arquivo de upload se existir
        uploaded_file = form_data.get("uploaded_file")
        if uploaded_file:
            try:
                # Manter o nome original do arquivo, apenas adicionar timestamp para evitar conflitos
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                original_filename = uploaded_file.name

                # Separar nome e extensão
                if '.' in original_filename:
                    name_part = original_filename.rsplit('.', 1)[0]
                    extension = original_filename.rsplit('.', 1)[1]
                    file_name = f"{name_part}_{timestamp}.{extension}"
                else:
                    file_name = f"{original_filename}_{timestamp}"

                # Upload para o storage buscaspdf
                logo_url = self.supabase_agent.upload_file_to_storage(
                    uploaded_file,
                    file_name,
                    st.session_state.jwt_token,
                    bucket="buscaspdf"
                )

                if logo_url:
                    busca_data["logo"] = logo_url
                    logging.info(f"Arquivo enviado com sucesso: {logo_url}")
                else:
                    st.warning(
                        "Erro ao fazer upload do arquivo. A busca será salva sem o arquivo.")
                    logging.error("Erro ao fazer upload do arquivo")
            except Exception as e:
                st.warning(
                    f"Erro ao processar arquivo: {e}. A busca será salva sem o arquivo.")
                logging.error(f"Erro ao processar arquivo: {e}")

        # Função para limpar dados antes da serialização JSON
        def clean_data_for_json(data):
            """Remove objetos não serializáveis do dicionário"""
            if isinstance(data, dict):
                cleaned = {}
                for key, value in data.items():
                    # Pular objetos UploadedFile e outros não serializáveis
                    if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                        continue
                    elif isinstance(value, (dict, list)):
                        cleaned[key] = clean_data_for_json(value)
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        cleaned[key] = value
                    else:
                        # Converter outros tipos para string
                        cleaned[key] = str(value)
                return cleaned
            elif isinstance(data, list):
                return [clean_data_for_json(item) for item in data if not hasattr(item, 'getvalue')]
            else:
                return data

        # Remover outros objetos não serializáveis
        for key in list(busca_data.keys()):
            value = busca_data[key]
            if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                busca_data.pop(key, None)

        # Limpar dados para serialização JSON
        form_data_limpo = clean_data_for_json(busca_data)

        # Validação final antes da serialização
        try:
            validate_serializable(form_data_limpo)
        except ValueError as e:
            logging.error(f"Erro de validação de serialização: {e}")
            st.error(f"Erro interno: dados não serializáveis detectados. {e}")
            return None

        # Salvar o dicionário completo no campo dados_completos
        busca_data["dados_completos"] = json.dumps(
            form_data_limpo, ensure_ascii=False)
        busca_data["consultor_id"] = get_user_id(st.session_state.user)
        if busca_data["consultor_id"]:
            busca_data["consultor_id"] = clean_id(busca_data["consultor_id"])
        busca_data.pop("marcas", None)
        busca_data["consultor_email"] = st.session_state.get(
            "consultor_email", "")

        # Definir status inicial como pendente (persistente)
        busca_data["status_busca"] = self.STATUS_PENDENTE
        # Remover analise_realizada do dict, se existir
        busca_data.pop("analise_realizada", None)

        return busca_data

    def enviar_busca(self, form_data: Dict[str, Any]) -> bool:
        """
        Envia uma nova busca (salva no banco e envia e-mail).

        Args:
            form_data: Dados do formulário

        Returns:
            bool: True se enviado com sucesso
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        try:
            # Processar dados para salvar
            busca_data = self.processar_form_data(form_data)

            # Adicionar e-mail do consultor para o e-mail
            # Criar uma cópia limpa do form_data para evitar problemas de serialização
            form_data_limpo = dict(form_data)
            form_data_limpo["consultor_email"] = st.session_state.get(
                "consultor_email", "")

            # Remover objetos não serializáveis do form_data_limpo
            for key in list(form_data_limpo.keys()):
                value = form_data_limpo[key]
                if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                    form_data_limpo.pop(key, None)

            # Enviar e-mail com anexo se houver arquivo
            with st.spinner("Enviando e-mail..."):
                uploaded_file = form_data.get("uploaded_file")
                if uploaded_file:
                    # Preparar dados para e-mail com anexo
                    tipo_busca = form_data_limpo.get('tipo_busca', '')
                    consultor = form_data_limpo.get('consultor', '')
                    cpf_cnpj_cliente = form_data_limpo.get(
                        'cpf_cnpj_cliente', '')
                    nome_cliente = form_data_limpo.get('nome_cliente', '')
                    marcas = form_data_limpo.get('marcas', [])
                    nome_marca = ''
                    classes = ''
                    if marcas and isinstance(marcas, list) and len(marcas) > 0 and isinstance(marcas[0], dict):
                        nome_marca = marcas[0].get('marca', '')
                        classes = ', '.join([c.get('classe', '') for c in marcas[0].get(
                            'classes', []) if c.get('classe', '')])
                    data_br = form_data_limpo.get('data', '')

                    subject = f"Pedido de busca de marca {tipo_busca} - Data: {data_br} - Marca: {nome_marca} - Classes: {classes} - Cliente: {nome_cliente} - Consultor: {consultor}"

                    # Criar form_data sem o arquivo para o e-mail
                    form_data_email = dict(form_data_limpo)
                    form_data_email.pop("uploaded_file", None)
                    body_html = self.email_agent.format_body_html(
                        form_data_email)

                    # Enviar e-mail com anexo para cada destinatário
                    if self.email_agent.destinatarios:
                        for destinatario in self.email_agent.destinatarios:
                            self.email_agent.send_email_com_anexo(
                                destinatario,
                                subject,
                                body_html,
                                uploaded_file.getvalue(),
                                uploaded_file.name
                            )
                    else:
                        st.warning(
                            "Nenhum destinatário configurado para envio de e-mail")
                else:
                    # Enviar e-mail sem anexo
                    # Criar form_data limpo para o e-mail
                    form_data_email = dict(form_data_limpo)
                    form_data_email.pop("uploaded_file", None)
                    self.email_agent.send_email(form_data_email)

            # Salvar no banco
            ok = self.supabase_agent.insert_busca_rest(
                busca_data, st.session_state.jwt_token)

            if ok:
                # Enviar e-mail de confirmação para o consultor
                consultor_email = st.session_state.get("consultor_email", "")
                if consultor_email:
                    self.email_agent.send_email_confirmacao_consultor(
                        consultor_email, form_data_limpo)

                st.success("✅ E-mail enviado com sucesso!")
                return True
            else:
                st.error("Erro ao salvar busca no Supabase!")
                return False

        except Exception as e:
            st.error(f"Erro ao enviar busca: {e}")
            logging.error(f"Erro ao enviar busca: {e}")
            return False

    def buscar_buscas_usuario(self, user_id: str = "", is_admin: bool = False) -> List[Dict[str, Any]]:
        """
        Busca as buscas do usuário ou todas as buscas do sistema se is_admin=True.
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        if is_admin:
            return self.supabase_agent.get_all_buscas_rest(st.session_state.jwt_token)
        else:
            return self.supabase_agent.get_buscas_rest(user_id or "", st.session_state.jwt_token)

    def filtrar_buscas(self, buscas: List[Dict[str, Any]],
                       busca_marca: Optional[str] = None,
                       busca_consultor: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filtra as buscas por marca e/ou consultor.

        Args:
            buscas: Lista de buscas
            busca_marca: Termo para filtrar por marca
            busca_consultor: Termo para filtrar por consultor

        Returns:
            Lista filtrada de buscas
        """
        if busca_marca:
            buscas = [b for b in buscas if busca_marca.lower()
                      in b.get('marca', '').lower()]

        if busca_consultor:
            buscas = [b for b in buscas if busca_consultor.lower() in b.get(
                'nome_consultor', '').lower()]

        return buscas

    def atualizar_status_busca(self, busca_id: str, novo_status: str) -> bool:
        """
        Atualiza o status de uma busca persistindo em status_busca no banco.
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        ok = self.supabase_agent.update_busca_status(
            busca_id, novo_status, st.session_state.jwt_token)
        if ok:
            status_text = self.get_status_display(novo_status)
            st.success(f"Status da busca atualizado para: {status_text}")
            return True
        else:
            st.error("Erro ao atualizar status da busca!")
            return False

    def get_status_display(self, status: str) -> str:
        """Retorna o texto de exibição para cada status"""
        status_map = {
            self.STATUS_PENDENTE: "Pendente",
            self.STATUS_RECEBIDA: "Recebida",
            self.STATUS_EM_EXECUCAO: "Em Execução",
            self.STATUS_CONCLUIDA: "Concluída"
        }
        return status_map.get(status, status)

    def get_status_icon(self, status: str) -> str:
        """Retorna o ícone para cada status"""
        icon_map = {
            self.STATUS_PENDENTE: "⏳",
            self.STATUS_RECEBIDA: "📥",
            self.STATUS_EM_EXECUCAO: "🔍",
            self.STATUS_CONCLUIDA: "✅"
        }
        return icon_map.get(status, "❓")

    def get_status_atual(self, busca: Dict[str, Any]) -> str:
        """
        Determina o status atual baseado em status_busca persistente no banco.
        """
        status = busca.get('status_busca', self.STATUS_PENDENTE)
        if status not in [self.STATUS_PENDENTE, self.STATUS_RECEBIDA, self.STATUS_EM_EXECUCAO, self.STATUS_CONCLUIDA]:
            return self.STATUS_PENDENTE
        return status

    def renderizar_busca(self, busca: Dict[str, Any], is_admin: bool = False, todas_buscas: Optional[List[Dict[str, Any]]] = None):
        """
        Renderiza uma busca individual na interface.

        Args:
            busca: Dados da busca
            is_admin: Se é admin
            todas_buscas: Lista de todas as buscas (para calcular posição na fila)
        """
        status = self.get_status_atual(busca)
        status_icon = self.get_status_icon(status)
        status_text = self.get_status_display(status)

        if is_admin:
            expander_label = f"{status_icon} {busca.get('marca', '')} - {busca.get('data', '')} - {busca.get('nome_consultor', '')} - {status_text}"
        else:
            fila_info = ""
            # Só mostrar posição na fila se status for RECEBIDA ou PENDENTE
            if todas_buscas is not None and status in [self.STATUS_RECEBIDA, self.STATUS_PENDENTE]:
                pos = self.get_posicao_na_fila(busca, todas_buscas)
                if pos >= 0:
                    if pos == 0:
                        fila_info = " (próxima)"
                    else:
                        fila_info = f" ({pos} na fila)"
            expander_label = f"{status_icon} {busca.get('marca', '')} - {busca.get('data', '')} - {status_text}{fila_info}"

        with st.expander(expander_label):
            st.write(f"Tipo: {busca.get('tipo_busca', '')}")
            st.write(f"Consultor: {busca.get('nome_consultor', '')}")
            st.write(f"Status: {status_text}")

            # Só mostrar info de fila se status for RECEBIDA ou PENDENTE
            if not is_admin and todas_buscas is not None and status in [self.STATUS_RECEBIDA, self.STATUS_PENDENTE]:
                pos = self.get_posicao_na_fila(busca, todas_buscas)
                if pos >= 0:
                    if pos == 0:
                        st.info("Sua busca é a próxima a ser analisada!")
                    else:
                        st.info(
                            f"Há {pos} busca(s) na fila para serem analisadas antes da sua.")

            # Exibir dados completos se disponível
            if "dados_completos" in busca:
                self._exibir_dados_completos(busca)
            elif "marcas" in busca and "especificacoes" in busca:
                self._exibir_dados_tradicionais(busca)

            # Exibir arquivo de logo se existir
            if busca.get('logo'):
                st.markdown("**Arquivo Anexado:**")
                logo_url = busca.get('logo', '')
                if isinstance(logo_url, str) and logo_url:
                    filename = logo_url.split(
                        '/')[-1] if '/' in logo_url else logo_url
                    st.markdown(
                        f"[📎 {filename}]({logo_url})", unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"[📎 Arquivo anexado]({logo_url})", unsafe_allow_html=True)

            if busca.get('observacao'):
                st.write(f"Observação: {busca.get('observacao')}")

            # Upload de PDF para admin APENAS se status for EM_EXECUCAO ou CONCLUIDA
            if is_admin and status in [self.STATUS_EM_EXECUCAO, self.STATUS_CONCLUIDA]:
                st.markdown("---")
                st.write("Upload dos arquivos do resultado da busca:")
                uploaded_files = st.file_uploader("Selecione os arquivos", type=[
                                                  "pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif", "bmp", "mp4", "avi", "mov", "wmv", "zip", "rar"], accept_multiple_files=True, key=f"pdf_{busca['id']}")
                if uploaded_files and st.button("Enviar Arquivo(s)", key=f"btn_pdf_{busca['id']}"):
                    admin_uid = get_user_id(st.session_state.user)
                    st.info(f"UID do admin logado no upload: {admin_uid}")
                    pdf_urls = []
                    for file in uploaded_files:
                        # Normalizar nome do arquivo: remover acentos, espaços e caracteres especiais
                        def normalize_filename(filename):
                            filename = unicodedata.normalize('NFKD', filename).encode(
                                'ASCII', 'ignore').decode('ASCII')
                            filename = re.sub(
                                r'[^a-zA-Z0-9_.-]', '_', filename)
                            return filename
                        file_name = normalize_filename(
                            f"{busca['id']}_{file.name}")
                        url = self.supabase_agent.upload_pdf_to_storage(
                            file, file_name, st.session_state.jwt_token, bucket="buscaspdf")
                        pdf_urls.append(url)
                    # Atualiza pdf_buscas como lista de URLs
                    self.supabase_agent.update_busca_pdf_url(
                        busca['id'], pdf_urls)
                    # Se estiver em execução, já marca como concluída
                    if status == self.STATUS_EM_EXECUCAO:
                        self.atualizar_status_busca(
                            busca['id'], self.STATUS_CONCLUIDA)
                        # NOVO: Usar o e-mail salvo na busca
                        consultor_email = busca.get(
                            'consultor_email', '').strip()
                        if consultor_email:
                            anexos = []
                            for file in uploaded_files:
                                pdf_bytes = file.getvalue()
                                # Nome do arquivo no e-mail: apenas o nome original normalizado
                                email_file_name = normalize_filename(file.name)
                                anexos.append((pdf_bytes, email_file_name))
                            marca = busca.get('marca', '')
                            consultor_nome = busca.get('nome_consultor', '')
                            cpf_cnpj_cliente = busca.get(
                                'cpf_cnpj_cliente', '')
                            nome_cliente = busca.get('nome_cliente', '')
                            assunto = f"Busca Concluída - {marca} - {consultor_nome}"

                            # Montar corpo do e-mail com dados do cliente
                            corpo_cliente = ""
                            if cpf_cnpj_cliente or nome_cliente:
                                corpo_cliente = f"<br>- Cliente: {nome_cliente}<br>- CPF/CNPJ: {cpf_cnpj_cliente}"

                            corpo = f"""<div style='font-family: Arial; font-size: 12pt;'>Olá,<br><br>Segue em anexo o resultado da busca.<br><br>Dados da busca:<br>- Marca: {marca}<br>- Consultor: {consultor_nome}{corpo_cliente}<br>- Tipo de busca: {busca.get('tipo_busca', '')}<br>- Data: {busca.get('data', '')}<br>- Classes: {busca.get('classes', '')}<br>- Especificações: {busca.get('especificacoes', '')}<br><br>Atenciosamente,<br>Equipe AGP Consultoria</div>"""
                            if len(anexos) > 1:
                                self.email_agent.send_email_multiplos_anexos(
                                    destinatario=consultor_email,
                                    assunto=assunto,
                                    corpo=corpo,
                                    anexos=anexos
                                )
                            else:
                                self.email_agent.send_email_com_anexo(
                                    destinatario=consultor_email,
                                    assunto=assunto,
                                    corpo=corpo,
                                    anexo_bytes=anexos[0][0],
                                    nome_arquivo=anexos[0][1]
                                )
                        else:
                            st.warning(
                                f"E-mail do consultor não encontrado na busca (busca id: {busca.get('id')})")
                    st.success("Arquivo(s) enviado(s) com sucesso!")
                    st.rerun()

            # Exibir links de download dos arquivos se existirem
            if busca.get("pdf_buscas"):
                pdfs = busca["pdf_buscas"]
                if isinstance(pdfs, str):
                    pdfs = [pdfs]
                st.markdown("**Arquivo(s) do resultado:**")
                for i, url in enumerate(pdfs):
                    st.markdown(f"[📄 Arquivo {i+1}]({url})",
                                unsafe_allow_html=True)

            # Botões de ação
            self._renderizar_botoes_acao(busca, is_admin)

    def _exibir_dados_completos(self, busca: Dict[str, Any]):
        """Exibe dados completos da busca"""
        try:
            dados = busca["dados_completos"]
            if isinstance(dados, str):
                dados = json.loads(dados)
                if isinstance(dados, str):
                    dados = json.loads(dados)

            if not isinstance(dados, dict):
                raise ValueError("dados_completos não é um dicionário")

            # Exibir dados do cliente se disponíveis
            cpf_cnpj_cliente = dados.get('cpf_cnpj_cliente', '')
            nome_cliente = dados.get('nome_cliente', '')
            if cpf_cnpj_cliente or nome_cliente:
                st.markdown("**Dados do Cliente:**")
                if cpf_cnpj_cliente:
                    st.markdown(
                        f"<b>CPF/CNPJ:</b> {cpf_cnpj_cliente}", unsafe_allow_html=True)
                if nome_cliente:
                    st.markdown(
                        f"<b>Nome:</b> {nome_cliente}", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            for i, marca in enumerate(dados.get("marcas", [])):
                st.markdown(
                    f"<b>Marca:</b> {marca.get('marca', '')}", unsafe_allow_html=True)

                # Filtrar apenas classes que foram preenchidas
                classes_preenchidas = []
                for classe in marca.get("classes", []):
                    classe_num = classe.get("classe", "").strip()
                    especificacao = classe.get("especificacao", "").strip()

                    # Incluir apenas se tanto a classe quanto a especificação foram preenchidas
                    if classe_num and especificacao:
                        classes_preenchidas.append((classe_num, especificacao))

                # Exibir apenas as classes preenchidas
                for jdx, (classe_num, especificacao) in enumerate(classes_preenchidas, 1):
                    if isinstance(especificacao, list):
                        especs = [e.strip()
                                  for e in especificacao if e.strip()]
                    else:
                        especs = [e.strip() for e in str(
                            especificacao).split("\n") if e.strip()]

                    if especs:
                        especs_str = "; ".join(especs)
                    else:
                        especs_str = "Sem especificações"

                    st.markdown(
                        f"<b>Classe {classe_num}:</b> {especs_str}", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erro ao exibir dados da busca: {e}")

    def _exibir_dados_tradicionais(self, busca: Dict[str, Any]):
        """Exibe dados tradicionais da busca"""
        st.write(f"Classes: {busca.get('classes', '')}")
        especs = busca.get('especificacoes', '')
        if especs:
            if isinstance(especs, str):
                especs_list = [e.strip()
                               for e in re.split(r",|\n", especs) if e.strip()]
            elif isinstance(especs, list):
                especs_list = [str(e).strip()
                               for e in especs if str(e).strip()]
            else:
                especs_list = []

            if especs_list:
                st.write(f"Especificações: {'; '.join(especs_list)}")
            else:
                st.write("Especificações: Sem especificações")
        else:
            st.write("Especificações: Sem especificações")

    def _renderizar_botoes_acao(self, busca: Dict[str, Any], is_admin: bool):
        """Renderiza os botões de ação para uma busca"""
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        if is_admin:
            status_atual = self.get_status_atual(busca)
            col_status = st.columns(1)[0]
            with col_status:
                # Avançar para próxima etapa
                if status_atual == self.STATUS_RECEBIDA:
                    if st.button("🔍 Em Execução", key=f"analise_{busca['id']}"):
                        if self.atualizar_status_busca(busca['id'], self.STATUS_EM_EXECUCAO):
                            st.rerun()
                elif status_atual == self.STATUS_EM_EXECUCAO:
                    if st.button("✅ Concluída", key=f"concluida_{busca['id']}"):
                        if self.atualizar_status_busca(busca['id'], self.STATUS_CONCLUIDA):
                            st.rerun()
                elif status_atual == self.STATUS_PENDENTE:
                    if st.button("📥 Recebida", key=f"recebida_{busca['id']}"):
                        if self.atualizar_status_busca(busca['id'], self.STATUS_RECEBIDA):
                            st.rerun()
                # Não mostra botão se já está concluída
            st.markdown(
                f"<div style='margin-top:8px;font-weight:600;color:#005fa3;'>Status atual: {self.get_status_icon(status_atual)} {self.get_status_display(status_atual)}</div>", unsafe_allow_html=True)

    def ordenar_buscas_prioridade(self, buscas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ordena buscas: Em Análise primeiro, depois Recebida, depois Pendente; dentro de cada status, por ordem de chegada (created_at)."""
        def prioridade_busca(b):
            status = self.get_status_atual(b)
            # Menor valor = maior prioridade
            if status == self.STATUS_EM_EXECUCAO:
                prioridade_status = 0
            elif status == self.STATUS_RECEBIDA:
                prioridade_status = 1
            else:  # PENDENTE
                prioridade_status = 2

            # Ordenar por data de criação (quem chegou primeiro tem prioridade)
            created_at = b.get('created_at', '')
            return (prioridade_status, created_at)

        return sorted(buscas, key=prioridade_busca)

    def get_posicao_na_fila(self, busca: Dict[str, Any], todas_buscas: List[Dict[str, Any]]) -> int:
        """Retorna quantas buscas estão na frente da busca informada na fila de análise (status RECEBIDA, PENDENTE ou EM_ANALISE, ordenadas por prioridade)."""
        # Considera buscas RECEBIDA, PENDENTE e EM_EXECUCAO
        pendentes = [b for b in todas_buscas if self.get_status_atual(
            b) in [self.STATUS_RECEBIDA, self.STATUS_PENDENTE, self.STATUS_EM_EXECUCAO]]
        pendentes_ordenadas = self.ordenar_buscas_prioridade(pendentes)
        # Busca o índice da busca na lista ordenada
        for idx, b in enumerate(pendentes_ordenadas):
            if b.get('id') == busca.get('id'):
                return idx  # idx é o número de buscas na frente
        return -1  # Não encontrada

    def separar_buscas_por_status(self, buscas: List[Dict[str, Any]]) -> dict:
        """
        Separa as buscas por status em um dicionário.
        """
        resultado = {
            self.STATUS_PENDENTE: [],
            self.STATUS_RECEBIDA: [],
            self.STATUS_EM_EXECUCAO: [],
            self.STATUS_CONCLUIDA: []
        }

        for busca in buscas:
            status = busca.get('status_busca', self.STATUS_PENDENTE)
            if status in resultado:
                resultado[status].append(busca)
            else:
                resultado[self.STATUS_PENDENTE].append(busca)

        return resultado
