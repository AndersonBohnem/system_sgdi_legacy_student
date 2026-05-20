"""
Gerador do Relatório Técnico: Uso de IA no Desenvolvimento do SGDI
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT

# ── Palette ───────────────────────────────────────────────────────────────────
C_PRIMARY  = colors.HexColor("#1e40af")
C_ACCENT   = colors.HexColor("#3b82f6")
C_LIGHT    = colors.HexColor("#dbeafe")
C_SUCCESS  = colors.HexColor("#059669")
C_WARNING  = colors.HexColor("#d97706")
C_DANGER   = colors.HexColor("#dc2626")
C_DARK     = colors.HexColor("#1e293b")
C_MUTED    = colors.HexColor("#64748b")
C_BG       = colors.HexColor("#f8fafc")
C_BORDER   = colors.HexColor("#e2e8f0")
C_WHITE    = colors.white
C_PURPLE   = colors.HexColor("#7c3aed")
C_TEAL     = colors.HexColor("#0d9488")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


def build_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    add("H1", fontSize=18, leading=22, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8)
    add("H2", fontSize=13, leading=17, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=5)
    add("H3", fontSize=11, leading=14, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    add("Body", fontSize=10, leading=15, textColor=C_DARK,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6)
    add("BodySmall", fontSize=9, leading=13, textColor=C_MUTED,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=4)
    add("Caption", fontSize=8, leading=11, textColor=C_MUTED,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=8)
    add("Footer", fontSize=8, leading=10, textColor=C_MUTED,
        fontName="Helvetica", alignment=TA_CENTER)
    return base


def hr(color=C_BORDER, thickness=0.5, spaceB=4, spaceA=4):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color, spaceAfter=spaceA, spaceBefore=spaceB)


def colored_table(headers, rows, col_widths, header_color=C_PRIMARY):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR",      (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 9),
        ("ALIGN",          (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME",       (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR",      (0, 1), (-1, -1), C_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG]),
        ("GRID",           (0, 0), (-1, -1), 0.4, C_BORDER),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def cover_page(canvas, doc):
    w, h = A4
    canvas.saveState()

    # Background
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#1e3a8a"))
    canvas.rect(0, 0, w, h * 0.35, fill=1, stroke=0)

    # Decorative circles
    canvas.setFillColor(colors.HexColor("#1d4ed8"))
    canvas.circle(w - 60, h - 60, 100, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#2563eb"))
    canvas.circle(w - 60, h - 60, 65, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#1d4ed8"))
    canvas.circle(55, 90, 75, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#1e40af"))
    canvas.circle(55, 90, 48, fill=1, stroke=0)

    # Tag
    canvas.setFillColor(colors.HexColor("#60a5fa"))
    canvas.roundRect(MARGIN, h - 82, 155, 24, 4, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN + 10, h - 74, "RELATÓRIO TÉCNICO · IA · 2026")

    # Title
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(MARGIN, h - 148, "Uso de Inteligência Artificial")
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawString(MARGIN, h - 184, "no Desenvolvimento do SGDI")

    # Subtitle
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(colors.HexColor("#bfdbfe"))
    canvas.drawString(MARGIN, h - 215,
                      "Sistema de Gestão de Demandas Internas — Desafio da Tecnologia")

    # Divider
    canvas.setStrokeColor(colors.HexColor("#3b82f6"))
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, h - 232, w - MARGIN, h - 232)

    # Meta
    meta = [
        ("Ferramenta de IA",  "Claude Sonnet 4.6 (Anthropic)"),
        ("Interface",         "Claude Code CLI / VSCode Extension"),
        ("Período",           "Fevereiro – Maio de 2026"),
        ("Equipe",            "Luis Felipe · Anderson · Eduardo · Guilherme"),
        ("Repositório",       "system_sgdi_legacy_student"),
    ]
    y = h - 265
    for label, value in meta:
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor("#93c5fd"))
        canvas.drawString(MARGIN, y, label.upper() + ":")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(MARGIN + 155, y, value)
        y -= 18

    # Stats bar
    canvas.setFillColor(colors.HexColor("#1e3a8a"))
    canvas.rect(0, h * 0.22, w, 44, fill=1, stroke=0)
    stats = [
        ("6.929", "linhas adicionadas"),
        ("23", "arquivos modificados"),
        ("24", "rotas Flask"),
        ("7", "commits"),
        ("8", "features"),
    ]
    col_w = (w - 2 * MARGIN) / len(stats)
    for i, (val, lbl) in enumerate(stats):
        x = MARGIN + i * col_w + col_w / 2
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(colors.HexColor("#60a5fa"))
        canvas.drawCentredString(x, h * 0.22 + 26, val)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#93c5fd"))
        canvas.drawCentredString(x, h * 0.22 + 12, lbl.upper())

    # Bottom
    canvas.setFillColor(colors.HexColor("#172554"))
    canvas.rect(0, 0, w, h * 0.15, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(C_WHITE)
    canvas.drawCentredString(w / 2, h * 0.10,
                             "Análise completa do processo de desenvolvimento assistido por IA")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawCentredString(w / 2, h * 0.065,
                             f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    canvas.restoreState()


def page_header_footer(canvas, doc):
    w, h = A4
    pg = canvas.getPageNumber()
    if pg == 1:
        return
    canvas.saveState()
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 26, w, 26, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, h - 16, "SGDI — Relatório Técnico: Uso de IA no Desenvolvimento")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawRightString(w - MARGIN, h - 16, "Confidencial · 2026")
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 26, w - MARGIN, 26)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 14, f"Página {pg}")
    canvas.restoreState()


def build_report(output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 0.8*cm, bottomMargin=MARGIN,
    )
    S = build_styles()
    story = []

    def p(text, style="Body"):
        return Paragraph(text, S[style])

    def sp(n=8):
        return Spacer(1, n)

    def section_box(title, paragraphs, border_color=C_ACCENT):
        content = []
        if title:
            content.append(Paragraph(title, ParagraphStyle(
                "bxt", fontSize=10, leading=13, fontName="Helvetica-Bold",
                textColor=border_color, spaceAfter=5)))
        content += paragraphs
        t = Table([[content]], colWidths=[PAGE_W - 2*MARGIN])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f0f7ff")),
            ("LINEBEFORE",    (0,0), (0,-1), 3, border_color),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ]))
        return t

    def feature_block(name, date_str, color, bullets):
        hdr = Table(
            [[Paragraph(name, ParagraphStyle("fnh", fontSize=10, leading=13,
                fontName="Helvetica-Bold", textColor=C_WHITE)),
              Paragraph(date_str, ParagraphStyle("fdh", fontSize=8, leading=10,
                fontName="Helvetica", textColor=colors.HexColor("#e0e0e0"),
                alignment=TA_RIGHT))]],
            colWidths=[PAGE_W - 2*MARGIN - 3*cm, 3*cm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), color),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ]))
        items = [[Paragraph(f"• {b}", ParagraphStyle("fbi", fontSize=9, leading=14,
                    fontName="Helvetica", textColor=C_DARK, leftIndent=6,
                    spaceAfter=3))] for b in bullets]
        bdy = Table(items, colWidths=[PAGE_W - 2*MARGIN])
        bdy.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("LINEBEFORE",    (0,0), (0,-1), 3, color),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ]))
        return KeepTogether([hdr, bdy, sp(10)])

    def decision_block(name, color, desc):
        hdr = Table(
            [[Paragraph(name, ParagraphStyle("dnh", fontSize=10, leading=13,
                fontName="Helvetica-Bold", textColor=C_WHITE))]],
            colWidths=[PAGE_W - 2*MARGIN])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), color),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ]))
        bdy = Table(
            [[Paragraph(desc, ParagraphStyle("ddb", fontSize=9, leading=14,
                fontName="Helvetica", textColor=C_DARK, alignment=TA_JUSTIFY))]],
            colWidths=[PAGE_W - 2*MARGIN])
        bdy.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("LINEBEFORE",    (0,0), (0,-1), 3, color),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ]))
        return KeepTogether([hdr, bdy, sp(10)])

    # ── Capa → página em branco que a cover_page substitui ───────────────────
    story.append(PageBreak())

    # ── 1. Contexto ───────────────────────────────────────────────────────────
    story.append(p("1. Contexto e Objetivo do Projeto", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "O <b>SGDI (Sistema de Gestão de Demandas Internas)</b> é uma aplicação web desenvolvida "
        "como parte do <i>Desafio da Tecnologia</i>, cujo objetivo é centralizar, priorizar e "
        "acompanhar demandas operacionais de uma instituição. O sistema foi construído sobre uma "
        "base legada em <b>Flask/Python</b>, evoluída incrementalmente ao longo de múltiplas sessões "
        "de desenvolvimento com suporte direto de <b>Inteligência Artificial</b>."))
    story.append(sp(6))
    story.append(p(
        "A IA utilizada foi o modelo <b>Claude Sonnet 4.6</b> da Anthropic, acessado via "
        "<b>Claude Code CLI</b> integrado ao VSCode. Todas as decisões arquiteturais, implementações "
        "de código, refatorações e revisões de segurança foram conduzidas em sessões interativas "
        "entre o desenvolvedor e o modelo."))
    story.append(sp(10))
    story.append(section_box(
        "Papel da IA no Projeto",
        [p("A IA atuou como <b>co-desenvolvedor em tempo real</b>: propondo soluções, escrevendo "
           "código, identificando bugs, sugerindo melhorias de UX e gerando toda a infraestrutura "
           "de exportação, dashboard e segurança. O desenvolvedor humano definiu os requisitos, "
           "validou as entregas e tomou as decisões de produto.", "Body")],
        C_ACCENT))
    story.append(sp(16))

    # ── 2. Histórico de Commits ───────────────────────────────────────────────
    story.append(p("2. Histórico de Desenvolvimento", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "O projeto evoluiu em <b>7 commits</b> ao longo de aproximadamente <b>3 meses</b> "
        "(fevereiro a maio de 2026), com uma equipe de 4 desenvolvedores."))
    story.append(sp(10))

    commits = [
        ["#", "Data", "Autor", "Mensagem do Commit", "Escopo Principal"],
        ["1", "24/02/2026", "Anderson B.", "feat: init setup",
         "Estrutura inicial Flask, templates base, banco SQLite"],
        ["2", "25/03/2026", "Luis Felipe", "fix: resolve 17 bugs de segurança",
         "OWASP Top 10, SQL injection, XSS, sessão, validações"],
        ["3", "27/03/2026", "Anderson B.", "feat: implement features",
         "Funcionalidades core de CRUD de demandas"],
        ["4", "08/04/2026", "Eduardo H.", "Correção de Bugs e Feature 002",
         "Correções gerais e segunda feature do desafio"],
        ["5", "08/04/2026", "Guilherme W.", "subindo melhorias",
         "Melhorias incrementais de UI e fluxos"],
        ["6", "19/04/2026", "Luis Felipe", "Add user auth, CSRF, demands",
         "Login/logout, CSRF token, usuários vinculados a demandas"],
        ["7", "12/05/2026", "Luis F. + IA",
         "feat: implement dashboard gerencial, responsavel,\nhistorico de status e alertas",
         "Dashboard KPIs+gráficos, exportações, responsável,\nhistórico, badge de alertas"],
    ]
    story.append(colored_table(commits[0], commits[1:],
                               [0.8*cm, 2.2*cm, 2.6*cm, 5.4*cm, 6.5*cm], C_PRIMARY))
    story.append(sp(6))
    story.append(p(
        "* O commit #7 é o maior da história do repositório: <b>6.929 linhas adicionadas</b> "
        "em 23 arquivos.", "Caption"))
    story.append(sp(16))

    # ── 3. Arquitetura ────────────────────────────────────────────────────────
    story.append(p("3. Arquitetura Técnica", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "A IA auxiliou no desenho e implementação de uma arquitetura modular em camadas, "
        "seguindo boas práticas de separação de responsabilidades mesmo em um projeto monolítico Flask."))
    story.append(sp(10))
    story.append(p("3.1 Stack Tecnológica", "H2"))

    stack = [
        ["Camada", "Tecnologia", "Uso"],
        ["Backend",      "Python 3.11 + Flask",          "Rotas, lógica de negócio, APIs REST JSON"],
        ["Banco",        "SQLite 3 (stdlib sqlite3)",     "Persistência, migrations automáticas, seed"],
        ["Frontend",     "HTML5 + CSS3 + Vanilla JS",     "Templates Jinja2, UI responsiva, polling"],
        ["Gráficos",     "Chart.js 4.4.0 (CDN)",          "Donut por status, barras, linha temporal"],
        ["Export PDF",   "reportlab 4.4.x",               "Relatórios PDF com formatação institucional"],
        ["Export Excel", "openpyxl",                      "Planilhas com cores, cabeçalhos, larguras"],
        ["Export CSV",   "csv (stdlib)",                   "CSV UTF-8-sig para compatibilidade Excel BR"],
        ["Segurança",    "werkzeug.security + secrets",   "Hash bcrypt, CSRF token, SECRET_KEY segura"],
    ]
    story.append(colored_table(stack[0], stack[1:],
                               [2.5*cm, 4.2*cm, 10.8*cm], C_TEAL))
    story.append(sp(12))

    story.append(p("3.2 Banco de Dados — Tabelas", "H2"))
    story.append(p(
        "A IA projetou o schema completo e implementou migrations automáticas usando "
        "<code>PRAGMA table_info()</code> para verificar colunas antes de <code>ALTER TABLE</code>, "
        "garantindo compatibilidade com bancos já existentes sem intervenção manual."))
    story.append(sp(8))

    tables_db = [
        ["Tabela", "Colunas Principais", "Função"],
        ["usuarios",
         "id, username, nome, senha_hash, criado_em",
         "Cadastro de usuários com senha hash bcrypt"],
        ["demandas",
         "id, titulo, descricao, prioridade, status,\nusuario_id, responsavel_id, data_prevista, data_conclusao",
         "Core do sistema — demandas com SLA, solicitante e responsável executor"],
        ["comentarios",
         "id, demanda_id, autor, comentario, data",
         "Thread de comentários por demanda com autor e timestamp"],
        ["historico_status",
         "id, demanda_id, status_anterior, status_novo, autor, data",
         "Log auditável e automático de todas as transições de status"],
    ]
    story.append(colored_table(tables_db[0], tables_db[1:],
                               [3*cm, 5.5*cm, 9*cm], C_SUCCESS))
    story.append(PageBreak())

    # ── 4. Rotas ──────────────────────────────────────────────────────────────
    story.append(p("4. Rotas e Endpoints Implementados", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "A IA implementou <b>24 rotas</b> no total, incluindo uma camada de <b>API REST JSON</b> "
        "para o dashboard que separa a obtenção de dados do rendering de templates HTML."))
    story.append(sp(10))

    routes = [
        ["Rota", "Método", "Tipo", "Descrição"],
        ["/  e  /dashboard",                   "GET",      "HTML",  "Dashboard gerencial (rota inicial)"],
        ["/demandas",                           "GET",      "HTML",  "Lista de demandas abertas com filtros"],
        ["/concluidas",                         "GET",      "HTML",  "Lista de demandas concluídas"],
        ["/detalhes/<id>",                      "GET",      "HTML",  "Detalhe + comentários + histórico de status"],
        ["/nova_demanda",                       "GET/POST", "HTML",  "Formulário de criação de demanda"],
        ["/editar/<id>",                        "GET/POST", "HTML",  "Edição de demanda existente"],
        ["/concluir, /reabrir,\n/andamento, /cancelar", "POST", "Redirect", "Transições de status com log automático"],
        ["/deletar/<id>",                       "POST",     "Redirect", "Exclusão com verificação de autoria"],
        ["/adicionar_comentario/<id>",          "POST",     "Redirect", "Adicionar comentário em demanda"],
        ["/usuarios",                           "GET",      "HTML",  "Listagem de usuários cadastrados"],
        ["/login",                              "GET/POST", "HTML",  "Autenticação com sessão e CSRF"],
        ["/logout",                             "POST",     "Redirect", "Encerramento de sessão"],
        ["/api/dashboard/data",                 "GET",      "JSON",  "KPIs + gráficos + críticas em uma requisição"],
        ["/api/dashboard/export",               "GET",      "File",  "Exportação geral: CSV / PDF / Excel"],
        ["/api/dashboard/critical-overdue",     "GET",      "JSON",  "Demandas críticas com SLA vencido"],
        ["/api/dashboard/critical-overdue/export", "GET",  "File",  "Exportação dedicada apenas de críticas"],
        ["/api/alerts/count",                   "GET",      "JSON",  "Contagem para badge da navbar"],
    ]
    story.append(colored_table(routes[0], routes[1:],
                               [4.8*cm, 1.8*cm, 1.8*cm, 9.1*cm], C_WARNING))
    story.append(PageBreak())

    # ── 5. Features ───────────────────────────────────────────────────────────
    story.append(p("5. Features Desenvolvidas com Suporte de IA", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "Cada feature foi resultado de uma instrução em linguagem natural para a IA, que gerou "
        "o código, explicou as decisões e ajustou conforme o feedback do desenvolvedor."))
    story.append(sp(12))

    features = [
        ("Revisão e Correção de Segurança", "Sessão 1 — 25/03/2026", C_DANGER, [
            "Identificação e correção de <b>17 vulnerabilidades</b> categorizadas pelo OWASP Top 10",
            "Hash bcrypt via <code>werkzeug.security</code> para senhas de usuários",
            "Proteção contra SQL Injection com queries 100% parametrizadas",
            "Sanitização de output para prevenção de XSS via Jinja2 auto-escape",
            "Controle de sessão com expiração e regeneração de ID pós-login",
            "SECRET_KEY gerada via <code>secrets.token_hex(32)</code>",
        ]),
        ("Autenticação e Proteção CSRF", "Sessão 2 — 19/04/2026", C_PRIMARY, [
            "Sistema completo de login/logout com sessão Flask persistida",
            "Decorator <code>@login_required</code> aplicado em todas as rotas protegidas",
            "CSRF token gerado por sessão e validado em todo formulário POST",
            "Vinculação de demandas ao usuário logado via <code>usuario_id</code>",
            "Redirecionamento inteligente para a URL solicitada após login",
        ]),
        ("Dashboard Gerencial com APIs JSON", "Sessão 3 — 12/05/2026", C_ACCENT, [
            "<b>7 KPIs</b> em tempo real: total, abertas, em andamento, concluídas, atrasadas, críticas, tempo médio",
            "<b>3 gráficos</b> Chart.js: donut por status, barras horizontais por prioridade, linha de evolução temporal",
            "Filtros combinados: período (hoje/7d/30d/personalizado), responsável, prioridade, status",
            "Endpoint único <code>/api/dashboard/data</code> consolidando 3 queries em 1 requisição HTTP",
            "Auto-refresh a cada 60 segundos e granularidade diário / semanal / mensal",
            "Tabela por Responsável com total, abertas, atrasadas e críticas por executor",
        ]),
        ("Seção Críticas + Atrasadas em Destaque", "Sessão 3 — 12/05/2026", C_DANGER, [
            "Destaque visual acima dos gráficos para demandas Críticas com SLA vencido",
            "Cálculo de dias de atraso via <code>CAST(julianday('now') - julianday(data_prevista) AS INTEGER)</code>",
            "Exportação dedicada CSV/PDF/Excel cobrindo <i>apenas</i> esses casos críticos",
            "Colunas: ID, Título, Responsável, Solicitante, Dias Atrasados, SLA Previsto, Status",
            "Badge counter na seção com total de casos em tempo real",
        ]),
        ("Campo Responsável pela Execução", "Sessão 3 — 12/05/2026", C_TEAL, [
            "Nova coluna <code>responsavel_id</code> adicionada via migration automática segura",
            "Separação entre quem <i>abre</i> (solicitante) e quem <i>executa</i> (responsável)",
            "Double JOIN na tabela <code>usuarios</code> com aliases distintos: <code>u</code> e <code>resp</code>",
            "<code>COALESCE(resp.nome, 'Não atribuído')</code> para exibição segura sem responsável",
            "Select de responsável nos formulários de nova demanda e edição",
        ]),
        ("Histórico de Transições de Status", "Sessão 3 — 12/05/2026", C_PURPLE, [
            "Tabela <code>historico_status</code> com <code>ON DELETE CASCADE</code> para integridade referencial",
            "Função auxiliar <code>_registrar_historico()</code> chamada em toda transição de status",
            "Cobertura completa: criação (None → Aberta), andamento, conclusão, cancelamento, reabertura",
            "Uso de <code>cursor.lastrowid</code> para obter ID da demanda recém-criada",
            "Timeline visual na tela de detalhes com chips coloridos por status e timestamp",
        ]),
        ("Badge de Alertas na Navbar", "Sessão 3 — 12/05/2026", C_WARNING, [
            "Endpoint <code>/api/alerts/count</code> retorna contagem de críticas atrasadas",
            "Script IIFE em <code>base.html</code> faz polling a cada 60 segundos em todas as páginas",
            "Badge vermelho aparece somente quando count > 0 e desaparece automaticamente",
            "Visível em <b>todas as páginas</b> do sistema por estar no template base compartilhado",
        ]),
        ("Exportação Geral (CSV / PDF / Excel)", "Sessão 3 — 12/05/2026", C_SUCCESS, [
            "Exportação que respeita todos os filtros ativos do dashboard",
            "PDF gerado com <b>reportlab</b>: tabelas formatadas, cabeçalho e rodapé institucionais",
            "Excel com <b>openpyxl</b>: cores alternadas nas linhas, header destacado, larguras calibradas",
            "CSV com encoding <code>utf-8-sig</code> (BOM) para compatibilidade com Excel brasileiro",
            "Seção dedicada no rodapé do dashboard indicando que cobre <i>todas</i> as demandas",
        ]),
    ]

    for name, date_str, color, bullets in features:
        story.append(feature_block(name, date_str, color, bullets))

    story.append(PageBreak())

    # ── 6. Padrões de Interação ───────────────────────────────────────────────
    story.append(p("6. Padrões de Interação com a IA", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "A análise das sessões de desenvolvimento revela <b>6 padrões recorrentes</b> de "
        "colaboração humano-IA, cada um com características distintas."))
    story.append(sp(10))

    patterns = [
        ("Instrução por Resultado Esperado", C_PRIMARY,
         '"adicione uma visão dedicada: críticas + atrasadas"',
         "O desenvolvedor descreve <i>o que quer ver</i>, não <i>como implementar</i>. A IA "
         "propõe a arquitetura, escolhe as queries SQL, define o layout HTML e escreve o "
         "JavaScript — tudo a partir de um requisito funcional em linguagem natural."),
        ("Iteração por Feedback Visual", C_ACCENT,
         '"mova esses exports para o final da dashboard"',
         "Após ver o resultado no browser, o desenvolvedor ajusta posicionamento e comportamentos. "
         "A IA interpreta a correção e modifica apenas o trecho relevante sem impactar o restante."),
        ("Solicitação de Sugestões Proativas", C_TEAL,
         '"alguma sugestão de melhoria?"',
         "A IA propõe melhorias com justificativas técnicas (badge de alertas, campo responsável, "
         "histórico de status). O desenvolvedor escolhe quais aceitar e solicita a implementação."),
        ("Aplicação em Lote", C_SUCCESS,
         '"aplique as 3"',
         "Com uma instrução mínima, a IA implementa múltiplas features de forma coordenada, "
         "garantindo consistência entre backend, banco de dados, templates e CSS."),
        ("Correção por Screenshot", C_WARNING,
         '"quando eu clico em Responsável ele abre essa tela e não deveria"',
         "O desenvolvedor reporta um bug com imagem. A IA identifica a causa raiz (hack "
         "onfocus/onblur em select multiple) e aplica a correção transformando em dropdown padrão."),
        ("Geração de Documentação", C_PURPLE,
         '"gere um relatório técnico completo em PDF"',
         "A própria IA gera este documento analisando o histórico de commits, o código "
         "produzido e as interações para construir uma visão estruturada do processo."),
    ]

    for pname, pcol, pquote, pdesc in patterns:
        row = Table(
            [[Paragraph(pname, ParagraphStyle("pnh", fontSize=10, leading=13,
                fontName="Helvetica-Bold", textColor=C_WHITE))]],
            colWidths=[PAGE_W - 2*MARGIN])
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), pcol),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ]))
        body_content = [
            Paragraph(f'Prompt: <i>"{pquote}"</i>', ParagraphStyle(
                "pq", fontSize=9, leading=12, fontName="Courier",
                textColor=colors.HexColor("#374151"), spaceAfter=6)),
            Paragraph(pdesc, ParagraphStyle(
                "pd", fontSize=9, leading=14, fontName="Helvetica",
                textColor=C_MUTED, alignment=TA_JUSTIFY)),
        ]
        bdy = Table([body_content], colWidths=[PAGE_W - 2*MARGIN])
        bdy.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("LINEBEFORE",    (0,0), (0,-1), 4, pcol),
            ("TOPPADDING",    (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,-1), 9),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        story.append(KeepTogether([row, bdy, sp(8)]))

    story.append(PageBreak())

    # ── 7. Decisões Técnicas Notáveis ─────────────────────────────────────────
    story.append(p("7. Decisões Técnicas Notáveis", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "Em diversas situações, a IA tomou decisões técnicas não triviais que demonstram "
        "raciocínio além da simples geração de código."))
    story.append(sp(10))

    decisions = [
        ("Double JOIN na mesma tabela usuarios", C_TEAL,
         "Para separar solicitante (criador) de responsável (executor) sem duplicar a tabela, "
         "a IA criou dois JOINs distintos com aliases diferentes: "
         "<code>JOIN usuarios u ON u.id = d.usuario_id</code> e "
         "<code>LEFT JOIN usuarios resp ON resp.id = d.responsavel_id</code>. "
         "O LEFT JOIN garante que demandas sem responsável apareçam com "
         "<code>COALESCE(resp.nome, 'Não atribuído')</code>."),
        ("Migration não-destrutiva com PRAGMA table_info()", C_SUCCESS,
         "Em vez de recriar tabelas (operação irreversível e perigosa), a IA usa "
         "<code>PRAGMA table_info(demandas)</code> para listar as colunas existentes e só "
         "então executa <code>ALTER TABLE ADD COLUMN</code> se a coluna ainda não existia. "
         "O mesmo código inicializa bancos novos e atualiza bancos legados sem intervenção manual."),
        ("Endpoint único /api/dashboard/data", C_ACCENT,
         "Em vez de 3 chamadas paralelas (KPIs, gráficos, críticas), a IA consolidou tudo em "
         "um endpoint que executa as queries sequencialmente e retorna um JSON estruturado. "
         "Isso eliminou 2/3 das requisições HTTP, reduzindo latência e possíveis "
         "inconsistências de estado entre os componentes visuais do dashboard."),
        ("cursor.lastrowid para log na criação", C_PRIMARY,
         "Para registrar o histórico de status na criação de uma demanda era necessário saber o "
         "ID gerado pelo INSERT antes de confirmar a transação. A IA capturou o cursor retornado "
         "pelo <code>conn.execute(INSERT...)</code> e usou <code>cursor.lastrowid</code> para "
         "inserir o registro de histórico <code>None → Aberta</code> dentro da mesma transação atômica."),
        ("IIFE para isolamento do badge de alertas", C_WARNING,
         "O script de polling do badge foi encapsulado em IIFE <code>(function(){...})()</code> "
         "para isolar variáveis do escopo global da página — especialmente importante por estar "
         "em <code>base.html</code> e executar em todas as páginas do sistema."),
        ("Decorator duplo sem duplicação de lógica", C_PURPLE,
         "Para fazer <code>/</code> e <code>/dashboard</code> servirem a mesma view, a IA "
         "adicionou <code>@app.route('/')</code> como decorator adicional na função "
         "<code>dashboard()</code> existente, sem criar nova função nem duplicar código. "
         "Todos os <code>url_for('dashboard')</code> continuam funcionando — Flask resolve "
         "o nome da função, não a URL registrada."),
    ]

    for dname, dcol, ddesc in decisions:
        story.append(decision_block(dname, dcol, ddesc))

    story.append(PageBreak())

    # ── 8. Segurança ──────────────────────────────────────────────────────────
    story.append(p("8. Segurança — OWASP Top 10", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "Uma sessão inteira foi dedicada à revisão e correção de vulnerabilidades. "
        "A IA identificou e corrigiu <b>17 problemas</b> de segurança mapeados pelo OWASP Top 10."))
    story.append(sp(10))

    security = [
        ["Categoria OWASP", "Vulnerabilidade Encontrada", "Solução Aplicada pela IA"],
        ["A01 — Broken Access Control",
         "Rotas acessíveis sem autenticação",
         "Decorator @login_required em todas as rotas protegidas"],
        ["A02 — Cryptographic Failures",
         "Senha armazenada em texto puro no banco",
         "Hash bcrypt via werkzeug.security (generate/check_password_hash)"],
        ["A03 — Injection (SQL)",
         "SQL construído por concatenação de string",
         "Queries 100% parametrizadas com placeholders (?)"],
        ["A03 — Injection (XSS)",
         "Output HTML renderizado sem escape",
         "Jinja2 auto-escape ativo + validação server-side de inputs"],
        ["A05 — Security Misconfiguration",
         "SECRET_KEY hardcoded ou ausente",
         "Geração dinâmica via secrets.token_hex(32) com fallback seguro"],
        ["A07 — Auth & Session Failures",
         "Ausência de proteção contra CSRF",
         "Token CSRF por sessão validado em todo formulário POST"],
        ["A09 — Logging Failures",
         "Sem rastreabilidade de ações críticas",
         "historico_status registra toda transição com autor e timestamp"],
        ["A10 — SSRF / Controle de Acesso",
         "Qualquer usuário podia deletar demanda de outro",
         "Verificação de autoria (eh_solicitante) antes de ações destrutivas"],
    ]
    story.append(colored_table(security[0], security[1:],
                               [4*cm, 5.5*cm, 8*cm], C_DANGER))
    story.append(sp(16))

    # ── 9. Métricas ───────────────────────────────────────────────────────────
    story.append(p("9. Métricas do Código Produzido", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "Números do delta total do repositório desde o commit inicial até o estado final, "
        "incluindo todo o código escrito ou revisado com suporte de IA."))
    story.append(sp(10))

    kpi_items = [
        ("Linhas adicionadas",  "6.929", C_SUCCESS),
        ("Linhas removidas",    "335",   C_DANGER),
        ("Arquivos modificados","23",    C_PRIMARY),
        ("Rotas Flask",         "24",    C_ACCENT),
        ("Tabelas no banco",    "4",     C_TEAL),
        ("Features entregues",  "8",     C_PURPLE),
    ]
    col_w = (PAGE_W - 2*MARGIN) / len(kpi_items)
    kpi_cells = []
    for label, value, col in kpi_items:
        cell = Table(
            [[Paragraph(value, ParagraphStyle("kv", fontSize=20, leading=22,
                fontName="Helvetica-Bold", textColor=col, alignment=TA_CENTER))],
             [Paragraph(label, ParagraphStyle("kl", fontSize=7.5, leading=10,
                fontName="Helvetica", textColor=C_MUTED, alignment=TA_CENTER))]],
            colWidths=[col_w - 4])
        cell.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))
        kpi_cells.append(cell)
    kpi_row = Table([kpi_cells], colWidths=[col_w]*len(kpi_items), hAlign="LEFT")
    story.append(kpi_row)
    story.append(sp(14))

    file_metrics = [
        ["Arquivo", "Linhas", "Responsabilidade"],
        ["app.py",                    "1.567", "Rotas, lógica de negócio, APIs REST, exportações"],
        ["static/style.css",          "1.794", "Design system completo, componentes, responsividade"],
        ["templates/dashboard.html",  "504",   "Dashboard com Chart.js e JavaScript assíncrono"],
        ["test_report.py",            "950",   "Suite de testes automatizados"],
        ["database.py",               "412",   "Schema, migrations automáticas, seed de dados"],
        ["static/ui.js",              "296",   "Comportamentos globais de UI e filtros"],
        ["templates/detalhes.html",   "271",   "Detalhes da demanda, comentários, histórico de status"],
        ["templates/index.html",      "224",   "Lista de demandas abertas com filtros e paginação"],
    ]
    story.append(colored_table(file_metrics[0], file_metrics[1:],
                               [5.5*cm, 1.8*cm, 10.2*cm], C_DARK))
    story.append(PageBreak())

    # ── 10. Conclusão ─────────────────────────────────────────────────────────
    story.append(p("10. Conclusão", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "O desenvolvimento do SGDI demonstra um modelo eficaz de <b>desenvolvimento assistido "
        "por IA</b>, onde a Inteligência Artificial atua como par técnico de alto desempenho — "
        "não apenas gerando código, mas propondo arquiteturas, identificando riscos, tomando "
        "decisões técnicas fundamentadas e adaptando o resultado conforme o feedback humano."))
    story.append(sp(8))
    story.append(p(
        "A experiência evidencia que o papel do desenvolvedor humano evolui: de <i>escritor de "
        "código</i> para <i>definidor de requisitos, validador de entregas e tomador de decisões "
        "de produto</i>. A IA assume a implementação; o humano assume a direção."))
    story.append(sp(14))

    takeaways = [
        ("Velocidade", C_SUCCESS,
         "Features que levariam dias foram implementadas em horas, com qualidade de produção "
         "e sem sacrificar boas práticas de segurança ou manutenibilidade."),
        ("Qualidade", C_ACCENT,
         "O código gerado segue padrões consistentes, usa as ferramentas certas para cada problema "
         "e evita soluções hackeadas — como demonstrado nas decisões técnicas notáveis da seção 7."),
        ("Iteração Rápida", C_PRIMARY,
         "O ciclo feedback → ajuste → resultado é quase instantâneo, permitindo múltiplas "
         "iterações de UX e lógica dentro de uma única sessão de desenvolvimento."),
        ("Limitações", C_WARNING,
         "A IA não substitui o conhecimento de domínio, a validação de requisitos de negócio "
         "nem o julgamento sobre o que realmente importa para o usuário final — esses permanecem "
         "responsabilidade exclusivamente humana."),
    ]

    for tname, tcol, tdesc in takeaways:
        t = Table(
            [[Paragraph(tname, ParagraphStyle("tn", fontSize=10, leading=13,
                fontName="Helvetica-Bold", textColor=tcol)),
              Paragraph(tdesc, ParagraphStyle("td", fontSize=9, leading=14,
                fontName="Helvetica", textColor=C_DARK, alignment=TA_JUSTIFY))]],
            colWidths=[2.8*cm, PAGE_W - 2*MARGIN - 2.8*cm - 4])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("LINEBEFORE",    (0,0), (0,-1), 4, tcol),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ]))
        story.append(t)
        story.append(sp(8))

    story.append(sp(20))
    story.append(hr(C_PRIMARY, 1, 0, 12))
    sig = Table(
        [[Paragraph("Relatório gerado com suporte de <b>Claude Sonnet 4.6</b> (Anthropic) · Claude Code CLI",
                    ParagraphStyle("sig", fontSize=8, leading=11, fontName="Helvetica-Oblique",
                                   textColor=C_MUTED, alignment=TA_CENTER)),
          Paragraph(f"SGDI · {datetime.now().strftime('%d/%m/%Y')}",
                    ParagraphStyle("sig2", fontSize=8, leading=11, fontName="Helvetica",
                                   textColor=C_MUTED, alignment=TA_RIGHT))]],
        colWidths=[(PAGE_W - 2*MARGIN)*0.72, (PAGE_W - 2*MARGIN)*0.28])
    story.append(sig)

    doc.build(story,
              onFirstPage=cover_page,
              onLaterPages=page_header_footer)
    print(f"PDF gerado: {output_path}")


if __name__ == "__main__":
    build_report("relatorio_uso_ia_sgdi.pdf")
