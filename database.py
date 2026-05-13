import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash


DB_PATH = "demandas.db"

PRIORIDADE_CRITICA = "Crítica"
PRIORIDADE_ALTA = "Alta"
PRIORIDADE_MEDIA = "Média"
PRIORIDADE_BAIXA = "Baixa"
PRIORIDADES = [PRIORIDADE_CRITICA, PRIORIDADE_ALTA, PRIORIDADE_MEDIA, PRIORIDADE_BAIXA]

STATUS_ABERTA = "Aberta"
STATUS_EM_ANDAMENTO = "Em andamento"
STATUS_CONCLUIDA = "Concluída"
STATUS_CANCELADA = "Cancelada"
TODOS_STATUS = [STATUS_ABERTA, STATUS_EM_ANDAMENTO, STATUS_CONCLUIDA, STATUS_CANCELADA]

PRIORIDADE_SLUGS = {
    PRIORIDADE_CRITICA: "critica",
    PRIORIDADE_ALTA: "alta",
    PRIORIDADE_MEDIA: "media",
    PRIORIDADE_BAIXA: "baixa",
}

PRIORIDADE_ORDEM_SQL = (
    "CASE d.prioridade "
    f"WHEN '{PRIORIDADE_CRITICA}' THEN 1 "
    f"WHEN '{PRIORIDADE_ALTA}' THEN 2 "
    f"WHEN '{PRIORIDADE_MEDIA}' THEN 3 "
    f"WHEN '{PRIORIDADE_BAIXA}' THEN 4 "
    "ELSE 5 END"
)

# Usuários fixos para testes — altere as senhas antes de produção
USUARIOS_FIXOS = [
    {"username": "admin",        "nome": "Administrador",  "senha": "Admin@2024"},
    {"username": "joao.silva",   "nome": "João Silva",     "senha": "Joao@2024"},
    {"username": "maria.santos", "nome": "Maria Santos",   "senha": "Maria@2024"},
    {"username": "pedro.costa",  "nome": "Pedro Costa",    "senha": "Pedro@2024"},
    {"username": "ana.lima",     "nome": "Ana Lima",       "senha": "Ana@2024"},
]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(seed=False):
    conn = get_db_connection()
    try:
        _create_tables(conn)
        _seed_users(conn)
        _migrate_demands(conn)
        _cleanup_legacy_demands(conn)
        seeded = _seed_sample_data(conn) if seed else False
        conn.commit()
        return seeded
    finally:
        conn.close()


def _create_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            senha_hash TEXT NOT NULL
        )
        """
    )

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS demandas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            solicitante TEXT NOT NULL,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            prioridade TEXT NOT NULL DEFAULT '{PRIORIDADE_MEDIA}',
            status TEXT NOT NULL DEFAULT '{STATUS_ABERTA}',
            data_criacao TEXT NOT NULL,
            data_prevista TEXT,
            data_conclusao TEXT,
            responsavel_id INTEGER REFERENCES usuarios(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demanda_id INTEGER NOT NULL REFERENCES demandas(id) ON DELETE CASCADE,
            status_anterior TEXT,
            status_novo TEXT NOT NULL,
            autor TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demanda_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            autor TEXT NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE
        )
        """
    )


def _seed_users(conn):
    for u in USUARIOS_FIXOS:
        exists = conn.execute(
            "SELECT 1 FROM usuarios WHERE username = ?", (u["username"],)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO usuarios (username, nome, senha_hash) VALUES (?, ?, ?)",
                (u["username"], u["nome"], generate_password_hash(u["senha"])),
            )


