"""
Gerador do Documento Técnico e Arquitetural do SGDI.
Produz um PDF profissional cobrindo decisoes de projeto, tecnologias,
segurança, arquitetura e perspectivas de evolucao.
"""
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Paleta de cores ────────────────────────────────────────────────────────────
C_PRIMARY  = colors.HexColor("#1e40af")
C_ACCENT   = colors.HexColor("#3b82f6")
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
C_NAVY     = colors.HexColor("#0f172a")
C_CODE_BG  = colors.HexColor("#0f172a")
C_CODE_FG  = colors.HexColor("#e2e8f0")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

SHOT_DIR = Path("doc_screenshots")


# ═══════════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════════

def build_styles():
    S = getSampleStyleSheet()

    def add(name, **kw):
        if name in S:
            S[name].__dict__.update(kw)
        else:
            S.add(ParagraphStyle(name=name, **kw))

    add("DocTitle",    fontSize=30, leading=36, textColor=C_WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("DocSubtitle", fontSize=13, leading=17, textColor=colors.HexColor("#93c5fd"),
        fontName="Helvetica", alignment=TA_CENTER)
    add("H1",  fontSize=15, leading=19, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=24, spaceAfter=10)
    add("H2",  fontSize=12, leading=15, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    add("H3",  fontSize=10.5, leading=13, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    add("Body", fontSize=9.5, leading=14.5, textColor=C_DARK,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6)
    add("Bullet", fontSize=9.5, leading=14, textColor=C_DARK,
        fontName="Helvetica", leftIndent=16, spaceAfter=3)
    add("BulletSub", fontSize=9, leading=13, textColor=C_MUTED,
        fontName="Helvetica", leftIndent=32, spaceAfter=2)
    add("Code", fontSize=8, leading=11.5, textColor=C_CODE_FG,
        fontName="Courier", backColor=C_CODE_BG,
        leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=8,
        borderPadding=8)
    add("Caption", fontSize=8, leading=11, textColor=C_MUTED,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=10)
    add("TOC",   fontSize=10, leading=15, textColor=C_PRIMARY,
        fontName="Helvetica", leftIndent=14, spaceAfter=3)
    add("TOCSec",fontSize=9, leading=14, textColor=C_MUTED,
        fontName="Helvetica", leftIndent=30, spaceAfter=2)
    add("Quote",  fontSize=9.5, leading=14, textColor=colors.HexColor("#1e40af"),
        fontName="Helvetica-Oblique", leftIndent=20, rightIndent=10,
        spaceBefore=6, spaceAfter=6)
    return S


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def sp(h=8):
    return Spacer(1, h)


def hr(color=C_BORDER, t=0.5, sb=4, sa=8):
    return HRFlowable(width="100%", thickness=t, color=color,
                      spaceBefore=sb, spaceAfter=sa)


def section_block(num, title, subtitle="", color=C_PRIMARY):
    """Bloco visual de titulo de secao numerada."""
    dark_map = {
        C_PRIMARY: colors.HexColor("#1e3a8a"),
        C_SUCCESS: colors.HexColor("#14532d"),
        C_WARNING: colors.HexColor("#78350f"),
        C_DANGER:  colors.HexColor("#7f1d1d"),
        C_PURPLE:  colors.HexColor("#4c1d95"),
        C_TEAL:    colors.HexColor("#134e4a"),
    }
    bg = dark_map.get(color, colors.HexColor("#1e3a8a"))

    num_s = ParagraphStyle(f"sn{num}", fontSize=16, fontName="Helvetica-Bold",
                            textColor=color, alignment=TA_CENTER, leading=19)
    title_s = ParagraphStyle(f"st{num}", fontSize=14, fontName="Helvetica-Bold",
                              textColor=C_WHITE, leading=17)
    sub_s = ParagraphStyle(f"ss{num}", fontSize=9, fontName="Helvetica",
                            textColor=colors.HexColor("#94a3b8"), leading=12)

    left_cell = Table([[Paragraph(f"{num:02d}", num_s)]],
                      colWidths=[1.2*cm],
                      style=TableStyle([
                          ("BACKGROUND",    (0,0), (-1,-1), C_NAVY),
                          ("TOPPADDING",    (0,0), (-1,-1), 8),
                          ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                      ]))
    right_content = [Paragraph(title, title_s)]
    if subtitle:
        right_content.append(Paragraph(subtitle, sub_s))

    t = Table([[left_cell, right_content]],
              colWidths=[1.6*cm, CONTENT_W - 1.6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def kv_table(rows, col_ratio=(0.35, 0.65), header=None):
    """Tabela chave-valor com linhas alternadas."""
    h_s = ParagraphStyle("kvh", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    k_s = ParagraphStyle("kvk", fontSize=9, fontName="Helvetica-Bold", textColor=C_PRIMARY)
    v_s = ParagraphStyle("kvv", fontSize=9, fontName="Helvetica", textColor=C_DARK)

    data = []
    if header:
        data.append([Paragraph(header[0], h_s), Paragraph(header[1], h_s)])
    for k, v in rows:
        data.append([Paragraph(k, k_s), Paragraph(v, v_s)])

    w1 = CONTENT_W * col_ratio[0]
    w2 = CONTENT_W * col_ratio[1]
    t = Table(data, colWidths=[w1, w2])
    style = [
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",     (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 6),
        ("LEFTPADDING",    (0,0), (-1,-1), 10),
        ("RIGHTPADDING",   (0,0), (-1,-1), 10),
        ("GRID",           (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
    ]
    if header:
        style.append(("BACKGROUND", (0,0), (-1,0), C_PRIMARY))
    t.setStyle(TableStyle(style))
    return t


def tech_table(rows):
    """Tabela de tecnologias: Tecnologia | Versao | Papel."""
    h_s = ParagraphStyle("tth", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    tech_s = ParagraphStyle("ttn", fontSize=9, fontName="Helvetica-Bold", textColor=C_PRIMARY)
    ver_s  = ParagraphStyle("ttv", fontSize=8.5, fontName="Courier", textColor=C_MUTED)
    role_s = ParagraphStyle("ttr", fontSize=9, fontName="Helvetica", textColor=C_DARK)

    data = [[Paragraph(h, h_s) for h in ["Tecnologia", "Versao", "Papel no Projeto"]]]
    for tech, ver, role in rows:
        data.append([
            Paragraph(tech, tech_s),
            Paragraph(ver, ver_s),
            Paragraph(role, role_s),
        ])
    w = CONTENT_W
    t = Table(data, colWidths=[w*0.25, w*0.15, w*0.60])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def comparison_table(rows, headers):
    """Tabela de comparacao de alternativas."""
    h_s  = ParagraphStyle("cth", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    c1_s = ParagraphStyle("ctc1", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)
    c2_s = ParagraphStyle("ctc2", fontSize=9, fontName="Helvetica", textColor=C_DARK)
    c3_s = ParagraphStyle("ctc3", fontSize=9, fontName="Helvetica", textColor=C_SUCCESS)
    c4_s = ParagraphStyle("ctc4", fontSize=8.5, fontName="Helvetica-Oblique", textColor=C_MUTED)

    data = [[Paragraph(h, h_s) for h in headers]]
    for row in rows:
        data.append([
            Paragraph(row[0], c1_s),
            Paragraph(row[1], c2_s),
            Paragraph(row[2], c3_s),
            Paragraph(row[3], c4_s),
        ])
    w = CONTENT_W
    t = Table(data, colWidths=[w*0.18, w*0.22, w*0.22, w*0.38])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_DARK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def routes_table(rows):
    """Tabela de rotas do sistema."""
    h_s  = ParagraphStyle("rth", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    method_colors = {
        "GET":    colors.HexColor("#dbeafe"),
        "POST":   colors.HexColor("#dcfce7"),
        "PATCH":  colors.HexColor("#fef3c7"),
        "DELETE": colors.HexColor("#fee2e2"),
    }
    data = [[Paragraph(h, h_s) for h in ["Método", "Rota", "Descrição", "Auth"]]]
    for method, route, desc, auth in rows:
        bg_m = method_colors.get(method, C_BG)
        m_color = {
            "GET":   colors.HexColor("#1d4ed8"),
            "POST":  colors.HexColor("#15803d"),
            "PATCH": colors.HexColor("#b45309"),
        }.get(method, C_DARK)
        data.append([
            Paragraph(method, ParagraphStyle(f"rm_{method}_{route}",
                fontSize=8.5, fontName="Helvetica-Bold",
                textColor=m_color, alignment=TA_CENTER)),
            Paragraph(route, ParagraphStyle(f"rr_{route}",
                fontSize=7.8, fontName="Courier", textColor=C_DARK)),
            Paragraph(desc, ParagraphStyle(f"rd_{route}",
                fontSize=8.5, fontName="Helvetica", textColor=C_DARK)),
            Paragraph(auth, ParagraphStyle(f"ra_{route}",
                fontSize=8, fontName="Helvetica-Oblique", textColor=C_MUTED)),
        ])
    w = CONTENT_W
    t = Table(data, colWidths=[w*0.10, w*0.32, w*0.43, w*0.15])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("ALIGN",         (0,0), (0,-1),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def security_table(rows):
    h_s   = ParagraphStyle("seth", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    owasp_s = ParagraphStyle("owasp", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_DANGER)
    impl_s  = ParagraphStyle("impl",  fontSize=8.5, fontName="Helvetica", textColor=C_DARK)
    how_s   = ParagraphStyle("how",   fontSize=8.5, fontName="Courier",   textColor=C_PRIMARY)

    data = [[Paragraph(h, h_s) for h in ["Ameaca (OWASP)", "Mitigacao Implementada", "Mecanismo Tecnico"]]]
    for owasp, mitigation, how in rows:
        data.append([
            Paragraph(owasp, owasp_s),
            Paragraph(mitigation, impl_s),
            Paragraph(how, how_s),
        ])
    w = CONTENT_W
    t = Table(data, colWidths=[w*0.28, w*0.38, w*0.34])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#7f1d1d")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#fff5f5"), C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def info_box(text, color=C_ACCENT, bg=None):
    bg = bg or colors.HexColor("#eff6ff")
    s = ParagraphStyle("ib", fontSize=9.5, fontName="Helvetica",
                       textColor=C_DARK, leftIndent=10, rightIndent=10,
                       spaceBefore=4, spaceAfter=4, leading=14,
                       borderPadding=10)
    t = Table([[Paragraph(text, s)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), bg),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LINEBEFORE",   (0,0), (-1,-1), 4, color),
    ]))
    return t


def warn_box(text):
    return info_box(text,
                    color=C_WARNING,
                    bg=colors.HexColor("#fffbeb"))


def img_block(name, caption, max_h=10*cm):
    path = str(SHOT_DIR / f"{name}.png")
    items = []
    if os.path.exists(path):
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as pil:
                w_px, h_px = pil.size
            aspect = h_px / w_px
            img_h = min(CONTENT_W * aspect, max_h)
            img_w = img_h / aspect
            items.append(Image(path, width=img_w, height=img_h))
            cap_s = ParagraphStyle("imgcap", fontSize=8, fontName="Helvetica-Oblique",
                                   textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=12)
            items.append(Paragraph(caption, cap_s))
            items.append(sp(6))
        except Exception:
            pass
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINAS DE TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

def cover_page(canvas, doc):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # Fundo principal
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # Faixa superior
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 100, w, 100, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h - 106, w, 8, fill=1, stroke=0)

    # Sigla SGDI em destaque
    canvas.setFillColor(C_NAVY)
    canvas.setFont("Helvetica-Bold", 38)
    canvas.drawString(MARGIN, h - 75, "SGDI")
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 38)
    canvas.drawString(MARGIN + 1, h - 76, "SGDI")

    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.setFont("Helvetica", 14)
    canvas.drawString(MARGIN + 98, h - 60, "Sistema de Gestao de Demandas Internas")
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(MARGIN + 98, h - 78, "v2.0")

    # Titulo do documento
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 26)
    title = "Documento Tecnico e Arquitetural"
    canvas.drawCentredString(w/2, h - 155, title)

    canvas.setFont("Helvetica", 13)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawCentredString(w/2, h - 178, "Decisoes de Projeto, Tecnologias e Justificativas")

    # Linha separadora
    canvas.setStrokeColor(C_ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN * 2, h - 198, w - MARGIN * 2, h - 198)

    # Grid de metadados
    meta = [
        ("Projeto",       "SGDI — Sistema de Gestao de Demandas Internas"),
        ("Versao",        "2.0.0"),
        ("Linguagem",     "Python 3.12"),
        ("Framework",     "Flask 3.0.3"),
        ("Banco de dados","SQLite 3 (demandas.db)"),
        ("API",           "REST JSON + Swagger/OpenAPI 2.0"),
        ("Autenticacao",  "Session-based (web) + API Key (REST)"),
        ("Classificacao", "Documento Tecnico Interno — Uso Irrestrito"),
    ]
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(MARGIN, h - 225, "METADADOS DO PROJETO")
    canvas.setLineWidth(0.5)
    canvas.setStrokeColor(colors.HexColor("#1e40af"))
    canvas.line(MARGIN, h - 230, MARGIN + 180, h - 230)

    y = h - 250
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(colors.HexColor("#475569"))
    for k, v in meta:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#3b82f6"))
        canvas.drawString(MARGIN, y, f"{k}:")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#cbd5e1"))
        canvas.drawString(MARGIN + 120, y, v)
        y -= 18

    # Indice visual
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(w/2 + 20, h - 225, "SECOES DO DOCUMENTO")
    canvas.setStrokeColor(colors.HexColor("#1e40af"))
    canvas.line(w/2 + 20, h - 230, w/2 + 210, h - 230)

    sections = [
        "01  Visao Geral e Objetivo",
        "02  Arquitetura do Sistema",
        "03  Stack de Tecnologias",
        "04  Decisoes Tecnicas e Justificativas",
        "05  Alternativas Avaliadas",
        "06  Seguranca e OWASP Top 10",
        "07  Estrutura da API REST",
        "08  Autenticacao e Autorizacao",
        "09  Organizacao do Codigo",
        "10  Performance e Otimizacao",
        "11  Fluxo Geral da Aplicacao",
        "12  Todas as Rotas do Sistema",
        "13  Escalabilidade e Manutencao",
        "14  Melhorias Futuras",
        "15  Conclusao Tecnica",
    ]
    canvas.setFont("Courier", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    y2 = h - 250
    for sec in sections:
        canvas.drawString(w/2 + 20, y2, sec)
        y2 -= 18

    # Badges de tecnologia
    techs = [("Python 3.12", C_PRIMARY),
             ("Flask 3.0", colors.HexColor("#1d4ed8")),
             ("SQLite 3", colors.HexColor("#0d9488")),
             ("Swagger 2.0", colors.HexColor("#059669")),
             ("bcrypt", colors.HexColor("#7c3aed")),
             ("Chart.js 4", colors.HexColor("#d97706")),
             ("openpyxl", colors.HexColor("#dc2626"))]
    bx = MARGIN
    by = 100
    canvas.setFont("Helvetica-Bold", 8)
    for tech, col in techs:
        tw = canvas.stringWidth(tech, "Helvetica-Bold", 8) + 18
        canvas.setFillColor(col)
        canvas.roundRect(bx, by, tw, 22, 5, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(bx + 9, by + 7, tech)
        bx += tw + 8

    # Rodape da capa
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, 0, w, 45, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(MARGIN, 28, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawCentredString(w/2, 28, "Documento Tecnico — Uso Academico e Institucional")
    canvas.drawRightString(w - MARGIN, 28, "SGDI v2.0 — 2026")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawCentredString(w/2, 12, "Desenvolvido com Python · Flask · SQLite · Swagger · openpyxl · Chart.js")

    canvas.restoreState()


def page_header_footer(canvas, doc):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # Header
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 26, w, 26, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(MARGIN, h - 16, "SGDI v2.0 — Documento Tecnico e Arquitetural")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawRightString(w - MARGIN, h - 16, "Confidencial — Uso Interno")

    # Footer
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 28, w - MARGIN, 28)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 14, "Sistema de Gestao de Demandas Internas")
    canvas.drawCentredString(w/2, 14, f"Pagina {doc.page}")
    canvas.drawRightString(w - MARGIN, 14, datetime.now().strftime("%d/%m/%Y"))

    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEÚDO
# ═══════════════════════════════════════════════════════════════════════════════

def build_pdf(output_path):
    print("[PDF] Construindo documento tecnico...")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 4, bottomMargin=MARGIN,
        title="SGDI — Documento Tecnico e Arquitetural",
        author="SGDI Development Team",
        subject="Arquitetura e Decisoes Tecnicas do SGDI v2.0",
    )

    S = build_styles()
    story = []

    def p(text, style="Body"):
        return Paragraph(text, S[style])

    def bul(text, sub=False):
        style = "BulletSub" if sub else "Bullet"
        prefix = "  —" if sub else "•"
        return Paragraph(f"{prefix} {text}", S[style])

    # ── CAPA (gerada pelo onFirstPage) ────────────────────────────────────────
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S01 — VISÃO GERAL E OBJETIVO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(1, "Visao Geral e Objetivo do Projeto",
        "Contexto, proposito e escopo da aplicacao"))
    story.append(sp(12))

    story.append(p(
        "O <b>SGDI (Sistema de Gestao de Demandas Internas)</b> e uma aplicacao web "
        "desenvolvida em Python com o framework Flask, projetada para centralizar, "
        "rastrear e gerenciar demandas operacionais dentro de uma organizacao. O sistema "
        "substitui fluxos informais — como planilhas, e-mails e mensagens de chat — por "
        "uma plataforma unica com historico auditavel, controle de SLA e integracao via API REST."
    ))
    story.append(sp(6))
    story.append(p(
        "A aplicacao cobre o ciclo completo de uma demanda: abertura, triagem, atribuicao de "
        "responsavel, acompanhamento de status, comunicacao via comentarios e encerramento. "
        "Cada transicao de estado e registrada em um historico imutavel, garantindo rastreabilidade "
        "total para fins de auditoria e gestao de desempenho."
    ))
    story.append(sp(10))

    story.append(p("Objetivos Especificos", "H2"))
    story.append(sp(4))
    objectives = [
        "<b>Centralizar demandas</b> — um unico ponto de controle para todas as solicitacoes internas",
        "<b>Rastrear SLA</b> — prazo previsto, alertas de atraso e indicadores de desempenho",
        "<b>Auditar mudancas</b> — historico completo de status com autor e data de cada transicao",
        "<b>Permitir integracao</b> — API REST autenticada para sistemas externos (ERP, scripts, apps)",
        "<b>Gerar relatorios</b> — exportacao em CSV, Excel e PDF com filtros aplicados",
        "<b>Dashboard executivo</b> — KPIs em tempo real, graficos e alertas de demandas criticas",
        "<b>Escalabilidade horizontal</b> — arquitetura preparada para migracao a banco maior se necessario",
    ]
    for obj in objectives:
        story.append(bul(obj))
    story.append(sp(10))

    story.append(p("Numeros do Sistema", "H2"))
    story.append(sp(4))
    story.append(kv_table([
        ("Rotas totais",           "31 (17 web UI + 7 dashboard interno + 7 API REST externa)"),
        ("Templates HTML",         "10 (base.html + 9 paginas especificas)"),
        ("Tabelas no banco",       "5 (usuarios, demandas, historico_status, comentarios, api_keys)"),
        ("Usuarios iniciais",      "5 (seed automatico com senha bcrypt)"),
        ("Niveis de prioridade",   "4 (Critica, Alta, Media, Baixa)"),
        ("Status de demanda",      "4 (Aberta, Em andamento, Concluida, Cancelada)"),
        ("Formatos de exportacao", "3 (CSV, Excel .xlsx, PDF via reportlab)"),
        ("Endpoints API publica",  "7 (Demandas: 4, Comentarios: 2, Usuarios: 1)"),
    ], header=("Indicador", "Valor")))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S02 — ARQUITETURA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(2, "Arquitetura do Sistema",
        "Padrao arquitetural, camadas e responsabilidades"))
    story.append(sp(12))

    story.append(p(
        "O SGDI adota uma <b>arquitetura monolitica em camadas</b>, inspirada no padrao "
        "<b>MVC (Model-View-Controller)</b>, adaptada ao modelo de aplicacoes Flask. "
        "Esta escolha foi deliberada: para sistemas internos de escala media (dezenas a centenas "
        "de usuarios simultaneos), o monolito e mais simples de desenvolver, implantar, depurar "
        "e manter do que uma arquitetura de microsservicos."
    ))
    story.append(sp(8))

    story.append(p("Camadas da Aplicacao", "H2"))
    story.append(sp(4))
    story.append(kv_table([
        ("Model — database.py",
         "Gerencia o banco SQLite: criacao de tabelas, migrations, seed de dados e todas as "
         "queries. Isola completamente o acesso a dados do resto da aplicacao. Contem tambem "
         "as constantes de dominio (PRIORIDADES, TODOS_STATUS, etc.)."),
        ("Controller — app.py",
         "Contém todas as rotas Flask (31 endpoints). Responsavel pela logica de negocio: "
         "validacao de entrada, orquestracao de queries, autenticacao, CSRF, formatacao de "
         "respostas JSON e renderizacao de templates."),
        ("View — templates/*.html",
         "10 templates Jinja2 que herdam de base.html. Responsaveis exclusivamente pela "
         "apresentacao. Nenhuma logica de negocio existe nos templates — apenas renderizacao "
         "condicional e iteracao sobre dados passados pelo controller."),
        ("Assets — static/",
         "style.css (design system CSS customizado, ~800 linhas) e ui.js (JavaScript vanilla "
         "para interatividade: modais, filtros AJAX do dashboard, Chart.js, badge de alertas)."),
    ], header=("Camada", "Responsabilidade")))
    story.append(sp(10))

    story.append(p("Dois Modos de Operacao", "H2"))
    story.append(sp(6))
    story.append(p(
        "O sistema opera em dois modos distintos e independentes, com mecanismos de autenticacao "
        "separados para cada contexto:"
    ))
    story.append(sp(4))

    dual_rows = [
        ["Interface Web (SSR)", "Usuarios humanos via browser",
         "Session cookie + CSRF token", "Jinja2 HTML + CSS + JS"],
        ["API REST Externa", "Sistemas externos (ERP, scripts)",
         "Header X-API-Key", "JSON puro (application/json)"],
    ]
    h_s = ParagraphStyle("dh", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    c_s = ParagraphStyle("dc", fontSize=9, fontName="Helvetica", textColor=C_DARK)
    dual_data = [[Paragraph(h, h_s) for h in ["Modo", "Consumidor", "Autenticacao", "Formato de Resposta"]]]
    for r in dual_rows:
        dual_data.append([Paragraph(c, c_s) for c in r])
    dual_t = Table(dual_data, colWidths=[CONTENT_W*0.22, CONTENT_W*0.26, CONTENT_W*0.26, CONTENT_W*0.26])
    dual_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_DARK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(dual_t)
    story.append(sp(10))

    story.append(p("Diagrama Logico de Camadas", "H2"))
    story.append(sp(6))
    story.append(Paragraph(
        "Browser / Sistema Externo\n"
        "        |\n"
        "        v\n"
        "  [ Flask Router ]  <-- WSGI / HTTP\n"
        "        |\n"
        "   _____|______\n"
        "  |             |\n"
        "  v             v\n"
        "login_required  api_key_required\n"
        "(session)       (X-API-Key header)\n"
        "  |             |\n"
        "  v             v\n"
        "[ Route Handler — app.py ]\n"
        "        |\n"
        "        v\n"
        "[ database.py ]  <-- get_db_connection() / parametrized SQL\n"
        "        |\n"
        "        v\n"
        "[ SQLite — demandas.db ]",
        S["Code"]
    ))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S03 — STACK DE TECNOLOGIAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(3, "Stack de Tecnologias",
        "Cada tecnologia escolhida e seu papel especifico no sistema"))
    story.append(sp(12))

    story.append(p("Backend", "H2"))
    story.append(sp(4))
    story.append(tech_table([
        ("Python 3.12",      "3.12.2",  "Linguagem principal. Escolhida por legibilidade, ecossistema maduro e suporte nativo a SQLite e JSON."),
        ("Flask",            "3.0.3",   "Microframework WSGI. Responsavel pelo roteamento HTTP, gerenciamento de sessao, renderizacao de templates e contexto de requisicao."),
        ("Werkzeug",         "3.1.3",   "Dependencia do Flask. Usada diretamente para hashing de senhas via PBKDF2-SHA256 (generate_password_hash / check_password_hash)."),
        ("flasgger",         "0.9.7.1", "Gera automaticamente a interface Swagger UI a partir de docstrings YAML nas funcoes Flask. Serve o spec OpenAPI em /apispec.json."),
        ("openpyxl",         "3.1.5",   "Geracao de planilhas .xlsx para exportacao de relatorios do dashboard com formatacao (cores, larguras de coluna, cabecalho destacado)."),
        ("secrets (stdlib)", "—",       "Geracao criptograficamente segura das API Keys via token_urlsafe(32), producindo strings de 43 caracteres base64url."),
        ("csv / io (stdlib)","—",       "Exportacao de relatorios em formato CSV com BOM UTF-8 para compatibilidade com Excel brasileiro."),
    ]))
    story.append(sp(10))

    story.append(p("Frontend", "H2"))
    story.append(sp(4))
    story.append(tech_table([
        ("Jinja2",      "3.x (Flask)", "Motor de templates SSR (Server-Side Rendering). Heranca de templates via base.html, auto-escape XSS, filtros customizados."),
        ("CSS Customizado", "—",       "Design system proprio (~800 linhas). Variaveis CSS (--primary, --surface-raised), componentes reutilizaveis (card, chip, btn, data-table, kpi-grid)."),
        ("JavaScript Vanilla","ES6+",  "Sem framework. Usado para: polling de alertas (IIFE + setInterval), graficos Chart.js, filtros AJAX do dashboard, toggles de UI."),
        ("Chart.js",    "4.4 (CDN)",   "Graficos interativos no dashboard: donut (status), barras horizontais (prioridade), linha temporal (criadas vs. concluidas)."),
    ]))
    story.append(sp(10))

    story.append(p("Banco de Dados e Infraestrutura", "H2"))
    story.append(sp(4))
    story.append(tech_table([
        ("SQLite 3",      "stdlib",  "Banco embarcado, arquivo unico (demandas.db). Zero configuracao. PRAGMA foreign_keys=ON garante integridade referencial."),
        ("WSGI (Flask dev)","—",     "Servidor de desenvolvimento embutido. Em producao, recomenda-se Gunicorn + Nginx (ver Secao 13)."),
        ("Playwright",    "1.44+",   "Automacao de browser para captura de screenshots dos PDFs de documentacao (uso exclusivo em ferramentas de dev, nao em producao)."),
        ("reportlab",     "4.0+",    "Geracao dos PDFs de relatorios e documentacao tecnica. Usado nas ferramentas auxiliares, nao no runtime da aplicacao."),
    ]))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S04 — DECISÕES TÉCNICAS E JUSTIFICATIVAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(4, "Decisoes Tecnicas e Justificativas",
        "Por que cada escolha foi feita — o raciocinio por tras da arquitetura"))
    story.append(sp(12))

    decisions = [
        (
            "Flask em vez de Django",
            "Django e um framework full-stack com ORM, admin, migrations automaticas e muitas "
            "convencoes impostas. Para o SGDI — um sistema interno de escala controlada — essa "
            "complexidade seria overhead desnecessario. Flask permite construir exatamente o que "
            "e necessario, sem magica implicita, tornando o codigo mais facil de auditar e entender "
            "por qualquer desenvolvedor Python. A ausencia de um ORM tambem foi intencional: "
            "SQL parametrizado explicito e mais transparente e permite otimizacoes especificas "
            "(como o ORDER BY com CASE para prioridade)."
        ),
        (
            "SQLite em vez de PostgreSQL ou MySQL",
            "SQLite e um banco embarcado — nao requer servidor, processo separado, configuracao "
            "de conexao ou gerenciamento de usuarios. Para um sistema interno com dezenas de "
            "usuarios simultaneos (nao milhares), SQLite e absolutamente suficiente e oferece "
            "zero-config deployment: o banco e um unico arquivo. A decisao inclui a clareza "
            "de migracao: se a escala crescer, a camada database.py pode ser reescrita para "
            "PostgreSQL sem alterar nenhuma linha do app.py — pois toda a logica de acesso "
            "esta isolada em get_db_connection()."
        ),
        (
            "Server-Side Rendering (SSR) em vez de SPA",
            "Uma Single Page Application (React, Vue) exigiria um projeto frontend separado, "
            "build toolchain (Node.js, npm/Yarn, Webpack/Vite), deploy independente e uma API "
            "completa para todas as operacoes — incluindo as que hoje sao simples POSTs de "
            "formulario. Para um sistema interno usado por um time pequeno em desktop, o SSR "
            "com Jinja2 e equivalente em experiencia de usuario, mais simples de manter e sem "
            "dependencia de ecosistema JavaScript em producao. As unicas partes interativas "
            "(dashboard AJAX, graficos) usam JavaScript vanilla sem framework."
        ),
        (
            "Sessao server-side em vez de JWT",
            "JWT (JSON Web Tokens) e ideal quando o backend e stateless e precisa escalar "
            "horizontalmente, ou quando ha multiplos servicos consumindo a mesma autenticacao. "
            "No SGDI — sistema monolito com um unico servidor — sessions Flask (backed em "
            "cookies assinados com SECRET_KEY) sao mais simples, sem necessidade de implementar "
            "refresh tokens, revogacao de tokens ou armazenamento de blacklist. Para a API REST "
            "externa, API Keys foram escolhidas por serem stateless, revogueis instantaneamente "
            "e nao exigirem expiracao/renovacao."
        ),
        (
            "CSS Customizado em vez de Bootstrap ou Tailwind",
            "Bootstrap impoe uma estetica generica e adiciona ~150KB de CSS nao utilizado. "
            "Tailwind requer um processo de build (PostCSS, PurgeCSS). O design system customizado "
            "do SGDI usa variaveis CSS nativas (--primary, --surface-raised, etc.) e componentes "
            "semanticos (.card, .chip, .btn--primary), resultando em ~30KB minificado e total "
            "controle visual. Nenhuma dependencia de build — o arquivo e servido estaticamente."
        ),
        (
            "Dual-auth: Session para web + API Key para REST",
            "Usuarios humanos acessam via browser com session e CSRF — o modelo mais seguro "
            "contra ataques CSRF em formularios HTML. Sistemas externos (ERPs, scripts) usam "
            "X-API-Key — stateless, sem necessidade de gerenciar cookies, e revogueis "
            "individualmente sem afetar outros integradores. Os dois mecanismos coexistem "
            "via decorators (@login_required e @api_key_required), aplicados por rota."
        ),
        (
            "Migrations manuais com PRAGMA table_info",
            "Em vez de uma ferramenta de migration (Alembic, Flask-Migrate), o SGDI usa um "
            "padrao simples: antes de cada ALTER TABLE, verifica via PRAGMA table_info se a "
            "coluna ja existe. Isso torna a aplicacao auto-migrante a cada inicializacao, "
            "sem estados externos de migration, sem arquivos de versao e sem risco de aplicar "
            "migrations duplicadas. A funcao _migrate_demands() em database.py encapsula toda "
            "essa logica."
        ),
        (
            "Ordenacao de prioridade via CASE SQL",
            "A ordenacao de demandas por prioridade (Critica > Alta > Media > Baixa) e "
            "implementada como uma expressao CASE na clausula ORDER BY do SQL. Isso garante "
            "que a ordenacao correta ocorra no nivel do banco — mais eficiente do que trazer "
            "todos os registros e ordenar em Python — e e reutilizavel em qualquer query "
            "via a constante PRIORIDADE_ORDEM_SQL em database.py."
        ),
    ]

    for i, (title_d, body_d) in enumerate(decisions):
        story.append(p(f"D{i+1:02d}  {title_d}", "H3"))
        story.append(p(body_d))
        story.append(sp(6))

    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S05 — ALTERNATIVAS AVALIADAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(5, "Alternativas Avaliadas e Descartadas",
        "O que foi considerado e por que nao foi adotado"))
    story.append(sp(12))

    story.append(p(
        "Toda decisao arquitetural envolve trade-offs. A tabela abaixo documenta as "
        "alternativas avaliadas durante o desenvolvimento, por que foram descartadas "
        "e qual criterio principal motivou a escolha final."
    ))
    story.append(sp(8))

    story.append(comparison_table([
        ["Supabase",
         "Backend-as-a-Service com PostgreSQL gerenciado, auth integrada, realtime",
         "SQLite local",
         "Dependencia de servico externo pago. Requer migracao de SQLite para PostgreSQL, reescrita de database.py e configuracao de rede. Adiciona latencia de rede em toda query. Overkill para sistema interno."],
        ["React / Vue SPA",
         "Frontend desacoplado consumindo API JSON, melhor UX interativa",
         "Jinja2 SSR",
         "Exige build toolchain separado (Node, npm, Vite), deploy independente e duplicacao de logica de validacao. Para uso interno desktop, SSR e equivalente em UX com 1/10 da complexidade."],
        ["Django",
         "Framework full-stack com ORM, admin gerado, migrations automaticas",
         "Flask + SQL puro",
         "ORM abstrai queries mas dificulta otimizacoes especificas (como CASE para prioridade). Admin gerado exige customizacao extensa. Curva de aprendizado maior sem beneficio proporcional para este escopo."],
        ["JWT Auth",
         "Tokens stateless para autenticacao, ideal para APIs distribuidas",
         "Session + API Key",
         "JWT exige refresh token, revogacao por blacklist e clock sync entre servicos. Para monolito com sessao unica e API key revogueis, o par session+API Key e mais simples e igualmente seguro."],
        ["PostgreSQL / MySQL",
         "SGBDs relacionais com suporte a concorrencia pesada e recursos avancados",
         "SQLite",
         "Requerem processo de servidor separado, configuracao de conexao, usuario/senha e backup especifico. Para dezenas de usuarios simultaneos, SQLite com WAL mode suporta centenas de leituras concorrentes sem degradacao."],
        ["Bootstrap / Tailwind",
         "Frameworks CSS que aceleram desenvolvimento de UI",
         "CSS customizado",
         "Bootstrap: CSS generica, dificil de customizar sem sobrescrever. Tailwind: requer build toolchain, classes verbosas no HTML. Design system proprio tem tamanho menor e controle total sem dependencias de build."],
        ["Redis (cache/session)",
         "Cache em memoria para sessoes e dados frequentes",
         "Session Flask nativa",
         "Adiciona infraestrutura (processo Redis, configuracao, monitoramento). Para este volume, sessoes assinadas em cookie sao suficientes e sem dependencia de infraestrutura adicional."],
        ["Celery (tarefas async)",
         "Processamento assincrono de tarefas pesadas (relatorios, emails)",
         "Processamento sincrono",
         "As exportacoes (CSV/XLSX/PDF) sao geradas on-demand em menos de 500ms para os volumes atuais. Celery adicionaria worker processes, broker (Redis/RabbitMQ) e complexidade sem ganho observavel."],
    ], ["Alternativa", "Vantagem", "Escolha Feita", "Motivo da Rejeicao"]))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S06 — SEGURANÇA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(6, "Estrategias de Seguranca",
        "Protecao contra as principais ameacas — OWASP Top 10"))
    story.append(sp(12))

    story.append(p(
        "O SGDI implementa defesas em profundidade contra as principais categorias de "
        "vulnerabilidade web catalogadas pelo OWASP Top 10 2021. Nenhuma mitigacao depende "
        "de seguranca por obscuridade — todas sao implementacoes tecnicas verificaveis."
    ))
    story.append(sp(8))

    story.append(security_table([
        ["A01 — Broken Access Control",
         "Todas as rotas exigem autenticacao previa. Edicao limitada ao proprio usuario. "
         "Decorators @login_required e @api_key_required aplicados por rota.",
         "@login_required em 28 de 31 rotas"],
        ["A02 — Cryptographic Failures",
         "Senhas nunca armazenadas em texto puro. Hash PBKDF2-SHA256 com salt aleatorio "
         "via werkzeug.security. Chaves de API geradas com CSPRNG.",
         "generate_password_hash() + secrets.token_urlsafe(32)"],
        ["A03 — SQL Injection",
         "Zero concatenacao de strings em queries SQL. Todos os valores externos "
         "passam como parametros ? no cursor.execute(). Validacao de enums antes da query.",
         "conn.execute('SELECT ... WHERE id=?', (id,))"],
        ["A03 — Cross-Site Scripting (XSS)",
         "Jinja2 realiza auto-escape de todas as variaveis por padrao. "
         "Conteudo HTML so e renderizado onde explicitamente marcado como |safe.",
         "Jinja2 auto-escape ativo em todos os templates"],
        ["A04 — Insecure Design",
         "Revisao do status de demanda valida enum antes de persistir. "
         "Campos obrigatorios validados no servidor, nao apenas no frontend.",
         "if prioridade not in PRIORIDADES: return error"],
        ["A05 — Security Misconfiguration",
         "SECRET_KEY lida de variavel de ambiente. Mensagem de erro generica exibida "
         "ao usuario — stack trace nunca exposto. Debug desabilitado em producao.",
         "os.environ.get('SECRET_KEY', fallback_dev_only)"],
        ["A07 — Auth Failures",
         "Sessao invalidada no logout (session.clear()). CSRF token validado "
         "em todo POST de formulario. API Key verificada a cada requisicao.",
         "_validate_csrf() + session.clear() + api_key_required"],
        ["A09 — Security Logging Failures",
         "Historico de status registra autor e timestamp de cada transicao. "
         "Criacao de API Key rastreada com usuario e data.",
         "INSERT INTO historico_status (autor, data, ...)"],
        ["API — Autenticacao",
         "API REST totalmente separada da sessao web. Chave revogavel individualmente "
         "sem afetar outros sistemas. Verificacao a cada requisicao (stateless).",
         "SELECT id FROM api_keys WHERE chave=? AND ativo=1"],
    ]))
    story.append(sp(10))

    story.append(p("Implementacao do CSRF", "H2"))
    story.append(sp(4))
    story.append(p(
        "O mecanismo CSRF customizado funciona da seguinte forma: ao renderizar qualquer "
        "formulario, o template inclui um campo oculto com o token armazenado na sessao. "
        "A funcao _validate_csrf() em app.py compara o token do formulario com o da sessao "
        "usando hmac.compare_digest() para prevenir timing attacks. Se nao houver match, "
        "a requisicao e abortada com HTTP 403. Todos os 13 formularios POST do sistema "
        "passam por esta validacao."
    ))
    story.append(sp(6))
    story.append(Paragraph(
        "# Geracao do token (no contexto de requisicao):\n"
        "if 'csrf_token' not in session:\n"
        "    session['csrf_token'] = secrets.token_hex(32)\n\n"
        "# Validacao antes de processar qualquer POST:\n"
        "def _validate_csrf():\n"
        "    token = request.form.get('csrf_token', '')\n"
        "    if not hmac.compare_digest(token, session.get('csrf_token', '')):\n"
        "        abort(403)",
        S["Code"]
    ))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S07 — API REST
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(7, "Estrutura da API REST",
        "Design, endpoints, autenticacao e contrato de comunicacao"))
    story.append(sp(12))

    story.append(p(
        "A API REST do SGDI e uma camada separada, construida sobre os mesmos dados e "
        "banco do sistema web, mas com autenticacao e formato de resposta proprios. "
        "Foi projetada para ser consumida por sistemas externos (ERPs, scripts de automacao, "
        "apps mobile) sem depender de sessao, cookies ou CSRF."
    ))
    story.append(sp(8))

    story.append(p("Principios de Design da API", "H2"))
    story.append(sp(4))
    api_principles = [
        "<b>Stateless</b>: cada requisicao e autossuficiente — inclui a chave de autenticacao no header",
        "<b>Envelope padronizado</b>: todas as respostas seguem {success, data, meta} ou {success, error}",
        "<b>Codigos HTTP semanticos</b>: 200 (OK), 201 (Created), 400 (Bad Request), 401, 403, 404",
        "<b>Validacao no servidor</b>: enums, campos obrigatorios e tipos verificados antes de persistir",
        "<b>Rastreabilidade</b>: toda criacao e mudanca de status gera registro em historico_status",
        "<b>Documentacao automatica</b>: Swagger UI gerado via flasgger a partir de docstrings YAML",
    ]
    for pr in api_principles:
        story.append(bul(pr))
    story.append(sp(10))

    story.append(p("Endpoints Disponiveis", "H2"))
    story.append(sp(4))
    story.append(routes_table([
        ("GET",   "/api/v1/demandas",                    "Lista demandas (filtros: status, prioridade, responsavel_id, limit, offset)", "API Key"),
        ("POST",  "/api/v1/demandas",                    "Cria nova demanda (body JSON: titulo, descricao, solicitante, prioridade)", "API Key"),
        ("GET",   "/api/v1/demandas/{id}",               "Retorna todos os campos de uma demanda especifica", "API Key"),
        ("PATCH", "/api/v1/demandas/{id}/status",        "Atualiza status (Aberta/Em andamento/Concluida/Cancelada) com registro no historico", "API Key"),
        ("GET",   "/api/v1/demandas/{id}/comentarios",   "Lista comentarios de uma demanda em ordem cronologica", "API Key"),
        ("POST",  "/api/v1/demandas/{id}/comentarios",   "Adiciona comentario (body JSON: autor, comentario)", "API Key"),
        ("GET",   "/api/v1/usuarios",                    "Lista usuarios ativos com id, username e nome", "API Key"),
    ]))
    story.append(sp(10))

    story.append(p("Formato do Envelope de Resposta", "H2"))
    story.append(sp(4))
    story.append(Paragraph(
        "# Sucesso (GET lista):\n"
        '{ "success": true, "data": [...], "meta": { "total": 42 } }\n\n'
        "# Sucesso (GET/PATCH objeto):\n"
        '{ "success": true, "data": { "id": 7, "titulo": "...", ... } }\n\n'
        "# Sucesso (POST — recurso criado):\n"
        '{ "success": true, "data": { "id": 24, "status": "Aberta" } }  → HTTP 201\n\n'
        "# Erro:\n"
        '{ "success": false, "error": "Campos obrigatorios: titulo, descricao, solicitante, prioridade" }',
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Swagger / OpenAPI", "H2"))
    story.append(sp(4))
    story.append(p(
        "A documentacao da API e gerada automaticamente pela biblioteca <b>flasgger</b>, "
        "que le as docstrings YAML embutidas em cada funcao de rota e constroi uma spec "
        "OpenAPI 2.0 servida em <b>/apispec.json</b>. A interface Swagger UI interativa "
        "fica disponivel em <b>/apidocs</b> e permite testar todos os endpoints diretamente "
        "no browser, inclusive com autenticacao por API Key via o botao Authorize."
    ))
    story.append(sp(6))
    for el in img_block("swagger_top", "Interface Swagger UI — documentacao interativa dos 7 endpoints da API REST", max_h=9*cm):
        story.append(el)
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S08 — AUTENTICAÇÃO E AUTORIZAÇÃO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(8, "Autenticacao e Autorizacao",
        "Dois mecanismos independentes para dois perfis de consumidor"))
    story.append(sp(12))

    story.append(p("Autenticacao Web — Session + CSRF", "H2"))
    story.append(sp(4))
    story.append(p(
        "O fluxo de autenticacao para usuarios humanos segue o padrao de sessao stateful "
        "tipico de aplicacoes web tradicionais. O usuario fornece username e senha, que sao "
        "verificados contra o hash PBKDF2 armazenado no banco. Em caso de sucesso, o ID do "
        "usuario e armazenado na sessao Flask (cookie assinado com SECRET_KEY). "
        "O decorator @login_required verifica a presenca de usuario_id na sessao antes de "
        "executar qualquer rota protegida."
    ))
    story.append(sp(6))
    story.append(Paragraph(
        "# Fluxo de login:\n"
        "usuario = authenticate_user(username, senha)  # verifica hash bcrypt\n"
        "session['usuario_id'] = usuario['id']         # armazena ID na sessao\n"
        "session['csrf_token'] = secrets.token_hex(32) # gera token CSRF\n\n"
        "# Decorator de protecao:\n"
        "def login_required(f):\n"
        "    @wraps(f)\n"
        "    def decorated(*args, **kwargs):\n"
        "        if 'usuario_id' not in session:\n"
        "            return redirect(url_for('login'))\n"
        "        return f(*args, **kwargs)\n"
        "    return decorated",
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Autenticacao API — API Key", "H2"))
    story.append(sp(4))
    story.append(p(
        "Sistemas externos autenticam via header <b>X-API-Key</b>. A chave e verificada "
        "a cada requisicao contra a tabela api_keys — sem sessao, sem cookie, sem estado. "
        "Chaves podem ser revogadas individualmente (ativo=0) sem afetar outros integradores. "
        "A chave e gerada com secrets.token_urlsafe(32) — 256 bits de entropia criptografica — "
        "e exibida apenas uma vez no momento da criacao."
    ))
    story.append(sp(6))
    story.append(Paragraph(
        "# Geracao da chave:\n"
        "nova_chave = secrets.token_urlsafe(32)  # 43 chars, 256 bits\n"
        "conn.execute('INSERT INTO api_keys (chave, descricao, criado_por) VALUES (?,?,?)',\n"
        "             (nova_chave, descricao, session['usuario_id']))\n\n"
        "# Decorator de verificacao (por requisicao):\n"
        "def api_key_required(f):\n"
        "    @wraps(f)\n"
        "    def decorated(*args, **kwargs):\n"
        "        chave = request.headers.get('X-API-Key', '').strip()\n"
        "        if not chave:\n"
        "            return jsonify({'success': False, 'error': '...'}), 401\n"
        "        row = conn.execute(\n"
        "            'SELECT id FROM api_keys WHERE chave=? AND ativo=1', (chave,)\n"
        "        ).fetchone()\n"
        "        if not row:\n"
        "            return jsonify({'success': False, 'error': '...'}), 403\n"
        "        return f(*args, **kwargs)\n"
        "    return decorated",
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Tabela de Controle de Acesso por Rota", "H2"))
    story.append(sp(4))
    access_rows = [
        ("Interface Web (17 rotas)",  "Session Flask",    "Qualquer usuario autenticado"),
        ("Edicao de demandas",         "Session + Dono",   "Apenas o criador da demanda"),
        ("Dashboard (7 rotas AJAX)",  "Session Flask",    "Qualquer usuario autenticado"),
        ("API REST v1 (7 endpoints)", "Header X-API-Key", "Qualquer chave ativa no banco"),
        ("Swagger UI (/apidocs)",     "Publica",          "Sem autenticacao — documentacao apenas"),
        ("/api/keys (gestao)",        "Session Flask",    "Qualquer usuario autenticado"),
        ("/login",                    "Publica",          "Unica rota publica da aplicacao"),
    ]
    h_s2 = ParagraphStyle("ach", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)
    v_s2 = ParagraphStyle("acv", fontSize=9, fontName="Helvetica", textColor=C_DARK)
    ac_data = [[Paragraph(h, h_s2) for h in ["Escopo", "Mecanismo", "Permissao"]]]
    for row in access_rows:
        ac_data.append([Paragraph(c, v_s2) for c in row])
    ac_t = Table(ac_data, colWidths=[CONTENT_W*0.38, CONTENT_W*0.28, CONTENT_W*0.34])
    ac_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(ac_t)
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S09 — ORGANIZAÇÃO DO CÓDIGO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(9, "Organizacao do Codigo e Padroes Adotados",
        "Estrutura de arquivos, padroes de nomenclatura e decisoes de design interno"))
    story.append(sp(12))

    story.append(Paragraph(
        "sgdi/\n"
        "├── app.py              # Controller — 2080 linhas, 31 rotas Flask\n"
        "├── database.py         # Model — tabelas, migrations, seed, queries utilitarias\n"
        "├── demandas.db         # Banco SQLite (gerado automaticamente)\n"
        "├── requirements.txt    # Dependencias do projeto\n"
        "├── templates/\n"
        "│   ├── base.html       # Layout base com navbar, footer, flash, JS de alertas\n"
        "│   ├── dashboard.html  # Dashboard com KPIs, graficos Chart.js e tabela critica\n"
        "│   ├── index.html      # Lista de demandas abertas\n"
        "│   ├── concluidas.html # Lista de demandas concluidas\n"
        "│   ├── nova_demanda.html\n"
        "│   ├── editar.html\n"
        "│   ├── detalhes.html   # Detalhe + timeline de historico + acoes\n"
        "│   ├── usuarios.html\n"
        "│   ├── api_keys.html\n"
        "│   └── login.html\n"
        "├── static/\n"
        "│   ├── style.css       # Design system customizado (~800 linhas)\n"
        "│   └── ui.js           # JS vanilla — modais, AJAX, Chart.js\n"
        "└── gerar_*.py          # Ferramentas auxiliares de documentacao (dev only)",
        S["Code"]
    ))
    story.append(sp(10))

    story.append(p("Padroes de Nomenclatura", "H2"))
    story.append(sp(4))
    story.append(kv_table([
        ("Rotas Flask",            "snake_case (nova_demanda, api_v1_demandas_list)"),
        ("Funcoes privadas",       "Prefixo _ (_validate_csrf, _api_ok, _api_err, _registrar_historico)"),
        ("Constantes",             "UPPER_SNAKE_CASE (STATUS_ABERTA, PRIORIDADE_CRITICA, TODOS_STATUS)"),
        ("Variaveis de template",  "snake_case (demanda, usuario_logado, criado_em)"),
        ("Classes CSS",            "BEM adaptado: .card, .card__header, .btn--primary, .chip--critica"),
        ("Endpoints API",          "REST semantico: substantivos em plural, PATCH para updates parciais"),
        ("Tabelas SQL",            "plural_snake_case (demandas, historico_status, api_keys)"),
    ], header=("Elemento", "Convencao")))
    story.append(sp(10))

    story.append(p("Padroes de Implementacao Recorrentes", "H2"))
    story.append(sp(4))
    patterns = [
        "<b>Decorator pattern</b>: @login_required e @api_key_required aplicados por rota, sem duplicacao de logica",
        "<b>Context manager para DB</b>: get_db() retorna conexao, finally conn.close() garante fechamento mesmo em excecoes",
        "<b>Constants as guard</b>: validacao de enums usa 'if prioridade not in PRIORIDADES' em vez de valores literais hardcoded",
        "<b>Template inheritance</b>: todos os templates estendem base.html com {% block content %}, garantindo navbar e footer consistentes",
        "<b>AJAX + JSON interno</b>: dashboard busca dados via fetch() para /api/dashboard/* sem recarregar a pagina",
        "<b>Dual JOIN</b>: demandas com solicitante e responsavel usam dois JOINs aliased na mesma tabela usuarios (u e resp)",
        "<b>Filtros customizados Jinja2</b>: display_datetime formata datas do banco para exibicao sem logica no template",
    ]
    for pat in patterns:
        story.append(bul(pat))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S10 — PERFORMANCE E OTIMIZAÇÃO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(10, "Performance e Otimizacao",
        "Decisoes que impactam velocidade, consumo de recursos e experiencia do usuario"))
    story.append(sp(12))

    story.append(p(
        "O SGDI foi desenvolvido com foco em <b>performance percebida</b> — a sensacao de "
        "rapidez que o usuario experimenta — e em <b>eficiencia de recursos</b> no servidor. "
        "As decisoes abaixo refletem esse objetivo."
    ))
    story.append(sp(8))

    perf_items = [
        (
            "SQLite com PRAGMA foreign_keys = ON",
            "A verificacao de integridade referencial e habilitada explicitamente a cada conexao. "
            "Embora adicione uma verificacao extra em INSERTs, previne inconsistencias que exigiriam "
            "queries de correcao muito mais custosas. O custo e desprezivel para o volume atual."
        ),
        (
            "Queries paginadas na API REST",
            "O endpoint GET /api/v1/demandas aceita limit (max 200) e offset para paginacao. "
            "A query usa LIMIT ? OFFSET ? diretamente no SQL — o banco retorna apenas os registros "
            "necessarios, sem trazer todo o dataset para Python."
        ),
        (
            "Ordenacao no banco (CASE SQL)",
            "A ordenacao por prioridade e feita no SQL via CASE WHEN, nao em Python apos o fetch. "
            "Para conjuntos grandes, isso reduz significativamente os dados transferidos entre banco "
            "e aplicacao, pois o banco pode usar o resultado do CASE diretamente no plano de execucao."
        ),
        (
            "Dashboard AJAX (zero SSR para atualizacoes)",
            "O dashboard nao recarrega a pagina ao aplicar filtros. O JavaScript faz fetch() "
            "para /api/dashboard/data retornando JSON, e atualiza apenas os elementos afetados no DOM. "
            "Isso elimina re-renderizacao de templates, re-envio de CSS/JS e tempo de parse no browser."
        ),
        (
            "Polling de alertas com intervalo de 60 segundos",
            "O badge de alertas no navbar atualiza automaticamente via fetch('/api/alerts/count') "
            "a cada 60 segundos. O intervalo foi escolhido para balancear frescor da informacao "
            "com carga no servidor — para o volume atual, uma query a cada 60s por usuario "
            "e desprezivel."
        ),
        (
            "Exportacao em streaming (io.BytesIO)",
            "Relatorios CSV e Excel sao gerados em memoria usando io.BytesIO e enviados "
            "diretamente como Response sem escrever em disco. Isso elimina I/O de arquivo, "
            "evita acumulacao de arquivos temporarios e reduz latencia de resposta."
        ),
        (
            "CSS como arquivo estatico (sem build)",
            "O design system e um unico arquivo CSS servido estaticamente. Sem preprocessador, "
            "sem minificacao obrigatoria, sem FOUC. O browser faz cache do arquivo entre "
            "requisicoes, eliminando redownload."
        ),
        (
            "Inicializacao auto-migrante",
            "initialize_database() e chamada uma vez no startup do app (app.py linha 84). "
            "Ela verifica e cria tabelas/colunas ausentes, mas retorna imediatamente se nada "
            "precisar ser alterado. O custo de PRAGMA table_info() e negligenciavel."
        ),
    ]
    for title_p, body_p in perf_items:
        story.append(p(f"• <b>{title_p}</b>", "Bullet"))
        story.append(Paragraph(f"  {body_p}", ParagraphStyle(
            f"ps_{title_p[:10]}", fontSize=9, fontName="Helvetica", textColor=C_MUTED,
            leftIndent=28, spaceAfter=6, leading=13)))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S11 — FLUXO GERAL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(11, "Fluxo Geral da Aplicacao",
        "Jornada de uma demanda do inicio ao fim"))
    story.append(sp(12))

    story.append(p("Fluxo 1 — Usuario via Interface Web", "H2"))
    story.append(sp(4))
    web_flow = [
        ("01", "Autenticacao",
         "Usuario acessa /login, fornece username e senha. O servidor verifica o hash PBKDF2. "
         "Em caso de sucesso, usuario_id e armazenado na sessao e um token CSRF e gerado."),
        ("02", "Abertura da Demanda",
         "Usuario acessa /nova_demanda, preenche titulo, descricao, prioridade, prazo e responsavel. "
         "O servidor valida o CSRF, verifica os campos obrigatorios e insere na tabela demandas. "
         "Um registro em historico_status (None -> Aberta) e criado imediatamente."),
        ("03", "Acompanhamento",
         "Demanda aparece na lista /demandas ordenada por prioridade. O responsavel pode "
         "clicar em 'Em andamento' gerando novo registro no historico. Comentarios podem "
         "ser adicionados via formulario no detalhes.html."),
        ("04", "Dashboard",
         "Gestores acessam / para ver KPIs em tempo real (Total, Abertas, Atrasadas, Criticas). "
         "Graficos Chart.js mostram distribuicao por status e linha temporal. "
         "Badge no navbar pisca se houver alertas de demandas paradas ha mais de 7 dias."),
        ("05", "Conclusao ou Cancelamento",
         "Ao concluir, o campo data_conclusao e preenchido com datetime.now(). "
         "A demanda some da lista de abertas e aparece em /concluidas. "
         "O historico registra o status final com autor e timestamp."),
        ("06", "Exportacao",
         "Gestor clica em Exportar CSV/Excel/PDF no dashboard. O servidor gera o arquivo "
         "em memoria com os filtros ativos e retorna como download — sem arquivo temporario em disco."),
    ]
    num_s = ParagraphStyle("fwn", fontSize=12, fontName="Helvetica-Bold",
                            textColor=C_PRIMARY, alignment=TA_CENTER)
    ttl_s = ParagraphStyle("fwt", fontSize=10, fontName="Helvetica-Bold", textColor=C_DARK, leading=13)
    bdy_s = ParagraphStyle("fwb", fontSize=9, fontName="Helvetica", textColor=C_MUTED, leading=13)
    for num, title_f, body_f in web_flow:
        t = Table([[
            Table([[Paragraph(num, num_s)]],
                  colWidths=[1.1*cm],
                  style=TableStyle([
                      ("BACKGROUND",    (0,0), (-1,-1), C_BG),
                      ("BOX",           (0,0), (-1,-1), 1.5, C_PRIMARY),
                      ("TOPPADDING",    (0,0), (-1,-1), 6),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                  ])),
            [Paragraph(title_f, ttl_s), Paragraph(body_f, bdy_s)],
        ]], colWidths=[1.5*cm, CONTENT_W - 1.5*cm])
        t.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(t)
        story.append(sp(2))

    story.append(sp(12))
    story.append(p("Fluxo 2 — Sistema Externo via API REST", "H2"))
    story.append(sp(4))
    api_flow = [
        ("01", "Obtencao da Chave",
         "Administrador acessa /api/keys no browser, cria uma chave com descricao identificadora. "
         "A chave completa e exibida uma unica vez — deve ser copiada e armazenada com seguranca."),
        ("02", "Abertura via API",
         "Sistema externo faz POST /api/v1/demandas com X-API-Key no header e body JSON. "
         "O servidor cria a demanda e retorna {id, status} com HTTP 201."),
        ("03", "Atualizacao de Status",
         "Ao processar a demanda internamente, o sistema externo faz PATCH /api/v1/demandas/{id}/status "
         "para mover para 'Em andamento' ou 'Concluida'. O historico e atualizado automaticamente."),
        ("04", "Comentarios programaticos",
         "O sistema externo pode adicionar comentarios automaticos via POST /comentarios — "
         "por exemplo, logs de processamento ou mensagens de status para o time interno."),
        ("05", "Consulta e Monitoramento",
         "O sistema externo pode consultar GET /api/v1/demandas?status=Aberta&responsavel_id=2 "
         "para listar apenas as demandas pendentes atribuidas a um responsavel especifico."),
    ]
    for num, title_f, body_f in api_flow:
        t = Table([[
            Table([[Paragraph(num, ParagraphStyle(
                f"afn{num}", fontSize=12, fontName="Helvetica-Bold",
                textColor=C_SUCCESS, alignment=TA_CENTER))]],
                  colWidths=[1.1*cm],
                  style=TableStyle([
                      ("BACKGROUND",    (0,0), (-1,-1), C_BG),
                      ("BOX",           (0,0), (-1,-1), 1.5, C_SUCCESS),
                      ("TOPPADDING",    (0,0), (-1,-1), 6),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                  ])),
            [Paragraph(title_f, ttl_s), Paragraph(body_f, bdy_s)],
        ]], colWidths=[1.5*cm, CONTENT_W - 1.5*cm])
        t.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(t)
        story.append(sp(2))

    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S12 — TODAS AS ROTAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(12, "Inventario Completo de Rotas",
        "Todos os 31 endpoints do sistema com metodo, autenticacao e funcao"))
    story.append(sp(12))

    story.append(p("Interface Web — Rotas com Renderizacao HTML", "H2"))
    story.append(sp(4))
    story.append(routes_table([
        ("GET",  "/login",                    "Exibe formulario de login",                              "Publica"),
        ("POST", "/login",                    "Autentica usuario, cria sessao e CSRF token",            "Publica"),
        ("POST", "/logout",                   "Invalida sessao (session.clear())",                      "Session"),
        ("GET",  "/demandas",                 "Lista demandas abertas e em andamento com filtros",      "Session"),
        ("GET",  "/concluidas",               "Lista demandas concluidas e canceladas",                 "Session"),
        ("GET",  "/nova_demanda",             "Exibe formulario de criacao de demanda",                 "Session"),
        ("POST", "/nova_demanda",             "Persiste nova demanda e cria historico inicial",         "Session"),
        ("GET",  "/editar/<id>",              "Exibe formulario de edicao (apenas o criador)",          "Session+Dono"),
        ("POST", "/editar/<id>",              "Atualiza demanda (titulo, descricao, prioridade, etc.)", "Session+Dono"),
        ("POST", "/concluir/<id>",            "Move status para Concluida, preenche data_conclusao",   "Session"),
        ("POST", "/reabrir/<id>",             "Move status de Concluida para Aberta",                  "Session"),
        ("POST", "/andamento/<id>",           "Move status para Em andamento",                         "Session"),
        ("POST", "/cancelar/<id>",            "Move status para Cancelada",                            "Session"),
        ("POST", "/deletar/<id>",             "Remove demanda e registros em cascata",                 "Session+Dono"),
        ("GET",  "/buscar",                   "Busca full-text em titulo e descricao",                  "Session"),
        ("GET",  "/detalhes/<id>",            "Detalhe da demanda + historico de status + comentarios","Session"),
        ("POST", "/adicionar_comentario/<id>","Adiciona comentario a uma demanda",                     "Session"),
        ("GET",  "/usuarios",                 "Lista usuarios com estatisticas de demandas",           "Session"),
        ("GET",  "/api/keys",                 "Exibe pagina de gestao de API Keys",                    "Session"),
        ("POST", "/api/keys",                 "Cria nova chave ou revoga existente",                   "Session"),
    ]))
    story.append(sp(10))

    story.append(p("Dashboard — Endpoints AJAX Internos", "H2"))
    story.append(sp(4))
    story.append(routes_table([
        ("GET",  "/",                              "Redireciona para /dashboard",                      "Session"),
        ("GET",  "/dashboard",                     "Renderiza pagina do dashboard gerencial",          "Session"),
        ("GET",  "/api/dashboard/kpis",            "Retorna KPIs em JSON (total, aberta, atrasada...)", "Session"),
        ("GET",  "/api/dashboard/charts",          "Dados para os 3 graficos Chart.js",               "Session"),
        ("GET",  "/api/dashboard/data",            "Dataset completo com filtros (usado pelo JS)",     "Session"),
        ("GET",  "/api/dashboard/critical-overdue","Lista demandas criticas e atrasadas",              "Session"),
        ("GET",  "/api/dashboard/export",          "Exporta relatorio (CSV/XLSX/PDF) com filtros",    "Session"),
        ("GET",  "/api/dashboard/critical-overdue/export","Exporta tabela de criticas (CSV/XLSX/PDF)", "Session"),
        ("GET",  "/api/alerts/count",              "Contagem de alertas para o badge do navbar",      "Session"),
    ]))
    story.append(sp(10))

    story.append(p("API REST Externa v1 — Endpoints com API Key", "H2"))
    story.append(sp(4))
    story.append(routes_table([
        ("GET",   "/api/v1/demandas",                  "Lista demandas (paginacao e filtros)",          "API Key"),
        ("POST",  "/api/v1/demandas",                  "Cria nova demanda via JSON",                   "API Key"),
        ("GET",   "/api/v1/demandas/<id>",             "Retorna demanda especifica pelo ID",            "API Key"),
        ("PATCH", "/api/v1/demandas/<id>/status",      "Atualiza status com registro no historico",    "API Key"),
        ("GET",   "/api/v1/demandas/<id>/comentarios", "Lista comentarios da demanda",                  "API Key"),
        ("POST",  "/api/v1/demandas/<id>/comentarios", "Adiciona comentario a demanda",                 "API Key"),
        ("GET",   "/api/v1/usuarios",                  "Lista usuarios ativos (id, username, nome)",    "API Key"),
        ("GET",   "/apidocs",                          "Interface Swagger UI (documentacao interativa)","Publica"),
        ("GET",   "/apispec.json",                     "Spec OpenAPI 2.0 em JSON",                     "Publica"),
    ]))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S13 — ESCALABILIDADE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(13, "Escalabilidade e Manutencao Futura",
        "Como o sistema pode crescer e o que precisaria mudar"))
    story.append(sp(12))

    story.append(p(
        "O SGDI foi projetado com limites conscientes e com caminhos claros de evolucao. "
        "A escolha de um monolito com camadas bem separadas significa que cada componente "
        "pode ser substituido independentemente quando o crescimento exigir."
    ))
    story.append(sp(8))

    story.append(p("Limites Atuais e Pontos de Escala", "H2"))
    story.append(sp(4))
    story.append(kv_table([
        ("Usuarios simultaneos",
         "SQLite suporta multiplos leitores concorrentes com WAL mode. Escritas sao serializadas. "
         "Estimativa: ate ~200 usuarios simultaneos antes de degradacao perceptivel."),
        ("Volume de dados",
         "SQLite e estavel ate ~terabytes. Para o SGDI, 100.000 demandas representam "
         "~50MB — margem confortavel para anos de operacao."),
        ("Sessoes concorrentes",
         "Sessoes Flask sao armazenadas em cookies — nao ha estado server-side por sessao. "
         "O servidor e stateless para sessoes, o que facilita scaling horizontal com load balancer."),
        ("Exportacoes pesadas",
         "Relatorios com 10.000+ registros podem adicionar latencia. Mitgacao futura: "
         "Celery worker + Redis para gerar em background e notificar quando pronto."),
    ], header=("Dimensao", "Situacao Atual e Limite")))
    story.append(sp(10))

    story.append(p("Roteiro de Evolucao Tecnica", "H2"))
    story.append(sp(4))
    evolution = [
        ("Fase 1 — Producao imediata",
         ["Gunicorn como servidor WSGI (substituir Flask dev server)",
          "Nginx como proxy reverso com cache de estaticos e TLS",
          "SECRET_KEY via variavel de ambiente (ja suportado)",
          "Backup automatico do demandas.db (cron diario)"]),
        ("Fase 2 — Crescimento (50-500 usuarios)",
         ["Ativar SQLite WAL mode (PRAGMA journal_mode=WAL) para maior concorrencia",
          "Adicionar indices nas colunas mais filtradas (status, prioridade, data_criacao)",
          "Implementar paginacao na lista de demandas (cursor-based)",
          "Cache de KPIs do dashboard com TTL de 30s usando Flask-Caching + Redis"]),
        ("Fase 3 — Escala maior (500+ usuarios ou multi-regiao)",
         ["Migrar SQLite para PostgreSQL — apenas database.py precisa ser reescrito",
          "Containerizar com Docker + docker-compose",
          "Separar API REST em servico independente se necessario",
          "Implementar webhooks (callback HTTP) para notificar sistemas externos de mudancas de status"]),
    ]
    for phase, items_e in evolution:
        story.append(p(phase, "H3"))
        for item_e in items_e:
            story.append(bul(item_e))
        story.append(sp(6))

    story.append(sp(4))
    story.append(p("Manutencao do Codigo", "H2"))
    story.append(sp(4))
    maint = [
        "<b>Adicionar novo status</b>: adicionar a TODOS_STATUS em database.py — automaticamente propagado para todas as validacoes e filtros",
        "<b>Adicionar nova coluna</b>: adicionar ALTER TABLE em _migrate_demands() com verificacao via PRAGMA — executa automaticamente no proximo startup",
        "<b>Novo endpoint API</b>: criar funcao com @app.route e @api_key_required + docstring YAML para Swagger — aparece automaticamente em /apidocs",
        "<b>Novo template</b>: estender base.html com {% extends 'base.html' %} — navbar, footer, flash messages e JS de alertas incluidos automaticamente",
        "<b>Novo usuario</b>: adicionar em USUARIOS_FIXOS em database.py — seed executado no proximo startup se username nao existir",
    ]
    for m in maint:
        story.append(bul(m))
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S14 — MELHORIAS FUTURAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(14, "Possiveis Melhorias Futuras",
        "Evolucoes identificadas durante o desenvolvimento"))
    story.append(sp(12))

    improvements = [
        ("Autenticacao LDAP/SAML",
         "Integrar com Active Directory ou SSO corporativo (SAML 2.0 / OAuth2). "
         "Eliminaria o gerenciamento de senhas locais e centralizaria o controle de acesso "
         "com o diretorio existente na organizacao."),
        ("Notificacoes por e-mail / Webhook",
         "Enviar e-mail automatico quando uma demanda critica e criada, quando o SLA esta "
         "proximo do vencimento ou quando o status muda. Alternativamente, webhooks HTTP "
         "para sistemas externos configurados por demanda."),
        ("Dashboard em tempo real (WebSocket)",
         "Substituir o polling de 60s do badge de alertas por WebSocket via Flask-SocketIO, "
         "eliminando latencia e reducando carga de requisicoes periodicas."),
        ("SLA configuravel por prioridade",
         "Hoje o SLA e informado manualmente (data_prevista). Uma melhoria seria configurar "
         "SLAs padrao por prioridade (ex: Critica = 4h, Alta = 24h, Media = 72h) aplicados "
         "automaticamente na criacao."),
        ("Perfis de usuario (RBAC)",
         "Implementar Role-Based Access Control com perfis: Solicitante (apenas abre), "
         "Executante (move status), Gestor (dashboard completo, exportacoes), Admin (tudo). "
         "Armazenado em uma nova coluna perfil na tabela usuarios."),
        ("Busca full-text avancada",
         "A busca atual usa LIKE %termo% — nao usa indice, custo O(n). SQLite tem extensao "
         "FTS5 (Full-Text Search) que indexa texto e permite busca booleana em millisegundos "
         "mesmo com 100k+ registros."),
        ("Anexos em demandas",
         "Permitir upload de arquivos (screenshots, documentos) vinculados a demandas, "
         "armazenados em disco com referencia no banco. Necessita validacao de tipo MIME "
         "e limite de tamanho."),
        ("Auditoria expandida",
         "Registrar nao apenas mudancas de status mas tambem edicoes de campos (quem, o que, quando). "
         "Implementavel com uma tabela auditoria_campos e um hook no endpoint /editar."),
        ("Testes automatizados",
         "Implementar suite de testes com pytest + Flask test client para todas as rotas, "
         "e testes de integracao para os endpoints da API REST verificando contratos JSON."),
    ]

    for i, (title_imp, body_imp) in enumerate(improvements, 1):
        imp_num_s = ParagraphStyle(f"impn{i}", fontSize=10, fontName="Helvetica-Bold",
                                    textColor=C_ACCENT, alignment=TA_CENTER)
        imp_title_s = ParagraphStyle(f"impt{i}", fontSize=10, fontName="Helvetica-Bold",
                                      textColor=C_DARK, leading=13)
        imp_body_s  = ParagraphStyle(f"impb{i}", fontSize=9, fontName="Helvetica",
                                      textColor=C_MUTED, leading=13)
        t = Table([[
            Table([[Paragraph(f"{i:02d}", imp_num_s)]],
                  colWidths=[1.0*cm],
                  style=TableStyle([
                      ("BACKGROUND",    (0,0), (-1,-1), C_BG),
                      ("BOX",           (0,0), (-1,-1), 1, C_ACCENT),
                      ("TOPPADDING",    (0,0), (-1,-1), 5),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                  ])),
            [Paragraph(title_imp, imp_title_s), Paragraph(body_imp, imp_body_s)],
        ]], colWidths=[1.4*cm, CONTENT_W - 1.4*cm])
        t.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(t)
        story.append(sp(2))

    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # S15 — CONCLUSÃO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_block(15, "Conclusao Tecnica do Projeto",
        "Avaliacao do que foi construido e o que ele representa tecnicamente"))
    story.append(sp(12))

    story.append(p(
        "O SGDI v2.0 e um sistema web completo, funcional e seguro para gestao de demandas "
        "internas. Mais do que uma aplicacao funcional, ele representa um conjunto de "
        "<b>decisoes arquiteturais conscientes e documentadas</b>, onde cada escolha tecnologica "
        "teve um motivo especifico e um trade-off avaliado."
    ))
    story.append(sp(8))

    story.append(p(
        "A escolha do <b>monolito em camadas</b> sobre microsservicos, do <b>SQLite</b> "
        "sobre bancos cliente-servidor, do <b>SSR com Jinja2</b> sobre SPA com React, e do "
        "<b>CSS customizado</b> sobre Bootstrap reflete uma filosofia de <b>complexidade "
        "minima necessaria</b>: o sistema deve ser tao simples quanto o problema permite, "
        "e complexo apenas onde o problema exige."
    ))
    story.append(sp(8))

    story.append(p(
        "A adicao da <b>API REST com Swagger</b> e <b>API Keys</b> transforma o SGDI de um "
        "sistema interno isolado em uma plataforma integravel. ERPs, scripts de automacao e "
        "aplicacoes mobile podem criar, consultar e atualizar demandas programaticamente, "
        "mantendo o mesmo banco de dados e as mesmas regras de negocio da interface web."
    ))
    story.append(sp(8))

    story.append(p(
        "A camada de <b>seguranca</b> — CSRF em todos os formularios, PBKDF2 para senhas, "
        "queries parametrizadas, auto-escape XSS e autenticacao stateless por API Key — "
        "endeca as categorias de maior risco do OWASP Top 10 sem depender de "
        "seguranca por obscuridade ou configuracoes externas."
    ))
    story.append(sp(10))

    # Tabela de metricas finais
    story.append(p("Resumo Tecnico Final", "H2"))
    story.append(sp(6))
    story.append(kv_table([
        ("Linguagem e Runtime",       "Python 3.12.2 — linguagem principal, unica"),
        ("Framework",                  "Flask 3.0.3 — microframework WSGI"),
        ("Banco de dados",             "SQLite 3 — embarcado, zero-config, arquivo unico"),
        ("Autenticacao web",           "Session Flask + CSRF token (PBKDF2-SHA256 para senhas)"),
        ("Autenticacao API",           "X-API-Key header — 256 bits de entropia (secrets.token_urlsafe)"),
        ("Frontend",                   "Jinja2 SSR + CSS customizado + JavaScript vanilla + Chart.js 4"),
        ("Documentacao API",           "Swagger UI via flasgger — OpenAPI 2.0"),
        ("Exportacao de dados",        "CSV (utf-8-sig), Excel (.xlsx via openpyxl), PDF (via reportlab)"),
        ("Total de rotas",             "31 endpoints (17 web + 7 dashboard + 7 API REST)"),
        ("Tabelas no banco",           "5 (usuarios, demandas, historico_status, comentarios, api_keys)"),
        ("Templates Jinja2",           "10 (heranca de base.html)"),
        ("Cobertura de seguranca",     "CSRF, XSS, SQLi, Auth Failures, Cryptographic (OWASP Top 10)"),
        ("Padrao de codigo",           "MVC adaptado, decorators de auth, SQL parametrizado, constants as guard"),
        ("Capacidade estimada",        "Ate ~200 usuarios simultaneos sem alteracao de infraestrutura"),
        ("Caminho de migracao",        "SQLite -> PostgreSQL requer apenas reescrita de database.py"),
        ("Linhas de codigo (aprox.)",  "app.py: ~2080 | database.py: ~280 | style.css: ~800 | ui.js: ~350"),
    ], header=("Dimensao", "Valor / Descricao")))
    story.append(sp(12))

    story.append(info_box(
        "<b>Consideracao Final:</b> O SGDI demonstra que e possivel construir um sistema "
        "web completo, seguro, com API REST documentada e dashboard gerencial em tempo real, "
        "usando exclusivamente tecnologias de codigo aberto, sem dependencias de nuvem e "
        "sem ferramentas de build — resultando em um artefato de zero-config deployment, "
        "facil auditoria e manutencao por qualquer desenvolvedor Python.",
        color=C_SUCCESS,
        bg=colors.HexColor("#f0fdf4")
    ))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=cover_page,
        onLaterPages=page_header_footer,
    )
    print(f"[OK] Documento gerado: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Gerador de Documento Tecnico SGDI ===\n")
    build_pdf("documento_tecnico_sgdi.pdf")
    print("\nConcluido. Arquivo: documento_tecnico_sgdi.pdf")
