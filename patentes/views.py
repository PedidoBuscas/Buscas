import streamlit as st
from supabase_agent import SupabaseAgent
from datetime import datetime
import json

MODULO_INFO = {
    "nome": "Patentes",
    "emoji": "📄",
    "opcoes": ["Solicitar Busca", "Minhas Buscas"]
}


def solicitar_busca():
    st.header("Solicitar Busca de Patente")
    st.info("Funcionalidade de solicitação de busca de patente em breve!")


def minhas_buscas():
    st.header("Minhas Buscas de Patente")
    st.info("Funcionalidade de visualização de buscas de patente em breve!")


def solicitar_patente():
    st.info("Funcionalidade de solicitação de patente em breve!")


def minhas_patentes():
    st.header("Minhas Patentes")
    supabase_agent = SupabaseAgent()

    if "user" not in st.session_state:
        st.error("Usuário não autenticado.")
        return

    user_id = st.session_state.user['id'] if isinstance(
        st.session_state.user, dict) else st.session_state.user.id

    # Verifica se é funcionário ou consultor
    funcionario = supabase_agent.get_funcionario_by_id(user_id)
    perfil = supabase_agent.get_profile(user_id)

    patentes = []

    # Se for funcionário, busca patentes cadastradas por ele
    if funcionario:
        st.subheader("Patentes que você cadastrou")
        patentes_funcionario = supabase_agent.get_depositos_patente_para_funcionario(
            user_id)
        if patentes_funcionario:
            for pat in patentes_funcionario:
                # Cabeçalho do expansor: título, cliente e vencimento
                titulo = pat.get('titulo', 'Sem título')
                cliente = pat.get('cliente', '')
                data_vencimento = pat.get('data_vencimento', '')
                resumo = f"📋 {titulo}"
                if cliente:
                    resumo += f" | Cliente: {cliente}"
                if data_vencimento:
                    try:
                        from datetime import datetime
                        data_br = datetime.fromisoformat(
                            data_vencimento).strftime('%d/%m/%Y')
                    except Exception:
                        data_br = data_vencimento
                    resumo += f" | Vencimento: {data_br}"
                with st.expander(resumo):
                    st.markdown(f"**Status:** 🟢 Depositada")
                    st.markdown(f"**Título:** {pat.get('titulo', '')}")
                    st.markdown(f"**Cliente:** {pat.get('cliente', '')}")
                    st.markdown(f"**Contrato:** {pat.get('ncontrato', '')}")
                    st.markdown(
                        f"**Vencimento:** {formatar_data_br(pat.get('data_vencimento', ''))}")
                    st.markdown(f"**Natureza:** {pat.get('natureza', '')}")
                    st.markdown(
                        f"**Consultor:** {pat.get('name_consultor', '')}")
                    if pat.get('observacoes'):
                        st.markdown(
                            f"**Observações:** {pat.get('observacoes', '')}")
                    # Exibir links dos PDFs
                    pdfs = pat.get('pdf_patente')
                    if pdfs:
                        st.markdown("**PDF(s) da patente:**")
                        for i, url in enumerate(pdfs):
                            st.markdown(f"[PDF {i+1}]({url})")
        else:
            st.info("Você ainda não cadastrou nenhuma patente.")

    # Se for consultor (perfil existe e não é admin), busca patentes associadas a ele
    if perfil and not perfil.get('is_admin', False):
        if funcionario:  # Se também é funcionário, adiciona uma divisão
            st.markdown("---")
        st.subheader("Patentes sob sua responsabilidade")
        patentes_consultor = supabase_agent.get_depositos_patente_para_consultor(
            user_id)
        if patentes_consultor:
            for pat in patentes_consultor:
                # Cabeçalho do expansor: título, cliente e vencimento
                titulo = pat.get('titulo', 'Sem título')
                cliente = pat.get('cliente', '')
                data_vencimento = pat.get('data_vencimento', '')
                resumo = f"📋 {titulo}"
                if cliente:
                    resumo += f" | Cliente: {cliente}"
                if data_vencimento:
                    try:
                        from datetime import datetime
                        data_br = datetime.fromisoformat(
                            data_vencimento).strftime('%d/%m/%Y')
                    except Exception:
                        data_br = data_vencimento
                    resumo += f" | Vencimento: {data_br}"
                with st.expander(resumo):
                    st.markdown(f"**Status:** 🟢 Depositada")
                    st.markdown(f"**Título:** {pat.get('titulo', '')}")
                    st.markdown(f"**Cliente:** {pat.get('cliente', '')}")
                    st.markdown(f"**Contrato:** {pat.get('ncontrato', '')}")
                    st.markdown(
                        f"**Vencimento:** {formatar_data_br(pat.get('data_vencimento', ''))}")
                    st.markdown(f"**Natureza:** {pat.get('natureza', '')}")
                    st.markdown(
                        f"**Funcionário:** {pat.get('name_funcionario', '')}")
                    if pat.get('observacoes'):
                        st.markdown(
                            f"**Observações:** {pat.get('observacoes', '')}")
                    # Exibir links dos PDFs
                    pdfs = pat.get('pdf_patente')
                    if pdfs:
                        st.markdown("**PDF(s) da patente:**")
                        for i, url in enumerate(pdfs):
                            st.markdown(f"[PDF {i+1}]({url})")
        else:
            st.info("Não há patentes sob sua responsabilidade.")

    # Se não for nem funcionário nem consultor
    if not funcionario and not perfil:
        st.error(
            "Você não tem permissão para ver patentes. É necessário estar cadastrado como funcionário ou consultor.")


