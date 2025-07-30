import streamlit as st
from supabase_agent import SupabaseAgent
from datetime import datetime
import json
import unicodedata
import re


class ObjecaoManager:
    """Gerencia operações relacionadas às objeções de marca"""

    # Status possíveis para as objeções
    STATUS_PENDENTE = "pendente"
    STATUS_RECEBIDO = "recebido"
    STATUS_EM_ANALISE = "em_analise"
    STATUS_CONCLUIDO = "concluido"

    def __init__(self, supabase_agent, email_agent):
        self.supabase_agent = supabase_agent
        self.email_agent = email_agent

    def atualizar_status_objecao(self, objecao_id: str, novo_status: str) -> bool:
        """
        Atualiza o status de uma objeção.
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        ok = self.supabase_agent.update_objecao_status(
            objecao_id, novo_status, st.session_state.jwt_token)
        if ok:
            status_text = self.supabase_agent.get_objecao_status_display(
                novo_status)
            st.success(f"Status da objeção atualizado para: {status_text}")
            return True
        else:
            st.error("Erro ao atualizar status da objeção!")
            return False

    def get_status_atual(self, objecao: dict) -> str:
        """
        Determina o status atual baseado em status_objecao persistente no banco.
        """
        status = objecao.get('status_objecao', self.STATUS_PENDENTE)
        if status not in [self.STATUS_PENDENTE, self.STATUS_RECEBIDO, self.STATUS_EM_ANALISE, self.STATUS_CONCLUIDO]:
            return self.STATUS_PENDENTE
        return status

    def separar_objecoes_por_status(self, objecoes: list) -> dict:
        """
        Separa as objeções em listas por status.
        Retorna um dicionário: {status: [objeções]}
        """
        status_dict = {
            self.STATUS_PENDENTE: [],
            self.STATUS_RECEBIDO: [],
            self.STATUS_EM_ANALISE: [],
            self.STATUS_CONCLUIDO: []
        }
        for objecao in objecoes:
            status = self.get_status_atual(objecao)
            if status in status_dict:
                status_dict[status].append(objecao)
        return status_dict

    def enviar_documentos_objecao(self, objecao: dict, uploaded_files: list, tipo_usuario: str = "funcionario") -> bool:
        """
        Envia documentos da objeção baseado no tipo de usuário.
        tipo_usuario: "funcionario" (obejpdf) ou "advogado" (peticaopdf)
        """
        try:
            # Verificar se email_agent está inicializado
            if not self.email_agent:
                st.error("Email agent não foi inicializado corretamente.")
                return False

            # Normalizar nome do arquivo
            def normalize_filename(filename):
                filename = unicodedata.normalize('NFKD', filename).encode(
                    'ASCII', 'ignore').decode('ASCII')
                filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
                return filename

            # Upload dos PDFs
            pdf_urls = []
            for i, file in enumerate(uploaded_files):
                try:
                    file_name = normalize_filename(
                        f"{objecao['id']}_{file.name}")

                    # Verificar se o usuário tem permissão para upload
                    from permission_manager import CargoPermissionManager
                    from app import get_user_id

                    permission_manager = CargoPermissionManager(
                        st.session_state.supabase_agent)
                    user_id = get_user_id(st.session_state.user)
                    cargo_info = permission_manager.get_user_cargo_info(
                        user_id)

                    tipos_multiplos = cargo_info.get(
                        'tipos_multiplos', [cargo_info['tipo']])
                    pode_fazer_upload = 'juridico' in tipos_multiplos or cargo_info[
                        'tipo'] == 'juridico'

                    if not pode_fazer_upload:
                        st.error(
                            "Você precisa ser um usuário jurídico (advogado/funcionário) para fazer upload de documentos.")
                        return False

                    url = self.supabase_agent.upload_pdf_to_storage(
                        file, file_name, st.session_state.jwt_token, bucket="obejecaopdf")
                    pdf_urls.append(url)

                except Exception as e:
                    st.error(f"Erro ao fazer upload de {file.name}: {str(e)}")
                    # Continuar com os outros arquivos mesmo se um falhar
                    continue

            # Verificar se pelo menos um arquivo foi enviado com sucesso
            if not pdf_urls:
                st.error(
                    "Nenhum arquivo foi enviado com sucesso. Verifique os erros acima.")
                return False

            # Preparar dados dos documentos para salvar no Supabase
            documentos_data = {
                "pdf_urls": pdf_urls,
                "data_envio": datetime.now().isoformat(),
                "arquivos": [{"nome": file.name, "url": url} for file, url in zip(uploaded_files, pdf_urls)]
            }

            # Atualizar coluna correta baseado no tipo de usuário
            if tipo_usuario == "advogado":
                # Advogados salvam em peticaopdf
                self.supabase_agent.update_objecao_peticaopdf(
                    objecao['id'], documentos_data, st.session_state.jwt_token)
            else:
                # Funcionários salvam em obejpdf
                self.supabase_agent.update_objecao_obejpdf(
                    objecao['id'], documentos_data, st.session_state.jwt_token)

            # Preparar anexos para e-mail no formato correto
            anexos = []
            for file in uploaded_files:
                pdf_bytes = file.getvalue()
                anexos.append({
                    "filename": file.name,
                    "content": pdf_bytes,
                    "content_type": "application/pdf"
                })

            # Usar o método específico do EmailAgent para enviar e-mails
            emails_enviados = self.email_agent.enviar_emails_objecao_completa(
                objecao, anexos, self.supabase_agent)

            # Notificar sobre e-mails enviados
            if emails_enviados:
                st.success(
                    f"📧 E-mails enviados com sucesso para: {', '.join(emails_enviados)}")
            else:
                st.warning(
                    "⚠️ Nenhum e-mail foi enviado. Verifique as configurações de e-mail.")

            # NOTA: Removida a alteração automática de status para "Concluído"
            # O status deve ser alterado manualmente pelo usuário quando apropriado
            # Uma objeção recém-criada deve permanecer como "pendente"

            return True

        except Exception as e:
            st.error(f"Erro ao enviar documentos: {str(e)}")
            return False


def limpar_formulario_objecao():
    """Limpa todos os dados do formulário de objeção"""
    # Incrementar a chave do formulário para forçar recriação dos widgets
    if "form_key" in st.session_state:
        st.session_state.form_key += 1

    # Limpar dados do formulário
    if "form_data" in st.session_state:
        st.session_state.form_data = {
            "marca": "",
            "nomecliente": "",
            "vencimento": None,
            "servicocontrato": "",
            "observacao": "",
            "consultor_selecionado": ""
        }

    # Limpar lista de processos
    if "processos" in st.session_state:
        st.session_state.processos = []

    # Limpar cache de upload (usando chave dinâmica)
    upload_key = f"upload_docs_{st.session_state.form_key}"
    if upload_key in st.session_state:
        del st.session_state[upload_key]


def solicitar_objecao(email_agent):
    """Página para solicitar nova objeção de marca"""

    # Verificação de segurança para email_agent
    if email_agent is None:
        st.error("Erro: email_agent não foi inicializado corretamente.")
        return

    # Verificação de login
    if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
        st.error("Você precisa estar logado para acessar esta funcionalidade.")
        st.stop()

    # Verificar se o usuário não é consultor (cargo='consultor' na tabela perfil)
    user_id = st.session_state.user['id'] if isinstance(
        st.session_state.user, dict) else st.session_state.user.id

    # Buscar perfil do usuário
    perfil = st.session_state.supabase_agent.get_profile(user_id)
    if perfil and perfil.get('cargo', '') == 'consultor':
        st.error("Você não tem acesso a essa funcionalidade por enquanto. Esta funcionalidade está em desenvolvimento para consultores.")
        st.stop()

    # Inicializar dados apenas uma vez usando cache
    @st.cache_data
    def get_servicos_contrato():
        return [
            "",  # Opção vazia para campo limpo
            "RECURSO DE MARCAS (EXCETO CONTRA INDEFERIMENTO DE PEDIDO DE REGISTRO DE MARCA)",
            "NULIDADE ADMINISTRATIVA DE REGISTRO DE MARCA",
            "CADUCIDADE",
            "MANIFESTAÇÃO CONTRA OPOSIÇÃO",
            "OPOSIÇÃO",
            "RECURSO COM DIVISÃO DE PROCESSO (UMA CLASSE)",
            "MANIFESTAÇÃO CONTRA CADUCIDADE",
            "CONTRARRAZÃO E/OU MANIFESTAÇÃO AO RECURSO/NULIDADE",
            "MANIFESTAÇÃO SOBRE PARECER PROFERIDO EM GRAU DE RECURSO",
            "RECURSO CONTRA INDEFERIMENTO DE PEDIDO DE REGISTRO DE MARCA",
            "NOTIFICAÇÃO EXTRAJUDICIAL"
        ]

    # Inicializar dados do formulário
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    if "form_data" not in st.session_state:
        st.session_state.form_data = {
            "marca": "",
            "nomecliente": "",
            "vencimento": None,
            "servicocontrato": "",
            "observacao": "",
            "consultor_selecionado": ""
        }

    if "processos" not in st.session_state:
        st.session_state.processos = []

    servicos_contrato = get_servicos_contrato()

    # Obter destinatário jurídico
    destinatario_juridico = email_agent.destinatario_juridico

    # Título
    st.title("📋 Solicitar Objeção de Marca")

    # Cache dos consultores
    @st.cache_data(ttl=3600)
    def get_consultores():
        try:
            consultores = st.session_state.supabase_agent.get_consultores_por_cargo(
                "consultor")
            return {c['name']: c['id'] for c in consultores}
        except Exception as e:
            return {"Consultor Padrão": "default"}

    consultor_options = get_consultores()

    # Formulário único para evitar reruns (estilo patentes)
    with st.form(f"form_objecao_{st.session_state.form_key}"):
        # 1. Consultor responsável
        st.subheader("Consultor Responsável")
        consultor_selecionado = st.selectbox(
            "Selecionar Consultor",
            options=list(consultor_options.keys()),
            key=f"consultor_objecao_{st.session_state.form_key}",
            index=0
        )

        # 2. Dados básicos
        st.subheader("Dados Básicos")
        marca = st.text_input("Marca", key=f"marca_{st.session_state.form_key}",
                              value=st.session_state.form_data["marca"])
        nomecliente = st.text_input(
            "Nome do Cliente", key=f"nomecliente_{st.session_state.form_key}",
            value=st.session_state.form_data["nomecliente"])
        vencimento = st.date_input(
            "Data de Vencimento", key=f"vencimento_{st.session_state.form_key}",
            value=st.session_state.form_data["vencimento"])

        servicocontrato = st.selectbox(
            "Serviços do Contrato",
            options=servicos_contrato,
            key=f"servicocontrato_{st.session_state.form_key}",
            index=servicos_contrato.index(
                st.session_state.form_data["servicocontrato"]) if st.session_state.form_data["servicocontrato"] in servicos_contrato else 0
        )

        observacao = st.text_area(
            "Observações (opcional)", key=f"observacao_{st.session_state.form_key}",
            value=st.session_state.form_data["observacao"])

        # 3. Processos e Classificações (dentro do form)
        st.subheader("Processos e Classificações")
        st.info(
            "Adicione os processos e suas respectivas classes. Cada processo tem uma classe.")

        # Campos para adicionar processo (dentro do form)
        processo_numero = st.text_input(
            "Número do Processo", key=f"processo_numero_{st.session_state.form_key}")
        classe_nice = st.text_input(
            "Classe Nice", key=f"classe_nice_{st.session_state.form_key}")
        ncontrato = st.text_input(
            "Número do Contrato", key=f"ncontrato_{st.session_state.form_key}")

        # Botão para adicionar processo (dentro do form)
        if st.form_submit_button("Adicionar Processo", type="secondary"):
            if processo_numero and classe_nice and ncontrato:
                processo_data = {
                    "numero": processo_numero,
                    "classe": classe_nice,
                    "contrato": ncontrato
                }
                st.session_state.processos.append(processo_data)
                st.success(f"Processo {processo_numero} adicionado!")
            else:
                st.error("Preencha o número do processo, classe e contrato.")

        # 4. Upload de documentos (dentro do form)
        st.subheader("PDFs da Objeção")
        uploaded_files = st.file_uploader(
            "Adicionar documentos (PDF)",
            type=['pdf'],
            accept_multiple_files=True,
            key=f"upload_docs_{st.session_state.form_key}"
        )

        # 5. Botão de submit (dentro do form, no final)
        submitted = st.form_submit_button("Solicitar Objeção")

    # Mostrar processos adicionados
    if st.session_state.processos:
        st.write("**Processos adicionados:**")
        for i, processo in enumerate(st.session_state.processos):
            with st.expander(f"Processo: {processo['numero']} - Contrato: {processo['contrato']}"):
                st.write(f"**Número:** {processo['numero']}")
                st.write(f"**Contrato:** {processo['contrato']}")
                st.write(f"**Classe:** {processo['classe']}")
                if st.button("Remover", key=f"remove_{i}"):
                    st.session_state.processos.pop(i)
                    st.success(f"Processo removido!")

    if submitted:
        # Verificar campos obrigatórios básicos
        if not all([marca, servicocontrato, nomecliente]):
            st.error("Por favor, preencha todos os campos obrigatórios.")
            return

        # Verificar se há processos (seja da lista ou dos campos atuais)
        processos_para_adicionar = []
        if st.session_state.processos:
            processos_para_adicionar = st.session_state.processos
        elif processo_numero and classe_nice and ncontrato:
            # Adicionar processo dos campos atuais
            processos_para_adicionar = [{
                "numero": processo_numero,
                "classe": classe_nice,
                "contrato": ncontrato
            }]

        if not processos_para_adicionar:
            st.error("Por favor, adicione pelo menos um processo.")
            return

        # Carregar dados necessários apenas quando for enviar
        with st.spinner("Enviando solicitação, aguarde..."):
            # Verificar permissões do usuário apenas no envio
            try:
                from permission_manager import CargoPermissionManager
                from app import get_user_id

                permission_manager = CargoPermissionManager(
                    st.session_state.supabase_agent)
                user_id = get_user_id(st.session_state.user)
                cargo_info = permission_manager.get_user_cargo_info(user_id)

                tipos_multiplos = cargo_info.get(
                    'tipos_multiplos', [cargo_info['tipo']])
                pode_fazer_upload = 'juridico' in tipos_multiplos or cargo_info[
                    'tipo'] == 'juridico'
            except:
                pode_fazer_upload = True
                cargo_info = {"tipo": "default"}
            # Preparar dados da objeção
            objecao_data = {
                "marca": marca,
                "servico": servicocontrato,  # Valor do selectbox vai para a coluna 'servico'
                "nomecliente": nomecliente,
                "vencimento": vencimento.isoformat() if vencimento else None,
                "servicocontrato": servicocontrato,
                "observacao": observacao,
                "processo": [p["numero"] for p in processos_para_adicionar],
                "classe": [p["classe"] for p in processos_para_adicionar],
                "ncontrato": [p["contrato"] for p in processos_para_adicionar],
                "consultor_objecao": consultor_options[consultor_selecionado],
                "juridico_id": st.session_state.user.get('id', 'default'),
                "status_objecao": "pendente"
            }

            # Inserir objeção
            objecao_criada = st.session_state.supabase_agent.insert_objecao(
                objecao_data, st.session_state.jwt_token)
            if objecao_criada:
                st.success("Solicitação sendo enviada!")

                # Processar arquivos enviados se houver
                if uploaded_files:
                    # Verificar se é advogado ou funcionário
                    is_advogado = cargo_info['tipo'] == 'juridico' and cargo_info.get(
                        'cargo') == 'advogado'
                    tipo_usuario = "advogado" if is_advogado else "funcionario"

                    # Processar os arquivos usando o ObjecaoManager
                    objecao_manager = ObjecaoManager(
                        st.session_state.supabase_agent, email_agent)
                    if objecao_manager.enviar_documentos_objecao(objecao_criada, uploaded_files, tipo_usuario):
                        pass  # Sucesso já foi notificado na função enviar_documentos_objecao
                    else:
                        st.warning(
                            "Objeção criada, mas houve erro ao enviar documentos.")
                else:
                    # Enviar e-mails de notificação apenas quando NÃO há documentos
                    emails_enviados = []

                    # 1. Enviar e-mail para consultor
                    if objecao_criada.get('email_consultor'):
                        try:
                            email_agent.enviar_email_nova_objecao(
                                objecao_criada['email_consultor'], objecao_criada)
                            emails_enviados.append(
                                f"consultor ({objecao_criada['email_consultor']})")
                        except Exception as e:
                            st.warning(
                                f"Erro ao enviar e-mail para consultor: {str(e)}")
                    else:
                        st.warning(
                            "E-mail do consultor não encontrado na objeção criada")

                    # 2. Enviar e-mail para destinatário jurídico
                    if destinatario_juridico:
                        try:
                            email_agent.enviar_email_nova_objecao(
                                destinatario_juridico, objecao_criada)
                            emails_enviados.append(
                                f"destinatário jurídico ({destinatario_juridico})")
                        except Exception as e:
                            st.warning(
                                f"Erro ao enviar e-mail para destinatário jurídico: {str(e)}")
                    else:
                        st.warning(
                            f"⚠️ Destinatário jurídico não configurado. E-mail não será enviado.")

                    # 3. Enviar e-mail para destinatário jurídico adicional
                    destinatario_juridico_um = email_agent.destinatario_juridico_um
                    if destinatario_juridico_um:
                        try:
                            email_agent.enviar_email_nova_objecao(
                                destinatario_juridico_um, objecao_criada)
                            emails_enviados.append(
                                f"destinatário jurídico adicional ({destinatario_juridico_um})")
                        except Exception as e:
                            st.warning(
                                f"Erro ao enviar e-mail para destinatário jurídico adicional: {str(e)}")
                    else:
                        st.warning(
                            f"⚠️ Destinatário jurídico adicional não configurado. E-mail não será enviado.")

                    # Notificar sobre e-mails enviados
                    if emails_enviados:
                        st.success(
                            f"📧 E-mails de notificação enviados para: {', '.join(emails_enviados)}")
                    else:
                        st.warning(
                            "⚠️ Nenhum e-mail de notificação foi enviado.")

                # Limpar formulário após envio bem-sucedido
                limpar_formulario_objecao()
                st.success(
                    "✅ Formulário limpo! Você pode criar uma nova objeção.")
                st.rerun()
            else:
                st.error("Erro ao solicitar objeção!")
                st.info(
                    "A objeção pode ter sido criada, mas houve erro ao retornar os dados. Verifique em 'Minhas Objeções'.")


def minhas_objecoes(email_agent):
    """Página para visualizar objeções do usuário"""
    # Verificação de segurança para email_agent
    if email_agent is None:
        st.error("Erro: email_agent não foi inicializado corretamente.")
        return

    st.title("📋 Minhas Objeções de Marca")

    if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
        st.error("Você precisa estar logado para acessar esta funcionalidade.")
        st.stop()

    # Verificar se é admin usando o permission_manager
    from permission_manager import CargoPermissionManager
    from app import get_user_id

    permission_manager = CargoPermissionManager(
        st.session_state.supabase_agent)
    user_id = get_user_id(st.session_state.user)
    cargo_info = permission_manager.get_user_cargo_info(user_id)
    is_admin = cargo_info['is_admin'] is True

    # Buscar objeções baseado no tipo de usuário
    if is_admin:
        # Admin vê todas as objeções
        objecoes = st.session_state.supabase_agent.get_all_objecoes(
            st.session_state.jwt_token)
    else:
        # Verificar se é usuário jurídico ou consultor
        tipos_multiplos = cargo_info.get(
            'tipos_multiplos', [cargo_info['tipo']])

        if 'juridico' in tipos_multiplos or cargo_info['tipo'] == 'juridico':
            # Usuário jurídico vê suas próprias objeções criadas
            objecoes = st.session_state.supabase_agent.get_objecoes_by_juridico(
                user_id, st.session_state.jwt_token)
        else:
            # Consultor vê objeções onde ele é o consultor responsável
            objecoes = st.session_state.supabase_agent.get_objecoes_by_consultor(
                user_id, st.session_state.jwt_token)

    if not objecoes:
        st.info("Nenhuma objeção encontrada.")
        return

    # Inicializar manager
    objecao_manager = ObjecaoManager(
        st.session_state.supabase_agent, email_agent)

    # Separar objeções por status
    objecoes_por_status = objecao_manager.separar_objecoes_por_status(objecoes)

    # Criar tabs para cada status
    tabs = st.tabs([
        f"⏳ Pendentes ({len(objecoes_por_status[objecao_manager.STATUS_PENDENTE])})",
        f"📥 Recebidas ({len(objecoes_por_status[objecao_manager.STATUS_RECEBIDO])})",
        f"🔍 Em Análise ({len(objecoes_por_status[objecao_manager.STATUS_EM_ANALISE])})",
        f"✅ Concluídas ({len(objecoes_por_status[objecao_manager.STATUS_CONCLUIDO])})"
    ])

    # Renderizar objeções em cada tab
    status_list = [
        objecao_manager.STATUS_PENDENTE,
        objecao_manager.STATUS_RECEBIDO,
        objecao_manager.STATUS_EM_ANALISE,
        objecao_manager.STATUS_CONCLUIDO
    ]

    for i, status in enumerate(status_list):
        with tabs[i]:
            objecoes_list = objecoes_por_status.get(status, [])
            if not objecoes_list:
                st.info(f"Nenhuma objeção {status}.")
                continue

            for objecao in objecoes_list:
                renderizar_objecao(objecao, objecao_manager, is_admin)


def renderizar_objecao(objecao, objecao_manager, is_admin):
    """Renderiza uma objeção individual"""
    # Preparar informações para o título do card
    marca = objecao.get('marca', 'N/A')
    cliente = objecao.get('nomecliente', 'N/A')
    servico = objecao.get('servico', 'N/A')
    consultor = objecao.get(
        'name_consultor', objecao.get('consultor_objecao', 'N/A'))

    # Formatar data
    data_criacao = ""
    if objecao.get('created_at'):
        data_criacao = formatar_data_br(objecao['created_at'])

    # Criar título do card
    titulo_card = f"📋 {marca} - {cliente}"
    if servico and servico != 'N/A':
        titulo_card += f" | {servico}"
    if data_criacao:
        titulo_card += f" | {data_criacao}"
    if consultor and consultor != 'N/A':
        titulo_card += f" | {consultor}"

    with st.expander(titulo_card):
        # Informações básicas organizadas (uma abaixo da outra)
        st.write(f"**Marca:** {objecao.get('marca', 'N/A')}")
        st.write(f"**Cliente:** {objecao.get('nomecliente', 'N/A')}")
        st.write(f"**Serviço:** {objecao.get('servico', 'N/A')}")
        if objecao.get('created_at'):
            data_criacao = formatar_data_br(objecao['created_at'])
            st.write(f"**Criado em:** {data_criacao}")
        if objecao.get('name_consultor'):
            st.write(f"**Consultor:** {objecao.get('name_consultor', 'N/A')}")
        elif objecao.get('consultor_objecao'):
            st.write(
                f"**Consultor:** {objecao.get('consultor_objecao', 'N/A')}")

        # Dados dos processos
        processos = objecao.get('processo', [])
        classes = objecao.get('classe', [])
        contratos = objecao.get('ncontrato', [])

        if processos:
            st.write("**📋 Processos:**")
            for i in range(len(processos)):
                processo_num = processos[i] if i < len(processos) else 'N/A'
                classe_num = classes[i] if i < len(classes) else 'N/A'
                contrato_num = contratos[i] if i < len(contratos) else 'N/A'

                st.write(f"  **Processo {i+1}:** {processo_num}")
                st.write(f"    **Contrato:** {contrato_num}")
                st.write(f"    **Classe:** {classe_num}")

        # Observações
        if objecao.get('observacao'):
            st.write(f"**📝 Observações:** {objecao.get('observacao')}")

        # Status atual (sempre por último)
        status_atual = objecao_manager.get_status_atual(objecao)
        status_icon = st.session_state.supabase_agent.get_objecao_status_icon(
            status_atual)
        status_text = st.session_state.supabase_agent.get_objecao_status_display(
            status_atual)
        st.write(f"{status_icon} **Status:** {status_text}")

        # Controles de status (apenas para admin jurídico)
        from permission_manager import CargoPermissionManager
        from app import get_user_id

        permission_manager = CargoPermissionManager(
            st.session_state.supabase_agent)
        user_id = get_user_id(st.session_state.user)
        cargo_info = permission_manager.get_user_cargo_info(user_id)
        is_admin_juridico = cargo_info['tipo'] == 'juridico' and cargo_info['is_admin'] is True

        if is_admin_juridico:
            st.subheader("Alterar Status")

            # Botões para avançar para o próximo status (sempre na coluna 1)
            if status_atual == objecao_manager.STATUS_PENDENTE:
                if st.button("📥 Recebida", key=f"btn_recebida_{objecao['id']}"):
                    objecao_manager.atualizar_status_objecao(
                        objecao['id'], objecao_manager.STATUS_RECEBIDO)
                    st.rerun()

            elif status_atual == objecao_manager.STATUS_RECEBIDO:
                if st.button("🔍 Em Análise", key=f"btn_analise_{objecao['id']}"):
                    objecao_manager.atualizar_status_objecao(
                        objecao['id'], objecao_manager.STATUS_EM_ANALISE)
                    st.rerun()

            elif status_atual == objecao_manager.STATUS_EM_ANALISE:
                if st.button("✅ Concluída", key=f"btn_concluida_{objecao['id']}"):
                    objecao_manager.atualizar_status_objecao(
                        objecao['id'], objecao_manager.STATUS_CONCLUIDO)
                    st.rerun()

                    # Exibir PDFs existentes
        st.subheader("📄 Documentos")

        # Verificar se há PDFs em obejpdf (funcionários)
        if objecao.get('obejpdf'):
            try:
                obejpdf_data = objecao['obejpdf']
                if isinstance(obejpdf_data, dict) and obejpdf_data.get('pdf_urls'):
                    st.write("**📎 Documentos enviados por funcionário:**")
                    for i, url in enumerate(obejpdf_data['pdf_urls']):
                        if url:
                            st.markdown(f"[📎 Documento {i+1}]({url})")
            except Exception as e:
                st.warning(f"Erro ao carregar documentos: {str(e)}")

        # Verificar se há PDFs em peticaopdf (advogados)
        if objecao.get('peticaopdf'):
            try:
                peticaopdf_data = objecao['peticaopdf']
                if isinstance(peticaopdf_data, dict) and peticaopdf_data.get('pdf_urls'):
                    st.write("**📄 Petições enviadas por advogado:**")
                    for i, url in enumerate(peticaopdf_data['pdf_urls']):
                        if url:
                            st.markdown(f"[📄 Petição {i+1}]({url})")
            except Exception as e:
                st.warning(f"Erro ao carregar petições: {str(e)}")

        # Upload de documentos (apenas quando status for "Em Análise")
        if status_atual == objecao_manager.STATUS_EM_ANALISE:
            # Determinar tipo de usuário
            from permission_manager import CargoPermissionManager
            from app import get_user_id

            permission_manager = CargoPermissionManager(
                st.session_state.supabase_agent)
            user_id = get_user_id(st.session_state.user)
            cargo_info = permission_manager.get_user_cargo_info(user_id)

            # Verificar se é advogado ou funcionário
            is_advogado = cargo_info['tipo'] == 'juridico' and cargo_info['cargo'] == 'advogado'
            is_funcionario = cargo_info['tipo'] == 'juridico' and cargo_info['cargo'] == 'funcionario'

            # Apenas usuários jurídicos podem fazer upload
            if cargo_info['tipo'] != 'juridico':
                st.info(
                    "Apenas usuários jurídicos (advogados/funcionários) podem fazer upload de documentos.")
            elif is_advogado:
                st.subheader("📄 Petições")
                uploaded_files = st.file_uploader(
                    "Adicionar petições (PDF)",
                    type=['pdf'],
                    accept_multiple_files=True,
                    key=f"upload_peticoes_{objecao['id']}"
                )

                if uploaded_files and st.button("Enviar Petições", key=f"btn_upload_peticoes_{objecao['id']}"):
                    with st.spinner("Enviando petições e notificando por e-mail..."):
                        if objecao_manager.enviar_documentos_objecao(
                                objecao, uploaded_files, tipo_usuario="advogado"):
                            st.success(
                                "📄 Petições enviadas com sucesso! E-mails enviados para consultor e funcionário.")

                            # Alterar status automaticamente para "Concluído" quando advogado envia petições
                            try:
                                objecao_manager.atualizar_status_objecao(
                                    objecao['id'], objecao_manager.STATUS_CONCLUIDO)
                                st.success(
                                    "✅ Status automaticamente alterado para 'Concluído'!")
                            except Exception as e:
                                st.warning(
                                    f"Petições enviadas, mas erro ao alterar status: {str(e)}")

                            st.rerun()
                        else:
                            st.error(
                                "Erro ao enviar petições. Verifique os logs.")

            elif is_funcionario:
                st.subheader("📎 Documentos")
                uploaded_files = st.file_uploader(
                    "Adicionar documentos (PDF)",
                    type=['pdf'],
                    accept_multiple_files=True,
                    key=f"upload_docs_{objecao['id']}"
                )

                if uploaded_files and st.button("Enviar Documentos", key=f"btn_upload_docs_{objecao['id']}"):
                    with st.spinner("Enviando documentos e notificando por e-mail..."):
                        if objecao_manager.enviar_documentos_objecao(
                                objecao, uploaded_files, tipo_usuario="funcionario"):
                            st.success(
                                "📎 Documentos enviados com sucesso! E-mails enviados para consultor e funcionário.")
                            st.rerun()
                        else:
                            st.error(
                                "Erro ao enviar documentos. Verifique os logs.")


def formatar_data_br(data_iso):
    """Formata data ISO para formato brasileiro"""
    try:
        data = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
        return data.strftime("%d/%m/%Y %H:%M")
    except:
        return data_iso
