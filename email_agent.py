import streamlit as st
import smtplib
from email.message import EmailMessage
import logging
import re


class EmailAgent:
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_pass, destinatarios):
        """
        Inicializa o agente de e-mail com as configurações SMTP e lista de destinatários.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.destinatarios = destinatarios

    def send_email(self, form_data):
        """
        Envia um e-mail com os dados do formulário de busca para os destinatários configurados.
        """
        # Debug SMTP vars
        print("[DEBUG] SMTP_HOST:", self.smtp_host)
        print("[DEBUG] SMTP_PORT:", self.smtp_port)
        print("[DEBUG] SMTP_USER:", self.smtp_user)
        print("[DEBUG] SMTP_PASS:", self.smtp_pass)
        print("[DEBUG] DESTINATARIOS:", self.destinatarios)
        # Extrair dados principais
        tipo_busca = form_data.get('tipo_busca', '')
        consultor = form_data.get('consultor', '')
        marcas = form_data.get('marcas', [])
        nome_marca = ''
        classes = ''
        if marcas and isinstance(marcas, list) and len(marcas) > 0 and isinstance(marcas[0], dict):
            nome_marca = marcas[0].get('marca', '')
            classes = ', '.join([c.get('classe', '') for c in marcas[0].get(
                'classes', []) if c.get('classe', '')])
        data_br = form_data.get('data', '')
        # Montar título conforme solicitado, incluindo a data brasileira
        subject = f"Pedido de busca de marca {tipo_busca} - Data: {data_br} - Marca: {nome_marca} - Classes: {classes} - Consultor: {consultor}"
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
            print("[DEBUG] Erro ao enviar e-mail:", e)

    def _limpar_quebras_palavras(self, texto):
        # Remove espaços duplos
        texto = re.sub(r' +', ' ', texto)
        return texto

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
        marcas = form_data.get('marcas', [])
        html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12pt;'>
            <b>Data:</b> {data}<br>
            <b>Tipo de busca:</b> {tipo_busca}<br>
            <b>Consultor:</b> {consultor}<br>
            <b>E-mail do consultor:</b> {consultor_email}<br><br>
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
