from marcas.busca_manager import get_user_attr
import streamlit as st
from datetime import datetime
from collections import defaultdict
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
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                            try:
                                data = datetime.strptime(data_str, fmt)
                                break
                            except ValueError:
                                continue
                except:
                    pass

        if data:
            mes_ano_en = data.strftime("%B/%Y")
            mes_en, ano = mes_ano_en.split('/')
            mes_pt = meses_pt.get(mes_en, mes_en)
            return f"{mes_pt}/{ano}"
        else:
            return "Data não disponível"

    except Exception as e:
        print(f"Erro ao formatar data '{data_str}': {e}")
        return "Data não disponível"


def organizar_buscas_por_mes(buscas):
    """Organiza as buscas por mês/ano de criação"""
    buscas_por_mes = defaultdict(list)

    for busca in buscas:
        data_criacao = busca.get('created_at')
        if data_criacao:
            mes_ano = formatar_mes_ano(data_criacao)
            buscas_por_mes[mes_ano].append(busca)
        else:
            buscas_por_mes["Data não disponível"].append(busca)

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

    return dict(sorted(buscas_por_mes.items(), key=lambda x: ordenar_mes_ano(x[0]), reverse=True))


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

    # Se é admin, buscar todas as buscas
    if is_admin:
        buscas = busca_manager.buscar_buscas_usuario(is_admin=True)
    else:
        # Para não-admin, buscar apenas buscas do consultor
        buscas = busca_manager.buscar_buscas_usuario(user_id, is_admin=False)

    # Filtro unificado
    if busca_geral:
        termo = busca_geral.lower()
        buscas = [
            b for b in buscas
            if termo in b.get('marca', '').lower() or termo in b.get('nome_consultor', '').lower()
        ]

    # Ordenar por prioridade
    buscas = busca_manager.ordenar_buscas_prioridade(buscas)

    # Buscar todas as buscas para a fila global (apenas se necessário)
    todas_buscas_fila = None
    if not is_admin:
        # Para não-admin, buscar todas as buscas apenas para calcular posição na fila
        todas_buscas_fila = busca_manager.buscar_buscas_usuario(is_admin=True)
        if busca_geral:
            termo = busca_geral.lower()
            todas_buscas_fila = [
                b for b in todas_buscas_fila
                if termo in b.get('marca', '').lower() or termo in b.get('nome_consultor', '').lower()
            ]
        todas_buscas_fila = busca_manager.ordenar_buscas_prioridade(
            todas_buscas_fila)
    else:
        # Para admin, usar as mesmas buscas já filtradas
        todas_buscas_fila = buscas

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
                    # Organizar por mês primeiro, depois por consultor (apenas para Concluídas)
                    buscas_concluidas = abas[i]
                    buscas_por_mes = organizar_buscas_por_mes(
                        buscas_concluidas)

                    for mes_ano, buscas_do_mes in buscas_por_mes.items():
                        with st.expander(f"📅 {mes_ano} ({len(buscas_do_mes)} buscas)"):
                            # Agrupar por consultor dentro do mês
                            buscas_por_consultor = defaultdict(list)
                            for busca in buscas_do_mes:
                                nome = busca.get(
                                    'nome_consultor', 'Sem Consultor')
                                buscas_por_consultor[nome].append(busca)

                            # Ordenar consultores alfabeticamente
                            for consultor in sorted(buscas_por_consultor.keys()):
                                buscas_do_consultor = buscas_por_consultor[consultor]
                                with st.expander(f"👤 {consultor} ({len(buscas_do_consultor)})"):
                                    for busca in buscas_do_consultor:
                                        busca_manager.renderizar_busca(
                                            busca, is_admin, todas_buscas=todas_buscas_fila)
                else:
                    # Para outros status, manter organização normal (sem divisão por mês)
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
                if labels[i] == "Concluídas":
                    # Organizar por mês apenas para Concluídas (usuários não-admin)
                    buscas_concluidas = abas[i]
                    buscas_por_mes = organizar_buscas_por_mes(
                        buscas_concluidas)

                    for mes_ano, buscas_do_mes in buscas_por_mes.items():
                        with st.expander(f"📅 {mes_ano} ({len(buscas_do_mes)} buscas)"):
                            for busca in buscas_do_mes:
                                busca_manager.renderizar_busca(
                                    busca, is_admin, todas_buscas=todas_buscas_fila)
                else:
                    # Para outros status, manter organização normal
                    for busca in abas[i]:
                        busca_manager.renderizar_busca(
                            busca, is_admin, todas_buscas=todas_buscas_fila)
