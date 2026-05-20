"""
Gerador de documentação completa da API REST do SGDI.
Inicia Flask, cria chave de teste, executa todos os endpoints (sucessos + erros),
captura screenshots e monta PDF profissional com reportlab.
"""
import io
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
C_CODE_BG = colors.HexColor("#0f172a")
C_CODE_FG = colors.HexColor("#e2e8f0")
C_GREEN   = colors.HexColor("#22c55e")
C_RED     = colors.HexColor("#f87171")
C_YELLOW  = colors.HexColor("#fbbf24")

PAGE_W, PAGE_H = A4
MARGIN   = 1.8 * cm
BASE_URL = "http://localhost:5000"
DB_PATH  = "demandas.db"
SHOT_DIR = Path("api_doc_shots")
SHOT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SERVIDOR FLASK
# ═══════════════════════════════════════════════════════════════════════════════

def start_flask():
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        try:
            requests.get(f"{BASE_URL}/login", timeout=2)
            return proc
        except Exception:
            time.sleep(1)
    raise RuntimeError("Flask nao iniciou")


def stop_flask(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PREPARAR DADOS DE TESTE NO BANCO
# ═══════════════════════════════════════════════════════════════════════════════

TEST_KEY = secrets.token_urlsafe(32)
TEST_KEY_DESC = "Chave de Documentação Automatizada"
CREATED_DEMAND_ID = None


def setup_test_data():
    """Insere chave de teste e demanda de exemplo diretamente no banco."""
    global CREATED_DEMAND_ID
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Limpar chaves antigas do mesmo nome
    conn.execute("DELETE FROM api_keys WHERE descricao = ?", (TEST_KEY_DESC,))

    # Inserir chave de teste
    conn.execute(
        "INSERT INTO api_keys (chave, descricao, criado_por, ativo) VALUES (?, ?, 1, 1)",
        (TEST_KEY, TEST_KEY_DESC),
    )

    # Verificar se já há demandas; se não, criar uma de exemplo
    total = conn.execute("SELECT COUNT(*) FROM demandas").fetchone()[0]
    if total == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO demandas (titulo, descricao, solicitante, usuario_id, prioridade, status, data_criacao) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            ("Demanda de exemplo", "Criada para testes", "Sistema", "Alta", "Aberta", now),
        )

    conn.commit()
    conn.close()
    print(f"[OK] Chave de teste configurada: {TEST_KEY[:12]}...")


def cleanup_test_data():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM api_keys WHERE descricao = ?", (TEST_KEY_DESC,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EXECUTAR CHAMADAS REAIS À API E CAPTURAR RESPOSTAS
# ═══════════════════════════════════════════════════════════════════════════════

def headers_ok():
    return {"X-API-Key": TEST_KEY, "Content-Type": "application/json"}

def headers_no_key():
    return {"Content-Type": "application/json"}

def headers_bad_key():
    return {"X-API-Key": "chave-invalida-abc123", "Content-Type": "application/json"}


def fmt(resp):
    """Formata resposta HTTP como string legível."""
    try:
        body = json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception:
        body = resp.text[:500]
    return resp.status_code, body


def run_api_tests():
    """Executa todos os cenários de teste e retorna resultados."""
    results = {}
    base = f"{BASE_URL}/api/v1"

    print("\n[API] Executando testes...")

    # ── GET /api/v1/demandas ──────────────────────────────────────────────────
    r = requests.get(f"{base}/demandas", headers=headers_ok())
    results["demandas_list_ok"] = fmt(r)
    print(f"  GET /demandas          -> {r.status_code}")

    r = requests.get(f"{base}/demandas?status=Aberta&limit=2", headers=headers_ok())
    results["demandas_list_filter"] = fmt(r)
    print(f"  GET /demandas?status=  -> {r.status_code}")

    r = requests.get(f"{base}/demandas", headers=headers_no_key())
    results["demandas_list_401"] = fmt(r)
    print(f"  GET /demandas (sem key)-> {r.status_code}")

    r = requests.get(f"{base}/demandas", headers=headers_bad_key())
    results["demandas_list_403"] = fmt(r)
    print(f"  GET /demandas (bad key)-> {r.status_code}")

    # ── POST /api/v1/demandas ─────────────────────────────────────────────────
    payload_ok = {
        "titulo": "Integração com ERP — módulo fiscal",
        "descricao": "O módulo de notas fiscais do ERP precisa enviar demandas automaticamente ao receber erros de rejeição da SEFAZ. Integração via API REST.",
        "solicitante": "Sistema ERP Totvs",
        "prioridade": "Alta",
        "data_prevista": "2026-06-30",
    }
    r = requests.post(f"{base}/demandas", headers=headers_ok(), json=payload_ok)
    results["demandas_create_ok"] = fmt(r)
    global CREATED_DEMAND_ID
    try:
        CREATED_DEMAND_ID = r.json()["data"]["id"]
    except Exception:
        CREATED_DEMAND_ID = 1
    print(f"  POST /demandas (ok)    -> {r.status_code}  id={CREATED_DEMAND_ID}")

    payload_missing = {"titulo": "Só título"}
    r = requests.post(f"{base}/demandas", headers=headers_ok(), json=payload_missing)
    results["demandas_create_400"] = fmt(r)
    print(f"  POST /demandas (400)   -> {r.status_code}")

    payload_bad_prio = {**payload_ok, "prioridade": "Urgentissima"}
    r = requests.post(f"{base}/demandas", headers=headers_ok(), json=payload_bad_prio)
    results["demandas_create_400b"] = fmt(r)
    print(f"  POST /demandas (prio?) -> {r.status_code}")

    r = requests.post(f"{base}/demandas", headers=headers_no_key(), json=payload_ok)
    results["demandas_create_401"] = fmt(r)
    print(f"  POST /demandas (401)   -> {r.status_code}")

    # ── GET /api/v1/demandas/{id} ─────────────────────────────────────────────
    r = requests.get(f"{base}/demandas/{CREATED_DEMAND_ID}", headers=headers_ok())
    results["demandas_get_ok"] = fmt(r)
    print(f"  GET /demandas/{CREATED_DEMAND_ID}      -> {r.status_code}")

    r = requests.get(f"{base}/demandas/99999", headers=headers_ok())
    results["demandas_get_404"] = fmt(r)
    print(f"  GET /demandas/99999    -> {r.status_code}")

    r = requests.get(f"{base}/demandas/{CREATED_DEMAND_ID}", headers=headers_no_key())
    results["demandas_get_401"] = fmt(r)

    # ── PATCH /api/v1/demandas/{id}/status ───────────────────────────────────
    r = requests.patch(
        f"{base}/demandas/{CREATED_DEMAND_ID}/status",
        headers=headers_ok(),
        json={"status": "Em andamento", "autor": "Sistema ERP"},
    )
    results["status_patch_ok"] = fmt(r)
    print(f"  PATCH /demandas/status -> {r.status_code}")

    r = requests.patch(
        f"{base}/demandas/{CREATED_DEMAND_ID}/status",
        headers=headers_ok(),
        json={"status": "StatusInvalido"},
    )
    results["status_patch_400"] = fmt(r)
    print(f"  PATCH status (invalid) -> {r.status_code}")

    r = requests.patch(
        f"{base}/demandas/99999/status",
        headers=headers_ok(),
        json={"status": "Concluida"},
    )
    results["status_patch_404"] = fmt(r)
    print(f"  PATCH status 404       -> {r.status_code}")

    r = requests.patch(
        f"{base}/demandas/{CREATED_DEMAND_ID}/status",
        headers=headers_no_key(),
        json={"status": "Concluida"},
    )
    results["status_patch_401"] = fmt(r)

    # ── GET /api/v1/demandas/{id}/comentarios ─────────────────────────────────
    r = requests.get(f"{base}/demandas/{CREATED_DEMAND_ID}/comentarios", headers=headers_ok())
    results["comentarios_list_ok"] = fmt(r)
    print(f"  GET /comentarios       -> {r.status_code}")

    r = requests.get(f"{base}/demandas/99999/comentarios", headers=headers_ok())
    results["comentarios_list_404"] = fmt(r)
    print(f"  GET /comentarios 404   -> {r.status_code}")

    # ── POST /api/v1/demandas/{id}/comentarios ────────────────────────────────
    r = requests.post(
        f"{base}/demandas/{CREATED_DEMAND_ID}/comentarios",
        headers=headers_ok(),
        json={"autor": "Sistema ERP", "comentario": "Demanda recebida. Equipe notificada. Previsão de resolução: 48h."},
    )
    results["comentarios_create_ok"] = fmt(r)
    print(f"  POST /comentarios (ok) -> {r.status_code}")

    r = requests.post(
        f"{base}/demandas/{CREATED_DEMAND_ID}/comentarios",
        headers=headers_ok(),
        json={"autor": "Sistema ERP"},
    )
    results["comentarios_create_400"] = fmt(r)
    print(f"  POST /comentarios 400  -> {r.status_code}")

    r = requests.post(
        f"{base}/demandas/99999/comentarios",
        headers=headers_ok(),
        json={"autor": "ERP", "comentario": "teste"},
    )
    results["comentarios_create_404"] = fmt(r)
    print(f"  POST /comentarios 404  -> {r.status_code}")

    r = requests.post(
        f"{base}/demandas/{CREATED_DEMAND_ID}/comentarios",
        headers=headers_no_key(),
        json={"autor": "ERP", "comentario": "teste"},
    )
    results["comentarios_create_401"] = fmt(r)

    # ── GET /api/v1/usuarios ──────────────────────────────────────────────────
    r = requests.get(f"{base}/usuarios", headers=headers_ok())
    results["usuarios_ok"] = fmt(r)
    print(f"  GET /usuarios          -> {r.status_code}")

    r = requests.get(f"{base}/usuarios", headers=headers_no_key())
    results["usuarios_401"] = fmt(r)
    print(f"  GET /usuarios 401      -> {r.status_code}")

    print(f"\n[OK] {len(results)} cenarios testados.")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SCREENSHOTS
