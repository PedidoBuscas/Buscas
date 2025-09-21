import streamlit as st
import smtplib
from email.message import EmailMessage
import logging
import re
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from datetime import datetime, timedelta


class IMAPAgent:
    """Agente para gerenciar conexões IMAP e leitura de e-mails"""

    def __init__(self, imap_host, imap_port, imap_user, imap_pass):
        """
        Inicializa o agente IMAP com as configurações do servidor.

        Args:
            imap_host: Servidor IMAP (ex: imap.hostinger.com)
            imap_port: Porta IMAP (ex: 993 para SSL)
            imap_user: Usuário/e-mail
            imap_pass: Senha
        """
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.imap_user = imap_user
        self.imap_pass = imap_pass
        self.connection = None

    def conectar(self):
        """Conecta ao servidor IMAP"""
        try:
            if self.imap_port == 993:
                # Usar SSL para porta 993
                self.connection = imaplib.IMAP4_SSL(
                    self.imap_host, self.imap_port)
            else:
                # Usar conexão normal para outras portas
                self.connection = imaplib.IMAP4(self.imap_host, self.imap_port)
                self.connection.starttls()

            # Fazer login
            self.connection.login(self.imap_user, self.imap_pass)
            st.success(
                f"Conectado ao servidor IMAP: {self.imap_host}:{self.imap_port}")
            return True

        except Exception as e:
            st.error(f"Erro ao conectar ao servidor IMAP: {e}")
            logging.error(f"Erro ao conectar ao servidor IMAP: {e}")
            return False

    def desconectar(self):
        """Desconecta do servidor IMAP"""
        if self.connection:
            try:
                self.connection.logout()
                self.connection = None
                st.info("Desconectado do servidor IMAP")
            except Exception as e:
                st.warning(f"Erro ao desconectar: {e}")

    def listar_caixas(self):
        """Lista todas as caixas de entrada disponíveis"""
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return []

        try:
            status, caixas = self.connection.list()
            if status == 'OK':
                caixas_list = []
                for caixa in caixas:
                    # Decodificar nome da caixa
                    caixa_decoded = caixa.decode('utf-8')
                    caixas_list.append(caixa_decoded)
                return caixas_list
            else:
                st.error("Erro ao listar caixas de entrada")
                return []
        except Exception as e:
            st.error(f"Erro ao listar caixas: {e}")
            return []

    def selecionar_caixa(self, caixa="INBOX"):
        """Seleciona uma caixa de entrada específica"""
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return False

        try:
            status, messages = self.connection.select(caixa)
            if status == 'OK':
                st.success(f"Caixa '{caixa}' selecionada")
                return True
            else:
                st.error(f"Erro ao selecionar caixa '{caixa}'")
                return False
        except Exception as e:
            st.error(f"Erro ao selecionar caixa: {e}")
            return False

    def buscar_emails(self, criterio="ALL", limite=10):
        """
        Busca e-mails na caixa selecionada

        Args:
            criterio: Critério de busca (ALL, UNSEEN, FROM "email@exemplo.com", etc.)
            limite: Número máximo de e-mails a retornar
        """
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return []

        try:
            status, message_numbers = self.connection.search(None, criterio)
            if status != 'OK':
                st.error("Erro ao buscar e-mails")
                return []

            email_list = message_numbers[0].split()
            emails = []

            # Pegar apenas os últimos 'limite' e-mails
            for num in email_list[-limite:]:
                try:
                    status, msg_data = self.connection.fetch(num, '(RFC822)')
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)

                        # Extrair informações do e-mail
                        email_info = self._extrair_info_email(
                            email_message, num)
                        emails.append(email_info)

                except Exception as e:
                    st.warning(f"Erro ao processar e-mail {num}: {e}")
                    continue

            return emails

        except Exception as e:
            st.error(f"Erro ao buscar e-mails: {e}")
            return []

    def _extrair_info_email(self, email_message, num):
        """Extrai informações básicas de um e-mail"""
        try:
            # Assunto
            subject = decode_header(email_message["subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            # Remetente
            from_addr = decode_header(email_message["from"])[0][0]
            if isinstance(from_addr, bytes):
                from_addr = from_addr.decode()

            # Data
            date_str = email_message["date"]
            if date_str:
                try:
                    date_obj = parsedate_to_datetime(date_str)
                    date_formatted = date_obj.strftime("%d/%m/%Y %H:%M")
                except:
                    date_formatted = date_str
            else:
                date_formatted = "Data não disponível"

            # Verificar se tem anexos
            has_attachments = self._tem_anexos(email_message)

            return {
                'numero': num.decode() if isinstance(num, bytes) else str(num),
                'assunto': subject or "Sem assunto",
                'remetente': from_addr or "Remetente desconhecido",
                'data': date_formatted,
                'tem_anexos': has_attachments,
                'mensagem': email_message
            }

        except Exception as e:
            st.warning(f"Erro ao extrair informações do e-mail: {e}")
            return {
                'numero': num.decode() if isinstance(num, bytes) else str(num),
                'assunto': "Erro ao processar",
                'remetente': "Desconhecido",
                'data': "Desconhecida",
                'tem_anexos': False,
                'mensagem': email_message
            }

    def _tem_anexos(self, email_message):
        """Verifica se o e-mail tem anexos"""
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is not None:
                return True
        return False

    def ler_email_completo(self, numero_email):
        """Lê o conteúdo completo de um e-mail específico"""
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return None

        try:
            status, msg_data = self.connection.fetch(numero_email, '(RFC822)')
            if status != 'OK':
                st.error("Erro ao buscar e-mail")
                return None

            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            # Extrair informações completas
            email_completo = self._extrair_info_email(
                email_message, numero_email)

            # Extrair corpo do e-mail
            email_completo['corpo_texto'] = self._extrair_corpo_texto(
                email_message)
            email_completo['corpo_html'] = self._extrair_corpo_html(
                email_message)
            email_completo['anexos'] = self._extrair_anexos(email_message)

            return email_completo

        except Exception as e:
            st.error(f"Erro ao ler e-mail completo: {e}")
            return None

    def _extrair_corpo_texto(self, email_message):
        """Extrai o corpo do e-mail em texto simples"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode()
                    except:
                        return part.get_payload()
        else:
            try:
                return email_message.get_payload(decode=True).decode()
            except:
                return email_message.get_payload()
        return "Corpo não disponível"

    def _extrair_corpo_html(self, email_message):
        """Extrai o corpo do e-mail em HTML"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    try:
                        return part.get_payload(decode=True).decode()
                    except:
                        return part.get_payload()
        else:
            if email_message.get_content_type() == "text/html":
                try:
                    return email_message.get_payload(decode=True).decode()
                except:
                    return email_message.get_payload()
        return None

    def _extrair_anexos(self, email_message):
        """Extrai anexos do e-mail"""
        anexos = []

        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                # Decodificar nome do arquivo se necessário
                if isinstance(filename, bytes):
                    filename = filename.decode()

                # Extrair conteúdo do anexo
                try:
                    anexo_content = part.get_payload(decode=True)
                    anexos.append({
                        'nome': filename,
                        'conteudo': anexo_content,
                        'tipo': part.get_content_type(),
                        'tamanho': len(anexo_content) if anexo_content else 0
                    })
                except Exception as e:
                    st.warning(f"Erro ao extrair anexo {filename}: {e}")

        return anexos

    def marcar_como_lido(self, numero_email):
        """Marca um e-mail como lido"""
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return False

        try:
            self.connection.store(numero_email, '+FLAGS', '\\Seen')
            st.success("E-mail marcado como lido")
            return True
        except Exception as e:
            st.error(f"Erro ao marcar e-mail como lido: {e}")
            return False

    def deletar_email(self, numero_email):
        """Deleta um e-mail"""
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return False

        try:
            self.connection.store(numero_email, '+FLAGS', '\\Deleted')
            self.connection.expunge()
            st.success("E-mail deletado")
            return True
        except Exception as e:
            st.error(f"Erro ao deletar e-mail: {e}")
            return False

    def buscar_emails_por_data(self, data_inicio, data_fim, limite=50):
        """
        Busca e-mails por período de data

        Args:
            data_inicio: Data de início (datetime)
            data_fim: Data de fim (datetime)
            limite: Número máximo de e-mails
        """
        if not self.connection:
            st.error("Não conectado ao servidor IMAP")
            return []

        try:
            # Formatar datas para critério IMAP
            data_inicio_str = data_inicio.strftime("%d-%b-%Y")
            data_fim_str = data_fim.strftime("%d-%b-%Y")

            criterio = f'SINCE "{data_inicio_str}" BEFORE "{data_fim_str}"'
            return self.buscar_emails(criterio, limite)

        except Exception as e:
            st.error(f"Erro ao buscar e-mails por data: {e}")
            return []


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

        # Criar agente IMAP com as mesmas credenciais
        self.imap_agent = IMAPAgent(smtp_host.replace(
            'smtp', 'imap'), 993, smtp_user, smtp_pass)

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

            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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

    def send_email_confirmacao_consultor(self, consultor_email: str, form_data: dict):
        """
        Envia e-mail de confirmação para o consultor informando que sua busca foi enviada.
        """
        if not consultor_email or not consultor_email.strip():
            st.warning(
                "E-mail do consultor não disponível para envio de confirmação.")
            return False

        # Limpar form_data para remover objetos não serializáveis
        def clean_form_data(data):
            if isinstance(data, dict):
                cleaned = {}
                for key, value in data.items():
                    # Pular objetos UploadedFile e outros não serializáveis
                    if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                        continue
                    elif isinstance(value, (dict, list)):
                        cleaned[key] = clean_form_data(value)
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        cleaned[key] = value
                    else:
                        # Converter outros tipos para string
                        cleaned[key] = str(value)
                return cleaned
            elif isinstance(data, list):
                return [clean_form_data(item) for item in data if not hasattr(item, 'getvalue')]
            else:
                return data

        # Limpar form_data antes de processar
        clean_data = clean_form_data(form_data)

        # Extrair dados principais
        tipo_busca = clean_data.get('tipo_busca', '')
        consultor = clean_data.get('consultor', '')
        cpf_cnpj_cliente = clean_data.get('cpf_cnpj_cliente', '')
        nome_cliente = clean_data.get('nome_cliente', '')
        marcas = clean_data.get('marcas', [])
        nome_marca = ''
        classes = ''
        if marcas and isinstance(marcas, list) and len(marcas) > 0 and isinstance(marcas[0], dict):
            nome_marca = marcas[0].get('marca', '')
            classes = ', '.join([c.get('classe', '') for c in marcas[0].get(
                'classes', []) if c.get('classe', '')])
        data_br = clean_data.get('data', '')

        subject = f"Confirmação - Busca de marca {tipo_busca} enviada - {nome_marca}"

        # Montar corpo HTML específico para o consultor
        body_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <h3>✅ Confirmação de Envio - Busca de Marca</h3>
            <p>Olá <b>{consultor}</b>,</p>
            <p>Sua solicitação de busca de marca foi <b>enviada com sucesso</b> e está sendo processada.</p>
            
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;'>
                <h4>📋 Detalhes da Busca:</h4>
                <p><b>Data:</b> {data_br}</p>
                <p><b>Tipo de busca:</b> {tipo_busca}</p>
                <p><b>Cliente:</b> {nome_cliente}</p>
                <p><b>CPF/CNPJ:</b> {cpf_cnpj_cliente}</p>
                <p><b>Marca:</b> {nome_marca}</p>
                <p><b>Classes:</b> {classes}</p>
            </div>
            
            <p>📧 <b>Notificação:</b> Um e-mail foi enviado para a equipe responsável com todos os detalhes da sua solicitação.</p>
            
            <p>⏱️ <b>Prazo:</b> Você será notificado assim que a busca for concluída.</p>
            
            <p>Agradecemos sua confiança!</p>
            
            <hr style='margin: 20px 0; border: 1px solid #ccc;'>
            <p style='font-size: 10pt; color: #666;'>
                Este é um e-mail automático. Por favor, não responda a esta mensagem.
            </p>
        </div>
        """

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = consultor_email
        msg.set_content(body_html, subtype='html')

        try:
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)

            st.success(
                f"✅ E-mail de confirmação enviado para: {consultor_email}")
            return True
        except Exception as e:
            st.error(f"Erro ao enviar e-mail de confirmação: {e}")
            logging.error(f"Erro ao enviar e-mail de confirmação: {e}")
            return False

    def send_email(self, form_data):
        """
        Envia um e-mail com os dados do formulário de busca para os destinatários configurados.
        """
        if not self.destinatarios:
            st.warning("Nenhum destinatário configurado para envio de e-mail")
            return

        # Limpar form_data para remover objetos não serializáveis
        def clean_form_data(data):
            if isinstance(data, dict):
                cleaned = {}
                for key, value in data.items():
                    # Pular objetos UploadedFile e outros não serializáveis
                    if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                        continue
                    elif isinstance(value, (dict, list)):
                        cleaned[key] = clean_form_data(value)
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        cleaned[key] = value
                    else:
                        # Converter outros tipos para string
                        cleaned[key] = str(value)
                return cleaned
            elif isinstance(data, list):
                return [clean_form_data(item) for item in data if not hasattr(item, 'getvalue')]
            else:
                return data

        # Limpar form_data antes de processar
        clean_data = clean_form_data(form_data)

        # Extrair dados principais
        tipo_busca = clean_data.get('tipo_busca', '')
        consultor = clean_data.get('consultor', '')
        cpf_cnpj_cliente = clean_data.get('cpf_cnpj_cliente', '')
        nome_cliente = clean_data.get('nome_cliente', '')
        marcas = clean_data.get('marcas', [])
        nome_marca = ''
        classes = ''
        if marcas and isinstance(marcas, list) and len(marcas) > 0 and isinstance(marcas[0], dict):
            nome_marca = marcas[0].get('marca', '')
            classes = ', '.join([c.get('classe', '') for c in marcas[0].get(
                'classes', []) if c.get('classe', '')])
        data_br = clean_data.get('data', '')
        # Montar título conforme solicitado, incluindo a data brasileira e dados do cliente
        subject = f"Pedido de busca de marca {tipo_busca} - Data: {data_br} - Marca: {nome_marca} - Classes: {classes} - Cliente: {nome_cliente} - Consultor: {consultor}"
        # Montar corpo HTML
        body_html = self.format_body_html(clean_data)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(self.destinatarios)
        msg.set_content(body_html, subtype='html')
        try:
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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

    def format_body_html(self, form_data):
        """
        Formata o corpo do e-mail em HTML com base nos dados do formulário.
        Agora cada classe aparece separada e as especificações aparecem em linha, separadas por vírgula.
        Aplica limpeza automática de quebras de palavras.
        """
        # Limpar form_data para remover objetos não serializáveis
        def clean_form_data(data):
            if isinstance(data, dict):
                cleaned = {}
                for key, value in data.items():
                    # Pular objetos UploadedFile e outros não serializáveis
                    if hasattr(value, 'getvalue') or hasattr(value, 'read'):
                        continue
                    elif isinstance(value, (dict, list)):
                        cleaned[key] = clean_form_data(value)
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        cleaned[key] = value
                    else:
                        # Converter outros tipos para string
                        cleaned[key] = str(value)
                return cleaned
            elif isinstance(data, list):
                return [clean_form_data(item) for item in data if not hasattr(item, 'getvalue')]
            else:
                return data

        # Limpar form_data antes de processar
        clean_data = clean_form_data(form_data)

        data = clean_data.get('data', '')
        tipo_busca = clean_data.get('tipo_busca', '')
        consultor = clean_data.get('consultor', '')
        consultor_email = clean_data.get('consultor_email', '')
        cpf_cnpj_cliente = clean_data.get('cpf_cnpj_cliente', '')
        nome_cliente = clean_data.get('nome_cliente', '')
        marcas = clean_data.get('marcas', [])
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

            # Filtrar apenas classes que foram preenchidas
            classes_preenchidas = []
            for classe in marcas[0].get('classes', []):
                classe_num = classe.get('classe', '').strip()
                especificacao = classe.get('especificacao', '').strip()

                # Incluir apenas se tanto a classe quanto a especificação foram preenchidas
                if classe_num and especificacao:
                    classes_preenchidas.append((classe_num, especificacao))

            # Exibir apenas as classes preenchidas
            for jdx, (classe_num, especificacao) in enumerate(classes_preenchidas, 1):
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
            # Usar SMTP_SSL para porta 465 (Hostinger)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # Usar SMTP normal com STARTTLS para outras portas
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
