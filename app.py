import secrets
from datetime import datetime
from functools import wraps
import os

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database import (
    PRIORIDADE_ORDEM_SQL,
    PRIORIDADE_SLUGS,
    PRIORIDADES,
    STATUS_ABERTA,
    STATUS_CONCLUIDA,
    authenticate_user,
    get_all_users_with_stats,
    get_db_connection,
    initialize_database,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sgdi-dev-key-troque-em-producao-2024")

ORDENACOES = {
    "prioridade": f"{PRIORIDADE_ORDEM_SQL}, d.data_criacao DESC",
    "recentes": "d.data_criacao DESC",
}
ORDENACAO_LABELS = {
    "prioridade": "Prioridade primeiro",
    "recentes": "Mais recentes primeiro",
}
DIAS_ALERTA_PARADA = 7

initialize_database()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return {
        "csrf_token": session["csrf_token"],
        "usuario_logado": {
            "id": session.get("usuario_id"),
            "nome": session.get("usuario_nome"),
            "username": session.get("usuario_username"),
        } if "usuario_id" in session else None,
    }


def _validate_csrf():
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        abort(403)


def get_db():
    return get_db_connection()


@app.template_filter("priority_slug")
def priority_slug(value):
    return PRIORIDADE_SLUGS.get(value, "neutra")


@app.template_filter("display_datetime")
def display_datetime(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M")
    except (TypeError, ValueError):
        return value or ""


def normalize_priority(prioridade):
    return prioridade if prioridade in PRIORIDADES else ""


def normalize_order(ordenacao):
    return ordenacao if ordenacao in ORDENACOES else "prioridade"


def _escape_like(term):
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_demand_context(
    status,
    filtro_prioridade="",
    filtro_usuario_id=None,
    termo_busca="",
    ordenacao="prioridade",
):
    filtro_normalizado = normalize_priority(filtro_prioridade)
    ordenacao_normalizada = normalize_order(ordenacao)

    conn = get_db()
    try:
        clauses = ["d.status = ?"]
        params = [status]

        if filtro_normalizado:
            clauses.append("d.prioridade = ?")
            params.append(filtro_normalizado)

        if filtro_usuario_id:
            try:
                clauses.append("d.usuario_id = ?")
                params.append(int(filtro_usuario_id))
            except (ValueError, TypeError):
                pass

        if termo_busca:
            termo_like = f"%{_escape_like(termo_busca)}%"
            clauses.append(
                "(d.titulo LIKE ? ESCAPE '\\' "
                "OR d.descricao LIKE ? ESCAPE '\\' "
                "OR d.solicitante LIKE ? ESCAPE '\\')"
            )
            params.extend([termo_like, termo_like, termo_like])

        query = (
            "SELECT d.*, u.username AS usuario_username "
            "FROM demandas d "
            "JOIN usuarios u ON u.id = d.usuario_id "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY {ORDENACOES[ordenacao_normalizada]}"
        )
        demandas = conn.execute(query, tuple(params)).fetchall()
        usuarios = conn.execute(
            "SELECT id, nome FROM usuarios ORDER BY nome"
        ).fetchall()
    finally:
        conn.close()

    demandas_enriquecidas = enrich_demands(demandas)

    return {
        "demandas": demandas_enriquecidas,
        "filtro_atual": filtro_normalizado,
        "filtro_usuario_id": filtro_usuario_id or "",
        "ordenacao_atual": ordenacao_normalizada,
        "resumo": build_summary(
            demandas_enriquecidas,
            filtro_normalizado,
            ordenacao_normalizada,
        ),
        "prioridades": PRIORIDADES,
        "termo_busca": termo_busca,
        "usuarios": usuarios,
    }


def enrich_demands(demandas):
    agora = datetime.now()
    resultado = []
    for demanda in demandas:
        d = dict(demanda)
        try:
            data_criacao = datetime.strptime(d["data_criacao"], "%Y-%m-%d %H:%M:%S")
            dias_parada = (agora - data_criacao).days
        except (ValueError, TypeError):
            dias_parada = 0
        d["dias_parada"] = dias_parada
        d["alerta_parada"] = d.get("status") == STATUS_ABERTA and dias_parada >= DIAS_ALERTA_PARADA
        resultado.append(d)
    return resultado


def build_summary(demandas, filtro_prioridade, ordenacao):
    contagem = {p: 0 for p in PRIORIDADES}
    for d in demandas:
        if d.get("prioridade") in contagem:
            contagem[d["prioridade"]] += 1
    return {
        "total": len(demandas),
        "alta": contagem[PRIORIDADES[0]],
        "media": contagem[PRIORIDADES[1]],
        "baixa": contagem[PRIORIDADES[2]],
        "alertas": sum(1 for d in demandas if d.get("alerta_parada")),
        "filtro_label": filtro_prioridade or "Todas as prioridades",
        "ordenacao_label": ORDENACAO_LABELS[ordenacao],
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        senha = request.form.get("senha", "").strip()

        usuario = authenticate_user(username, senha)
        if usuario:
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_username"] = usuario["username"]
            session["csrf_token"] = secrets.token_hex(32)
            flash(f"Bem-vindo, {usuario['nome']}!")
            return redirect(url_for("index"))

        flash("Usuário ou senha incorretos.")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    _validate_csrf()
    session.clear()
    flash("Sessão encerrada com sucesso.")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    contexto = build_demand_context(
        STATUS_ABERTA,
        filtro_prioridade=request.args.get("prioridade", "").strip(),
        filtro_usuario_id=request.args.get("usuario_id", "").strip() or None,
        ordenacao=request.args.get("ordenacao", "prioridade"),
    )
    contexto["rota_listagem"] = "index"
    return render_template("index.html", **contexto)


@app.route("/concluidas")
@login_required
def concluidas():
    contexto = build_demand_context(
        STATUS_CONCLUIDA,
        filtro_prioridade=request.args.get("prioridade", "").strip(),
        filtro_usuario_id=request.args.get("usuario_id", "").strip() or None,
        ordenacao=request.args.get("ordenacao", "prioridade"),
    )
    return render_template("concluidas.html", **contexto)


@app.route("/nova_demanda", methods=["GET", "POST"])
@login_required
def nova_demanda():
    form_data = {"titulo": "", "descricao": "", "prioridade": ""}

    if request.method == "POST":
        _validate_csrf()
        form_data = {
            "titulo": request.form.get("titulo", "").strip(),
            "descricao": request.form.get("descricao", "").strip(),
            "prioridade": request.form.get("prioridade", "").strip(),
        }

        if not form_data["titulo"] or not form_data["descricao"]:
            flash("Todos os campos são obrigatórios.")
            return render_template("nova_demanda.html", prioridades=PRIORIDADES, form_data=form_data)

        if form_data["prioridade"] not in PRIORIDADES:
            flash("Selecione uma prioridade válida.")
            return render_template("nova_demanda.html", prioridades=PRIORIDADES, form_data=form_data)

        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO demandas (
                    titulo, descricao, solicitante, usuario_id,
                    prioridade, status, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form_data["titulo"],
                    form_data["descricao"],
                    session["usuario_nome"],
                    session["usuario_id"],
                    form_data["prioridade"],
                    STATUS_ABERTA,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        flash("Demanda criada com sucesso.")
        return redirect(url_for("index"))

    return render_template("nova_demanda.html", prioridades=PRIORIDADES, form_data=form_data)


@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    conn = get_db()
    try:
        demanda = conn.execute(
            "SELECT d.*, u.username AS usuario_username "
            "FROM demandas d JOIN usuarios u ON u.id = d.usuario_id "
            "WHERE d.id = ?",
            (id,),
        ).fetchone()
        if not demanda:
            abort(404)

        # Apenas o solicitante original pode editar a demanda
        if session["usuario_id"] != demanda["usuario_id"]:
            flash("Apenas o solicitante da demanda pode editá-la.")
            return redirect(url_for("detalhes", id=id))

        if request.method == "POST":
            _validate_csrf()
            titulo = request.form.get("titulo", "").strip()
            descricao = request.form.get("descricao", "").strip()
            prioridade = request.form.get("prioridade", "").strip()

            demanda_atualizada = dict(demanda)
            demanda_atualizada.update({
                "titulo": titulo,
                "descricao": descricao,
                "prioridade": prioridade or demanda["prioridade"],
            })

            if not titulo or not descricao:
                flash("Título e descrição são obrigatórios.")
                return render_template("editar.html", demanda=demanda_atualizada, prioridades=PRIORIDADES)

            if prioridade not in PRIORIDADES:
                flash("Selecione uma prioridade válida.")
                return render_template("editar.html", demanda=demanda_atualizada, prioridades=PRIORIDADES)

            conn.execute(
                "UPDATE demandas SET titulo = ?, descricao = ?, prioridade = ? WHERE id = ?",
                (titulo, descricao, prioridade, id),
            )
            conn.commit()
            flash("Demanda atualizada.")
            return redirect(url_for("detalhes", id=id))

        return render_template("editar.html", demanda=demanda, prioridades=PRIORIDADES)
    finally:
        conn.close()


@app.route("/concluir/<int:id>", methods=["POST"])
@login_required
def concluir(id):
    _validate_csrf()
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)
        conn.execute("UPDATE demandas SET status = ? WHERE id = ?", (STATUS_CONCLUIDA, id))
        conn.commit()
    finally:
        conn.close()
    flash("Demanda marcada como concluída.")
    return redirect(url_for("index"))


@app.route("/reabrir/<int:id>", methods=["POST"])
@login_required
def reabrir(id):
    _validate_csrf()
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)
        conn.execute("UPDATE demandas SET status = ? WHERE id = ?", (STATUS_ABERTA, id))
        conn.commit()
    finally:
        conn.close()
    flash("Demanda reaberta.")
    return redirect(url_for("concluidas"))


@app.route("/deletar/<int:id>", methods=["POST"])
@login_required
def deletar(id):
    _validate_csrf()
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)
        destino = "concluidas" if demanda["status"] == STATUS_CONCLUIDA else "index"
        if session["usuario_id"] != demanda["usuario_id"]:
            flash("Apenas o solicitante da demanda pode deletá-la.")
            return redirect(url_for("detalhes", id=id))
        conn.execute("DELETE FROM demandas WHERE id = ?", (id,))
        conn.commit()
    finally:
        conn.close()
    flash("Demanda deletada.")
    return redirect(url_for(destino))


@app.route("/buscar")
@login_required
def buscar():
    termo_busca = request.args.get("q", "").strip()
    filtro_prioridade = request.args.get("prioridade", "").strip()
    filtro_usuario_id = request.args.get("usuario_id", "").strip() or None
    ordenacao = request.args.get("ordenacao", "prioridade")

    if not termo_busca:
        return redirect(url_for(
            "index",
            prioridade=normalize_priority(filtro_prioridade) or None,
            usuario_id=filtro_usuario_id or None,
            ordenacao=normalize_order(ordenacao),
        ))

    contexto = build_demand_context(
        STATUS_ABERTA,
        filtro_prioridade=filtro_prioridade,
        filtro_usuario_id=filtro_usuario_id,
        termo_busca=termo_busca,
        ordenacao=ordenacao,
    )
    contexto["rota_listagem"] = "buscar"
    return render_template("index.html", **contexto)


@app.route("/detalhes/<int:id>")
@login_required
def detalhes(id):
    conn = get_db()
    try:
        demanda = conn.execute(
            "SELECT d.*, u.username AS usuario_username "
            "FROM demandas d JOIN usuarios u ON u.id = d.usuario_id "
            "WHERE d.id = ?",
            (id,),
        ).fetchone()
        if not demanda:
            abort(404)

        comentarios = conn.execute(
            "SELECT * FROM comentarios WHERE demanda_id = ? ORDER BY data DESC",
            (id,),
        ).fetchall()
    finally:
        conn.close()

    rota_voltar = "concluidas" if demanda["status"] == STATUS_CONCLUIDA else "index"
    return render_template(
        "detalhes.html",
        demanda=demanda,
        comentarios=comentarios,
        comentarios_total=len(comentarios),
        rota_voltar=rota_voltar,
        eh_solicitante=(session.get("usuario_id") == demanda["usuario_id"]),
    )


@app.route("/adicionar_comentario/<int:demanda_id>", methods=["POST"])
@login_required
def adicionar_comentario(demanda_id):
    _validate_csrf()
    conn = get_db()
    try:
        demanda = conn.execute("SELECT id FROM demandas WHERE id = ?", (demanda_id,)).fetchone()
        if not demanda:
            abort(404)

        comentario = request.form.get("comentario", "").strip()
        if not comentario:
            flash("O comentário não pode estar vazio.")
            return redirect(url_for("detalhes", id=demanda_id))

        conn.execute(
            "INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)",
            (
                demanda_id,
                comentario,
                session["usuario_nome"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    flash("Comentário adicionado.")
    return redirect(url_for("detalhes", id=demanda_id))


@app.route("/usuarios")
@login_required
def usuarios():
    stats = get_all_users_with_stats()
    return render_template("usuarios.html", usuarios_stats=stats)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0")