# ═══════════════════════════════════════════════════════════════════════════════

def capture_screenshots():
    shots = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        def shot(name, full=False):
            path = str(SHOT_DIR / f"{name}.png")
            page.screenshot(path=path, full_page=full)
            shots[name] = path
            print(f"  [OK] {name}")

        def login():
            page.goto(f"{BASE_URL}/login")
            page.wait_for_load_state("networkidle")
            page.fill("input[name='username']", "admin")
            page.fill("input[name='senha']", "Admin@2024")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

        print("\n[Screenshots] Capturando...")

        # Login page
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        shot("login")

        # Login preenchido
        page.fill("input[name='username']", "admin")
        page.fill("input[name='senha']", "Admin@2024")
        shot("login_filled")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        # API Keys page (lista)
        page.goto(f"{BASE_URL}/api/keys")
        page.wait_for_load_state("networkidle")
        shot("api_keys_list", full=True)

        # Formulário de criação em destaque
        try:
            page.locator(".card").first.screenshot(path=str(SHOT_DIR / "api_keys_form.png"))
            shots["api_keys_form"] = str(SHOT_DIR / "api_keys_form.png")
            print("  [OK] api_keys_form")
        except Exception:
            pass

        # Swagger UI
        page.goto(f"{BASE_URL}/apidocs")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        shot("swagger_full", full=True)
        shot("swagger_top")

        # Swagger expandido — GET /demandas
        try:
            page.locator("text=/api/v1/demandas").first.click()
            page.wait_for_timeout(1500)
            shot("swagger_demandas_expanded")
        except Exception:
            pass

        ctx.close()
        browser.close()

    print(f"  Total: {len(shots)} screenshots")
    return shots


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ESTILOS PDF
# ═══════════════════════════════════════════════════════════════════════════════

def build_styles():
    S = getSampleStyleSheet()

    def add(name, **kw):
        if name in S:
            S[name].__dict__.update(kw)
        else:
            S.add(ParagraphStyle(name=name, **kw))

    add("Title", fontSize=28, leading=34, textColor=C_WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("H1", fontSize=17, leading=21, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=22, spaceAfter=8)
    add("H2", fontSize=13, leading=16, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    add("H3", fontSize=11, leading=14, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    add("Body", fontSize=9.5, leading=14, textColor=C_DARK,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=5)
    add("Bullet", fontSize=9.5, leading=14, textColor=C_DARK,
        fontName="Helvetica", leftIndent=14, spaceAfter=3)
    add("Caption", fontSize=8, leading=11, textColor=C_MUTED,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=10)
    add("Code", fontSize=7.8, leading=11, textColor=C_CODE_FG,
        fontName="Courier", backColor=C_CODE_BG,
        leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=6,
        borderPadding=8)
    add("CodeInline", fontSize=8, leading=12, textColor=colors.HexColor("#1d4ed8"),
        fontName="Courier")
    add("StatusOk", fontSize=9, leading=12, textColor=C_SUCCESS,
        fontName="Helvetica-Bold")
    add("StatusErr", fontSize=9, leading=12, textColor=C_DANGER,
        fontName="Helvetica-Bold")
    add("Endpoint", fontSize=11, leading=14, textColor=C_WHITE,
        fontName="Courier-Bold")
    add("TOC", fontSize=10, leading=15, textColor=C_PRIMARY,
        fontName="Helvetica", leftIndent=10, spaceAfter=2)
    add("TOCSub", fontSize=9, leading=13, textColor=C_MUTED,
        fontName="Helvetica", leftIndent=22, spaceAfter=1)
    return S


# ═══════════════════════════════════════════════════════════════════════════════
# 6. HELPERS VISUAIS
# ═══════════════════════════════════════════════════════════════════════════════

def hr(color=C_BORDER, t=0.5, sb=4, sa=6):
    return HRFlowable(width="100%", thickness=t, color=color,
                      spaceBefore=sb, spaceAfter=sa)


def sp(h=6):
    return Spacer(1, h)


def method_badge(method, S):
    """Retorna tabela colorida com o método HTTP."""
    colors_map = {
        "GET":   (colors.HexColor("#1d4ed8"), colors.HexColor("#dbeafe")),
        "POST":  (colors.HexColor("#15803d"), colors.HexColor("#dcfce7")),
        "PATCH": (colors.HexColor("#b45309"), colors.HexColor("#fef3c7")),
        "DELETE":(colors.HexColor("#b91c1c"), colors.HexColor("#fee2e2")),
    }
    fg, bg = colors_map.get(method, (C_DARK, C_BG))
    t = Table([[Paragraph(method, ParagraphStyle(
        f"mb_{method}", fontSize=9, fontName="Helvetica-Bold",
        textColor=fg, alignment=TA_CENTER))]],
        colWidths=[1.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, fg),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [3,3,3,3]),
    ]))
    return t