def _migrate_demands(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(demandas)").fetchall()
    }

    if "prioridade" not in columns:
        conn.execute(
            f"ALTER TABLE demandas ADD COLUMN prioridade TEXT NOT NULL DEFAULT '{PRIORIDADE_MEDIA}'"
        )

    if "usuario_id" not in columns:
        conn.execute(
            "ALTER TABLE demandas ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)"
        )

    if "data_prevista" not in columns:
        conn.execute("ALTER TABLE demandas ADD COLUMN data_prevista TEXT")
        conn.execute(
            "UPDATE demandas SET data_prevista = datetime(data_criacao, '+30 days') "
            "WHERE data_prevista IS NULL AND data_criacao IS NOT NULL"
        )

    if "data_conclusao" not in columns:
        conn.execute("ALTER TABLE demandas ADD COLUMN data_conclusao TEXT")
        conn.execute(
            f"UPDATE demandas SET data_conclusao = datetime(data_criacao, '+14 days') "
            f"WHERE status = '{STATUS_CONCLUIDA}' AND data_conclusao IS NULL"
        )

    if "responsavel_id" not in columns:
        conn.execute(
            "ALTER TABLE demandas ADD COLUMN responsavel_id INTEGER REFERENCES usuarios(id)"
        )

    # Normaliza prioridades inválidas
    conn.execute(
        "UPDATE demandas SET prioridade = ? WHERE prioridade IS NULL OR TRIM(prioridade) = ''",
        (PRIORIDADE_MEDIA,),
    )
    conn.execute(
        "UPDATE demandas SET prioridade = ? WHERE prioridade IN ('Urgente', 'urgente')",
        (PRIORIDADE_ALTA,),
    )
    conn.execute(
        "UPDATE demandas SET prioridade = ? WHERE prioridade NOT IN (?, ?, ?, ?)",
        (PRIORIDADE_MEDIA, *PRIORIDADES),
    )

    # Normaliza status inválidos
    conn.execute(
        "UPDATE demandas SET status = ? WHERE status IS NULL OR TRIM(status) = ''",
        (STATUS_ABERTA,),
    )
    conn.execute(
        "UPDATE demandas SET status = ? WHERE status GLOB 'Conclu*'",
        (STATUS_CONCLUIDA,),
    )
    conn.execute(
        "UPDATE demandas SET status = ? WHERE status NOT IN (?, ?, ?, ?)",
        (STATUS_ABERTA, STATUS_ABERTA, STATUS_EM_ANDAMENTO, STATUS_CONCLUIDA, STATUS_CANCELADA),
    )


def _cleanup_legacy_demands(conn):
    conn.execute("DELETE FROM demandas WHERE usuario_id IS NULL")


def authenticate_user(username, senha):
    conn = get_db_connection()
    try:
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()

    if usuario and check_password_hash(usuario["senha_hash"], senha):
        return usuario
    return None


def get_all_users_with_stats():
    conn = get_db_connection()
    try:
        return conn.execute(
            """
            SELECT
                u.id,
                u.username,
                u.nome,
                COUNT(d.id) AS total,
                SUM(CASE WHEN d.status = ? THEN 1 ELSE 0 END) AS abertas,
                SUM(CASE WHEN d.status = ? THEN 1 ELSE 0 END) AS concluidas,
                SUM(CASE WHEN d.status = ? AND d.prioridade = ? THEN 1 ELSE 0 END) AS alta_abertas
            FROM usuarios u
            LEFT JOIN demandas d ON d.usuario_id = u.id
            GROUP BY u.id
            ORDER BY u.nome
            """,
            (STATUS_ABERTA, STATUS_CONCLUIDA, STATUS_ABERTA, PRIORIDADE_ALTA),
        ).fetchall()
    finally:
        conn.close()


