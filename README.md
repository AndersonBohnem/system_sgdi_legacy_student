# SGDI - Sistema de Gestao de Demandas Internas

Sistema simples em Flask para gerenciar demandas internas da empresa.

## Como rodar

```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

Acesse: http://localhost:5000

## Funcionalidades

- Criar, editar e deletar demandas
- Definir prioridade em `Alta`, `Media` ou `Baixa`
- Filtrar e ordenar demandas abertas por prioridade
- Filtrar e ordenar demandas concluidas por prioridade
- Buscar demandas abertas por titulo, descricao ou solicitante
- Visualizar detalhes e comentarios

## Banco de dados

- `init_db.py` cria as tabelas se necessario
- Bancos antigos sao migrados para incluir a coluna `prioridade`
- Registros antigos com prioridade `Urgente` sao normalizados para `Alta`
- Dados de exemplo so sao inseridos quando a base estiver vazia

## Pendencias

- Melhorar busca avancada
- Adicionar usuarios

*Atualizado em 2026*