def endpoint_header(method, path, description, S):
    """Bloco visual de cabeçalho de endpoint."""
    method_colors = {
        "GET":   colors.HexColor("#1e3a8a"),
        "POST":  colors.HexColor("#14532d"),
        "PATCH": colors.HexColor("#78350f"),
    }
    bg = method_colors.get(method, C_PRIMARY)

    label_style = ParagraphStyle(
        f"el_{method}", fontSize=8, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#93c5fd"), leading=10)
    path_style = ParagraphStyle(
        f"ep_{method}", fontSize=12, fontName="Courier-Bold",
        textColor=C_WHITE, leading=15)
    desc_style = ParagraphStyle(
        f"ed_{method}", fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#cbd5e1"), leading=12)

    method_tag_colors = {
        "GET":   colors.HexColor("#3b82f6"),
        "POST":  colors.HexColor("#22c55e"),
        "PATCH": colors.HexColor("#f59e0b"),
    }
    mtag_bg = method_tag_colors.get(method, C_ACCENT)

    tag_style = ParagraphStyle(
        f"etag_{method}", fontSize=9, fontName="Helvetica-Bold",
        textColor=C_WHITE, alignment=TA_CENTER, leading=11)

    t = Table([
        [
            Table([[Paragraph(method, tag_style)]],
                  colWidths=[1.4*cm],
                  style=TableStyle([
                      ("BACKGROUND", (0,0), (-1,-1), mtag_bg),
                      ("TOPPADDING", (0,0), (-1,-1), 4),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                      ("LEFTPADDING", (0,0), (-1,-1), 4),
                      ("RIGHTPADDING", (0,0), (-1,-1), 4),
                  ])),
            [Paragraph(path, path_style), Paragraph(description, desc_style)],
        ]
    ], colWidths=[1.8*cm, PAGE_W - 2*MARGIN - 1.8*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (0,-1),  4),
        ("BOTTOMPADDING", (0,0), (0,-1),  4),
    ]))
    return t


def response_block(status_code, body_str, S, label=""):
    """Bloco visual de resposta HTTP com status colorido."""
    is_ok = status_code < 400
    status_color = C_SUCCESS if is_ok else C_DANGER
    border_color = colors.HexColor("#bbf7d0") if is_ok else colors.HexColor("#fecaca")

    hdr_style = ParagraphStyle(
        f"rh_{status_code}", fontSize=9, fontName="Helvetica-Bold",
        textColor=status_color, leading=12)

    # Truncar respostas muito longas
    lines = body_str.strip().split("\n")
    if len(lines) > 40:
        lines = lines[:40] + ["  ...(truncado)"]
    body_display = "\n".join(lines)

    code_style = ParagraphStyle(
        f"rc_{status_code}", fontSize=7.5, fontName="Courier",
        textColor=C_CODE_FG, backColor=C_CODE_BG, leading=11,
        leftIndent=10, rightIndent=10, spaceBefore=2, spaceAfter=2,
        borderPadding=8)

    items = [
        Paragraph(f"HTTP {status_code}  {label}", hdr_style),
        sp(3),
        Paragraph(body_display.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style),
        sp(4),
    ]
    return items


def params_table(rows, S):
    """Tabela de parâmetros do endpoint."""
    header = [
        Paragraph("Parâmetro", ParagraphStyle("ph", fontSize=8.5, fontName="Helvetica-Bold",
                                               textColor=C_WHITE)),
        Paragraph("Tipo", ParagraphStyle("pt", fontSize=8.5, fontName="Helvetica-Bold",
                                          textColor=C_WHITE)),
        Paragraph("Obrig.", ParagraphStyle("po", fontSize=8.5, fontName="Helvetica-Bold",
                                            textColor=C_WHITE)),
        Paragraph("Descrição", ParagraphStyle("pd", fontSize=8.5, fontName="Helvetica-Bold",
                                               textColor=C_WHITE)),
    ]
    data = [header]
    for i, (name, typ, req, desc) in enumerate(rows):
        bg = C_BG if i % 2 == 0 else C_WHITE
        req_color = C_DANGER if req == "Sim" else C_MUTED
        data.append([
            Paragraph(f"<b>{name}</b>", ParagraphStyle(f"pn{i}", fontSize=8,
                       fontName="Courier", textColor=C_PRIMARY)),
            Paragraph(typ, ParagraphStyle(f"pt{i}", fontSize=8, fontName="Helvetica",
                       textColor=C_MUTED)),
            Paragraph(req, ParagraphStyle(f"pr{i}", fontSize=8, fontName="Helvetica-Bold",
                       textColor=req_color)),
            Paragraph(desc, ParagraphStyle(f"pd{i}", fontSize=8, fontName="Helvetica",
                       textColor=C_DARK)),
        ])
    w = PAGE_W - 2 * MARGIN
    t = Table(data, colWidths=[w*0.22, w*0.12, w*0.10, w*0.56])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def status_codes_table(rows, S):
    """Tabela resumo de status codes."""
    header = [
        Paragraph("Código", ParagraphStyle("sch", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE)),
        Paragraph("Significado", ParagraphStyle("smh", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE)),
        Paragraph("Quando ocorre", ParagraphStyle("swh", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE)),
    ]
    data = [header]
    code_colors = {
        "200": C_SUCCESS, "201": C_SUCCESS,
        "400": C_WARNING, "401": C_DANGER, "403": C_DANGER, "404": C_WARNING,
    }
    for i, (code, meaning, when) in enumerate(rows):
        color = code_colors.get(code, C_DARK)
        bg = C_BG if i % 2 == 0 else C_WHITE
        data.append([
            Paragraph(code, ParagraphStyle(f"sc{i}", fontSize=9, fontName="Helvetica-Bold",
                       textColor=color, alignment=TA_CENTER)),
            Paragraph(meaning, ParagraphStyle(f"sm{i}", fontSize=8.5, fontName="Helvetica-Bold",
                       textColor=C_DARK)),
            Paragraph(when, ParagraphStyle(f"sw{i}", fontSize=8.5, fontName="Helvetica",
                       textColor=C_MUTED)),
        ])
    w = PAGE_W - 2 * MARGIN
    t = Table(data, colWidths=[w*0.12, w*0.28, w*0.60])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("ALIGN",         (0,0), (0,-1),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def img_block(path, caption, max_h=10*cm):
    items = []
    if path and os.path.exists(path):
        from PIL import Image as PILImage
        with PILImage.open(path) as pil:
            w_px, h_px = pil.size
        aspect = h_px / w_px
        avail_w = PAGE_W - 2 * MARGIN
        img_h = min(avail_w * aspect, max_h)
        img_w = img_h / aspect
        items.append(Image(path, width=img_w, height=img_h))
        cap = ParagraphStyle("imgcap", fontSize=7.5, fontName="Helvetica-Oblique",
                              textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=10)
        items.append(Paragraph(caption, cap))
        items.append(sp(4))
    return items


def info_box(text, color=C_ACCENT, S=None):
    """Caixa de aviso/info destacada."""
    style = ParagraphStyle("ib", fontSize=9, fontName="Helvetica",
                           textColor=C_DARK, leftIndent=10, rightIndent=10,
                           spaceBefore=4, spaceAfter=4, leading=13,
                           backColor=colors.HexColor("#eff6ff"),
                           borderPadding=8)
    t = Table([[Paragraph(text, style)]], colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING",(0,0), (-1,-1), 12),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LINEBEFORE",  (0,0), (-1,-1), 3, color),
    ]))
    return t


