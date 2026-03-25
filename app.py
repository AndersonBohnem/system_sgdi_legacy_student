from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))


def get_db():
    conn = sqlite3.connect('demandas.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


@app.route('/')
def index():
    conn = get_db()
    try:
        demandas = conn.execute('SELECT * FROM demandas').fetchall()
        return render_template('index.html', demandas=demandas)
    finally:
        conn.close()


@app.route('/nova_demanda', methods=['GET', 'POST'])
def nova_demanda():
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        solicitante = request.form.get('solicitante', '').strip()

        if not titulo or not descricao or not solicitante:
            flash('Todos os campos são obrigatórios!')
            return render_template('nova_demanda.html')

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO demandas (titulo, descricao, solicitante, data_criacao) VALUES (?, ?, ?, ?)',
                (titulo, descricao, solicitante, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            flash('Salvo!')
            return redirect(url_for('index'))
        finally:
            conn.close()

    return render_template('nova_demanda.html')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = get_db()
    try:
        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            solicitante = request.form.get('solicitante', '').strip()

            if not titulo or not descricao or not solicitante:
                flash('Todos os campos são obrigatórios!')
                demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
                if not demanda:
                    abort(404)
                return render_template('editar.html', demanda=demanda)

            conn.execute(
                'UPDATE demandas SET titulo = ?, descricao = ?, solicitante = ? WHERE id = ?',
                (titulo, descricao, solicitante, id)
            )
            conn.commit()
            flash('Atualizado!')
            return redirect(url_for('index'))

        demanda = conn.execute('SELECT * FROM demandas WHERE id = ?', (id,)).fetchone()
        if not demanda:
            abort(404)
        return render_template('editar.html', demanda=demanda)
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
            'SELECT * FROM demandas WHERE titulo LIKE ?', (f'%{termo}%',)
        ).fetchall()
        return render_template('index.html', demandas=resultados)
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
