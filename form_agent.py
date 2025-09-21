import streamlit as st
from datetime import date
import re
from collections import defaultdict
from classificador_agent import buscar_no_classificador


class FormAgent:
    def limpar_formulario_completo(self):
        """Limpa completamente o formulário e todos os campos relacionados"""
        # Resetar marcas para estado inicial
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

        # Limpar todos os campos do formulário
        campos_para_limpar = [
            "enviando_pedido",
            "cpf_cnpj_cliente",
            "nome_cliente",
            "observacao",
            "data",
            "envio_sucesso",
            "last_form_data",
            "uploaded_file"
        ]

        for campo in campos_para_limpar:
            if campo in st.session_state:
                del st.session_state[campo]

        # Limpar campos dinâmicos
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

    def collect_data(self):
        """
        Renderiza e gerencia o formulário de solicitação de análise de viabilidade de marca no INPI.
        Retorna um dicionário com os dados do formulário se o envio for bem-sucedido, ou None caso contrário.
        """
        # Overlay de carregamento
        if st.session_state.get('enviando_pedido', False):
            st.markdown(
                '''
                <style>
                .overlay-loading {
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(255,255,255,0.7);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .spinner {
                    border: 8px solid #f3f3f3;
                    border-top: 8px solid #005fa3;
                    border-radius: 50%;
                    width: 80px;
                    height: 80px;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .loading-msg {
                    color: #005fa3;
                    font-size: 1.5rem;
                    font-weight: bold;
                    margin-top: 24px;
                }
                </style>
                <div class="overlay-loading">
                    <div>
                        <div class="spinner"></div>
                        <div class="loading-msg">Enviando pedido de busca...</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            return

        st.markdown(
            "<h1 style='color:#002060;'>Solicitação de Análise de Viabilidade de Marca no INPI</h1>", unsafe_allow_html=True)

        # Inicializar marcas com 5 classes fixas
        if "marcas" not in st.session_state:
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

        marcas = st.session_state.marcas

        # --- Bloco 1: Dados Gerais (FORA DO FORM) ---
        st.markdown(
            '<b style="font-size:1.2rem;color:#002060;">Dados Gerais</b>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1.2, 1, 1])
        with col1:
            data = st.date_input(
                "Data", value=st.session_state.get("data", date.today()))
            data_br = data.strftime("%d/%m/%Y")
        with col2:
            st.text_input("Tipo de Busca", value="Paga", disabled=True)
        with col3:
            consultor_nome = st.session_state.get("consultor_nome", "")
            consultor_email = st.session_state.get("consultor_email", "")
            st.text_input("Consultor", value=consultor_nome, disabled=True)
            st.text_input("E-mail", value=consultor_email, disabled=True)
            consultor = consultor_nome
            st.session_state["consultor"] = consultor

        # --- Bloco 2: Classificador INPI (FORA DO FORM - OTIMIZADO) ---
        st.markdown("---")
        st.markdown(
            '<b style="font-size:1.2rem;color:#002060;">🔍 Classificador INPI - Consulta de Produtos/Serviços</b>', unsafe_allow_html=True)

        from ui_components import render_classificador_inpi
        render_classificador_inpi()

        # Formulário principal
        with st.form("formulario_busca", clear_on_submit=False):
            # --- Dados do Cliente ---
            st.markdown(
                '<b style="font-size:1.2rem;color:#002060;">Dados do Cliente</b>', unsafe_allow_html=True)
            col_cliente1, col_cliente2 = st.columns([1, 1])
            with col_cliente1:
                cpf_cnpj_cliente = st.text_input(
                    "CPF/CNPJ do Cliente",
                    value=st.session_state.get("cpf_cnpj_cliente", ""),
                    placeholder="Digite o CPF ou CNPJ do cliente"
                )
            with col_cliente2:
                nome_cliente = st.text_input(
                    "Nome do Cliente",
                    value=st.session_state.get("nome_cliente", ""),
                    placeholder="Digite o nome completo do cliente"
                )

            # --- Marcas, Classes e Especificação ---
            st.markdown(
                '<b style="font-size:1.2rem;color:#002060;">Marcas, Classes e Especificação</b>', unsafe_allow_html=True)

            # Aplicar especificações automaticamente se necessário
            if st.session_state.get('aplicar_especificacoes', False) and st.session_state.get('especificacoes_para_aplicar'):
                # Agrupar especificações por classe
                classes_agrupadas = {}
                for item in st.session_state.especificacoes_para_aplicar:
                    classe = item.get('classe', '')
                    especificacao = item.get('especificacao', '')

                    # Remover prefixo da classe da especificação (ex: "34 - " -> "")
                    if especificacao.startswith(f"{classe} - "):
                        especificacao = especificacao[len(f"{classe} - "):]
                    elif especificacao.startswith(f"{classe} "):
                        especificacao = especificacao[len(f"{classe} "):]

                    if classe not in classes_agrupadas:
                        classes_agrupadas[classe] = []
                    classes_agrupadas[classe].append(especificacao)

                # Aplicar especificações agrupadas aos campos do formulário
                for i, marca_dict in enumerate(marcas):
                    if i == 0:  # Apenas para a primeira marca por enquanto
                        # Ordenar classes para aplicar de forma consistente
                        classes_ordenadas = sorted(classes_agrupadas.items())

                        for classe, especificacoes in classes_ordenadas:
                            # Juntar todas as especificações da mesma classe
                            especificacoes_juntas = '; '.join(especificacoes)

                            # Verificar se esta classe já existe nos campos
                            classe_ja_existe = False
                            for campo in marca_dict["classes"]:
                                if campo["classe"] == classe:
                                    # Se a classe já existe, adicionar as especificações ao campo existente
                                    if campo["especificacao"]:
                                        campo["especificacao"] += f"; {especificacoes_juntas}"
                                    else:
                                        campo["especificacao"] = especificacoes_juntas
                                    classe_ja_existe = True
                                    break

                            # Se a classe não existe, procurar um campo vazio
                            if not classe_ja_existe:
                                for campo in marca_dict["classes"]:
                                    if not campo["classe"] and not campo["especificacao"]:
                                        # Campo vazio encontrado
                                        campo["classe"] = classe
                                        campo["especificacao"] = especificacoes_juntas
                                        break

                # Limpar o flag após aplicar
                st.session_state.aplicar_especificacoes = False
                st.session_state.especificacoes_para_aplicar = None

            for i, marca_dict in enumerate(marcas):
                marca_dict["marca"] = st.text_input(
                    "Marca", value=marca_dict["marca"], key=f"marca_{i}")

                st.markdown(
                    f"<b>Classes para {marca_dict['marca'] or 'Marca'}</b>", unsafe_allow_html=True)

                # Renderizar as 5 classes fixas
                for j in range(5):
                    # Layout em colunas para classe e especificação lado a lado
                    col_classe, col_espec = st.columns([1, 3])

                    with col_classe:
                        classe_val = st.text_input(
                            f"Classe {j+1}",
                            value=marca_dict["classes"][j]["classe"],
                            key=f"classe_{i}_{j}",
                            help="Digite apenas números entre 1 e 45 (ex: 1, 25, 42)"
                        )
                        if classe_val and (not re.fullmatch(r"\d{1,2}", classe_val)):
                            st.error("Apenas números (1-45)")
                        elif classe_val and (int(classe_val) < 1 or int(classe_val) > 45):
                            st.error("Número deve estar entre 1 e 45")
                        else:
                            marca_dict["classes"][j]["classe"] = classe_val

                    with col_espec:
                        marca_dict["classes"][j]["especificacao"] = st.text_area(
                            f"Especificação {j+1}",
                            value=marca_dict["classes"][j]["especificacao"],
                            key=f"especificacao_{i}_{j}",
                            height=80,  # Altura reduzida
                            help="Descreva os produtos/serviços desta classe"
                        )

                        # Exibir especificações em linha, separadas por ponto e vírgula, se houver valor
                        especs = [e.strip() for e in marca_dict["classes"]
                                  [j]["especificacao"].split('\n') if e.strip()]
                        if especs:
                            especs_str = '; '.join(especs)
                            st.markdown(
                                f"<div style='color:#666;font-size:11px;margin-top:2px;'><b>Preview:</b> {especs_str}</div>",
                                unsafe_allow_html=True
                            )

                    # Separador visual entre classes
                    if j < 4:  # Não mostrar separador na última classe
                        st.markdown(
                            "<hr style='margin: 8px 0; border-color: #e0e0e0;'>", unsafe_allow_html=True)

            # Campo Observação
            observacao = st.text_area(
                "Observação", value=st.session_state.get("observacao", ""))

            # --- Upload de Arquivo (NO FINAL) ---
            st.markdown(
                '<b style="font-size:1.2rem;color:#002060;">Upload de Arquivo</b>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Anexar arquivo (opcional)",
                type=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif'],
                help="Formatos aceitos: PDF, DOC, DOCX, JPG, JPEG, PNG, GIF"
            )

            # Botão de envio
            submitted = st.form_submit_button(
                "Enviar Pedido de Busca", disabled=st.session_state.get('enviando_pedido', False))

            if submitted:
                # Validações
                if not consultor.strip():
                    st.error(
                        "Por favor, preencha o nome do consultor antes de enviar.")
                    return None

                if not nome_cliente.strip():
                    st.error(
                        "Por favor, preencha o nome do cliente antes de enviar.")
                    return None

                if not cpf_cnpj_cliente.strip():
                    st.error(
                        "Por favor, preencha o CPF/CNPJ do cliente antes de enviar.")
                    return None

                # Validar marca e classes
                for i, marca in enumerate(marcas):
                    marca_val = marca["marca"].strip()
                    if not marca_val:
                        st.error(
                            "Por favor, preencha o nome da marca antes de enviar.")
                        return None

                    # Verificar se pelo menos uma classe foi preenchida
                    classes_preenchidas = []
                    for j, classe in enumerate(marca["classes"]):
                        classe_val = classe["classe"].strip()
                        especificacao_val = classe["especificacao"].strip()

                        # Se a classe tem valor, validar
                        if classe_val or especificacao_val:
                            if not classe_val:
                                st.error(
                                    f"O campo Classe {j+1} deve ser preenchido.")
                                return None
                            if not re.fullmatch(r"\d{1,2}", classe_val):
                                st.error(
                                    "O campo Classe deve conter apenas números (1-99).")
                                return None
                            if int(classe_val) < 1 or int(classe_val) > 45:
                                st.error(
                                    "A classe deve ser um número entre 1 e 45.")
                                return None
                            if not especificacao_val:
                                st.error(
                                    f"A especificação da classe {j+1} não pode estar vazia.")
                                return None
                            classes_preenchidas.append(j)

                    # Verificar se pelo menos uma classe foi preenchida
                    if not classes_preenchidas:
                        st.error("Pelo menos uma classe deve ser preenchida.")
                        return None

                # Preparar dados do formulário
                form_data = {
                    "data": data.strftime("%d/%m/%Y"),
                    "tipo_busca": "Paga",
                    "consultor": consultor,
                    "cpf_cnpj_cliente": cpf_cnpj_cliente,
                    "nome_cliente": nome_cliente,
                    "marcas": marcas,
                    "observacao": observacao,
                    "uploaded_file": uploaded_file
                }

                st.session_state.envio_sucesso = True
                return form_data

        return None
