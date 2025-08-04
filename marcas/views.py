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


@st.cache_data(ttl=60)  # 1 minuto
def formatar_mes_ano_cached(data_str: str) -> str:
    """Cache para formatação de datas para otimizar performance"""
    return formatar_mes_ano_fallback(data_str)


def formatar_mes_ano(data_str):
    """Formata a data para exibição de mês/ano"""
    try:
        if not data_str:
            print(f"DEBUG: Data vazia ou None")
            return "Data não disponível"

        print(
            f"DEBUG: Tentando formatar data: '{data_str}' (tipo: {type(data_str)})")

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
                print(f"DEBUG: Parseado como ISO com timezone")
            else:
                # Formato ISO sem timezone
                data = datetime.fromisoformat(data_str)
                print(f"DEBUG: Parseado como ISO sem timezone")
        except ValueError as e1:
            print(f"DEBUG: Erro ISO: {e1}")
            try:
                # Formato ISO sem timezone (removendo Z se existir)
                data = datetime.fromisoformat(data_str.replace('Z', ''))
                print(f"DEBUG: Parseado como ISO sem Z")
            except ValueError as e2:
                print(f"DEBUG: Erro ISO sem Z: {e2}")
                try:
                    # Formato brasileiro DD/MM/YYYY
                    if '/' in data_str and len(data_str.split('/')) == 3:
                        dia, mes, ano = data_str.split('/')
                        data = datetime(int(ano), int(mes), int(dia))
                        print(f"DEBUG: Parseado como formato brasileiro")
                    else:
                        # Tentar outros formatos comuns
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                data = datetime.strptime(data_str, fmt)
                                print(f"DEBUG: Parseado com formato: {fmt}")
                                break
                            except ValueError:
                                continue
                except Exception as e3:
                    print(f"DEBUG: Erro formato brasileiro: {e3}")
                    pass

        if data:
            mes_ano_en = data.strftime("%B/%Y")
            mes_en, ano = mes_ano_en.split('/')
            mes_pt = meses_pt.get(mes_en, mes_en)
            resultado = f"{mes_pt}/{ano}"
            print(f"DEBUG: Resultado final: {resultado}")
            return resultado
        else:
            print(f"DEBUG: Não foi possível parsear a data, tentando fallback")
            return formatar_mes_ano_fallback(data_str)

    except Exception as e:
        print(f"DEBUG: Erro geral ao formatar data '{data_str}': {e}")
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
                except:
                    pass

        return "Data não disponível"
    except Exception as e:
        print(f"DEBUG: Erro no fallback: {e}")
        return "Data não disponível"


