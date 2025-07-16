# app.py
import streamlit as st
from form_agent import FormAgent
from email_agent import EmailAgent
from supabase_agent import SupabaseAgent
from ui_components import apply_global_styles, render_login_screen, render_sidebar, limpar_formulario
from busca_manager import BuscaManager
from config import carregar_configuracoes, configurar_logging
from busca_manager import get_user_attr


def get_user_id(user):
    if isinstance(user, dict):
        return user.get('id')
    return getattr(user, 'id', None)


def main():
    """Função principal da aplicação"""
    # Carregar configurações
    config = carregar_configuracoes()
    configurar_logging()

    # Aplicar estilos globais
    apply_global_styles()

    # Inicializar agentes
    supabase_agent = SupabaseAgent()
    email_agent = EmailAgent(
        config["smtp_host"],
        config["smtp_port"],
        config["smtp_user"],
        config["smtp_pass"],
        config["destinatarios"]
    )
    busca_manager = BuscaManager(supabase_agent, email_agent)
    form_agent = FormAgent()

    # Tela de login
    if "user" not in st.session_state:
        render_login_screen(supabase_agent)
        return

    # Controle de envio para bloquear ações
    if "enviando_pedido" not in st.session_state:
        st.session_state.enviando_pedido = False

    # Renderizar sidebar e obter menu selecionado
    menu = render_sidebar()

    # Verificar se é admin usando o BuscaManager
    is_admin = busca_manager.verificar_acesso_admin(st.session_state.user)

    # Navegação baseada no menu
    if menu == "Solicitar Busca":
        renderizar_pagina_solicitar_busca(form_agent, busca_manager)
    elif menu == "Minhas Buscas":
        renderizar_pagina_minhas_buscas(busca_manager, is_admin)


def renderizar_pagina_solicitar_busca(form_agent, busca_manager):
    """Renderiza a página de solicitar busca"""
    if st.session_state.get('enviando_pedido', False):
        # Overlay será mostrado pelo form_agent
        form_agent.collect_data()  # para garantir overlay
        with st.spinner("Enviando pedido de busca..."):
            pass  # Removido salvamento duplicado
        st.session_state.enviando_pedido = False
        limpar_formulario()
        st.session_state["form_nonce"] = st.session_state.get(
            "form_nonce", 0) + 1
        st.rerun()
    else:
        form_data = form_agent.collect_data()
        if form_data and st.session_state.get('envio_sucesso', False):
            st.session_state['last_form_data'] = form_data
            st.session_state.enviando_pedido = True

            # Enviar busca usando o manager
            if busca_manager.enviar_busca(form_data):
                st.rerun()


def renderizar_pagina_minhas_buscas(busca_manager, is_admin):
    """Renderiza a página de minhas buscas"""
    if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
        st.error("Você precisa estar logado para acessar esta funcionalidade.")
        st.stop()
    st.markdown("<h2>Buscas Solicitadas</h2>", unsafe_allow_html=True)

    # Campos de busca
    busca_marca = st.text_input("Pesquisar marca...", key="busca_marca")
    busca_consultor = None
    if is_admin:
        busca_consultor = st.text_input(
            "Pesquisar consultor...", key="busca_consultor")

    # Buscar buscas do usuário (para exibir)
    user_id = get_user_id(st.session_state.user)
    buscas = busca_manager.buscar_buscas_usuario(
        user_id,
        is_admin=is_admin
    )
    buscas = busca_manager.filtrar_buscas(buscas, busca_marca, busca_consultor)
    # Ordenar por prioridade
    buscas = busca_manager.ordenar_buscas_prioridade(buscas)

    # Buscar todas as buscas para a fila global (para contagem)
    todas_buscas_fila = busca_manager.buscar_buscas_usuario(is_admin=True)
    todas_buscas_fila = busca_manager.filtrar_buscas(
        todas_buscas_fila, busca_marca, None)
    # Ordenar por prioridade
    todas_buscas_fila = busca_manager.ordenar_buscas_prioridade(
        todas_buscas_fila)

    # Organizar buscas por status
    buscas_por_status = busca_manager.separar_buscas_por_status(buscas)

    if is_admin:
        abas = []
        labels = []
        status_keys = [
            (busca_manager.STATUS_PENDENTE, "Pendentes"),
            (busca_manager.STATUS_RECEBIDA, "Recebidas"),
            (busca_manager.STATUS_EM_ANALISE, "Em Análise"),
            (busca_manager.STATUS_CONCLUIDA, "Concluídas")
        ]
        for status, label in status_keys:
            buscas_status = buscas_por_status[status]
            if buscas_status:
                labels.append(label)
                abas.append(buscas_status)
        if not abas:
            st.info("Nenhuma busca realizada ainda.")
            return
        tabs = st.tabs(labels)
        for i, tab in enumerate(tabs):
            with tab:
                for busca in abas[i]:
                    busca_manager.renderizar_busca(
                        busca, is_admin, todas_buscas=todas_buscas_fila)
    else:
        enviadas = buscas_por_status[busca_manager.STATUS_PENDENTE] + \
            buscas_por_status[busca_manager.STATUS_RECEBIDA] + \
            buscas_por_status[busca_manager.STATUS_EM_ANALISE]
        concluidas = buscas_por_status[busca_manager.STATUS_CONCLUIDA]
        abas = []
        labels = []
        if enviadas:
            labels.append("Enviadas")
            abas.append(enviadas)
        if concluidas:
            labels.append("Concluídas")
            abas.append(concluidas)
        if not abas:
            st.info("Nenhuma busca realizada ainda.")
            return
        tabs = st.tabs(labels)
        for i, tab in enumerate(tabs):
            with tab:
                for busca in abas[i]:
                    busca_manager.renderizar_busca(
                        busca, is_admin, todas_buscas=todas_buscas_fila)


if __name__ == "__main__":
    main()
