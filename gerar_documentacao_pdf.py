"""
Gerador de documentação completa do SGDI com screenshots reais do sistema.
Inicia o Flask, captura cada tela com Playwright e monta o PDF com reportlab.
"""
import io
import os
import subprocess
import sys
import time

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Palette ───────────────────────────────────────────────────────────────────
C_PRIMARY = colors.HexColor("#1e40af")
C_ACCENT  = colors.HexColor("#3b82f6")
C_SUCCESS = colors.HexColor("#059669")
C_WARNING = colors.HexColor("#d97706")
C_DANGER  = colors.HexColor("#dc2626")
C_DARK    = colors.HexColor("#1e293b")
C_MUTED   = colors.HexColor("#64748b")
C_BG      = colors.HexColor("#f8fafc")
C_BORDER  = colors.HexColor("#e2e8f0")
C_WHITE   = colors.white
C_PURPLE  = colors.HexColor("#7c3aed")
C_TEAL    = colors.HexColor("#0d9488")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
BASE_URL = "http://localhost:5000"
SHOT_DIR = Path("doc_screenshots")
SHOT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CAPTURA DE SCREENSHOTS
# ═══════════════════════════════════════════════════════════════════════════════

def capture_screenshots():
    shots = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        def shot(name, selector=None, full=False):
            path = str(SHOT_DIR / f"{name}.png")
            if selector:
                try:
                    el = page.locator(selector).first
                    el.screenshot(path=path)
                except Exception:
                    page.screenshot(path=path, full_page=False)
            else:
                page.screenshot(path=path, full_page=full)
            shots[name] = path
            print(f"  [OK] {name}")
            return path

        def login():
            page.goto(f"{BASE_URL}/login")
            page.wait_for_load_state("networkidle")
            page.fill("input[name='username']", "admin")
            page.fill("input[name='senha']", "Admin@2024")
            shot("login")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

        print("\n[1/9] Login")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        shot("login")

        print("[2/9] Dashboard")
        login()
        page.wait_for_timeout(2500)
        shot("dashboard_full", full=True)
        # KPI section
        try:
            page.locator(".kpi-grid").first.screenshot(path=str(SHOT_DIR / "dashboard_kpis.png"))
            shots["dashboard_kpis"] = str(SHOT_DIR / "dashboard_kpis.png")
            print("  [OK] dashboard_kpis")
        except Exception:
            pass
        # Critical section
        try:
            page.locator(".card--critical-section").first.screenshot(
                path=str(SHOT_DIR / "dashboard_criticas.png"))
            shots["dashboard_criticas"] = str(SHOT_DIR / "dashboard_criticas.png")
            print("  [OK] dashboard_criticas")
        except Exception:
            pass
        # Charts
        try:
            page.locator(".chart-grid").first.screenshot(
                path=str(SHOT_DIR / "dashboard_charts.png"))
            shots["dashboard_charts"] = str(SHOT_DIR / "dashboard_charts.png")
            print("  [OK] dashboard_charts")
        except Exception:
            pass

        print("[3/9] Lista de demandas")
        page.goto(f"{BASE_URL}/demandas")
        page.wait_for_load_state("networkidle")
        shot("demandas_lista")

        print("[4/9] Nova demanda")
        page.goto(f"{BASE_URL}/nova_demanda")
        page.wait_for_load_state("networkidle")
        shot("nova_demanda")

        print("[5/9] Detalhes de demanda")
        page.goto(f"{BASE_URL}/detalhes/1")
        page.wait_for_load_state("networkidle")
        shot("detalhes", full=True)
        try:
            page.locator(".status-timeline").first.screenshot(
                path=str(SHOT_DIR / "historico_status.png"))
            shots["historico_status"] = str(SHOT_DIR / "historico_status.png")
            print("  [OK] historico_status")
        except Exception:
            pass
        try:
            page.locator(".action-stack").first.screenshot(
                path=str(SHOT_DIR / "detalhes_acoes.png"))
            shots["detalhes_acoes"] = str(SHOT_DIR / "detalhes_acoes.png")
            print("  [OK] detalhes_acoes")
        except Exception:
            pass

        print("[6/9] Editar demanda")
        page.goto(f"{BASE_URL}/editar/1")
        page.wait_for_load_state("networkidle")
        shot("editar")

        print("[7/9] Usuários")
        page.goto(f"{BASE_URL}/usuarios")
        page.wait_for_load_state("networkidle")
        shot("usuarios")

        print("[8/9] API Keys")
        page.goto(f"{BASE_URL}/api/keys")
        page.wait_for_load_state("networkidle")
        shot("api_keys")

        print("[9/9] Swagger / apidocs")
        page.goto(f"{BASE_URL}/apidocs")
        page.wait_for_timeout(2000)
        shot("swagger", full=True)
        # Concluídas
        page.goto(f"{BASE_URL}/concluidas")
        page.wait_for_load_state("networkidle")
        shot("concluidas")
        # Dashboard export section
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        try:
            page.locator(".dash-export-all").first.screenshot(
                path=str(SHOT_DIR / "dashboard_export.png"))
            shots["dashboard_export"] = str(SHOT_DIR / "dashboard_export.png")
            print("  [OK] dashboard_export")
        except Exception:
            pass

        ctx.close()
        browser.close()

    return shots


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONSTRUÇÃO DO PDF
# ═══════════════════════════════════════════════════════════════════════════════

