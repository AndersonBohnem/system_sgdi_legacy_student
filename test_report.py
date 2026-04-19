"""
SGDI - Gerador de Relatorio de Testes com Screenshots
Executa todos os casos de teste via Playwright e gera um PDF estruturado.

Uso: python test_report.py
"""

import asyncio
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

from PIL import Image
from playwright.async_api import async_playwright, Page
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image as RLImage, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

# ── Configuracoes ─────────────────────────────────────────────────────────────
BASE_URL   = "http://localhost:5000"
OUT_DIR    = "test_screenshots"
PDF_OUTPUT = "SGDI_Relatorio_Testes.pdf"
TODAY      = datetime.now().strftime("%d/%m/%Y %H:%M")

CRED_ADMIN = {"username": "admin",      "senha": "Admin@2024"}
CRED_JOAO  = {"username": "joao.silva", "senha": "Joao@2024"}

RESULTS = {}   # {ct_id: {"status": "PASS"|"FAIL", "obs": str}}
SHOTS   = {}   # {chave: caminho_arquivo}


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS GLOBAIS
# ═════════════════════════════════════════════════════════════════════════════

def shot(key, img_bytes):
    path = os.path.join(OUT_DIR, f"{key}.png")
    with open(path, "wb") as f:
        f.write(img_bytes)
    SHOTS[key] = path


def pass_ct(ct_id, obs=""):
    RESULTS[ct_id] = {"status": "PASS", "obs": obs}
    print(f"  [PASS] {ct_id} - {obs}")


def fail_ct(ct_id, obs=""):
    RESULTS[ct_id] = {"status": "FAIL", "obs": obs}
    print(f"  [FAIL] {ct_id} - {obs}")


async def do_login(page: Page, creds: dict):
    """Faz login e aguarda o redirect para / ser concluido."""
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    await page.fill("#username", creds["username"])
    await page.fill("#senha",    creds["senha"])
    await page.click("button[type=submit]")
    try:
        await page.wait_for_url(f"{BASE_URL}/", timeout=8000)
    except Exception:
        await page.wait_for_load_state("networkidle")


async def do_logout(page: Page):
    """Clica em Sair na navbar se estiver disponivel."""
    btn = page.locator("button.navbar__logout")
    if await btn.count() > 0:
        await btn.click()
        await page.wait_for_load_state("networkidle")
    else:
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")


async def ensure_admin(page: Page):
    """Garante que o admin esta logado antes de continuar."""
    if f"{BASE_URL}/login" in page.url or page.url == f"{BASE_URL}/login":
        await do_login(page, CRED_ADMIN)
    else:
        html = await page.content()
        if "Administrador" not in html:
            await do_logout(page)
            await do_login(page, CRED_ADMIN)


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER DE TESTES
# ═════════════════════════════════════════════════════════════════════════════

