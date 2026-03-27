from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

PRIORIDADES = ['Urgente', 'Alta', 'Média']
ORDEM_PRIORIDADE = "CASE prioridade WHEN 'Urgente' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Média' THEN 3 ELSE 4 END"
DIAS_ALERTA_PARADA = 7


def get_db():
    conn = sqlite3.connect('demandas.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


@app.route('/')
def index():
    filtro_prioridade = request.args.get('prioridade', '')
    conn = get_db()
    try:
        if filtro_prioridade and filtro_prioridade in PRIORIDADES:
            demandas = conn.execute(
                f"SELECT * FROM demandas WHERE status = 'Aberta' AND prioridade = ? ORDER BY {ORDEM_PRIORIDADE}, data_criacao DESC",
                (filtro_prioridade,)
            ).fetchall()
        else:
            demandas = conn.execute(
                f"SELECT * FROM demandas WHERE status = 'Aberta' ORDER BY {ORDEM_PRIORIDADE}, data_criacao DESC"
            ).fetchall()

        agora = datetime.now()
        demandas_com_alerta = []
        for d in demandas:
            d_dict = dict(d)
            try:
                data_criacao = datetime.strptime(d['data_criacao'], '%Y-%m-%d %H:%M:%S')
                dias_parada = (agora - data_criacao).days
                d_dict['dias_parada'] = dias_parada
                d_dict['alerta_parada'] = dias_parada >= DIAS_ALERTA_PARADA
            except (ValueError, TypeError):
                d_dict['dias_parada'] = 0
                d_dict['alerta_parada'] = False
            demandas_com_alerta.append(d_dict)

        return render_template('index.html',
                               demandas=demandas_com_alerta,
                               prioridades=PRIORIDADES,
                               filtro_atual=filtro_prioridade)
    finally:
        conn.close()


@app.route('/concluidas')
def concluidas():
    conn = get_db()
    try:
        demandas = conn.execute(
            f"SELECT * FROM demandas WHERE status = 'Concluída' ORDER BY data_criacao DESC"
        ).fetchall()
        return render_template('concluidas.html', demandas=demandas)
    finally:
        conn.close()


@app.route('/nova_demanda', methods=['GET', 'POST'])
def nova_demanda():
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        solicitante = request.form.get('solicitante', '').strip()
        prioridade = request.form.get('prioridade', '').strip()

        if not titulo or not descricao or not solicitante:
            flash('Todos os campos são obrigatórios!')
            return render_template('nova_demanda.html', prioridades=PRIORIDADES)

        if prioridade not in PRIORIDADES:
            flash('Selecione uma prioridade válida!')
            return render_template('nova_demanda.html', prioridades=PRIORIDADES)

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO demandas (titulo, descricao, solicitante, prioridade, status, data_criacao) VALUES (?, ?, ?, ?, ?, ?)',
                (titulo, descricao, solicitante, prioridade, 'Aberta', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            flash('Demanda criada com sucesso!')
            return redirect(url_for('index'))
        finally:
            conn.close()

    return render_template('nova_demanda.html', prioridades=PRIORIDADES)


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = get_db()
    try:
        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            solicitante = request.form.get('solicitante', '').strip()
            prioridade = request.form.get('prioridade', '').strip()
            nome_editor = request.form.get('nome_editor', '').strip()

            demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
            if not demanda:
                abort(404)

            if not titulo or not descricao or not solicitante:
                flash('Todos os campos são obrigatórios!')
                return render_template('editar.html', demanda=demanda, prioridades=PRIORIDADES)

            if prioridade not in PRIORIDADES:
                flash('Selecione uma prioridade válida!')
                return render_template('editar.html', demanda=demanda, prioridades=PRIORIDADES)

            if prioridade != demanda['prioridade'] and nome_editor.lower() != demanda['solicitante'].lower():
                flash('Apenas o criador da demanda pode alterar a prioridade!')
                return render_template('editar.html', demanda=demanda, prioridades=PRIORIDADES)

            conn.execute(
                'UPDATE demandas SET titulo = ?, descricao = ?, solicitante = ?, prioridade = ? WHERE id = ?',
                (titulo, descricao, solicitante, prioridade, id)
            )
            conn.commit()
            flash('Demanda atualizada!')
            return redirect(url_for('index'))

        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)
        return render_template('editar.html', demanda=demanda, prioridades=PRIORIDADES)
    finally:
        conn.close()


@app.route('/concluir/<int:id>', methods=['POST'])
def concluir(id):
    conn = get_db()
    try:
        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)
        conn.execute("UPDATE demandas SET status = 'Concluída' WHERE id = ?", (id,))
        conn.commit()
        flash('Demanda marcada como concluída!')
        return redirect(url_for('index'))
    finally:
        conn.close()


@app.route('/reabrir/<int:id>', methods=['POST'])
def reabrir(id):
    conn = get_db()
    try:
        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)
        conn.execute("UPDATE demandas SET status = 'Aberta' WHERE id = ?", (id,))
        conn.commit()
        flash('Demanda reaberta!')
        return redirect(url_for('concluidas'))
    finally:
        conn.close()


@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    conn = get_db()
    try:
        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)
        conn.execute('DELETE FROM demandas WHERE id = ?', (id,))
        conn.commit()
        flash('Deletado!')
        return redirect(url_for('index'))
    finally:
        conn.close()


@app.route('/buscar')
def buscar():
    termo = request.args.get('q', '').strip()
    if not termo:
        return redirect(url_for('index'))

    conn = get_db()
    try:
        resultados = conn.execute(
            f"SELECT * FROM demandas WHERE titulo LIKE ? AND status = 'Aberta' ORDER BY {ORDEM_PRIORIDADE}, data_criacao DESC",
            (f'%{termo}%',)
        ).fetchall()

        agora = datetime.now()
        demandas_com_alerta = []
        for d in resultados:
            d_dict = dict(d)
            try:
                data_criacao = datetime.strptime(d['data_criacao'], '%Y-%m-%d %H:%M:%S')
                dias_parada = (agora - data_criacao).days
                d_dict['dias_parada'] = dias_parada
                d_dict['alerta_parada'] = dias_parada >= DIAS_ALERTA_PARADA
            except (ValueError, TypeError):
                d_dict['dias_parada'] = 0
                d_dict['alerta_parada'] = False
            demandas_com_alerta.append(d_dict)

        return render_template('index.html',
                               demandas=demandas_com_alerta,
                               prioridades=PRIORIDADES,
                               filtro_atual='')
    finally:
        conn.close()


@app.route('/detalhes/<int:id>')
def detalhes(id):
    conn = get_db()
    try:
        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)

        comentarios = conn.execute(
            'SELECT * FROM comentarios WHERE demanda_id = ?', (id,)
        ).fetchall()

        return render_template('detalhes.html', demanda=demanda, comentarios=comentarios)
    finally:
        conn.close()


@app.route('/adicionar_comentario/<int:demanda_id>', methods=['POST'])
def adicionar_comentario(demanda_id):
    conn = get_db()
    try:
        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (demanda_id,)).fetchone()
        if not demanda:
            abort(404)

        comentario = request.form.get('comentario', '').strip()
        autor = request.form.get('autor', '').strip()

        if not comentario or not autor:
            flash('Nome e comentário são obrigatórios!')
            return redirect(url_for('detalhes', id=demanda_id))

        conn.execute(
            'INSERT INTO comentarios (demanda_id, comentario, autor, data) VALUES (?, ?, ?, ?)',
            (demanda_id, comentario, autor, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        return redirect(url_for('detalhes', id=demanda_id))
    finally:
        conn.close()


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0')
