# app.py
import streamlit as st
from marcas import views as marcas_views
from patentes import views as patentes_views
from objeções import views as objeções_views
from marcas.busca_manager import BuscaManager, get_user_attr
from form_agent import FormAgent
from email_agent import EmailAgent
from supabase_agent import SupabaseAgent
from ui_components import apply_global_styles, render_login_screen, render_sidebar, limpar_formulario, limpar_session_state, limpar_cache_completo
from config import carregar_configuracoes, configurar_logging
from permission_manager import CargoPermissionManager


def get_user_id(user):
    """Extrai o ID do usuário de forma segura"""
    if isinstance(user, dict):
        return user.get('id')
    return getattr(user, 'id', None)


def get_user_permissions_direct(user_id, permission_manager):
    """Obtém permissões do usuário diretamente sem cache"""
    try:
        return {
            'user_info': permission_manager.get_user_display_info(user_id),
            'cargo_info': permission_manager.get_user_cargo_info(user_id),
            'available_menu': permission_manager.get_available_menu_items(user_id),
            'menu_icons': permission_manager.get_icons_for_menu(
                permission_manager.get_available_menu_items(user_id)
            )
        }
    except Exception as e:

        return None


def get_user_permissions_isolated(user_id, permission_manager):
    """Obtém permissões do usuário com isolamento por sessão"""
    # Criar chave única para o usuário
    cache_key = f"user_permissions_{user_id}"

    # Verificar se já temos as permissões no session_state
    if cache_key in st.session_state:
        cached_data = st.session_state[cache_key]
        # Verificar se os dados são válidos
        if cached_data and isinstance(cached_data, dict):
            return cached_data

    # Se não temos cache ou é inválido, buscar diretamente
    permissions_data = get_user_permissions_direct(user_id, permission_manager)

    # Armazenar no session_state para este usuário específico
    if permissions_data:
        st.session_state[cache_key] = permissions_data

    return permissions_data


def clear_user_cache(user_id):
    """Limpa o cache específico do usuário"""
    cache_key = f"user_permissions_{user_id}"
    if cache_key in st.session_state:
        del st.session_state[cache_key]


def get_image_base64(image_path):
    """Converte imagem para base64"""
    import base64
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:

        return ""


