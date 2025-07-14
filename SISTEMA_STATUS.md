# Sistema de Status das Buscas

## Visão Geral

O sistema utiliza a coluna `analise_realizada` existente no banco de dados para controlar o status das buscas. Isso permite que tanto os consultores quanto os analistas acompanhem o status de cada busca.

## Status Disponíveis

### 1. **Pendente** ⏳
- **Descrição**: Busca solicitada, aguardando análise
- **Valor no banco**: `analise_realizada = False`
- **Quem pode ver**: Consultor e Administradores
- **Ação disponível**: Administradores podem marcar como "Concluída"

### 2. **Concluída** ✅
- **Descrição**: Busca analisada e concluída
- **Valor no banco**: `analise_realizada = True`
- **Quem pode ver**: Consultor e Administradores
- **Ação disponível**: Administradores podem "Voltar para Pendente" (para correções)

## Usuários com Acesso Administrativo

Os seguintes usuários podem ver todas as buscas e gerenciar status:

- `admin@agpmarcas.com`
- `analista1@agpmarcas.com`
- `analista2@agpmarcas.com`
- `coordenador@agpmarcas.com`

## Fluxo de Trabalho

### Para Consultores:
1. **Solicita busca** → Status: Pendente (analise_realizada = False)
2. **Acompanha progresso** → Vê status atualizado
3. **Recebe resultado** → Status: Concluída (analise_realizada = True)

### Para Administradores/Analistas:
1. **Recebe busca** → Vê busca pendente
2. **Realiza análise** → Trabalha na busca
3. **Conclui análise** → Marca como "Concluída"
4. **Correções** → Pode voltar para "Pendente" se necessário

## Interface

### Exibição do Status:
- **Ícones visuais** para cada status
- **Texto descritivo** do status atual
- **Cor diferenciada** para cada status

### Botões de Ação (apenas para administradores):
- **✅ Marcar como Concluída** (quando Pendente)
- **⏳ Marcar como Pendente** (quando Concluída)

## Benefícios

### Para Consultores:
- **Transparência**: Sabem exatamente onde está sua busca
- **Acompanhamento**: Podem acompanhar o progresso em tempo real
- **Previsibilidade**: Sabem quando a busca será concluída

### Para Analistas:
- **Organização**: Controle claro do fluxo de trabalho
- **Responsabilidade**: Cada analista sabe quais buscas precisa atender
- **Flexibilidade**: Podem corrigir status se necessário

### Para Administradores:
- **Gestão**: Visão completa de todas as buscas
- **Controle**: Podem gerenciar status conforme necessário
- **Relatórios**: Podem gerar relatórios por status

## Implementação Técnica

### Banco de Dados:
- Campo `analise_realizada` na tabela `buscas` (já existente)
- Valores possíveis: `True` (Concluída) ou `False` (Pendente)

### Código:
- `BuscaManager` gerencia todos os status
- `SupabaseAgent` atualiza status no banco
- Interface adaptativa baseada no status atual

## Próximas Melhorias Sugeridas

1. **Notificações**: E-mail automático quando status muda
2. **Histórico**: Log de mudanças de status
3. **Prazos**: Definição de prazos para cada status
4. **Relatórios**: Dashboard com estatísticas por status
5. **Comentários**: Campo para observações em cada mudança de status
6. **Status intermediários**: Adicionar status como "Em Análise" se necessário 