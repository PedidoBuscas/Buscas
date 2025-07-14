import streamlit as st
from datetime import date
import json
import re
from fpdf import FPDF


def apply_global_styles():
    """Aplica estilos globais da aplicação"""
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display: none !important;}
        
        [data-testid="stSidebar"] {
            background-color: #fff !important;
        }
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #e5e8ec !important;
        }
        .main .block-container {
            background-color: #e5e8ec !important;
        }
        .stMarkdown, .stText, .stSelectbox, .stTextInput, .stButton, .stExpander {
            color: #005fa3 !important;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #005fa3 !important;
        }
        .stTextInput > div > input {
            background-color: #fff !important;
            color: #005fa3 !important;
            border: 1px solid #ddd !important;
            height: 40px !important;
            min-height: 40px !important;
            max-height: 40px !important;
            font-size: 1.1rem !important;
            border-radius: 12px !important;
            padding: 8px 16px !important;
            box-sizing: border-box !important;
            line-height: 1.2 !important;
        }
        .stTextInput label {
            color: #005fa3 !important;
        }
        .stSelectbox > div > div {
            background-color: #fff !important;
            color: #005fa3 !important;
        }
        .stSelectbox label {
            color: #005fa3 !important;
        }
        .stButton > button {
            background-color: #005fa3 !important;
            color: #fff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500;
            padding: 8px 24px;
            font-size: 1.1rem !important;
            height: 40px !important;
            min-height: 40px !important;
            max-height: 40px !important;
        }
        .stButton > button:hover {
            background-color: #0074cc !important;
            color: #fff !important;
        }
        .stExpander, .stExpander > div, .stExpander .streamlit-expanderContent {
            background-color: #fff !important;
            border-radius: 12px !important;
            color: #005fa3 !important;
        }
        .stExpanderHeader {
            color: #005fa3 !important;
        }
        .stDownloadButton > button {
            background-color: #fff;
            color: #005fa3;
            border: 2px solid #005fa3;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px 24px;
            margin: 4px 0;
            transition: background 0.2s;
        }
        .stDownloadButton > button:hover {
            background-color: #005fa3;
            color: #fff;
        }
        input[disabled], .stTextInput input:disabled {
            color: #005fa3 !important;
            background-color: #fff !important;
            opacity: 1 !important;
            font-weight: bold !important;
        }
        /* Campo de login sempre branco */
        input[data-testid="stTextInput"][aria-label="Login"],
        input[data-testid="stTextInput"][aria-label="Senha"] {
            background-color: #fff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_login_screen(supabase_agent):
    """Renderiza a tela de login"""
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #fff !important;
        }
        .stTextInput > div > input {
            background-color: #fff !important;
        }
        .centered-login {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height:1vh;
        }
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
            color: #005fa3;
            text-align: center;
        }
        .login-subtitle {
            font-size: 1.1rem;
            color: #005fa3;
            margin-bottom: 24px;
            text-align: center;
        }
        .stTextInput > div > input[aria-label="Login"] {
            background: #fff !important;
        }
        .stTextInput > div > input {
            background: #f5f7fa !important;
            color: #005fa3 !important;
            border-radius: 6px;
            border: 1.5px solid #005fa3;
            width: 100% !important;
        }
        .stTextInput label {
            color: #005fa3 !important;
            font-weight: 600;
        }
        .stButton > button {
            background-color: #005fa3;
            color: #fff;
            border-radius: 6px;
            font-weight: 600;
            border: none;
            height: 44px;
            width: 100%;
            margin-top: 8px;
        }
        .stButton > button:hover {
            background-color: #0074cc;
            color: #fff;
        }
        .footer {
            text-align: center;
            color: #005fa3;
            margin-top: 32px;
            font-size: 1rem;
        }
        </style>
        <script>
        function setupEnterKey() {
            const passwordInput = document.querySelector('input[type="password"]');
            const emailInput = document.querySelector('input[type="text"]');
            
            if (passwordInput && emailInput) {
                passwordInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        if (emailInput.value && passwordInput.value) {
                            e.preventDefault();
                            const buttons = document.querySelectorAll('button');
                            for (let button of buttons) {
                                if (button.textContent.includes('Entrar') && !button.disabled) {
                                    button.click();
                                    break;
                                }
                            }
                        }
                    }
                });
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(setupEnterKey, 500);
        });
        
        if (document.readyState !== 'loading') {
            setTimeout(setupEnterKey, 500);
        }
        </script>
        <div class="centered-login">
        """,
        unsafe_allow_html=True
    )

    st.image("logo_agp.png", width=120)
    st.markdown('<div class="login-title">Bem-vindo</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Faça seu login</div>',
                unsafe_allow_html=True)

    email = st.text_input("Login", key="login_email")
    password = st.text_input("Senha", type="password", key="login_password")

    st.markdown(
        "<div style='color:#888;font-size:13px;margin-bottom:10px;'>Se você usou o preenchimento automático do navegador, clique no campo de login antes de entrar para garantir que o valor seja reconhecido corretamente.</div>",
        unsafe_allow_html=True
    )

    login_btn = st.button("Entrar")

    if login_btn:
        try:
            user, jwt_token = supabase_agent.login(email, password)
            if user:
                user_id = user.get('id') if isinstance(
                    user, dict) else getattr(user, 'id', None)
                if not user_id:
                    st.error("Não foi possível obter o ID do usuário.")
                    return

                from classificador_agent import carregar_classificador_inpi_json
                with st.spinner("Carregando Classificador INPI..."):
                    st.session_state.classificador_inpi = carregar_classificador_inpi_json()

                st.session_state.user = user
                st.session_state.jwt_token = jwt_token

                perfil = supabase_agent.get_profile(user_id)
                if perfil:
                    st.session_state.consultor_nome = perfil.get('name', '')
                    st.session_state.consultor_email = perfil.get('email', '')
                else:
                    st.session_state.consultor_nome = user.get('email', user_id) if isinstance(
                        user, dict) else getattr(user, 'email', user_id)
                    st.session_state.consultor_email = st.session_state.consultor_nome

                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Login ou senha incorretos. Por favor, tente novamente.")
        except Exception as e:
            st.error(f"Erro ao tentar logar: {e}")

    st.markdown(
        """
        <div class='footer'>© 2025 AGP Consultoria</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar():
    """Renderiza a sidebar com logo e menu"""
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center; width:100%;'>",
            unsafe_allow_html=True
        )
        st.image("logo_agp.png", width=120)
        st.markdown("</div>", unsafe_allow_html=True)
        # Exibe o nome do consultor, se estiver logado
        nome = st.session_state.get("consultor_nome", None)
        if nome:
            st.markdown(
                f"<div style='color:#005fa3;font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;'>👤 {nome}</div>",
                unsafe_allow_html=True
            )
        from streamlit_option_menu import option_menu
        menu = option_menu(
            menu_title=None,
            options=["Solicitar Busca", "Minhas Buscas"],
            icons=["search", "list-task"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fff", "width": "100%"},
                "icon": {"color": "#005fa3", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "2px 0",
                    "color": "#005fa3",
                    "background-color": "#fff",
                    "border-radius": "6px",
                    "padding": "8px 16px"
                },
                "nav-link-selected": {
                    "background-color": "#005fa3",
                    "color": "#fff",
                    "font-size": "15px",
                    "border-radius": "6px",
                    "padding": "8px 16px"
                },
            }
        )
        return menu


