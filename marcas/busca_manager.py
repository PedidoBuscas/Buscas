import streamlit as st
import json
import re
import logging
from typing import List, Dict, Any, Optional
from pdf_generator import gerar_pdf_busca
from ui_components import exibir_especificacoes_card
from config import USUARIOS_ADMIN


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
    STATUS_EM_ANALISE = "em_analise"
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
        busca_data = dict(form_data)
        busca_data["nome_consultor"] = form_data.get("consultor", "")
        busca_data.pop("consultor", None)

        if "marcas" in busca_data and busca_data["marcas"]:
            busca_data["marca"] = busca_data["marcas"][0]["marca"]
            busca_data["classes"] = json.dumps(
                [c["classe"] for c in busca_data["marcas"][0]["classes"]])
            busca_data["especificacoes"] = ", ".join(
                [c["especificacao"] for c in busca_data["marcas"][0]["classes"]])

        # Salvar o dicionário completo no campo dados_completos
        busca_data["dados_completos"] = json.dumps(
            form_data, ensure_ascii=False)
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
            form_data["consultor_email"] = st.session_state.get(
                "consultor_email", "")

            # Enviar e-mail
            with st.spinner("Enviando e-mail..."):
                self.email_agent.send_email(form_data)

            # Salvar no banco
            ok = self.supabase_agent.insert_busca_rest(
                busca_data, st.session_state.jwt_token)

            if ok:
                st.success("Busca salva no Supabase!")
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

    def deletar_busca(self, busca_id: str) -> bool:
        """
        Deleta uma busca.

        Args:
            busca_id: ID da busca

        Returns:
            bool: True se deletado com sucesso
        """
        if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            st.stop()
        ok = self.supabase_agent.delete_busca_rest(
            busca_id, st.session_state.jwt_token)
        if ok:
            st.success("Busca apagada com sucesso!")
            return True
        else:
            st.error("Erro ao apagar busca!")
            return False

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
            self.STATUS_EM_ANALISE: "Em Análise",
            self.STATUS_CONCLUIDA: "Concluída"
        }
        return status_map.get(status, status)

    def get_status_icon(self, status: str) -> str:
        """Retorna o ícone para cada status"""
        icon_map = {
            self.STATUS_PENDENTE: "⏳",
            self.STATUS_RECEBIDA: "📥",
            self.STATUS_EM_ANALISE: "🔍",
            self.STATUS_CONCLUIDA: "✅"
        }
        return icon_map.get(status, "❓")

    def get_status_atual(self, busca: Dict[str, Any]) -> str:
        """
        Determina o status atual baseado em status_busca persistente no banco.
        """
        status = busca.get('status_busca', self.STATUS_PENDENTE)
        if status not in [self.STATUS_PENDENTE, self.STATUS_RECEBIDA, self.STATUS_EM_ANALISE, self.STATUS_CONCLUIDA]:
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

            if busca.get('observacao'):
                st.write(f"Observação: {busca.get('observacao')}")

            # Upload de PDF para admin APENAS se status for EM_ANALISE ou CONCLUIDA
            if is_admin and status in [self.STATUS_EM_ANALISE, self.STATUS_CONCLUIDA]:
                st.markdown("---")
                st.write("Upload do PDF do resultado da busca:")
                uploaded_files = st.file_uploader("Selecione os PDFs", type=[
                                                  "pdf"], accept_multiple_files=True, key=f"pdf_{busca['id']}")
                if uploaded_files and st.button("Enviar PDF(s)", key=f"btn_pdf_{busca['id']}"):
                    admin_uid = get_user_id(st.session_state.user)
                    st.info(f"UID do admin logado no upload: {admin_uid}")
                    pdf_urls = []
                    for file in uploaded_files:
                        file_name = f"{admin_uid}/{busca['id']}_{file.name}"
                        url = self.supabase_agent.upload_pdf_to_storage(
                            file, file_name, st.session_state.jwt_token)
                        pdf_urls.append(url)
                    # Atualiza pdf_buscas como lista de URLs
                    self.supabase_agent.update_busca_pdf_url(
                        busca['id'], pdf_urls)
                    # Se estiver em análise, já marca como concluída
                    if status == self.STATUS_EM_ANALISE:
                        self.atualizar_status_busca(
                            busca['id'], self.STATUS_CONCLUIDA)
                        # NOVO: Usar o e-mail salvo na busca
                        consultor_email = busca.get(
                            'consultor_email', '').strip()
                        if consultor_email:
                            for file in uploaded_files:
                                pdf_bytes = file.getvalue()
                                marca = busca.get('marca', '')
                                consultor_nome = busca.get(
                                    'nome_consultor', '')
                                assunto = f"Busca Concluída - {marca} - {consultor_nome}"
                                corpo = f"""<div style=\"font-family: Arial, sans-serif; font-size: 12pt;\">\nOlá,\n\nSegue em anexo o resultado da busca.\n\nDados da busca:\n- Marca: {marca}\n- Consultor: {consultor_nome}\n- Tipo de busca: {busca.get('tipo_busca', '')}\n- Data: {busca.get('data', '')}\n- Classes: {busca.get('classes', '')}\n- Especificações: {busca.get('especificacoes', '')}\n\nAtenciosamente,\nEquipe AGP Consultoria\n</div>"""
                                self.email_agent.send_email_com_anexo(
                                    destinatario=consultor_email,
                                    assunto=assunto,
                                    corpo=corpo,
                                    anexo_bytes=pdf_bytes,
                                    nome_arquivo=f"busca_{busca['id']}_{file.name}"
                                )
                        else:
                            st.warning(
                                f"E-mail do consultor não encontrado na busca (busca id: {busca.get('id')})")
                    st.success("PDF(s) enviado(s) com sucesso!")
                    st.rerun()

            # Exibir links de download dos PDFs se existirem
            if busca.get("pdf_buscas"):
                pdfs = busca["pdf_buscas"]
                if isinstance(pdfs, str):
                    pdfs = [pdfs]
                st.markdown("**PDF(s) do resultado:**")
                for i, url in enumerate(pdfs):
                    st.markdown(f"[📄 PDF {i+1}]({url})",
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

            for i, marca in enumerate(dados.get("marcas", [])):
                st.markdown(
                    f"<b>Marca:</b> {marca.get('marca', '')}", unsafe_allow_html=True)
                for classe in marca.get("classes", []):
                    classe_num = classe.get("classe", "")
                    especificacao = classe.get("especificacao", "")

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

        # Exibir botão de apagar apenas para o admin@agpmarcas.com
        from config import USUARIOS_ADMIN
        user_email = None
        if hasattr(st.session_state.user, 'email'):
            user_email = st.session_state.user.email
        elif isinstance(st.session_state.user, dict):
            user_email = st.session_state.user.get('email')
        if user_email == 'admin@agpmarcas.com':
            with col1:
                if st.button("��️ Apagar", key=f"apagar_{busca['id']}"):
                    if self.deletar_busca(busca['id']):
                        st.rerun()

        if is_admin:
            status_atual = self.get_status_atual(busca)
            col_status = st.columns(1)[0]
            with col_status:
                # Avançar para próxima etapa
                if status_atual == self.STATUS_RECEBIDA:
                    if st.button("🔍 Em Análise", key=f"analise_{busca['id']}"):
                        if self.atualizar_status_busca(busca['id'], self.STATUS_EM_ANALISE):
                            st.rerun()
                elif status_atual == self.STATUS_EM_ANALISE:
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
        """Ordena buscas: Em Análise primeiro, depois Recebida, depois Pendente; dentro de cada status, Paga antes de Cortesia, depois por data."""
        def prioridade_busca(b):
            status = self.get_status_atual(b)
            # Menor valor = maior prioridade
            if status == self.STATUS_EM_ANALISE:
                prioridade_status = 0
            elif status == self.STATUS_RECEBIDA:
                prioridade_status = 1
            else:  # PENDENTE
                prioridade_status = 2
            tipo = str(b.get('tipo_busca', '')).strip().lower()
            prioridade_tipo = 0 if tipo == 'paga' else 1
            data = b.get('data', '')
            return (prioridade_status, prioridade_tipo, data)
        return sorted(buscas, key=prioridade_busca)

    def get_posicao_na_fila(self, busca: Dict[str, Any], todas_buscas: List[Dict[str, Any]]) -> int:
        """Retorna quantas buscas estão na frente da busca informada na fila de análise (status RECEBIDA, PENDENTE ou EM_ANALISE, ordenadas por prioridade)."""
        # Considera buscas RECEBIDA, PENDENTE e EM_ANALISE
        pendentes = [b for b in todas_buscas if self.get_status_atual(
            b) in [self.STATUS_RECEBIDA, self.STATUS_PENDENTE, self.STATUS_EM_ANALISE]]
        pendentes_ordenadas = self.ordenar_buscas_prioridade(pendentes)
        # Busca o índice da busca na lista ordenada
        for idx, b in enumerate(pendentes_ordenadas):
            if b.get('id') == busca.get('id'):
                return idx  # idx é o número de buscas na frente
        return -1  # Não encontrada

    def separar_buscas_por_status(self, buscas: List[Dict[str, Any]]) -> dict:
        """
        Separa as buscas em listas por status.
        Retorna um dicionário: {status: [buscas]}
        """
        status_dict = {
            self.STATUS_PENDENTE: [],
            self.STATUS_RECEBIDA: [],
            self.STATUS_EM_ANALISE: [],
            self.STATUS_CONCLUIDA: []
        }
        for busca in buscas:
            status = self.get_status_atual(busca)
            if status in status_dict:
                status_dict[status].append(busca)
        return status_dict