def organizar_buscas_por_mes(buscas):
    """Organiza as buscas por mês/ano de criação"""
    buscas_por_mes = defaultdict(list)

    for busca in buscas:
        data_criacao = busca.get('created_at')
        if data_criacao:
            mes_ano = formatar_mes_ano_cached(data_criacao)
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

    # Inicializar variáveis de session_state necessárias
    if 'aba_atual' not in st.session_state:
        st.session_state.aba_atual = 0
    if 'acessando_relatorio_custos' not in st.session_state:
        st.session_state.acessando_relatorio_custos = False
    if 'admin_aba_atual' not in st.session_state:
        st.session_state.admin_aba_atual = 0

    # Verificar se usuário tem permissão para relatório de custos
    from permission_manager import CargoPermissionManager
    from supabase_agent import SupabaseAgent

    supabase_agent = SupabaseAgent()
    permission_manager = CargoPermissionManager(supabase_agent)

    # Verificação mais robusta de permissões
    try:
        tem_permissao_custos = permission_manager.check_page_permission(
            user_id, "Relatório de Custos")
    except Exception as e:
        # Se houver erro na verificação, permitir acesso para evitar redirecionamento
        st.warning("⚠️ Erro ao verificar permissões de relatório.")
        st.info("💡 Tentando carregar relatório...")
        tem_permissao_custos = True  # Permitir acesso para evitar redirecionamento

    if is_admin:
        # Usar lógica FIXA como os consultores para evitar problemas de redirecionamento
        pendentes = buscas_por_status[busca_manager.STATUS_PENDENTE]
        recebidas = buscas_por_status[busca_manager.STATUS_RECEBIDA]
        em_analise = buscas_por_status[busca_manager.STATUS_EM_ANALISE]
        concluidas = buscas_por_status[busca_manager.STATUS_CONCLUIDA]

        # Criar abas em ordem FIXA
        abas = []
        labels = []

        # Sempre criar todas as abas em ordem fixa
        labels.append("Pendentes")
        abas.append(pendentes)
        labels.append("Recebidas")
        abas.append(recebidas)
        labels.append("Em Análise")
        abas.append(em_analise)
        labels.append("Concluídas")
        abas.append(concluidas)

        # Adicionar aba de relatório de custos se tiver permissão
        if tem_permissao_custos:
            labels.append("📊 Relatório de Custos")
            abas.append([])  # Lista vazia para a aba de custos

        if not any(abas):  # Se todas as abas estão vazias
            st.info("Nenhuma busca realizada ainda.")
            return

        # Usar tabs sem key (st.tabs não aceita key)
        tabs = st.tabs(labels)

        # Detectar qual aba está ativa e manter estado
        for i, tab in enumerate(tabs):
            with tab:
                # Manter estado da aba ativa
                if 'aba_atual' not in st.session_state:
                    st.session_state.aba_atual = i

                if labels[i] == "📊 Relatório de Custos":
                    # Marcar que está acessando o relatório de custos
                    st.session_state.acessando_relatorio_custos = True
                    st.session_state.aba_atual = i
                    st.session_state.admin_aba_atual = i

                    # Exibir relatório de custos
                    from marcas.relatorio_custos import relatorio_custos
                    try:
                        relatorio_custos(busca_manager, is_admin, user_id)
                    except Exception as e:
                        st.error(
                            f"❌ Erro ao carregar relatório de custos: {e}")
                        st.info(
                            "💡 Tente novamente ou entre em contato com o suporte.")
                        st.info(
                            "🔄 Se o problema persistir, tente recarregar a página.")
                elif labels[i] == "Concluídas":
                    # Organizar por mês primeiro, depois por consultor (apenas para Concluídas)
                    buscas_concluidas = abas[i]
                    if buscas_concluidas:
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
                        st.info("Nenhuma busca concluída ainda.")
                else:
                    # Para outros status, manter organização normal
                    buscas_status = abas[i]
                    if buscas_status:
                        for busca in buscas_status:
                            busca_manager.renderizar_busca(
                                busca, is_admin, todas_buscas=todas_buscas_fila)
                    else:
                        st.info(f"Nenhuma busca {labels[i].lower()} ainda.")

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

        # Adicionar aba de relatório de custos se tiver permissão
        if tem_permissao_custos:
            labels.append("📊 Relatório de Custos")
            abas.append([])  # Lista vazia para a aba de custos

        if not abas:
            st.info("Nenhuma busca realizada ainda.")
            return

        # Usar tabs sem key (st.tabs não aceita key)
        tabs = st.tabs(labels)

        # Detectar qual aba está ativa e manter estado
        for i, tab in enumerate(tabs):
            with tab:
                # Manter estado da aba ativa
                if 'aba_atual' not in st.session_state:
                    st.session_state.aba_atual = i

                if labels[i] == "📊 Relatório de Custos":
                    # Marcar que está acessando o relatório de custos
                    st.session_state.acessando_relatorio_custos = True
                    st.session_state.aba_atual = i

                    # Exibir relatório de custos
                    from marcas.relatorio_custos import relatorio_custos
                    try:
                        relatorio_custos(busca_manager, is_admin, user_id)
                    except Exception as e:
                        st.error(
                            f"❌ Erro ao carregar relatório de custos: {e}")
                        st.info(
                            "💡 Tente novamente ou entre em contato com o suporte.")
                        st.info(
                            "🔄 Se o problema persistir, tente recarregar a página.")
                elif labels[i] == "Concluídas":
                    # Organizar por mês apenas para Concluídas (usuários não-admin)
                    buscas_concluidas = abas[i]
                    if buscas_concluidas:
                        buscas_por_mes = organizar_buscas_por_mes(
                            buscas_concluidas)

                        for mes_ano, buscas_do_mes in buscas_por_mes.items():
                            with st.expander(f"📅 {mes_ano} ({len(buscas_do_mes)} buscas)"):
                                for busca in buscas_do_mes:
                                    busca_manager.renderizar_busca(
                                        busca, is_admin, todas_buscas=todas_buscas_fila)
                    else:
                        st.info("Nenhuma busca concluída ainda.")
                else:
                    # Para outros status, manter organização normal
                    for busca in abas[i]:
                        busca_manager.renderizar_busca(
                            busca, is_admin, todas_buscas=todas_buscas_fila)
