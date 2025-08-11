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
    STATUS_AGUARDANDO_INFORMACOES = "aguardando_informacoes"
    STATUS_RELATORIO_SENDO_ELABORADO = "relatorio_sendo_elaborado"
    STATUS_RELATORIO_ENVIADO_APROVACAO = "relatorio_enviado_aprovacao"
    STATUS_RELATORIO_APROVADO = "relatorio_aprovado"
    STATUS_CONCLUIDO = "concluido"

    def __init__(self, supabase_agent, email_agent):
        self.supabase_agent = supabase_agent
        self.email_agent = email_agent

    def verificar_permissao_status_patente(self, user_id: str) -> bool:
        """
        Verifica se o usuário tem permissão para alterar status de patentes.
        Apenas usuários is_admin com cargo 'engenheiro' podem alterar status.
        """
        # Buscar funcionário
        funcionario = self.supabase_agent.get_funcionario_by_id(user_id)
        if not funcionario:
            return False

        # Verificar se é admin e tem cargo engenheiro
        is_admin = funcionario.get('is_admin', False)
        # Usar cargo_func como no permission_manager
        cargo = funcionario.get('cargo_func', 'funcionario')

        return is_admin and cargo == 'engenheiro'

    def atualizar_status_patente(self, patente_id: str, novo_status: str) -> bool:
        """
        Atualiza o status de uma patente.
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()

        # Verificar permissão para alterar status
        user_id = st.session_state.user['id'] if isinstance(
            st.session_state.user, dict) else st.session_state.user.id

        if not self.verificar_permissao_status_patente(user_id):
            st.error(
                "Você não tem permissão para alterar o status de patentes. Apenas engenheiros administradores podem fazer esta alteração.")
            return False

        ok = self.supabase_agent.update_patente_status(
            patente_id, novo_status, st.session_state.jwt_token)
        if ok:
            status_text = self.supabase_agent.get_patente_status_display(
                novo_status)
            st.success(f"Status da patente atualizado para: {status_text}")

            # Enviar e-mail quando status for alterado para "Aguardando Informações"
            if novo_status == self.STATUS_AGUARDANDO_INFORMACOES:
                self._enviar_email_aguardando_informacoes(patente_id)

            return True
        else:
            st.error("Erro ao atualizar status da patente!")
            return False

    def get_status_atual(self, patente: dict) -> str:
        """
        Determina o status atual baseado em status_patente persistente no banco.
        """
        status = patente.get('status_patente', self.STATUS_PENDENTE)
        status_validos = [
            self.STATUS_PENDENTE,
            self.STATUS_RECEBIDO,
            self.STATUS_AGUARDANDO_INFORMACOES,
            self.STATUS_RELATORIO_SENDO_ELABORADO,
            self.STATUS_RELATORIO_ENVIADO_APROVACAO,
            self.STATUS_RELATORIO_APROVADO,
            self.STATUS_CONCLUIDO
        ]
        if status not in status_validos:
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
            self.STATUS_AGUARDANDO_INFORMACOES: [],
            self.STATUS_RELATORIO_SENDO_ELABORADO: [],
            self.STATUS_RELATORIO_ENVIADO_APROVACAO: [],
            self.STATUS_RELATORIO_APROVADO: [],
            self.STATUS_CONCLUIDO: []
        }
        for patente in patentes:
            status = self.get_status_atual(patente)
            if status in status_dict:
                status_dict[status].append(patente)
        return status_dict

    def enviar_relatorio_patente(self, patente: dict, uploaded_files: list) -> bool:
        """
        Envia relatório da patente para consultor.
        """
        try:
            # Normalizar nome do arquivo
            def normalize_filename(filename):
                filename = unicodedata.normalize('NFKD', filename).encode(
                    'ASCII', 'ignore').decode('ASCII')
                filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
                return filename

            # Upload dos arquivos
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

            # Enviar e-mail APENAS para consultor
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

            return True
        except Exception as e:
            st.error(f"Erro ao enviar relatório: {e}")
            return False

    def _enviar_email_aguardando_informacoes(self, patente_id: str):
        """
        Envia e-mail para consultor e funcionário quando status é alterado para "Aguardando Informações"
        """
        try:
            # Buscar dados do engenheiro que alterou o status
            user_id = st.session_state.user['id'] if isinstance(
                st.session_state.user, dict) else st.session_state.user.id
            engenheiro = self.supabase_agent.get_funcionario_by_id(user_id)
            engenheiro_nome = engenheiro.get(
                'name', 'Engenheiro') if engenheiro else 'Engenheiro'

            # Buscar dados da patente usando as funções existentes
            # Primeiro, buscar todas as patentes do funcionário
            patentes_funcionario = self.supabase_agent.get_depositos_patente_para_funcionario(
                user_id, st.session_state.jwt_token)

            # Procurar a patente específica pelo ID
            patente = None
            if patentes_funcionario:
                for p in patentes_funcionario:
                    if p.get('id') == patente_id:
                        patente = p
                        break

            # Se não encontrou, buscar nas patentes de consultor
            if not patente:
                patentes_consultor = self.supabase_agent.get_depositos_patente_para_consultor(
                    user_id, st.session_state.jwt_token)
                if patentes_consultor:
                    for p in patentes_consultor:
                        if p.get('id') == patente_id:
                            patente = p
                            break

            # Se ainda não encontrou, buscar em todas as patentes (para admin)
            if not patente:
                todas_patentes = self.supabase_agent.get_all_depositos_patente(
                    st.session_state.jwt_token)
                if todas_patentes:
                    for p in todas_patentes:
                        if p.get('id') == patente_id:
                            patente = p
                            break

            if not patente:
                st.warning(
                    "Não foi possível buscar dados da patente para envio de e-mail")
                return

            # Dados da patente
            titulo = patente.get('titulo', '')
            cliente = patente.get('cliente', '')
            processo = patente.get('processo', '')
            consultor_nome = patente.get('name_consultor', '')
            funcionario_nome = patente.get('name_funcionario', '')
            email_consultor = patente.get('email_consultor', '').strip()
            email_funcionario = patente.get('email_funcionario', '').strip()

            assunto = f"Aguardando Informações - Patente: {titulo} ({cliente})"
            corpo = f"""
            <div style='font-family: Arial; font-size: 12pt;'>
            Olá,<br><br>
            O engenheiro {engenheiro_nome} alterou o status da patente para "Aguardando Informações".<br><br>
            <b>Dados da patente:</b><br>
            - Título: {titulo}<br>
            - Cliente: {cliente}<br>
            - Processo: {processo}<br>
            - Consultor: {consultor_nome}<br>
            - Funcionário: {funcionario_nome}<br><br>
            <b>Próximos passos:</b><br>
            É necessário fornecer documentos adicionais para que o engenheiro possa elaborar o relatório da patente.<br><br>
            Por favor, acesse o sistema e adicione os documentos necessários na seção "Aguardando Informações".<br><br>
            Atenciosamente,<br>
            Equipe AGP Consultoria
            </div>
            """

            # Enviar e-mail para consultor
            if email_consultor:
                try:
                    self.email_agent.send_email_com_anexo(
                        email_consultor,
                        assunto,
                        corpo,
                        None,  # sem anexo
                        None   # sem nome de arquivo
                    )
                    st.success(
                        f"E-mail enviado para consultor: {email_consultor}")
                except Exception as e:
                    st.warning(f"Erro ao enviar e-mail para consultor: {e}")

            # Enviar e-mail para funcionário
            if email_funcionario:
                try:
                    self.email_agent.send_email_com_anexo(
                        email_funcionario,
                        assunto,
                        corpo,
                        None,  # sem anexo
                        None   # sem nome de arquivo
                    )
                    st.success(
                        f"E-mail enviado para funcionário: {email_funcionario}")
                except Exception as e:
                    st.warning(f"Erro ao enviar e-mail para funcionário: {e}")

        except Exception as e:
            st.warning(f"Erro ao enviar e-mails de notificação: {e}")


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

    # Verificar se é engenheiro com permissões de admin (única verificação necessária)
    is_admin = funcionario and funcionario.get('is_admin', False) and funcionario.get(
        'cargo_func', 'funcionario') == 'engenheiro'

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

    # Definir todos os status possíveis com seus labels
    status_keys = [
        (patente_manager.STATUS_PENDENTE, "Pendentes"),
        (patente_manager.STATUS_RECEBIDO, "Recebidas"),
        (patente_manager.STATUS_AGUARDANDO_INFORMACOES, "Aguardando Info"),
        (patente_manager.STATUS_RELATORIO_SENDO_ELABORADO, "Elab Relatório"),
        (patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO, "Para Aprovação"),
        (patente_manager.STATUS_RELATORIO_APROVADO, "Rel Aprovado"),
        (patente_manager.STATUS_CONCLUIDO, "Concluído")
    ]

    # Criar abas para todos os status com contagem
    labels = []
    abas = []
    for status, label in status_keys:
        patentes_status = patentes_por_status[status]
        count = len(patentes_status)
        # Adicionar contagem ao label
        label_with_count = f"{label} ({count})"
        labels.append(label_with_count)
        abas.append(patentes_status)

    # Criar abas para todos os status
    tabs = st.tabs(labels)
    for i, tab in enumerate(tabs):
        with tab:
            patentes_na_aba = abas[i]
            if patentes_na_aba:
                for patente in patentes_na_aba:
                    renderizar_patente(
                        patente, patente_manager, is_admin, funcionario)
            else:
                st.info(
                    f"Nenhuma patente encontrada no status '{status_keys[i][1]}'.")


def renderizar_patente(patente, patente_manager, is_admin, funcionario=None):
    """Renderiza uma patente individual na interface."""
    status = patente_manager.get_status_atual(patente)
    status_icon = patente_manager.supabase_agent.get_patente_status_icon(
        status)
    status_text = patente_manager.supabase_agent.get_patente_status_display(
        status)

    # Determinar se é consultor
    is_consultor = False
    consultor_nome = ""
    try:
        if hasattr(st.session_state, 'user_id'):
            user_id = st.session_state.user_id
            # Verificar se o usuário é o consultor da patente
            if patente.get('consultor') == user_id:
                is_consultor = True
                # Buscar nome do consultor
                from supabase_agent import SupabaseAgent
                supabase_agent = SupabaseAgent()
                consultor_info = supabase_agent.get_consultor_by_id(user_id)
                if consultor_info:
                    consultor_nome = consultor_info.get('name', '')
    except:
        pass

    # Verificação alternativa: usar o user_id da sessão
    if not is_consultor:
        try:
            user_id = st.session_state.user['id'] if isinstance(
                st.session_state.user, dict) else st.session_state.user.id
            if patente.get('consultor') == user_id:
                is_consultor = True
                consultor_nome = patente.get('name_consultor', '')
        except:
            pass

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
        # Exibir dados da patente organizados verticalmente
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

        # Exibir links dos arquivos da patente
        pdfs = patente.get('pdf_patente')
        if pdfs:
            st.markdown("---")
            st.markdown("**📄 Documentos Anexados:**")
            if isinstance(pdfs, str):
                try:
                    import json
                    pdfs = json.loads(pdfs)
                except:
                    pdfs = [pdfs]
            if isinstance(pdfs, list):
                for i, url in enumerate(pdfs):
                    if url:
                        filename = url.split(
                            '/')[-1] if '/' in url else f"Documento_{i+1}.pdf"
                        st.markdown(f"• [{filename}]({url})")

        # Exibir documentos da coluna aguardando_info
        aguardando_info = patente.get('aguardando_info')
        if aguardando_info:
            st.markdown("---")
            st.markdown("**📄 Documentos - Aguardando Informações:**")
            if isinstance(aguardando_info, str):
                try:
                    import json
                    aguardando_info = json.loads(aguardando_info)
                except:
                    aguardando_info = [aguardando_info]
            if isinstance(aguardando_info, list):
                for i, url in enumerate(aguardando_info):
                    if url:
                        filename = url.split(
                            '/')[-1] if '/' in url else f"Documento_{i+1}.pdf"
                        st.markdown(f"• [{filename}]({url})")

        # Exibir documentos da coluna para_aprovacao
        para_aprovacao = patente.get('para_aprovacao')
        if para_aprovacao:
            st.markdown("---")
            st.markdown("**📄 Documentos - Para Aprovação:**")
            if isinstance(para_aprovacao, str):
                try:
                    import json
                    para_aprovacao = json.loads(para_aprovacao)
                except:
                    para_aprovacao = [para_aprovacao]
            if isinstance(para_aprovacao, list):
                for i, url in enumerate(para_aprovacao):
                    if url:
                        filename = url.split(
                            '/')[-1] if '/' in url else f"Documento_{i+1}.pdf"
                        st.markdown(f"• [{filename}]({url})")

        # Upload de documentos para consultores (após envio da requisição)
        if is_consultor and status in [patente_manager.STATUS_AGUARDANDO_INFORMACOES, patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO]:
            st.markdown("---")
            st.write("📄 **Adicionar Documentos Complementares**")
            st.info(
                "Você pode adicionar documentos complementares que serão enviados aos responsáveis.")

            uploaded_files = st.file_uploader(
                "Selecione os documentos",
                type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png",
                      "gif", "bmp", "mp4", "avi", "mov", "wmv", "zip", "rar"],
                accept_multiple_files=True,
                key=f"docs_consultor_patente_{patente['id']}"
            )
            if uploaded_files and st.button("Enviar Arquivos", key=f"btn_docs_consultor_patente_{patente['id']}"):
                with st.spinner("Enviando arquivos..."):
                    if _enviar_documentos_consultor_patente(patente, uploaded_files, consultor_nome, patente_manager):
                        st.success("✅ Arquivos enviados com sucesso!")
                        st.rerun()
                    else:
                        st.error(
                            "❌ Erro ao enviar arquivos. Verifique os logs.")

        # Exibir links dos arquivos do relatório
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
                    st.markdown("---")
                    st.markdown("**📄 Arquivo(s) do relatório:**")
                    for i, url in enumerate(pdf_urls):
                        st.markdown(f"• [Relatório {i+1}]({url})")

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

            # Upload de documentos para funcionários (exceto engenheiros)
            is_engenheiro_admin = (funcionario and
                                   funcionario.get('cargo_func', '') == 'engenheiro' and
                                   funcionario.get('is_admin', False))

            # Upload de documentos para funcionários (não engenheiros)
            if (status in [patente_manager.STATUS_PENDENTE, patente_manager.STATUS_RECEBIDO, patente_manager.STATUS_AGUARDANDO_INFORMACOES] and
                    not is_engenheiro_admin):
                st.markdown("**📤 Upload de Documentos:**")
                uploaded_files = st.file_uploader(
                    "Selecione os documentos",
                    type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png",
                          "gif", "bmp", "mp4", "avi", "mov", "wmv", "zip", "rar"],
                    accept_multiple_files=True,
                    key=f"docs_funcionario_patente_{patente['id']}"
                )
                if uploaded_files and st.button("Enviar Arquivos", key=f"btn_docs_funcionario_patente_{patente['id']}"):
                    with st.spinner("Enviando arquivos..."):
                        if _enviar_documentos_funcionario_patente(patente, uploaded_files, patente_manager):
                            st.success("✅ Arquivos enviados com sucesso!")
                            st.rerun()
                        else:
                            st.error(
                                "❌ Erro ao enviar arquivos. Verifique os logs.")

            # Upload e envio de relatório (apenas para engenheiros com is_admin=true quando status for "Relatório Sendo Elaborado")
            if status == patente_manager.STATUS_RELATORIO_SENDO_ELABORADO and is_engenheiro_admin:
                st.markdown("**📤 Upload do relatório:**")
                uploaded_files = st.file_uploader(
                    "Selecione os arquivos do relatório",
                    type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png",
                          "gif", "bmp", "mp4", "avi", "mov", "wmv", "zip", "rar"],
                    accept_multiple_files=True,
                    key=f"relatorio_{patente['id']}"
                )

                # Se há arquivos no upload, mostrar apenas botão de enviar
                if uploaded_files and len(uploaded_files) > 0:
                    if st.button("📤 Enviar Relatório", key=f"enviar_relatorio_{patente['id']}"):
                        if patente_manager.enviar_relatorio_patente(patente, uploaded_files):
                            # Atualizar status para "Para Aprovação" após envio bem-sucedido
                            if status == patente_manager.STATUS_RELATORIO_SENDO_ELABORADO:
                                patente_manager.atualizar_status_patente(
                                    patente['id'], patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO)
                            st.success("Relatório enviado com sucesso!")
                            st.rerun()
                else:
                    # Se não há arquivos, mostrar apenas botão para ir para aprovação
                    if st.button("📤 Para Aprovação", key=f"para_aprovacao_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO):
                            st.rerun()

            # Botões de alteração de status para engenheiros administradores
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                if status == patente_manager.STATUS_PENDENTE:
                    if st.button("📥 Recebido", key=f"recebido_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RECEBIDO):
                            st.rerun()
                elif status == patente_manager.STATUS_RECEBIDO:
                    if st.button("📋 Aguardando Info", key=f"documentos_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_AGUARDANDO_INFORMACOES):
                            st.rerun()
                elif status == patente_manager.STATUS_AGUARDANDO_INFORMACOES:
                    if st.button("📝 Elaborando Relatório", key=f"elaborando_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RELATORIO_SENDO_ELABORADO):
                            st.rerun()
                # Botão "Para Aprovação" removido daqui - agora só aparece na seção de upload de relatório
                elif status == patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO:
                    if st.button("✅ Relatório Aprovado", key=f"aprovado_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_RELATORIO_APROVADO):
                            st.rerun()
                elif status == patente_manager.STATUS_RELATORIO_APROVADO:
                    if st.button("🎉 Concluído", key=f"concluido_{patente['id']}"):
                        if patente_manager.atualizar_status_patente(patente['id'], patente_manager.STATUS_CONCLUIDO):
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
        # Usuários não-admin não devem ver botões de alteração de status
        # (Removido completamente - não há botões para usuários normais)

        st.markdown(
            f"<div style='margin-top:8px;font-weight:600;color:#005fa3;'>Status atual: {status_icon} {status_text}</div>", unsafe_allow_html=True)


def _enviar_documentos_consultor_patente(patente, uploaded_files, consultor_nome, patente_manager):
    """Envia documentos complementares do consultor para patente"""
    try:
        from supabase_agent import SupabaseAgent
        import datetime

        supabase_agent = SupabaseAgent()

        pdf_urls = []

        for uploaded_file in uploaded_files:
            try:
                pdf_url = supabase_agent.upload_pdf_to_storage(
                    uploaded_file,
                    uploaded_file.name,
                    st.session_state.jwt_token,
                    bucket="patentepdf"
                )
                if pdf_url:
                    pdf_urls.append(pdf_url)
                else:
                    st.error(
                        f"Erro ao fazer upload do arquivo {uploaded_file.name}")
                    return False
            except Exception as e:
                st.error(
                    f"Erro ao fazer upload do arquivo {uploaded_file.name}: {str(e)}")
                return False

        if pdf_urls:
            # Determinar qual coluna usar baseado no status atual
            status = patente_manager.get_status_atual(patente)

            if status == patente_manager.STATUS_AGUARDANDO_INFORMACOES:
                # Usar coluna aguardando_info
                success = supabase_agent.update_patente_aguardando_info(
                    patente['id'],
                    pdf_urls,
                    st.session_state.jwt_token
                )
            elif status == patente_manager.STATUS_RELATORIO_ENVIADO_APROVACAO:
                # Usar coluna para_aprovacao
                success = supabase_agent.update_patente_para_aprovacao(
                    patente['id'],
                    pdf_urls,
                    st.session_state.jwt_token
                )
            else:
                st.error("Status não permitido para upload de documentos")
                return False

            if not success:
                st.error("Erro ao atualizar documentos no banco de dados")
                return False

            # Enviar notificação por email se necessário
            try:
                from config import carregar_configuracoes

                config = carregar_configuracoes()
                destinatario_enge = config.get("destinatario_enge", "")

                # Usar o email_agent já configurado no session_state
                email_agent = st.session_state.get('email_agent')
                if not email_agent:
                    st.warning("Email agent não encontrado na sessão")
                    return False

                # Enviar email para destinatario_enge com anexos
                if destinatario_enge:
                    assunto = f"Documentos Complementares - Patente {patente.get('titulo', '')}"
                    corpo = f"""
                    <div style='font-family: Arial; font-size: 12pt;'>
                    Olá,<br><br>
                    O consultor {consultor_nome} adicionou documentos complementares à patente:<br><br>
                    <b>Dados da patente:</b><br>
                    - Título: {patente.get('titulo', '')}<br>
                    - Cliente: {patente.get('cliente', '')}<br>
                    - Processo: {patente.get('processo', '')}<br>
                    - Consultor: {patente.get('name_consultor', '')}<br>
                    - Funcionário: {patente.get('name_funcionario', '')}<br>
                    - Status: {patente_manager.supabase_agent.get_patente_status_display(status)}<br><br>
                    Os documentos foram adicionados à coluna {status} e estão anexados a este e-mail.<br><br>
                    Atenciosamente,<br>
                    Equipe AGP Consultoria
                    </div>
                    """

                    # Preparar anexos dos documentos
                    anexos = []
                    for uploaded_file in uploaded_files:
                        anexos.append(
                            (uploaded_file.getvalue(), uploaded_file.name))

                    # Enviar email com anexos
                    if len(anexos) > 1:
                        email_agent.send_email_multiplos_anexos(
                            destinatario_enge,
                            assunto,
                            corpo,
                            anexos
                        )
                    else:
                        email_agent.send_email_com_anexo(
                            destinatario_enge,
                            assunto,
                            corpo,
                            anexos[0][0],  # bytes do arquivo
                            anexos[0][1]   # nome do arquivo
                        )
            except Exception as e:
                st.warning(
                    f"Documentos enviados, mas houve erro ao enviar notificação por email: {str(e)}")

        return True

    except Exception as e:
        st.error(f"Erro ao enviar documentos: {str(e)}")
        return False


def _enviar_documentos_funcionario_patente(patente, uploaded_files, patente_manager):
    """Envia documentos do funcionário para patente"""
    try:
        from supabase_agent import SupabaseAgent

        supabase_agent = SupabaseAgent()

        pdf_urls = []

        for uploaded_file in uploaded_files:
            try:
                pdf_url = supabase_agent.upload_pdf_to_storage(
                    uploaded_file,
                    uploaded_file.name,
                    st.session_state.jwt_token,
                    bucket="patentepdf"
                )
                if pdf_url:
                    pdf_urls.append(pdf_url)
                else:
                    st.error(
                        f"Erro ao fazer upload do arquivo {uploaded_file.name}")
                    return False
            except Exception as e:
                st.error(
                    f"Erro ao fazer upload do arquivo {uploaded_file.name}: {str(e)}")
                return False

        if pdf_urls:
            success = supabase_agent.update_patente_pdf_url(
                patente['id'],
                pdf_urls,
                st.session_state.jwt_token
            )

            if not success:
                st.error("Erro ao atualizar documentos no banco de dados")
                return False

            # Enviar notificação por email se necessário
            try:
                from config import carregar_configuracoes

                config = carregar_configuracoes()
                destinatario_enge = config.get("destinatario_enge", "")

                # Usar o email_agent já configurado no session_state
                email_agent = st.session_state.get('email_agent')
                if not email_agent:
                    st.warning("Email agent não encontrado na sessão")
                    return False

                # Enviar email para destinatario_enge com anexos
                if destinatario_enge:
                    assunto = f"Documentos Adicionados - Patente {patente.get('titulo', '')}"
                    corpo = f"""
                    <div style='font-family: Arial; font-size: 12pt;'>
                    Olá,<br><br>
                    Documentos foram adicionados à patente pelo funcionário:<br><br>
                    <b>Dados da patente:</b><br>
                    - Título: {patente.get('titulo', '')}<br>
                    - Cliente: {patente.get('cliente', '')}<br>
                    - Processo: {patente.get('processo', '')}<br>
                    - Funcionário: {patente.get('name_funcionario', '')}<br>
                    - Consultor: {patente.get('name_consultor', '')}<br><br>
                    Os documentos foram adicionados à coluna pdf_patente e estão anexados a este e-mail.<br><br>
                    Atenciosamente,<br>
                    Equipe AGP Consultoria
                    </div>
                    """

                    # Preparar anexos dos documentos
                    anexos = []
                    for uploaded_file in uploaded_files:
                        anexos.append(
                            (uploaded_file.getvalue(), uploaded_file.name))

                    # Enviar email com anexos
                    if len(anexos) > 1:
                        email_agent.send_email_multiplos_anexos(
                            destinatario_enge,
                            assunto,
                            corpo,
                            anexos
                        )
                    else:
                        email_agent.send_email_com_anexo(
                            destinatario_enge,
                            assunto,
                            corpo,
                            anexos[0][0],  # bytes do arquivo
                            anexos[0][1]   # nome do arquivo
                        )
            except Exception as e:
                st.warning(
                    f"Documentos enviados, mas houve erro ao enviar notificação por email: {str(e)}")

        return True

    except Exception as e:
        st.error(f"Erro ao enviar documentos: {str(e)}")
        return False


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
            "Documentos da patente", type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif", "bmp", "mp4", "avi", "mov", "wmv", "zip", "rar"], accept_multiple_files=True, key=f"uploaded_files_{nonce}")
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

                    # Se há arquivos, enviar com anexos
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
                        # Se não há arquivos, enviar e-mail simples
                        email_agent.send_email_com_anexo(
                            destinatario_enge,
                            assunto,
                            corpo,
                            None,  # sem anexo
                            None   # sem nome de arquivo
                        )
                except Exception as e:
                    st.warning(
                        f"Não foi possível enviar o e-mail de notificação: {e}")

            # Enviar e-mail para o consultor
            email_consultor = consultor.get('email', '').strip()
            if email_consultor:
                try:
                    assunto_consultor = f"Nova patente atribuída: {titulo} ({cliente})"
                    corpo_consultor = f"""
                    <div style='font-family: Arial; font-size: 12pt;'>
                    Olá {consultor['name']},<br><br>
                    Uma nova patente foi atribuída a você:<br><br>
                    <b>Dados da patente:</b><br>
                    - Título: {titulo}<br>
                    - Cliente: {cliente}<br>
                    - CPF/CNPJ: {cpf_cnpj}<br>
                    - Pessoa para contato: {nome_contato}<br>
                    - Telefone: {fone_contato}<br>
                    - E-mail: {email_contato}<br>
                    - Processo: {processo}<br>
                    - Serviço: {servico}<br>
                    - Natureza: {natureza}<br>
                    - Contrato: {ncontrato}<br>
                    - Vencimento: {data_vencimento.strftime('%d/%m/%Y')}<br>
                    - Funcionário responsável: {funcionario['name']}<br>
                    - Observações: {observacoes}<br><br>
                    A patente está no status "Pendente" e será processada conforme o fluxo de trabalho.<br><br>
                    Atenciosamente,<br>
                    Equipe AGP Consultoria
                    </div>
                    """

                    # Se há arquivos, enviar com anexos
                    if uploaded_files and len(uploaded_files) > 0:
                        anexos = []
                        for file in uploaded_files:
                            anexos.append((file.getvalue(), file.name))
                        email_agent.send_email_multiplos_anexos(
                            email_consultor,
                            assunto_consultor,
                            corpo_consultor,
                            anexos
                        )
                    else:
                        # Se não há arquivos, enviar e-mail simples
                        email_agent.send_email_com_anexo(
                            email_consultor,
                            assunto_consultor,
                            corpo_consultor,
                            None,  # sem anexo
                            None   # sem nome de arquivo
                        )
                except Exception as e:
                    st.warning(
                        f"Não foi possível enviar o e-mail para o consultor: {e}")

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
