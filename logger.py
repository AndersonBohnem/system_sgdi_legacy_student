"""
Camada de logging estruturado do SGDI.
Registra eventos no banco (logs_sistema) e em arquivos rotativos separados:
  - logs/sgdi.log       — todos os eventos
  - logs/security.log   — apenas SEGURANCA, AUTH falhas e CRITICAL
  - logs/api_access.log — apenas chamadas à API REST
"""
import hashlib
import json
import logging
import logging.handlers
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "demandas.db"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ── Níveis e categorias ───────────────────────────────────────────────────────
NIVEIS = ("INFO", "WARNING", "ERROR", "CRITICAL")

CAT_AUTH       = "AUTH"
CAT_DEMANDA    = "DEMANDA"
CAT_API        = "API"
CAT_SEGURANCA  = "SEGURANCA"
CAT_EXPORTACAO = "EXPORTACAO"
CAT_API_KEY    = "API_KEY"
CAT_USUARIO    = "USUARIO"
CAT_SISTEMA    = "SISTEMA"

# ── Retenção por categoria (dias) ─────────────────────────────────────────────
RETENCAO_DIAS = {
    CAT_AUTH:       365,   # compliance: 1 ano
    CAT_SEGURANCA:  365,   # compliance: 1 ano
    CAT_API_KEY:    365,   # compliance: 1 ano
    CAT_DEMANDA:    180,   # 6 meses
    CAT_EXPORTACAO: 180,   # 6 meses
    CAT_USUARIO:    180,   # 6 meses
    CAT_API:         30,   # volume alto — 30 dias
    CAT_SISTEMA:     90,   # padrão
}
RETENCAO_PADRAO = 90

# ── Chaves sensíveis que nunca devem aparecer nos logs ────────────────────────
_CHAVES_SENSIVEIS = frozenset({
    "senha", "password", "passwd", "secret", "token",
    "chave", "key", "api_key", "hash", "hash_registro",
    "hash_anterior", "authorization",
})


# ═══════════════════════════════════════════════════════════════════════════════
# SANITIZAÇÃO DE DADOS SENSÍVEIS
# ═══════════════════════════════════════════════════════════════════════════════

def _sanitizar(detalhes: dict, depth: int = 0) -> dict:
    """Mascara recursivamente chaves sensíveis no dict de detalhes."""
    if not isinstance(detalhes, dict) or depth > 3:
        return detalhes
    resultado = {}
    for k, v in detalhes.items():
        if k.lower() in _CHAVES_SENSIVEIS:
            resultado[k] = "***"
        elif isinstance(v, dict):
            resultado[k] = _sanitizar(v, depth + 1)
        elif isinstance(v, str) and len(v) > 43 and k.lower() in ("chave_usada", "chave"):
            resultado[k] = v[:8] + "••••"
        else:
            resultado[k] = v
    return resultado


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER — SQLite
# ═══════════════════════════════════════════════════════════════════════════════

