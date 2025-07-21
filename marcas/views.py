from marcas.busca_manager import get_user_attr
import streamlit as st
MODULO_INFO = {
    "nome": "Marcas",
    "emoji": "🏷️",
    "opcoes": ["Solicitar Busca", "Minhas Buscas"]
}


def solicitar_busca(form_agent, busca_manager):
    st.header("Solicitar Busca de Marca")
    if st.session_state.get('enviando_pedido', False):
        # Overlay será mostrado pelo form_agent
        form_agent.collect_data()  # para garantir overlay
        with st.spinner("Enviando pedido de busca..."):
            pass  # Removido salvamento duplicado
        st.session_state.enviando_pedido = False
        from ui_components import limpar_formulario
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


def minhas_buscas(busca_manager, is_admin, todas_buscas_fila=None):
    st.header("Minhas Buscas de Marca")
    if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
        st.error("Você precisa estar logado para acessar esta funcionalidade.")
        st.stop()
    st.markdown("<h2>Buscas Solicitadas</h2>", unsafe_allow_html=True)

    # Campo de busca unificado
    busca_geral = st.text_input(
        "Pesquisar marca ou consultor...", key="busca_geral")

    # Buscar buscas do usuário (para exibir)
    def get_user_id(user):
        if isinstance(user, dict):
            return user.get('id')
        return getattr(user, 'id', None)
    user_id = get_user_id(st.session_state.user)
    buscas = busca_manager.buscar_buscas_usuario(
        user_id,
        is_admin=is_admin
    )

    # Filtro unificado
    if busca_geral:
        termo = busca_geral.lower()
        buscas = [
            b for b in buscas
            if termo in b.get('marca', '').lower() or termo in b.get('nome_consultor', '').lower()
        ]

    # Ordenar por prioridade
    buscas = busca_manager.ordenar_buscas_prioridade(buscas)

    # Buscar todas as buscas para a fila global (para contagem)
    todas_buscas_fila = busca_manager.buscar_buscas_usuario(is_admin=True)
    if busca_geral:
        termo = busca_geral.lower()
        todas_buscas_fila = [
            b for b in todas_buscas_fila
            if termo in b.get('marca', '').lower() or termo in b.get('nome_consultor', '').lower()
        ]
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
                if labels[i] == "Concluídas":
                    # Agrupar por consultor
                    from collections import defaultdict
                    buscas_por_consultor = defaultdict(list)
                    for busca in abas[i]:
                        nome = busca.get('nome_consultor', 'Sem Consultor')
                        buscas_por_consultor[nome].append(busca)
                    for consultor, buscas_do_consultor in buscas_por_consultor.items():
                        with st.expander(f"Consultor: {consultor} ({len(buscas_do_consultor)})"):
                            for busca in buscas_do_consultor:
                                busca_manager.renderizar_busca(
                                    busca, is_admin, todas_buscas=todas_buscas_fila)
                else:
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