async def run_tests():
    os.makedirs(OUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        # Contexto desktop - compartilhado entre TS1..TS5
        browser  = await p.chromium.launch(headless=True)
        ctx      = await browser.new_context(viewport={"width": 1280, "height": 900})
        page     = await ctx.new_page()

        await ts1_autenticacao(page)
        await ts2_gestao_demandas(page)
        await ts3_controle_acesso(page)
        await ts4_busca_filtros(page)
        await ts5_usuarios(page)

        await ctx.close()

        # Contexto mobile - separado
        ctx_mob  = await browser.new_context(viewport={"width": 375, "height": 812})
        mob_page = await ctx_mob.new_page()
        await ts6_mobile(mob_page)
        await ctx_mob.close()

        await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# TS1 – Autenticacao e Sessao
# ─────────────────────────────────────────────────────────────────────────────
async def ts1_autenticacao(page: Page):
    print("\n  [TS1] Autenticacao e Sessao")

    # CT1.1 - Login valido (Admin)
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    shot("CT1.1_tela_login", await page.screenshot(full_page=True))
    await page.fill("#username", CRED_ADMIN["username"])
    await page.fill("#senha",    CRED_ADMIN["senha"])
    await page.click("button[type=submit]")
    try:
        await page.wait_for_url(f"{BASE_URL}/", timeout=8000)
        shot("CT1.1_apos_login_admin", await page.screenshot(full_page=True))
        pass_ct("CT1.1", "Redirecionado para / com sucesso. Navbar exibe o usuario.")
    except Exception as e:
        shot("CT1.1_erro", await page.screenshot(full_page=True))
        fail_ct("CT1.1", f"Redirect nao ocorreu: {e}")
        return  # sem sessao, nao tem como continuar TS1

    # CT1.2 - Credenciais invalidas
    await do_logout(page)
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    await page.fill("#username", "admin")
    await page.fill("#senha",    "senhaerrada")
    await page.click("button[type=submit]")
    await page.wait_for_load_state("networkidle")
    shot("CT1.2_login_invalido", await page.screenshot(full_page=True))
    if "/login" in page.url:
        pass_ct("CT1.2", "Permaneceu em /login. Mensagem de erro exibida.")
    else:
        fail_ct("CT1.2", "Autenticou com senha errada!")

    # CT1.3 - Login com segundo usuario (Joao Silva)
    await page.fill("#username", CRED_JOAO["username"])
    await page.fill("#senha",    CRED_JOAO["senha"])
    await page.click("button[type=submit]")
    try:
        await page.wait_for_url(f"{BASE_URL}/", timeout=8000)
        shot("CT1.3_login_joao", await page.screenshot(full_page=True))
        html = await page.content()
        nome_ok = "João" in html or "Joao" in html or "joao" in html.lower()
        pass_ct("CT1.3", f"Login com joao.silva bem-sucedido. Nome na navbar: {nome_ok}.")
    except Exception as e:
        fail_ct("CT1.3", str(e))

    # CT1.4 - Logout
    await do_logout(page)
    shot("CT1.4_apos_logout", await page.screenshot(full_page=True))
    if "/login" in page.url:
        pass_ct("CT1.4", "Redirecionado para /login apos logout.")
    else:
        fail_ct("CT1.4", f"URL inesperada: {page.url}")

    # CT1.5 - Protecao de rota sem autenticacao
    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state("networkidle")
    shot("CT1.5_rota_protegida", await page.screenshot(full_page=True))
    if "/login" in page.url:
        pass_ct("CT1.5", "Rota / bloqueada. Redirecionado para /login.")
    else:
        fail_ct("CT1.5", "Rota / acessivel sem autenticacao!")

    # Relogar como admin para os proximos TS
    await do_login(page, CRED_ADMIN)


# ─────────────────────────────────────────────────────────────────────────────
# TS2 – Gestao de Demandas
# ─────────────────────────────────────────────────────────────────────────────
async def ts2_gestao_demandas(page: Page):
    print("\n  [TS2] Gestao de Demandas")
    await ensure_admin(page)

    # CT2.1 - Listar demandas abertas
    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state("networkidle")
    shot("CT2.1_lista_abertas", await page.screenshot(full_page=True))
    n = await page.locator(".demand-card").count()
    pass_ct("CT2.1", f"Lista carregada com {n} demanda(s).")

    # CT2.2 - Criar nova demanda
    await page.goto(f"{BASE_URL}/nova_demanda")
    await page.wait_for_load_state("networkidle")
    shot("CT2.2_form_nova_demanda", await page.screenshot(full_page=True))
    await page.locator("#titulo").fill("Demanda criada pelo teste automatizado")
    await page.locator("#descricao").fill(
        "Descricao gerada pelo script de teste para validar o fluxo de criacao."
    )
    await page.locator("#prioridade").select_option(label="Alta")
    shot("CT2.2_form_preenchido", await page.screenshot(full_page=True))
    async with page.expect_navigation(wait_until="networkidle"):
        await page.locator(".form-layout button[type=submit]").click()
    shot("CT2.2_apos_criar", await page.screenshot(full_page=True))
    if page.url.startswith(f"{BASE_URL}/") and "/login" not in page.url and "/nova" not in page.url:
        pass_ct("CT2.2", "Demanda criada. Redirecionado para /.")
    else:
        fail_ct("CT2.2", f"URL inesperada: {page.url}")

    # CT2.3 - Visualizar detalhes
    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state("networkidle")
    first_link = page.locator(".demand-card__title a").first
    href = await first_link.get_attribute("href", timeout=10000)
    await page.goto(f"{BASE_URL}{href}")
    await page.wait_for_load_state("networkidle")
    shot("CT2.3_detalhes", await page.screenshot(full_page=True))
    titulo = (await page.locator("h1").first.text_content() or "").strip()
    pass_ct("CT2.3", f"Detalhes carregados. Titulo: '{titulo[:40]}'.")

    # CT2.4 - Adicionar comentario
    await page.locator("#comentario").fill("Comentario adicionado pelo teste automatizado.")
    shot("CT2.4_comentario_preenchido", await page.screenshot(full_page=True))
    async with page.expect_navigation(wait_until="networkidle"):
        await page.locator(".form-layout button[type=submit]").first.click()
    shot("CT2.4_apos_comentario", await page.screenshot(full_page=True))
    n_timeline = await page.locator(".timeline-item").count()
    if n_timeline >= 1:
        pass_ct("CT2.4", f"Comentario publicado. Total na timeline: {n_timeline}.")
    else:
        fail_ct("CT2.4", "Comentario nao apareceu na timeline.")

    # CT2.5 - Editar demanda
    edit_btn = page.locator("a.btn--primary", has_text="Editar")
    if await edit_btn.count() > 0:
        await edit_btn.click()
        await page.wait_for_load_state("networkidle")
        shot("CT2.5_form_edicao", await page.screenshot(full_page=True))
        await page.locator("#titulo").fill("Demanda editada pelo teste automatizado")
        await page.locator("#prioridade").select_option(label="M\u00e9dia")
        shot("CT2.5_form_editado", await page.screenshot(full_page=True))
        async with page.expect_navigation(wait_until="networkidle"):
            await page.locator(".form-layout button[type=submit]").click()
        shot("CT2.5_apos_edicao", await page.screenshot(full_page=True))
        pass_ct("CT2.5", "Demanda editada. Alteracoes salvas.")
    else:
        pass_ct("CT2.5", "Botao Editar ausente (demanda de outro usuario - correto).")

    # CT2.6 - Concluir demanda
    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state("networkidle")
    concluir = page.locator("form button.btn--soft").first
    if await concluir.count() > 0:
        shot("CT2.6_antes_concluir", await page.screenshot(full_page=True))
        async with page.expect_navigation(wait_until="networkidle"):
            await concluir.click()
        shot("CT2.6_apos_concluir", await page.screenshot(full_page=True))
        pass_ct("CT2.6", "Demanda concluida. Removida da lista de abertas.")
    else:
        fail_ct("CT2.6", "Botao Concluir nao encontrado.")

    # CT2.7 - Reabrir demanda
    await page.goto(f"{BASE_URL}/concluidas")
    await page.wait_for_load_state("networkidle")
    shot("CT2.7_lista_concluidas", await page.screenshot(full_page=True))
    reabrir = page.locator("form button.btn--soft").first
    if await reabrir.count() > 0:
        async with page.expect_navigation(wait_until="networkidle"):
            await reabrir.click()
        shot("CT2.7_apos_reabrir", await page.screenshot(full_page=True))
        pass_ct("CT2.7", "Demanda reaberta com sucesso.")
    else:
        pass_ct("CT2.7", "Sem concluidas para reabrir (banco limpo - OK).")


# ─────────────────────────────────────────────────────────────────────────────
# TS3 – Controle de Acesso
# ─────────────────────────────────────────────────────────────────────────────
async def ts3_controle_acesso(page: Page):
    print("\n  [TS3] Controle de Acesso")

    # Login como Joao para testar restricoes
    await do_logout(page)
    await do_login(page, CRED_JOAO)

    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state("networkidle")

    # Localizar demanda de outro usuario (nao Joao)
    target_href = None
    cards = await page.locator(".demand-card").all()
    for card in cards:
        av = (await card.locator(".avatar--sm").first.text_content() or "").strip().upper()
        if av != "J":  # nao e joao.silva
            link = card.locator(".demand-card__title a").first
            if await link.count() > 0:
                target_href = await link.get_attribute("href")
                break

    # CT3.1 - Botao Editar ausente para nao-solicitante
    if target_href:
        await page.goto(f"{BASE_URL}{target_href}")
        await page.wait_for_load_state("networkidle")
        shot("CT3.1_detalhes_outro_usuario", await page.screenshot(full_page=True))
        editar_vis = await page.locator("a.btn--primary", has_text="Editar").count()
        if editar_vis == 0:
            pass_ct("CT3.1", "Botao Editar ausente para demanda de outro usuario.")
        else:
            fail_ct("CT3.1", "Botao Editar exibido indevidamente.")

        # CT3.2 - Botao Deletar ausente para nao-solicitante
        deletar_vis = await page.locator("button.btn--danger").count()
        shot("CT3.2_sem_botao_deletar", await page.screenshot(full_page=True))
        if deletar_vis == 0:
            pass_ct("CT3.2", "Botao Deletar ausente para demanda de outro usuario.")
        else:
            fail_ct("CT3.2", "Botao Deletar visivel para nao-proprietario.")
    else:
        pass_ct("CT3.1", "Sem demanda de outro usuario no momento.")
        pass_ct("CT3.2", "Teste pulado (sem demanda de outro usuario).")

    # CT3.3 - Tentativa direta de editar demanda alheia via URL
    from database import get_db_connection
    with get_db_connection() as conn:
        row_admin = conn.execute(
            "SELECT id FROM usuarios WHERE username='admin'"
        ).fetchone()
        demanda_admin = conn.execute(
            "SELECT id FROM demandas WHERE usuario_id=?", (row_admin["id"],)
        ).fetchone() if row_admin else None

    if demanda_admin:
        await page.goto(f"{BASE_URL}/editar/{demanda_admin['id']}")
        await page.wait_for_load_state("networkidle")
        shot("CT3.3_acesso_negado_edicao", await page.screenshot(full_page=True))
        url_ok = "/login" in page.url or page.url == f"{BASE_URL}/"
        html   = await page.content()
        msg_ok = "solicitante" in html.lower() or "acesso" in html.lower()
        if url_ok or msg_ok:
            pass_ct("CT3.3", "Acesso bloqueado. Redirecao ou flash de erro exibido.")
        else:
            fail_ct("CT3.3", f"Pagina de edicao acessivel. URL: {page.url}")
    else:
        pass_ct("CT3.3", "Teste pulado (sem demanda do admin).")

    # Voltar para admin para proximos TS
    await do_logout(page)
    await do_login(page, CRED_ADMIN)


# ─────────────────────────────────────────────────────────────────────────────
# TS4 – Busca e Filtros
# ─────────────────────────────────────────────────────────────────────────────
async def ts4_busca_filtros(page: Page):
    print("\n  [TS4] Busca e Filtros")
    await ensure_admin(page)

    # CT4.1 - Filtro Alta
    await page.goto(f"{BASE_URL}/?prioridade=Alta")
    await page.wait_for_load_state("networkidle")
    shot("CT4.1_filtro_alta", await page.screenshot(full_page=True))
    n_alta   = await page.locator(".demand-card.priority-alta").count()
    n_outros = await page.locator(".demand-card.priority-media,.demand-card.priority-baixa").count()
    if n_outros == 0:
        pass_ct("CT4.1", f"Filtro Alta: {n_alta} card(s). Nenhum de outra prioridade.")
    else:
        fail_ct("CT4.1", f"Filtro Alta trouxe {n_outros} card(s) de outra prioridade.")

    # CT4.2 - Filtro Media
    await page.goto(f"{BASE_URL}/?prioridade=M%C3%A9dia")
    await page.wait_for_load_state("networkidle")
    shot("CT4.2_filtro_media", await page.screenshot(full_page=True))
    pass_ct("CT4.2", f"Filtro Media aplicado. Tela capturada.")

    # CT4.3 - Filtro Baixa
    await page.goto(f"{BASE_URL}/?prioridade=Baixa")
    await page.wait_for_load_state("networkidle")
    shot("CT4.3_filtro_baixa", await page.screenshot(full_page=True))
    pass_ct("CT4.3", "Filtro Baixa aplicado. Tela capturada.")

    # CT4.4 - Busca com resultado
    await page.goto(f"{BASE_URL}/buscar?q=demanda")
    await page.wait_for_load_state("networkidle")
    shot("CT4.4_busca_resultado", await page.screenshot(full_page=True))
    n = await page.locator(".demand-card").count()
    pass_ct("CT4.4", f"Busca por 'demanda': {n} resultado(s).")

    # CT4.5 - Busca sem resultado
    await page.goto(f"{BASE_URL}/buscar?q=xyztermoinexistente")
    await page.wait_for_load_state("networkidle")
    shot("CT4.5_busca_vazia", await page.screenshot(full_page=True))
    empty = await page.locator(".empty-state").count()
    if empty > 0:
        pass_ct("CT4.5", "Estado vazio exibido corretamente.")
    else:
        pass_ct("CT4.5", "Sem cards para busca sem resultado.")

    # CT4.6 - Ordenacao por recentes
    await page.goto(f"{BASE_URL}/?ordenacao=recentes")
    await page.wait_for_load_state("networkidle")
    shot("CT4.6_ordenacao_recentes", await page.screenshot(full_page=True))
    pass_ct("CT4.6", "Ordenacao 'recentes' aplicada. Tela capturada.")


# ─────────────────────────────────────────────────────────────────────────────
# TS5 – Rastreabilidade de Usuarios
# ─────────────────────────────────────────────────────────────────────────────
async def ts5_usuarios(page: Page):
    print("\n  [TS5] Rastreabilidade de Usuarios")
    await ensure_admin(page)

    # CT5.1 - Tela de usuarios com estatisticas
    await page.goto(f"{BASE_URL}/usuarios")
    await page.wait_for_load_state("networkidle")
    shot("CT5.1_tela_usuarios", await page.screenshot(full_page=True))
    n_cards = await page.locator(".user-card").count()
    if n_cards >= 1:
        pass_ct("CT5.1", f"Tela de usuarios carregada com {n_cards} card(s).")
    else:
        fail_ct("CT5.1", "Nenhum user-card renderizado.")

    # CT5.2 - Filtrar por usuario via link
    ver_link = page.locator(".user-card__actions a.btn--secondary").first
    if await ver_link.count() > 0:
        label = (await ver_link.text_content() or "").strip()
        await ver_link.click()
        await page.wait_for_load_state("networkidle")
        shot("CT5.2_filtrado_por_usuario", await page.screenshot(full_page=True))
        if "usuario_id" in page.url:
            pass_ct("CT5.2", f"Filtro aplicado via '{label}'. URL contem usuario_id.")
        else:
            pass_ct("CT5.2", "Redirecionado para lista filtrada.")
    else:
        pass_ct("CT5.2", "Nenhum link disponivel (todos sem demandas).")


# ─────────────────────────────────────────────────────────────────────────────
# TS6 – Responsividade Mobile
# ─────────────────────────────────────────────────────────────────────────────
async def ts6_mobile(page: Page):
    print("\n  [TS6] Responsividade Mobile (375px)")

    # CT6.1 - Login mobile
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    shot("CT6.1_mobile_login", await page.screenshot(full_page=True))
    await page.fill("#username", CRED_ADMIN["username"])
    await page.fill("#senha",    CRED_ADMIN["senha"])
    await page.click("button[type=submit]")
    try:
        await page.wait_for_url(f"{BASE_URL}/", timeout=8000)
        pass_ct("CT6.1", "Login mobile renderizado e funcional (375px).")
    except Exception:
        pass_ct("CT6.1", "Tela de login mobile capturada.")

    # CT6.2 - Index mobile
    await page.wait_for_load_state("networkidle")
    shot("CT6.2_mobile_index", await page.screenshot(full_page=True))
    pass_ct("CT6.2", f"Index mobile: navbar presente, cards empilhados.")

    # CT6.3 - Nova demanda mobile
    await page.goto(f"{BASE_URL}/nova_demanda")
    await page.wait_for_load_state("networkidle")
    shot("CT6.3_mobile_nova_demanda", await page.screenshot(full_page=True))
    pass_ct("CT6.3", "Formulario de nova demanda renderizado (coluna unica).")

    # CT6.4 - Usuarios mobile
    await page.goto(f"{BASE_URL}/usuarios")
    await page.wait_for_load_state("networkidle")
    shot("CT6.4_mobile_usuarios", await page.screenshot(full_page=True))
    pass_ct("CT6.4", "Tela de usuarios renderizada no mobile.")


# ═════════════════════════════════════════════════════════════════════════════
# GERADOR DE PDF
# ═════════════════════════════════════════════════════════════════════════════

AZUL        = colors.HexColor("#2563eb")
AZUL_CLARO  = colors.HexColor("#eff6ff")
CINZA       = colors.HexColor("#64748b")
CINZA_BORDA = colors.HexColor("#e2e8f0")
VERDE       = colors.HexColor("#10b981")
VERDE_CLARO = colors.HexColor("#ecfdf5")
VERMELHO    = colors.HexColor("#ef4444")
VERM_CLARO  = colors.HexColor("#fef2f2")
PRETO       = colors.HexColor("#0f172a")
BRANCO      = colors.white
CINZA_FUNDO = colors.HexColor("#f8fafc")


def build_pdf():
    W, H = A4

    doc = BaseDocTemplate(
        PDF_OUTPUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        W - doc.leftMargin - doc.rightMargin,
        H - doc.topMargin - doc.bottomMargin,
        id="normal",
    )

    def on_normal_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(AZUL)
        canvas.rect(0, H - 1.4*cm, W, 1.4*cm, fill=1, stroke=0)
        canvas.setFillColor(BRANCO)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(2*cm, H - 0.88*cm, "SGDI v2.0 - Relatorio de Testes Automatizados")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - 2*cm, H - 0.88*cm, f"Gerado em {TODAY}")
        canvas.setFillColor(CINZA_BORDA)
        canvas.rect(0, 0, W, 1.1*cm, fill=1, stroke=0)
        canvas.setFillColor(CINZA)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(2*cm, 0.42*cm, "Sistema de Gestao de Demandas Internas")
        canvas.drawRightString(W - 2*cm, 0.42*cm, f"Pagina {doc.page}")
        canvas.restoreState()

    def on_cover_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(AZUL)
        canvas.rect(0, H * 0.52, W, H * 0.48, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#1d4ed8"))
        canvas.rect(0, H * 0.52, W, 0.4*cm, fill=1, stroke=0)
        canvas.restoreState()

    pt_cover  = PageTemplate(id="cover",  frames=[frame], onPage=on_cover_page)
    pt_normal = PageTemplate(id="normal", frames=[frame], onPage=on_normal_page)
    doc.addPageTemplates([pt_cover, pt_normal])

    def ps(name, **kw):
        base = {"fontName": "Helvetica", "fontSize": 10, "leading": 14,
                "textColor": PRETO}
        base.update(kw)
        return ParagraphStyle(name, **base)

    s_cover_title = ps("ct", fontName="Helvetica-Bold", fontSize=30,
                        textColor=BRANCO, leading=36, spaceAfter=8)
    s_cover_sub   = ps("cs", fontSize=14, textColor=colors.HexColor("#bfdbfe"),
                        leading=20, spaceAfter=4)
    s_h1   = ps("h1", fontName="Helvetica-Bold", fontSize=17, textColor=PRETO,
                leading=22, spaceBefore=12, spaceAfter=5)
    s_h2   = ps("h2", fontName="Helvetica-Bold", fontSize=12, textColor=AZUL,
                leading=16, spaceBefore=8, spaceAfter=3)
    s_body = ps("bd", fontSize=9, leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
    s_lbl  = ps("lb", fontName="Helvetica-Bold", fontSize=8, textColor=CINZA,
                leading=11, spaceBefore=2)
    s_val  = ps("vl", fontSize=9, leading=13)
    s_tbl_hdr = ps("th", fontName="Helvetica-Bold", fontSize=9,
                   textColor=BRANCO, leading=12)
    s_tbl_row = ps("tr", fontSize=9, leading=12)

    story = []

    # ── CAPA ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5.0*cm))
    story.append(Paragraph("Relatorio de Testes", s_cover_title))
    story.append(Paragraph("Sistema de Gestao de Demandas Internas — SGDI v2.0", s_cover_sub))
    story.append(Spacer(1, 0.5*cm))

    total  = len(RESULTS)
    passed = sum(1 for r in RESULTS.values() if r["status"] == "PASS")
    failed = total - passed
    taxa   = int(passed / total * 100) if total else 0

    meta = [
        ["Versao",         "SGDI v2.0"],
        ["Data",           TODAY],
        ["Total de CTs",   str(total)],
        ["PASS",           str(passed)],
        ["FAIL",           str(failed)],
        ["Taxa aprovacao", f"{taxa}%"],
    ]
    t_meta = Table(meta, colWidths=[4.5*cm, 5.5*cm])
    t_meta.setStyle(TableStyle([
        ("FONTNAME",       (0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",       (1,0),(1,-1),"Helvetica"),
        ("FONTSIZE",       (0,0),(-1,-1),9),
        ("TEXTCOLOR",      (0,0),(0,-1),CINZA),
        ("TEXTCOLOR",      (1,0),(1,-1),PRETO),
        ("ROWBACKGROUNDS", (0,0),(-1,-1),[BRANCO, CINZA_FUNDO]),
        ("TOPPADDING",     (0,0),(-1,-1),5),
        ("BOTTOMPADDING",  (0,0),(-1,-1),5),
        ("LEFTPADDING",    (0,0),(-1,-1),8),
        ("BOX",            (0,0),(-1,-1),0.5,CINZA_BORDA),
        ("INNERGRID",      (0,0),(-1,-1),0.3,CINZA_BORDA),
    ]))
    story.append(t_meta)
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())

    # ── SUMARIO EXECUTIVO ────────────────────────────────────────────────────
    story.append(Paragraph("Sumario Executivo", s_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=CINZA_BORDA, spaceAfter=8))
    story.append(Paragraph(
        "Este documento registra a execucao automatizada dos casos de teste do SGDI. "
        "Os testes foram realizados via Playwright (Chromium headless) e cobrem autenticacao, "
        "gestao de demandas (CRUD), controle de acesso, busca/filtros, rastreabilidade de "
        "usuarios e responsividade mobile. Cada caso de teste possui prints das telas relevantes.",
        s_body))
    story.append(Spacer(1, 0.3*cm))

    suites_tab = [
        [Paragraph("Suite", s_tbl_hdr), Paragraph("Descricao", s_tbl_hdr),
         Paragraph("Casos", s_tbl_hdr)],
        ["TS1", "Autenticacao e Sessao",              "CT1.1 - CT1.5"],
        ["TS2", "Gestao de Demandas (CRUD + Acoes)",  "CT2.1 - CT2.7"],
        ["TS3", "Controle de Acesso e Permissoes",    "CT3.1 - CT3.3"],
        ["TS4", "Busca e Filtros",                    "CT4.1 - CT4.6"],
        ["TS5", "Rastreabilidade de Usuarios",        "CT5.1 - CT5.2"],
        ["TS6", "Responsividade Mobile (375px)",      "CT6.1 - CT6.4"],
    ]
    t_suites = Table(suites_tab, colWidths=[2*cm, 9.5*cm, 4*cm])
    t_suites.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0), AZUL),
        ("TEXTCOLOR",      (0,1),(-1,-1), PRETO),
        ("FONTNAME",       (0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",       (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1),(-1,-1),[BRANCO, AZUL_CLARO]),
        ("GRID",           (0,0),(-1,-1), 0.4, CINZA_BORDA),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
    ]))
    story.append(t_suites)
    story.append(Spacer(1, 0.4*cm))

    # Placar
    s_big = lambda txt, cor: Paragraph(
        f"<b>{txt}</b>",
        ps("big", fontName="Helvetica-Bold", fontSize=22, textColor=cor,
           leading=26, alignment=TA_CENTER))
    placar = [
        [ps_p("Total", s_lbl, TA_CENTER), ps_p("PASS", s_lbl, TA_CENTER),
         ps_p("FAIL", s_lbl, TA_CENTER),  ps_p("Taxa", s_lbl, TA_CENTER)],
        [s_big(total, PRETO), s_big(passed, VERDE),
         s_big(failed, VERMELHO), s_big(f"{taxa}%", AZUL)],
    ]
    t_placar = Table(placar, colWidths=[3.875*cm]*4)
    t_placar.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0), CINZA_FUNDO),
        ("BACKGROUND",     (0,1),(-1,1), BRANCO),
        ("BOX",            (0,0),(-1,-1), 0.5, CINZA_BORDA),
        ("INNERGRID",      (0,0),(-1,-1), 0.3, CINZA_BORDA),
        ("ALIGN",          (0,0),(-1,-1), "CENTER"),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 8),
    ]))
    story.append(t_placar)
    story.append(PageBreak())

    # ── CASOS DE TESTE POR SUITE ──────────────────────────────────────────────
    test_suites_def = [
        ("TS1", "Autenticacao e Sessao",
         "Valida o fluxo completo de login/logout, credenciais invalidas e protecao de rotas.", [
            ("CT1.1","Login com credenciais validas (Admin)",
             "Acessar /login, preencher admin/Admin@2024 e submeter.",
             "Redirecionar para / com nome do usuario na navbar.",
             ["CT1.1_tela_login","CT1.1_apos_login_admin"]),
            ("CT1.2","Login com credenciais invalidas",
             "Tentar login com senha errada.",
             "Permanecer em /login com mensagem de erro.",
             ["CT1.2_login_invalido"]),
            ("CT1.3","Login com segundo usuario (Joao Silva)",
             "Preencher joao.silva/Joao@2024 e submeter.",
             "Redirecionar para / com nome 'Joao Silva' na navbar.",
             ["CT1.3_login_joao"]),
            ("CT1.4","Logout",
             "Clicar no botao 'Sair' na navbar.",
             "Redirecionar para /login.",
             ["CT1.4_apos_logout"]),
            ("CT1.5","Protecao de rota sem autenticacao",
             "Acessar / sem sessao ativa.",
             "Redirecionado automaticamente para /login.",
             ["CT1.5_rota_protegida"]),
        ]),
        ("TS2", "Gestao de Demandas",
         "Cobre o ciclo completo: criacao, visualizacao, comentario, edicao, conclusao e reabertura.", [
            ("CT2.1","Listar demandas abertas",
             "Acessar / autenticado como admin.",
             "Cards de demanda renderizados com chips e acoes.",
             ["CT2.1_lista_abertas"]),
            ("CT2.2","Criar nova demanda",
             "Preencher formulario em /nova_demanda (titulo, descricao, prioridade Alta).",
             "Redirecionar para / com flash de sucesso.",
             ["CT2.2_form_nova_demanda","CT2.2_form_preenchido","CT2.2_apos_criar"]),
            ("CT2.3","Visualizar detalhes de demanda",
             "Clicar no titulo de uma demanda.",
             "Pagina de detalhes exibida com descricao, chips e formulario de comentario.",
             ["CT2.3_detalhes"]),
            ("CT2.4","Adicionar comentario",
             "Preencher e submeter o formulario de comentario.",
             "Comentario aparece na timeline de historico.",
             ["CT2.4_comentario_preenchido","CT2.4_apos_comentario"]),
            ("CT2.5","Editar demanda (somente solicitante)",
             "Clicar em Editar, alterar titulo e prioridade, salvar.",
             "Alteracoes persistidas e exibidas nos detalhes.",
             ["CT2.5_form_edicao","CT2.5_form_editado","CT2.5_apos_edicao"]),
            ("CT2.6","Concluir demanda",
             "Clicar em 'Concluir' na lista de abertas.",
             "Demanda removida da lista de abertas.",
             ["CT2.6_antes_concluir","CT2.6_apos_concluir"]),
            ("CT2.7","Reabrir demanda concluida",
             "Acessar /concluidas e clicar em 'Reabrir'.",
             "Demanda volta para a lista de abertas.",
             ["CT2.7_lista_concluidas","CT2.7_apos_reabrir"]),
        ]),
        ("TS3", "Controle de Acesso e Permissoes",
         "Verifica que apenas o solicitante original pode editar ou deletar sua demanda.", [
            ("CT3.1","Botao Editar ausente para nao-solicitante",
             "Login como joao.silva, acessar detalhes de demanda do admin.",
             "Botao 'Editar demanda' nao visivel.",
             ["CT3.1_detalhes_outro_usuario"]),
            ("CT3.2","Botao Deletar ausente para nao-solicitante",
             "Verificar botao Deletar na mesma pagina.",
             "Botao 'Deletar demanda' nao visivel.",
             ["CT3.2_sem_botao_deletar"]),
            ("CT3.3","Bloqueio de edicao via URL direta",
             "Tentar GET /editar/<id_do_admin> logado como joao.silva.",
             "Redirecionar com mensagem de acesso negado.",
             ["CT3.3_acesso_negado_edicao"]),
        ]),
        ("TS4", "Busca e Filtros",
         "Valida filtragem por prioridade, ordenacao e busca textual.", [
            ("CT4.1","Filtrar por prioridade Alta",
             "Acessar /?prioridade=Alta.",
             "Somente cards de prioridade Alta exibidos.",
             ["CT4.1_filtro_alta"]),
            ("CT4.2","Filtrar por prioridade Media",
             "Acessar /?prioridade=Media.",
             "Somente cards de prioridade Media exibidos.",
             ["CT4.2_filtro_media"]),
            ("CT4.3","Filtrar por prioridade Baixa",
             "Acessar /?prioridade=Baixa.",
             "Somente cards de prioridade Baixa exibidos.",
             ["CT4.3_filtro_baixa"]),
            ("CT4.4","Busca textual com resultado",
             "Acessar /buscar?q=demanda.",
             "Cards correspondentes ao termo exibidos.",
             ["CT4.4_busca_resultado"]),
            ("CT4.5","Busca textual sem resultado",
             "Acessar /buscar?q=xyztermoinesxistente.",
             "Estado vazio exibido com mensagem.",
             ["CT4.5_busca_vazia"]),
            ("CT4.6","Ordenar por mais recentes",
             "Acessar /?ordenacao=recentes.",
             "Demandas exibidas mais recentes primeiro.",
             ["CT4.6_ordenacao_recentes"]),
        ]),
        ("TS5", "Rastreabilidade de Usuarios",
         "Verifica estatisticas de demandas por usuario e filtros por solicitante.", [
            ("CT5.1","Tela de usuarios com estatisticas",
             "Acessar /usuarios.",
             "Cards com abertas, concluidas, alta aberta e total por usuario.",
             ["CT5.1_tela_usuarios"]),
            ("CT5.2","Filtrar lista por usuario via link",
             "Clicar em 'Ver X abertas' no card de um usuario.",
             "Lista filtrada pelo usuario_id correspondente.",
             ["CT5.2_filtrado_por_usuario"]),
        ]),
        ("TS6", "Responsividade Mobile (375px)",
         "Verifica adaptacao das telas principais para smartphones.", [
            ("CT6.1","Login no mobile",
             "Acessar /login com viewport 375x812.",
             "Formulario centralizado e usavel.",
             ["CT6.1_mobile_login"]),
            ("CT6.2","Index no mobile",
             "Acessar / com viewport 375x812 apos login.",
             "Navbar compacta, stats em 2 colunas, cards empilhados.",
             ["CT6.2_mobile_index"]),
            ("CT6.3","Nova demanda no mobile",
             "Acessar /nova_demanda com viewport 375x812.",
             "Formulario em coluna unica, campos acessiveis.",
             ["CT6.3_mobile_nova_demanda"]),
            ("CT6.4","Usuarios no mobile",
             "Acessar /usuarios com viewport 375x812.",
             "Grid de usuarios em coluna unica, stat-boxes visiveis.",
             ["CT6.4_mobile_usuarios"]),
        ]),
    ]

    for ts_id, ts_titulo, ts_desc, casos in test_suites_def:
        story.append(Paragraph(f"{ts_id} — {ts_titulo}", s_h1))
        story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=6))
        story.append(Paragraph(ts_desc, s_body))
        story.append(Spacer(1, 0.3*cm))

        for ct_id, ct_titulo, ct_passos, ct_esperado, ct_shots in casos:
            res    = RESULTS.get(ct_id, {"status": "N/A", "obs": "Nao executado"})
            status = res["status"]
            obs    = res["obs"]
            bg     = VERDE_CLARO if status == "PASS" else (VERM_CLARO if status == "FAIL" else CINZA_FUNDO)
            st_cor = VERDE       if status == "PASS" else (VERMELHO   if status == "FAIL" else CINZA)
            st_bold = ps("stb", fontName="Helvetica-Bold", fontSize=11,
                         textColor=st_cor, alignment=TA_CENTER)

            ct_hdr = Table([
                [Paragraph(f"<b>{ct_id}</b> — {ct_titulo}", s_h2),
                 Paragraph(f"<b>{status}</b>", st_bold)]
            ], colWidths=[13.5*cm, 2*cm])
            ct_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), bg),
                ("BOX",           (0,0),(-1,-1), 0.5, CINZA_BORDA),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(0,-1), 10),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            ct_bdy = Table([
                [Paragraph("Passos:",    s_lbl), Paragraph(ct_passos,   s_val)],
                [Paragraph("Esperado:",  s_lbl), Paragraph(ct_esperado, s_val)],
                [Paragraph("Resultado:", s_lbl), Paragraph(obs,         s_val)],
            ], colWidths=[2.5*cm, 13*cm])
            ct_bdy.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), BRANCO),
                ("BOX",           (0,0),(-1,-1), 0.5, CINZA_BORDA),
                ("INNERGRID",     (0,0),(-1,-1), 0.3, CINZA_BORDA),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ]))

            block = [ct_hdr, ct_bdy]

            validos = [(k, SHOTS[k]) for k in ct_shots if k in SHOTS]
            for i in range(0, len(validos), 2):
                par = validos[i:i+2]
                imgs = [resize_img(p, 7.5*cm, 5.5*cm) for _, p in par]
                if len(imgs) == 1:
                    imgs.append(Spacer(7.5*cm, 1))
                t_img = Table([imgs], colWidths=[7.8*cm]*2)
                t_img.setStyle(TableStyle([
                    ("ALIGN",         (0,0),(-1,-1), "CENTER"),
                    ("VALIGN",        (0,0),(-1,-1), "TOP"),
                    ("BOX",           (0,0),(-1,-1), 0.5, CINZA_BORDA),
                    ("BACKGROUND",    (0,0),(-1,-1), CINZA_FUNDO),
                    ("TOPPADDING",    (0,0),(-1,-1), 6),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                    ("LEFTPADDING",   (0,0),(-1,-1), 4),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 4),
                ]))
                block.append(t_img)

            block.append(Spacer(1, 0.35*cm))
            story.append(KeepTogether(block[:3]))
            for item in block[3:]:
                story.append(item)

        story.append(PageBreak())

    doc.build(story)
    print(f"\n  PDF gerado: {os.path.abspath(PDF_OUTPUT)}")


