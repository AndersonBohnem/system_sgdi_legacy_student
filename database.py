import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash


DB_PATH = "demandas.db"

PRIORIDADE_ALTA = "Alta"
PRIORIDADE_MEDIA = "Média"
PRIORIDADE_BAIXA = "Baixa"
PRIORIDADES = [PRIORIDADE_ALTA, PRIORIDADE_MEDIA, PRIORIDADE_BAIXA]

STATUS_ABERTA = "Aberta"
STATUS_CONCLUIDA = "Concluída"

PRIORIDADE_SLUGS = {
    PRIORIDADE_ALTA: "alta",
    PRIORIDADE_MEDIA: "media",
    PRIORIDADE_BAIXA: "baixa",
}

PRIORIDADE_ORDEM_SQL = (
    "CASE d.prioridade "
    f"WHEN '{PRIORIDADE_ALTA}' THEN 1 "
    f"WHEN '{PRIORIDADE_MEDIA}' THEN 2 "
    f"WHEN '{PRIORIDADE_BAIXA}' THEN 3 "
    "ELSE 4 END"
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
            data_criacao TEXT NOT NULL
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
        """
        UPDATE demandas
        SET prioridade = ?
        WHERE prioridade NOT IN (?, ?, ?)
        """,
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
        "UPDATE demandas SET status = ? WHERE status NOT IN (?, ?)",
        (STATUS_ABERTA, STATUS_ABERTA, STATUS_CONCLUIDA),
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

    demandas = [
        (
            "Corrigir bug no login",
            "Usuarios nao conseguem fazer login apos a ultima atualizacao.",
            "João Silva",
            users.get("joao.silva"),
            PRIORIDADE_ALTA,
            STATUS_ABERTA,
            "2024-01-15 10:30:00",
        ),
        (
            "Implementar relatorio de vendas",
            "Precisamos de um relatorio mensal de vendas por categoria.",
            "Maria Santos",
            users.get("maria.santos"),
            PRIORIDADE_MEDIA,
            STATUS_ABERTA,
            "2024-01-16 14:20:00",
        ),
        (
            "Melhorar performance",
            "O sistema esta lento nas horas de pico. Investigar gargalos.",
            "Pedro Costa",
            users.get("pedro.costa"),
            PRIORIDADE_BAIXA,
            STATUS_ABERTA,
            "2024-01-17 09:15:00",
        ),
        (
            "Adicionar filtros na listagem",
            "Usuarios querem filtrar demandas por data e responsavel.",
            "Ana Lima",
            users.get("ana.lima"),
            PRIORIDADE_MEDIA,
            STATUS_CONCLUIDA,
            "2024-01-18 11:00:00",
        ),
        (
            "Revisar politica de acesso",
            "Definir permissoes corretas por perfil de usuario.",
            "Administrador",
            users.get("admin"),
            PRIORIDADE_ALTA,
            STATUS_ABERTA,
            "2024-01-19 08:45:00",
        ),
    ]

    conn.executemany(
        """
        INSERT INTO demandas (
            titulo, descricao, solicitante, usuario_id,
            prioridade, status, data_criacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        demandas,
    )

    demanda_id = conn.execute(
        "SELECT id FROM demandas WHERE titulo = 'Corrigir bug no login'"
    ).fetchone()
    if demanda_id:
        conn.executemany(
            "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
            [
                (demanda_id["id"], "Vou investigar esse bug.", "João Silva", "2024-01-15 11:00:00"),
                (demanda_id["id"], "Bug identificado na validacao do token. Corrigindo.", "João Silva", "2024-01-15 16:30:00"),
            ],
        )
    return True
