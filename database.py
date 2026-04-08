import sqlite3


DB_PATH = "demandas.db"

PRIORIDADE_ALTA = "Alta"
PRIORIDADE_MEDIA = "M\u00e9dia"
PRIORIDADE_BAIXA = "Baixa"
PRIORIDADES = [PRIORIDADE_ALTA, PRIORIDADE_MEDIA, PRIORIDADE_BAIXA]

STATUS_ABERTA = "Aberta"
STATUS_CONCLUIDA = "Conclu\u00edda"

PRIORIDADE_SLUGS = {
    PRIORIDADE_ALTA: "alta",
    PRIORIDADE_MEDIA: "media",
    PRIORIDADE_BAIXA: "baixa",
}

PRIORIDADE_ORDEM_SQL = (
    "CASE prioridade "
    f"WHEN '{PRIORIDADE_ALTA}' THEN 1 "
    f"WHEN '{PRIORIDADE_MEDIA}' THEN 2 "
    f"WHEN '{PRIORIDADE_BAIXA}' THEN 3 "
    "ELSE 4 END"
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(seed=False):
    conn = get_db_connection()
    try:
        _create_tables(conn)
        _migrate_demands(conn)
        seeded = _seed_sample_data(conn) if seed else False
        conn.commit()
        return seeded
    finally:
        conn.close()


def _create_tables(conn):
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS demandas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            solicitante TEXT NOT NULL,
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


def _migrate_demands(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(demandas)").fetchall()
    }

    if "prioridade" not in columns:
        conn.execute(
            f"ALTER TABLE demandas ADD COLUMN prioridade TEXT NOT NULL DEFAULT '{PRIORIDADE_MEDIA}'"
        )

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

    conn.execute(
        "UPDATE demandas SET status = ? WHERE status IS NULL OR TRIM(status) = ''",
        (STATUS_ABERTA,),
    )
    conn.execute(
        """
        UPDATE demandas
        SET status = ?
        WHERE status GLOB 'Conclu*'
        """,
        (STATUS_CONCLUIDA,),
    )
    conn.execute(
        """
        UPDATE demandas
        SET status = ?
        WHERE status NOT IN (?, ?)
        """,
        (STATUS_ABERTA, STATUS_ABERTA, STATUS_CONCLUIDA),
    )


def _seed_sample_data(conn):
    total_demandas = conn.execute("SELECT COUNT(*) FROM demandas").fetchone()[0]
    if total_demandas:
        return False

    demandas = [
        (
            "Corrigir bug no login",
            "Usuarios nao conseguem fazer login",
            "Joao Silva",
            PRIORIDADE_ALTA,
            STATUS_ABERTA,
            "2024-01-15 10:30:00",
        ),
        (
            "Implementar relatorio de vendas",
            "Precisamos de um relatorio mensal",
            "Maria Santos",
            PRIORIDADE_MEDIA,
            STATUS_ABERTA,
            "2024-01-16 14:20:00",
        ),
        (
            "Melhorar performance",
            "Sistema esta lento",
            "Pedro Costa",
            PRIORIDADE_BAIXA,
            STATUS_ABERTA,
            "2024-01-17 09:15:00",
        ),
        (
            "Adicionar filtros",
            "Usuarios querem filtrar demandas",
            "Ana Lima",
            PRIORIDADE_MEDIA,
            STATUS_CONCLUIDA,
            "2024-01-18 11:00:00",
        ),
    ]

    conn.executemany(
        """
        INSERT INTO demandas (
            titulo,
            descricao,
            solicitante,
            prioridade,
            status,
            data_criacao
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        demandas,
    )

    comentarios = [
        (1, "Vou investigar esse bug", "Tech Team", "2024-01-15 11:00:00"),
        (1, "Bug corrigido na branch develop", "Desenvolvedor", "2024-01-15 16:30:00"),
    ]

    conn.executemany(
        """
        INSERT INTO comentarios (demanda_id, comentario, autor, data)
        VALUES (?, ?, ?, ?)
        """,
        comentarios,
    )
    return True
