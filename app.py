from datetime import datetime
import os

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import (
    PRIORIDADE_ORDEM_SQL,
    PRIORIDADE_SLUGS,
    PRIORIDADES,
    STATUS_ABERTA,
    STATUS_CONCLUIDA,
    get_db_connection,
    initialize_database,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

ORDENACOES = {
    "prioridade": f"{PRIORIDADE_ORDEM_SQL}, data_criacao DESC",
    "recentes": "data_criacao DESC",
}
DIAS_ALERTA_PARADA = 7

initialize_database()


def get_db():
    return get_db_connection()


@app.template_filter("priority_slug")
def priority_slug(value):
    return PRIORIDADE_SLUGS.get(value, "neutra")


def normalize_priority(prioridade):
    return prioridade if prioridade in PRIORIDADES else ""


def normalize_order(ordenacao):
    return ordenacao if ordenacao in ORDENACOES else "prioridade"


def build_demand_context(status, filtro_prioridade="", termo_busca="", ordenacao="prioridade"):
    filtro_normalizado = normalize_priority(filtro_prioridade)
    ordenacao_normalizada = normalize_order(ordenacao)

    conn = get_db()
    try:
        clauses = ["status = ?"]
        params = [status]

        if filtro_normalizado:
            clauses.append("prioridade = ?")
            params.append(filtro_normalizado)

        if termo_busca:
            clauses.append("(titulo LIKE ? OR descricao LIKE ? OR solicitante LIKE ?)")
            termo_like = f"%{termo_busca}%"
            params.extend([termo_like, termo_like, termo_like])

        query = (
            "SELECT * FROM demandas "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY {ORDENACOES[ordenacao_normalizada]}"
        )
        demandas = conn.execute(query, tuple(params)).fetchall()
    finally:
        conn.close()

    return {
        "demandas": enrich_demands(demandas),
        "filtro_atual": filtro_normalizado,
        "ordenacao_atual": ordenacao_normalizada,
        "prioridades": PRIORIDADES,
        "termo_busca": termo_busca,
    }


def enrich_demands(demandas):
    agora = datetime.now()
    demandas_com_alerta = []

    for demanda in demandas:
        demanda_dict = dict(demanda)
        try:
            data_criacao = datetime.strptime(demanda["data_criacao"], "%Y-%m-%d %H:%M:%S")
            dias_parada = (agora - data_criacao).days
        except (ValueError, TypeError):
            dias_parada = 0

        demanda_dict["dias_parada"] = dias_parada
        demanda_dict["alerta_parada"] = (
            demanda_dict.get("status") == STATUS_ABERTA and dias_parada >= DIAS_ALERTA_PARADA
        )
        demandas_com_alerta.append(demanda_dict)

    return demandas_com_alerta


@app.route("/")
def index():
    contexto = build_demand_context(
        STATUS_ABERTA,
        filtro_prioridade=request.args.get("prioridade", "").strip(),
        ordenacao=request.args.get("ordenacao", "prioridade"),
    )
    contexto["rota_listagem"] = "index"
    return render_template("index.html", **contexto)


@app.route("/concluidas")
def concluidas():
    contexto = build_demand_context(
        STATUS_CONCLUIDA,
        filtro_prioridade=request.args.get("prioridade", "").strip(),
        ordenacao=request.args.get("ordenacao", "prioridade"),
    )
    return render_template("concluidas.html", **contexto)


@app.route("/nova_demanda", methods=["GET", "POST"])
def nova_demanda():
    form_data = {
        "titulo": "",
        "descricao": "",
        "solicitante": "",
        "prioridade": "",
    }

    if request.method == "POST":
        form_data = {
            "titulo": request.form.get("titulo", "").strip(),
            "descricao": request.form.get("descricao", "").strip(),
            "solicitante": request.form.get("solicitante", "").strip(),
            "prioridade": request.form.get("prioridade", "").strip(),
        }

        if not form_data["titulo"] or not form_data["descricao"] or not form_data["solicitante"]:
            flash("Todos os campos sao obrigatorios.")
            return render_template(
                "nova_demanda.html",
                prioridades=PRIORIDADES,
                form_data=form_data,
            )

        if form_data["prioridade"] not in PRIORIDADES:
            flash("Selecione uma prioridade valida.")
            return render_template(
                "nova_demanda.html",
                prioridades=PRIORIDADES,
                form_data=form_data,
            )

        conn = get_db()
        try:
            conn.execute(
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
                (
                    form_data["titulo"],
                    form_data["descricao"],
                    form_data["solicitante"],
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
def editar(id):
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)

        if request.method == "POST":
            titulo = request.form.get("titulo", "").strip()
            descricao = request.form.get("descricao", "").strip()
            solicitante = request.form.get("solicitante", "").strip()
            prioridade = request.form.get("prioridade", "").strip()
            nome_editor = request.form.get("nome_editor", "").strip()

            demanda_atualizada = dict(demanda)
            demanda_atualizada.update(
                {
                    "titulo": titulo,
                    "descricao": descricao,
                    "solicitante": solicitante,
                    "prioridade": prioridade or demanda["prioridade"],
                }
            )

            if not titulo or not descricao or not solicitante or not nome_editor:
                flash("Todos os campos sao obrigatorios.")
                return render_template(
                    "editar.html",
                    demanda=demanda_atualizada,
                    prioridades=PRIORIDADES,
                )

            if prioridade not in PRIORIDADES:
                flash("Selecione uma prioridade valida.")
                return render_template(
                    "editar.html",
                    demanda=demanda_atualizada,
                    prioridades=PRIORIDADES,
                )

            if prioridade != demanda["prioridade"] and nome_editor.lower() != demanda["solicitante"].lower():
                flash("Apenas o criador da demanda pode alterar a prioridade.")
                return render_template(
                    "editar.html",
                    demanda=demanda_atualizada,
                    prioridades=PRIORIDADES,
                )

            conn.execute(
                """
                UPDATE demandas
                SET titulo = ?, descricao = ?, solicitante = ?, prioridade = ?
                WHERE id = ?
                """,
                (titulo, descricao, solicitante, prioridade, id),
            )
            conn.commit()
            flash("Demanda atualizada.")
            return redirect(url_for("index"))

        return render_template("editar.html", demanda=demanda, prioridades=PRIORIDADES)
    finally:
        conn.close()


@app.route("/concluir/<int:id>", methods=["POST"])
def concluir(id):
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)

        conn.execute("UPDATE demandas SET status = ? WHERE id = ?", (STATUS_CONCLUIDA, id))
        conn.commit()
    finally:
        conn.close()

    flash("Demanda marcada como concluida.")
    return redirect(url_for("index"))


@app.route("/reabrir/<int:id>", methods=["POST"])
def reabrir(id):
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
def deletar(id):
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
        if not demanda:
            abort(404)

        destino = "concluidas" if demanda["status"] == STATUS_CONCLUIDA else "index"
        conn.execute("DELETE FROM demandas WHERE id = ?", (id,))
        conn.commit()
    finally:
        conn.close()

    flash("Demanda deletada.")
    return redirect(url_for(destino))


@app.route("/buscar")
def buscar():
    termo_busca = request.args.get("q", "").strip()
    filtro_prioridade = request.args.get("prioridade", "").strip()
    ordenacao = request.args.get("ordenacao", "prioridade")

    if not termo_busca:
        return redirect(
            url_for(
                "index",
                prioridade=normalize_priority(filtro_prioridade) or None,
                ordenacao=normalize_order(ordenacao),
            )
        )

    contexto = build_demand_context(
        STATUS_ABERTA,
        filtro_prioridade=filtro_prioridade,
        termo_busca=termo_busca,
        ordenacao=ordenacao,
    )
    contexto["rota_listagem"] = "buscar"
    return render_template("index.html", **contexto)


@app.route("/detalhes/<int:id>")
def detalhes(id):
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (id,)).fetchone()
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
        rota_voltar=rota_voltar,
    )


@app.route("/adicionar_comentario/<int:demanda_id>", methods=["POST"])
def adicionar_comentario(demanda_id):
    conn = get_db()
    try:
        demanda = conn.execute("SELECT * FROM demandas WHERE id = ?", (demanda_id,)).fetchone()
        if not demanda:
            abort(404)

        comentario = request.form.get("comentario", "").strip()
        autor = request.form.get("autor", "").strip()

        if not comentario or not autor:
            flash("Nome e comentario sao obrigatorios.")
            return redirect(url_for("detalhes", id=demanda_id))

        conn.execute(
            """
            INSERT INTO comentarios (demanda_id, comentario, autor, data)
            VALUES (?, ?, ?, ?)
            """,
            (
                demanda_id,
                comentario,
                autor,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    flash("Comentario adicionado.")
    return redirect(url_for("detalhes", id=demanda_id))


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0")
