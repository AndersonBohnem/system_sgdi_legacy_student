# SGDI — Sistema de Gestão de Demandas Internas

Sistema web em Flask para gerenciar demandas internas com controle de acesso por papel (RBAC), priorização, rastreabilidade completa, auditoria enterprise com cadeia de hashes, API REST documentada (Swagger) e dashboard gerencial interativo.

---

## Sumário

1. [Pré-requisitos](#pré-requisitos)
2. [Como rodar](#como-rodar)
3. [Usuários de teste](#usuários-de-teste)
4. [Funcionalidades](#funcionalidades)
5. [Dashboard Gerencial](#dashboard-gerencial)
6. [Auditoria e Logs](#auditoria-e-logs)
7. [API REST](#api-rest)
8. [Banco de dados](#banco-de-dados)
9. [Segurança](#segurança)
10. [Variáveis de ambiente](#variáveis-de-ambiente)
11. [Estrutura do projeto](#estrutura-do-projeto)
12. [Rotas registradas](#rotas-registradas)
13. [Testes automatizados](#testes-automatizados)
14. [Documentos técnicos](#documentos-técnicos)

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

Cria o arquivo `demandas.db`, as 7 tabelas, os 5 usuários de teste e 20 demandas de exemplo com comentários, responsáveis e histórico de status.

### 5. Inicie o servidor

```bash
python app.py
```

### 6. Acesse o sistema

Abra o navegador em **http://localhost:5000** — redireciona automaticamente para o **Dashboard Gerencial**.

---

## Usuários de teste

| Usuário | Senha | Papel |
|---|---|---|
| `admin` | `Admin@2024` | Administrador — acesso total |
| `joao.silva` | `Joao@2024` | Gerente |
| `maria.santos` | `Maria@2024` | Responsável |
| `pedro.costa` | `Pedro@2024` | Solicitante |
| `ana.lima` | `Ana@2024` | Solicitante |

---

## Funcionalidades

### Autenticação e Sessão

- Login com usuário e senha (hash **PBKDF2-SHA256**, 260.000 iterações)
- Sessão do lado do servidor — todas as páginas exigem login via `@login_required`
- Proteção **CSRF** em todos os formulários POST (token `secrets.token_hex(32)` por sessão)
- **Brute-force protection**: bloqueio automático após 5 tentativas falhas em 5 minutos
- Botão "Sair" encerra a sessão e invalida o token CSRF
- Após login, redireciona para o Dashboard Gerencial

### Controle de Acesso por Papel (RBAC)

| Papel | Permissões |
|---|---|
| `admin` | Tudo: criar, editar, excluir, gerenciar usuários, API Keys, auditoria completa |
| `gerente` | Ver, criar, editar status, exportar, dashboard completo |
| `responsavel` | Ver e atualizar status das demandas atribuídas |
| `solicitante` | Criar demandas, ver as próprias |

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
- Registro automático de `None → Aberta` no histórico de status

### Editar demanda (`/editar/<id>`)

- Apenas o solicitante original pode editar (verificado no servidor)
- Campos editáveis: título, descrição, prioridade, prazo previsto, responsável
- Acesso bloqueado com redirecionamento e mensagem para outros usuários

### Detalhe da demanda (`/detalhes/<id>`)

- Visualização completa: descrição, metadados, status, solicitante, responsável
- **Ações contextuais por status:**
  - **Aberta:** Iniciar andamento · Concluir · Cancelar · Editar (se solicitante)
  - **Em andamento:** Concluir · Cancelar · Reabrir
  - **Concluída / Cancelada:** Reabrir
- Histórico de comentários em ordem cronológica
- Formulário de novo comentário com autor preenchido automaticamente
- **Histórico de status:** timeline completa de todas as transições com autor e timestamp
- **Acesso registrado em auditoria:** cada visualização gera evento `demanda_visualizada`

### Transições de Status

Toda mudança de status é registrada na tabela `historico_status` e na auditoria:

| De | Para | Rota |
|---|---|---|
| — | Aberta | Criação da demanda |
| Aberta | Em andamento | `/andamento/<id>` |
| Aberta / Em andamento | Concluída | `/concluir/<id>` |
| Aberta / Em andamento | Cancelada | `/cancelar/<id>` |
| Concluída / Cancelada | Aberta | `/reabrir/<id>` |

### Busca (`/buscar`)

- Busca em demandas abertas por título, descrição ou solicitante
- Filtros de prioridade e ordenação
- Metacaracteres SQL (`%`, `_`) tratados corretamente

### Usuários (`/usuarios`)

- Painel com todos os usuários cadastrados
- Por usuário: total de demandas, abertas, concluídas, alta prioridade
- Barra de progresso de demandas abertas

---

## Dashboard Gerencial

O Dashboard (`/dashboard`) é a **tela inicial** do sistema. Atualiza automaticamente a cada 60 segundos via API JSON.

### KPIs em tempo real

| Indicador | Descrição |
|---|---|
| Total de Demandas | Contagem geral com os filtros ativos |
| Abertas | Com percentual do total |
| Em Andamento | Demandas em execução |
| Concluídas | Com percentual do total |
| Atrasadas (SLA) | Status não-final com prazo vencido |
| Prioridade Crítica | Com contagem das atrasadas |
| Tempo Médio de Resolução | Média ponderada por criticidade (dias) |

### Gráficos (Chart.js 4.x)

- **Donut** — distribuição por status com percentuais
- **Barras horizontais** — volume por prioridade
- **Linha de evolução temporal** — demandas criadas vs. concluídas (diário / semanal / mensal)

### Filtros

Todos os dados (KPIs, gráficos, tabelas, críticas) respondem aos filtros:

| Filtro | Opções |
|---|---|
| Período | Todos · Hoje · Últimos 7 dias · Último mês · Personalizado |
| Responsável | Qualquer usuário cadastrado |
| Prioridade | Crítica · Alta · Média · Baixa |
| Status | Aberta · Em andamento · Concluída · Cancelada |

### Seção Críticas e Atrasadas

Destaque visual para demandas com prioridade Crítica e SLA vencido:

- Tabela com: ID · Título · Responsável · Solicitante · Dias Atrasados · SLA Previsto · Status
- Exportação dedicada em **CSV**, **PDF** e **Excel**

### Badges de Alerta na Navbar

Dois badges atualizados a cada 60 segundos via `/api/alerts/count`:

| Badge | Posição | Condição |
|---|---|---|
| Amarelo | Ao lado de "Dashboard" | Demandas críticas com SLA vencido |
| Vermelho | Ao lado de "Auditoria" | Erros/críticos de segurança nas últimas 24h |

### Exportação

| Escopo | Formatos | Rota |
|---|---|---|
| Críticas + Atrasadas | CSV · PDF · Excel | `/api/dashboard/critical-overdue/export` |
| Todas as demandas (filtros ativos) | CSV · PDF · Excel | `/api/dashboard/export` |

---

## Auditoria e Logs

O módulo de auditoria (`/auditoria`) registra **todos os eventos** do sistema com rastreabilidade completa, cadeia de hashes tamper-evident e painel de métricas.

### Destinos de Log

| Destino | Arquivo / Tabela | Conteúdo | Retenção |
|---|---|---|---|
| SQLite | `logs_sistema` | Todos os eventos + hash chain | Por categoria |
| Arquivo geral | `logs/sgdi.log` | Todos os eventos INFO+ | Rotativo 5 MB × 5 backups |
| Arquivo segurança | `logs/security.log` | CRITICAL, ERROR, falhas de auth | Rotativo 5 MB × 5 backups |
| Arquivo API | `logs/api_access.log` | Apenas chamadas REST | Rotativo 5 MB × 5 backups |

### Cadeia de Hashes (Integridade)

Cada registro em `logs_sistema` carrega um **hash SHA-256 encadeado**: `SHA256(conteudo + hash_anterior)`. Qualquer adulteração direta no banco invalida a cadeia. O endpoint `/api/admin/integridade` verifica os últimos 500 registros sob demanda.

### Política de Retenção por Categoria

| Categoria | Retenção | Justificativa |
|---|---|---|
| AUTH, SEGURANÇA, API_KEY | 365 dias | Compliance e investigação forense |
| DEMANDA, EXPORTAÇÃO, USUÁRIO | 180 dias | Histórico de negócio |
| SISTEMA | 90 dias | Diagnóstico operacional |
| API | 30 dias | Volume alto — rotação rápida |

### Painel de Métricas

A página `/auditoria` inclui um painel colapsável com três gráficos Chart.js:
- **Pizza** — distribuição por nível (INFO / WARNING / ERROR / CRITICAL)
- **Barras** — distribuição por categoria
- **Linha** — atividade dos últimos 7 dias

### Filtros e Exportação

- Filtre por nível, categoria, data, usuário e ação
- Exporte em **CSV** ou **Excel** (`.xlsx` com linhas coloridas por severidade):
  - CRITICAL → vermelho forte | ERROR → vermelho claro | WARNING → amarelo

### As 10 Melhorias Implementadas

| # | Melhoria |
|---|---|
| 1 | Badge de segurança vermelho na navbar (erros das últimas 24h) |
| 2 | Log de visualização de demanda (`demanda_visualizada`) |
| 3 | Verificação de integridade automática na inicialização |
| 4 | Sanitização de campos sensíveis (`senha`, `token`, `key`, etc.) |
| 5 | Endpoint `/api/auditoria/metricas` com agregados JSON |
| 6 | Endpoint `/api/admin/integridade` para verificação sob demanda |
| 7 | Painel de métricas com Chart.js na página de auditoria |
| 8 | Exportação Excel da auditoria com coloração por severidade |
| 9 | Rotação de logs por tamanho (5 MB × 5 backups) |
| 10 | Política de retenção diferenciada por categoria |

---

## API REST

O SGDI disponibiliza uma API REST para integração com sistemas externos, autenticada por **API Key**.

### Gerar chave (`/api/keys`)

1. Faça login no sistema
2. Acesse **API Keys** na navbar
3. Informe uma descrição (ex: "Integração ERP") e clique em **Gerar chave**
4. Copie a chave exibida — ela **não será mostrada novamente** (apenas o hash SHA-256 é armazenado)

### Autenticação

```http
GET /api/v1/demandas HTTP/1.1
Host: localhost:5000
X-API-Key: sua-chave-aqui
```

| Situação | Código |
|---|---|
| Chave ausente | 401 |
| Chave inválida ou revogada | 403 |
| Limite de requisições excedido | 429 |
| Sucesso | 200 / 201 |

> **Rate limiting:** 60 requisições/minuto por chave (in-memory).

### Endpoints disponíveis

#### Demandas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/demandas` | Lista demandas (filtros: status, prioridade, responsavel_id, limit, offset) |
| `POST` | `/api/v1/demandas` | Cria nova demanda |
| `GET` | `/api/v1/demandas/<id>` | Detalhe completo de uma demanda |
| `PATCH` | `/api/v1/demandas/<id>/status` | Atualiza status (registra no histórico) |
| `GET` | `/api/v1/demandas/<id>/comentarios` | Lista comentários |
| `POST` | `/api/v1/demandas/<id>/comentarios` | Adiciona comentário |

#### Outros

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/usuarios` | Lista usuários ativos |
| `GET` | `/api/alerts/count` | Contadores de alertas (criticas_atrasadas, alertas_seguranca) |
| `GET` | `/api/dashboard/kpis` | KPIs do dashboard |
| `GET` | `/api/dashboard/charts` | Dados dos gráficos |
| `GET` | `/api/auditoria/metricas` | Métricas de auditoria (agregados JSON) |
| `GET` | `/api/admin/integridade` | Verifica cadeia de hashes (apenas admin) |

### Formato de resposta

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

Interface interativa disponível em **`/apidocs`** — lista todos os endpoints com parâmetros, schemas e botão "Try it out".

---

## Banco de dados

- Arquivo: `demandas.db` (SQLite, criado automaticamente)
- `PRAGMA foreign_keys = ON` ativo em todas as conexões
- Migrations automáticas via `PRAGMA table_info()` — nunca destrói dados existentes

### Tabelas

| Tabela | Descrição |
|---|---|
| `usuarios` | Usuários com username, nome, papel e hash de senha PBKDF2 |
| `demandas` | Core: título, descrição, prioridade, status, solicitante, responsável, SLA |
| `comentarios` | Comentários vinculados a demandas |
| `historico_status` | Log auditável de toda transição de status com autor e timestamp |
| `api_keys` | Chaves de API (hash SHA-256, descrição, criador, expiração, flag ativa) |
| `logs_sistema` | Audit trail completo com hash chain encadeado |
| `alertas` | Alertas gerados pelo sistema para notificação no dashboard |

---

## Segurança

| Controle | Implementação |
|---|---|
| Autenticação | Session + PBKDF2-SHA256 (260.000 iterações) |
| Autorização | RBAC — verificado por rota e por recurso |
| CSRF | Token `secrets.token_hex(32)` em sessão, verificado em todo POST |
| SQL Injection | Queries 100% parametrizadas (`?` placeholder) |
| XSS | Jinja2 auto-escape em todos os templates |
| Brute Force | Bloqueio após 5 falhas em 5 min (contador em `logs_sistema`) |
| Rate Limiting | 60 req/min por API key (in-memory com `threading.Lock`) |
| Dados sensíveis em logs | `_sanitizar()` mascara senha/token/key recursivamente |
| Integridade de logs | SHA-256 hash chain em `logs_sistema` |
| Expiração de chaves | Campo `expira_em` em `api_keys` |
| Rotação de logs | `RotatingFileHandler` 5 MB × 5 backups |
| Retenção diferenciada | Purga por categoria (30–365 dias) |

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | valor fixo de desenvolvimento | Chave para assinar sessões Flask — **defina valor seguro em produção** |
| `DB_PATH` | `demandas.db` | Caminho para o arquivo SQLite |
| `LOG_DIR` | `logs/` | Diretório para arquivos de log rotativos |
| `FLASK_DEBUG` | `false` | `true` para ativar o modo debug |

```bash
SECRET_KEY="chave-segura-aleatoria" python app.py
```

---

## Estrutura do projeto

```
system_sgdi_legacy_student/
├── app.py                        # Rotas, lógica, APIs REST, exportações, Swagger
├── logger.py                     # Camada de auditoria: logging estruturado + hash chain
├── database.py                   # Schema, migrations automáticas, seed de dados
├── init_db.py                    # Script de inicialização do banco
├── requirements.txt              # Dependências Python
├── test_report.py                # Suite de testes automatizados (46 casos)
├── gerar_decisoes.py             # Gerador PDF — 12 ADRs de decisões técnicas
├── gerar_doc_completo.py         # Gerador PDF — documento técnico completo
├── demandas.db                   # Banco SQLite (gerado em runtime)
├── logs/
│   ├── sgdi.log                  # Todos os eventos (rotativo)
│   ├── security.log              # Eventos de segurança e falhas
│   └── api_access.log            # Chamadas REST
├── static/
│   ├── style.css                 # Design system completo
│   └── ui.js                     # Filtros, paginação e interações client-side
└── templates/
    ├── base.html                 # Layout base: navbar, badges de alerta, CSRF
    ├── login.html                # Tela de login
    ├── dashboard.html            # Dashboard com KPIs, Chart.js e APIs JSON
    ├── index.html                # Lista de demandas abertas
    ├── concluidas.html           # Histórico de demandas concluídas/canceladas
    ├── nova_demanda.html         # Formulário de criação
    ├── editar.html               # Edição de demanda
    ├── detalhes.html             # Detalhe completo + histórico + ações
    ├── usuarios.html             # Rastreabilidade por usuário
    ├── auditoria.html            # Logs de auditoria + painel de métricas
    └── api_keys.html             # Gestão de chaves de API
```

---

## Rotas registradas

### Interface Web

| Rota | Método | Descrição |
|---|---|---|
| `/` e `/dashboard` | GET | Dashboard gerencial (tela inicial) |
| `/demandas` | GET | Lista de demandas abertas |
| `/concluidas` | GET | Lista de demandas concluídas/canceladas |
| `/nova_demanda` | GET / POST | Criar nova demanda |
| `/editar/<id>` | GET / POST | Editar demanda |
| `/detalhes/<id>` | GET | Detalhe da demanda |
| `/concluir/<id>` | POST | Marcar como concluída |
| `/reabrir/<id>` | POST | Reabrir demanda |
| `/andamento/<id>` | POST | Marcar como em andamento |
| `/cancelar/<id>` | POST | Cancelar demanda |
| `/deletar/<id>` | POST | Excluir demanda |
| `/adicionar_comentario/<id>` | POST | Adicionar comentário |
| `/buscar` | GET | Busca em demandas abertas |
| `/usuarios` | GET | Rastreabilidade por usuário |
| `/auditoria` | GET | Logs de auditoria com filtros e métricas |
| `/auditoria/export` | GET | Exportar auditoria (`?format=csv` ou `?format=xlsx`) |
| `/api/keys` | GET / POST | Gestão de API Keys (login obrigatório) |
| `/login` | GET / POST | Autenticação |
| `/logout` | POST | Encerrar sessão |
| `/apidocs` | GET | Documentação Swagger interativa |

### APIs JSON (sessão)

| Rota | Descrição |
|---|---|
| `/api/alerts/count` | Contadores de alertas para badges da navbar |
| `/api/dashboard/kpis` | KPIs do dashboard |
| `/api/dashboard/charts` | Dados dos gráficos |
| `/api/dashboard/data` | KPIs + gráficos + críticas consolidados |
| `/api/dashboard/critical-overdue` | Demandas críticas com SLA vencido |
| `/api/dashboard/export` | Exportação geral CSV / PDF / Excel |
| `/api/dashboard/critical-overdue/export` | Exportação de críticas CSV / PDF / Excel |
| `/api/auditoria/metricas` | Métricas de auditoria (agregados JSON) |
| `/api/admin/integridade` | Verificação da cadeia de hashes (apenas admin) |

### API REST Externa (X-API-Key)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/demandas` | Lista demandas (filtros, paginação) |
| POST | `/api/v1/demandas` | Cria nova demanda |
| GET | `/api/v1/demandas/<id>` | Detalhe de demanda |
| PATCH | `/api/v1/demandas/<id>/status` | Atualiza status |
| GET | `/api/v1/demandas/<id>/comentarios` | Lista comentários |
| POST | `/api/v1/demandas/<id>/comentarios` | Adiciona comentário |
| GET | `/api/v1/usuarios` | Lista usuários ativos |

---

## Testes automatizados

```bash
# Instalar driver do browser (apenas na primeira vez)
playwright install chromium

# Executar a suite completa
python test_report.py
```

O servidor deve estar rodando em `http://localhost:5000` antes de executar os testes.

### Resultado

**46/46 casos — 100% PASS**

| Suite | Casos | Tipo | Escopo |
|---|---|---|---|
| TS1 — Autenticação | 5 | E2E | Login sucesso/falha, logout, CSRF, brute force |
| TS2 — Demandas CRUD | 6 | E2E | Criar, listar, detalhar, log de visualização, status, concluir |
| TS3 — Busca / Filtros | 3 | E2E | Busca por texto, filtro por prioridade, resultado vazio |
| TS4 — Exportação | 2 | E2E + HTTP | CSV e Excel — content-type e tamanho |
| TS5 — Usuários | 3 | E2E | Listar, criar, permissão de papel |
| TS6 — Segurança | 3 | E2E | Acesso sem login, CSRF inválido, SQL injection |
| TS7 — Auditoria | 7 | E2E + HTTP | Página, filtros, CSV, Excel, métricas, integridade |
| TS8 — API Keys | 6 | E2E + HTTP | Criar chave, GET/POST REST, chave inválida, sem chave |
| TS9 — Dashboard | 5 | E2E + HTTP | Página, KPIs JSON, charts JSON, alertas, export CSV |
| TS10 — Relatórios | 6 | E2E + HTTP | PDF técnico, relatório gerencial, histórico, responsável |

---

## Documentos técnicos

Dois PDFs de documentação são gerados pelos scripts incluídos:

```bash
# 12 ADRs — decisões arquiteturais com contexto, alternativas e racional
python gerar_decisoes.py
# → decisoes_tecnicas_sgdi.pdf

# Documento técnico completo — todas as implementações (10 seções)
python gerar_doc_completo.py
# → documento_tecnico_completo_sgdi.pdf
```

| Documento | Conteúdo |
|---|---|
| `decisoes_tecnicas_sgdi.pdf` | 12 ADRs: Flask, SQLite, Jinja2 SSR, Sessions vs JWT, PBKDF2, CSRF, Logging, Hash Chain, Rate Limiting, Flasgger, openpyxl, Chart.js |
| `documento_tecnico_completo_sgdi.pdf` | Visão geral, Autenticação, CRUD, Auditoria (10 melhorias), API REST, Dashboard, Testes (46 casos), Segurança, Guia de operação, Roadmap |

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

## Dependências

| Biblioteca | Versão mínima | Uso |
|---|---|---|
| Flask | 3.1.0 | Framework web |
| Werkzeug | 3.1.0 | Hash de senhas PBKDF2 |
| openpyxl | 3.1.0 | Exportação Excel (.xlsx) |
| reportlab | 4.0.0 | Geração de PDFs |
| flasgger | 0.9.7 | Swagger UI e documentação OpenAPI |
| playwright | 1.44.0 | Testes E2E com browser |
| Pillow | 10.0.0 | Processamento de imagens nos testes |

---

*SGDI v2.0 — Sistema de Gestão de Demandas Internas · Desafio da Tecnologia · 2026*
