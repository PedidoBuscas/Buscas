import streamlit as st
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from marcas.busca_manager import get_user_attr, get_user_id


class RelatorioCustos:
    """Gerencia relatórios de custos de análise de marca por consultor"""

    def __init__(self, busca_manager):
        self.busca_manager = busca_manager

    def calcular_custo_busca(self, busca: Dict[str, Any]) -> float:
        """
        Calcula o custo de uma busca baseado no número de classes.

        Regras de custo:
        - 1 marca + 1 classe = R$ 40,00
        - Cada classe adicional = +R$ 10,00

        Args:
            busca: Dicionário com dados da busca

        Returns:
            float: Custo total da busca
        """
        try:
            # Tentar obter classes do campo 'classes' (JSON string)
            classes_str = busca.get('classes', '[]')
            if isinstance(classes_str, str):
                classes = json.loads(classes_str)
            else:
                classes = classes_str if isinstance(classes_str, list) else []

            # Se não conseguir obter do campo 'classes', tentar do 'dados_completos'
            if not classes:
                dados_completos = busca.get('dados_completos', '{}')
                if isinstance(dados_completos, str):
                    try:
                        dados = json.loads(dados_completos)
                        marcas = dados.get('marcas', [])
                        if marcas and len(marcas) > 0:
                            classes = [c.get('classe', '')
                                       for c in marcas[0].get('classes', [])]
                    except:
                        classes = []

            # Filtrar classes vazias
            classes = [c for c in classes if c and c.strip()]
            num_classes = len(classes)

            # Calcular custo
            if num_classes == 0:
                return 0.0  # Busca sem classes
            elif num_classes == 1:
                return 40.0  # 1 marca + 1 classe = R$ 40,00
            else:
                # 1 marca + 1 classe = R$ 40,00 + (classes adicionais × R$ 10,00)
                return 40.0 + ((num_classes - 1) * 10.0)

        except Exception as e:
            logging.error(
                f"Erro ao calcular custo da busca {busca.get('id', 'N/A')}: {e}")
            return 0.0

    def gerar_relatorio_custos(self, buscas: List[Dict[str, Any]], filtro_consultor: str = None, filtro_periodo: Tuple[date, date] = None) -> Dict[str, Any]:
        """
        Gera relatório de custos por consultor.

        Args:
            buscas: Lista de buscas
            filtro_consultor: Nome do consultor para filtrar (opcional)
            filtro_periodo: Tupla (data_inicio, data_fim) para filtrar por período (opcional)

        Returns:
            Dict com dados do relatório
        """
        # Filtrar por consultor se especificado
        if filtro_consultor:
            buscas = [b for b in buscas if filtro_consultor.lower() in b.get(
                'nome_consultor', '').lower()]

        # Filtrar por período se especificado
        if filtro_periodo:
            data_inicio, data_fim = filtro_periodo
            buscas_filtradas = []
            for busca in buscas:
                try:
                    data_busca = datetime.fromisoformat(
                        busca.get('created_at', '').replace('Z', '+00:00'))
                    if data_inicio <= data_busca.date() <= data_fim:
                        buscas_filtradas.append(busca)
                except:
                    continue
            buscas = buscas_filtradas

        # Agrupar por consultor e mês
        custos_por_consultor_mes = {}
        total_geral = 0.0

        for busca in buscas:
            consultor = busca.get(
                'nome_consultor', 'Consultor não identificado')
            custo = self.calcular_custo_busca(busca)

            # Extrair mês/ano da data da busca
            try:
                # Usar a mesma lógica robusta de formatação de data
                from marcas.views import formatar_mes_ano_cached
                mes_ano = formatar_mes_ano_cached(busca.get('created_at', ''))
            except Exception as e:
                print(f"Erro ao formatar data: {e}")
                mes_ano = "Data não disponível"

            if consultor not in custos_por_consultor_mes:
                custos_por_consultor_mes[consultor] = {}

            if mes_ano not in custos_por_consultor_mes[consultor]:
                custos_por_consultor_mes[consultor][mes_ano] = {
                    'total_buscas': 0,
                    'total_custo': 0.0,
                    'buscas': []
                }

            custos_por_consultor_mes[consultor][mes_ano]['total_buscas'] += 1
            custos_por_consultor_mes[consultor][mes_ano]['total_custo'] += custo
            custos_por_consultor_mes[consultor][mes_ano]['buscas'].append({
                'id': busca.get('id'),
                'marca': busca.get('marca', ''),
                'custo': custo,
                'data': busca.get('created_at', ''),
                'status': busca.get('status_busca', '')
            })

            total_geral += custo

        return {
            'custos_por_consultor_mes': custos_por_consultor_mes,
            'total_geral': total_geral,
            'total_buscas': len(buscas),
            'periodo': filtro_periodo,
            'consultor_filtro': filtro_consultor
        }

    def exibir_relatorio_custos(self, is_admin: bool = False, user_id: str = None):
        """
        Exibe o relatório de custos de análise de marca.

        Args:
            is_admin: Se o usuário é administrador
            user_id: ID do usuário para verificar permissões específicas
        """
        st.header("📊 Relatório de Custos - Análise de Marca")

        # Inicializar estado do relatório
        if 'relatorio_custos_carregado' not in st.session_state:
            st.session_state.relatorio_custos_carregado = False

        # Verificar se o usuário está logado - mas não redirecionar
        if not user_id:
            st.warning(
                "⚠️ Você precisa estar logado para acessar esta funcionalidade.")
            st.info("Por favor, faça login novamente.")
            return

        # Informações sobre a política de custos
        with st.expander("ℹ️ Política de Custos", expanded=False):
            st.markdown("""
            **Política de Custos para Análise de Marca:**
            
            - **1 marca + 1 classe = R$ 40,00**
            - **Cada classe adicional = +R$ 10,00**
            
            **Exemplos:**
            - 1 marca com 1 classe: R$ 40,00
            - 1 marca com 2 classes: R$ 50,00
            - 1 marca com 3 classes: R$ 60,00
            - 1 marca com 5 classes: R$ 80,00
            """)

        # Buscar buscas com tratamento de erro melhorado
        try:
            if is_admin:
                buscas = self.busca_manager.buscar_buscas_usuario(
                    is_admin=True)
            else:
                # Para consultores, buscar apenas suas próprias buscas
                buscas = self.busca_manager.buscar_buscas_usuario(
                    user_id, is_admin=False)

            if not buscas:
                st.info("📊 Nenhuma busca encontrada para gerar o relatório.")
                st.info("As buscas aparecerão aqui após serem concluídas.")
                return

            # Gerar relatório sem filtros (mostrar todos)
            relatorio = self.gerar_relatorio_custos(buscas, None, None)

            # Verificar se há dados no relatório
            if not relatorio['custos_por_consultor_mes']:
                st.info("📊 Nenhum dado encontrado com os filtros aplicados.")
                st.info(
                    "Tente ajustar os filtros ou aguarde mais buscas serem concluídas.")
                return

            # Marcar que o relatório foi carregado com sucesso
            st.session_state.relatorio_custos_carregado = True

            # Exibir resultados
            st.subheader("📈 Resultados")

            # Resumo geral
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Buscas", relatorio['total_buscas'])
            with col2:
                st.metric("Total Geral", f"R$ {relatorio['total_geral']:.2f}")
            with col3:
                st.metric("Consultores", len(
                    relatorio['custos_por_consultor_mes']))

            # Detalhamento por consultor
            st.subheader("👥 Detalhamento por Consultor")

            if not relatorio['custos_por_consultor_mes']:
                st.info("Nenhum resultado encontrado com os filtros aplicados.")
                return

            # Ordenar consultores por total de custo (maior para menor)
            consultores_ordenados = sorted(
                relatorio['custos_por_consultor_mes'].items(),
                key=lambda x: sum(dados['total_custo']
                                  for dados in x[1].values()),
                reverse=True
            )

            for consultor, dados_por_mes in consultores_ordenados:
                # Calcular total do consultor
                total_consultor = sum(dados['total_custo']
                                      for dados in dados_por_mes.values())
                total_buscas_consultor = sum(
                    dados['total_buscas'] for dados in dados_por_mes.values())

                with st.expander(f"👤 {consultor} - R$ {total_consultor:.2f}", expanded=True):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total de Buscas", total_buscas_consultor)

                    with col2:
                        st.metric("Total de Custo",
                                  f"R$ {total_consultor:.2f}")

                    with col3:
                        if total_buscas_consultor > 0:
                            custo_medio = total_consultor / total_buscas_consultor
                            st.metric("Custo Médio", f"R$ {custo_medio:.2f}")
                        else:
                            st.metric("Custo Médio", "R$ 0,00")

                    # Exibir dados por mês
                    st.markdown("**Detalhamento por Mês:**")

                    # Ordenar meses cronologicamente
                    meses_ordenados = sorted(
                        dados_por_mes.items(), key=lambda x: x[0])

                    for mes_ano, dados_mes in meses_ordenados:
                        with st.expander(f"📅 {mes_ano} - R$ {dados_mes['total_custo']:.2f} ({dados_mes['total_buscas']} buscas)", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Buscas no Mês",
                                          dados_mes['total_buscas'])

                            with col2:
                                st.metric("Custo do Mês",
                                          f"R$ {dados_mes['total_custo']:.2f}")

                            with col3:
                                if dados_mes['total_buscas'] > 0:
                                    custo_medio_mes = dados_mes['total_custo'] / \
                                        dados_mes['total_buscas']
                                    st.metric("Custo Médio",
                                              f"R$ {custo_medio_mes:.2f}")
                                else:
                                    st.metric("Custo Médio", "R$ 0,00")

                            # Tabela com detalhes das buscas do mês
                            st.markdown("**Detalhes das Buscas:**")

                            if dados_mes['buscas']:
                                # Criar DataFrame para exibição
                                import pandas as pd

                                df_data = []
                                for busca in dados_mes['buscas']:
                                    try:
                                        # Usar a mesma lógica robusta de formatação de data
                                        from marcas.views import formatar_mes_ano_cached

                                        # Tentar formatar a data completa primeiro
                                        data_busca = datetime.fromisoformat(
                                            busca['data'].replace('Z', '+00:00'))
                                        data_formatada = data_busca.strftime(
                                            '%d/%m/%Y %H:%M')
                                    except Exception as e:
                                        print(
                                            f"Erro ao formatar data para exibição: {e}")
                                        # Se falhar, usar a data original
                                        data_formatada = busca['data']

                                    df_data.append({
                                        'Marca': busca['marca'],
                                        'Custo': f"R$ {busca['custo']:.2f}",
                                        'Data': data_formatada,
                                        'Status': busca['status'].title()
                                    })

                                df = pd.DataFrame(df_data)

                                # Criar PDF para download do DataFrame
                                def download_dataframe_as_pdf():
                                    try:
                                        from fpdf import FPDF

                                        pdf = FPDF()
                                        pdf.add_page()
                                        pdf.set_font("Arial", size=12)

                                        # Título
                                        pdf.cell(
                                            200, 10, txt=f"Detalhes das Buscas - {mes_ano}", ln=True, align='C')
                                        pdf.cell(
                                            200, 10, txt=f"Consultor: {consultor}", ln=True, align='C')
                                        pdf.cell(
                                            200, 10, txt=f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
                                        pdf.ln(10)

                                        # Resumo
                                        pdf.cell(
                                            200, 10, txt=f"Total de Buscas: {dados_mes['total_buscas']}", ln=True)
                                        pdf.cell(
                                            200, 10, txt=f"Total do Mês: R$ {dados_mes['total_custo']:.2f}", ln=True)
                                        pdf.ln(10)

                                        # Cabeçalho da tabela
                                        pdf.set_font("Arial", 'B', 10)
                                        pdf.cell(60, 8, txt="Marca", border=1)
                                        pdf.cell(40, 8, txt="Custo", border=1)
                                        pdf.cell(50, 8, txt="Data", border=1)
                                        pdf.cell(40, 8, txt="Status", border=1)
                                        pdf.ln()

                                        # Dados da tabela
                                        pdf.set_font("Arial", size=9)
                                        for _, row in df.iterrows():
                                            pdf.cell(60, 8, txt=str(
                                                row['Marca'])[:25], border=1)
                                            pdf.cell(40, 8, txt=str(
                                                row['Custo']), border=1)
                                            pdf.cell(50, 8, txt=str(
                                                row['Data']), border=1)
                                            pdf.cell(40, 8, txt=str(
                                                row['Status']), border=1)
                                            pdf.ln()

                                        return pdf.output(dest='S').encode('latin-1')
                                    except Exception as e:
                                        st.error(f"Erro ao gerar PDF: {e}")
                                        return None

                                # Exibir DataFrame
                                st.dataframe(df, use_container_width=True)

                                # CSS para botão branco com letras pretas
                                st.markdown("""
                                <style>
                                .stDownloadButton > button {
                                    background-color: white !important;
                                    color: black !important;
                                    border: 1px solid #ccc !important;
                                }
                                .stDownloadButton > button:hover {
                                    background-color: #f0f0f0 !important;
                                    color: black !important;
                                }
                                </style>
                                """, unsafe_allow_html=True)

                                # Botão de download PDF personalizado
                                pdf_data = download_dataframe_as_pdf()
                                if pdf_data:
                                    st.download_button(
                                        label=f"📄 Baixar PDF - {mes_ano}",
                                        data=pdf_data,
                                        file_name=f"detalhes_buscas_{consultor}_{mes_ano}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                        mime="application/pdf",
                                        key=f"download_pdf_{mes_ano}_{consultor}",
                                        use_container_width=True,
                                        help="Baixar detalhes das buscas em PDF"
                                    )
                            else:
                                st.info(
                                    "Nenhuma busca encontrada para este mês.")

            # Exportar relatório (apenas para admins)
            if is_admin:
                st.subheader("📤 Exportar Relatório")

                # Usar download_button em vez de button para evitar reruns
                pdf_data = self.exportar_pdf_data(relatorio)
                if pdf_data:
                    st.download_button(
                        label="📄 Exportar PDF",
                        data=pdf_data,
                        file_name=f"relatorio_custos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="download_relatorio_custos"
                    )

        except Exception as e:
            st.error(f"Erro ao gerar relatório: {e}")
            logging.error(f"Erro ao gerar relatório de custos: {e}")

    def exportar_pdf(self, relatorio: Dict[str, Any]):
        """Exporta o relatório em formato PDF"""
        try:
            from fpdf import FPDF

            # Criar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Título
            pdf.cell(
                200, 10, txt="Relatório de Custos - Análise de Marca", ln=True, align='C')
            pdf.cell(
                200, 10, txt=f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
            pdf.ln(10)

            # Resumo
            pdf.cell(
                200, 10, txt=f"Total de Buscas: {relatorio['total_buscas']}", ln=True)
            pdf.cell(
                200, 10, txt=f"Total Geral: R$ {relatorio['total_geral']:.2f}", ln=True)
            pdf.cell(
                200, 10, txt=f"Consultores: {len(relatorio['custos_por_consultor_mes'])}", ln=True)
            pdf.ln(10)

            # Tabela de dados
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Tabela de Custos por Consultor e Mês",
                     ln=True, align='C')
            pdf.ln(5)

            # Cabeçalho da tabela
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(60, 8, txt="Consultor", border=1)
            pdf.cell(30, 8, txt="Mês/Ano", border=1)
            pdf.cell(30, 8, txt="Buscas", border=1)
            pdf.cell(40, 8, txt="Custo Total", border=1)
            pdf.cell(40, 8, txt="Custo Médio", border=1)
            pdf.ln()

            # Dados da tabela
            pdf.set_font("Arial", size=9)

            # Ordenar consultores por total de custo
            consultores_ordenados = sorted(
                relatorio['custos_por_consultor_mes'].items(),
                key=lambda x: sum(dados['total_custo']
                                  for dados in x[1].values()),
                reverse=True
            )

            for consultor, dados_por_mes in consultores_ordenados:
                # Ordenar meses cronologicamente
                meses_ordenados = sorted(
                    dados_por_mes.items(), key=lambda x: x[0])

                for i, (mes_ano, dados_mes) in enumerate(meses_ordenados):
                    # Calcular custo médio
                    if dados_mes['total_buscas'] > 0:
                        custo_medio = dados_mes['total_custo'] / \
                            dados_mes['total_buscas']
                    else:
                        custo_medio = 0.0

                    # Primeira linha do consultor - mostrar nome
                    if i == 0:
                        pdf.cell(60, 8, txt=consultor[:25], border=1)
                    else:
                        pdf.cell(60, 8, txt="", border=1)

                    pdf.cell(30, 8, txt=mes_ano, border=1)
                    pdf.cell(30, 8, txt=str(
                        dados_mes['total_buscas']), border=1)
                    pdf.cell(
                        40, 8, txt=f"R$ {dados_mes['total_custo']:.2f}", border=1)
                    pdf.cell(40, 8, txt=f"R$ {custo_medio:.2f}", border=1)
                    pdf.ln()

            # Resumo por consultor
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Resumo por Consultor", ln=True)
            pdf.ln(5)

            # Cabeçalho do resumo
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(80, 8, txt="Consultor", border=1)
            pdf.cell(40, 8, txt="Total Buscas", border=1)
            pdf.cell(40, 8, txt="Total Custo", border=1)
            pdf.cell(40, 8, txt="Custo Médio", border=1)
            pdf.ln()

            # Dados do resumo
            pdf.set_font("Arial", size=9)
            for consultor, dados_por_mes in consultores_ordenados:
                total_consultor = sum(dados['total_custo']
                                      for dados in dados_por_mes.values())
                total_buscas_consultor = sum(
                    dados['total_buscas'] for dados in dados_por_mes.values())

                if total_buscas_consultor > 0:
                    custo_medio_consultor = total_consultor / total_buscas_consultor
                else:
                    custo_medio_consultor = 0.0

                pdf.cell(80, 8, txt=consultor[:35], border=1)
                pdf.cell(40, 8, txt=str(total_buscas_consultor), border=1)
                pdf.cell(40, 8, txt=f"R$ {total_consultor:.2f}", border=1)
                pdf.cell(
                    40, 8, txt=f"R$ {custo_medio_consultor:.2f}", border=1)
                pdf.ln()

            # Salvar PDF
            pdf_output = pdf.output(dest='S').encode('latin-1')

            # Download
            st.download_button(
                label="📥 Baixar PDF",
                data=pdf_output,
                file_name=f"relatorio_custos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"Erro ao exportar PDF: {e}")

    def exportar_pdf_data(self, relatorio: Dict[str, Any]) -> bytes:
        """Exporta o relatório em formato PDF e retorna os dados"""
        try:
            from fpdf import FPDF

            # Criar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Título
            pdf.cell(
                200, 10, txt="Relatório de Custos - Análise de Marca", ln=True, align='C')
            pdf.cell(
                200, 10, txt=f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
            pdf.ln(10)

            # Resumo
            pdf.cell(
                200, 10, txt=f"Total de Buscas: {relatorio['total_buscas']}", ln=True)
            pdf.cell(
                200, 10, txt=f"Total Geral: R$ {relatorio['total_geral']:.2f}", ln=True)
            pdf.cell(
                200, 10, txt=f"Consultores: {len(relatorio['custos_por_consultor_mes'])}", ln=True)
            pdf.ln(10)

            # Tabela de dados
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Tabela de Custos por Consultor e Mês",
                     ln=True, align='C')
            pdf.ln(5)

            # Cabeçalho da tabela
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(60, 8, txt="Consultor", border=1)
            pdf.cell(30, 8, txt="Mês/Ano", border=1)
            pdf.cell(30, 8, txt="Buscas", border=1)
            pdf.cell(40, 8, txt="Custo Total", border=1)
            pdf.cell(40, 8, txt="Custo Médio", border=1)
            pdf.ln()

            # Dados da tabela
            pdf.set_font("Arial", size=9)

            # Ordenar consultores por total de custo
            consultores_ordenados = sorted(
                relatorio['custos_por_consultor_mes'].items(),
                key=lambda x: sum(dados['total_custo']
                                  for dados in x[1].values()),
                reverse=True
            )

            for consultor, dados_por_mes in consultores_ordenados:
                # Ordenar meses cronologicamente
                meses_ordenados = sorted(
                    dados_por_mes.items(), key=lambda x: x[0])

                for i, (mes_ano, dados_mes) in enumerate(meses_ordenados):
                    # Calcular custo médio
                    if dados_mes['total_buscas'] > 0:
                        custo_medio = dados_mes['total_custo'] / \
                            dados_mes['total_buscas']
                    else:
                        custo_medio = 0.0

                    # Primeira linha do consultor - mostrar nome
                    if i == 0:
                        pdf.cell(60, 8, txt=consultor[:25], border=1)
                    else:
                        pdf.cell(60, 8, txt="", border=1)

                    pdf.cell(30, 8, txt=mes_ano, border=1)
                    pdf.cell(30, 8, txt=str(
                        dados_mes['total_buscas']), border=1)
                    pdf.cell(
                        40, 8, txt=f"R$ {dados_mes['total_custo']:.2f}", border=1)
                    pdf.cell(40, 8, txt=f"R$ {custo_medio:.2f}", border=1)
                    pdf.ln()

            # Resumo por consultor
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Resumo por Consultor", ln=True)
            pdf.ln(5)

            # Cabeçalho do resumo
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(80, 8, txt="Consultor", border=1)
            pdf.cell(40, 8, txt="Total Buscas", border=1)
            pdf.cell(40, 8, txt="Total Custo", border=1)
            pdf.cell(40, 8, txt="Custo Médio", border=1)
            pdf.ln()

            # Dados do resumo
            pdf.set_font("Arial", size=9)
            for consultor, dados_por_mes in consultores_ordenados:
                total_consultor = sum(dados['total_custo']
                                      for dados in dados_por_mes.values())
                total_buscas_consultor = sum(
                    dados['total_buscas'] for dados in dados_por_mes.values())

                if total_buscas_consultor > 0:
                    custo_medio_consultor = total_consultor / total_buscas_consultor
                else:
                    custo_medio_consultor = 0.0

                pdf.cell(80, 8, txt=consultor[:35], border=1)
                pdf.cell(40, 8, txt=str(total_buscas_consultor), border=1)
                pdf.cell(40, 8, txt=f"R$ {total_consultor:.2f}", border=1)
                pdf.cell(
                    40, 8, txt=f"R$ {custo_medio_consultor:.2f}", border=1)
                pdf.ln()

            # Retornar dados do PDF
            return pdf.output(dest='S').encode('latin-1')

        except Exception as e:
            st.error(f"Erro ao exportar PDF: {e}")
            return None


def relatorio_custos(busca_manager, is_admin: bool = False, user_id: str = None):
    """
    Função principal para exibir o relatório de custos.

    Args:
        busca_manager: Instância do BuscaManager
        is_admin: Se o usuário é administrador
        user_id: ID do usuário para verificar permissões específicas
    """
    try:
        relatorio = RelatorioCustos(busca_manager)
        relatorio.exibir_relatorio_custos(is_admin, user_id)
    except Exception as e:
        st.error(f"❌ Erro ao carregar relatório de custos: {str(e)}")
        st.info("💡 Tente novamente ou entre em contato com o suporte.")
        st.info("🔄 Se o problema persistir, tente recarregar a página.")

        # Log do erro para debug
        import logging
        logging.error(f"Erro no relatório de custos: {str(e)}")

        # Não fazer rerun para evitar redirecionamento
        return
