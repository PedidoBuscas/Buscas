# PROJETO_BUSCA

Sistema de busca e análise de viabilidade de marcas no INPI, com autenticação, envio de e-mails e integração ao Supabase.

## Funcionalidades

- Busca de produtos/serviços no Classificador INPI
- Cadastro e consulta de buscas
- Envio de e-mails automáticos
- Autenticação de usuários via Supabase
- Geração de PDF dos resultados

## Requisitos

- Python 3.8+
- Variáveis de ambiente configuradas (ver `.env.example`)
- Dependências do `requirements.txt`

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/seu-repo.git
   cd seu-repo
   ```

2. Crie e ative o ambiente virtual:
   ```bash
   python -m venv venv
   # No Windows:
   .\venv\Scripts\Activate.ps1
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure o arquivo `.env`:
   - Copie `.env.example` para `.env` e preencha com seus dados.

## Como rodar

```bash
streamlit run app.py
```

Acesse no navegador: [http://localhost:8501](http://localhost:8501)

## Variáveis de ambiente

Veja o arquivo `.env.example` para saber quais variáveis precisam ser configuradas.

## Deploy

- Suba o projeto para o GitHub.
- Configure as variáveis de ambiente no painel do serviço cloud (Cloudflare, Streamlit Cloud, etc).
- Instale as dependências com `pip install -r requirements.txt`.
- Rode o app com `streamlit run app.py`.

## Licença

[MIT](LICENSE) (ou a licença que preferir) 