def deposito_patente():
    st.header("Depósito de Patente")
    supabase_agent = SupabaseAgent()

    # Verifica se há usuário na sessão e JWT token
    if "user" not in st.session_state or "jwt_token" not in st.session_state:
        st.error("Usuário não autenticado.")
        return

    user_id = st.session_state.user['id'] if isinstance(
        st.session_state.user, dict) else st.session_state.user.id

    # Verifica se o usuário está em ambas as tabelas
    if not supabase_agent.verificar_usuario_funcionario_perfil(user_id):
        st.error("Você não tem permissão para cadastrar depósitos de patente. É necessário estar cadastrado como funcionário e ter um perfil ativo.")
        return

    # Buscar funcionário logado
    funcionario = supabase_agent.get_funcionario_by_id(user_id)
    if not funcionario:
        st.error("Erro ao buscar dados do funcionário.")
        return

    # Buscar apenas consultores não-admin
    consultores = supabase_agent.get_consultores_nao_admin()
    if not consultores:
        st.warning("Nenhum consultor disponível no momento.")
        return

    consultor_nomes = [c['name'] for c in consultores if c.get('name')]
    consultor_escolhido = st.selectbox(
        "Consultor responsável", consultor_nomes)
    consultor = next(
        (c for c in consultores if c['name'] == consultor_escolhido), None) if consultor_nomes else None

    with st.form("form_deposito_patente"):
        ncontrato = st.text_input("Número do contrato")
        data_vencimento = st.date_input("Vencimento da primeira parcela")
        cliente = st.text_input("Nome do cliente")
        titulo = st.text_input("Título da patente")
        servico = st.text_input("Serviço do contrato")
        natureza = st.selectbox("Natureza da patente", [
                                "Invenção", "Modelo de Utilidade", "Desenho Industrial"])
        observacoes = st.text_area("Observações (opcional)")
        uploaded_files = st.file_uploader(
            "PDFs da patente", type=["pdf"], accept_multiple_files=True)
        submitted = st.form_submit_button("Salvar Depósito de Patente")

    if submitted:
        if not consultor:
            st.error("Por favor, selecione um consultor válido.")
            return

        pdf_urls = []
        if uploaded_files:
            for file in uploaded_files:
                url = supabase_agent.upload_pdf_to_storage(
                    file, file.name, st.session_state.jwt_token)
                pdf_urls.append(url)

        data = {
            "funcionario_id": funcionario['id'],
            "name_funcionario": funcionario['name'],
            "consultor": consultor['id'],
            "name_consultor": consultor['name'],
            "ncontrato": ncontrato,
            "data_vencimento": data_vencimento.isoformat(),
            "cliente": cliente,
            "titulo": titulo,
            "servico": servico,
            "natureza": natureza,
            "observacoes": observacoes,
            "pdf_patente": pdf_urls if pdf_urls else None,
        }
        ok = supabase_agent.insert_deposito_patente(
            data, st.session_state.jwt_token)
        if ok:
            st.success("Depósito de patente cadastrado com sucesso!")
        else:
            st.error("Erro ao salvar depósito de patente.")


def formatar_data_br(data_iso):
    try:
        if not data_iso:
            return ""
        if isinstance(data_iso, str):
            data = datetime.fromisoformat(data_iso)
        else:
            data = data_iso
        return data.strftime('%d/%m/%Y')
    except Exception:
        return str(data_iso)