def main():
    # Configurar página com ícone personalizado
    st.set_page_config(
        page_title="A2NUNES",
        page_icon="a2nunes.jpeg",  # Nova logo
        layout="centered",
        initial_sidebar_state="expanded"
    )

    config = carregar_configuracoes()
    configurar_logging()

    # Criar agentes sem cache para evitar compartilhamento entre usuários
    supabase_agent = SupabaseAgent()
    email_agent = EmailAgent(
        config["smtp_host"],
        config["smtp_port"],
        config["smtp_user"],
        config["smtp_pass"],
        config["destinatarios"],
        config["destinatario_juridico"],
        config["destinatario_juridico_um"]
    )
    busca_manager = BuscaManager(supabase_agent, email_agent)
    form_agent = FormAgent()
    permission_manager = CargoPermissionManager(supabase_agent)

    # Inicializar agentes no session_state
    if "supabase_agent" not in st.session_state:
        st.session_state.supabase_agent = supabase_agent

    if "email_agent" not in st.session_state:
        st.session_state.email_agent = email_agent

    # Garantir que email_agent sempre esteja disponível
    st.session_state.email_agent = email_agent

    if "user" not in st.session_state:
        render_login_screen(supabase_agent)
        return

    # Aplicar estilos globais apenas quando o usuário estiver logado
    apply_global_styles()

    if "enviando_pedido" not in st.session_state:
        st.session_state.enviando_pedido = False

    # Obter informações do usuário
    user_id = get_user_id(st.session_state.user)

    # Validação de segurança: verificar se o usuário atual é o correto
    jwt_token = st.session_state.get('jwt_token', '')
    if not user_id or not jwt_token:
        st.error("Sessão inválida. Por favor, faça login novamente.")
        # Limpar cache e session_state
        st.cache_data.clear()
        limpar_session_state()
        st.rerun()

    # Verificar se o JWT token ainda é válido
    try:
        # Tentar fazer uma requisição simples para validar o token
        test_profile = supabase_agent.get_profile(user_id)
        if not test_profile:
            st.error("Token expirado. Por favor, faça login novamente.")
            clear_user_cache(user_id)
            st.cache_data.clear()
            limpar_session_state()
            st.rerun()
    except Exception as e:
        st.error("Erro de autenticação. Por favor, faça login novamente.")
        clear_user_cache(user_id)
        st.cache_data.clear()
        limpar_session_state()
        st.rerun()

    # Obter permissões do usuário
    permissions_data = get_user_permissions_isolated(
        user_id, permission_manager)

    # Se não conseguiu obter permissões, mostrar erro
    if permissions_data is None:
        st.error(
            "Erro ao carregar permissões do usuário. Por favor, faça login novamente.")
        st.cache_data.clear()
        limpar_session_state()
        st.rerun()

    user_info = permissions_data['user_info']
    cargo_info = permissions_data['cargo_info']
    available_menu_items = permissions_data['available_menu']
    menu_icons = permissions_data['menu_icons']

    with st.sidebar:
        # Adicionar logo e informações do usuário
        st.image("a2nunes.jpeg", width=120)

        # Exibir informações do usuário com cargo
        if user_info['nome']:
            st.markdown(
                f"<div style='color:#434f65;font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;'>"
                f"<span style='font-size:1.3em;margin-right:7px;vertical-align:middle;'>"
                f"<svg width='22' height='22' viewBox='0 0 24 24' fill='#434f65' xmlns='http://www.w3.org/2000/svg' style='display:inline-block;vertical-align:middle;'><path d='M12 12c2.7 0 8 1.34 8 4v2H4v-2c0-2.66 5.3-4 8-4zm0-2a4 4 0 100-8 4 4 0 000 8z'/></svg>"
                f"</span>{user_info['nome']}</div>",
                unsafe_allow_html=True
            )

        # Verificar se há itens no menu
        if not available_menu_items:
            st.error("Nenhuma opção de menu disponível para seu perfil.")
            return

        # Menu filtrado por permissões
        from streamlit_option_menu import option_menu
        escolha = option_menu(
            menu_title=None,
            options=available_menu_items,
            icons=menu_icons,
            key="menu_unico",
            styles={
                "container": {"padding": "0!important", "background-color": "#ffffff", "width": "100%"},
                "icon": {"color": "#434f65", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                                  "margin": "2px 0",
                                  "color": "#434f65",
                                  "background-color": "#f8f9fa",
                                  "border-radius": "6px",
                                  "padding": "8px 16px"
                },
                "nav-link-selected": {
                    "background-color": "#434f65",
                    "color": "#fff",
                    "font-size": "15px",
                    "border-radius": "6px",
                    "padding": "8px 16px"
                },
            }
        )

        # Separador visual
        st.markdown(
            "<hr style='margin: 20px 0; border-color: #e0e0e0;'>", unsafe_allow_html=True)

        # Adicionar espaço extra para empurrar o botão para baixo
        st.markdown("<div style='height: 20px;'></div>",
                    unsafe_allow_html=True)

        # Botão de logout simples em cinza
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # CSS para botão cinza
            st.markdown("""
            <style>
            [data-testid="baseButton-secondary"] {
                background-color: #6c757d !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 12px 24px !important;
                font-weight: 600 !important;
                font-size: 1rem !important;
                transition: all 0.2s !important;
                box-shadow: 0 2px 8px rgba(108, 117, 125, 0.3) !important;
                width: 100% !important;
                max-width: 200px !important;
                cursor: pointer !important;
                margin: 0 auto !important;
            }
            [data-testid="baseButton-secondary"]:hover {
                background-color: #5a6268 !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4) !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # Botão Streamlit cinza com texto "Sair"
            if st.button("Sair", help="Sair do sistema", key="logout_button"):
                clear_user_cache(user_id)
                limpar_session_state()
                st.success("Logout realizado com sucesso!")
                st.rerun()

    # Verificar permissões antes de renderizar cada página
    if escolha == "Solicitar Busca":
        # Limpar estados do relatório de custos ao navegar para outras abas
        from marcas.relatorio_custos import RelatorioCustos
        relatorio_custos = RelatorioCustos(busca_manager)
        relatorio_custos.limpar_estados_relatorio()

        if not permission_manager.check_page_permission(user_id, "Solicitar Busca"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        if st.session_state.enviando_pedido:
            st.warning("Aguarde, enviando pedido...")
        else:
            form_data = form_agent.collect_data()
            if form_data:
                st.session_state.enviando_pedido = True
                ok = busca_manager.enviar_busca(form_data)
                if ok:
                    st.session_state["sucesso"] = True
                    # Limpar formulário usando a função completa do FormAgent
                    form_agent.limpar_formulario_completo()
                    st.success(
                        "✅ Pedido enviado com sucesso! O formulário foi limpo.")
                    st.rerun()
                else:
                    st.error("Erro ao enviar pedido. Tente novamente.")
                st.session_state.enviando_pedido = False

        # Mostrar mensagem de sucesso se necessário
        if st.session_state.get("sucesso"):
            st.success("✅ Pedido enviado com sucesso! O formulário foi limpo.")
            del st.session_state["sucesso"]

    elif escolha == "Minhas Buscas":
        # Limpar estados do relatório de custos ao navegar para outras abas
        from marcas.relatorio_custos import RelatorioCustos
        relatorio_custos = RelatorioCustos(busca_manager)
        relatorio_custos.limpar_estados_relatorio()

        # Verificar permissões de forma mais suave para evitar redirecionamentos
        try:
            if not permission_manager.check_page_permission(user_id, "Minhas Buscas"):
                st.warning(
                    "⚠️ Você não tem permissão para acessar esta funcionalidade.")
                st.info(
                    "Entre em contato com o administrador para solicitar acesso.")
                return
        except Exception as e:
            st.warning("⚠️ Erro ao verificar permissões.")
            st.info("Tente novamente ou entre em contato com o suporte.")
            return

        # Determinar se é admin baseado no tipo de usuário
        try:
            # Para buscas: APENAS usuários com is_admin=True na tabela perfil
            perfil = supabase_agent.get_profile(user_id)
            is_admin = perfil and perfil.get('is_admin', False)

        except Exception as e:
            st.warning("⚠️ Erro ao determinar permissões de administrador.")
            st.info("Tente novamente ou entre em contato com o suporte.")
            return

        marcas_views.minhas_buscas(busca_manager, is_admin)

    elif escolha == "Solicitar Serviço de Patente":
        if not permission_manager.check_page_permission(user_id, "Solicitar Serviço de Patente"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        patentes_views.deposito_patente(email_agent)

    elif escolha == "Minhas Patentes":
        if not permission_manager.check_page_permission(user_id, "Minhas Patentes"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        patentes_views.minhas_patentes(email_agent)

    elif escolha == "Solicitação para o Jurídico":
        if not permission_manager.check_page_permission(user_id, "Solicitação para o Jurídico"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        objeções_views.solicitar_objecao(email_agent)

    elif escolha == "Minhas Solicitações Jurídicas":
        if not permission_manager.check_page_permission(user_id, "Minhas Solicitações Jurídicas"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        objeções_views.minhas_objecoes(email_agent)

    elif escolha == "Relatório de Custos":
        if not permission_manager.check_page_permission(user_id, "Relatório de Custos"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        # Determinar se é admin baseado no tipo de usuário
        try:
            # Para relatório de custos: verificar admin em funcionário OU perfil (financeiro)
            funcionario = supabase_agent.get_funcionario_by_id(user_id)
            perfil = supabase_agent.get_profile(user_id)

            is_admin = False
            if funcionario and funcionario.get('is_admin', False):
                is_admin = True
            if perfil and perfil.get('is_admin', False):
                is_admin = True

        except Exception as e:
            st.warning("⚠️ Erro ao determinar permissões de administrador.")
            st.info("Tente novamente ou entre em contato com o suporte.")
            return

        # Importar e executar o relatório de custos
        from marcas.relatorio_custos import relatorio_custos
        relatorio_custos(busca_manager, is_admin, user_id)


if __name__ == "__main__":
    main()