def _seed_sample_data(conn):
    total = conn.execute("SELECT COUNT(*) FROM demandas").fetchone()[0]
    if total:
        return False

    users = {
        row["username"]: row["id"]
        for row in conn.execute("SELECT id, username FROM usuarios").fetchall()
    }

    if not users:
        return False

    # titulo, descricao, solicitante, usuario_id, prioridade, status,
    # data_criacao, data_prevista, data_conclusao
    demandas = [
        (
            "Sistema de pagamentos fora do ar",
            "Módulo de pagamentos não processa transações desde as 18h. Clientes reportando falhas em massa.",
            "João Silva", users.get("joao.silva"), PRIORIDADE_CRITICA, STATUS_ABERTA,
            "2025-04-20 18:00:00", "2025-04-21 06:00:00", None,
        ),
        (
            "Vazamento de dados detectado",
            "Logs indicam acesso não autorizado a dados de clientes nas últimas 24h. Auditoria iniciada.",
            "Administrador", users.get("admin"), PRIORIDADE_CRITICA, STATUS_EM_ANDAMENTO,
            "2025-04-15 09:00:00", "2025-04-16 18:00:00", None,
        ),
        (
            "Servidor de produção instável",
            "CPU acima de 95% nas últimas 6 horas sem causa identificada. Risco de queda total.",
            "Pedro Costa", users.get("pedro.costa"), PRIORIDADE_CRITICA, STATUS_ABERTA,
            "2025-05-01 07:00:00", "2025-05-01 12:00:00", None,
        ),
        (
            "Corrigir bug no módulo de login",
            "Usuários não conseguem fazer login após a última atualização do sistema.",
            "João Silva", users.get("joao.silva"), PRIORIDADE_ALTA, STATUS_ABERTA,
            "2025-03-15 10:30:00", "2025-04-15 10:30:00", None,
        ),
        (
            "Implementar relatório de vendas",
            "Precisamos de um relatório mensal de vendas por categoria para a diretoria.",
            "Maria Santos", users.get("maria.santos"), PRIORIDADE_ALTA, STATUS_EM_ANDAMENTO,
            "2025-03-01 14:20:00", "2025-06-01 14:20:00", None,
        ),
        (
            "Revisar política de acesso",
            "Definir permissões corretas por perfil de usuário conforme requisitos de compliance.",
            "Administrador", users.get("admin"), PRIORIDADE_ALTA, STATUS_CONCLUIDA,
            "2025-01-19 08:45:00", "2025-02-28 08:45:00", "2025-02-20 15:30:00",
        ),
        (
            "Migração do banco de dados",
            "Migrar dados do banco legado para novo formato normalizado sem downtime.",
            "Pedro Costa", users.get("pedro.costa"), PRIORIDADE_ALTA, STATUS_CONCLUIDA,
            "2025-01-10 09:00:00", "2025-02-10 09:00:00", "2025-02-05 14:00:00",
        ),
        (
            "Atualizar dependências de segurança",
            "CVE crítico identificado nas bibliotecas de autenticação. Patch disponível.",
            "Ana Lima", users.get("ana.lima"), PRIORIDADE_ALTA, STATUS_ABERTA,
            "2025-04-28 11:00:00", "2025-05-05 11:00:00", None,
        ),
        (
            "Melhorar performance do sistema",
            "Sistema está lento nas horas de pico. Investigar gargalos no banco de dados.",
            "Pedro Costa", users.get("pedro.costa"), PRIORIDADE_MEDIA, STATUS_ABERTA,
            "2025-02-17 09:15:00", "2025-04-17 09:15:00", None,
        ),
        (
            "Adicionar filtros avançados na listagem",
            "Usuários querem filtrar demandas por data, responsável e categoria de forma combinada.",
            "Ana Lima", users.get("ana.lima"), PRIORIDADE_MEDIA, STATUS_CONCLUIDA,
            "2025-01-18 11:00:00", "2025-02-18 11:00:00", "2025-02-15 16:00:00",
        ),
        (
            "Relatório mensal automático",
            "Gerar e enviar relatório para gestores automaticamente todo dia 1 do mês.",
            "Maria Santos", users.get("maria.santos"), PRIORIDADE_MEDIA, STATUS_EM_ANDAMENTO,
            "2025-02-01 10:00:00", "2025-07-01 10:00:00", None,
        ),
        (
            "Criar tela de auditoria de logs",
            "Tela para visualizar logs de ações dos usuários com filtro por período e tipo.",
            "Administrador", users.get("admin"), PRIORIDADE_MEDIA, STATUS_ABERTA,
            "2025-01-10 14:00:00", "2025-03-10 14:00:00", None,
        ),
        (
            "Integração com sistema de RH",
            "Sincronizar dados de colaboradores com sistema legado do RH via API REST.",
            "João Silva", users.get("joao.silva"), PRIORIDADE_MEDIA, STATUS_CANCELADA,
            "2024-11-01 09:00:00", "2025-01-01 09:00:00", None,
        ),
        (
            "Documentar API interna",
            "Criar documentação Swagger completa para todos os endpoints da API interna.",
            "Ana Lima", users.get("ana.lima"), PRIORIDADE_MEDIA, STATUS_CONCLUIDA,
            "2024-12-15 10:00:00", "2025-01-15 10:00:00", "2025-01-10 17:00:00",
        ),
        (
            "Atualizar manual do usuário",
            "Manual está desatualizado com as novas funcionalidades lançadas no último trimestre.",
            "Maria Santos", users.get("maria.santos"), PRIORIDADE_BAIXA, STATUS_ABERTA,
            "2025-02-01 09:00:00", "2025-04-01 09:00:00", None,
        ),
        (
            "Refatorar módulo de notificações",
            "Código legado com muita duplicação e ausência de testes automatizados.",
            "Pedro Costa", users.get("pedro.costa"), PRIORIDADE_BAIXA, STATUS_CANCELADA,
            "2024-10-20 11:00:00", "2024-12-20 11:00:00", None,
        ),
        (
            "Criar atalhos de teclado na interface",
            "Usuários avançados solicitaram suporte a atalhos de teclado para agilizar navegação.",
            "João Silva", users.get("joao.silva"), PRIORIDADE_BAIXA, STATUS_ABERTA,
            "2025-03-15 14:00:00", "2025-09-15 14:00:00", None,
        ),
        (
            "Otimizar imagens do sistema",
            "Imagens com resolução alta aumentam o tempo de carregamento das páginas em mobile.",
            "Ana Lima", users.get("ana.lima"), PRIORIDADE_BAIXA, STATUS_CONCLUIDA,
            "2024-12-01 10:00:00", "2025-01-01 10:00:00", "2024-12-20 16:00:00",
        ),
        (
            "Implementar modo escuro",
            "Usuários solicitaram suporte a tema escuro para uso em ambientes com pouca luz.",
            "Pedro Costa", users.get("pedro.costa"), PRIORIDADE_BAIXA, STATUS_ABERTA,
            "2025-04-01 09:00:00", "2025-12-01 09:00:00", None,
        ),
        (
            "Revisar textos de mensagens de erro",
            "Mensagens de erro muito técnicas e confusas para usuários não técnicos do sistema.",
            "Maria Santos", users.get("maria.santos"), PRIORIDADE_BAIXA, STATUS_ABERTA,
            "2025-01-20 11:00:00", "2025-03-20 11:00:00", None,
        ),
    ]

    conn.executemany(
        """
        INSERT INTO demandas (
            titulo, descricao, solicitante, usuario_id,
            prioridade, status, data_criacao, data_prevista, data_conclusao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        demandas,
    )

    # Assign sample responsaveis for richer demo data
    user_ids = sorted(users.values())
    for i, d in enumerate(
        conn.execute("SELECT id, usuario_id FROM demandas ORDER BY id").fetchall()
    ):
        cand = user_ids[i % len(user_ids)]
        if cand == d["usuario_id"] and len(user_ids) > 1:
            cand = user_ids[(i + 1) % len(user_ids)]
        conn.execute("UPDATE demandas SET responsavel_id = ? WHERE id = ?", (cand, d["id"]))

    demanda_id = conn.execute(
        "SELECT id FROM demandas WHERE titulo = 'Sistema de pagamentos fora do ar'"
    ).fetchone()
    if demanda_id:
        conn.executemany(
            "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
            [
                (demanda_id["id"], "Investigando as causas. Gateway de pagamento parece instável.", "João Silva", "2025-04-20 18:30:00"),
                (demanda_id["id"], "Gateway confirma instabilidade na infraestrutura deles. Escalando para o fornecedor.", "Administrador", "2025-04-20 19:00:00"),
                (demanda_id["id"], "Solução temporária ativada via roteamento alternativo. Aguardando retorno do fornecedor.", "João Silva", "2025-04-20 20:00:00"),
            ],
        )
    return True
