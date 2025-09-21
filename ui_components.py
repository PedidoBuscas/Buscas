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
            background-color: #ffffff !important;
        }
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #e6e8ec !important;
        }
        .main .block-container {
            background-color: #e6e8ec !important;
        }
        .stMarkdown, .stText, .stSelectbox, .stTextInput, .stButton, .stExpander {
            color: #35434f !important;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #35434f !important;
        }
        .stTextInput > div > input {
            background-color: #fff !important;
            color: #35434f !important;
            border: 1px solid #434f65 !important;
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
            color: #35434f !important;
        }
        .stSelectbox > div > div {
            background-color: #fff !important;
            color: #35434f !important;
        }
        .stSelectbox label {
            color: #35434f !important;
        }
        .stButton > button {
            background-color: #434f65 !important;
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
            background-color: #2a3441 !important;
            color: #fff !important;
        }
        .stExpander, .stExpander > div, .stExpander .streamlit-expanderContent {
            background-color: #fff !important;
            border-radius: 12px !important;
            color: #35434f !important;
        }
        .stExpanderHeader {
            color: #35434f !important;
        }
        .stDownloadButton > button {
            background-color: #fff;
            color: #434f65;
            border: 2px solid #434f65;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px 24px;
            margin: 4px 0;
            transition: background 0.2s;
        }
        .stDownloadButton > button:hover {
            background-color: #434f65;
            color: #fff;
        }
        input[disabled], .stTextInput input:disabled {
            color: #35434f !important;
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


def apply_sidebar_styles():
    import streamlit as st
    st.markdown("""
    <style>
    .sidebar-module-group {
        background: #2a3a48;
        border-radius: 16px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        padding: 10px 0 6px 0;
        border: 2px solid #1caf9a;
        /* Removido outline, border extra ou height/min-height que criava círculo */
    }
    .sidebar-module-btn {
        width: 92% !important;
        margin-left: 4%;
        min-height: 38px !important;
        font-size: 1.08rem !important;
        font-weight: 600;
        margin-bottom: 8px;
        background-color: #1caf9a;
        color: #fff !important;
        border-radius: 10px;
        border: none;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        transition: background 0.2s;
    }
    .sidebar-module-btn.inactive {
        background-color: #35434f;
        color: #fff !important;
        border: 2px solid #1caf9a;
        opacity: 0.85;
    }
    .sidebar-module-btn .emoji {
        margin-right: 10px;
        font-size: 1.3em;
    }
    .sidebar-opcao-btn {
        width: 86% !important;
        margin-left: 7%;
        min-height: 36px !important;
        font-size: 1.02rem !important;
        font-weight: 500;
        margin-bottom: 6px;
        background-color: #1caf9a;
        color: #fff !important;
        border-radius: 8px;
        border: none;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        transition: background 0.2s;
    }
    .sidebar-opcao-btn.inactive {
        background-color: #35434f;
        color: #fff !important;
        border: 2px solid #1caf9a;
        opacity: 0.85;
    }
    .sidebar-radio label, .sidebar-radio span {
        color: #fff !important;
        font-size: 1.1rem;
    }
    .sidebar-radio .stRadio > div { color: #fff !important; }
    .stButton > button {
        width: 100% !important;
        min-height: 38px !important;
        font-size: 1.08rem !important;
        font-weight: 600;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)


def render_login_screen(supabase_agent):
    """Renderiza a tela de login"""
    st.markdown(
        """
        <style>
        /* Força a página principal a alinhar no topo */
        .main {
            display: block !important;
            padding-top: 40px;
        }

        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #ffffff !important;
        }
        .stTextInput > div > input {
            background-color: #fff !important;
        }
        .centered-login {
            margin-top: 0px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
            color: #35434f;
            text-align: center;
        }
        .login-subtitle {
            font-size: 1.1rem;
            color: #35434f;
            margin-bottom: 24px;
            text-align: center;
        }
        .stTextInput > div > input[aria-label="Login"] {
            background: #fff !important;
        }
        .stTextInput > div > input {
            background: #f5f7fa !important;
            color: #35434f !important;
            border-radius: 6px;
            border: 1.5px solid #434f65;
            width: 100% !important;
        }
        .stTextInput label {
            color: #35434f !important;
            font-weight: 600;
        }
        .stButton > button {
            background-color: #434f65;
            color: #fff;
            border-radius: 6px;
            font-weight: 600;
            border: none;
            height: 44px;
            width: 100%;
            margin-top: 8px;
        }
        .stButton > button:hover {
            background-color: #2a3441;
            color: #fff;
        }
        .footer {
            text-align: center;
            color: #666;
            margin-top: 5px;
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

    st.image("a2nunes.jpeg", width=120)
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
        # Verificar se já está tentando fazer login para evitar múltiplas tentativas
        if 'login_in_progress' in st.session_state and st.session_state.login_in_progress:
            st.warning("Login em andamento. Aguarde...")
            return

        # Marcar que o login está em andamento
        st.session_state.login_in_progress = True

        # Verificar se deve mostrar erro (isso deve vir ANTES de qualquer CSS)
        if 'show_login_error' in st.session_state and st.session_state.show_login_error:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4);
                animation: slideInUp 0.6s ease-out;
                border: 3px solid #d32f2f;
                min-width: 300px;
                position: relative;
                z-index: 1001;
            ">
                <div style="font-size: 28px; margin-bottom: 12px;">❌</div>
                <div style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">Falha no Login</div>
                <div style="font-size: 16px; opacity: 0.95;">Por favor, verifique a senha ou o login e tente novamente.</div>
            </div>
            <style>
            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(-40px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            </style>
            """, unsafe_allow_html=True)
            # Limpar o flag de erro
            del st.session_state.show_login_error
            # Limpar flag de login em andamento
            if 'login_in_progress' in st.session_state:
                del st.session_state.login_in_progress
            return

        # NOVA ABORDAGEM: Fazer login primeiro, depois aplicar CSS se necessário
        try:
            user, jwt_token = supabase_agent.login(email, password)

            # Verificar se o login foi bem-sucedido
            login_successful = user is not None and jwt_token is not None

            if login_successful:
                # Aplicar CSS de loading APENAS se o login foi bem-sucedido
                st.markdown("""
                <style>
                /* Ocultar todos os elementos da tela de login */
                .centered-login, .login-title, .login-subtitle,
                .stTextInput, .stButton, .footer {
                    display: none !important;
                }
                </style>
                """, unsafe_allow_html=True)

                # Loading personalizado mais bonito
                with st.spinner(""):
                    st.markdown("""
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 40px;
                        text-align: center;
                        background: rgba(255, 255, 255, 0.95);
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                        margin: 20px;
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        z-index: 1000;
                    ">
                        <div style="
                            width: 60px;
                            height: 60px;
                            border: 4px solid rgba(28, 175, 154, 0.2);
                            border-radius: 50%;
                            border-top-color: #1caf9a;
                            animation: spin 1s linear infinite;
                            margin-bottom: 20px;
                        "></div>
                        <div style="
                            font-size: 18px;
                            font-weight: 600;
                            color: #35434f;
                            margin-bottom: 10px;
                        ">Entrando no sistema...</div>
                        <div style="
                            font-size: 14px;
                            color: #666;
                        ">Aguarde um momento</div>
                    </div>
                    <style>
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                    </style>
                    """, unsafe_allow_html=True)

                user_id = user.get('id') if isinstance(
                    user, dict) else getattr(user, 'id', None)
                if not user_id:
                    st.error("Não foi possível obter o ID do usuário.")
                    # Limpar flag de login em andamento
                    if 'login_in_progress' in st.session_state:
                        del st.session_state.login_in_progress
                    return

                # Limpar cache de dados do usuário anterior
                st.cache_data.clear()

                # Loading para carregamento do classificador
                with st.spinner(""):
                    st.markdown("""
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 30px;
                        text-align: center;
                        background: rgba(255, 255, 255, 0.95);
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                        margin: 20px;
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        z-index: 1000;
                    ">
                        <div style="
                            width: 50px;
                            height: 50px;
                            border: 3px solid rgba(76, 175, 80, 0.2);
                            border-radius: 50%;
                            border-top-color: #4CAF50;
                            animation: spin 1s linear infinite;
                            margin-bottom: 15px;
                        "></div>
                        <div style="
                            font-size: 16px;
                            font-weight: 600;
                            color: #35434f;
                            margin-bottom: 8px;
                        ">Preparando sistema...</div>
                        <div style="
                            font-size: 12px;
                            color: #666;
                        ">Carregando recursos necessários</div>
                    </div>
                    """, unsafe_allow_html=True)

                perfil = supabase_agent.get_profile(user_id)
                if perfil:
                    st.session_state.user = perfil  # Sempre um dict!
                    st.session_state.consultor_nome = perfil.get(
                        'name', '')
                    st.session_state.consultor_email = perfil.get(
                        'email', '')
                else:
                    # Fallback: cria um dict mínimo
                    st.session_state.user = {
                        "id": user_id,
                        "email": user.get('email', user_id) if isinstance(user, dict) else getattr(user, 'email', user_id),
                        "name": user.get('name', '') if isinstance(user, dict) else getattr(user, 'name', ''),
                        "is_admin": False
                    }
                    st.session_state.consultor_nome = st.session_state.user["email"]
                    st.session_state.consultor_email = st.session_state.user["email"]

                st.session_state.jwt_token = jwt_token

                # Mensagem de sucesso melhorada
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 15px;
                    margin: 20px 0;
                    text-align: center;
                    box-shadow: 0 8px 25px rgba(76, 175, 80, 0.4);
                    animation: slideInUp 0.8s ease-out;
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    z-index: 1000;
                    min-width: 300px;
                    border: 3px solid #45a049;
                ">
                    <div style="font-size: 32px; margin-bottom: 15px;">✅</div>
                    <div style="font-size: 22px; font-weight: 700; margin-bottom: 10px;">Login Realizado com Sucesso!</div>
                    <div style="font-size: 16px; opacity: 0.95; margin-bottom: 15px;">Bem-vindo ao sistema</div>
                    <div style="
                        width: 40px;
                        height: 4px;
                        background: rgba(255, 255, 255, 0.3);
                        border-radius: 2px;
                        margin: 0 auto;
                        animation: pulse 2s infinite;
                    "></div>
                </div>
                <style>
                @keyframes slideInUp {
                    from {
                        opacity: 0;
                        transform: translate(-50%, -60px);
                    }
                    to {
                        opacity: 1;
                        transform: translate(-50%, -50%);
                    }
                }
                @keyframes pulse {
                    0%, 100% { opacity: 0.3; }
                    50% { opacity: 1; }
                }
                </style>
                """, unsafe_allow_html=True)

                # Delay maior para mostrar a mensagem de sucesso
                import time
                time.sleep(3.0)  # Aumentado de 1.5 para 3.0 segundos
                # Limpar flag de login em andamento
                if 'login_in_progress' in st.session_state:
                    del st.session_state.login_in_progress
                st.rerun()
            else:
                # ERRO: Mostrar erro imediatamente sem aplicar CSS de loading
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 15px;
                    margin: 20px 0;
                    text-align: center;
                    box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4);
                    animation: slideInUp 0.6s ease-out;
                    border: 3px solid #d32f2f;
                    min-width: 300px;
                    position: relative;
                    z-index: 1001;
                ">
                    <div style="font-size: 28px; margin-bottom: 12px;">❌</div>
                    <div style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">Falha no Login</div>
                    <div style="font-size: 16px; opacity: 0.95;">Por favor, verifique a senha ou o login e tente novamente.</div>
                </div>
                <style>
                @keyframes slideInUp {
                    from {
                        opacity: 0;
                        transform: translateY(-40px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                </style>
                """, unsafe_allow_html=True)

                # Limpar campos de login em caso de erro
                if 'login_email' in st.session_state:
                    del st.session_state.login_email
                if 'login_password' in st.session_state:
                    del st.session_state.login_password

                # Limpar flag de login em andamento
                if 'login_in_progress' in st.session_state:
                    del st.session_state.login_in_progress

                return  # Retornar sem fazer rerun
        except Exception as e:
            # ERRO DE SISTEMA: Mostrar erro imediatamente sem aplicar CSS de loading
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 6px 20px rgba(255, 152, 0, 0.4);
                animation: slideInUp 0.6s ease-out;
                border: 3px solid #f57c00;
                min-width: 300px;
                position: relative;
                z-index: 1001;
            ">
                <div style="font-size: 28px; margin-bottom: 12px;">⚠️</div>
                <div style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">Erro no Sistema</div>
                <div style="font-size: 16px; opacity: 0.95;">{str(e)}</div>
            </div>
            <style>
            @keyframes slideInUp {{
                from {{
                    opacity: 0;
                    transform: translateY(-40px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            </style>
            """, unsafe_allow_html=True)

            # Limpar campos de login em caso de erro
            if 'login_email' in st.session_state:
                del st.session_state.login_email
            if 'login_password' in st.session_state:
                del st.session_state.login_password

            # Limpar flag de login em andamento
            if 'login_in_progress' in st.session_state:
                del st.session_state.login_in_progress

            return  # Retornar sem fazer rerun

    st.markdown(
        """
        <div class='footer'>© 2025 AGP Consultoria</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar(modulos=None):
    """
    Renderiza o conteúdo da sidebar com múltiplos módulos, cada um como botão estilizado. Só mostra o menu de opções do módulo ativo.
    Esta função NÃO deve abrir o bloco 'with st.sidebar:'.
    modulos: lista de dicts, cada um com 'nome', 'icone', 'emoji', 'opcoes' (lista de dicts com 'nome' e 'icone')
    Retorna (modulo_selecionado, opcao_selecionada)
    """
    from streamlit_option_menu import option_menu
    st.markdown(
        """
        <style>
        .sidebar-module-btn {
            width: 100%;
            min-height: 40px;
            font-size: 1.08rem;
            font-weight: 600;
            margin-bottom: 8px;
            background-color: #35434f;
            color: #fff !important;
            border-radius: 10px;
            border: 2px solid #1caf9a;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            transition: background 0.2s;
            padding-left: 16px;
        }
        .sidebar-module-btn.active {
            background-color: #1caf9a !important;
            color: #fff !important;
            border: 2px solid #fff;
        }
        .sidebar-module-btn .emoji {
            margin-right: 10px;
            font-size: 1.3em;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='text-align:center; width:100%;'>",
        unsafe_allow_html=True
    )
    st.image("a2nunes.jpeg", width=120)
    st.markdown("</div>", unsafe_allow_html=True)
    nome = st.session_state.get("consultor_nome", None)
    if nome:
        st.markdown(
            f"""<div style='color:#fff;font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;'>
<svg width='20' height='20' viewBox='0 0 24 24' fill='white' xmlns='http://www.w3.org/2000/svg' style='margin-right:6px;'><path d='M12 12c2.7 0 8 1.34 8 4v2H4v-2c0-2.66 5.3-4 8-4zm0-2a4 4 0 100-8 4 4 0 000 8z'/></svg>
{nome}
</div>""",
            unsafe_allow_html=True
        )
    if not modulos:
        modulos = [
            {
                'nome': 'Marcas',
                'icone': 'tag',
                'emoji': '🏷️',
                'opcoes': [
                    {'nome': 'Solicitar Busca', 'icone': 'search'},
                    {'nome': 'Minhas Buscas', 'icone': 'list-task'}
                ]
            }
        ]
    # Controle de módulo ativo
    if 'modulo_ativo' not in st.session_state or st.session_state['modulo_ativo'] not in [m['nome'] for m in modulos]:
        st.session_state['modulo_ativo'] = modulos[0]['nome']
    modulo_ativo = st.session_state['modulo_ativo']
    modulo_selecionado = modulo_ativo
    # Renderizar botões de módulos
    for modulo in modulos:
        is_active = modulo['nome'] == modulo_ativo
        btn_label = f"{modulo.get('emoji', '')} {modulo['nome']}"
        if st.button(btn_label, key=f"btn_modulo_{modulo['nome']}"):
            st.session_state['modulo_ativo'] = modulo['nome']
            st.rerun()
    # Só mostrar opções do módulo ativo
    modulo = next(
        m for m in modulos if m['nome'] == st.session_state['modulo_ativo'])
    st.markdown(
        f"<div style='margin:18px 0 0 0;'><b style='color:#1caf9a;font-size:1.08rem;'><span style='margin-right:7px;'>{modulo.get('emoji', '')}</span>{modulo['nome']}</b></div>", unsafe_allow_html=True)
    opcoes = [op['nome'] for op in modulo['opcoes']]
    icones = [op['icone'] for op in modulo['opcoes']]
    escolha = option_menu(
        menu_title=None,
        options=opcoes,
        icons=icones,
        key=f"menu_{modulo['nome']}",
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
    return modulo['nome'], escolha


def limpar_formulario():
    """Limpa todos os campos do formulário"""
    # Resetar marcas para estado inicial (1 marca com 5 classes vazias)
    st.session_state["marcas"] = [
        {
            "marca": "",
            "classes": [
                {"classe": "", "especificacao": ""},
                {"classe": "", "especificacao": ""},
                {"classe": "", "especificacao": ""},
                {"classe": "", "especificacao": ""},
                {"classe": "", "especificacao": ""}
            ]
        }
    ]

    # Limpar campos específicos do formulário
    campos_para_limpar = [
        "enviando_pedido",
        "cpf_cnpj_cliente",
        "nome_cliente",
        "observacao",
        "data",  # Limpar data também
        "envio_sucesso",  # Limpar flag de sucesso
        "last_form_data"  # Limpar dados do último formulário
    ]

    for k in campos_para_limpar:
        if k in st.session_state:
            del st.session_state[k]

    # Remove campos dinâmicos do formulário
    chaves_dinamicas = [
        k for k in list(st.session_state.keys())
        if isinstance(k, str) and (
            k.startswith("classe_") or k.startswith("especificacao_") or
            k.startswith("marca_") or k.startswith("data_") or
            k.startswith("observacao_") or k.startswith("cpf_cnpj_cliente_") or
            k.startswith("nome_cliente_")
        )
    ]
    for k in chaves_dinamicas:
        del st.session_state[k]

    # Forçar rerun para atualizar a interface
    st.rerun()


def exibir_especificacoes_card(busca):
    """Exibe especificações em formato de card usando componentes nativos do Streamlit - OTIMIZADO"""
    especs = busca.get('especificacoes', '')
    classes = busca.get('classes', '')

    # Garantir que classes_list seja sempre uma lista
    if isinstance(classes, str):
        try:
            classes_list = json.loads(classes)
            if isinstance(classes_list, int):
                classes_list = [str(classes_list)]
            elif not isinstance(classes_list, list):
                classes_list = [str(classes_list)]
        except Exception:
            classes_list = [c.strip() for c in classes.split(',') if c.strip()]
    elif isinstance(classes, list):
        classes_list = [str(c).strip() for c in classes if str(c).strip()]
    elif isinstance(classes, int):
        classes_list = [str(classes)]
    else:
        classes_list = []

    if especs:
        if isinstance(especs, str):
            # Dividir por ponto e vírgula primeiro, depois por vírgula
            especs_list = []
            for es in re.split(r";", especs):
                if es.strip():
                    especs_list.append(es.strip())
        elif isinstance(especs, list):
            especs_list = [str(es).strip() for es in especs if str(es).strip()]
        else:
            especs_list = []

        if especs_list:
            # Criar título do card
            if classes_list and len(classes_list) == 1:
                card_title = f"📋 Classe {classes_list[0]} - Produtos/Serviços ({len(especs_list)} itens)"
            else:
                card_title = f"📋 Produtos/Serviços Encontrados ({len(especs_list)} itens)"

            # Usar expander para criar o card (sempre aberto para facilitar seleção)
            with st.expander(card_title, expanded=True):
                # Lista com checkboxes usando componentes nativos do Streamlit
                for i, espec in enumerate(especs_list):
                    # Remover o número da classe do início da especificação
                    espec_limpa = espec
                    if classes_list and len(classes_list) > 0:
                        classe_num = classes_list[0]
                        if espec.startswith(f"{classe_num} - "):
                            espec_limpa = espec[len(f"{classe_num} - "):]
                        elif espec.startswith(f"{classe_num} "):
                            espec_limpa = espec[len(f"{classe_num} "):]

                    # Criar checkbox nativo do Streamlit com chave única
                    checkbox_key = f"checkbox_{st.session_state.busca_session_key}_{classes_list[0] if classes_list else 'geral'}_{i}"

                    # Verificar se esta especificação já está selecionada
                    is_selected = any(
                        sel.get('especificacao') == espec and sel.get(
                            'classe') == (classes_list[0] if classes_list else '')
                        for sel in st.session_state.get('especificacoes_selecionadas', [])
                    )

                    # Checkbox do Streamlit com texto inline
                    checkbox_clicked = st.checkbox(
                        espec_limpa, value=is_selected, key=checkbox_key)

                    # Atualizar estado apenas se houve mudança
                    if checkbox_clicked != is_selected:
                        if checkbox_clicked:
                            # Adicionar à lista de selecionados
                            item = {
                                'classe': classes_list[0] if classes_list else '',
                                'especificacao': espec
                            }
                            if 'especificacoes_selecionadas' not in st.session_state:
                                st.session_state.especificacoes_selecionadas = []

                            # Verificar se já não existe
                            if not any(
                                sel.get('especificacao') == espec and sel.get(
                                    'classe') == item['classe']
                                    for sel in st.session_state.especificacoes_selecionadas
                            ):
                                st.session_state.especificacoes_selecionadas.append(
                                    item)
                        else:
                            # Remover da lista de selecionados
                            if 'especificacoes_selecionadas' in st.session_state:
                                st.session_state.especificacoes_selecionadas = [
                                    sel for sel in st.session_state.especificacoes_selecionadas
                                    if not (sel.get('especificacao') == espec and sel.get('classe') == (classes_list[0] if classes_list else ''))
                                ]

                # Mostrar contador de seleções
                if st.session_state.get('especificacoes_selecionadas', []):
                    st.success(
                        f"✅ {len(st.session_state.especificacoes_selecionadas)} especificação(ões) selecionada(s)")
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


def limpar_session_state():
    """Limpa o session_state e cache para logout"""
    # Limpar cache
    st.cache_data.clear()

    # Limpar cache específico do usuário se existir
    current_user_id = st.session_state.get('current_user_id', None)
    if current_user_id:
        cache_key = f"user_permissions_{current_user_id}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]

    # Limpar session_state
    keys_to_clear = [
        'user', 'jwt_token', 'consultor_nome', 'consultor_email',
        'enviando_pedido', 'sucesso',
        'form_nonce', 'marcas', 'supabase_agent', 'email_agent',
        'current_user_id'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Aplicar estilos CSS globais
    st.markdown(
        """
        <style>
        .stButton > button {
            background-color: #434f65 !important;
            color: #fff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600;
            font-size: 1.1rem !important;
            height: 40px !important;
            min-height: 40px !important;
            max-height: 40px !important;
            margin-bottom: 8px;
            width: 100% !important;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding-left: 16px;
        }
        .stButton > button:hover {
            background-color: #2a3441 !important;
            color: #fff !important;
        }
        /* Botão do módulo ativo (primeiro botão após login) */
        .stButton > button:focus:not(:active),
        .stButton > button:active {
            background-color: #2a3441 !important;
            color: #fff !important;
            border: 2px solid #fff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_classificador_inpi():
    """Renderiza o classificador do INPI com campo de busca unificado - FORMULÁRIO SEPARADO"""
    # Carregar dados do classificador com cache otimizado
    try:
        from classificador_agent import carregar_classificador_inpi_json
        especificacoes = carregar_classificador_inpi_json()
        if not especificacoes:
            st.error("❌ Não foi possível carregar o classificador INPI")
            return
    except Exception as e:
        st.error(f"❌ Erro ao carregar classificador: {e}")
        return

    # Inicializar especificações selecionadas se não existir
    if "especificacoes_selecionadas" not in st.session_state:
        st.session_state.especificacoes_selecionadas = []

    # Criar uma chave única para esta sessão de busca
    if "busca_session_key" not in st.session_state:
        import time
        st.session_state.busca_session_key = f"busca_{int(time.time())}"

    # Classificador sem formulário para permitir comunicação com o formulário principal

    # Layout em colunas para campo de busca e botão
    col_busca, col_botao = st.columns([3, 1])

    with col_busca:
        termo_busca = st.text_input(
            "Digite uma palavra, produto ou número da classe:",
            placeholder="Ex: computador, software, consultoria, 9, 35, 42...",
            key="termo_busca_unificado"
        )

    with col_botao:
        # Espaçamento para alinhar com o campo
        st.markdown("<br>", unsafe_allow_html=True)
        buscar_btn = st.button("🔍 Buscar", type="primary",
                               key="btn_buscar_classificador")

    # Processar busca quando o botão for clicado
    if buscar_btn and termo_busca and len(termo_busca) >= 1:
        from classificador_agent import buscar_no_classificador

        # Busca por palavra/produto com cache
        resultados = buscar_no_classificador(termo_busca, especificacoes)

        # Salvar resultados na sessão para manter as seleções
        st.session_state.resultados_busca_atual = resultados
        st.session_state.termo_busca_atual = termo_busca

        if resultados:
            st.markdown(
                f"**📋 Produto/Serviço '{termo_busca}' encontrado ({len(resultados)} itens):**")

            # Agrupar resultados por classe
            classes_agrupadas = {}
            for r in resultados:
                classe = r['classe']
                especificacao = r['especificacao']

                if classe not in classes_agrupadas:
                    classes_agrupadas[classe] = []
                classes_agrupadas[classe].append(especificacao)

            # Exibir um card para cada classe (ordenado numericamente)
            for classe, especificacoes in sorted(classes_agrupadas.items(), key=lambda x: int(x[0])):
                busca_data = {
                    'classes': [classe],
                    'especificacoes': especificacoes
                }
                exibir_especificacoes_card(busca_data)

            # Botão para adicionar especificações selecionadas (sempre visível após busca)
            st.markdown("---")  # Separador visual
            if st.button("📋 Adicionar Especificações Selecionadas", type="primary", key="btn_adicionar_especificacoes"):
                if st.session_state.get('especificacoes_selecionadas', []):
                    # Inicializar lista se não existir
                    if "classificador_selecionado" not in st.session_state:
                        st.session_state.classificador_selecionado = []

                    # Adicionar apenas as especificações selecionadas
                    itens_adicionados = 0
                    for item in st.session_state.especificacoes_selecionadas:
                        # Verificar se já não existe na lista
                        ja_existe = any(
                            sel.get('especificacao') == item.get('especificacao') and
                            sel.get('classe') == item.get('classe')
                            for sel in st.session_state.classificador_selecionado
                        )

                        if not ja_existe:
                            st.session_state.classificador_selecionado.append(
                                item)
                            itens_adicionados += 1

                    # Marcar que as especificações devem ser aplicadas ao formulário principal
                    st.session_state.aplicar_especificacoes = True
                    st.session_state.especificacoes_para_aplicar = st.session_state.especificacoes_selecionadas.copy()

                    # Limpar seleções temporárias
                    st.session_state.especificacoes_selecionadas = []

                    st.success(
                        f"✅ {itens_adicionados} especificação(ões) adicionada(s) e aplicada(s) ao formulário!")
                    st.rerun()
                else:
                    st.warning(
                        "⚠️ Nenhuma especificação foi selecionada. Selecione pelo menos uma especificação antes de adicionar.")

    # Mostrar resultados salvos se existirem (para manter seleções após rerun)
    elif "resultados_busca_atual" in st.session_state and st.session_state.resultados_busca_atual:
        resultados = st.session_state.resultados_busca_atual
        termo_busca = st.session_state.termo_busca_atual

        st.markdown(
            f"**📋 Produto/Serviço '{termo_busca}' encontrado ({len(resultados)} itens):**")

        # Agrupar resultados por classe
        classes_agrupadas = {}
        for r in resultados:
            classe = r['classe']
            especificacao = r['especificacao']

            if classe not in classes_agrupadas:
                classes_agrupadas[classe] = []
            classes_agrupadas[classe].append(especificacao)

        # Exibir um card para cada classe (ordenado numericamente)
        for classe, especificacoes in sorted(classes_agrupadas.items(), key=lambda x: int(x[0])):
            busca_data = {
                'classes': [classe],
                'especificacoes': especificacoes
            }
            exibir_especificacoes_card(busca_data)

        # Botão para adicionar especificações selecionadas (sempre visível após busca)
        st.markdown("---")  # Separador visual
        if st.button("📋 Adicionar Especificações Selecionadas", type="primary", key="btn_adicionar_especificacoes_saved"):
            if st.session_state.get('especificacoes_selecionadas', []):
                # Inicializar lista se não existir
                if "classificador_selecionado" not in st.session_state:
                    st.session_state.classificador_selecionado = []

                # Adicionar apenas as especificações selecionadas
                itens_adicionados = 0
                for item in st.session_state.especificacoes_selecionadas:
                    # Verificar se já não existe na lista
                    ja_existe = any(
                        sel.get('especificacao') == item.get('especificacao') and
                        sel.get('classe') == item.get('classe')
                        for sel in st.session_state.classificador_selecionado
                    )

                    if not ja_existe:
                        st.session_state.classificador_selecionado.append(
                            item)
                        itens_adicionados += 1

                # Marcar que as especificações devem ser aplicadas ao formulário principal
                st.session_state.aplicar_especificacoes = True
                st.session_state.especificacoes_para_aplicar = st.session_state.especificacoes_selecionadas.copy()

                # Limpar seleções temporárias
                st.session_state.especificacoes_selecionadas = []

                st.success(
                    f"✅ {itens_adicionados} especificação(ões) adicionada(s) e aplicada(s) ao formulário!")
                st.rerun()
            else:
                st.warning(
                    "⚠️ Nenhuma especificação foi selecionada. Selecione pelo menos uma especificação antes de adicionar.")


def limpar_cache_completo():
    """Limpa todo o cache e session_state de forma mais agressiva"""
    try:
        # Limpar todos os caches
        st.cache_data.clear()
        st.cache_resource.clear()

        # Limpar session_state
        limpar_session_state()

        return True
    except Exception as e:

        return False
