import streamlit as st
from supabase_agent import SupabaseAgent
from datetime import datetime
import json
import unicodedata
import re


class PatenteManager:
    """Gerencia operações relacionadas às patentes"""

    # Status possíveis para as patentes
    STATUS_PENDENTE = "pendente"
    STATUS_RECEBIDO = "recebido"
    STATUS_FAZENDO_RELATORIO = "fazendo_relatorio"
    STATUS_RELATORIO_CONCLUIDO = "relatorio_concluido"

    def __init__(self, supabase_agent, email_agent):
        self.supabase_agent = supabase_agent
        self.email_agent = email_agent

    def atualizar_status_patente(self, patente_id: str, novo_status: str) -> bool:
        """
        Atualiza o status de uma patente.
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        ok = self.supabase_agent.update_patente_status(
            patente_id, novo_status, st.session_state.jwt_token)
        if ok:
            status_text = self.supabase_agent.get_patente_status_display(
                novo_status)
            st.success(f"Status da patente atualizado para: {status_text}")
            return True
        else:
            st.error("Erro ao atualizar status da patente!")
            return False

    def get_status_atual(self, patente: dict) -> str:
        """
        Determina o status atual baseado em status_patente persistente no banco.
        """
        status = patente.get('status_patente', self.STATUS_PENDENTE)
        if status not in [self.STATUS_PENDENTE, self.STATUS_RECEBIDO, self.STATUS_FAZENDO_RELATORIO, self.STATUS_RELATORIO_CONCLUIDO]:
            return self.STATUS_PENDENTE
        return status

    def separar_patentes_por_status(self, patentes: list) -> dict:
        """
        Separa as patentes em listas por status.
        Retorna um dicionário: {status: [patentes]}
        """
        status_dict = {
            self.STATUS_PENDENTE: [],
            self.STATUS_RECEBIDO: [],
            self.STATUS_FAZENDO_RELATORIO: [],
            self.STATUS_RELATORIO_CONCLUIDO: []
        }
        for patente in patentes:
            status = self.get_status_atual(patente)
            if status in status_dict:
                status_dict[status].append(patente)
        return status_dict

    def enviar_relatorio_patente(self, patente: dict, uploaded_files: list) -> bool:
        """
        Envia relatório da patente para consultor e funcionário.
        """
        try:
            # Normalizar nome do arquivo
            def normalize_filename(filename):
                filename = unicodedata.normalize('NFKD', filename).encode(
                    'ASCII', 'ignore').decode('ASCII')
                filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
                return filename

            # Upload dos PDFs
            pdf_urls = []
            for file in uploaded_files:
                file_name = normalize_filename(f"{patente['id']}_{file.name}")
                url = self.supabase_agent.upload_pdf_to_storage(
                    file, file_name, st.session_state.jwt_token, bucket="patentepdf")
                pdf_urls.append(url)

            # Preparar dados do relatório para salvar no Supabase
            relatorio_data = {
                "pdf_urls": pdf_urls,
                "data_envio": datetime.now().isoformat(),
                "arquivos": [{"nome": file.name, "url": url} for file, url in zip(uploaded_files, pdf_urls)]
            }

            # Atualizar relatorio_patente no banco
            self.supabase_agent.update_patente_relatorio(
                patente['id'], relatorio_data, st.session_state.jwt_token)

            # Preparar anexos para e-mail
            anexos = []
            for file in uploaded_files:
                pdf_bytes = file.getvalue()
                email_file_name = normalize_filename(file.name)
                anexos.append((pdf_bytes, email_file_name))

            # Enviar e-mail para consultor
            email_consultor = patente.get('email_consultor', '').strip()
            if email_consultor:
                titulo = patente.get('titulo', '')
                cliente = patente.get('cliente', '')
                consultor_nome = patente.get('name_consultor', '')
                servico = patente.get('servico', '')

                assunto = f"Relatório de Patente Concluído - {titulo} ({cliente})"
                corpo = f"""
                <div style='font-family: Arial; font-size: 12pt;'>
                Olá {consultor_nome},<br><br>
                Segue em anexo o relatório da patente solicitada.<br><br>
                <b>Dados da patente:</b><br>
                - Título: {titulo}<br>
                - Cliente: {cliente}<br>
                - Serviço: {servico}<br>
                - Processo: {patente.get('processo', '')}<br>
                - Natureza: {patente.get('natureza', '')}<br>
                - Contrato: {patente.get('ncontrato', '')}<br><br>
                Atenciosamente,<br>
                Equipe AGP Consultoria
                </div>
                """

                if len(anexos) > 1:
                    self.email_agent.send_email_multiplos_anexos(
                        destinatario=email_consultor,
                        assunto=assunto,
                        corpo=corpo,
                        anexos=anexos
                    )
                else:
                    self.email_agent.send_email_com_anexo(
                        destinatario=email_consultor,
                        assunto=assunto,
                        corpo=corpo,
                        anexo_bytes=anexos[0][0],
                        nome_arquivo=anexos[0][1]
                    )

            # Enviar e-mail para funcionário
            email_funcionario = patente.get('email_funcionario', '').strip()
            if email_funcionario:
                titulo = patente.get('titulo', '')
                cliente = patente.get('cliente', '')
                funcionario_nome = patente.get('name_funcionario', '')
                servico = patente.get('servico', '')

                assunto = f"Relatório de Patente Concluído - {titulo} ({cliente})"
                corpo = f"""
                <div style='font-family: Arial; font-size: 12pt;'>
                Olá {funcionario_nome},<br><br>
                Segue em anexo o relatório da patente que você cadastrou.<br><br>
                <b>Dados da patente:</b><br>
                - Título: {titulo}<br>
                - Cliente: {cliente}<br>
                - Serviço: {servico}<br>
                - Processo: {patente.get('processo', '')}<br>
                - Natureza: {patente.get('natureza', '')}<br>
                - Contrato: {patente.get('ncontrato', '')}<br><br>
                Atenciosamente,<br>
                Equipe AGP Consultoria
                </div>
                """

                if len(anexos) > 1:
                    self.email_agent.send_email_multiplos_anexos(
                        destinatario=email_funcionario,
                        assunto=assunto,
                        corpo=corpo,
                        anexos=anexos
                    )
                else:
                    self.email_agent.send_email_com_anexo(
                        destinatario=email_funcionario,
                        assunto=assunto,
                        corpo=corpo,
                        anexo_bytes=anexos[0][0],
                        nome_arquivo=anexos[0][1]
                    )

            return True
        except Exception as e:
            st.error(f"Erro ao enviar relatório: {e}")
            return False


MODULO_INFO = {
    "nome": "Patentes",
    "emoji": "📄",
    "opcoes": ["Solicitar Busca", "Minhas Buscas"]
}


def solicitar_busca():
    st.header("Solicitar Busca de Patente")
    st.info("Funcionalidade de solicitação de busca de patente em breve!")


def minhas_buscas():
    st.header("Minhas Buscas de Patente")
    st.info("Funcionalidade de visualização de buscas de patente em breve!")


def solicitar_patente():
    st.info("Funcionalidade de solicitação de patente em breve!")


def minhas_patentes(email_agent):
    st.header("Minhas Patentes")
    supabase_agent = SupabaseAgent()
    patente_manager = PatenteManager(supabase_agent, email_agent)

    if "user" not in st.session_state:
        st.error("Usuário não autenticado.")
        return

    user_id = st.session_state.user['id'] if isinstance(
        st.session_state.user, dict) else st.session_state.user.id

    # Verificar se é funcionário e se tem permissões de admin
    funcionario = supabase_agent.get_funcionario_by_id(user_id)
    is_admin = funcionario and funcionario.get('is_admin', False)

    patentes = []

    # Se for funcionário, busca patentes cadastradas por ele
    if funcionario:
        patentes_funcionario = supabase_agent.get_depositos_patente_para_funcionario(
            user_id, st.session_state.jwt_token)
        if patentes_funcionario:
            patentes.extend(patentes_funcionario)

    # Se for consultor (perfil existe), busca patentes associadas a ele
    perfil = supabase_agent.get_profile(user_id)
    if perfil and not perfil.get('is_admin', False):
        patentes_consultor = supabase_agent.get_depositos_patente_para_consultor(
            user_id, st.session_state.jwt_token)
        if patentes_consultor:
            patentes.extend(patentes_consultor)

    # Se for administrador (funcionário com is_admin=true), mostra todas as patentes
    if is_admin:
        todas_patentes = supabase_agent.get_all_depositos_patente(
            st.session_state.jwt_token)
        if todas_patentes:
            patentes = todas_patentes

    if is_admin:
        # Adicionar filtro por consultor para administradores
        st.subheader("Filtros")

        # Buscar nomes únicos de consultores das patentes existentes
        consultor_nomes_unicos = set()
        for patente in patentes:
            consultor_nome = patente.get('name_consultor', '')
            if consultor_nome:
                consultor_nomes_unicos.add(consultor_nome)

        consultor_nomes = ["Todos os consultores"] + \
            sorted(list(consultor_nomes_unicos))

        consultor_filtro = st.selectbox(
            "Filtrar por consultor:",
            consultor_nomes,
            key="filtro_consultor_patentes"
        )

        # Filtrar patentes por consultor se selecionado
        if consultor_filtro and consultor_filtro != "Todos os consultores":
            patentes_filtradas = []
            for patente in patentes:
                consultor_patente = patente.get('name_consultor', '')
                if consultor_patente == consultor_filtro:
                    patentes_filtradas.append(patente)
            patentes = patentes_filtradas

            if not patentes:
                st.info(
                    f"Nenhuma patente encontrada para o consultor: {consultor_filtro}")
                return

    # Organizar patentes por status (após o filtro)
    patentes_por_status = patente_manager.separar_patentes_por_status(patentes)

    if is_admin:
        # Interface para administradores com abas por status
        abas = []
        labels = []
        status_keys = [
            (patente_manager.STATUS_PENDENTE, "Pendentes"),
            (patente_manager.STATUS_RECEBIDO, "Recebidas"),
            (patente_manager.STATUS_FAZENDO_RELATORIO, "Fazendo Relatório"),
            (patente_manager.STATUS_RELATORIO_CONCLUIDO, "Relatórios Concluídos")
        ]

        for status, label in status_keys:
            patentes_status = patentes_por_status[status]
            if patentes_status:
                labels.append(label)
                abas.append(patentes_status)

        if not abas:
            st.info("Nenhuma patente encontrada.")
            return

        tabs = st.tabs(labels)
        for i, tab in enumerate(tabs):
            with tab:
                for patente in abas[i]:
                    renderizar_patente(patente, patente_manager, is_admin)
    else:
        # Interface para usuários normais
        enviadas = (patentes_por_status[patente_manager.STATUS_PENDENTE] +
                    patentes_por_status[patente_manager.STATUS_RECEBIDO] +
                    patentes_por_status[patente_manager.STATUS_FAZENDO_RELATORIO])
        concluidas = patentes_por_status[patente_manager.STATUS_RELATORIO_CONCLUIDO]

        abas = []
        labels = []
        if enviadas:
            labels.append("Enviadas")
            abas.append(enviadas)
        if concluidas:
            labels.append("Concluídas")
            abas.append(concluidas)

        if not abas:
            st.info("Nenhuma patente encontrada.")
            return

        tabs = st.tabs(labels)
        for i, tab in enumerate(tabs):
            with tab:
                for patente in abas[i]:
                    renderizar_patente(patente, patente_manager, is_admin)


def renderizar_patente(patente, patente_manager, is_admin):
    """Renderiza uma patente individual na interface."""
    status = patente_manager.get_status_atual(patente)
    status_icon = patente_manager.supabase_agent.get_patente_status_icon(
        status)
    status_text = patente_manager.supabase_agent.get_patente_status_display(
        status)

    # Cabeçalho do expansor
    titulo = patente.get('titulo', 'Sem título')
    cliente = patente.get('cliente', '')
    processo = patente.get('processo', '')
    consultor = patente.get('name_consultor', '')

    expander_label = f"{status_icon} {titulo} - {cliente}"
    if processo:
        expander_label += f" (Proc: {processo})"
    if consultor:
        expander_label += f" - {consultor}"
    expander_label += f" - {status_text}"

    with st.expander(expander_label):
        # Exibir dados da patente
        st.markdown(f"**Título:** {patente.get('titulo', '')}")
        st.markdown(f"**Cliente:** {patente.get('cliente', '')}")
        if patente.get('processo'):
            st.markdown(f"**Processo:** {patente.get('processo', '')}")
        if patente.get('cpf_cnpj'):
            st.markdown(f"**CPF/CNPJ:** {patente.get('cpf_cnpj', '')}")
        if patente.get('nome_contato'):
            st.markdown(
                f"**Pessoa para contato:** {patente.get('nome_contato', '')}")
        if patente.get('fone_contato'):
            st.markdown(f"**Telefone:** {patente.get('fone_contato', '')}")
        if patente.get('email_contato'):
            st.markdown(f"**E-mail:** {patente.get('email_contato', '')}")
        st.markdown(f"**Contrato:** {patente.get('ncontrato', '')}")
        st.markdown(
            f"**Vencimento:** {formatar_data_br(patente.get('data_vencimento', ''))}")
        st.markdown(f"**Natureza:** {patente.get('natureza', '')}")
        st.markdown(f"**Serviço:** {patente.get('servico', '')}")
        st.markdown(f"**Funcionário:** {patente.get('name_funcionario', '')}")
        st.markdown(f"**Consultor:** {patente.get('name_consultor', '')}")
        if patente.get('observacoes'):
            st.markdown(f"**Observações:** {patente.get('observacoes', '')}")

        # Exibir links dos PDFs da patente
        pdfs = patente.get('pdf_patente')
        if pdfs:
            st.markdown("**PDF(s) da patente:**")
            for i, url in enumerate(pdfs):
                st.markdown(f"[PDF {i+1}]({url})")

        # Exibir links dos PDFs do relatório
        relatorio_data = patente.get('relatorio_patente')
        if relatorio_data:
            if isinstance(relatorio_data, str):
                try:
                    relatorio_data = json.loads(relatorio_data)
                except:
                    relatorio_data = None

            if relatorio_data and isinstance(relatorio_data, dict):
                pdf_urls = relatorio_data.get('pdf_urls', [])
                if pdf_urls:
                    st.markdown("**PDF(s) do relatório:**")
                    for i, url in enumerate(pdf_urls):
                        st.markdown(f"[Relatório {i+1}]({url})")

                    # Mostrar data de envio se disponível
                    data_envio = relatorio_data.get('data_envio')
                    if data_envio:
                        try:
                            data_br = datetime.fromisoformat(data_envio.replace(
                                'Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
                            st.markdown(f"**Enviado em:** {data_br}")
                        except:
                            pass

        # Botões de ação para administradores
        if is_admin:
            st.markdown("---")

            # Upload e envio de relatório (apenas quando status for "Fazendo Relatório" ou "Relatório Concluído")
            if status in [patente_manager.STATUS_FAZENDO_RELATORIO, patente_manager.STATUS_RELATORIO_CONCLUIDO]:
                st.write("**Upload do relatório:**")
                uploaded_files = st.file_uploader(
                    "Selecione os PDFs do relatório",
                    type=["pdf"],
                    accept_multiple_files=True,
                    key=f"relatorio_{patente['id']}"
                )

                # Se há arquivos no upload, mostrar apenas botão de enviar
                if uploaded_files and len(uploaded_files) > 0:
                    if st.button("📤 Enviar Relatório", key=f"enviar_relatorio_{patente['id']}"):
                        if patente_manager.enviar_relatorio_patente(patente, uploaded_files):
                            # Atualizar status para "Relatório Concluído" após envio bem-sucedido
                            if status == patente_manager.STATUS_FAZENDO_RELATORIO:
                                patente_manager.atualizar_status_patente(
                                    patente['id'], patente_manager.STATUS_RELATORIO_CONCLUIDO)
                            st.success("Relatório enviado com sucesso!")
                            st.rerun()
                else:
                    # Se não há arquivos, mostrar botão de status
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

                    with col1:
                        if status == patente_manager.STATUS_FAZENDO_RELATORIO:
                            if st.button("✅ Relatório Concluído", key=f"concluido_{patente['id']}"):
                                if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RELATORIO_CONCLUIDO):
                                    st.rerun()

                    with col2:
                        # Espaço reservado para futuras ações
                        pass

                    with col3:
                        # Espaço reservado para futuras ações
                        pass

                    with col4:
                        # Espaço reservado para futuras ações
                        pass
        else:
            # Para outros status, mostrar botões normais
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            with col1:
                if status == patente_manager.STATUS_PENDENTE:
                    if st.button("📥 Recebido", key=f"recebido_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RECEBIDO):
                            st.rerun()
                elif status == patente_manager.STATUS_RECEBIDO:
                    if st.button("📝 Fazendo Relatório", key=f"fazendo_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_FAZENDO_RELATORIO):
                            st.rerun()

            with col2:
                # Espaço reservado para futuras ações
                pass

            with col3:
                # Espaço reservado para futuras ações
                pass

            with col4:
                # Espaço reservado para futuras ações
                pass

        st.markdown(
            f"<div style='margin-top:8px;font-weight:600;color:#005fa3;'>Status atual: {status_icon} {status_text}</div>", unsafe_allow_html=True)


def deposito_patente(email_agent):
    st.header("Solicitar Serviço de Patente")
    from config import carregar_configuracoes
    config = carregar_configuracoes()
    destinatario_enge = config.get("destinatario_enge", "")
    supabase_agent = SupabaseAgent()

    # Verifica se há usuário na sessão e JWT token
    if "user" not in st.session_state or "jwt_token" not in st.session_state:
        st.error("Usuário não autenticado.")
        return

    user_id = st.session_state.user['id'] if isinstance(
        st.session_state.user, dict) else st.session_state.user.id

    # Verifica se o usuário está em ambas as tabelas
    if not supabase_agent.verificar_usuario_funcionario_perfil(user_id):
        st.error("Você não tem permissão para cadastrar depósitos de patente. É necessário estar cadastrado como funcionário e ter um perfil ativo.")
        return

    # Buscar funcionário logado
    funcionario = supabase_agent.get_funcionario_by_id(user_id)
    if not funcionario:
        st.error("Erro ao buscar dados do funcionário.")
        return

    # Buscar apenas consultores com cargo = 'consultor'
    consultores = supabase_agent.get_consultores_por_cargo("consultor")
    if not consultores:
        st.warning("Nenhum consultor disponível no momento.")
        return

    consultor_nomes = [c['name'] for c in consultores if c.get('name')]
    consultor_escolhido = st.selectbox(
        "Consultor responsável", consultor_nomes)
    consultor = next(
        (c for c in consultores if c['name'] == consultor_escolhido), None) if consultor_nomes else None

    # Nonce para forçar limpeza dos campos
    nonce = st.session_state.get("patente_form_nonce", 0)

    with st.form("form_deposito_patente"):
        ncontrato = st.text_input(
            "Número do contrato", key=f"ncontrato_{nonce}")
        data_vencimento = st.date_input(
            "Vencimento da primeira parcela", key=f"data_vencimento_{nonce}")
        cliente = st.text_input("Nome do cliente", key=f"cliente_{nonce}")

        # Novos campos de contato
        col1, col2 = st.columns(2)
        with col1:
            cpf_cnpj = st.text_input("CPF/CNPJ", key=f"cpf_cnpj_{nonce}")
        with col2:
            nome_contato = st.text_input(
                "Pessoa para contato", key=f"nome_contato_{nonce}")

        col3, col4 = st.columns(2)
        with col3:
            fone_contato = st.text_input(
                "Telefone para contato", key=f"fone_contato_{nonce}")
        with col4:
            email_contato = st.text_input(
                "E-mail para contato", key=f"email_contato_{nonce}")

        titulo = st.text_input("Título da patente", key=f"titulo_{nonce}")
        processo = st.text_input(
            "Processo da patente", key=f"processo_{nonce}")
        servico = st.selectbox("Serviço do contrato", [
            "Manifestação à Nulidade",
            "Alterações nos relatórios",
            "Apresentação de Subsídios ao Exame Técnico",
            "Busca de Patente",
            "Cumprimento de Exigência",
            "Depósito de Desenho Industrial",
            "Depósito de PI, MU, PCT, e etc…",
            "Recurso ao Indeferimento",
            "Manifestação Sobre Invenção",
            "Apresentação de Nulidade Administrativa em DI, PI e MU"
        ], key=f"servico_{nonce}")
        natureza = st.selectbox("Natureza da patente", [
                                "Invenção", "Modelo de Utilidade", "Desenho Industrial"], key=f"natureza_{nonce}")
        observacoes = st.text_area(
            "Observações (opcional)", key=f"observacoes_{nonce}")
        uploaded_files = st.file_uploader(
            "PDFs da patente", type=["pdf"], accept_multiple_files=True, key=f"uploaded_files_{nonce}")
        submitted = st.form_submit_button("Solicitar Serviço de Patente")

    if submitted:
        if not consultor:
            st.error("Por favor, selecione um consultor válido.")
            return

        pdf_urls = []
        if uploaded_files:
            for file in uploaded_files:
                url = supabase_agent.upload_pdf_to_storage(
                    file, file.name, st.session_state.jwt_token, bucket="patentepdf")
                pdf_urls.append(url)

        data = {
            "funcionario_id": funcionario['id'],
            "name_funcionario": funcionario['name'],
            "email_funcionario": funcionario.get('email', ''),
            "consultor": consultor['id'],
            "name_consultor": consultor['name'],
            "email_consultor": consultor.get('email', ''),
            "ncontrato": ncontrato or "",
            "data_vencimento": data_vencimento.isoformat(),
            "cliente": cliente or "",
            "cpf_cnpj": cpf_cnpj or "",
            "nome_contato": nome_contato or "",
            "fone_contato": fone_contato or "",
            "email_contato": email_contato or "",
            "titulo": titulo or "",
            "processo": processo or "",
            "servico": servico or "",
            "natureza": natureza or "",
            "observacoes": observacoes or "",
            "pdf_patente": pdf_urls if pdf_urls else [],
        }
        ok = supabase_agent.insert_deposito_patente(
            data, st.session_state.jwt_token)
        if ok:
            # Enviar e-mail para destinatario_enge
            if destinatario_enge:
                try:
                    assunto = f"Nova solicitação de serviço de patente: {servico} - {titulo} ({cliente}) - Consultor: {consultor['name']}"
                    corpo = f"""
                    <b>Solicitação de Serviço de Patente</b><br><br>
                    <b>Cliente:</b> {cliente}<br>
                    <b>CPF/CNPJ:</b> {cpf_cnpj}<br>
                    <b>Pessoa para contato:</b> {nome_contato}<br>
                    <b>Telefone:</b> {fone_contato}<br>
                    <b>E-mail:</b> {email_contato}<br>
                    <b>Título da patente:</b> {titulo}<br>
                    <b>Processo:</b> {processo}<br>
                    <b>Serviço:</b> {servico}<br>
                    <b>Natureza:</b> {natureza}<br>
                    <b>Contrato:</b> {ncontrato}<br>
                    <b>Vencimento:</b> {data_vencimento.strftime('%d/%m/%Y')}<br>
                    <b>Consultor responsável:</b> {consultor['name']}<br>
                    <b>Funcionário que cadastrou:</b> {funcionario['name']}<br>
                    <b>Observações:</b> {observacoes}<br>
                    <br><br>
                    Atenciosamente,<br>
                    Equipe AGP
                    """

                    # Se há PDFs, enviar com anexos
                    if uploaded_files and len(uploaded_files) > 0:
                        anexos = []
                        for file in uploaded_files:
                            anexos.append((file.getvalue(), file.name))
                        email_agent.send_email_multiplos_anexos(
                            destinatario_enge,
                            assunto,
                            corpo,
                            anexos
                        )
                    else:
                        # Se não há PDFs, enviar e-mail simples
                        email_agent.send_email_com_anexo(
                            destinatario_enge,
                            assunto,
                            corpo,
                            None,
                            None
                        )
                except Exception as e:
                    st.warning(
                        f"Não foi possível enviar o e-mail de notificação: {e}")
            st.session_state["patente_sucesso"] = True
            # Incrementar nonce para forçar limpeza dos campos
            st.session_state["patente_form_nonce"] = st.session_state.get(
                "patente_form_nonce", 0) + 1
            st.rerun()
        else:
            st.error("Erro ao solicitar serviço de patente.")

    if st.session_state.get("patente_sucesso"):
        st.success(
            "Serviço de patente solicitado com sucesso! O formulário foi limpo.")
        del st.session_state["patente_sucesso"]


def formatar_data_br(data_iso):
    try:
        if not data_iso:
            return ""
        if isinstance(data_iso, str):
            data = datetime.fromisoformat(data_iso)
        else:
            data = data_iso
        return data.strftime('%d/%m/%Y')
    except Exception:
        return str(data_iso)
