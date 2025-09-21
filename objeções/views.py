import streamlit as st
from supabase_agent import SupabaseAgent
from datetime import datetime
import json
import unicodedata
import re
from collections import defaultdict


class ObjecaoManager:
    """Gerencia operações relacionadas às objeções de marca"""

    # Status possíveis para as objeções
    STATUS_PENDENTE = "pendente"
    STATUS_RECEBIDO = "recebido"
    STATUS_EM_EXECUCAO = "em_execucao"
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
        if status not in [self.STATUS_PENDENTE, self.STATUS_RECEBIDO, self.STATUS_EM_EXECUCAO, self.STATUS_CONCLUIDO]:
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
            self.STATUS_EM_EXECUCAO: [],
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

            # Upload dos arquivos
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

                    # Verificar se é usuário jurídico (APENAS na tabela juridico)
                    juridico = st.session_state.supabase_agent.get_juridico_by_id(
                        user_id)
                    pode_fazer_upload = juridico is not None

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

            # Enviar e-mails baseado no tipo de usuário
            emails_enviados = []

            if tipo_usuario == "advogado":
                # Advogados enviam e-mail apenas para o funcionário responsável
                juridico_id = objecao.get('juridico_id')

                # 1. Enviar para o funcionário responsável
                if juridico_id:
                    try:
                        # Buscar e-mail do funcionário no banco de dados
                        funcionario_email = self.supabase_agent.get_user_email_by_id(
                            juridico_id)

                        if funcionario_email and funcionario_email != 'N/A':
                            resultado = self.email_agent.enviar_email_objecao_funcionario(
                                funcionario_email, objecao, anexos, self.supabase_agent)

                            if resultado:
                                emails_enviados.append(
                                    f"funcionário ({funcionario_email})")
                        else:
                            st.warning(
                                f"E-mail do funcionário não encontrado para o ID: {juridico_id}")
                    except Exception as e:
                        st.warning(
                            f"Erro ao enviar e-mail para funcionário: {str(e)}")
                else:
                    st.warning("ID do funcionário não encontrado na objeção.")

            else:
                # Funcionários enviam e-mails para consultor e destinatários jurídicos
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

    def enviar_documentos_objecao_sem_email(self, objecao: dict, uploaded_files: list, tipo_usuario: str = "funcionario") -> bool:
        """
        Envia documentos da objeção SEM enviar e-mails (apenas upload).
        tipo_usuario: "funcionario" (obejpdf) ou "advogado" (peticaopdf)
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

                    # Verificar se é usuário jurídico (APENAS na tabela juridico)
                    juridico = st.session_state.supabase_agent.get_juridico_by_id(
                        user_id)
                    pode_fazer_upload = juridico is not None

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
    """Página para solicitar novo serviço jurídico"""

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
            "NOTIFICAÇÃO EXTRAJUDICIAL",
            "ELABORAÇÃO DE CONTRATO",
            "CUMPRIMENTO DE EXIGÊNCIA"
        ]

    # Inicializar dados do formulário
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    if "form_data" not in st.session_state:
        st.session_state.form_data = {
            "marca": "",
            "nomecliente": "",
            "cnpj_cpf_cliente": "",
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
    st.title("📋 Solicitação para o Jurídico")

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
        cnpj_cpf_cliente = st.text_input(
            "CPF/CNPJ do Cliente", key=f"cnpj_cpf_cliente_{st.session_state.form_key}",
            value=st.session_state.form_data.get("cnpj_cpf_cliente", ""))
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
        st.subheader("Documentos da Objeção")
        uploaded_files = st.file_uploader(
            "Adicionar documentos",
            type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png',
                  'gif', 'bmp', 'mp4', 'avi', 'mov', 'wmv', 'zip', 'rar'],
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

                # Verificar se é usuário jurídico (APENAS na tabela juridico)
                juridico = st.session_state.supabase_agent.get_juridico_by_id(
                    user_id)
                pode_fazer_upload = juridico is not None
            except:
                pode_fazer_upload = True
            # Preparar dados da objeção
            objecao_data = {
                "marca": marca,
                "servico": servicocontrato,  # Valor do selectbox vai para a coluna 'servico'
                "nomecliente": nomecliente,
                "cnpj_cpf_cliente": cnpj_cpf_cliente,
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

                # Preparar anexos se houver documentos
                anexos = []
                if uploaded_files:
                    for file in uploaded_files:
                        pdf_bytes = file.getvalue()
                        anexos.append({
                            "filename": file.name,
                            "content": pdf_bytes,
                            "content_type": "application/pdf"
                        })

                # Fluxo unificado: sempre enviar e-mails para consultor e destinatários jurídicos
                emails_enviados = []

                # 1. Enviar e-mail para consultor
                if objecao_criada.get('email_consultor'):
                    try:
                        if anexos:
                            # Se há anexos, usar método que suporta anexos
                            email_agent.enviar_email_objecao_consultor(
                                objecao_criada['email_consultor'], objecao_criada, anexos)
                        else:
                            # Se não há anexos, usar método simples
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
                        if anexos:
                            # Se há anexos, usar método que suporta anexos
                            email_agent.enviar_email_objecao_consultor(
                                destinatario_juridico, objecao_criada, anexos)
                        else:
                            # Se não há anexos, usar método simples
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
                        if anexos:
                            # Se há anexos, usar método que suporta anexos
                            email_agent.enviar_email_objecao_consultor(
                                destinatario_juridico_um, objecao_criada, anexos)
                        else:
                            # Se não há anexos, usar método simples
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

                # Processar upload dos arquivos se houver (apenas para salvar no banco)
                if uploaded_files:
                    # Verificar se é advogado ou funcionário
                    juridico = st.session_state.supabase_agent.get_juridico_by_id(
                        user_id)
                    is_advogado = juridico and juridico.get(
                        'cargo', '') == 'advogado'
                    tipo_usuario = "advogado" if is_advogado else "funcionario"

                    # Processar os arquivos usando o ObjecaoManager (apenas upload, sem e-mail)
                    objecao_manager = ObjecaoManager(
                        st.session_state.supabase_agent, email_agent)
                    if objecao_manager.enviar_documentos_objecao_sem_email(objecao_criada, uploaded_files, tipo_usuario):
                        st.success("📄 Documentos salvos no sistema!")
                    else:
                        st.warning(
                            "Objeção criada, mas houve erro ao salvar documentos.")

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
                    "✅ Formulário limpo! Você pode criar um novo serviço jurídico.")
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

    # Verificar se é funcionário e se tem permissões de admin
    funcionario = st.session_state.supabase_agent.get_funcionario_by_id(
        user_id)

    # Para objeções: APENAS usuários com is_admin=True na tabela juridico
    juridico = st.session_state.supabase_agent.get_juridico_by_id(user_id)
    is_admin = juridico and juridico.get('is_admin', False)

    # Buscar objeções baseado no tipo de usuário
    if is_admin:
        # Admin vê todas as objeções
        objecoes = st.session_state.supabase_agent.get_all_objecoes(
            st.session_state.jwt_token)
    else:
        # Verificar se é usuário jurídico ou consultor
        # Buscar dados específicos para determinar o tipo de usuário
        juridico = st.session_state.supabase_agent.get_juridico_by_id(user_id)
        perfil = st.session_state.supabase_agent.get_profile(user_id)

        if juridico:
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

    # Adicionar filtro por consultor para administradores e funcionários
    is_funcionario = funcionario and funcionario.get(
        'cargo_func', '') == 'funcionario'
    if is_admin or is_funcionario:
        st.subheader("Filtros")

        # Buscar nomes únicos de consultores das objeções existentes
        consultor_nomes_unicos = set()
        for objecao in objecoes:
            consultor_nome = objecao.get(
                'name_consultor', '') or objecao.get('consultor_objecao', '')
            if consultor_nome:
                consultor_nomes_unicos.add(consultor_nome)

        consultor_nomes = ["Todos os consultores"] + \
            sorted(list(consultor_nomes_unicos))

        consultor_filtro = st.selectbox(
            "Filtrar por consultor:",
            consultor_nomes,
            key="filtro_consultor_objecoes"
        )

        # Filtrar objeções por consultor se selecionado
        if consultor_filtro and consultor_filtro != "Todos os consultores":
            objecoes_filtradas = []
            for objecao in objecoes:
                consultor_objecao = objecao.get(
                    'name_consultor', '') or objecao.get('consultor_objecao', '')
                if consultor_objecao == consultor_filtro:
                    objecoes_filtradas.append(objecao)
            objecoes = objecoes_filtradas

            if not objecoes:
                st.info(
                    f"Nenhuma objeção encontrada para o consultor: {consultor_filtro}")
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
        f"🔍 Em Execução ({len(objecoes_por_status[objecao_manager.STATUS_EM_EXECUCAO])})",
        f"✅ Concluídas ({len(objecoes_por_status[objecao_manager.STATUS_CONCLUIDO])})"
    ])

    # Renderizar objeções em cada tab
    status_list = [
        objecao_manager.STATUS_PENDENTE,
        objecao_manager.STATUS_RECEBIDO,
        objecao_manager.STATUS_EM_EXECUCAO,
        objecao_manager.STATUS_CONCLUIDO
    ]

    for i, status in enumerate(status_list):
        with tabs[i]:
            objecoes_list = objecoes_por_status.get(status, [])
            if not objecoes_list:
                st.info(f"Nenhuma objeção {status}.")
                continue

            # Verificar se é a aba "Concluído"
            if status == objecao_manager.STATUS_CONCLUIDO:
                # Organizar por mês primeiro, depois por consultor (apenas para Concluídas)
                objecoes_por_mes = organizar_objecoes_por_mes(objecoes_list)

                for mes_ano, objecoes_do_mes in objecoes_por_mes.items():
                    with st.expander(f"📅 {mes_ano} ({len(objecoes_do_mes)} objeções)"):
                        # Agrupar por consultor dentro do mês
                        objecoes_por_consultor = defaultdict(list)
                        for objecao in objecoes_do_mes:
                            nome = objecao.get('name_consultor', objecao.get(
                                'consultor_objecao', 'Sem Consultor'))
                            objecoes_por_consultor[nome].append(objecao)

                        # Ordenar consultores alfabeticamente
                        for consultor in sorted(objecoes_por_consultor.keys()):
                            objecoes_do_consultor = objecoes_por_consultor[consultor]
                            with st.expander(f"👤 {consultor} ({len(objecoes_do_consultor)})"):
                                for objecao in objecoes_do_consultor:
                                    renderizar_objecao(
                                        objecao, objecao_manager, is_admin)
            else:
                # Para outros status, manter organização normal
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
        if objecao.get('cnpj_cpf_cliente'):
            st.write(f"**CPF/CNPJ:** {objecao.get('cnpj_cpf_cliente', 'N/A')}")
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

        # Verificar se é admin jurídico (APENAS na tabela juridico)
        juridico = st.session_state.supabase_agent.get_juridico_by_id(user_id)
        is_admin_juridico = juridico and juridico.get('is_admin', False)

        if is_admin_juridico:
            st.subheader("Alterar Status")

            # Botões para avançar para o próximo status (sempre na coluna 1)
            if status_atual == objecao_manager.STATUS_PENDENTE:
                if st.button("📥 Recebida", key=f"btn_recebida_{objecao['id']}"):
                    if objecao_manager.atualizar_status_objecao(
                            objecao['id'], objecao_manager.STATUS_RECEBIDO):
                        st.success("✅ Status alterado para 'Recebida'!")
                        st.rerun()

            elif status_atual == objecao_manager.STATUS_RECEBIDO:
                if st.button("🔍 Em Execução", key=f"btn_analise_{objecao['id']}"):
                    if objecao_manager.atualizar_status_objecao(
                            objecao['id'], objecao_manager.STATUS_EM_EXECUCAO):
                        st.success("✅ Status alterado para 'Em Execução'!")
                        st.rerun()

            elif status_atual == objecao_manager.STATUS_EM_EXECUCAO:
                if st.button("✅ Concluída", key=f"btn_concluida_{objecao['id']}"):
                    if objecao_manager.atualizar_status_objecao(
                            objecao['id'], objecao_manager.STATUS_CONCLUIDO):
                        st.success("✅ Status alterado para 'Concluída'!")
                        st.rerun()

                    # Exibir arquivos existentes
        st.subheader("📄 Documentos")

        # Verificar se há arquivos em obejpdf (funcionários)
        if objecao.get('obejpdf'):
            try:
                obejpdf_data = objecao['obejpdf']
                if isinstance(obejpdf_data, dict) and obejpdf_data.get('pdf_urls'):
                    st.write("**📎 Arquivos enviados por funcionário:**")
                    for i, url in enumerate(obejpdf_data['pdf_urls']):
                        if url:
                            st.markdown(f"[📎 Arquivo {i+1}]({url})")
            except Exception as e:
                st.warning(f"Erro ao carregar arquivos: {str(e)}")

        # Verificar se há arquivos em peticaopdf (advogados)
        if objecao.get('peticaopdf'):
            try:
                peticaopdf_data = objecao['peticaopdf']
                if isinstance(peticaopdf_data, dict) and peticaopdf_data.get('pdf_urls'):
                    st.write("**📄 Arquivos enviados por advogado:**")
                    for i, url in enumerate(peticaopdf_data['pdf_urls']):
                        if url:
                            st.markdown(f"[📄 Arquivo {i+1}]({url})")
            except Exception as e:
                st.warning(f"Erro ao carregar arquivos: {str(e)}")

        # Upload de arquivos (apenas quando status for "Em Execução")
        if status_atual == objecao_manager.STATUS_EM_EXECUCAO:
            # Determinar tipo de usuário
            from permission_manager import CargoPermissionManager
            from app import get_user_id

            permission_manager = CargoPermissionManager(
                st.session_state.supabase_agent)
            user_id = get_user_id(st.session_state.user)

            # Verificar se é usuário jurídico (APENAS na tabela juridico)
            juridico = st.session_state.supabase_agent.get_juridico_by_id(
                user_id)

            if not juridico:
                st.info(
                    "Apenas usuários jurídicos (advogados/funcionários) podem fazer upload de arquivos.")
            else:
                # Verificar se é advogado ou funcionário
                is_advogado = juridico.get('cargo', '') == 'advogado'
                is_funcionario = juridico.get('cargo', '') == 'funcionario'

                if is_advogado:
                    st.subheader("📄 Petições")

                    # Usar form para evitar recarregamento automático
                    with st.form(key=f"upload_form_peticoes_{objecao['id']}"):
                        uploaded_files = st.file_uploader(
                            "Adicionar petições",
                            type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png',
                                  'gif', 'bmp', 'mp4', 'avi', 'mov', 'wmv', 'zip', 'rar'],
                            accept_multiple_files=True,
                            key=f"upload_peticoes_{objecao['id']}"
                        )

                        submit_button = st.form_submit_button(
                            "Enviar Arquivos")

                        if submit_button and uploaded_files:
                            with st.spinner("Enviando arquivos e notificando por e-mail..."):
                                if objecao_manager.enviar_documentos_objecao(
                                        objecao, uploaded_files, tipo_usuario="advogado"):
                                    st.success(
                                        "📄 Arquivos enviados com sucesso! E-mail enviado para funcionário responsável")

                                    # Alterar status automaticamente para "Concluída" quando advogado envia petições
                                    try:
                                        objecao_manager.atualizar_status_objecao(
                                            objecao['id'], objecao_manager.STATUS_CONCLUIDO)
                                        st.success(
                                            "✅ Status automaticamente alterado para 'Concluída'!")
                                    except Exception as e:
                                        st.warning(
                                            f"Petições enviadas, mas erro ao alterar status: {str(e)}")

                                    # Limpar o upload após envio bem-sucedido
                                    upload_key = f"upload_peticoes_{objecao['id']}"
                                    if upload_key in st.session_state:
                                        del st.session_state[upload_key]
                                    st.rerun()
                                else:
                                    st.error(
                                        "Erro ao enviar arquivos. Verifique os logs.")

                elif is_funcionario:
                    st.subheader("📎 Documentos")

                    # Usar form para evitar recarregamento automático
                    with st.form(key=f"upload_form_{objecao['id']}"):
                        uploaded_files = st.file_uploader(
                            "Adicionar documentos",
                            type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png',
                                  'gif', 'bmp', 'mp4', 'avi', 'mov', 'wmv', 'zip', 'rar'],
                            accept_multiple_files=True,
                            key=f"upload_docs_{objecao['id']}"
                        )

                        submit_button = st.form_submit_button(
                            "Enviar Arquivos")

                        if submit_button and uploaded_files:
                            with st.spinner("Enviando arquivos e notificando por e-mail..."):
                                if objecao_manager.enviar_documentos_objecao(
                                        objecao, uploaded_files, tipo_usuario="funcionario"):
                                    st.success(
                                        "📎 Arquivos enviados com sucesso! E-mails enviados para consultor e destinatários jurídicos.")
                                    # Limpar o upload após envio bem-sucedido
                                    upload_key = f"upload_docs_{objecao['id']}"
                                    if upload_key in st.session_state:
                                        del st.session_state[upload_key]
                                    st.rerun()
                                else:
                                    st.error(
                                        "Erro ao enviar arquivos. Verifique os logs.")


def formatar_data_br(data_iso):
    """Formata data ISO para formato brasileiro"""
    try:
        data = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
        return data.strftime("%d/%m/%Y %H:%M")
    except:
        return data_iso


@st.cache_data(ttl=60)  # 1 minuto
def formatar_mes_ano_cached(data_str: str) -> str:
    """Cache para formatação de datas para otimizar performance"""
    return formatar_mes_ano_fallback(data_str)


def formatar_mes_ano(data_str):
    """Formata a data para exibição de mês/ano"""
    try:
        if not data_str:
            return "Data não disponível"

        # Mapeamento de meses em português
        meses_pt = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }

        data = None

        # Tentar diferentes formatos de data
        try:
            # Formato ISO com timezone
            if data_str.endswith('Z'):
                data = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
            else:
                # Formato ISO sem timezone
                data = datetime.fromisoformat(data_str)
        except ValueError:
            try:
                # Formato ISO sem timezone (removendo Z se existir)
                data = datetime.fromisoformat(data_str.replace('Z', ''))
            except ValueError:
                try:
                    # Formato brasileiro DD/MM/YYYY
                    if '/' in data_str and len(data_str.split('/')) == 3:
                        dia, mes, ano = data_str.split('/')
                        data = datetime(int(ano), int(mes), int(dia))
                    else:
                        # Tentar outros formatos comuns
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                data = datetime.strptime(data_str, fmt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass

        if data:
            mes_ano_en = data.strftime("%B/%Y")
            mes_en, ano = mes_ano_en.split('/')
            mes_pt = meses_pt.get(mes_en, mes_en)
            resultado = f"{mes_pt}/{ano}"
            return resultado
        else:
            return formatar_mes_ano_fallback(data_str)

    except Exception:
        return formatar_mes_ano_fallback(data_str)


def formatar_mes_ano_fallback(data_str):
    """Função de fallback mais robusta para formatação de data"""
    try:
        if not data_str:
            return "Data não disponível"

        # Se já é uma string de mês/ano, retornar diretamente
        if '/' in data_str and len(data_str.split('/')) == 2:
            return data_str

        # Tentar extrair apenas a data (YYYY-MM-DD) ignorando timezone
        if isinstance(data_str, str):
            # Remover timezone e hora se existir
            data_limpa = data_str.split(
                'T')[0] if 'T' in data_str else data_str
            data_limpa = data_limpa.split(
                ' ')[0] if ' ' in data_limpa else data_limpa
            data_limpa = data_limpa.split(
                '+')[0] if '+' in data_limpa else data_limpa
            data_limpa = data_limpa.split(
                'Z')[0] if 'Z' in data_limpa else data_limpa

            # Verificar se é formato YYYY-MM-DD
            if len(data_limpa.split('-')) == 3:
                ano, mes, dia = data_limpa.split('-')
                try:
                    mes_int = int(mes)
                    ano_int = int(ano)

                    # Mapeamento direto de meses
                    meses = {
                        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
                    }

                    mes_nome = meses.get(mes_int, f'Mês {mes_int}')
                    return f"{mes_nome}/{ano_int}"
                except (ValueError, TypeError):
                    pass

        return "Data não disponível"

    except Exception:
        return "Data não disponível"


def organizar_objecoes_por_mes(objecoes):
    """Organiza as objeções por mês/ano de criação"""
    objecoes_por_mes = defaultdict(list)

    for objecao in objecoes:
        data_criacao = objecao.get('created_at')
        if data_criacao:
            mes_ano = formatar_mes_ano_cached(data_criacao)
            objecoes_por_mes[mes_ano].append(objecao)
        else:
            objecoes_por_mes["Data não disponível"].append(objecao)

    # Ordenar por data (mais recente primeiro)
    def ordenar_mes_ano(mes_ano):
        if mes_ano == "Data não disponível":
            return "0000-00"
        try:
            # Converter "Janeiro/2024" para "2024-01" para ordenação
            mes, ano = mes_ano.split('/')
            meses = {
                'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 'Abril': '04',
                'Maio': '05', 'Junho': '06', 'Julho': '07', 'Agosto': '08',
                'Setembro': '09', 'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
            }
            return f"{ano}-{meses.get(mes, '00')}"
        except:
            return "0000-00"

    return dict(sorted(objecoes_por_mes.items(), key=lambda x: ordenar_mes_ano(x[0]), reverse=True))