def img(path, max_w=None, max_h=None):
    """Retorna Image do reportlab respeitando proporção."""
    if not path or not os.path.exists(path):
        return Spacer(1, 4)
    max_w = max_w or (PAGE_W - 2 * MARGIN)
    max_h = max_h or 14 * cm
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    ratio = w / h
    rw = max_w
    rh = rw / ratio
    if rh > max_h:
        rh = max_h
        rw = rh * ratio
    return Image(path, width=rw, height=rh)


def cover_page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#1e3a8a"))
    canvas.rect(0, 0, w, h * 0.32, fill=1, stroke=0)

    # Decorative circles
    for cx, cy, r, col in [
        (w - 55, h - 55, 95, "#1d4ed8"), (w - 55, h - 55, 60, "#2563eb"),
        (50, 85, 78, "#1d4ed8"), (50, 85, 50, "#1e40af"),
    ]:
        canvas.setFillColor(colors.HexColor(col))
        canvas.circle(cx, cy, r, fill=1, stroke=0)

    canvas.setFillColor(colors.HexColor("#60a5fa"))
    canvas.roundRect(MARGIN, h - 82, 200, 24, 4, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN + 10, h - 74, "DOCUMENTAÇÃO TÉCNICA · SGDI · 2026")

    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(MARGIN, h - 148, "SGDI — Sistema de Gestão")
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawString(MARGIN, h - 184, "de Demandas Internas")

    canvas.setFont("Helvetica", 13)
    canvas.setFillColor(colors.HexColor("#bfdbfe"))
    canvas.drawString(MARGIN, h - 215,
                      "Documentação completa com capturas de tela reais do sistema")

    canvas.setStrokeColor(colors.HexColor("#3b82f6"))
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, h - 232, w - MARGIN, h - 232)

    meta = [
        ("Versão",    "2.0"),
        ("Stack",     "Python · Flask · SQLite · Chart.js"),
        ("API",       "REST v1 com autenticação por API Key · Swagger UI"),
        ("Gerado em", datetime.now().strftime("%d/%m/%Y às %H:%M")),
    ]
    y = h - 265
    for label, value in meta:
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor("#93c5fd"))
        canvas.drawString(MARGIN, y, label.upper() + ":")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(MARGIN + 100, y, value)
        y -= 18

    canvas.setFillColor(colors.HexColor("#172554"))
    canvas.rect(0, 0, w, h * 0.15, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(C_WHITE)
    canvas.drawCentredString(w / 2, h * 0.10,
                             "Desafio da Tecnologia · Documentação com prints reais")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawCentredString(w / 2, h * 0.065, "Capturas geradas via Playwright · PDF via reportlab")
    canvas.restoreState()


def page_chrome(canvas, doc):
    w, h = A4
    pg = canvas.getPageNumber()
    if pg == 1:
        return
    canvas.saveState()
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 26, w, 26, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, h - 17, "SGDI — Documentação Técnica Completa")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawRightString(w - MARGIN, h - 17, "2026")
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 28, w - MARGIN, 28)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 14, f"Página {pg}")
    canvas.restoreState()


