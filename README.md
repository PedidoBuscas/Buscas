# PROJETO_BUSCA

Sistema completo de busca e análise de viabilidade de marcas no INPI, com autenticação, envio de e-mails, gestão de patentes e integração ao Supabase.

## Funcionalidades

### 🔍 Sistema de Busca de Marcas
- Busca de produtos/serviços no Classificador INPI
- Cadastro e consulta de buscas
- Envio de e-mails automáticos
- Geração de PDF dos resultados
- Sistema de status para acompanhamento (Pendente, Recebida, Em Análise, Concluída)
- Upload de PDFs para relatórios
- Interface administrativa para gestão de buscas

### 📄 Sistema de Patentes
- **Solicitação de Serviços de Patente**: Formulário completo com campos:
  - CPF/CNPJ do cliente
  - Pessoa para contato
  - Telefone para contato
  - E-mail para contato
  - Processo da patente
  - Seleção de serviços específicos (Manifestação à Nulidade, Alterações nos relatórios, etc.)
  - Upload de PDFs da patente
  - Envio automático de e-mails para engenheiros

- **Gestão de Patentes**: Sistema completo de status:
  - **Pendente**: Patente recém cadastrada
  - **Recebido**: Patente recebida para análise
  - **Fazendo Relatório**: Em processo de elaboração
  - **Relatório Concluído**: Relatório finalizado e enviado

- **Funcionalidades Administrativas**:
  - Visualização de todas as patentes por administradores
  - Mudança de status com botões intuitivos
  - Upload de relatórios PDF
  - Envio automático de relatórios para consultores e funcionários
  - Interface organizada por abas de status

### 🔐 Sistema de Autenticação e Permissões
- Autenticação de usuários via Supabase
- **Tabela `perfil`**: Para consultores e administradores de busca
- **Tabela `funcionario`**: Para funcionários e administradores de patentes
- Controle de acesso baseado em roles
- Row Level Security (RLS) implementado

### 📧 Sistema de E-mails
- Envio automático de notificações
- E-mails personalizados com dados da solicitação
- Anexos de PDFs automáticos
- Múltiplos destinatários configuráveis

### 🗄️ Armazenamento e Banco de Dados
- **Supabase**: Backend completo (PostgreSQL, Auth, Storage)
- **Storage Buckets**:
  - `buscaspdf`: Para PDFs de buscas de marcas
  - `patentepdf`: Para PDFs de patentes
- **Tabelas principais**:
  - `buscas`: Buscas de marcas
  - `deposito_patente`: Solicitações de patentes
  - `perfil`: Perfis de consultores
  - `funcionario`: Funcionários e administradores

## Requisitos

- Python 3.8+
- Variáveis de ambiente configuradas (ver `.env.example`)
- Dependências do `requirements.txt`
- Conta no Supabase configurada

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/PROJETO_BUSCA.git
   cd PROJETO_BUSCA
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
   - Copie `.env.example` para `.env` e preencha com seus dados do Supabase.

## Como rodar

```bash
streamlit run app.py
```

Acesse no navegador: [http://localhost:8501](http://localhost:8501)

## Variáveis de ambiente

Veja o arquivo `.env.example` para saber quais variáveis precisam ser configuradas:

- `SUPABASE_URL`: URL do seu projeto Supabase
- `SUPABASE_KEY`: Chave de API do Supabase
- `SMTP_HOST`: Servidor SMTP para e-mails
- `SMTP_PORT`: Porta do servidor SMTP
- `SMTP_USER`: Usuário do e-mail
- `SMTP_PASS`: Senha do e-mail
- `DESTINATARIOS`: Lista de e-mails para notificações
- `DESTINATARIO_ENGE`: E-mail para notificações de patentes

## Estrutura do Projeto

```
PROJETO_BUSCA/
├── app.py                 # Aplicação principal
├── config.py              # Configurações e variáveis
├── supabase_agent.py      # Agente para interação com Supabase
├── email_agent.py         # Agente para envio de e-mails
├── form_agent.py          # Agente para formulários
├── pdf_generator.py       # Geração de PDFs
├── classificador_agent.py # Classificador INPI
├── ui_components.py       # Componentes de interface
├── marcas/
│   ├── views.py          # Views de buscas de marcas
│   └── busca_manager.py  # Gerenciador de buscas
├── patentes/
│   └── views.py          # Views de patentes
├── requirements.txt       # Dependências Python
└── README.md             # Este arquivo
```

## Funcionalidades Técnicas

### 🔧 Melhorias Implementadas
- **REST API com JWT**: Todas as operações usam REST API com autenticação JWT
- **Row Level Security**: Políticas RLS configuradas para segurança
- **Upload de Arquivos**: Sistema robusto de upload com sanitização de nomes
- **Sistema de Status**: Controle completo de status para buscas e patentes
- **Interface Responsiva**: Design moderno com Streamlit
- **Tratamento de Erros**: Logs detalhados e mensagens informativas

### 📊 Banco de Dados
- **Tabela `buscas`**: Buscas de marcas com status
- **Tabela `deposito_patente`**: Solicitações de patentes com campos completos
- **Tabela `perfil`**: Consultores e administradores de busca
- **Tabela `funcionario`**: Funcionários e administradores de patentes
- **Storage Buckets**: Organização por tipo de documento

## Deploy

- Suba o projeto para o GitHub
- Configure as variáveis de ambiente no painel do serviço cloud (Cloudflare, Streamlit Cloud, etc)
- Instale as dependências com `pip install -r requirements.txt`
- Rode o app com `streamlit run app.py`

## Licença

[MIT](LICENSE) (ou a licença que preferir) 