import json
import re
from fpdf import FPDF
from ui_components import exibir_especificacoes_pdf


def gerar_pdf_busca(busca):
    """
    Gera um PDF com os detalhes da busca.

    Args:
        busca (dict): Dicionário com os dados da busca

    Returns:
        bytes: Conteúdo do PDF em bytes
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.image('logo_agp.png', x=80, y=10, w=50)  # Centraliza a logo no topo
    pdf.ln(30)  # Espaço após a logo
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Detalhes da Busca", ln=1, align="C")

    # Campos que não devem aparecer no PDF
    campos_ocultos = {"id", "created_at", "consultor_id"}

    # Adiciona campos básicos
    for k, v in busca.items():
        if k not in campos_ocultos and k != "marcas" and k != "especificacoes" and k != "dados_completos":
            pdf.cell(200, 10, f"{k}: {v}", ln=1)

    # Processa dados completos se disponível
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

    # Processa marcas se dados_completos não estiver disponível
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

    # Processa especificações se marcas não estiver disponível
    elif "especificacoes" in busca and busca["especificacoes"]:
        for espec in re.split(r",|\n", busca["especificacoes"]):
            espec = espec.strip()
            if espec:
                pdf.multi_cell(0, 10, f"- {espec}")

    # Adiciona observação
    if "observacao" in busca and busca["observacao"]:
        observacao = busca.get("observacao")
        if observacao is None:
            observacao = "Sem observações"
        else:
            observacao = str(observacao)
        pdf.multi_cell(0, 10, f"Observação: {observacao}")

    # Retorna o PDF em bytes
    result = pdf.output(dest='S')
    if isinstance(result, str):
        return result.encode('latin1')
    return bytes(result)