def build_styles():
    S = getSampleStyleSheet()

    def add(name, **kw):
        if name in S:
            S[name].__dict__.update(kw)
        else:
            S.add(ParagraphStyle(name=name, **kw))

    add("H1", fontSize=18, leading=22, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8)
    add("H2", fontSize=13, leading=16, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    add("H3", fontSize=11, leading=14, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    add("Body", fontSize=9.5, leading=14, textColor=C_DARK,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=5)
    add("Bullet", fontSize=9.5, leading=14, textColor=C_DARK,
        fontName="Helvetica", leftIndent=14, spaceAfter=3)
    add("Caption", fontSize=8, leading=11, textColor=C_MUTED,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=10)
    add("Code", fontSize=8, leading=12, textColor=colors.HexColor("#1e3a5f"),
        fontName="Courier", backColor=colors.HexColor("#f1f5f9"),
        leftIndent=8, rightIndent=8, spaceBefore=2, spaceAfter=4,
        borderPadding=4)
    return S


def hr(color=C_BORDER, t=0.5, sb=4, sa=6):
    return HRFlowable(width="100%", thickness=t, color=color,
                      spaceBefore=sb, spaceAfter=sa)


def section_header(title, color=C_PRIMARY):
    t = Table([[Paragraph(title, ParagraphStyle(
        "sh", fontSize=12, leading=15, fontName="Helvetica-Bold",
        textColor=C_WHITE))]],
        colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), color),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
    ]))
    return t


def feature_img(shot_path, caption, shots, max_h=11*cm):
    path = shots.get(shot_path)
    items = []
    if path and os.path.exists(path):
        items.append(img(path, max_h=max_h))
        items.append(Paragraph(f"↑ {caption}", ParagraphStyle(
            "cap", fontSize=8, leading=11, fontName="Helvetica-Oblique",
            textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=12)))
    return items


def bullets(items, S):
    return [Paragraph(f"• {i}", S["Bullet"]) for i in items]