class SQLiteLogHandler(logging.Handler):
    """Persiste cada registro de log na tabela logs_sistema com hash encadeado."""

    _lock = threading.Lock()

    def emit(self, record):
        try:
            extra = getattr(record, "extra", {})
            detalhes_limpos = _sanitizar(extra.get("detalhes") or {})
            detalhes_json   = json.dumps(detalhes_limpos, ensure_ascii=False)

            with self._lock:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                try:
                    last = conn.execute(
                        "SELECT hash_registro FROM logs_sistema ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                    hash_anterior = last["hash_registro"] if last else ""

                    conteudo = (
                        f"{record.created}"
                        f"{record.levelname}"
                        f"{extra.get('categoria', '')}"
                        f"{extra.get('acao', '')}"
                        f"{extra.get('usuario_id', '')}"
                        f"{extra.get('ip', '')}"
                        f"{detalhes_json}"
                        f"{hash_anterior}"
                    )
                    hash_atual = hashlib.sha256(conteudo.encode()).hexdigest()

                    conn.execute(
                        """
                        INSERT INTO logs_sistema
                            (timestamp, nivel, categoria, acao,
                             usuario_id, usuario_nome, ip, session_id,
                             recurso_tipo, recurso_id, detalhes,
                             hash_anterior, hash_registro)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            record.levelname,
                            extra.get("categoria", CAT_SISTEMA),
                            extra.get("acao", record.getMessage()),
                            extra.get("usuario_id"),
                            extra.get("usuario_nome"),
                            extra.get("ip"),
                            extra.get("session_id"),
                            extra.get("recurso_tipo"),
                            extra.get("recurso_id"),
                            detalhes_json,
                            hash_anterior,
                            hash_atual,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception:
            self.handleError(record)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMATADORES E FILTROS DE ARQUIVO
# ═══════════════════════════════════════════════════════════════════════════════

class _FileFormatter(logging.Formatter):
    def format(self, record):
        extra   = getattr(record, "extra", {})
        usuario = extra.get("usuario_nome") or "anonimo"
        uid     = extra.get("usuario_id")
        if uid:
            usuario = f"{usuario}(id={uid})"
        sid  = str(extra.get("session_id") or "-")
        ip   = str(extra.get("ip") or "-")
        cat  = str(extra.get("categoria") or CAT_SISTEMA)
        acao = str(extra.get("acao") or record.getMessage())
        det  = json.dumps(_sanitizar(extra.get("detalhes") or {}), ensure_ascii=False)
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"{ts} | {record.levelname:<8} | {cat:<12} | {acao:<28} | "
            f"user={usuario:<22} | ip={ip:<16} | sid={sid:<8} | {det}"
        )


class _SecurityFilter(logging.Filter):
    """Passa apenas eventos de segurança e críticos."""
    _ACOES_FALHA = frozenset({
        "login_falha", "brute_force_detectado", "csrf_falha",
        "acesso_negado", "api_chave_invalida", "api_sem_chave", "api_rate_limit",
    })

    def filter(self, record):
        extra = getattr(record, "extra", {})
        cat   = extra.get("categoria", "")
        acao  = extra.get("acao", "")
        nivel = record.levelname
        return (
            nivel in ("CRITICAL", "ERROR")
            or cat == CAT_SEGURANCA
            or (cat == CAT_AUTH   and acao in self._ACOES_FALHA)
            or (cat == CAT_API    and acao in self._ACOES_FALHA)
            or (cat == CAT_API_KEY and acao == "api_key_revogada")
        )


class _APIAccessFilter(logging.Filter):
    """Passa apenas chamadas à API REST."""
    def filter(self, record):
        extra = getattr(record, "extra", {})
        return extra.get("categoria", "") == CAT_API


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DO LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

_logger = logging.getLogger("sgdi")
_logger.setLevel(logging.DEBUG)
_logger.propagate = False

if not _logger.handlers:
    _fmt = _FileFormatter()

    def _make_fh(filename, filtro=None):
        fh = logging.handlers.RotatingFileHandler(
            LOG_DIR / filename,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(logging.INFO)
        fh.setFormatter(_fmt)
        if filtro:
            fh.addFilter(filtro)
        return fh

    _logger.addHandler(_make_fh("sgdi.log"))                          # todos
    _logger.addHandler(_make_fh("security.log",   _SecurityFilter())) # segurança
    _logger.addHandler(_make_fh("api_access.log", _APIAccessFilter())) # API

    # Handler SQLite
    _sh = SQLiteLogHandler()
    _sh.setLevel(logging.INFO)
    _logger.addHandler(_sh)


# ═══════════════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════════

def registrar(
    categoria: str,
    acao: str,
    nivel: str = "INFO",
    usuario_id=None,
    usuario_nome: str = None,
    ip: str = None,
    session_id: str = None,
    recurso_tipo: str = None,
    recurso_id=None,
    detalhes: dict = None,
):
    """
    Ponto central de registro de eventos do sistema.

    Exemplos:
        registrar(CAT_AUTH, "login_sucesso", usuario_id=2, usuario_nome="Ana", ip="1.2.3.4")
        registrar(CAT_DEMANDA, "demanda_criada", recurso_tipo="demanda", recurso_id=25,
                  usuario_id=2, detalhes={"titulo": "Falha no ERP", "prioridade": "Alta"})
    """
    nivel = nivel.upper()
    if nivel not in NIVEIS:
        nivel = "INFO"

    level_map = {
        "INFO":     logging.INFO,
        "WARNING":  logging.WARNING,
        "ERROR":    logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    record = logging.LogRecord(
        name="sgdi", level=level_map[nivel],
        pathname="", lineno=0, msg=acao, args=(), exc_info=None,
    )
    record.extra = {
        "categoria":    categoria,
        "acao":         acao,
        "usuario_id":   usuario_id,
        "usuario_nome": usuario_nome,
        "ip":           ip,
        "session_id":   session_id,
        "recurso_tipo": recurso_tipo,
        "recurso_id":   recurso_id,
        "detalhes":     _sanitizar(detalhes or {}),
    }
    _logger.handle(record)


# ═══════════════════════════════════════════════════════════════════════════════
# BRUTE-FORCE
# ═══════════════════════════════════════════════════════════════════════════════

def verificar_brute_force(ip: str, janela_minutos: int = 5, max_tentativas: int = 5) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            limite = (datetime.now() - timedelta(minutes=janela_minutos)
                      ).strftime("%Y-%m-%d %H:%M:%S")
            row = conn.execute(
                "SELECT COUNT(*) FROM logs_sistema WHERE acao='login_falha' AND ip=? AND timestamp>=?",
                (ip, limite),
            ).fetchone()
            return (row[0] if row else 0) >= max_tentativas
        finally:
            conn.close()
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRIDADE DA CADEIA DE HASHES
# ═══════════════════════════════════════════════════════════════════════════════

def verificar_integridade(limite: int = 1000) -> dict:
    """
    Verifica a cadeia de hashes dos últimos N registros.
    Detecta adulteração direta de campos de texto no banco.
    Retorna {"integro": bool, "total": int, "falhas": [ids], "verificado_em": str}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT id, timestamp, nivel, categoria, acao, usuario_id, ip,
                          detalhes, hash_anterior, hash_registro
                   FROM logs_sistema ORDER BY id ASC LIMIT ?""",
                (limite,),
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return {"integro": False, "total": 0, "falhas": ["Erro ao acessar banco"],
                "verificado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    falhas = []
    hash_prev = ""
    for row in rows:
        det = row["detalhes"] or "{}"
        conteudo = (
            f"{row['timestamp']}{row['nivel']}{row['categoria']}"
            f"{row['acao']}{row['usuario_id'] or ''}{row['ip'] or ''}"
            f"{det}{row['hash_anterior'] or ''}"
        )
        esperado = hashlib.sha256(conteudo.encode()).hexdigest()
        if row["hash_registro"] != esperado and row["hash_anterior"] != hash_prev:
            falhas.append(row["id"])
        hash_prev = row["hash_registro"] or ""

    return {
        "integro":       len(falhas) == 0,
        "total":         len(rows),
        "falhas":        falhas,
        "verificado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PURGA DE LOGS ANTIGOS (POR CATEGORIA)
# ═══════════════════════════════════════════════════════════════════════════════

def purgar_logs_antigos(dias: int = None) -> int:
    """
    Remove logs antigos respeitando a política de retenção por categoria.
    Se `dias` for fornecido, usa esse valor para todas as categorias (override global).
    Retorna o total de registros removidos.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        total_removidos = 0
        try:
            if dias is not None:
                # Override global: remove tudo mais antigo que `dias`
                limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
                cur = conn.execute("DELETE FROM logs_sistema WHERE timestamp < ?", (limite,))
                total_removidos = cur.rowcount
            else:
                # Política por categoria
                for cat, retention in RETENCAO_DIAS.items():
                    limite = (datetime.now() - timedelta(days=retention)).strftime("%Y-%m-%d %H:%M:%S")
                    cur = conn.execute(
                        "DELETE FROM logs_sistema WHERE categoria = ? AND timestamp < ?",
                        (cat, limite),
                    )
                    total_removidos += cur.rowcount
                # Categorias sem política explícita → padrão
                cats_conhecidas = list(RETENCAO_DIAS.keys())
                placeholders = ",".join("?" * len(cats_conhecidas))
                limite_padrao = (datetime.now() - timedelta(days=RETENCAO_PADRAO)
                                 ).strftime("%Y-%m-%d %H:%M:%S")
                cur = conn.execute(
                    f"DELETE FROM logs_sistema WHERE categoria NOT IN ({placeholders}) AND timestamp < ?",
                    cats_conhecidas + [limite_padrao],
                )
                total_removidos += cur.rowcount
            conn.commit()
            return total_removidos
        finally:
            conn.close()
    except Exception:
        return 0
