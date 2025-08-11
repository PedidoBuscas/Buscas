import streamlit as st
import smtplib
from email.message import EmailMessage
import logging
import re


class EmailAgent:
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_pass, destinatarios, destinatario_juridico="", destinatario_juridico_um=""):
        """
        Inicializa o agente de e-mail com as configurações SMTP e lista de destinatários.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.destinatarios = destinatarios
        self.destinatario_juridico = destinatario_juridico
        self.destinatario_juridico_um = destinatario_juridico_um

    def enviar_notificacao_documento_busca(self, busca_data, anexos, consultor_nome):
        """
        Envia notificação para destinatarios quando consultor adiciona documento de busca
        """
        if not self.destinatarios:
            st.warning(
                "⚠️ Destinatários de busca não configurados. E-mail não será enviado.")
            return False

        marca = busca_data.get('marca', 'N/A')
        nome_cliente = busca_data.get('nome_cliente', 'N/A')
        cpf_cnpj_cliente = busca_data.get('cpf_cnpj_cliente', 'N/A')
        tipo_busca = busca_data.get('tipo_busca', 'N/A')

        subject = f"Novo documento adicionado - Busca de Marca: {marca} - Consultor: {consultor_nome}"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Novo Documento Adicionado - Busca de Marca</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nome_cliente}</p>
            <p><b>CPF/CNPJ:</b> {cpf_cnpj_cliente}</p>
            <p><b>Tipo de Busca:</b> {tipo_busca}</p>
            <p><b>Consultor:</b> {consultor_nome}</p>
            <p>Um novo documento foi adicionado pelo consultor e está anexado a este e-mail.</p>
        </div>
        """

        return self._enviar_email_com_anexos(self.destinatarios, subject, body_html, anexos)

    def enviar_notificacao_documento_patente(self, patente_data, anexos, consultor_nome):
        """
        Envia notificação para destinatario_enge quando consultor adiciona documento de patente
        """
        from config import carregar_configuracoes
        config = carregar_configuracoes()
        destinatario_enge = config.get("destinatario_enge", "")

        if not destinatario_enge:
            st.warning(
                "⚠️ Destinatário de engenharia não configurado. E-mail não será enviado.")
            return False

        titulo = patente_data.get('titulo', 'N/A')
        cliente = patente_data.get('cliente', 'N/A')
        servico = patente_data.get('servico', 'N/A')

        subject = f"Novo documento adicionado - Patente: {titulo} - Consultor: {consultor_nome}"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Novo Documento Adicionado - Patente</h3>
            <p><b>Título:</b> {titulo}</p>
            <p><b>Cliente:</b> {cliente}</p>
            <p><b>Serviço:</b> {servico}</p>
            <p><b>Consultor:</b> {consultor_nome}</p>
            <p>Um novo documento foi adicionado pelo consultor e está anexado a este e-mail.</p>
        </div>
        """

        return self._enviar_email_com_anexos([destinatario_enge], subject, body_html, anexos)

    def enviar_notificacao_documento_objecao(self, objecao_data, anexos, consultor_nome):
        """
        Envia notificação para destinatario_juridico e destinatario_juridico_um quando consultor adiciona documento de serviço jurídico
        """
        destinatarios = []
        if self.destinatario_juridico:
            destinatarios.append(self.destinatario_juridico)
        if self.destinatario_juridico_um:
            destinatarios.append(self.destinatario_juridico_um)

        if not destinatarios:
            st.warning(
                "⚠️ Destinatários jurídicos não configurados. E-mail não será enviado.")
            return False

        marca = objecao_data.get('marca', 'N/A')
        nomecliente = objecao_data.get('nomecliente', 'N/A')
        servico = objecao_data.get('servico', 'N/A')

        subject = f"Novo documento adicionado - Serviço Jurídico: {marca} - Consultor: {consultor_nome}"

        # Adicionar observação se existir
        observacao = objecao_data.get('observacao', '')
        observacao_html = ""
        if observacao:
            observacao_html = f"<p><b>Observação:</b> {observacao}</p>"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Novo Documento Adicionado - Serviço Jurídico</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nomecliente}</p>
            <p><b>Serviço:</b> {servico}</p>
            <p><b>Consultor:</b> {consultor_nome}</p>
            {observacao_html}
            <p>Um novo documento foi adicionado pelo consultor e está anexado a este e-mail.</p>
        </div>
        """

        return self._enviar_email_com_anexos(destinatarios, subject, body_html, anexos)

    def _enviar_email_com_anexos(self, destinatarios, subject, body_html, anexos):
        """
        Método auxiliar para enviar email com anexos para múltiplos destinatários
        """
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(destinatarios)
            msg.set_content(body_html, subtype='html')

            # Adicionar anexos
            for anexo in anexos:
                if isinstance(anexo, dict) and 'content' in anexo and 'filename' in anexo:
                    maintype, subtype = self._detectar_tipo_mime(
                        anexo['filename'])
                    msg.add_attachment(
                        anexo['content'],
                        maintype=maintype,
                        subtype=subtype,
                        filename=anexo['filename']
                    )
                elif isinstance(anexo, tuple) and len(anexo) == 2:
                    # Formato (bytes, filename)
                    maintype, subtype = self._detectar_tipo_mime(anexo[1])
                    msg.add_attachment(
                        anexo[0],
                        maintype=maintype,
                        subtype=subtype,
                        filename=anexo[1]
                    )

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

            st.success(
                f"E-mail de notificação enviado com sucesso para: {', '.join(destinatarios)}")
            return True

        except Exception as e:
            st.error(f"Erro ao enviar e-mail de notificação: {e}")
            logging.error(f"Erro ao enviar e-mail de notificação: {e}")
            return False

    def send_email(self, form_data):
        """
        Envia um e-mail com os dados do formulário de busca para os destinatários configurados.
        """
        # Extrair dados principais
        tipo_busca = form_data.get('tipo_busca', '')
        consultor = form_data.get('consultor', '')
        cpf_cnpj_cliente = form_data.get('cpf_cnpj_cliente', '')
        nome_cliente = form_data.get('nome_cliente', '')
        marcas = form_data.get('marcas', [])
        nome_marca = ''
        classes = ''
        if marcas and isinstance(marcas, list) and len(marcas) > 0 and isinstance(marcas[0], dict):
            nome_marca = marcas[0].get('marca', '')
            classes = ', '.join([c.get('classe', '') for c in marcas[0].get(
                'classes', []) if c.get('classe', '')])
        data_br = form_data.get('data', '')
        # Montar título conforme solicitado, incluindo a data brasileira e dados do cliente
        subject = f"Pedido de busca de marca {tipo_busca} - Data: {data_br} - Marca: {nome_marca} - Classes: {classes} - Cliente: {nome_cliente} - Consultor: {consultor}"
        # Montar corpo HTML
        body_html = self._format_body_html(form_data)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(self.destinatarios)
        msg.set_content(body_html, subtype='html')
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(
                f"E-mail enviado com sucesso para: {', '.join(self.destinatarios)}")
        except Exception as e:
            st.error(f"Erro ao enviar e-mail: {e}")
            logging.error(f"Erro ao enviar e-mail: {e}")

    def send_email_com_anexo(self, destinatario, assunto, corpo, anexo_bytes, nome_arquivo):
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = self.smtp_user
        msg["To"] = destinatario
        msg.set_content(corpo, subtype='html')
        # Anexar arquivo apenas se fornecido
        if anexo_bytes is not None and nome_arquivo is not None:
            maintype, subtype = self._detectar_tipo_mime(nome_arquivo)
            msg.add_attachment(anexo_bytes, maintype=maintype,
                               subtype=subtype, filename=nome_arquivo)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(f"E-mail enviado com sucesso para: {destinatario}")
        except Exception as e:
            st.error(f"Erro ao enviar e-mail: {e}")
            logging.error(f"Erro ao enviar e-mail: {e}")

    def send_email_multiplos_anexos(self, destinatario, assunto, corpo, anexos):
        """
        Envia um e-mail com múltiplos anexos.
        anexos: lista de tuplas (anexo_bytes, nome_arquivo)
        """
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = self.smtp_user
        msg["To"] = destinatario
        msg.set_content(corpo, subtype='html')
        for anexo_bytes, nome_arquivo in anexos:
            maintype, subtype = self._detectar_tipo_mime(nome_arquivo)
            msg.add_attachment(anexo_bytes, maintype=maintype,
                               subtype=subtype, filename=nome_arquivo)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(f"E-mail enviado com sucesso para: {destinatario}")
        except Exception as e:
            st.error(f"Erro ao enviar e-mail: {e}")
            logging.error(f"Erro ao enviar e-mail: {e}")

    def _limpar_quebras_palavras(self, texto):
        # Remove espaços duplos
        texto = re.sub(r' +', ' ', texto)
        return texto

    def _detectar_tipo_mime(self, filename):
        """
        Detecta o tipo MIME baseado na extensão do arquivo.
        """
        filename = filename.lower()
        if filename.endswith('.pdf'):
            return "application", "pdf"
        elif filename.endswith('.docx'):
            return "application", "vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith('.doc'):
            return "application", "msword"
        elif filename.endswith('.xlsx'):
            return "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.endswith('.xls'):
            return "application", "vnd.ms-excel"
        elif filename.endswith('.pptx'):
            return "application", "vnd.openxmlformats-officedocument.presentationml.presentation"
        elif filename.endswith('.ppt'):
            return "application", "vnd.ms-powerpoint"
        elif filename.endswith('.txt'):
            return "text", "plain"
        else:
            # Padrão para outros tipos de arquivo
            return "application", "octet-stream"

    def _format_body_html(self, form_data):
        """
        Formata o corpo do e-mail em HTML com base nos dados do formulário.
        Agora cada classe aparece separada e as especificações aparecem em linha, separadas por vírgula.
        Aplica limpeza automática de quebras de palavras.
        """
        data = form_data.get('data', '')
        tipo_busca = form_data.get('tipo_busca', '')
        consultor = form_data.get('consultor', '')
        consultor_email = form_data.get('consultor_email', '')
        cpf_cnpj_cliente = form_data.get('cpf_cnpj_cliente', '')
        nome_cliente = form_data.get('nome_cliente', '')
        marcas = form_data.get('marcas', [])
        html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <b>Data:</b> {data}<br>
            <b>Tipo de busca:</b> {tipo_busca}<br>
            <b>Consultor:</b> {consultor}<br>
            <b>E-mail do consultor:</b> {consultor_email}<br>
            <b>CPF/CNPJ do Cliente:</b> {cpf_cnpj_cliente}<br>
            <b>Nome do Cliente:</b> {nome_cliente}<br><br>
        """
        if marcas:
            html += f"<b>Marca:</b> {marcas[0].get('marca', '')}<br>"
            for jdx, classe in enumerate(marcas[0].get('classes', []), 1):
                classe_num = classe.get('classe', '')
                especificacao = classe.get('especificacao', '')
                especs = re.split(r'[;\n]', especificacao)
                especs = [self._limpar_quebras_palavras(
                    e.strip()) for e in especs if e.strip()]
                especs_str = ', '.join(especs)
                html += f"<div style='margin-top:8px;'><b>{jdx}ª classe: {classe_num}</b> - Especificação: {especs_str}</div>"
        # Adicionar observação ao final
        observacao = form_data.get('observacao', '')
        if observacao:
            html += f"<br><b>Observação:</b> {observacao}<br>"
        html += "</div>"
        return html

    # ==================== MÉTODOS PARA OBJEÇÕES DE MARCA ====================

    def enviar_email_nova_objecao(self, destinatario: str, objecao_data: dict):
        """
        Envia e-mail de notificação para novo serviço jurídico.
        """
        # Verificar parâmetros
        if not destinatario or not destinatario.strip():
            st.error(
                "Destinatário não fornecido para e-mail de novo serviço jurídico.")
            return False

        if not objecao_data:
            st.error(
                "Dados do serviço jurídico não fornecidos para e-mail de novo serviço jurídico.")
            return False

        marca = objecao_data.get('marca', 'N/A')
        nomecliente = objecao_data.get('nomecliente', 'N/A')
        servico = objecao_data.get('servico', 'N/A')

        # Processos e contratos
        processo_list = objecao_data.get('processo', [])
        ncontrato_list = objecao_data.get('ncontrato', [])

        # Criar lista de processos com contratos
        processos_info = []
        for i, (processo, contrato) in enumerate(zip(processo_list, ncontrato_list), 1):
            processos_info.append(
                f"Processo {i}: {processo} - Contrato: {contrato}")

        processos_text = '<br>'.join(
            processos_info) if processos_info else 'N/A'

        subject = f"Novo Serviço Jurídico - {marca} - Cliente: {nomecliente}"

        # Adicionar observação se existir
        observacao = objecao_data.get('observacao', '')
        observacao_html = ""
        if observacao:
            observacao_html = f"<p><b>Observação:</b> {observacao}</p>"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Novo Serviço Jurídico Solicitado</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nomecliente}</p>
            <p><b>Serviço:</b> {servico}</p>
            <p><b>Processos:</b><br>{processos_text}</p>
            {observacao_html}
        </div>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = destinatario
        msg.set_content(body_html, subtype='html')

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(
                f"E-mail de notificação enviado com sucesso para: {destinatario}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"Erro de autenticação SMTP: {e}")
            logging.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            st.error(f"Erro de conexão SMTP: {e}")
            logging.error(f"Erro de conexão SMTP: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"Destinatário recusado: {e}")
            logging.error(f"Destinatário recusado: {e}")
            return False
        except Exception as e:
            st.error(f"Erro ao enviar e-mail de notificação: {e}")
            logging.error(f"Erro ao enviar e-mail de notificação: {e}")
            return False

    def enviar_email_objecao_consultor(self, destinatario: str, objecao: dict, anexos: list):
        """
        Envia e-mail para consultor com documentos do serviço jurídico.
        """
        # Verificar parâmetros
        if not destinatario or not destinatario.strip():
            st.error("Destinatário não fornecido para e-mail do consultor.")
            return False

        if not objecao:
            st.error(
                "Dados do serviço jurídico não fornecidos para e-mail do consultor.")
            return False

        marca = objecao.get('marca', 'N/A')
        nomecliente = objecao.get('nomecliente', 'N/A')

        # Processos e contratos
        processo_list = objecao.get('processo', [])
        ncontrato_list = objecao.get('ncontrato', [])

        # Criar lista de processos com contratos
        processos_info = []
        for i, (processo, contrato) in enumerate(zip(processo_list, ncontrato_list), 1):
            processos_info.append(
                f"Processo {i}: {processo} - Contrato: {contrato}")

        processos_text = '<br>'.join(
            processos_info) if processos_info else 'N/A'

        subject = f"Documentos do Serviço Jurídico - {marca} - Cliente: {nomecliente}"

        # Adicionar observação se existir
        observacao = objecao.get('observacao', '')
        observacao_html = ""
        if observacao:
            observacao_html = f"<p><b>Observação:</b> {observacao}</p>"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Documentos do Serviço Jurídico</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nomecliente}</p>
            <p><b>Serviço:</b> {objecao.get('servico', 'N/A')}</p>
            <p><b>Processos:</b><br>{processos_text}</p>
            {observacao_html}
            <p>Os documentos estão anexados a este e-mail.</p>
        </div>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = destinatario
        msg.set_content(body_html, subtype='html')

        # Adicionar anexos se fornecidos
        if anexos:
            for anexo in anexos:
                if isinstance(anexo, dict) and 'content' in anexo and 'filename' in anexo:
                    maintype, subtype = self._detectar_tipo_mime(
                        anexo['filename'])
                    msg.add_attachment(
                        anexo['content'],
                        maintype=maintype,
                        subtype=subtype,
                        filename=anexo['filename']
                    )
                else:
                    logging.warning(f"Anexo inválido ignorado: {anexo}")

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(
                f"E-mail com documentos enviado com sucesso para: {destinatario}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"Erro de autenticação SMTP: {e}")
            logging.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            st.error(f"Erro de conexão SMTP: {e}")
            logging.error(f"Erro de conexão SMTP: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"Destinatário recusado: {e}")
            logging.error(f"Destinatário recusado: {e}")
            return False
        except Exception as e:
            st.error(f"Erro ao enviar e-mail com documentos: {e}")
            logging.error(f"Erro ao enviar e-mail com documentos: {e}")
            return False

    def enviar_email_objecao_funcionario(self, destinatario: str, objecao: dict, anexos: list, supabase_agent):
        """
        Envia e-mail para funcionário com documentos do serviço jurídico.
        Usa destinatario_juridico se disponível, senão usa o destinatario fornecido.
        """
        # Verificar parâmetros
        if not destinatario or not destinatario.strip():
            st.error("Destinatário não fornecido para e-mail do funcionário.")
            return False

        if not objecao:
            st.error(
                "Dados do serviço jurídico não fornecidos para e-mail do funcionário.")
            return False

        marca = objecao.get('marca', 'N/A')
        nomecliente = objecao.get('nomecliente', 'N/A')

        # Buscar nome do consultor
        consultor_nome = "N/A"
        try:
            consultor_id = objecao.get('consultor_objecao')
            if consultor_id:
                consultor_nome = supabase_agent.get_consultor_name_by_id(
                    consultor_id, st.session_state.get('jwt_token', ''))
        except Exception as e:
            st.warning(f"Erro ao buscar nome do consultor: {str(e)}")

        # Processos e contratos
        processo_list = objecao.get('processo', [])
        ncontrato_list = objecao.get('ncontrato', [])

        # Criar lista de processos com contratos
        processos_info = []
        for i, (processo, contrato) in enumerate(zip(processo_list, ncontrato_list), 1):
            processos_info.append(
                f"Processo {i}: {processo} - Contrato: {contrato}")

        processos_text = '<br>'.join(
            processos_info) if processos_info else 'N/A'

        subject = f"Documentos do Serviço Jurídico - {marca} - Cliente: {nomecliente}"

        # Adicionar observação se existir
        observacao = objecao.get('observacao', '')
        observacao_html = ""
        if observacao:
            observacao_html = f"<p><b>Observação:</b> {observacao}</p>"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Documentos do Serviço Jurídico</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nomecliente}</p>
            <p><b>Serviço:</b> {objecao.get('servico', 'N/A')}</p>
            <p><b>Consultor Responsável:</b> {consultor_nome}</p>
            <p><b>Processos:</b><br>{processos_text}</p>
            {observacao_html}
            <p>Os documentos estão anexados a este e-mail.</p>
        </div>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user

        # Usar o destinatario fornecido diretamente (já é o email correto)
        email_destino = destinatario

        msg["To"] = email_destino
        msg.set_content(body_html, subtype='html')

        # Adicionar anexos se fornecidos
        if anexos:
            for anexo in anexos:
                if isinstance(anexo, dict) and 'content' in anexo and 'filename' in anexo:
                    maintype, subtype = self._detectar_tipo_mime(
                        anexo['filename'])
                    msg.add_attachment(
                        anexo['content'],
                        maintype=maintype,
                        subtype=subtype,
                        filename=anexo['filename']
                    )
                else:
                    logging.warning(f"Anexo inválido ignorado: {anexo}")

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(
                f"E-mail com documentos enviado com sucesso para: {email_destino}")

            # Aviso específico para o jurídico
            st.info(
                "📧 **Notificação enviada ao funcionário responsável.** Os destinatários foram notificados sobre os documentos enviados.")

            return True
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"Erro de autenticação SMTP: {e}")
            logging.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            st.error(f"Erro de conexão SMTP: {e}")
            logging.error(f"Erro de conexão SMTP: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"Destinatário recusado: {e}")
            logging.error(f"Destinatário recusado: {e}")
            return False
        except Exception as e:
            st.error(f"Erro ao enviar e-mail com documentos: {e}")
            logging.error(f"Erro ao enviar e-mail com documentos: {e}")
            return False

    def enviar_emails_objecao_completa(self, objecao: dict, anexos: list, supabase_agent):
        """
        Envia e-mails para consultor, destinatário jurídico e destinatário jurídico adicional.
        Retorna lista de e-mails enviados com sucesso.
        """
        emails_enviados = []

        # Verificar se os parâmetros necessários estão presentes
        if not objecao:
            st.error("Dados do serviço jurídico não fornecidos.")
            return emails_enviados

        if not supabase_agent:
            st.error("Supabase agent não fornecido.")
            return emails_enviados

        # 1. Enviar e-mail para o consultor responsável
        consultor_id = objecao.get('consultor_objecao')
        if consultor_id:
            try:
                # Buscar e-mail do consultor no banco de dados
                jwt_token = st.session_state.get('jwt_token', '')
                consultor_email = supabase_agent.get_consultor_email_by_id(
                    consultor_id, jwt_token)

                if consultor_email and consultor_email != 'N/A':
                    resultado = self.enviar_email_objecao_consultor(
                        consultor_email,
                        objecao,
                        anexos
                    )

                    if resultado:
                        emails_enviados.append(
                            f"consultor ({consultor_email})")
                else:
                    st.warning(
                        f"E-mail do consultor não encontrado para o ID: {consultor_id}")
            except Exception as e:
                st.warning(f"Erro ao enviar e-mail para consultor: {str(e)}")
        else:
            st.warning(
                "ID do consultor não encontrado no serviço jurídico.")

        # 2. Enviar e-mail para destinatário jurídico
        if self.destinatario_juridico:
            try:
                resultado = self.enviar_email_objecao_consultor(
                    self.destinatario_juridico,
                    objecao,
                    anexos
                )

                if resultado:
                    emails_enviados.append(
                        f"destinatário jurídico ({self.destinatario_juridico})")
            except Exception as e:
                st.warning(
                    f"Erro ao enviar e-mail para destinatário jurídico: {str(e)}")
        else:
            st.warning(
                "⚠️ Destinatário jurídico não configurado. E-mail não será enviado.")

        # 3. Enviar e-mail para destinatário jurídico adicional
        if self.destinatario_juridico_um:
            try:
                resultado = self.enviar_email_objecao_consultor(
                    self.destinatario_juridico_um,
                    objecao,
                    anexos
                )

                if resultado:
                    emails_enviados.append(
                        f"destinatário jurídico adicional ({self.destinatario_juridico_um})")
            except Exception as e:
                st.warning(
                    f"Erro ao enviar e-mail para destinatário jurídico adicional: {str(e)}")
        else:
            st.warning(
                "⚠️ Destinatário jurídico adicional não configurado. E-mail não será enviado.")

        return emails_enviados

    def enviar_email_objecao_aprov_teor(self, destinatario: str, objecao: dict, anexos: list, supabase_agent):
        """
        Envia e-mail para aprova_teor com documentos do serviço jurídico.
        Inclui informações do funcionário e consultor para aprovação.
        """
        # Verificar parâmetros
        if not destinatario or not destinatario.strip():
            st.error("Destinatário não fornecido para e-mail de aprova_teor.")
            return False

        if not objecao:
            st.error(
                "Dados do serviço jurídico não fornecidos para e-mail de aprova_teor.")
            return False

        marca = objecao.get('marca', 'N/A')
        nomecliente = objecao.get('nomecliente', 'N/A')

        # Processos e contratos
        processo_list = objecao.get('processo', [])
        ncontrato_list = objecao.get('ncontrato', [])

        # Criar lista de processos com contratos
        processos_info = []
        for i, (processo, contrato) in enumerate(zip(processo_list, ncontrato_list), 1):
            processos_info.append(
                f"Processo {i}: {processo} - Contrato: {contrato}")

        processos_text = '<br>'.join(
            processos_info) if processos_info else 'N/A'

        # Buscar informações do funcionário e consultor
        funcionario_nome = "N/A"
        funcionario_email = "N/A"
        consultor_nome = "N/A"

        try:
            # Buscar nome e e-mail do funcionário
            juridico_id = objecao.get('juridico_id')
            if juridico_id:
                funcionario_nome = supabase_agent.get_juridico_name_by_id(
                    juridico_id, st.session_state.get('jwt_token', ''))
                funcionario_email = supabase_agent.get_user_email_by_id(
                    juridico_id)

            # Buscar nome do consultor
            consultor_id = objecao.get('consultor_objecao')
            if consultor_id:
                consultor_nome = supabase_agent.get_consultor_name_by_id(
                    consultor_id, st.session_state.get('jwt_token', ''))
        except Exception as e:
            st.warning(f"Erro ao buscar informações adicionais: {str(e)}")

        subject = f"Documentos para Aprovação de Teor - {marca} - Cliente: {nomecliente}"

        # Adicionar observação se existir
        observacao = objecao.get('observacao', '')
        observacao_html = ""
        if observacao:
            observacao_html = f"<p><b>Observação:</b> {observacao}</p>"

        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>Documentos para Aprovação de Teor</h3>
            <p><b>Marca:</b> {marca}</p>
            <p><b>Cliente:</b> {nomecliente}</p>
            <p><b>Serviço:</b> {objecao.get('servico', 'N/A')}</p>
            <p><b>Processos:</b><br>{processos_text}</p>
            {observacao_html}
            <hr style='margin: 20px 0; border: 1px solid #ccc;'>
            <h4>Informações para Aprovação:</h4>
            <p><b>Funcionário Responsável:</b> {funcionario_nome}</p>
            <p><b>E-mail do Funcionário:</b> {funcionario_email}</p>
            <p><b>Consultor Responsável:</b> {consultor_nome}</p>
            <p><b>Instruções:</b> Após revisar os documentos anexados, encaminhe o e-mail de aprovação para o funcionário responsável.</p>
            <p>Os documentos estão anexados a este e-mail.</p>
        </div>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = destinatario
        msg.set_content(body_html, subtype='html')

        # Adicionar anexos se fornecidos
        if anexos:
            for anexo in anexos:
                if isinstance(anexo, dict) and 'content' in anexo and 'filename' in anexo:
                    maintype, subtype = self._detectar_tipo_mime(
                        anexo['filename'])
                    msg.add_attachment(
                        anexo['content'],
                        maintype=maintype,
                        subtype=subtype,
                        filename=anexo['filename']
                    )
                else:
                    logging.warning(f"Anexo inválido ignorado: {anexo}")

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            st.success(
                f"E-mail para aprovação enviado com sucesso para: {destinatario}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"Erro de autenticação SMTP: {e}")
            logging.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            st.error(f"Erro de conexão SMTP: {e}")
            logging.error(f"Erro de conexão SMTP: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            st.error(f"Destinatário recusado: {e}")
            logging.error(f"Destinatário recusado: {e}")
            return False
        except Exception as e:
            st.error(f"Erro ao enviar e-mail para aprovação: {e}")
            logging.error(f"Erro ao enviar e-mail para aprovação: {e}")
            return False
