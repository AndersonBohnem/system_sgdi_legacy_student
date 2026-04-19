# SGDI — Sistema de Gestão de Demandas Internas

Sistema web em Flask para gerenciar demandas internas com controle de acesso por usuário, priorização e rastreabilidade completa. Interface minimalista, moderna e totalmente responsiva (mobile-first).

---

## Pré-requisitos

- Python 3.10 ou superior
- pip

---

## Como rodar (passo a passo)

### 1. Clone ou baixe o projeto

```bash
git clone <url-do-repositorio>
cd system_sgdi_legacy_student
```

### 2. Crie e ative um ambiente virtual (recomendado)

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

Este comando cria o banco `demandas.db`, cria as tabelas, registra os 5 usuários de teste e insere dados de exemplo.

### 5. Inicie o servidor

```bash
python app.py
```

### 6. Acesse o sistema

Abra o navegador em: **http://localhost:5000**

Você será redirecionado para a tela de login.

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

### Autenticação
- Tela de login com usuário e senha
- Sessão autenticada — todas as páginas exigem login
- Botão "Sair" no cabeçalho para encerrar a sessão
- Proteção CSRF em todos os formulários POST

### Demandas — Abertas
- Listagem de todas as demandas com status **Aberta**
- Ordenação por prioridade (padrão) ou por data de criação (mais recentes)
- Filtro por prioridade: Alta, Média, Baixa
- Filtro por solicitante (usuário)
- Alerta visual para demandas paradas há mais de 7 dias
- Métricas no topo: total visível, alta prioridade, demandas paradas, visão atual
- Paginação com carregamento em lotes de 6 itens

### Demandas — Concluídas
- Histórico de demandas com status **Concluída**
- Mesmos filtros de prioridade e solicitante das demandas abertas
- Opção de reabrir qualquer demanda concluída

### Criar demanda
- Campos: título, descrição, prioridade
- Solicitante preenchido automaticamente pelo usuário logado (sem digitação manual)
- Validação de campos obrigatórios e prioridade válida

### Editar demanda
- Apenas o solicitante original pode editar a demanda (todos os campos)
- Acesso bloqueado no servidor para outros usuários — redirecionamento com mensagem de erro
- Campos editáveis: título, descrição e prioridade

### Detalhe da demanda
- Visualização completa: descrição, metadados, status, solicitante
- Indicação visual se a demanda pertence ao usuário logado ("você")
- Ações disponíveis: concluir, reabrir, editar, deletar
- Histórico de comentários em ordem cronológica reversa (mais recente primeiro)
- Formulário para adicionar novo comentário — autor preenchido automaticamente pelo usuário logado

### Busca
- Busca em demandas abertas por título, descrição ou nome do solicitante
- Respeita os filtros de prioridade e ordenação ativos
- Metacaracteres SQL (`%`, `_`) tratados corretamente — busca por texto literal

### Rastreabilidade de usuários (`/usuarios`)
- Painel com todos os usuários cadastrados
- Por usuário: total de demandas, abertas, concluídas, alta prioridade abertas
- Barra de progresso mostrando percentual de demandas abertas
- Links diretos para filtrar o painel de abertas ou concluídas por usuário
- Métricas globais no topo: total de usuários, total de abertas, total concluídas, alta prioridade abertas

---

## Banco de dados

- Arquivo: `demandas.db` (SQLite, criado automaticamente)
- `init_db.py` cria as tabelas, migra schemas antigos e insere dados de exemplo se o banco estiver vazio
- Demandas sem vínculo com usuário são removidas automaticamente na inicialização
- Registros legados com prioridade `Urgente` são normalizados para `Alta`

### Tabelas

| Tabela | Descrição |
|---|---|
| `usuarios` | Usuários com username, nome e senha (hash bcrypt) |
| `demandas` | Demandas vinculadas a um usuário (`usuario_id` FK) |
| `comentarios` | Comentários vinculados a uma demanda (`demanda_id` FK) |

---

## Variáveis de ambiente (opcionais)

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | valor fixo de desenvolvimento | Chave para assinar sessões Flask — **defina um valor seguro em produção** |
| `FLASK_DEBUG` | `false` | Define `true` para ativar o modo debug do Flask |

Exemplo:

```bash
SECRET_KEY="chave-segura-aleatoria" FLASK_DEBUG=true python app.py
```

---

## Estrutura do projeto

```
system_sgdi_legacy_student/
├── app.py                      # Rotas, lógica de negócio, autenticação
├── database.py                 # Conexão, schema, migrations, seed
├── init_db.py                  # Script de inicialização do banco
├── requirements.txt            # Dependências Python
├── BUGS.md                     # Relatório de bugs encontrados e corrigidos
├── IMPLEMENTACAO.md            # Notas de implementação e decisões técnicas
├── test_report.py              # Suite de testes automatizados + geração de PDF
├── SGDI_Relatorio_Testes.pdf   # Último relatório de testes gerado
├── demandas.db                 # Banco SQLite (gerado em runtime)
├── test_screenshots/           # Screenshots geradas pelo test_report.py
├── static/
│   ├── style.css               # Estilos completos
│   └── ui.js                   # Filtros e paginação client-side
└── templates/
    ├── base.html               # Layout base com navegação
    ├── login.html              # Página de login (standalone)
    ├── index.html              # Painel de demandas abertas
    ├── concluidas.html         # Histórico de demandas concluídas
    ├── nova_demanda.html
    ├── editar.html
    ├── detalhes.html
    └── usuarios.html           # Rastreabilidade por usuário
```

---

## Testes Automatizados

### Suite de testes + relatório PDF (`test_report.py`)

Executa 27 casos de teste distribuídos em 6 suites (TS1–TS6), captura screenshots de cada passo e gera `SGDI_Relatorio_Testes.pdf`.

```bash
pip install -r requirements.txt
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

O PDF gerado inclui capa, resumo executivo, placar de resultados e detalhamento de cada CT com screenshots salvas em `test_screenshots/`.

---

## Reiniciar o banco do zero

Para apagar todos os dados e recriar com os exemplos:

```bash
rm demandas.db       # Linux/macOS
del demandas.db      # Windows
python init_db.py
```

---

*Atualizado em 2026 — versão 2.0*
