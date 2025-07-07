# app.py
import streamlit as st
from datetime import date
from form_agent import FormAgent
from email_agent import EmailAgent
from supabase_agent import SupabaseAgent
import json
from fpdf import FPDF
from streamlit_option_menu import option_menu
from dotenv import load_dotenv
import os
import logging
import re
from typing import Dict, List, Optional
from classificador_agent import carregar_classificador_inpi_json


st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    /* header {visibility: hidden;} */
    footer {visibility: hidden;}
    .stDeployButton {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)


def login_screen(supabase_agent):
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #fff !important;
        }
        .centered-login {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 10vh;
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
        // Detectar quando Enter é pressionado no campo de senha
        function setupEnterKey() {
            const passwordInput = document.querySelector('input[type="password"]');
            const emailInput = document.querySelector('input[type="text"]');
            
            if (passwordInput && emailInput) {
                passwordInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        if (emailInput.value && passwordInput.value) {
                            e.preventDefault();
                            // Encontrar e clicar no botão de login
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
        
        // Executar quando a página carrega
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(setupEnterKey, 500);
        });
        
        // Executar imediatamente se a página já carregou
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
                # Carregar classificador INPI do JSON aqui!
                with st.spinner("Carregando Classificador INPI..."):
                    st.session_state.classificador_inpi = carregar_classificador_inpi_json()
                st.session_state.user = user
                st.session_state.jwt_token = jwt_token
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Login ou senha incorretos. Por favor, tente novamente.")
        except Exception:
            st.error("Login ou senha incorretos. Por favor, tente novamente.")
    st.markdown(
        """
        <div class='footer'>© 2025 AGP Consultoria</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def gerar_pdf_busca(busca):
    pdf = FPDF()
    pdf.add_page()
    pdf.image('logo_agp.png', x=80, y=10, w=50)  # Centraliza a logo no topo
    pdf.ln(30)  # Espaço após a logo
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Detalhes da Busca", ln=1, align="C")
    campos_ocultos = {"id", "created_at", "consultor_id"}
    for k, v in busca.items():
        if k not in campos_ocultos and k != "marcas" and k != "especificacoes" and k != "dados_completos":
            pdf.cell(200, 10, f"{k}: {v}", ln=1)
    # Se houver dados_completos, use para gerar o PDF
    if "dados_completos" in busca:
        try:
            dados = busca["dados_completos"]
            if isinstance(dados, str):
                dados = json.loads(dados)
                if isinstance(dados, str):
                    dados = json.loads(dados)
            for i, marca in enumerate(dados.get("marcas", [])):
                pdf.cell(200, 10, f"Marca: {marca.get('marca', '')}", ln=1)
                for classe in marca.get("classes", []):
                    classe_num = classe.get("classe", "")
                    pdf.set_font("Arial", style="B", size=12)
                    pdf.cell(0, 10, f"Classe {classe_num}", ln=1)
                    pdf.set_font("Arial", size=12)
                    especificacao = classe.get("especificacao", "")
                    if isinstance(especificacao, list):
                        especs = [e.strip()
                                  for e in especificacao if e.strip()]
                    else:
                        especs = [e.strip() for e in str(
                            especificacao).split("\n") if e.strip()]
                    if especs:
                        for espec in especs:
                            pdf.multi_cell(0, 10, f"- {espec}")
                    else:
                        pdf.multi_cell(0, 10, "(Sem especificações)")
                    pdf.ln(2)
        except Exception as e:
            pdf.multi_cell(0, 10, f"Erro ao exibir dados da busca: {e}")
    elif "marcas" in busca and busca["marcas"]:
        try:
            especificacoes_por_classe = json.loads(busca["marcas"])
            for classe, bloco in especificacoes_por_classe.items():
                pdf.set_font("Arial", style="B", size=12)
                pdf.cell(0, 10, f"Classe {classe}", ln=1)
                pdf.set_font("Arial", size=12)
                for espec in re.split(r";|\n", bloco):
                    espec = espec.strip()
                    if espec:
                        pdf.multi_cell(0, 10, f"- {espec}")
                pdf.ln(2)
        except Exception:
            marcas = busca.get("marcas")
            if marcas is None:
                marcas = "Dados de marcas não disponíveis para esta busca."
            else:
                marcas = str(marcas)
            pdf.multi_cell(0, 10, marcas)
    elif "especificacoes" in busca and busca["especificacoes"]:
        for espec in re.split(r",|\n", busca["especificacoes"]):
            espec = espec.strip()
            if espec:
                pdf.multi_cell(0, 10, f"- {espec}")
    if "observacao" in busca and busca["observacao"]:
        observacao = busca.get("observacao")
        if observacao is None:
            observacao = "Sem observações"
        else:
            observacao = str(observacao)
        pdf.multi_cell(0, 10, f"Observação: {observacao}")
    result = pdf.output(dest='S')
    if isinstance(result, str):
        return result.encode('latin1')
    return bytes(result)


def limpar_formulario():
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


def main():
    # Carregar variáveis de ambiente
    load_dotenv()
    SMTP_HOST = os.getenv("smtp_host", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("smtp_port", 587))
    SMTP_USER = os.getenv("smtp_user", "")
    SMTP_PASS = os.getenv("smtp_pass", "")
    DESTINATARIOS = os.getenv("destinatarios", "").split(",")

    supabase_agent = SupabaseAgent()

    # Tela de login
    if "user" not in st.session_state:
        login_screen(supabase_agent)
        return

    # Controle de envio para bloquear ações
    if "enviando_pedido" not in st.session_state:
        st.session_state.enviando_pedido = False

    # CSS para deixar a sidebar branca e área principal azul
    st.markdown(
        """
        <style>
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
        }
        .stButton > button:hover {
            background-color: #004d8a !important;
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
        .stButton > button {
            background-color: #005fa3 !important;
            color: #fff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500;
            padding: 8px 24px;
        }
        .stButton > button:hover {
            background-color: #0074cc !important;
            color: #fff !important;
        }
        </style>
    """,
        unsafe_allow_html=True
    )

    st.markdown("""
<style>
/* Input */
.stTextInput input, div[data-testid="stTextInput"] input {
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    padding: 8px 16px !important;
    background: #fff !important;
    color: #005fa3 !important;
    border: 1px solid #ddd !important;
    box-sizing: border-box !important;
    line-height: 1.2 !important;
}
/* Botão de Login e botões padrão (menos específicos) */
.stButton > button, div[data-testid="stButton"] button {
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
    transition: background 0.2s;
}
.stButton > button:hover, div[data-testid="stButton"] button:hover {
    background: #0074cc !important;
    color: #fff !important;
}
/* Botão Apagar (coluna 1) */
div[data-testid="column"]:nth-of-type(1) button {
    height: 40px !important;
    min-width: 40px !important;
    max-width: 48px !important;
    padding: 0 !important;
    font-size: 1.3rem !important;
    border-radius: 12px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Botão Marcar/Desmarcar análise (coluna 2) */
div[data-testid="column"]:nth-of-type(2) button {
    height: 40px !important;
    padding: 0 24px !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    background: #0869ae !important;
    color: #fff !important;
    font-weight: 450 !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Botão Baixar PDF (coluna 3) */
div[data-testid="column"]:nth-of-type(3) button,
div[data-testid="column"]:nth-of-type(3) .stDownloadButton > button {
    height: 40px !important;
    padding: 0 32px !important;
    font-size: 1.2rem !important;
    border-radius: 12px !important;
    box-sizing: border-box !important;
    line-height: 1.1 !important;
    font-weight: 450 !important;
}
/* Botão Buscar (fora das colunas) */
div[data-testid="stButton"] > button {
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    padding: 0 24px !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    box-sizing: border-box !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)

    # Sidebar com logo e menu moderno
    with st.sidebar:
        st.image("logo_agp.png", width=120)
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

    form_agent = FormAgent()
    email_agent = EmailAgent(SMTP_HOST, SMTP_PORT,
                             SMTP_USER, SMTP_PASS, DESTINATARIOS)

    # Configuração de logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(filename='logs/app.log', level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')

    if menu == "Solicitar Busca":
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
                # --- Fluxo antigo: salvar campos tradicionais ---
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
                busca_data["consultor_id"] = st.session_state.user.id
                busca_data.pop("marcas", None)
                try:
                    email_agent.send_email(form_data)
                except Exception as e:
                    st.error(f"Erro ao enviar e-mail: {e}")
                    logging.error(f"Erro ao enviar e-mail: {e}")
                ok = supabase_agent.insert_busca_rest(
                    busca_data, st.session_state.jwt_token)
                if ok:
                    st.success("Busca salva no Supabase!")
                st.rerun()

    elif menu == "Minhas Buscas":
        st.markdown("<h2>Buscas Solicitadas</h2>", unsafe_allow_html=True)
        busca_marca = st.text_input("Pesquisar marca...", key="busca_marca")
        busca_consultor = None
        if getattr(st.session_state.user, 'email', None) == "admin@agpmarcas.com":
            busca_consultor = st.text_input(
                "Pesquisar consultor...", key="busca_consultor")
        if getattr(st.session_state.user, 'email', None) == "admin@agpmarcas.com":
            buscas = supabase_agent.get_all_buscas_rest(
                st.session_state.jwt_token)
        else:
            buscas = supabase_agent.get_buscas_rest(
                st.session_state.user.id, st.session_state.jwt_token)
        if busca_marca:
            buscas = [b for b in buscas if busca_marca.lower()
                      in b.get('marca', '').lower()]
        if busca_consultor:
            buscas = [b for b in buscas if busca_consultor.lower() in b.get(
                'nome_consultor', '').lower()]
        if buscas:
            for busca in buscas:
                status = busca.get('analise_realizada', False)
                status_icon = '✅' if status else '❌'
                if getattr(st.session_state.user, 'email', None) == "admin@agpmarcas.com":
                    expander_label = f"{status_icon} {busca.get('marca', '')} - {busca.get('data', '')} - {busca.get('nome_consultor', '')}"
                else:
                    expander_label = f"{status_icon} {busca.get('marca', '')} - {busca.get('data', '')}"
                with st.expander(expander_label):
                    st.write(f"Tipo: {busca.get('tipo_busca', '')}")
                    st.write(f"Consultor: {busca.get('nome_consultor', '')}")
                    # Remover exibição de 'especificacoes', priorizar agrupamento por classe
                    if "dados_completos" in busca:
                        try:
                            dados = busca["dados_completos"]
                            if isinstance(dados, str):
                                dados = json.loads(dados)
                                if isinstance(dados, str):
                                    dados = json.loads(dados)
                            if not isinstance(dados, dict):
                                raise ValueError(
                                    "dados_completos não é um dicionário")
                            for i, marca in enumerate(dados.get("marcas", [])):
                                st.markdown(
                                    f"<b>Marca:</b> {marca.get('marca', '')}", unsafe_allow_html=True)
                                for classe in marca.get("classes", []):
                                    classe_num = classe.get("classe", "")
                                    especificacao = classe.get(
                                        "especificacao", "")
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
                    elif "marcas" in busca and "especificacoes" in busca:
                        st.write(f"Classes: {busca.get('classes', '')}")
                        especs = busca.get('especificacoes', '')
                        if especs:
                            if isinstance(especs, str):
                                especs_list = [e.strip() for e in re.split(
                                    r",|\n", especs) if e.strip()]
                            elif isinstance(especs, list):
                                especs_list = [str(e).strip()
                                               for e in especs if str(e).strip()]
                            else:
                                especs_list = []
                            if especs_list:
                                st.write(
                                    f"Especificações: {'; '.join(especs_list)}")
                            else:
                                st.write("Especificações: Sem especificações")
                        else:
                            st.write("Especificações: Sem especificações")
                    if busca.get('observacao'):
                        st.write(f"Observação: {busca.get('observacao')}")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.button("🗑️ Apagar", key=f"apagar_{busca['id']}"):
                            ok = supabase_agent.delete_busca_rest(
                                busca['id'], st.session_state.jwt_token)
                            if ok:
                                st.success("Busca apagada com sucesso!")
                                st.rerun()
                    with col2:
                        if getattr(st.session_state.user, 'email', None) == "admin@agpmarcas.com":
                            novo_status = not status
                            btn_label = "✅ Marcar como analisada" if not status else "❌ Desmarcar análise"
                            if st.button(btn_label, key=f"toggle_analise_{busca['id']}"):
                                ok = supabase_agent.update_analise_status(
                                    busca['id'], novo_status, st.session_state.jwt_token)
                                if ok:
                                    st.success("Status de análise atualizado!")
                                    st.rerun()
                    with col3:
                        pdf_bytes = gerar_pdf_busca(busca)
                        st.download_button(
                            "📄 Baixar PDF", data=pdf_bytes, file_name=f"busca_{busca.get('id', '')}.pdf", mime="application/pdf")
        else:
            st.info("Nenhuma busca realizada ainda.")

    st.markdown("""
        <style>
        .stButton > button {
            background-color: #005fa3;
            color: #fff;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px 24px;
            margin: 4px 0;
            border: none;
            transition: background 0.2s;
        }
        .stButton > button:hover {
            background-color: #0074cc;
            color: #fff;
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
        /* Altura igual para input e botão */
        .stTextInput > div > input {
            height: 48px !important;
            font-size: 1.1rem !important;
            border-radius: 12px !important;
        }
        div[data-testid="column"]:nth-of-type(2) button {
            height: 48px !important;
            font-size: 1.1rem !important;
            border-radius: 12px !important;
            margin-top: 0 !important;
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
