import sqlite3


conn = sqlite3.connect('demandas.db')
cursor = conn.cursor()

cursor.execute('PRAGMA foreign_keys = ON')

cursor.execute('''
CREATE TABLE IF NOT EXISTS demandas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    solicitante TEXT NOT NULL,
    prioridade TEXT NOT NULL DEFAULT 'Média',
    status TEXT NOT NULL DEFAULT 'Aberta',
    data_criacao TEXT NOT NULL
)
''')


cursor.execute('''
CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id INTEGER NOT NULL,
    comentario TEXT NOT NULL,
    autor TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE
)
''')


cursor.execute("INSERT INTO demandas (titulo, descricao, solicitante, prioridade, status, data_criacao) VALUES ('Corrigir bug no login', 'Usuários não conseguem fazer login', 'João Silva', 'Urgente', 'Aberta', '2024-01-15 10:30:00')")
cursor.execute("INSERT INTO demandas (titulo, descricao, solicitante, prioridade, status, data_criacao) VALUES ('Implementar relatório de vendas', 'Precisamos de um relatório mensal', 'Maria Santos', 'Alta', 'Aberta', '2024-01-16 14:20:00')")
cursor.execute("INSERT INTO demandas (titulo, descricao, solicitante, prioridade, status, data_criacao) VALUES ('Melhorar performance', 'Sistema está lento', 'Pedro Costa', 'Média', 'Aberta', '2024-01-17 09:15:00')")
cursor.execute("INSERT INTO demandas (titulo, descricao, solicitante, prioridade, status, data_criacao) VALUES ('Adicionar filtros', 'Usuários querem filtrar demandas', 'Ana Lima', 'Média', 'Concluída', '2024-01-18 11:00:00')")

cursor.execute("INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (1, 'Vou investigar esse bug', 'Tech Team', '2024-01-15 11:00:00')")
cursor.execute("INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (1, 'Bug corrigido na branch develop', 'Desenvolvedor', '2024-01-15 16:30:00')")

conn.commit()
conn.close()

print("Banco de dados criado com sucesso!")