def warn_box(text, S=None):
    style = ParagraphStyle("wb", fontSize=9, fontName="Helvetica",
                           textColor=colors.HexColor("#78350f"),
                           leftIndent=10, rightIndent=10,
                           spaceBefore=4, spaceAfter=4, leading=13,
                           borderPadding=8)
    t = Table([[Paragraph(text, style)]], colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#fffbeb")),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LINEBEFORE",   (0,0), (-1,-1), 3, C_WARNING),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PÁGINAS ESPECIAIS
# ═══════════════════════════════════════════════════════════════════════════════

def cover_page(canvas, doc):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # Fundo degradê
    from reportlab.lib.colors import HexColor
    canvas.setFillColor(HexColor("#0f172a"))
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # Faixa superior decorativa
    canvas.setFillColor(HexColor("#1e40af"))
    canvas.rect(0, h - 90, w, 90, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#3b82f6"))
    canvas.rect(0, h - 95, w, 8, fill=1, stroke=0)

    # Logo/Badge
    canvas.setFillColor(HexColor("#3b82f6"))
    canvas.roundRect(MARGIN, h - 75, 60, 55, 8, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(MARGIN + 30, h - 52, "API")

    # Título principal
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 32)
    canvas.drawString(MARGIN + 75, h - 42, "SGDI — Documentação de API")
    canvas.setFont("Helvetica", 14)
    canvas.setFillColor(HexColor("#93c5fd"))
    canvas.drawString(MARGIN + 75, h - 62, "Guia completo de integração via REST API")

    # Linha divisória
    canvas.setStrokeColor(HexColor("#1e40af"))
    canvas.setLineWidth(1)
    canvas.line(MARGIN, h - 110, w - MARGIN, h - 110)

    # Seções do documento (índice visual)
    sections = [
        "01  Visão Geral da API",
        "02  Criando Chaves de API (API Keys)",
        "03  Autenticação — Header X-API-Key",
        "04  Formato de Resposta JSON",
        "05  Todos os Códigos de Status",
        "06  GET  /api/v1/demandas",
        "07  POST /api/v1/demandas",
        "08  GET  /api/v1/demandas/{id}",
        "09  PATCH /api/v1/demandas/{id}/status",
        "10  GET  /api/v1/demandas/{id}/comentarios",
        "11  POST /api/v1/demandas/{id}/comentarios",
        "12  GET  /api/v1/usuarios",
        "13  Interface Swagger UI",
        "14  Exemplos em PowerShell e cURL",
    ]
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(HexColor("#64748b"))
    canvas.drawString(MARGIN, h - 135, "CONTEÚDO DESTE DOCUMENTO")

    canvas.setFont("Courier", 9)
    canvas.setFillColor(HexColor("#94a3b8"))
    for i, sec in enumerate(sections):
        col = 0 if i < 7 else 1
        row = i if i < 7 else i - 7
        x = MARGIN + col * (w / 2 - MARGIN)
        y = h - 155 - row * 18
        canvas.drawString(x, y, sec)

    # Badges de tecnologia
    techs = ["Flask 3.x", "SQLite 3", "Python 3.12", "Flasgger/Swagger", "REST/JSON"]
    bx = MARGIN
    by = 120
    canvas.setFont("Helvetica-Bold", 8)
    for tech in techs:
        tw = canvas.stringWidth(tech, "Helvetica-Bold", 8) + 16
        canvas.setFillColor(HexColor("#1e3a8a"))
        canvas.roundRect(bx, by, tw, 20, 5, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#93c5fd"))
        canvas.drawString(bx + 8, by + 6, tech)
        bx += tw + 8

    # Data e versão
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(HexColor("#475569"))
    canvas.drawString(MARGIN, 80, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawString(MARGIN, 65, "Versão da API: 1.0.0")
    canvas.drawString(MARGIN, 50, "Sistema: SGDI v2.0 — Sistema de Gestão de Demandas Internas")

    canvas.setFillColor(HexColor("#1e40af"))
    canvas.rect(0, 0, w, 30, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#93c5fd"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w/2, 11, "SGDI — Documentação Técnica API REST — Uso Interno")

    canvas.restoreState()


def page_template(canvas, doc):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 28, w, 28, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, h - 17, "SGDI — Documentação API REST v1.0")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawRightString(w - MARGIN, h - 17, "api.sgdi.internal")
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 28, w - MARGIN, 28)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w/2, 14, f"Página {doc.page}")
    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CONSTRUÇÃO DO PDF
# ═══════════════════════════════════════════════════════════════════════════════

def build_pdf(results, shots, output_path):
    print("\n[PDF] Construindo documento...")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 10, bottomMargin=MARGIN,
        title="SGDI — Documentação API REST",
        author="SGDI System",
    )

    S = build_styles()
    story = []

    def p(text, style="Body"):
        return Paragraph(text, S[style])

    def section_title(num, title, color=C_PRIMARY):
        bg_map = {
            C_PRIMARY: colors.HexColor("#1e3a8a"),
            C_SUCCESS: colors.HexColor("#14532d"),
            C_WARNING: colors.HexColor("#78350f"),
            C_DANGER:  colors.HexColor("#7f1d1d"),
            C_PURPLE:  colors.HexColor("#4c1d95"),
            C_TEAL:    colors.HexColor("#134e4a"),
        }
        bg = bg_map.get(color, colors.HexColor("#1e3a8a"))
        badge_style = ParagraphStyle(f"st_badge_{num}", fontSize=10,
            fontName="Helvetica-Bold", textColor=color, alignment=TA_CENTER)
        title_style = ParagraphStyle(f"st_title_{num}", fontSize=14,
            fontName="Helvetica-Bold", textColor=C_WHITE, leading=17)
        t = Table([[
            Table([[Paragraph(f"{num:02d}", badge_style)]],
                  colWidths=[0.9*cm],
                  style=TableStyle([
                      ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#0f172a")),
                      ("TOPPADDING", (0,0), (-1,-1), 5),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                  ])),
            Paragraph(title, title_style),
        ]], colWidths=[1.3*cm, PAGE_W - 2*MARGIN - 1.3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        return t

    # ── CAPA ─────────────────────────────────────────────────────────────────
    story.append(PageBreak())  # força capa em página separada

    # ── S01: VISÃO GERAL ─────────────────────────────────────────────────────
    story.append(section_title(1, "Visão Geral da API"))
    story.append(sp(10))
    story.append(p(
        "A API REST do SGDI permite que sistemas externos criem, consultem e atualizem demandas "
        "programaticamente, sem depender da interface web. É ideal para integrações com ERPs, "
        "scripts de automação, apps mobile ou qualquer sistema que precise abrir ou acompanhar "
        "demandas de forma automatizada."
    ))
    story.append(sp(8))

    # Tabela de características gerais
    info_rows = [
        ["Base URL", f"{BASE_URL}/api/v1"],
        ["Protocolo", "HTTP/HTTPS"],
        ["Formato",   "JSON (application/json)"],
        ["Autenticação", "Header X-API-Key"],
        ["Versão",    "1.0.0"],
        ["Endpoints", "7 endpoints em 3 grupos (Demandas, Comentários, Usuários)"],
    ]
    header_s = ParagraphStyle("ih", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    val_s    = ParagraphStyle("iv", fontSize=9, fontName="Courier", textColor=C_DARK)
    data = [[Paragraph(k, header_s), Paragraph(v, val_s)] for k, v in info_rows]
    w = PAGE_W - 2*MARGIN
    t = Table(data, colWidths=[w*0.30, w*0.70])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_PRIMARY, colors.HexColor("#1e3a8a")]),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_BG, C_WHITE]),
        ("BACKGROUND",     (0,0), (0,-1),  C_PRIMARY),
        ("TOPPADDING",     (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 6),
        ("LEFTPADDING",    (0,0), (-1,-1), 10),
        ("RIGHTPADDING",   (0,0), (-1,-1), 10),
        ("GRID",           (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(sp(12))

    # Tabela de endpoints resumo
    story.append(p("Todos os Endpoints", "H2"))
    story.append(sp(6))
    ep_header_s = ParagraphStyle("eph", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_WHITE)
    ep_rows = [
        ["GET",   "/api/v1/demandas",                     "Lista demandas (com filtros e paginação)"],
        ["POST",  "/api/v1/demandas",                     "Cria uma nova demanda"],
        ["GET",   "/api/v1/demandas/{id}",                "Retorna uma demanda específica"],
        ["PATCH", "/api/v1/demandas/{id}/status",         "Atualiza o status de uma demanda"],
        ["GET",   "/api/v1/demandas/{id}/comentarios",    "Lista comentários de uma demanda"],
        ["POST",  "/api/v1/demandas/{id}/comentarios",    "Adiciona comentário a uma demanda"],
        ["GET",   "/api/v1/usuarios",                     "Lista todos os usuários ativos"],
    ]
    method_colors_map = {
        "GET":   (colors.HexColor("#dbeafe"), colors.HexColor("#1d4ed8")),
        "POST":  (colors.HexColor("#dcfce7"), colors.HexColor("#15803d")),
        "PATCH": (colors.HexColor("#fef3c7"), colors.HexColor("#b45309")),
    }
    ep_data = [[
        Paragraph("Método",    ep_header_s),
        Paragraph("Endpoint",  ep_header_s),
        Paragraph("Descrição", ep_header_s),
    ]]
    for method, path_ep, desc_ep in ep_rows:
        bg, fg = method_colors_map.get(method, (C_BG, C_DARK))
        ep_data.append([
            Paragraph(method, ParagraphStyle(f"em_{method}_{path_ep}", fontSize=8.5,
                       fontName="Helvetica-Bold", textColor=fg, alignment=TA_CENTER)),
            Paragraph(path_ep, ParagraphStyle(f"ep_{path_ep}", fontSize=8,
                       fontName="Courier", textColor=C_PRIMARY)),
            Paragraph(desc_ep, ParagraphStyle(f"ed_{path_ep}", fontSize=8.5,
                       fontName="Helvetica", textColor=C_DARK)),
        ])

    ep_t = Table(ep_data, colWidths=[w*0.12, w*0.40, w*0.48])
    ep_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("BACKGROUND",    (0,1), (0,1),   method_colors_map["GET"][0]),
        ("BACKGROUND",    (0,2), (0,2),   method_colors_map["POST"][0]),
        ("BACKGROUND",    (0,3), (0,3),   method_colors_map["GET"][0]),
        ("BACKGROUND",    (0,4), (0,4),   method_colors_map["PATCH"][0]),
        ("BACKGROUND",    (0,5), (0,5),   method_colors_map["GET"][0]),
        ("BACKGROUND",    (0,6), (0,6),   method_colors_map["POST"][0]),
        ("BACKGROUND",    (0,7), (0,7),   method_colors_map["GET"][0]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("ALIGN",         (0,0), (0,-1),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(ep_t)
    story.append(PageBreak())

    # ── S02: CRIANDO API KEYS ─────────────────────────────────────────────────
    story.append(section_title(2, "Criando Chaves de API (API Keys)", C_SUCCESS))
    story.append(sp(10))
    story.append(p(
        "Toda chamada à API exige uma chave de autenticação. As chaves são gerenciadas pela "
        "interface web do SGDI e têm vida útil indefinida até serem revogadas manualmente."
    ))
    story.append(sp(8))

    # Passo a passo
    steps = [
        ("01", "Acesse o sistema", "Faça login no SGDI com suas credenciais de usuário."),
        ("02", "Vá em API Keys", "Clique em <b>API Keys</b> no menu de navegação superior."),
        ("03", "Preencha a descrição", "No campo <b>Descrição da chave</b>, informe o nome do sistema "
               "que irá usar a chave (ex: 'Integração ERP Totvs', 'App Mobile', 'Script Nightly')."),
        ("04", "Clique em Gerar chave", "A chave completa será exibida em um aviso verde no topo da página."),
        ("05", "Copie imediatamente", "<b>Atenção:</b> a chave completa é exibida apenas uma vez. "
               "Guarde-a em local seguro (cofre de senhas, variável de ambiente). "
               "A listagem exibe apenas os primeiros 8 caracteres mascarados."),
        ("06", "Use no header X-API-Key", "Inclua a chave em todas as requisições à API "
               "via header HTTP <code>X-API-Key: sua-chave-aqui</code>."),
    ]
    step_num_s = ParagraphStyle("stepn", fontSize=12, fontName="Helvetica-Bold",
                                 textColor=C_PRIMARY, alignment=TA_CENTER)
    step_title_s = ParagraphStyle("stept", fontSize=10, fontName="Helvetica-Bold",
                                   textColor=C_DARK, leading=13)
    step_body_s  = ParagraphStyle("stepb", fontSize=9, fontName="Helvetica",
                                   textColor=C_MUTED, leading=13)
    for num, title_s, body_s in steps:
        t = Table([[
            Table([[Paragraph(num, step_num_s)]],
                  colWidths=[1.1*cm],
                  style=TableStyle([
                      ("BACKGROUND",    (0,0), (-1,-1), C_BG),
                      ("TOPPADDING",    (0,0), (-1,-1), 8),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                      ("BOX",           (0,0), (-1,-1), 1, C_PRIMARY),
                  ])),
            [Paragraph(title_s, step_title_s), Paragraph(body_s, step_body_s)],
        ]], colWidths=[1.5*cm, PAGE_W - 2*MARGIN - 1.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_WHITE),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(t)
        story.append(sp(2))

    story.append(sp(10))
    for el in img_block(shots.get("api_keys_list"), "Tela de Gestão de API Keys — formulário de criação e lista de chaves", max_h=12*cm):
        story.append(el)

    story.append(sp(8))
    story.append(warn_box(
        "<b>Segurança:</b> nunca versione chaves de API em repositórios Git. "
        "Use variáveis de ambiente (ex: API_KEY=xxx) ou um cofre de segredos. "
        "Revogar uma chave desativa o acesso imediatamente para todos os sistemas que a usam."
    ))
    story.append(PageBreak())

    # ── S03: AUTENTICAÇÃO ─────────────────────────────────────────────────────
    story.append(section_title(3, "Autenticação — Header X-API-Key", C_PURPLE))
    story.append(sp(10))
    story.append(p(
        "A API usa autenticação stateless por API Key. Cada requisição deve incluir o header "
        "<b>X-API-Key</b> com a chave gerada na interface web. Não há sessão, cookie ou JWT "
        "envolvido — a chave é verificada a cada chamada."
    ))
    story.append(sp(8))

    story.append(p("Formato do Header", "H2"))
    story.append(Paragraph(
        "GET /api/v1/demandas HTTP/1.1\n"
        "Host: localhost:5000\n"
        "X-API-Key: SUA_CHAVE_AQUI\n"
        "Content-Type: application/json",
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Exemplo em PowerShell", "H2"))
    story.append(Paragraph(
        "$key = 'SUA_CHAVE_AQUI'\n"
        "$headers = @{ 'X-API-Key' = $key }\n\n"
        "# GET — listar demandas\n"
        "Invoke-RestMethod -Uri 'http://localhost:5000/api/v1/demandas' -Headers $headers\n\n"
        "# POST — criar demanda\n"
        "$body = @{ titulo='Falha crítica'; descricao='...'; solicitante='ERP'; prioridade='Alta' } | ConvertTo-Json\n"
        "Invoke-RestMethod -Uri 'http://localhost:5000/api/v1/demandas' -Method POST -Headers $headers -Body $body -ContentType 'application/json'",
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Exemplo em cURL (Linux/Mac/WSL)", "H2"))
    story.append(Paragraph(
        'curl -H "X-API-Key: SUA_CHAVE_AQUI" http://localhost:5000/api/v1/demandas\n\n'
        'curl -X POST http://localhost:5000/api/v1/demandas \\\n'
        '  -H "X-API-Key: SUA_CHAVE_AQUI" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"titulo":"Falha","descricao":"...","solicitante":"ERP","prioridade":"Alta"}\'',
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Erros de Autenticação", "H2"))
    story.append(sp(4))

    story.append(p("<b>401 — Header X-API-Key ausente:</b>"))
    for el in response_block(401, results["demandas_list_401"][1], S, "X-API-Key não enviado"):
        story.append(el)

    story.append(p("<b>403 — Chave inválida ou revogada:</b>"))
    for el in response_block(403, results["demandas_list_403"][1], S, "Chave inexistente ou desativada"):
        story.append(el)

    story.append(PageBreak())

    # ── S04: FORMATO DE RESPOSTA ──────────────────────────────────────────────
    story.append(section_title(4, "Formato de Resposta JSON", C_TEAL))
    story.append(sp(10))
    story.append(p(
        "Todas as respostas seguem um envelope JSON padronizado. Isso garante que o "
        "sistema consumidor possa sempre verificar o campo <b>success</b> antes de "
        "processar os dados, sem precisar analisar o código HTTP individualmente."
    ))
    story.append(sp(8))

    story.append(p("Resposta de Sucesso", "H2"))
    story.append(Paragraph(
        '{\n'
        '  "success": true,\n'
        '  "data": { ... },     // objeto ou array com os dados\n'
        '  "meta": {            // presente apenas em listagens\n'
        '    "total": 42        // total de registros (sem paginação)\n'
        '  }\n'
        '}',
        S["Code"]
    ))
    story.append(sp(8))

    story.append(p("Resposta de Erro", "H2"))
    story.append(Paragraph(
        '{\n'
        '  "success": false,\n'
        '  "error": "Mensagem descritiva do problema"\n'
        '}',
        S["Code"]
    ))
    story.append(sp(8))

    story.append(info_box(
        "<b>Dica de integração:</b> sempre verifique o campo <b>success</b> primeiro. "
        "Se for <b>false</b>, leia o campo <b>error</b> para a mensagem de erro. "
        "O campo <b>meta.total</b> é útil para implementar paginação no frontend."
    ))
    story.append(PageBreak())

    # ── S05: STATUS CODES ─────────────────────────────────────────────────────
    story.append(section_title(5, "Todos os Códigos de Status HTTP"))
    story.append(sp(10))
    story.append(p(
        "A API usa os códigos HTTP padrão para comunicar o resultado de cada operação. "
        "A tabela abaixo cobre todos os códigos que podem ser retornados."
    ))
    story.append(sp(8))
    story.append(status_codes_table([
        ("200", "OK",                  "Requisição processada com sucesso (GET, PATCH)"),
        ("201", "Created",             "Recurso criado com sucesso (POST)"),
        ("400", "Bad Request",         "Dados inválidos: campo obrigatório ausente, enum fora do esperado, tipo errado"),
        ("401", "Unauthorized",        "Header X-API-Key não foi enviado na requisição"),
        ("403", "Forbidden",           "Chave enviada mas inválida ou revogada — acesso negado"),
        ("404", "Not Found",           "Recurso solicitado não existe (ID de demanda inválido)"),
        ("500", "Internal Server Error","Erro inesperado no servidor — entre em contato com o administrador"),
    ], S))
    story.append(PageBreak())

    # ── S06: GET /api/v1/demandas ─────────────────────────────────────────────
    story.append(section_title(6, "Listar Demandas", C_PRIMARY))
    story.append(sp(8))
    story.append(endpoint_header("GET", "/api/v1/demandas",
        "Retorna a lista de demandas com suporte a filtros e paginação.", S))
    story.append(sp(10))

    story.append(p("Parâmetros de Query (todos opcionais)", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("status",        "string",  "Não", "Filtrar por status. Valores: Aberta · Em andamento · Concluída · Cancelada"),
        ("prioridade",    "string",  "Não", "Filtrar por prioridade. Valores: Crítica · Alta · Média · Baixa"),
        ("responsavel_id","integer", "Não", "Filtrar por ID do responsável pela execução"),
        ("limit",         "integer", "Não", "Máximo de registros retornados (padrão: 50, máx: 200)"),
        ("offset",        "integer", "Não", "Número de registros a pular — para paginação (padrão: 0)"),
    ], S))
    story.append(sp(10))

    story.append(p("Resposta de Sucesso — 200 OK", "H2"))
    for el in response_block(200, results["demandas_list_ok"][1], S, "Lista completa de demandas"):
        story.append(el)

    story.append(p("Com filtro: ?status=Aberta&limit=2", "H2"))
    for el in response_block(200, results["demandas_list_filter"][1], S, "Filtrado por status"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["demandas_list_401"][1], S):
        story.append(el)
    story.append(p("<b>403</b> — Chave inválida:"))
    for el in response_block(403, results["demandas_list_403"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S07: POST /api/v1/demandas ────────────────────────────────────────────
    story.append(section_title(7, "Criar Demanda", C_SUCCESS))
    story.append(sp(8))
    story.append(endpoint_header("POST", "/api/v1/demandas",
        "Cria uma nova demanda no sistema. Registra automaticamente o histórico inicial.", S))
    story.append(sp(10))

    story.append(p("Body da Requisição (JSON)", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("titulo",        "string",  "Sim", "Resumo objetivo da demanda (máx. 200 caracteres)"),
        ("descricao",     "string",  "Sim", "Descrição completa com contexto, impacto e expectativas"),
        ("solicitante",   "string",  "Sim", "Nome do sistema ou pessoa que está abrindo a demanda"),
        ("prioridade",    "string",  "Sim", "Nível de criticidade: Crítica · Alta · Média · Baixa"),
        ("responsavel_id","integer", "Não", "ID do usuário SGDI que será responsável pela execução"),
        ("data_prevista", "string",  "Não", "Prazo de SLA no formato YYYY-MM-DD (ex: 2026-06-30)"),
    ], S))
    story.append(sp(10))

    story.append(p("Exemplo de Requisição", "H2"))
    story.append(Paragraph(
        'POST /api/v1/demandas\n'
        'X-API-Key: SUA_CHAVE_AQUI\n'
        'Content-Type: application/json\n\n'
        '{\n'
        '  "titulo": "Integração com ERP — módulo fiscal",\n'
        '  "descricao": "O módulo de notas fiscais do ERP precisa enviar demandas\\n'
        '               automaticamente ao receber erros de rejeição da SEFAZ.",\n'
        '  "solicitante": "Sistema ERP Totvs",\n'
        '  "prioridade": "Alta",\n'
        '  "data_prevista": "2026-06-30"\n'
        '}',
        S["Code"]
    ))
    story.append(sp(8))

    story.append(p("Resposta de Sucesso — 201 Created", "H2"))
    for el in response_block(201, results["demandas_create_ok"][1], S, "Demanda criada, ID retornado"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>400</b> — Campos obrigatórios ausentes:"))
    for el in response_block(400, results["demandas_create_400"][1], S):
        story.append(el)
    story.append(p("<b>400</b> — Prioridade inválida:"))
    for el in response_block(400, results["demandas_create_400b"][1], S):
        story.append(el)
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["demandas_create_401"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S08: GET /api/v1/demandas/{id} ────────────────────────────────────────
    story.append(section_title(8, "Buscar Demanda por ID"))
    story.append(sp(8))
    story.append(endpoint_header("GET", f"/api/v1/demandas/{CREATED_DEMAND_ID}",
        "Retorna todos os detalhes de uma demanda específica pelo seu ID.", S))
    story.append(sp(10))

    story.append(p("Parâmetro de Rota", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("id", "integer", "Sim", "ID numérico da demanda (ex: /api/v1/demandas/42)"),
    ], S))
    story.append(sp(10))

    story.append(p(f"Resposta de Sucesso — 200 OK (ID {CREATED_DEMAND_ID})", "H2"))
    for el in response_block(200, results["demandas_get_ok"][1], S, "Todos os campos da demanda"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>404</b> — Demanda não existe:"))
    for el in response_block(404, results["demandas_get_404"][1], S):
        story.append(el)
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["demandas_get_401"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S09: PATCH status ─────────────────────────────────────────────────────
    story.append(section_title(9, "Atualizar Status da Demanda", C_WARNING))
    story.append(sp(8))
    story.append(endpoint_header("PATCH", f"/api/v1/demandas/{CREATED_DEMAND_ID}/status",
        "Altera o status de uma demanda e registra a mudança no histórico.", S))
    story.append(sp(10))

    story.append(p("Body da Requisição (JSON)", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("status", "string", "Sim", "Novo status: Aberta · Em andamento · Concluída · Cancelada"),
        ("autor",  "string", "Não", "Identificação de quem fez a mudança (padrão: 'API')"),
    ], S))
    story.append(sp(10))

    # Fluxo de status
    story.append(p("Fluxo de Status Permitido", "H2"))
    story.append(info_box(
        "Aberta  →  Em andamento  →  Concluída<br/>"
        "Aberta  →  Cancelada<br/>"
        "Em andamento  →  Cancelada<br/>"
        "A API não bloqueia transições inválidas — qualquer status pode ir para qualquer outro. "
        "O controle de fluxo é feito pela interface web. Via API, use com responsabilidade."
    ))
    story.append(sp(8))

    story.append(p("Resposta de Sucesso — 200 OK", "H2"))
    for el in response_block(200, results["status_patch_ok"][1], S, "Status anterior e novo retornados"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>400</b> — Status inválido:"))
    for el in response_block(400, results["status_patch_400"][1], S):
        story.append(el)
    story.append(p("<b>404</b> — Demanda não encontrada:"))
    for el in response_block(404, results["status_patch_404"][1], S):
        story.append(el)
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["status_patch_401"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S10: GET comentarios ──────────────────────────────────────────────────
    story.append(section_title(10, "Listar Comentários de uma Demanda"))
    story.append(sp(8))
    story.append(endpoint_header("GET", f"/api/v1/demandas/{CREATED_DEMAND_ID}/comentarios",
        "Retorna todos os comentários de uma demanda em ordem cronológica.", S))
    story.append(sp(10))

    story.append(p("Parâmetro de Rota", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("id", "integer", "Sim", "ID da demanda cujos comentários serão listados"),
    ], S))
    story.append(sp(10))

    story.append(p("Resposta de Sucesso — 200 OK", "H2"))
    for el in response_block(200, results["comentarios_list_ok"][1], S, "Lista de comentários (pode ser vazia)"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>404</b> — Demanda não existe:"))
    for el in response_block(404, results["comentarios_list_404"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S11: POST comentarios ─────────────────────────────────────────────────
    story.append(section_title(11, "Adicionar Comentário", C_SUCCESS))
    story.append(sp(8))
    story.append(endpoint_header("POST", f"/api/v1/demandas/{CREATED_DEMAND_ID}/comentarios",
        "Adiciona um comentário público a uma demanda existente.", S))
    story.append(sp(10))

    story.append(p("Body da Requisição (JSON)", "H2"))
    story.append(sp(4))
    story.append(params_table([
        ("autor",      "string", "Sim", "Nome do sistema ou usuário que está comentando"),
        ("comentario", "string", "Sim", "Texto do comentário (sem limite de caracteres)"),
    ], S))
    story.append(sp(10))

    story.append(p("Exemplo de Requisição", "H2"))
    story.append(Paragraph(
        f'POST /api/v1/demandas/{CREATED_DEMAND_ID}/comentarios\n'
        'X-API-Key: SUA_CHAVE_AQUI\n'
        'Content-Type: application/json\n\n'
        '{\n'
        '  "autor": "Sistema ERP",\n'
        '  "comentario": "Demanda recebida. Equipe notificada. Previsao de resolucao: 48h."\n'
        '}',
        S["Code"]
    ))
    story.append(sp(8))

    story.append(p("Resposta de Sucesso — 201 Created", "H2"))
    for el in response_block(201, results["comentarios_create_ok"][1], S, "ID do comentário criado"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>400</b> — Campos obrigatórios ausentes:"))
    for el in response_block(400, results["comentarios_create_400"][1], S):
        story.append(el)
    story.append(p("<b>404</b> — Demanda não encontrada:"))
    for el in response_block(404, results["comentarios_create_404"][1], S):
        story.append(el)
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["comentarios_create_401"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S12: GET usuarios ─────────────────────────────────────────────────────
    story.append(section_title(12, "Listar Usuários"))
    story.append(sp(8))
    story.append(endpoint_header("GET", "/api/v1/usuarios",
        "Retorna todos os usuários ativos cadastrados no SGDI.", S))
    story.append(sp(10))

    story.append(p(
        "Este endpoint é útil para descobrir os IDs de usuários disponíveis antes de "
        "criar uma demanda com <b>responsavel_id</b>. Não há parâmetros de filtro."
    ))
    story.append(sp(8))

    story.append(p("Resposta de Sucesso — 200 OK", "H2"))
    for el in response_block(200, results["usuarios_ok"][1], S, "Lista de todos os usuários ativos"):
        story.append(el)

    story.append(p("Erros Possíveis", "H2"))
    story.append(p("<b>401</b> — Header ausente:"))
    for el in response_block(401, results["usuarios_401"][1], S):
        story.append(el)
    story.append(PageBreak())

    # ── S13: SWAGGER ──────────────────────────────────────────────────────────
    story.append(section_title(13, "Interface Swagger UI", C_PURPLE))
    story.append(sp(10))
    story.append(p(
        "O SGDI inclui uma interface Swagger UI interativa em <b>/apidocs</b>. "
        "Ela permite explorar, testar e entender todos os endpoints diretamente pelo navegador, "
        "sem precisar de ferramentas externas como Postman ou cURL."
    ))
    story.append(sp(8))
    for el in img_block(shots.get("swagger_top"), "Interface Swagger UI — visão geral dos endpoints disponíveis", max_h=11*cm):
        story.append(el)

    story.append(sp(6))
    story.append(p("Como usar o Swagger para testar a API", "H2"))
    swagger_steps = [
        "Acesse <b>http://localhost:5000/apidocs</b> no navegador",
        "Clique em <b>Authorize</b> (cadeado) e informe sua API Key",
        "Clique em qualquer endpoint para expandi-lo",
        'Clique em <b>Try it out</b> para habilitar o formulário de teste',
        "Preencha os parâmetros e clique em <b>Execute</b>",
        "A resposta real do servidor é exibida abaixo — com código HTTP, headers e body JSON",
    ]
    for i, step in enumerate(swagger_steps, 1):
        story.append(Paragraph(f"{i}. {step}", S["Bullet"]))
    story.append(sp(6))
    for el in img_block(shots.get("swagger_full"), "Swagger UI expandido — documentação completa e interativa", max_h=12*cm):
        story.append(el)
    story.append(PageBreak())

    # ── S14: EXEMPLOS COMPLETOS ───────────────────────────────────────────────
    story.append(section_title(14, "Exemplos Completos — PowerShell e cURL", C_TEAL))
    story.append(sp(10))
    story.append(p(
        "Exemplos prontos para copiar e executar. Substitua <b>SUA_CHAVE</b> pela chave "
        "gerada em /api/keys e <b>localhost:5000</b> pelo endereço do servidor em produção."
    ))
    story.append(sp(10))

    story.append(p("PowerShell — Fluxo completo de integração", "H2"))
    story.append(Paragraph(
        "# 1. Configurar chave\n"
        "$key = 'SUA_CHAVE'\n"
        "$base = 'http://localhost:5000/api/v1'\n"
        "$h = @{ 'X-API-Key' = $key }\n\n"
        "# 2. Listar usuarios para descobrir IDs\n"
        "Invoke-RestMethod -Uri \"$base/usuarios\" -Headers $h\n\n"
        "# 3. Criar demanda com responsavel\n"
        "$body = @{\n"
        "    titulo      = 'Erro critico no modulo de relatorios'\n"
        "    descricao   = 'Sistema trava ao gerar relatorios com mais de 1000 linhas'\n"
        "    solicitante = 'Sistema ERP'\n"
        "    prioridade  = 'Critica'\n"
        "    responsavel_id = 2\n"
        "    data_prevista  = '2026-06-01'\n"
        "} | ConvertTo-Json\n"
        "$nova = Invoke-RestMethod -Uri \"$base/demandas\" -Method POST `\n"
        "    -Headers $h -Body $body -ContentType 'application/json'\n"
        "$id = $nova.data.id\n"
        "Write-Host \"Demanda criada: ID $id\"\n\n"
        "# 4. Acompanhar a demanda\n"
        "Invoke-RestMethod -Uri \"$base/demandas/$id\" -Headers $h\n\n"
        "# 5. Adicionar comentario\n"
        "$com = @{ autor='ERP'; comentario='Analise iniciada. Retorno em 2h.' } | ConvertTo-Json\n"
        "Invoke-RestMethod -Uri \"$base/demandas/$id/comentarios\" -Method POST `\n"
        "    -Headers $h -Body $com -ContentType 'application/json'\n\n"
        "# 6. Mover para Em andamento\n"
        "$st = @{ status='Em andamento'; autor='Sistema ERP' } | ConvertTo-Json\n"
        "Invoke-RestMethod -Uri \"$base/demandas/$id/status\" -Method PATCH `\n"
        "    -Headers $h -Body $st -ContentType 'application/json'\n\n"
        "# 7. Concluir a demanda\n"
        "$st2 = @{ status='Concluida'; autor='Sistema ERP' } | ConvertTo-Json\n"
        "Invoke-RestMethod -Uri \"$base/demandas/$id/status\" -Method PATCH `\n"
        "    -Headers $h -Body $st2 -ContentType 'application/json'",
        S["Code"]
    ))
    story.append(sp(12))

    story.append(p("cURL — Mesmos exemplos para Linux/Mac/WSL", "H2"))
    story.append(Paragraph(
        'KEY="SUA_CHAVE"\n'
        'BASE="http://localhost:5000/api/v1"\n\n'
        '# Listar demandas abertas\n'
        'curl -s -H "X-API-Key: $KEY" "$BASE/demandas?status=Aberta" | python3 -m json.tool\n\n'
        '# Criar demanda\n'
        'curl -s -X POST "$BASE/demandas" \\\n'
        '  -H "X-API-Key: $KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"titulo":"Erro critico","descricao":"...","solicitante":"ERP","prioridade":"Alta"}\' \\\n'
        '  | python3 -m json.tool\n\n'
        '# Atualizar status (substitua ID)\n'
        'curl -s -X PATCH "$BASE/demandas/ID/status" \\\n'
        '  -H "X-API-Key: $KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"status":"Em andamento","autor":"Sistema ERP"}\' \\\n'
        '  | python3 -m json.tool\n\n'
        '# Adicionar comentario\n'
        'curl -s -X POST "$BASE/demandas/ID/comentarios" \\\n'
        '  -H "X-API-Key: $KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"autor":"ERP","comentario":"Analise em andamento"}\' \\\n'
        '  | python3 -m json.tool',
        S["Code"]
    ))
    story.append(sp(12))

    story.append(warn_box(
        "<b>Ambientes de produção:</b> substitua <b>localhost:5000</b> pelo domínio ou IP "
        "real do servidor. Recomenda-se usar HTTPS em produção para proteger a chave de API "
        "em trânsito. Cada ambiente (dev/homolog/prod) deve ter chaves separadas."
    ))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=cover_page,
        onLaterPages=page_template,
    )
    print(f"[OK] PDF gerado: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Gerador de Documentacao API SGDI ===\n")

    print("Configurando dados de teste...")
    setup_test_data()

    print("\nIniciando servidor Flask...")
    proc = start_flask()
    print("Servidor ativo.")

    try:
        results = run_api_tests()
        shots   = capture_screenshots()
        build_pdf(results, shots, "documentacao_api_sgdi.pdf")
    finally:
        stop_flask(proc)
        cleanup_test_data()
        print("Servidor encerrado. Chave de teste removida.")

    print("\nConcluido. Arquivo: documentacao_api_sgdi.pdf")
