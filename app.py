# app.py
import streamlit as st
from marcas import views as marcas_views
from patentes import views as patentes_views
from objeções import views as objeções_views
from marcas.busca_manager import BuscaManager, get_user_attr
from form_agent import FormAgent
from email_agent import EmailAgent
from supabase_agent import SupabaseAgent
from ui_components import apply_global_styles, render_login_screen, render_sidebar, limpar_formulario, apply_sidebar_styles
from config import carregar_configuracoes, configurar_logging
from permission_manager import CargoPermissionManager


def get_user_id(user):
    """Extrai o ID do usuário de forma segura"""
    if isinstance(user, dict):
        return user.get('id')
    return getattr(user, 'id', None)


@st.cache_resource
def get_supabase_agent():
    """Cache do SupabaseAgent para evitar recriação"""
    return SupabaseAgent()


@st.cache_resource
def get_email_agent(_config):
    """Cache do EmailAgent para evitar recriação"""
    return EmailAgent(
        _config["smtp_host"],
        _config["smtp_port"],
        _config["smtp_user"],
        _config["smtp_pass"],
        _config["destinatarios"],
        _config["destinatario_juridico"],
        _config["destinatario_juridico_um"]
    )


@st.cache_resource
def get_busca_manager(_supabase_agent, _email_agent):
    """Cache do BuscaManager para evitar recriação"""
    return BuscaManager(_supabase_agent, _email_agent)


@st.cache_resource
def get_form_agent():
    """Cache do FormAgent para evitar recriação"""
    return FormAgent()


@st.cache_resource
def get_permission_manager(_supabase_agent):
    """Cache do PermissionManager para evitar recriação"""
    return CargoPermissionManager(_supabase_agent)


def main():
    config = carregar_configuracoes()
    configurar_logging()
    apply_global_styles()

    # Usar cache para otimizar criação de agentes
    supabase_agent = get_supabase_agent()
    email_agent = get_email_agent(config)
    busca_manager = get_busca_manager(supabase_agent, email_agent)
    form_agent = get_form_agent()
    permission_manager = get_permission_manager(supabase_agent)

    # Inicializar supabase_agent e email_agent no session_state
    if "supabase_agent" not in st.session_state:
        st.session_state.supabase_agent = supabase_agent

    if "email_agent" not in st.session_state:
        st.session_state.email_agent = email_agent

    # Garantir que email_agent sempre esteja disponível
    st.session_state.email_agent = email_agent

    # Verificação de segurança para email_agent
    if not hasattr(st.session_state, 'email_agent') or st.session_state.email_agent is None:
        st.session_state.email_agent = email_agent

    # Garantir que email_agent esteja sempre disponível
    try:
        if st.session_state.email_agent is None:
            st.session_state.email_agent = email_agent
    except AttributeError:
        st.session_state.email_agent = email_agent

    # Verificação adicional para garantir que email_agent esteja disponível
    if "email_agent" not in st.session_state:
        st.session_state.email_agent = email_agent

    # Garantir que email_agent esteja sempre disponível no session_state
    st.session_state.email_agent = email_agent

    if "user" not in st.session_state:
        render_login_screen(supabase_agent)
        return
    if "enviando_pedido" not in st.session_state:
        st.session_state.enviando_pedido = False

    # Obter informações do usuário
    user_id = get_user_id(st.session_state.user)

    # Cache de permissões para otimizar consultas repetidas
    @st.cache_data(ttl=300)  # 5 minutos
    def get_user_permissions_cached(_user_id, _permission_manager):
        return {
            'user_info': _permission_manager.get_user_display_info(_user_id),
            'cargo_info': _permission_manager.get_user_cargo_info(_user_id),
            'available_menu': _permission_manager.get_available_menu_items(_user_id),
            'menu_icons': _permission_manager.get_icons_for_menu(
                _permission_manager.get_available_menu_items(_user_id)
            )
        }

    # Usar cache para otimizar consultas de permissões
    permissions_data = get_user_permissions_cached(user_id, permission_manager)
    user_info = permissions_data['user_info']
    cargo_info = permissions_data['cargo_info']
    available_menu_items = permissions_data['available_menu']
    menu_icons = permissions_data['menu_icons']

    with st.sidebar:
        # Adicionar logo e informações do usuário
        st.image("Logo_sigepi.png", width=120)

        # Exibir informações do usuário com cargo
        if user_info['nome']:
            st.markdown(
                f"<div style='color:#fff;font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;'>"
                f"<span style='font-size:1.3em;margin-right:7px;vertical-align:middle;'>"
                f"<svg width='22' height='22' viewBox='0 0 24 24' fill='white' xmlns='http://www.w3.org/2000/svg' style='display:inline-block;vertical-align:middle;'><path d='M12 12c2.7 0 8 1.34 8 4v2H4v-2c0-2.66 5.3-4 8-4zm0-2a4 4 0 100-8 4 4 0 000 8z'/></svg>"
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
                "container": {"padding": "0!important", "background-color": "#35434f", "width": "100%"},
                "icon": {"color": "#fff", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "2px 0",
                    "color": "#fff",
                    "background-color": "#35434f",
                    "border-radius": "6px",
                    "padding": "8px 16px"
                },
                "nav-link-selected": {
                    "background-color": "#1caf9a",
                    "color": "#fff",
                    "font-size": "15px",
                    "border-radius": "6px",
                    "padding": "8px 16px"
                },
            }
        )

    # Verificar permissões antes de renderizar cada página
    if escolha == "Solicitar Busca":
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
                    limpar_formulario()
                    st.rerun()
                else:
                    st.error("Erro ao enviar pedido. Tente novamente.")
                st.session_state.enviando_pedido = False
        if st.session_state.get("sucesso"):
            st.success("Pedido enviado com sucesso! O formulário foi limpo.")
            del st.session_state["sucesso"]

    elif escolha == "Minhas Buscas":
        if not permission_manager.check_page_permission(user_id, "Minhas Buscas"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        # Determinar se é admin baseado no tipo de usuário
        cargo_info = permission_manager.get_user_cargo_info(user_id)
        # Admin de busca: qualquer usuário com is_admin = True
        is_admin = cargo_info['is_admin'] is True
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

    elif escolha == "Solicitar Objeção de Marca":
        if not permission_manager.check_page_permission(user_id, "Solicitar Objeção de Marca"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        objeções_views.solicitar_objecao(email_agent)

    elif escolha == "Minhas Objeções":
        if not permission_manager.check_page_permission(user_id, "Minhas Objeções"):
            st.error("Você não tem permissão para acessar esta funcionalidade.")
            return

        objeções_views.minhas_objecoes(email_agent)


if __name__ == "__main__":
    main()