def limpar_formulario():
    """Limpa todos os campos do formulário"""
    campos_para_limpar = [
        "highlight_classe", "highlight_marca", "envio_sucesso", "data",
        "tipo_busca", "consultor_select", "consultor_input", "consultor",
        "observacao", "last_form_data"
    ]
    for k in campos_para_limpar:
        if k in st.session_state:
            del st.session_state[k]

    # Remove campos dinâmicos primeiro
    chaves_dinamicas = [
        k for k in list(st.session_state.keys())
        if isinstance(k, str) and (
            k.startswith("classe_") or k.startswith(
                "especificacao_") or k.startswith("marca_")
        )
    ]
    for k in chaves_dinamicas:
        del st.session_state[k]

    # Resetar marcas para estado inicial (1 marca com 1 classe vazia)
    st.session_state["marcas"] = [
        {"marca": "", "classes": [{"classe": "", "especificacao": ""}]}
    ]


def exibir_especificacoes_card(busca):
    """Exibe especificações em formato de card"""
    especs = busca.get('especificacoes', '')
    classes = busca.get('classes', '')
    if isinstance(classes, str):
        try:
            classes_list = json.loads(classes)
        except Exception:
            classes_list = [c.strip() for c in classes.split(',') if c.strip()]
    elif isinstance(classes, list):
        classes_list = [str(c).strip() for c in classes if str(c).strip()]
    else:
        classes_list = []

    if especs:
        if isinstance(especs, str):
            especs_list = [es.strip()
                           for es in re.split(r",|\n", especs) if es.strip()]
        elif isinstance(especs, list):
            especs_list = [str(es).strip() for es in especs if str(es).strip()]
        else:
            especs_list = []

        if classes_list and len(classes_list) == len(especs_list):
            for c, e in zip(classes_list, especs_list):
                st.write(f"Classe {c}: {e}")
        elif especs_list:
            st.write(f"Especificações: {'; '.join(especs_list)}")
        else:
            st.write("Especificações: Sem especificações")
    else:
        st.write("Especificações: Sem especificações")


def exibir_especificacoes_pdf(busca, pdf):
    """Exibe especificações em formato PDF"""
    especs = busca.get('especificacoes', '')
    classes = busca.get('classes', '')
    if isinstance(classes, str):
        try:
            classes_list = json.loads(classes)
        except Exception:
            classes_list = [c.strip() for c in classes.split(',') if c.strip()]
    elif isinstance(classes, list):
        classes_list = [str(c).strip() for c in classes if str(c).strip()]
    else:
        classes_list = []

    if especs:
        if isinstance(especs, str):
            especs_list = [es.strip()
                           for es in re.split(r",|\n", especs) if es.strip()]
        elif isinstance(especs, list):
            especs_list = [str(es).strip() for es in especs if str(es).strip()]
        else:
            especs_list = []

        if classes_list and len(classes_list) == len(especs_list):
            for c, e in zip(classes_list, especs_list):
                pdf.multi_cell(0, 10, f"Classe {c}: {e}")
        elif especs_list:
            for espec in especs_list:
                pdf.multi_cell(0, 10, f"- {espec}")
        else:
            pdf.multi_cell(0, 10, "Especificações: Sem especificações")
    else:
        pdf.multi_cell(0, 10, "Especificações: Sem especificações")
