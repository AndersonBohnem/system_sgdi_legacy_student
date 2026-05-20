# SGDI — Sistema de Gestão de Demandas Internas

Sistema web em Flask para gerenciar demandas internas com controle de acesso por usuário, priorização, rastreabilidade completa e API REST para integrações externas. Interface minimalista, moderna e totalmente responsiva (mobile-first).

---

## Sumário

1. [Pré-requisitos](#pré-requisitos)
2. [Como rodar](#como-rodar)
3. [Usuários de teste](#usuários-de-teste)
4. [Funcionalidades](#funcionalidades)
5. [Dashboard Gerencial](#dashboard-gerencial)
6. [API REST Externa](#api-rest-externa)
7. [Banco de dados](#banco-de-dados)
8. [Segurança](#segurança)
9. [Variáveis de ambiente](#variáveis-de-ambiente)
10. [Estrutura do projeto](#estrutura-do-projeto)
11. [Testes automatizados](#testes-automatizados)

---

## Pré-requisitos

- Python 3.10 ou superior
- pip

---

## Como rodar

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd system_sgdi_legacy_student
```

### 2. Crie e ative um ambiente virtual

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Inicialize o banco de dados

```bash
python init_db.py
```

Cria o arquivo `demandas.db`, as 4 tabelas, os 5 usuários de teste e 20 demandas de exemplo com comentários, responsáveis e histórico de status.

### 5. Inicie o servidor

```bash
python app.py
```

### 6. Acesse o sistema

Abra o navegador em **http://localhost:5000** — a rota inicial já abre o Dashboard Gerencial.

---

## Usuários de teste

| Usuário | Senha | Perfil |
|---|---|---|
| `admin` | `Admin@2024` | Administrador |
| `joao.silva` | `Joao@2024` | João Silva |
| `maria.santos` | `Maria@2024` | Maria Santos |
| `pedro.costa` | `Pedro@2024` | Pedro Costa |
| `ana.lima` | `Ana@2024` | Ana Lima |

---

## Funcionalidades

### Autenticação e Sessão

- Tela de login com usuário e senha (hash bcrypt)
- Sessão autenticada — todas as páginas exigem login via `@login_required`
- Proteção CSRF em todos os formulários POST (token por sessão)
- Botão "Sair" encerra a sessão e invalida o token CSRF
- Após login, redireciona para o Dashboard Gerencial

### Demandas — Lista de Abertas (`/demandas`)

- Listagem de todas as demandas com status **Aberta** e **Em andamento**
- Ordenação por prioridade (padrão) ou por data de criação
- Filtro por prioridade: Crítica, Alta, Média, Baixa
- Filtro por solicitante (usuário)
- Alerta visual para demandas paradas há mais de 7 dias
- Métricas no topo: total visível, alta prioridade, demandas paradas
- Paginação em lotes de 6 itens (carregamento client-side)

### Demandas — Concluídas (`/concluidas`)

- Histórico de demandas com status **Concluída** e **Cancelada**
- Mesmos filtros de prioridade e solicitante das demandas abertas
- Opção de reabrir qualquer demanda diretamente da lista

### Criar demanda (`/nova_demanda`)

- Campos: título, descrição, prioridade, prazo previsto (SLA), responsável
- Solicitante preenchido automaticamente pelo usuário logado
- Prazo previsto alimenta os indicadores de atraso no Dashboard
- Responsável pode ser atribuído no momento da criação
- Registro automático de `None → Aberta` no histórico de status

### Editar demanda (`/editar/<id>`)

- Apenas o solicitante original pode editar (verificado no servidor)
- Campos editáveis: título, descrição, prioridade, prazo previsto, responsável
- Acesso bloqueado com redirecionamento e mensagem para outros usuários

### Detalhe da demanda (`/detalhes/<id>`)

- Visualização completa: descrição, metadados, status, solicitante, responsável
- Indicação visual "você" se a demanda pertence ao usuário logado
- **Ações contextuais por status:**
  - **Aberta:** Iniciar andamento · Concluir · Cancelar · Editar (se solicitante)
  - **Em andamento:** Concluir · Cancelar · Reabrir
  - **Concluída / Cancelada:** Reabrir
- Histórico de comentários em ordem cronológica
- Formulário de novo comentário com autor preenchido automaticamente
- **Histórico de status:** timeline completa de todas as transições com autor e timestamp
- **Resumo operacional:** solicitante, responsável, prazo, prioridade, status

### Transições de Status

Toda mudança de status é registrada automaticamente na tabela `historico_status`:

| De | Para | Rota |
|---|---|---|
| — | Aberta | Criação da demanda |
| Aberta | Em andamento | `/andamento/<id>` |
| Aberta / Em andamento | Concluída | `/concluir/<id>` |
| Aberta / Em andamento | Cancelada | `/cancelar/<id>` |
| Concluída / Cancelada | Aberta | `/reabrir/<id>` |

### Responsável pela Execução

- Campo `responsavel_id` separado do `usuario_id` (solicitante)
- Permite atribuir um executor diferente de quem abriu a demanda
- Exibido no resumo operacional, na tabela do dashboard e nas exportações
- "Não atribuído" quando nenhum responsável foi definido

### Busca (`/buscar`)

- Busca em demandas abertas por título, descrição ou solicitante
- Respeita filtros de prioridade e ordenação ativos
- Metacaracteres SQL (`%`, `_`) tratados corretamente

### Usuários (`/usuarios`)

- Painel com todos os usuários cadastrados
- Por usuário: total de demandas, abertas, concluídas, alta prioridade
- Barra de progresso de demandas abertas
- Links para filtrar o painel por usuário
- Métricas globais no topo

---

## Dashboard Gerencial

O Dashboard (`/dashboard`) é a **tela inicial** do sistema. Atualiza automaticamente a cada 60 segundos via API JSON, sem recarregar a página.

### KPIs em tempo real

| Indicador | Descrição |
|---|---|
| Total de Demandas | Contagem geral com os filtros ativos |
| Abertas | Com percentual do total |
| Em Andamento | Demandas em execução |
| Concluídas | Com percentual do total |
| Atrasadas (SLA) | Status não-final com `data_prevista` vencida |
| Prioridade Crítica | Com contagem das atrasadas |
| Tempo Médio de Resolução | Média ponderada por criticidade (dias) |

### Gráficos (Chart.js)

- **Donut** — distribuição por status com percentuais
- **Barras horizontais** — volume por prioridade
- **Linha de evolução temporal** — demandas criadas vs. concluídas com granularidade diária, semanal ou mensal

### Filtros

Todos os dados (KPIs, gráficos, tabelas, críticas) respondem aos filtros:

| Filtro | Opções |
|---|---|
| Período | Todos · Hoje · Últimos 7 dias · Último mês · Personalizado |
| Responsável | Qualquer usuário cadastrado |
| Prioridade | Crítica · Alta · Média · Baixa |
| Status | Aberta · Em andamento · Concluída · Cancelada |

### Seção Críticas e Atrasadas

Destaque visual **acima dos gráficos** para demandas com prioridade Crítica e SLA vencido:

- Tabela com: ID · Título · Responsável · Solicitante · Dias Atrasados · SLA Previsto · Status
- Dias de atraso calculados via `julianday()` do SQLite
- Exportação dedicada (somente esses casos) em **CSV**, **PDF** e **Excel**

### Tabela Por Responsável

Visão por executor: total de demandas, abertas, atrasadas e críticas. Linhas com atraso são destacadas em amarelo.

### Exportação

| Escopo | Formatos | Rota |
|---|---|---|
| Críticas + Atrasadas | CSV · PDF · Excel | `/api/dashboard/critical-overdue/export` |
| Todas as demandas (filtros ativos) | CSV · PDF · Excel | `/api/dashboard/export` |

### Badge de Alertas na Navbar

Contador vermelho ao lado de "Dashboard" visível em **todas as páginas**. Atualiza a cada 60 segundos via `/api/alerts/count`. Desaparece quando não há casos críticos atrasados.

---

## API REST Externa

O SGDI disponibiliza uma API REST para integração com sistemas externos, autenticada por **API Key**.

### Geração de chaves (`/api/keys`)

1. Faça login no sistema
2. Acesse **API Keys** na navbar
3. Informe uma descrição (ex: "Integração ERP") e clique em **Gerar chave**
4. Copie a chave exibida — ela não será mostrada novamente

### Autenticação

Inclua o header `X-API-Key` em toda requisição:

```http
GET /api/v1/demandas HTTP/1.1
Host: localhost:5000
X-API-Key: sua-chave-aqui
```

Sem chave → `401`. Chave inválida ou revogada → `403`.

### Endpoints disponíveis

#### Demandas

```
GET  /api/v1/demandas
```
Lista demandas com filtros opcionais.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `status` | string | Aberta · Em andamento · Concluída · Cancelada |
| `prioridade` | string | Crítica · Alta · Média · Baixa |
| `responsavel_id` | integer | ID do usuário responsável |
| `limit` | integer | Máximo de resultados (padrão 50, máx 200) |
| `offset` | integer | Paginação — registros a pular |

```
POST /api/v1/demandas
```
Cria uma nova demanda.

```json
{
  "titulo": "Falha no módulo de relatórios",
  "descricao": "Trava ao gerar relatórios com mais de 1000 linhas.",
  "solicitante": "Sistema ERP",
  "prioridade": "Alta",
  "responsavel_id": 2,
  "data_prevista": "2026-06-30"
}
```

```
GET  /api/v1/demandas/<id>
```
Retorna detalhes completos de uma demanda.

```
PATCH /api/v1/demandas/<id>/status
```
Atualiza o status. Registra automaticamente no histórico.

```json
{ "status": "Em andamento", "autor": "Sistema ERP" }
```

#### Comentários

```
GET  /api/v1/demandas/<id>/comentarios
POST /api/v1/demandas/<id>/comentarios
```

```json
{ "autor": "Sistema ERP", "comentario": "Recebido e em análise." }
```

#### Usuários

```
GET /api/v1/usuarios
```
Lista todos os usuários com `id`, `username` e `nome`.

### Formato de resposta

Todas as respostas seguem o mesmo envelope:

```json
{
  "success": true,
  "data": [...],
  "meta": { "total": 22 }
}
```

Erros:

```json
{ "success": false, "error": "Chave de API inválida ou desativada" }
```

### Documentação Swagger

Interface interativa disponível em **`/apidocs`** — lista todos os endpoints com parâmetros, exemplos e botão "Try it out" para testar direto no browser.

### Gestão de chaves (`/api/keys`)

- Listar todas as chaves cadastradas (mascaradas)
- Ver quem criou e quando
- Revogar chaves de sistemas que não precisam mais de acesso

---

## Banco de dados

- Arquivo: `demandas.db` (SQLite, criado automaticamente)
- Migrations automáticas via `PRAGMA table_info()` — nunca destrói dados existentes
- Demandas sem vínculo com usuário são removidas na inicialização
- Prioridades legadas (`Urgente`) são normalizadas para `Alta`

### Tabelas

| Tabela | Descrição |
|---|---|
| `usuarios` | Usuários com username, nome e senha hash bcrypt |
| `demandas` | Core do sistema — título, descrição, prioridade, status, solicitante, responsável, SLA |
| `comentarios` | Comentários vinculados a demandas com autor e timestamp |
| `historico_status` | Log auditável de toda transição de status com autor, status anterior/novo e data |
| `api_keys` | Chaves de API para integração externa com descrição, criador e flag ativo/revogada |

### Coluna `responsavel_id` em `demandas`

Separa o **solicitante** (quem abriu, coluna `usuario_id`) do **responsável** (quem executa, coluna `responsavel_id`). O JOIN usa aliases distintos para evitar conflito:

```sql
LEFT JOIN usuarios resp ON resp.id = d.responsavel_id
```

---

## Segurança

| Categoria (OWASP) | Implementação |
|---|---|
| Broken Access Control | `@login_required` em todas as rotas; verificação de autoria antes de editar/deletar |
| Cryptographic Failures | Senha com hash bcrypt via `werkzeug.security` |
| Injection (SQL) | Queries 100% parametrizadas com placeholders `?` |
| Injection (XSS) | Jinja2 auto-escape ativo em todos os templates |
| Security Misconfiguration | `SECRET_KEY` gerada via `secrets.token_hex(32)` |
| Auth & Session Failures | CSRF token por sessão validado em todo POST |
| Logging Failures | `historico_status` registra toda transição com autor e timestamp |
| API Authentication | `X-API-Key` validada em banco antes de qualquer operação da API v1 |

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | valor fixo de desenvolvimento | Chave para assinar sessões Flask — **defina um valor seguro em produção** |
| `FLASK_DEBUG` | `false` | `true` para ativar o modo debug do Flask |

```bash
SECRET_KEY="chave-segura-aleatoria" FLASK_DEBUG=true python app.py
```

---

## Estrutura do projeto

```
system_sgdi_legacy_student/
├── app.py                    # Rotas, lógica, APIs REST, exportações, Swagger
├── database.py               # Schema, migrations automáticas, seed de dados
├── init_db.py                # Script de inicialização do banco
├── requirements.txt          # Dependências Python
├── gerar_relatorio_ia.py     # Gerador do relatório técnico de uso de IA (PDF)
├── test_report.py            # Suite de testes automatizados + relatório PDF
├── demandas.db               # Banco SQLite (gerado em runtime)
├── static/
│   ├── style.css             # Design system completo — todos os componentes
│   └── ui.js                 # Filtros, paginação e interações client-side
└── templates/
    ├── base.html             # Layout base: navbar, badge de alertas, CSRF
    ├── login.html            # Tela de login (standalone)
    ├── dashboard.html        # Dashboard gerencial com Chart.js e APIs JSON
    ├── index.html            # Lista de demandas abertas
    ├── concluidas.html       # Histórico de demandas concluídas/canceladas
    ├── nova_demanda.html     # Formulário de criação (SLA + responsável)
    ├── editar.html           # Edição de demanda (SLA + responsável)
    ├── detalhes.html         # Detalhe completo + histórico de status + ações
    ├── usuarios.html         # Rastreabilidade por usuário
    └── api_keys.html         # Gestão de chaves de API
```

### Rotas registradas

| Rota | Método | Descrição |
|---|---|---|
| `/` e `/dashboard` | GET | Dashboard gerencial (rota inicial) |
| `/demandas` | GET | Lista de demandas abertas |
| `/concluidas` | GET | Lista de demandas concluídas |
| `/nova_demanda` | GET/POST | Criar nova demanda |
| `/editar/<id>` | GET/POST | Editar demanda |
| `/detalhes/<id>` | GET | Detalhe da demanda |
| `/concluir/<id>` | POST | Marcar como concluída |
| `/reabrir/<id>` | POST | Reabrir demanda |
| `/andamento/<id>` | POST | Marcar como em andamento |
| `/cancelar/<id>` | POST | Cancelar demanda |
| `/deletar/<id>` | POST | Excluir demanda |
| `/adicionar_comentario/<id>` | POST | Adicionar comentário |
| `/buscar` | GET | Busca em demandas abertas |
| `/usuarios` | GET | Rastreabilidade por usuário |
| `/login` | GET/POST | Autenticação |
| `/logout` | POST | Encerrar sessão |
| `/api/keys` | GET/POST | Gestão de API Keys (login obrigatório) |
| `/apidocs` | GET | Documentação Swagger interativa |
| `/api/alerts/count` | GET (JSON) | Contagem de críticas atrasadas (badge) |
| `/api/dashboard/data` | GET (JSON) | KPIs + gráficos + críticas consolidados |
| `/api/dashboard/export` | GET (file) | Exportação geral CSV/PDF/Excel |
| `/api/dashboard/critical-overdue` | GET (JSON) | Críticas com SLA vencido |
| `/api/dashboard/critical-overdue/export` | GET (file) | Exportação de críticas CSV/PDF/Excel |
| `/api/v1/demandas` | GET/POST | API externa — listar e criar demandas |
| `/api/v1/demandas/<id>` | GET | API externa — detalhe de demanda |
| `/api/v1/demandas/<id>/status` | PATCH | API externa — atualizar status |
| `/api/v1/demandas/<id>/comentarios` | GET/POST | API externa — comentários |
| `/api/v1/usuarios` | GET | API externa — listar usuários |

---

## Testes automatizados

### Suite de testes + relatório PDF (`test_report.py`)

Executa casos de teste distribuídos em suites, captura screenshots de cada passo e gera `SGDI_Relatorio_Testes.pdf`.

```bash
playwright install chromium
python test_report.py
```

| Suite | Escopo |
|---|---|
| TS1 | Autenticação (login/logout) |
| TS2 | Criação e validação de demandas |
| TS3 | Edição e controle de acesso |
| TS4 | Filtros, busca e ordenação |
| TS5 | Detalhe, comentários e rastreabilidade |
| TS6 | Responsividade mobile |

---

## Reiniciar o banco do zero

```bash
# Windows
del demandas.db

# Linux / macOS
rm demandas.db

python init_db.py
```

---

## Dependências principais

| Biblioteca | Versão mínima | Uso |
|---|---|---|
| Flask | 3.1.0 | Framework web |
| Werkzeug | 3.1.0 | Hash de senhas bcrypt |
| openpyxl | 3.1.0 | Exportação Excel (.xlsx) |
| reportlab | 4.0.0 | Exportação PDF |
| flasgger | 0.9.7 | Swagger UI e documentação OpenAPI |
| playwright | 1.44.0 | Testes automatizados com browser |
| Pillow | 10.0.0 | Processamento de imagens nos testes |

---

*SGDI v2.0 — Sistema de Gestão de Demandas Internas · Desafio da Tecnologia · 2026*