def build_pdf(shots, output="documentacao_sgdi.pdf"):
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 0.6*cm, bottomMargin=MARGIN,
    )
    S = build_styles()
    story = []

    def p(text, style="Body"):
        return Paragraph(text, S[style])

    def sp(n=8):
        return Spacer(1, n)

    def b(items):
        return bullets(items, S)

    # ── Capa ─────────────────────────────────────────────────────────────────
    story.append(PageBreak())

    # ── Índice de Seções ─────────────────────────────────────────────────────
    story.append(p("Índice de Seções", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))

    toc_items = [
        ("1", "Visão Geral do Sistema",          C_PRIMARY),
        ("2", "Login e Autenticação",             C_PRIMARY),
        ("3", "Dashboard Gerencial",              C_ACCENT),
        ("4", "Lista de Demandas Abertas",        C_TEAL),
        ("5", "Criar Nova Demanda",               C_SUCCESS),
        ("6", "Editar Demanda",                   C_WARNING),
        ("7", "Detalhe e Histórico de Status",    C_PURPLE),
        ("8", "Demandas Concluídas",              C_MUTED),
        ("9", "Usuários e Rastreabilidade",       C_TEAL),
        ("10","API Keys — Gestão de Chaves",      C_DANGER),
        ("11","API REST Externa (v1)",            C_PRIMARY),
        ("12","Documentação Swagger",             C_ACCENT),
        ("13","Exportação de Relatórios",         C_SUCCESS),
        ("14","Banco de Dados",                   C_DARK),
        ("15","Segurança",                        C_DANGER),
    ]
    toc_rows = [[
        Paragraph(num, ParagraphStyle("tn", fontSize=9, fontName="Helvetica-Bold",
                                      textColor=col, alignment=TA_CENTER)),
        Paragraph(title, ParagraphStyle("tt", fontSize=9, fontName="Helvetica",
                                        textColor=C_DARK)),
    ] for num, title, col in toc_items]

    toc_table = Table(toc_rows, colWidths=[1.2*cm, PAGE_W - 2*MARGIN - 1.2*cm])
    toc_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS",  (0,0), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",            (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",      (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",   (0,0), (-1,-1), 6),
        ("LEFTPADDING",     (0,0), (-1,-1), 8),
        ("VALIGN",          (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 1 — VISÃO GERAL
    # ════════════════════════════════════════════════════════════════════════
    story.append(p("1. Visão Geral do Sistema", "H1"))
    story.append(hr(C_ACCENT, 1.5, 0, 10))
    story.append(p(
        "O <b>SGDI (Sistema de Gestão de Demandas Internas)</b> é uma aplicação web desenvolvida "
        "em <b>Python/Flask</b> com banco de dados <b>SQLite</b>. O sistema centraliza o registro, "
        "acompanhamento e resolução de demandas operacionais internas, com controle de acesso "
        "por usuário, priorização, SLA, histórico de status e API REST para integrações externas."))
    story.append(sp(8))

    arch_rows = [
        ["Camada", "Tecnologia", "Responsabilidade"],
        ["Backend",    "Python 3.11 + Flask",       "Rotas, lógica, APIs REST, exportações"],
        ["Banco",      "SQLite (sqlite3)",           "Persistência com migrations automáticas"],
        ["Frontend",   "HTML5 + CSS3 + Vanilla JS", "Templates Jinja2, UI responsiva"],
        ["Gráficos",   "Chart.js 4.4",              "Dashboard com donut, barras e linha temporal"],
        ["Exportação", "reportlab + openpyxl + csv","PDF, Excel e CSV das demandas"],
        ["API Docs",   "flasgger (Swagger UI)",     "Documentação interativa em /apidocs"],
        ["Testes",     "Playwright + Pillow",        "Screenshots automatizadas e relatório PDF"],
    ]
    t = Table(arch_rows, colWidths=[2.8*cm, 4.2*cm, PAGE_W - 2*MARGIN - 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("ALIGN",         (0,0), (-1,0), "CENTER"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 2 — LOGIN
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("2. Login e Autenticação"))
    story.append(sp(10))
    story.append(p(
        "A tela de login é o ponto de entrada do sistema. Toda rota é protegida pelo decorator "
        "<code>@login_required</code> — sem login válido, o usuário é redirecionado automaticamente."))
    story.append(sp(8))

    for el in feature_img("login", "Tela de login do SGDI", shots, max_h=10*cm):
        story.append(el)

    story.append(p("Como funciona:", "H3"))
    for el in b([
        "Usuário informa <b>username</b> e <b>senha</b>",
        "Senha comparada com hash bcrypt armazenado no banco — nunca texto puro",
        "Sessão Flask criada com ID do usuário, nome e CSRF token",
        "Redirecionamento automático para o <b>Dashboard Gerencial</b>",
        "Proteção CSRF em todo formulário POST (token único por sessão)",
    ]):
        story.append(el)

    story.append(sp(10))
    cred_rows = [
        ["Usuário", "Senha", "Nome"],
        ["admin",        "Admin@2024",  "Administrador"],
        ["joao.silva",   "Joao@2024",   "João Silva"],
        ["maria.santos", "Maria@2024",  "Maria Santos"],
        ["pedro.costa",  "Pedro@2024",  "Pedro Costa"],
        ["ana.lima",     "Ana@2024",    "Ana Lima"],
    ]
    ct = Table(cred_rows, colWidths=[4*cm, 4*cm, PAGE_W - 2*MARGIN - 8*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_TEAL),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 3 — DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("3. Dashboard Gerencial", C_ACCENT))
    story.append(sp(10))
    story.append(p(
        "O Dashboard é a <b>tela inicial</b> do sistema (rota <code>/</code>). "
        "Todos os dados são carregados via chamada JSON única ao endpoint "
        "<code>/api/dashboard/data</code> e atualizados automaticamente a cada <b>60 segundos</b> "
        "sem recarregar a página."))
    story.append(sp(10))

    for el in feature_img("dashboard_full", "Dashboard Gerencial completo", shots, max_h=13*cm):
        story.append(el)

    story.append(p("KPIs em tempo real", "H3"))
    for el in feature_img("dashboard_kpis", "Cards de KPI: total, abertas, em andamento, concluídas, atrasadas, críticas, tempo médio", shots, max_h=5*cm):
        story.append(el)

    for el in b([
        "<b>Total de Demandas</b> — contagem geral com filtros ativos",
        "<b>Abertas</b> — com percentual do total",
        "<b>Em Andamento</b> — demandas em execução",
        "<b>Concluídas</b> — com percentual",
        "<b>Atrasadas (SLA)</b> — status ativo com data_prevista vencida",
        "<b>Prioridade Crítica</b> — total e quantas estão atrasadas",
        "<b>Tempo Médio de Resolução</b> — média ponderada por criticidade em dias",
    ]):
        story.append(el)

    story.append(PageBreak())
    story.append(p("Seção Críticas e Atrasadas", "H3"))
    for el in feature_img("dashboard_criticas",
                          "Demandas com prioridade Crítica e SLA vencido — em destaque acima dos gráficos",
                          shots, max_h=7*cm):
        story.append(el)

    for el in b([
        "Exibida <b>acima dos gráficos</b> para máxima visibilidade",
        "Critério: prioridade Crítica + status ativo + data_prevista < hoje",
        "Mostra: ID · Título · Responsável · Solicitante · Dias Atrasados · SLA · Status",
        "Dias de atraso calculados com <code>julianday()</code> do SQLite",
        "Exportação dedicada em CSV, PDF e Excel (somente esses casos)",
    ]):
        story.append(el)

    story.append(sp(10))
    story.append(p("Gráficos", "H3"))
    for el in feature_img("dashboard_charts",
                          "Gráfico donut por status e barras por prioridade",
                          shots, max_h=7*cm):
        story.append(el)

    for el in b([
        "<b>Donut por Status</b> — distribuição visual com percentuais no tooltip",
        "<b>Barras horizontais por Prioridade</b> — volume por nível de criticidade",
        "<b>Linha de Evolução Temporal</b> — criadas vs. concluídas (diário/semanal/mensal)",
    ]):
        story.append(el)

    story.append(sp(10))
    story.append(p("Filtros disponíveis", "H3"))
    for el in b([
        "<b>Período:</b> Todos · Hoje · Últimos 7 dias · Último mês · Personalizado",
        "<b>Responsável:</b> qualquer usuário cadastrado",
        "<b>Prioridade:</b> Crítica · Alta · Média · Baixa",
        "<b>Status:</b> Aberta · Em andamento · Concluída · Cancelada",
        "Todos os filtros afetam KPIs, gráficos, tabela por responsável e exportações",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 4 — LISTA DE DEMANDAS
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("4. Lista de Demandas Abertas", C_TEAL))
    story.append(sp(10))
    story.append(p(
        "A rota <code>/demandas</code> exibe todas as demandas com status <b>Aberta</b> e "
        "<b>Em andamento</b>. A ordenação padrão é por prioridade (Crítica → Baixa), "
        "com alerta visual para demandas paradas há mais de 7 dias."))
    story.append(sp(10))

    for el in feature_img("demandas_lista", "Lista de demandas abertas com filtros e métricas", shots):
        story.append(el)

    for el in b([
        "Métricas no topo: total visível, alta prioridade, demandas paradas",
        "Filtros por prioridade e por solicitante",
        "Ordenação por prioridade (padrão) ou por data de criação",
        "Busca por título, descrição ou nome do solicitante",
        "Paginação em lotes de 6 itens (carregamento client-side via ui.js)",
        "Alerta em demandas sem atualização há mais de 7 dias",
        "Chip de status colorido: Aberta (azul) · Em andamento (âmbar)",
    ]):
        story.append(el)

    story.append(sp(10))
    story.append(p("Demandas Concluídas", "H3"))
    for el in feature_img("concluidas",
                          "Histórico de demandas concluídas e canceladas", shots, max_h=9*cm):
        story.append(el)

    story.append(p(
        "A rota <code>/concluidas</code> exibe o histórico de demandas com status "
        "<b>Concluída</b> ou <b>Cancelada</b>. Qualquer demanda pode ser reaberta "
        "diretamente da listagem."))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 5 — NOVA DEMANDA
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("5. Criar Nova Demanda", C_SUCCESS))
    story.append(sp(10))
    story.append(p(
        "Rota <code>/nova_demanda</code>. O formulário registra a demanda vinculada ao usuário "
        "logado como solicitante. Após salvar, o sistema cria automaticamente o primeiro "
        "registro no histórico de status: <b>None → Aberta</b>."))
    story.append(sp(10))

    for el in feature_img("nova_demanda", "Formulário de criação de nova demanda", shots):
        story.append(el)

    for el in b([
        "<b>Título</b> — resumo objetivo da demanda (obrigatório, máx. 200 chars)",
        "<b>Descrição</b> — contexto completo, impacto e expectativa (obrigatório)",
        "<b>Prioridade</b> — Crítica · Alta · Média · Baixa (obrigatório)",
        "<b>Prazo previsto</b> — data de SLA da demanda (opcional, alimenta indicadores)",
        "<b>Responsável pela execução</b> — quem vai executar, separado do solicitante (opcional)",
        "Solicitante preenchido automaticamente pelo usuário logado",
        "Registro automático no historico_status com autor e timestamp",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 6 — EDITAR
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("6. Editar Demanda", C_WARNING))
    story.append(sp(10))
    story.append(p(
        "Rota <code>/editar/&lt;id&gt;</code>. Somente o <b>solicitante original</b> pode "
        "acessar o formulário de edição — verificação feita no servidor, não apenas no frontend."))
    story.append(sp(10))

    for el in feature_img("editar", "Formulário de edição de demanda existente", shots):
        story.append(el)

    for el in b([
        "Campos editáveis: título, descrição, prioridade, prazo previsto e responsável",
        "Solicitante original e data de criação exibidos mas não editáveis",
        "Tentativa de acesso por outro usuário → redirecionamento com mensagem de erro",
        "Responsável pré-selecionado com o valor atual da demanda",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 7 — DETALHES
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("7. Detalhe e Histórico de Status", C_PURPLE))
    story.append(sp(10))
    story.append(p(
        "Rota <code>/detalhes/&lt;id&gt;</code>. Visão completa da demanda com todas as "
        "informações operacionais, comentários, ações contextuais e histórico completo "
        "de transições de status."))
    story.append(sp(10))

    for el in feature_img("detalhes", "Tela de detalhes completa", shots, max_h=13*cm):
        story.append(el)

    story.append(p("Ações contextuais por status", "H3"))
    for el in feature_img("detalhes_acoes", "Painel de ações — muda conforme o status atual", shots, max_h=6*cm):
        story.append(el)

    actions_rows = [
        ["Status atual", "Ações disponíveis"],
        ["Aberta",              "Iniciar andamento · Concluir · Cancelar · Editar (se solicitante)"],
        ["Em andamento",        "Concluir · Cancelar · Reabrir"],
        ["Concluída/Cancelada", "Reabrir"],
    ]
    at = Table(actions_rows, colWidths=[4*cm, PAGE_W - 2*MARGIN - 4*cm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_PURPLE),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(at)
    story.append(sp(12))

    story.append(p("Histórico de Status", "H3"))
    for el in feature_img("historico_status",
                          "Timeline de transições de status com autor e timestamp",
                          shots, max_h=6*cm):
        story.append(el)

    for el in b([
        "Toda transição de status é registrada automaticamente na tabela <code>historico_status</code>",
        "Cada registro contém: status anterior, status novo, autor e data/hora",
        "A criação da demanda gera o primeiro registro: <b>— → Aberta</b>",
        "Chips coloridos por status facilitam a leitura da linha do tempo",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 8 — CONCLUÍDAS (já inserida como sub-seção da 4)
    # SEÇÃO 9 — USUÁRIOS
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("9. Usuários e Rastreabilidade", C_TEAL))
    story.append(sp(10))
    story.append(p(
        "Rota <code>/usuarios</code>. Painel de rastreabilidade com métricas por usuário "
        "e visão global do estado das demandas distribuídas pela equipe."))
    story.append(sp(10))

    for el in feature_img("usuarios", "Painel de usuários com métricas por pessoa", shots):
        story.append(el)

    for el in b([
        "Por usuário: total de demandas, abertas, concluídas, alta prioridade abertas",
        "Barra de progresso visual mostrando percentual de demandas abertas",
        "Links diretos para filtrar o painel por usuário específico",
        "Métricas globais no topo da página",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 10 — API KEYS
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("10. API Keys — Gestão de Chaves", C_DANGER))
    story.append(sp(10))
    story.append(p(
        "Rota <code>/api/keys</code>. Interface para gerar, listar e revogar chaves de "
        "autenticação da API REST. Cada chave identifica um sistema externo e "
        "concede acesso completo aos endpoints <code>/api/v1/*</code>."))
    story.append(sp(10))

    for el in feature_img("api_keys", "Tela de gestão de API Keys", shots):
        story.append(el)

    for el in b([
        "Informe uma descrição clara (ex: \"Integração ERP\", \"App Mobile\")",
        "Clique em <b>Gerar chave</b> — a chave completa é exibida uma única vez",
        "Copie imediatamente — não será mostrada novamente por segurança",
        "Chaves são mascaradas na listagem: apenas os primeiros 8 caracteres visíveis",
        "Revogar desativa a chave imediatamente — sistemas que a usam perdem acesso",
        "Chaves revogadas ficam no histórico com status \"Revogada\"",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 11 — API REST
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("11. API REST Externa (v1)", C_PRIMARY))
    story.append(sp(10))
    story.append(p(
        "O SGDI disponibiliza uma API REST versionada em <code>/api/v1/</code> para "
        "integração com sistemas externos. Toda requisição deve incluir o header "
        "<code>X-API-Key</code> com uma chave ativa gerada em <code>/api/keys</code>."))
    story.append(sp(10))

    story.append(p("Autenticação", "H3"))
    story.append(Paragraph(
        "GET /api/v1/demandas\nHost: localhost:5000\nX-API-Key: sua-chave-aqui",
        S["Code"]))
    story.append(sp(6))

    ep_rows = [
        ["Método", "Rota", "Descrição"],
        ["GET",   "/api/v1/demandas",                    "Lista demandas com filtros (status, prioridade, responsavel_id, limit, offset)"],
        ["POST",  "/api/v1/demandas",                    "Cria nova demanda (titulo, descricao, solicitante, prioridade, data_prevista, responsavel_id)"],
        ["GET",   "/api/v1/demandas/<id>",               "Retorna detalhes completos de uma demanda"],
        ["PATCH", "/api/v1/demandas/<id>/status",        "Atualiza o status e registra no historico_status automaticamente"],
        ["GET",   "/api/v1/demandas/<id>/comentarios",   "Lista todos os comentários de uma demanda"],
        ["POST",  "/api/v1/demandas/<id>/comentarios",   "Adiciona comentário (autor, comentario)"],
        ["GET",   "/api/v1/usuarios",                    "Lista todos os usuários ativos do sistema"],
    ]
    et = Table(ep_rows, colWidths=[1.5*cm, 5.5*cm, PAGE_W - 2*MARGIN - 7*cm])
    et.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(et)
    story.append(sp(12))

    story.append(p("Formato de Resposta", "H3"))
    story.append(p("Todas as respostas seguem o mesmo envelope JSON:"))
    story.append(Paragraph(
        '{ "success": true, "data": [...], "meta": { "total": 22 } }',
        S["Code"]))
    story.append(Paragraph(
        '{ "success": false, "error": "Chave de API inválida ou desativada" }',
        S["Code"]))
    story.append(sp(10))

    story.append(p("Exemplo — Criar demanda via API", "H3"))
    story.append(Paragraph(
        'POST /api/v1/demandas\n'
        'X-API-Key: xK9mP2rQ8n...\n'
        'Content-Type: application/json\n\n'
        '{\n'
        '  "titulo": "Falha no módulo de relatórios",\n'
        '  "descricao": "Trava ao gerar relatórios com 1000+ linhas.",\n'
        '  "solicitante": "Sistema ERP",\n'
        '  "prioridade": "Alta",\n'
        '  "responsavel_id": 2,\n'
        '  "data_prevista": "2026-06-30"\n'
        '}',
        S["Code"]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 12 — SWAGGER
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("12. Documentação Swagger", C_ACCENT))
    story.append(sp(10))
    story.append(p(
        "A rota <code>/apidocs</code> exibe a interface Swagger UI gerada automaticamente "
        "pelo <b>flasgger</b>. Qualquer desenvolvedor pode visualizar todos os endpoints, "
        "parâmetros, exemplos de resposta e testar chamadas direto no browser "
        "sem precisar de ferramentas externas como Postman ou curl."))
    story.append(sp(10))

    for el in feature_img("swagger", "Interface Swagger UI — documentação interativa da API", shots, max_h=13*cm):
        story.append(el)

    for el in b([
        "Lista todos os endpoints <code>/api/v1/*</code> organizados por tag",
        "Cada endpoint mostra: método HTTP, parâmetros, body esperado e respostas",
        "Botão <b>Try it out</b> permite executar chamadas reais diretamente na interface",
        "Campo de autenticação para informar o <code>X-API-Key</code>",
        "Gerado automaticamente a partir dos docstrings YAML nas funções Flask",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 13 — EXPORTAÇÃO
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("13. Exportação de Relatórios", C_SUCCESS))
    story.append(sp(10))
    story.append(p(
        "O Dashboard oferece dois escopos de exportação independentes, "
        "ambos disponíveis em <b>CSV</b>, <b>PDF</b> e <b>Excel</b>."))
    story.append(sp(10))

    for el in feature_img("dashboard_export",
                          "Seção de exportação global no rodapé do Dashboard", shots, max_h=4*cm):
        story.append(el)

    exp_rows = [
        ["Escopo", "Rota", "Conteúdo"],
        ["Críticas + Atrasadas",
         "/api/dashboard/critical-overdue/export",
         "Somente demandas Críticas com SLA vencido. Independente dos filtros ativos."],
        ["Todas as demandas",
         "/api/dashboard/export",
         "Todas as demandas respeitando os filtros ativos (período, responsável, prioridade, status)."],
    ]
    expt = Table(exp_rows, colWidths=[3.5*cm, 5.5*cm, PAGE_W - 2*MARGIN - 9*cm])
    expt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_SUCCESS),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(expt)
    story.append(sp(12))

    for el in b([
        "<b>CSV</b> — encoding UTF-8 com BOM para compatibilidade com Excel brasileiro",
        "<b>Excel (.xlsx)</b> — linhas alternadas, header destacado, larguras calibradas por coluna",
        "<b>PDF</b> — tabela formatada com cabeçalho institucional e filtros aplicados no rodapé",
    ]):
        story.append(el)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 14 — BANCO DE DADOS
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("14. Banco de Dados", C_DARK))
    story.append(sp(10))
    story.append(p(
        "O banco de dados é um arquivo <b>SQLite</b> (<code>demandas.db</code>) criado "
        "automaticamente na inicialização. As migrations são executadas via "
        "<code>PRAGMA table_info()</code> — o sistema nunca destrói dados existentes "
        "ao adicionar novas colunas."))
    story.append(sp(10))

    db_rows = [
        ["Tabela", "Colunas principais", "Função"],
        ["usuarios",
         "id · username · nome · senha_hash",
         "Usuários com autenticação bcrypt"],
        ["demandas",
         "id · titulo · descricao · prioridade · status · usuario_id · responsavel_id · data_prevista · data_conclusao",
         "Core do sistema — separa solicitante de responsável"],
        ["comentarios",
         "id · demanda_id · comentario · autor · data",
         "Thread de comentários com ON DELETE CASCADE"],
        ["historico_status",
         "id · demanda_id · status_anterior · status_novo · autor · data",
         "Log auditável de toda transição de status"],
        ["api_keys",
         "id · chave · descricao · criado_por · ativo · criado_em",
         "Chaves de API para integração externa"],
    ]
    dbt = Table(db_rows, colWidths=[2.8*cm, 5.5*cm, PAGE_W - 2*MARGIN - 8.3*cm])
    dbt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(dbt)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # SEÇÃO 15 — SEGURANÇA
    # ════════════════════════════════════════════════════════════════════════
    story.append(section_header("15. Segurança", C_DANGER))
    story.append(sp(10))
    story.append(p(
        "O sistema implementa proteções contra as principais vulnerabilidades do "
        "<b>OWASP Top 10</b>. Uma sessão completa de revisão de segurança identificou "
        "e corrigiu 17 problemas no código legado."))
    story.append(sp(10))

    sec_rows = [
        ["Categoria OWASP", "Proteção implementada"],
        ["A01 — Broken Access Control",
         "@login_required em todas as rotas · verificação de autoria antes de editar/deletar"],
        ["A02 — Cryptographic Failures",
         "Senhas com hash bcrypt via werkzeug.security — nunca texto puro"],
        ["A03 — Injection (SQL)",
         "Queries 100% parametrizadas com placeholders ? — sem concatenação de string"],
        ["A03 — Injection (XSS)",
         "Jinja2 auto-escape ativo em todos os templates HTML"],
        ["A05 — Security Misconfiguration",
         "SECRET_KEY gerada via secrets.token_hex(32) — nunca hardcoded"],
        ["A07 — Auth Failures",
         "CSRF token único por sessão validado em todo formulário POST"],
        ["A09 — Logging Failures",
         "historico_status registra toda ação crítica com autor e timestamp"],
        ["API — Auth",
         "X-API-Key validada em banco antes de qualquer operação nos endpoints /api/v1/*"],
    ]
    st = Table(sec_rows, colWidths=[4.5*cm, PAGE_W - 2*MARGIN - 4.5*cm])
    st.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DANGER),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_BG]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_DARK),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(st)
    story.append(sp(20))
    story.append(hr(C_PRIMARY, 1, 0, 14))

    story.append(Paragraph(
        f"SGDI v2.0 — Documentação gerada automaticamente em "
        f"{datetime.now().strftime('%d/%m/%Y às %H:%M')} · "
        "Screenshots capturadas via Playwright · PDF via reportlab",
        ParagraphStyle("footer", fontSize=8, leading=11, fontName="Helvetica-Oblique",
                       textColor=C_MUTED, alignment=TA_CENTER)))

    doc.build(story, onFirstPage=cover_page, onLaterPages=page_chrome)
    print(f"\nPDF gerado: {output}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def wait_for_server(url, timeout=15):
    for _ in range(timeout * 2):
        try:
            requests.get(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    print("=== Gerador de Documentação SGDI ===\n")

    print("Iniciando servidor Flask...")
    server = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_server(f"{BASE_URL}/login"):
        print("ERRO: servidor não respondeu. Encerrando.")
        server.terminate()
        sys.exit(1)
    print("Servidor ativo.\n")

    try:
        print("Capturando screenshots...")
        shots = capture_screenshots()
        print(f"\n{len(shots)} screenshots capturadas.\n")

        print("Gerando PDF...")
        build_pdf(shots, "documentacao_sgdi.pdf")
        print("\nConcluído.")
    finally:
        server.terminate()