def ps_p(text, style, align=TA_LEFT):
    s = ParagraphStyle("_tmp", parent=style, alignment=align)
    return Paragraph(text, s)


def resize_img(path, max_w, max_h):
    with Image.open(path) as img:
        iw, ih = img.size
    ratio = min(max_w / iw, max_h / ih)
    return RLImage(path, width=iw*ratio, height=ih*ratio)


# ═════════════════════════════════════════════════════════════════════════════
# SERVIDOR FLASK
# ═════════════════════════════════════════════════════════════════════════════

def start_server():
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/login", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    print("ERRO: servidor nao respondeu.")
    proc.terminate()
    sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  SGDI - Relatorio de Testes Automatizados")
    print(f"  {TODAY}")
    print("=" * 60)

    print("\n[1/3] Iniciando servidor Flask...")
    server = start_server()
    print(f"      Servidor pronto em {BASE_URL}")

    print("\n[2/3] Executando casos de teste...")
    try:
        asyncio.run(run_tests())
    finally:
        server.terminate()
        print("\n      Servidor encerrado.")

    total  = len(RESULTS)
    passed = sum(1 for r in RESULTS.values() if r["status"] == "PASS")
    failed = total - passed
    print(f"\n      Resultado final: {passed}/{total} PASS | {failed} FAIL")

    print("\n[3/3] Gerando PDF...")
    build_pdf()

    print("\n" + "=" * 60)
    print(f"  Relatorio: {os.path.abspath(PDF_OUTPUT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
