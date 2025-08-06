import streamlit as st
from datetime import date
import re
from collections import defaultdict
from classificador_agent import buscar_no_classificador


class FormAgent:
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
        # Removido CSS redundante, todo o estilo agora está centralizado no app.py
        st.markdown(
            "<h1 style='color:#002060;'>Solicitação de Análise de Viabilidade de Marca no INPI</h1>", unsafe_allow_html=True)

        nonce = st.session_state.get("form_nonce", 0)
        # --- Estado dinâmico para marcas e classes ---
        # Garante que marcas sempre começa limpo se não existir
        if "marcas" not in st.session_state:
            st.session_state["marcas"] = [
                {"marca": "", "classes": [{"classe": "", "especificacao": ""}]}
            ]
        if "highlight_classe" not in st.session_state:
            st.session_state.highlight_classe = None
        if "highlight_marca" not in st.session_state:
            st.session_state.highlight_marca = None
        if "envio_sucesso" not in st.session_state:
            st.session_state.envio_sucesso = False
        marcas = st.session_state.marcas

        # --- Bloco 1: Dados Gerais ---
        col1, col2, col3 = st.columns([1.2, 1, 1])
        with col1:
            data = st.date_input("Data", value=st.session_state.get(
                "data", date.today()), key=f"data_{nonce}")
            data_br = data.strftime("%d/%m/%Y")
        with col2:
            # Remover selectbox e deixar apenas "Paga" como opção fixa
            st.text_input("Tipo de Busca", value="Paga",
                          disabled=True, key=f"tipo_busca_{nonce}")
        with col3:
            consultor_nome = st.session_state.get("consultor_nome", "")
            consultor_email = st.session_state.get("consultor_email", "")
            st.text_input("Consultor", value=consultor_nome, disabled=True)
            st.text_input("E-mail", value=consultor_email, disabled=True)
            consultor = consultor_nome
            st.session_state["consultor"] = consultor

        # --- Dados do Cliente ---
        st.markdown(
            '<b style="font-size:1.2rem;color:#002060;">Dados do Cliente</b>', unsafe_allow_html=True)
        col_cliente1, col_cliente2 = st.columns([1, 1])
        with col_cliente1:
            cpf_cnpj_cliente = st.text_input(
                "CPF/CNPJ do Cliente",
                value=st.session_state.get("cpf_cnpj_cliente", ""),
                key=f"cpf_cnpj_cliente_{nonce}",
                placeholder="Digite o CPF ou CNPJ do cliente"
            )
        with col_cliente2:
            nome_cliente = st.text_input(
                "Nome do Cliente",
                value=st.session_state.get("nome_cliente", ""),
                key=f"nome_cliente_{nonce}",
                placeholder="Digite o nome completo do cliente"
            )

        st.markdown("""
    <style>
    input[disabled], .stTextInput input:disabled {
        color: #005fa3 !important;  /* Azul escuro, igual ao seu tema */
        background-color: #fff !important;  /* Fundo branco */
        opacity: 1 !important;  /* Remove o efeito apagado */
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

        # --- Bloco 2: Consulta ao Classificador INPI ---
        st.markdown(
            '<b style="font-size:1.2rem;color:#002060;">Consulta ao Classificador INPI</b>', unsafe_allow_html=True)

        # Carregar classificador se ainda não foi carregado
        if "classificador_inpi" not in st.session_state:
            with st.spinner("Carregando Classificador INPI..."):
                # carregar_classificador_inpi() # Removido
                pass  # Mantido para evitar erro se a função for removida

        # Interface de busca
        col_busca1, col_busca2 = st.columns([2, 1])
        with col_busca1:
            termo_busca = st.text_input(
                "Digite um produto ou serviço para buscar no Classificador INPI:",
                key=f"termo_busca_classificador_{nonce}",
                placeholder="Ex: software, roupas, alimentos...",
                label_visibility="visible"
            )
        with col_busca2:
            st.markdown("<div style='height:1.7em'></div>",
                        unsafe_allow_html=True)  # Alinha o botão verticalmente
            if st.button("🔍 Buscar", key=f"btn_buscar_classificador_{nonce}"):
                if termo_busca.strip():
                    resultados = buscar_no_classificador(
                        termo_busca.strip(),
                        st.session_state.classificador_inpi
                    )
                    st.session_state.resultados_busca = resultados
                    st.session_state.termo_buscado = termo_busca.strip()
                    st.success(f"Busca realizada por '{termo_busca.strip()}'.")
                    st.rerun()

        # Exibir resultados da busca
        if "resultados_busca" in st.session_state:
            if st.session_state.resultados_busca:
                agrupados = defaultdict(list)
                for item in st.session_state.resultados_busca:
                    agrupados[item['classe']].append(item['especificacao'])

                for classe, especificacoes in sorted(agrupados.items(), key=lambda x: int(x[0])):
                    with st.expander(f"Classe {classe} ({len(especificacoes)} resultados)", expanded=False):
                        selecionadas = []
                        for idx, espec in enumerate(especificacoes):
                            checked = st.checkbox(
                                espec, key=f"check_{classe}_{idx}_{nonce}")
                            if checked:
                                selecionadas.append((idx, espec))
                        if selecionadas and st.button(f"Usar essas especificações da classe {classe}", key=f"usar_varias_{classe}_{nonce}"):
                            marca = st.session_state.marcas[0]
                            especificacoes_texto = []
                            for _, espec in selecionadas:
                                match = re.match(
                                    r"^(\d{1,2})\s*-\s*(.+)$", espec)
                                if match:
                                    especificacoes_texto.append(match.group(2))
                            nova_especificacao = "\n".join(
                                especificacoes_texto)
                            # Verifica se já existem 5 classes preenchidas e a classe não existe
                            if len([c for c in marca["classes"] if c["classe"].strip()]) >= 5 and not any(c["classe"].strip() == classe for c in marca["classes"]):
                                st.error(
                                    "Limite máximo de 5 classes por marca atingido!")
                            else:
                                # Verifica se já existe a classe
                                for c in marca["classes"]:
                                    if c["classe"].strip() == classe:
                                        # Concatena se não estiver duplicado
                                        for espec in especificacoes_texto:
                                            if espec not in c["especificacao"]:
                                                if c["especificacao"]:
                                                    c["especificacao"] += "\n" + espec
                                                else:
                                                    c["especificacao"] = espec
                                        break
                                else:
                                    # Não existe a classe, procura a primeira vaga vazia
                                    for c in marca["classes"]:
                                        if not c["classe"].strip() and not c["especificacao"].strip():
                                            c["classe"] = classe
                                            c["especificacao"] = nova_especificacao
                                            break
                                    else:
                                        # Se não houver vaga vazia, adiciona nova
                                        marca["classes"].append({
                                            "classe": classe,
                                            "especificacao": nova_especificacao
                                        })
                            # Limpar os checkboxes removendo as chaves do session_state
                            for idx, espec in selecionadas:
                                key = f"check_{classe}_{idx}"
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.success(
                                f"{len(selecionadas)} especificação(ões) adicionada(s)!")
                            st.rerun()
                st.info(
                    f"Mostrando {len(st.session_state.resultados_busca)} resultados agrupados por classe. Refine sua busca para ver menos resultados.")
            else:
                st.warning(
                    "Nenhum resultado encontrado para sua pesquisa. Tente outro termo!")

        # Botão para limpar resultados
        if "resultados_busca" in st.session_state and st.session_state.resultados_busca:
            if st.button("Limpar resultados", key=f"limpar_resultados_{nonce}"):
                del st.session_state.resultados_busca
                del st.session_state.termo_buscado
                st.rerun()

        st.markdown("---")

        # --- Bloco 3: Marcas, Classes e Especificação ---
        st.markdown(
            '<b style="font-size:1.2rem;color:#002060;">Marcas, Classes e Especificação</b>', unsafe_allow_html=True)
        remover_marca_idx = None
        add_classe_idx = None
        remover_classe_idx = None
        for i, marca_dict in enumerate(marcas):
            # Só renderiza se for o primeiro ou se a marca tiver valor preenchido
            if i == 0 or marca_dict["marca"].strip() or any(c["classe"].strip() or c["especificacao"].strip() for c in marca_dict["classes"]):
                mcol1, mcol2 = st.columns([4, 1])
                with mcol1:
                    marca_dict["marca"] = st.text_input(
                        "Marca", value=marca_dict["marca"], key=f"marca_{i}_{nonce}")
                with mcol2:
                    pass  # Não exibir botão de remover marca, pois só haverá uma
                st.markdown(
                    f"<b>Classes para {marca_dict['marca'] or 'Marca'}</b>", unsafe_allow_html=True)
                for j, classe_dict in enumerate(marca_dict["classes"]):
                    classe_val = st.text_input(
                        f"Classe {j+1} da Marca", value=classe_dict["classe"], key=f"classe_{i}_{j}_{nonce}")
                    if classe_val and (not re.fullmatch(r"\d{1,2}", classe_val)):
                        st.error(
                            "A classe deve conter apenas números e até dois dígitos.")
                    else:
                        classe_dict["classe"] = classe_val
                    classe_dict["especificacao"] = st.text_area(
                        f"Especificação da Classe {j+1} da Marca", value=classe_dict["especificacao"], key=f"especificacao_{i}_{j}_{nonce}")
                    # Exibir especificações em linha, separadas por ponto e vírgula, se houver valor
                    especs = [e.strip() for e in classe_dict["especificacao"].split(
                        '\n') if e.strip()]
                    if especs:
                        especs_str = '; '.join(especs)
                        st.markdown(
                            f"<div style='color:#444;font-size:12px;margin-bottom:8px;'><b>Visualização:</b> {especs_str}</div>", unsafe_allow_html=True)
                    if st.button("➖", key=f"remover_classe_{i}_{j}_{nonce}", help="Remover esta classe", disabled=st.session_state.get('enviando_pedido', False)):
                        remover_classe_idx = (i, j)
                # Botão de adicionar classe (máximo 5 classes por marca)
                if len(marca_dict["classes"]) < 5:
                    if st.button("➕ Adicionar Classe", key=f"add_classe_{i}_{nonce}", help="Adicionar nova classe para esta marca", disabled=st.session_state.get('enviando_pedido', False)):
                        add_classe_idx = i
        # Remover o botão de adicionar nova marca
        # if st.button("➕ Adicionar Nova Marca", key="add_marca", help="Adicionar mais uma marca"):
        #     marcas.append({"marca": "", "classes": [{"classe": "", "especificacao": ""}]})
        #     st.session_state.marcas = marcas
        #     st.session_state.highlight_marca = len(marcas)-1
        #     st.rerun()
        # Manipulação dos botões após o loop
        if remover_marca_idx is not None:
            marcas.pop(remover_marca_idx)
            st.session_state.marcas = marcas
            st.rerun()
        if add_classe_idx is not None:
            marcas[add_classe_idx]["classes"].append(
                {"classe": "", "especificacao": ""})
            st.session_state.marcas = marcas
            st.session_state.highlight_classe = (
                add_classe_idx, len(marcas[add_classe_idx]["classes"])-1)
            st.rerun()
        if remover_classe_idx is not None:
            i, j = remover_classe_idx
            if len(marcas[i]["classes"]) > 1:
                marcas[i]["classes"].pop(j)
                st.session_state.marcas = marcas
                st.rerun()

        # Efeito visual temporário para novo bloco de classe
        # Removido time.sleep para evitar lentidão
        # if st.session_state.highlight_classe is not None:
        #     time.sleep(1)
        #     st.session_state.highlight_classe = None
        # if st.session_state.highlight_marca is not None:
        #     time.sleep(1)
        #     st.session_state.highlight_marca = None

        # Campo Observação (sempre no final, independente do número de classes)
        observacao = st.text_area("Observação", value=st.session_state.get(
            "observacao", ""), key=f"observacao_{nonce}")

        # --- Botão de envio final ---
        if st.button("Enviar Pedido de Busca", key=f"enviar_final_{nonce}", disabled=st.session_state.get('enviando_pedido', False)):
            st.session_state.enviando_pedido = True
            consultor_val = st.session_state.get("consultor", "").strip()
            if not consultor_val:
                st.error(
                    "Por favor, preencha o nome do consultor antes de enviar.")
                return None

            # Validar campos do cliente
            cpf_cnpj_cliente_val = st.session_state.get(
                f"cpf_cnpj_cliente_{nonce}", "").strip()
            if not cpf_cnpj_cliente_val:
                st.error(
                    "Por favor, preencha o CPF/CNPJ do cliente antes de enviar.")
                return None

            nome_cliente_val = st.session_state.get(
                f"nome_cliente_{nonce}", "").strip()
            if not nome_cliente_val:
                st.error("Por favor, preencha o nome do cliente antes de enviar.")
                return None
            for i, marca in enumerate(st.session_state.marcas):
                # Validar se o nome da marca está preenchido
                marca_val = st.session_state.get(
                    f"marca_{i}_{nonce}", "").strip()
                if not marca_val:
                    st.error(
                        "Por favor, preencha o nome da marca antes de enviar.")
                    return None
                for j, classe in enumerate(marca["classes"]):
                    classe_val = st.session_state.get(
                        f"classe_{i}_{j}_{nonce}", "").strip()
                    especificacao_val = st.session_state.get(
                        f"especificacao_{i}_{j}_{nonce}", "").strip()
                    if not classe_val:
                        st.error("O campo Classe deve ser preenchido.")
                        return None
                    if not re.fullmatch(r"\d{1,2}", classe_val):
                        st.error(
                            "O campo Classe deve conter apenas números e até dois dígitos.")
                        return None
                    if not especificacao_val:
                        st.error(
                            "A especificação da classe não pode estar vazia.")
                        return None
            # Sincroniza os valores do session_state para o dicionário marcas
            for i, marca in enumerate(st.session_state.marcas):
                marca["marca"] = st.session_state.get(f"marca_{i}_{nonce}", "")
                for j, classe in enumerate(marca["classes"]):
                    classe["classe"] = st.session_state.get(
                        f"classe_{i}_{j}_{nonce}", "")
                    classe["especificacao"] = st.session_state.get(
                        f"especificacao_{i}_{j}_{nonce}", "")
            st.session_state.envio_sucesso = True
            form_data = {
                "data": st.session_state.get(f"data_{nonce}", date.today()).strftime("%d/%m/%Y"),
                "tipo_busca": st.session_state.get(f"tipo_busca_{nonce}", ""),
                "consultor": consultor_val,
                "cpf_cnpj_cliente": cpf_cnpj_cliente_val,
                "nome_cliente": nome_cliente_val,
                "marcas": st.session_state.marcas,
                "observacao": st.session_state.get(f"observacao_{nonce}", "")
            }
            return form_data
        return None
