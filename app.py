# app.py
import streamlit as st
from marcas import views as marcas_views
from patentes import views as patentes_views
from marcas.busca_manager import BuscaManager, get_user_attr
from form_agent import FormAgent
from email_agent import EmailAgent
from supabase_agent import SupabaseAgent
from ui_components import apply_global_styles, render_login_screen, render_sidebar, limpar_formulario, apply_sidebar_styles
from config import carregar_configuracoes, configurar_logging


def main():
    config = carregar_configuracoes()
    configurar_logging()
    apply_global_styles()

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

    if "user" not in st.session_state:
        render_login_screen(supabase_agent)
        return
    if "enviando_pedido" not in st.session_state:
        st.session_state.enviando_pedido = False

    # Menu lateral único com todas as opções
    opcoes_menu = [
        'Solicitar Busca',
        'Minhas Buscas',
        'Solicitar Serviço de Patente',
        'Minhas Patentes'
    ]
    icones_menu = [
        'search',            # Solicitar Busca
        'list-task',         # Minhas Buscas
        'file-earmark-arrow-up',  # Solicitar Serviço de Patente
        'file-earmark-text'  # Minhas Patentes
    ]
    with st.sidebar:
        # Adicionar logo e nome do consultor
        st.image("Logo_sigepi.png", width=120)
        nome = st.session_state.get("consultor_nome", None)
        if nome:
            st.markdown(
                f"<div style='color:#fff;font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;'>"
                f"<span style='font-size:1.3em;margin-right:7px;vertical-align:middle;'>"
                f"<svg width='22' height='22' viewBox='0 0 24 24' fill='white' xmlns='http://www.w3.org/2000/svg' style='display:inline-block;vertical-align:middle;'><path d='M12 12c2.7 0 8 1.34 8 4v2H4v-2c0-2.66 5.3-4 8-4zm0-2a4 4 0 100-8 4 4 0 000 8z'/></svg>"
                f"</span>{nome}</div>",
                unsafe_allow_html=True
            )
        from streamlit_option_menu import option_menu
        escolha = option_menu(
            menu_title=None,
            options=opcoes_menu,
            icons=icones_menu,
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

    # Verificar se o usuário é admin
    is_admin = get_user_attr(st.session_state.user, 'is_admin', False)

    # Renderizar a página selecionada
    if escolha == "Solicitar Busca":
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
        marcas_views.minhas_buscas(busca_manager, is_admin)
    elif escolha == "Solicitar Serviço de Patente":
        patentes_views.deposito_patente(email_agent)
    elif escolha == "Minhas Patentes":
        patentes_views.minhas_patentes(email_agent)


if __name__ == "__main__":
    main()
