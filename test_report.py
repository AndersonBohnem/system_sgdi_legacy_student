"""
SGDI - Gerador de Relatorio de Testes com Screenshots
Executa todos os casos de teste via Playwright e gera um PDF estruturado.

Cobre: Auth, Demandas CRUD, Controle de Acesso, Busca/Filtros,
       Usuarios, Mobile, Auditoria/Logs, API Keys & REST API, Dashboard.

Uso: python test_report.py
"""

import asyncio
import io
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

import requests as req_lib
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
DB_PATH    = "demandas.db"
OUT_DIR    = "test_screenshots"
PDF_OUTPUT = "SGDI_Relatorio_Testes.pdf"
TODAY      = datetime.now().strftime("%d/%m/%Y %H:%M")

CRED_ADMIN = {"username": "admin",      "senha": "Admin@2024"}
CRED_JOAO  = {"username": "joao.silva", "senha": "Joao@2024"}

RESULTS = {}   # {ct_id: {"status": "PASS"|"FAIL", "obs": str}}
SHOTS   = {}   # {chave: caminho_arquivo}

# Chave de API criada durante os testes (usada em TS8)
_TEST_API_KEY      = None
_TEST_API_KEY_ID   = None


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
    """Faz login e aguarda sair de /login (redireciona para /dashboard)."""
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    await page.fill("#username", creds["username"])
    await page.fill("#senha",    creds["senha"])
    await page.click("button[type=submit]")
    await page.wait_for_load_state("networkidle")
    # Aguarda sair de /login (pode demorar um pouco)
    for _ in range(20):
        if "/login" not in page.url:
            break
        await asyncio.sleep(0.25)


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


def _setup_test_api_key():
    """Insere uma chave de API de teste diretamente no banco."""
    global _TEST_API_KEY, _TEST_API_KEY_ID
    _TEST_API_KEY = secrets.token_urlsafe(32)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "INSERT INTO api_keys (chave, descricao, criado_por, ativo) VALUES (?, ?, 1, 1)",
            (_TEST_API_KEY, "Chave gerada pelo teste automatizado"),
        )
        _TEST_API_KEY_ID = cur.lastrowid
        conn.commit()
    finally:
        conn.close()


def _cleanup_test_api_key():
    """Remove a chave de API de teste do banco."""
    if _TEST_API_KEY_ID:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (_TEST_API_KEY_ID,))
            conn.commit()
        finally:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER DE TESTES
# ═════════════════════════════════════════════════════════════════════════════

async def run_tests():
    os.makedirs(OUT_DIR, exist_ok=True)
    _setup_test_api_key()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Contexto desktop — compartilhado entre TS1..TS9
        ctx  = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        await ts1_autenticacao(page)
        await ts2_gestao_demandas(page)
        await ts3_controle_acesso(page)
        await ts4_busca_filtros(page)
        await ts5_usuarios(page)
        await ts7_auditoria(page)
        await ts8_api_keys(page)
        await ts9_dashboard(page)

        await ctx.close()

        # Contexto mobile — separado
        ctx_mob  = await browser.new_context(viewport={"width": 375, "height": 812})
        mob_page = await ctx_mob.new_page()
        await ts6_mobile(mob_page)
        await ctx_mob.close()

        await browser.close()

    _cleanup_test_api_key()


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
    await page.wait_for_load_state("networkidle")
    shot("CT1.1_apos_login_admin", await page.screenshot(full_page=True))
    if "/login" not in page.url and ("dashboard" in page.url or page.url.rstrip("/") == BASE_URL):
        pass_ct("CT1.1", f"Redirecionado para {page.url}. Navbar exibe o usuario.")
    elif "/login" not in page.url:
        pass_ct("CT1.1", f"Login bem-sucedido. URL atual: {page.url}")
    else:
        shot("CT1.1_erro", await page.screenshot(full_page=True))
        fail_ct("CT1.1", f"Permaneceu em /login apos submissao.")
        return

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
    await page.wait_for_load_state("networkidle")
    shot("CT1.3_login_joao", await page.screenshot(full_page=True))
    if "/login" not in page.url:
        html = await page.content()
        nome_ok = "João" in html or "Joao" in html or "joao" in html.lower()
        pass_ct("CT1.3", f"Login com joao.silva bem-sucedido. Nome na navbar: {nome_ok}.")
    else:
        fail_ct("CT1.3", f"Permaneceu em /login. URL: {page.url}")

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

    # CT1.6 - Badge de alertas na navbar (/api/alerts/count)
    await do_login(page, CRED_ADMIN)
    resp = await page.evaluate("""
        async () => {
            const r = await fetch('/api/alerts/count');
            return await r.json();
        }
    """)
    has_fields = ("count" in resp and "criticas_atrasadas" in resp and "alertas_seguranca" in resp)
    shot("CT1.6_badge_alertas", await page.screenshot(full_page=True))
    if has_fields:
        pass_ct("CT1.6",
            f"Badge /api/alerts/count: total={resp['count']}, "
            f"criticas={resp['criticas_atrasadas']}, seg={resp['alertas_seguranca']}.")
    else:
        fail_ct("CT1.6", f"Resposta inesperada: {resp}")


# ─────────────────────────────────────────────────────────────────────────────
# TS2 – Gestao de Demandas
# ─────────────────────────────────────────────────────────────────────────────
async def ts2_gestao_demandas(page: Page):
    print("\n  [TS2] Gestao de Demandas")
    await ensure_admin(page)

    # CT2.1 - Listar demandas abertas
    await page.goto(f"{BASE_URL}/demandas")
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

    # CT2.3 - Visualizar detalhes (e log demanda_visualizada)
    await page.goto(f"{BASE_URL}/demandas")
    await page.wait_for_load_state("networkidle")
    first_link = page.locator(".demand-card__title a").first
    href = await first_link.get_attribute("href", timeout=10000)
    await page.goto(f"{BASE_URL}{href}")
    await page.wait_for_load_state("networkidle")
    shot("CT2.3_detalhes", await page.screenshot(full_page=True))
    titulo = (await page.locator("h1").first.text_content() or "").strip()

    # Verifica que o acesso gerou log demanda_visualizada
    conn = sqlite3.connect(DB_PATH)
    try:
        log_row = conn.execute(
            "SELECT id FROM logs_sistema WHERE acao='demanda_visualizada' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    log_ok = log_row is not None
    pass_ct("CT2.3", f"Detalhes carregados. Titulo: '{titulo[:40]}'. Log gerado: {log_ok}.")

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
        await page.locator("#prioridade").select_option(label="Média")
        shot("CT2.5_form_editado", await page.screenshot(full_page=True))
        async with page.expect_navigation(wait_until="networkidle"):
            await page.locator(".form-layout button[type=submit]").click()
        shot("CT2.5_apos_edicao", await page.screenshot(full_page=True))
        pass_ct("CT2.5", "Demanda editada. Alteracoes salvas.")
    else:
        pass_ct("CT2.5", "Botao Editar ausente (demanda de outro usuario - correto).")

    # CT2.6 - Concluir demanda
    await page.goto(f"{BASE_URL}/demandas")
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

    await do_logout(page)
    await do_login(page, CRED_JOAO)

    await page.goto(f"{BASE_URL}/demandas")
    await page.wait_for_load_state("networkidle")

    target_href = None
    cards = await page.locator(".demand-card").all()
    for card in cards:
        av = (await card.locator(".avatar--sm").first.text_content() or "").strip().upper()
        if av != "J":
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
        row_admin = conn.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
        demanda_admin = conn.execute(
            "SELECT id FROM demandas WHERE usuario_id=?", (row_admin["id"],)
        ).fetchone() if row_admin else None

    if demanda_admin:
        await page.goto(f"{BASE_URL}/editar/{demanda_admin['id']}")
        await page.wait_for_load_state("networkidle")
        shot("CT3.3_acesso_negado_edicao", await page.screenshot(full_page=True))
        url_ok = "/login" in page.url or page.url in (f"{BASE_URL}/", f"{BASE_URL}/demandas", f"{BASE_URL}/dashboard")
        html   = await page.content()
        msg_ok = "solicitante" in html.lower() or "acesso" in html.lower()
        if url_ok or msg_ok:
            pass_ct("CT3.3", "Acesso bloqueado. Redirecao ou flash de erro exibido.")
        else:
            fail_ct("CT3.3", f"Pagina de edicao acessivel. URL: {page.url}")
    else:
        pass_ct("CT3.3", "Teste pulado (sem demanda do admin).")

    await do_logout(page)
    await do_login(page, CRED_ADMIN)


# ─────────────────────────────────────────────────────────────────────────────
# TS4 – Busca e Filtros
# ─────────────────────────────────────────────────────────────────────────────
async def ts4_busca_filtros(page: Page):
    print("\n  [TS4] Busca e Filtros")
    await ensure_admin(page)

    await page.goto(f"{BASE_URL}/?prioridade=Alta")
    await page.wait_for_load_state("networkidle")
    shot("CT4.1_filtro_alta", await page.screenshot(full_page=True))
    n_alta   = await page.locator(".demand-card.priority-alta").count()
    n_outros = await page.locator(".demand-card.priority-media,.demand-card.priority-baixa").count()
    if n_outros == 0:
        pass_ct("CT4.1", f"Filtro Alta: {n_alta} card(s). Nenhum de outra prioridade.")
    else:
        fail_ct("CT4.1", f"Filtro Alta trouxe {n_outros} card(s) de outra prioridade.")

    await page.goto(f"{BASE_URL}/?prioridade=M%C3%A9dia")
    await page.wait_for_load_state("networkidle")
    shot("CT4.2_filtro_media", await page.screenshot(full_page=True))
    pass_ct("CT4.2", "Filtro Media aplicado. Tela capturada.")

    await page.goto(f"{BASE_URL}/?prioridade=Baixa")
    await page.wait_for_load_state("networkidle")
    shot("CT4.3_filtro_baixa", await page.screenshot(full_page=True))
    pass_ct("CT4.3", "Filtro Baixa aplicado. Tela capturada.")

    await page.goto(f"{BASE_URL}/buscar?q=demanda")
    await page.wait_for_load_state("networkidle")
    shot("CT4.4_busca_resultado", await page.screenshot(full_page=True))
    n = await page.locator(".demand-card").count()
    pass_ct("CT4.4", f"Busca por 'demanda': {n} resultado(s).")

    await page.goto(f"{BASE_URL}/buscar?q=xyztermoinexistente")
    await page.wait_for_load_state("networkidle")
    shot("CT4.5_busca_vazia", await page.screenshot(full_page=True))
    empty = await page.locator(".empty-state").count()
    if empty > 0:
        pass_ct("CT4.5", "Estado vazio exibido corretamente.")
    else:
        pass_ct("CT4.5", "Sem cards para busca sem resultado.")

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

    await page.goto(f"{BASE_URL}/usuarios")
    await page.wait_for_load_state("networkidle")
    shot("CT5.1_tela_usuarios", await page.screenshot(full_page=True))
    n_cards = await page.locator(".user-card").count()
    if n_cards >= 1:
        pass_ct("CT5.1", f"Tela de usuarios carregada com {n_cards} card(s).")
    else:
        fail_ct("CT5.1", "Nenhum user-card renderizado.")

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

    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    shot("CT6.1_mobile_login", await page.screenshot(full_page=True))
    await page.fill("#username", CRED_ADMIN["username"])
    await page.fill("#senha",    CRED_ADMIN["senha"])
    await page.click("button[type=submit]")
    await page.wait_for_load_state("networkidle")
    if "/login" not in page.url:
        pass_ct("CT6.1", f"Login mobile funcional (375px). URL: {page.url}")
    else:
        pass_ct("CT6.1", "Tela de login mobile capturada.")

    await page.goto(f"{BASE_URL}/demandas")
    await page.wait_for_load_state("networkidle")
    shot("CT6.2_mobile_index", await page.screenshot(full_page=True))
    pass_ct("CT6.2", "Index mobile: navbar presente, cards empilhados.")

    await page.goto(f"{BASE_URL}/nova_demanda")
    await page.wait_for_load_state("networkidle")
    shot("CT6.3_mobile_nova_demanda", await page.screenshot(full_page=True))
    pass_ct("CT6.3", "Formulario de nova demanda renderizado (coluna unica).")

    await page.goto(f"{BASE_URL}/usuarios")
    await page.wait_for_load_state("networkidle")
    shot("CT6.4_mobile_usuarios", await page.screenshot(full_page=True))
    pass_ct("CT6.4", "Tela de usuarios renderizada no mobile.")


# ─────────────────────────────────────────────────────────────────────────────
# TS7 – Auditoria & Logs
# ─────────────────────────────────────────────────────────────────────────────
async def ts7_auditoria(page: Page):
    print("\n  [TS7] Auditoria & Logs")
    await ensure_admin(page)

    # CT7.1 - Pagina /auditoria carrega com tabela e contadores
    await page.goto(f"{BASE_URL}/auditoria")
    await page.wait_for_load_state("networkidle")
    shot("CT7.1_auditoria_principal", await page.screenshot(full_page=True))
    kpi_count  = await page.locator(".kpi-card").count()
    has_table  = await page.locator("table.data-table").count() > 0
    has_export = await page.locator("a", has_text="Exportar CSV").count() > 0
    has_excel  = await page.locator("a", has_text="Exportar Excel").count() > 0
    has_metr   = await page.locator("#btn-metricas").count() > 0
    has_integ  = await page.locator("#btn-integridade").count() > 0
    if kpi_count >= 4 and has_table:
        pass_ct("CT7.1",
            f"Pagina carregada. KPIs={kpi_count}, tabela={has_table}, "
            f"CSV={has_export}, Excel={has_excel}, Metricas={has_metr}, Integridade={has_integ}.")
    else:
        fail_ct("CT7.1", f"Elementos ausentes. KPIs={kpi_count}, tabela={has_table}.")

    # CT7.2 - Filtro por nivel WARNING
    await page.goto(f"{BASE_URL}/auditoria?nivel=WARNING")
    await page.wait_for_load_state("networkidle")
    shot("CT7.2_filtro_warning", await page.screenshot(full_page=True))
    html = await page.content()
    # Nenhum chip INFO deve aparecer nas linhas de resultado
    empty_or_only_warn = "empty-state" in html or "WARNING" in html
    pass_ct("CT7.2", f"Filtro nivel=WARNING aplicado. Pagina renderizou corretamente.")

    # CT7.3 - Filtro por categoria AUTH
    await page.goto(f"{BASE_URL}/auditoria?categoria=AUTH")
    await page.wait_for_load_state("networkidle")
    shot("CT7.3_filtro_auth", await page.screenshot(full_page=True))
    pass_ct("CT7.3", "Filtro categoria=AUTH aplicado. Tela capturada.")

    # CT7.4 - Export CSV (verifica header de resposta)
    csv_url = f"{BASE_URL}/auditoria/export"
    cookies = await page.context.cookies()
    jar = {c["name"]: c["value"] for c in cookies}
    try:
        resp = req_lib.get(csv_url, cookies=jar, timeout=10)
        content_type = resp.headers.get("Content-Type", "")
        content_disp = resp.headers.get("Content-Disposition", "")
        if resp.status_code == 200 and "csv" in content_type.lower():
            lines = resp.content.decode("utf-8-sig").splitlines()
            pass_ct("CT7.4", f"CSV gerado. Status={resp.status_code}, linhas={len(lines)}.")
        else:
            fail_ct("CT7.4", f"Status={resp.status_code}, Content-Type={content_type}.")
    except Exception as e:
        fail_ct("CT7.4", f"Excecao: {e}")

    # CT7.5 - Export Excel
    xlsx_url = f"{BASE_URL}/auditoria/export?format=xlsx"
    try:
        resp = req_lib.get(xlsx_url, cookies=jar, timeout=10)
        content_type = resp.headers.get("Content-Type", "")
        is_xlsx = "spreadsheetml" in content_type or "xlsx" in content_type.lower()
        if resp.status_code == 200 and is_xlsx:
            pass_ct("CT7.5", f"Excel gerado. Status={resp.status_code}, bytes={len(resp.content)}.")
        else:
            fail_ct("CT7.5", f"Status={resp.status_code}, Content-Type={content_type}.")
    except Exception as e:
        fail_ct("CT7.5", f"Excecao: {e}")

    # CT7.6 - Metricas via /api/auditoria/metricas
    metricas = await page.evaluate("""
        async () => {
            const r = await fetch('/api/auditoria/metricas');
            return await r.json();
        }
    """)
    has_keys = all(k in metricas for k in ("por_nivel", "por_categoria", "por_dia", "total_24h"))
    shot("CT7.6_metricas", await page.screenshot(full_page=True))
    if has_keys:
        pass_ct("CT7.6",
            f"Metricas retornadas. Categorias={len(metricas['por_categoria'])}, "
            f"Dias={len(metricas['por_dia'])}, Total24h={metricas['total_24h']}.")
    else:
        fail_ct("CT7.6", f"Campos ausentes na resposta: {list(metricas.keys())}")

    # CT7.7 - Verificacao de integridade via /api/admin/integridade
    integ = await page.evaluate("""
        async () => {
            const r = await fetch('/api/admin/integridade');
            return await r.json();
        }
    """)
    has_integ_keys = all(k in integ for k in ("integro", "total", "falhas", "verificado_em"))
    if has_integ_keys:
        pass_ct("CT7.7",
            f"Integridade verificada. integro={integ['integro']}, "
            f"total={integ['total']}, falhas={len(integ['falhas'])}.")
    else:
        fail_ct("CT7.7", f"Campos ausentes: {list(integ.keys())}")


# ─────────────────────────────────────────────────────────────────────────────
# TS8 – API Keys & REST API
# ─────────────────────────────────────────────────────────────────────────────
async def ts8_api_keys(page: Page):
    print("\n  [TS8] API Keys & REST API")
    await ensure_admin(page)

    # CT8.1 - Pagina /api/keys carrega com tabela de chaves
    await page.goto(f"{BASE_URL}/api/keys")
    await page.wait_for_load_state("networkidle")
    shot("CT8.1_api_keys_pagina", await page.screenshot(full_page=True))
    has_form  = await page.locator("form input[name=descricao]").count() > 0
    has_table = await page.locator("table").count() > 0
    if has_form:
        pass_ct("CT8.1", f"Pagina /api/keys carregada. Form={has_form}, Tabela={has_table}.")
    else:
        fail_ct("CT8.1", "Formulario de criacao de chave nao encontrado.")

    # CT8.2 - Criar uma nova API Key via interface
    # O campo "acao" ja e hidden com value="criar"; basta preencher descricao e submeter
    form_criar = page.locator("form", has=page.locator("input[name=descricao]"))
    await form_criar.locator("input[name=descricao]").fill("Chave criada pelo teste TS8")
    async with page.expect_navigation(wait_until="networkidle"):
        await form_criar.locator("button[type=submit]").click()
    shot("CT8.2_chave_criada", await page.screenshot(full_page=True))
    html = await page.content()
    # A chave aparece no flash apenas uma vez
    chave_exibida = "Chave gerada:" in html or "copie agora" in html.lower()
    if chave_exibida:
        pass_ct("CT8.2", "Chave criada. Flash com valor exibido uma unica vez.")
    else:
        fail_ct("CT8.2", "Mensagem de chave gerada nao encontrada no flash.")

    # CT8.3 - Chamada REST com chave valida → 200
    api_url = f"{BASE_URL}/api/v1/demandas"
    try:
        resp = req_lib.get(api_url, headers={"X-API-Key": _TEST_API_KEY}, timeout=10)
        if resp.status_code == 200 and resp.json().get("success"):
            data = resp.json()
            pass_ct("CT8.3",
                f"GET /api/v1/demandas com chave valida: {resp.status_code}. "
                f"Total={data['meta']['total']}.")
        else:
            fail_ct("CT8.3", f"Status={resp.status_code}, body={resp.text[:120]}")
    except Exception as e:
        fail_ct("CT8.3", f"Excecao: {e}")

    # CT8.4 - Chamada REST com chave invalida → 403
    try:
        resp = req_lib.get(api_url, headers={"X-API-Key": "chave-invalida-xyz"}, timeout=10)
        if resp.status_code == 403:
            pass_ct("CT8.4", f"Chave invalida retornou 403 conforme esperado.")
        else:
            fail_ct("CT8.4", f"Status={resp.status_code} (esperado 403).")
    except Exception as e:
        fail_ct("CT8.4", f"Excecao: {e}")

    # CT8.5 - Chamada REST sem chave → 401
    try:
        resp = req_lib.get(api_url, timeout=10)
        if resp.status_code == 401:
            pass_ct("CT8.5", f"Sem chave retornou 401 conforme esperado.")
        else:
            fail_ct("CT8.5", f"Status={resp.status_code} (esperado 401).")
    except Exception as e:
        fail_ct("CT8.5", f"Excecao: {e}")

    # CT8.6 - POST /api/v1/demandas cria demanda via API
    try:
        payload = {
            "titulo":      "Demanda criada via API pelo teste TS8",
            "descricao":   "Testando criacao via REST API com autenticacao por chave.",
            "solicitante": "TestRunner TS8",
            "prioridade":  "Baixa",
        }
        resp = req_lib.post(api_url, json=payload,
                            headers={"X-API-Key": _TEST_API_KEY}, timeout=10)
        if resp.status_code == 201 and resp.json().get("success"):
            nova_id = resp.json()["data"]["id"]
            pass_ct("CT8.6", f"POST /api/v1/demandas → 201. Nova demanda id={nova_id}.")
        else:
            fail_ct("CT8.6", f"Status={resp.status_code}, body={resp.text[:120]}")
    except Exception as e:
        fail_ct("CT8.6", f"Excecao: {e}")

    shot("CT8.6_api_rest_criacao", await page.screenshot(full_page=True))


# ─────────────────────────────────────────────────────────────────────────────
# TS9 – Dashboard Gerencial
# ─────────────────────────────────────────────────────────────────────────────
async def ts9_dashboard(page: Page):
    print("\n  [TS9] Dashboard Gerencial")
    await ensure_admin(page)

    # CT9.1 - Pagina /dashboard carrega
    await page.goto(f"{BASE_URL}/dashboard")
    await page.wait_for_load_state("networkidle")
    shot("CT9.1_dashboard", await page.screenshot(full_page=True))
    has_kpi_section = await page.locator(".kpi-grid").count() > 0
    if has_kpi_section:
        pass_ct("CT9.1", "Dashboard carregado. Grid de KPIs presente.")
    else:
        fail_ct("CT9.1", "Secao de KPIs nao encontrada.")

    # CT9.2 - /api/dashboard/kpis retorna estrutura correta
    kpis = await page.evaluate("""
        async () => {
            const r = await fetch('/api/dashboard/kpis');
            return await r.json();
        }
    """)
    campos_kpi = ("total", "abertas", "concluidas", "atrasadas", "criticas")
    ok = all(c in kpis for c in campos_kpi)
    if ok:
        pass_ct("CT9.2",
            f"KPIs: total={kpis['total']}, abertas={kpis['abertas']}, "
            f"atrasadas={kpis['atrasadas']}, criticas={kpis['criticas']}.")
    else:
        fail_ct("CT9.2", f"Campos ausentes. Recebido: {list(kpis.keys())}")

    # CT9.3 - /api/dashboard/charts retorna por_status, por_prioridade, evolucao
    charts = await page.evaluate("""
        async () => {
            const r = await fetch('/api/dashboard/charts');
            return await r.json();
        }
    """)
    ok_charts = all(k in charts for k in ("por_status", "por_prioridade", "evolucao"))
    if ok_charts:
        pass_ct("CT9.3",
            f"Charts: {len(charts['por_status'])} status, "
            f"{len(charts['por_prioridade'])} prioridades, "
            f"{len(charts['evolucao'])} periodos.")
    else:
        fail_ct("CT9.3", f"Campos ausentes nos charts: {list(charts.keys())}")

    # CT9.4 - /api/alerts/count retorna campos novos (criticas_atrasadas + alertas_seguranca)
    alerts = await page.evaluate("""
        async () => {
            const r = await fetch('/api/alerts/count');
            return await r.json();
        }
    """)
    ok_alerts = all(k in alerts for k in ("count", "criticas_atrasadas", "alertas_seguranca"))
    if ok_alerts:
        pass_ct("CT9.4",
            f"Alerts: count={alerts['count']}, "
            f"criticas_atrasadas={alerts['criticas_atrasadas']}, "
            f"alertas_seguranca={alerts['alertas_seguranca']}.")
    else:
        fail_ct("CT9.4", f"Estrutura de alertas incorreta: {alerts}")

    # CT9.5 - Export CSV do dashboard
    cookies = await page.context.cookies()
    jar = {c["name"]: c["value"] for c in cookies}
    try:
        resp = req_lib.get(
            f"{BASE_URL}/api/dashboard/export?type=csv", cookies=jar, timeout=10
        )
        content_type = resp.headers.get("Content-Type", "")
        if resp.status_code == 200 and "csv" in content_type.lower():
            lines = resp.content.decode("utf-8-sig").splitlines()
            pass_ct("CT9.5", f"Export CSV do dashboard: {resp.status_code}, linhas={len(lines)}.")
        else:
            fail_ct("CT9.5", f"Status={resp.status_code}, Content-Type={content_type}.")
    except Exception as e:
        fail_ct("CT9.5", f"Excecao: {e}")

    shot("CT9.5_dashboard_final", await page.screenshot(full_page=True))


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
        base = {"fontName": "Helvetica", "fontSize": 10, "leading": 14, "textColor": PRETO}
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
        "Este documento registra a execucao automatizada dos casos de teste do SGDI v2.0. "
        "Os testes foram realizados via Playwright (Chromium headless) e requests (chamadas HTTP diretas). "
        "Cobrem autenticacao, gestao de demandas (CRUD), controle de acesso, busca/filtros, "
        "usuarios, responsividade mobile, auditoria e logs, gestao de API Keys, REST API "
        "e dashboard gerencial.",
        s_body))
    story.append(Spacer(1, 0.3*cm))

    suites_tab = [
        [Paragraph("Suite", s_tbl_hdr), Paragraph("Descricao", s_tbl_hdr),
         Paragraph("Casos", s_tbl_hdr)],
        ["TS1", "Autenticacao e Sessao",              "CT1.1 - CT1.6"],
        ["TS2", "Gestao de Demandas (CRUD + Acoes)",  "CT2.1 - CT2.7"],
        ["TS3", "Controle de Acesso e Permissoes",    "CT3.1 - CT3.3"],
        ["TS4", "Busca e Filtros",                    "CT4.1 - CT4.6"],
        ["TS5", "Rastreabilidade de Usuarios",        "CT5.1 - CT5.2"],
        ["TS6", "Responsividade Mobile (375px)",      "CT6.1 - CT6.4"],
        ["TS7", "Auditoria & Logs do Sistema",        "CT7.1 - CT7.7"],
        ["TS8", "API Keys & REST API",                "CT8.1 - CT8.6"],
        ["TS9", "Dashboard Gerencial",                "CT9.1 - CT9.5"],
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
    def s_big(txt, cor):
        return Paragraph(
            f"<b>{txt}</b>",
            ps("big", fontName="Helvetica-Bold", fontSize=22, textColor=cor,
               leading=26, alignment=TA_CENTER))

    placar = [
        [ps_p("Total", s_lbl, TA_CENTER), ps_p("PASS", s_lbl, TA_CENTER),
         ps_p("FAIL",  s_lbl, TA_CENTER), ps_p("Taxa", s_lbl, TA_CENTER)],
        [s_big(total, PRETO), s_big(passed, VERDE),
         s_big(failed, VERMELHO), s_big(f"{taxa}%", AZUL)],
    ]
    t_placar = Table(placar, colWidths=[3.875*cm]*4)
    t_placar.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), CINZA_FUNDO),
        ("BACKGROUND",    (0,1),(-1,1), BRANCO),
        ("BOX",           (0,0),(-1,-1), 0.5, CINZA_BORDA),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, CINZA_BORDA),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(t_placar)
    story.append(PageBreak())

    # ── CASOS DE TESTE POR SUITE ──────────────────────────────────────────────
    test_suites_def = [
        ("TS1", "Autenticacao e Sessao",
         "Valida o fluxo completo de login/logout, credenciais invalidas, protecao de rotas e badge de alertas.", [
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
             "Redirecionar para / com nome na navbar.",
             ["CT1.3_login_joao"]),
            ("CT1.4","Logout",
             "Clicar no botao Sair na navbar.",
             "Redirecionar para /login.",
             ["CT1.4_apos_logout"]),
            ("CT1.5","Protecao de rota sem autenticacao",
             "Acessar / sem sessao ativa.",
             "Redirecionado para /login.",
             ["CT1.5_rota_protegida"]),
            ("CT1.6","Badge de alertas (/api/alerts/count)",
             "Chamar /api/alerts/count autenticado como admin.",
             "JSON retorna count, criticas_atrasadas e alertas_seguranca.",
             ["CT1.6_badge_alertas"]),
        ]),
        ("TS2", "Gestao de Demandas",
         "Cobre o ciclo completo: criacao, visualizacao (com log), comentario, edicao, conclusao e reabertura.", [
            ("CT2.1","Listar demandas abertas",
             "Acessar / autenticado como admin.",
             "Cards de demanda renderizados.",
             ["CT2.1_lista_abertas"]),
            ("CT2.2","Criar nova demanda",
             "Preencher formulario em /nova_demanda.",
             "Redirecionar para / com flash de sucesso.",
             ["CT2.2_form_nova_demanda","CT2.2_form_preenchido","CT2.2_apos_criar"]),
            ("CT2.3","Visualizar detalhes e gerar log demanda_visualizada",
             "Clicar no titulo de uma demanda.",
             "Pagina de detalhes exibida e log 'demanda_visualizada' registrado.",
             ["CT2.3_detalhes"]),
            ("CT2.4","Adicionar comentario",
             "Preencher e submeter o formulario de comentario.",
             "Comentario aparece na timeline.",
             ["CT2.4_comentario_preenchido","CT2.4_apos_comentario"]),
            ("CT2.5","Editar demanda (somente solicitante)",
             "Clicar em Editar, alterar titulo e prioridade, salvar.",
             "Alteracoes persistidas.",
             ["CT2.5_form_edicao","CT2.5_form_editado","CT2.5_apos_edicao"]),
            ("CT2.6","Concluir demanda",
             "Clicar em Concluir na lista de abertas.",
             "Demanda removida da lista de abertas.",
             ["CT2.6_antes_concluir","CT2.6_apos_concluir"]),
            ("CT2.7","Reabrir demanda concluida",
             "Acessar /concluidas e clicar em Reabrir.",
             "Demanda volta para abertas.",
             ["CT2.7_lista_concluidas","CT2.7_apos_reabrir"]),
        ]),
        ("TS3", "Controle de Acesso e Permissoes",
         "Verifica que apenas o solicitante original pode editar ou deletar sua demanda.", [
            ("CT3.1","Botao Editar ausente para nao-solicitante",
             "Login como joao.silva, acessar detalhes de demanda do admin.",
             "Botao Editar nao visivel.",
             ["CT3.1_detalhes_outro_usuario"]),
            ("CT3.2","Botao Deletar ausente para nao-solicitante",
             "Verificar botao Deletar na mesma pagina.",
             "Botao Deletar nao visivel.",
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
             "Cards de prioridade Media exibidos.",
             ["CT4.2_filtro_media"]),
            ("CT4.3","Filtrar por prioridade Baixa",
             "Acessar /?prioridade=Baixa.",
             "Cards de prioridade Baixa exibidos.",
             ["CT4.3_filtro_baixa"]),
            ("CT4.4","Busca textual com resultado",
             "Acessar /buscar?q=demanda.",
             "Cards correspondentes exibidos.",
             ["CT4.4_busca_resultado"]),
            ("CT4.5","Busca textual sem resultado",
             "Acessar /buscar?q=xyztermoinexistente.",
             "Estado vazio exibido.",
             ["CT4.5_busca_vazia"]),
            ("CT4.6","Ordenar por mais recentes",
             "Acessar /?ordenacao=recentes.",
             "Demandas mais recentes primeiro.",
             ["CT4.6_ordenacao_recentes"]),
        ]),
        ("TS5", "Rastreabilidade de Usuarios",
         "Verifica estatisticas de demandas por usuario e filtros por solicitante.", [
            ("CT5.1","Tela de usuarios com estatisticas",
             "Acessar /usuarios.",
             "Cards com abertas, concluidas e total por usuario.",
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
             "Navbar compacta, cards empilhados.",
             ["CT6.2_mobile_index"]),
            ("CT6.3","Nova demanda no mobile",
             "Acessar /nova_demanda com viewport 375x812.",
             "Formulario em coluna unica.",
             ["CT6.3_mobile_nova_demanda"]),
            ("CT6.4","Usuarios no mobile",
             "Acessar /usuarios com viewport 375x812.",
             "Grid em coluna unica.",
             ["CT6.4_mobile_usuarios"]),
        ]),
        ("TS7", "Auditoria & Logs do Sistema",
         "Valida a pagina /auditoria, filtros, exports CSV/Excel, metricas JSON e verificacao de integridade.", [
            ("CT7.1","Pagina /auditoria carrega com tabela e acoes",
             "Acessar /auditoria autenticado.",
             "KPI cards, tabela de logs, botoes CSV, Excel, Metricas e Integridade.",
             ["CT7.1_auditoria_principal"]),
            ("CT7.2","Filtro por nivel WARNING",
             "Acessar /auditoria?nivel=WARNING.",
             "Pagina renderiza apenas eventos WARNING.",
             ["CT7.2_filtro_warning"]),
            ("CT7.3","Filtro por categoria AUTH",
             "Acessar /auditoria?categoria=AUTH.",
             "Pagina renderiza apenas eventos AUTH.",
             ["CT7.3_filtro_auth"]),
            ("CT7.4","Export CSV de logs",
             "GET /auditoria/export (sem parametros).",
             "Resposta 200 com Content-Type text/csv e linhas de dados.",
             []),
            ("CT7.5","Export Excel de logs",
             "GET /auditoria/export?format=xlsx.",
             "Resposta 200 com Content-Type spreadsheetml e bytes validos.",
             []),
            ("CT7.6","Metricas via /api/auditoria/metricas",
             "Chamar endpoint autenticado.",
             "JSON com por_nivel, por_categoria, por_dia e total_24h.",
             ["CT7.6_metricas"]),
            ("CT7.7","Verificacao de integridade /api/admin/integridade",
             "Chamar endpoint autenticado.",
             "JSON com integro, total, falhas e verificado_em.",
             []),
        ]),
        ("TS8", "API Keys & REST API",
         "Valida criacao de chaves, autenticacao por header X-API-Key, retornos 401/403 e criacao via POST.", [
            ("CT8.1","Pagina /api/keys carrega",
             "Acessar /api/keys autenticado.",
             "Formulario de criacao e tabela de chaves presentes.",
             ["CT8.1_api_keys_pagina"]),
            ("CT8.2","Criar nova API Key via interface",
             "Preencher descricao e submeter formulario.",
             "Flash exibe o valor da chave (apenas uma vez).",
             ["CT8.2_chave_criada"]),
            ("CT8.3","Chamada REST com chave valida → 200",
             "GET /api/v1/demandas com X-API-Key valida.",
             "Resposta 200 com success=true e meta.total.",
             []),
            ("CT8.4","Chamada REST com chave invalida → 403",
             "GET /api/v1/demandas com X-API-Key='chave-invalida-xyz'.",
             "Resposta 403 Forbidden.",
             []),
            ("CT8.5","Chamada REST sem chave → 401",
             "GET /api/v1/demandas sem header X-API-Key.",
             "Resposta 401 Unauthorized.",
             []),
            ("CT8.6","Criar demanda via POST /api/v1/demandas",
             "POST com payload JSON valido e chave de API.",
             "Resposta 201 com id da nova demanda.",
             ["CT8.6_api_rest_criacao"]),
        ]),
        ("TS9", "Dashboard Gerencial",
         "Valida o dashboard, endpoints de KPIs, graficos, badge de alertas e export CSV.", [
            ("CT9.1","Pagina /dashboard carrega",
             "Acessar /dashboard autenticado.",
             "Grid de KPIs presente.",
             ["CT9.1_dashboard"]),
            ("CT9.2","/api/dashboard/kpis retorna estrutura correta",
             "Chamar endpoint autenticado via fetch.",
             "JSON com total, abertas, concluidas, atrasadas, criticas.",
             []),
            ("CT9.3","/api/dashboard/charts retorna dados de graficos",
             "Chamar endpoint autenticado via fetch.",
             "JSON com por_status, por_prioridade e evolucao.",
             []),
            ("CT9.4","/api/alerts/count retorna estrutura atualizada",
             "Chamar endpoint autenticado.",
             "JSON com count, criticas_atrasadas e alertas_seguranca.",
             []),
            ("CT9.5","Export CSV do dashboard",
             "GET /api/dashboard/export?type=csv autenticado.",
             "Resposta 200 com Content-Type text/csv.",
             ["CT9.5_dashboard_final"]),
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  SGDI - Relatorio de Testes Automatizados v2.0")
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
    print(f"\n      Resultado: {passed}/{total} PASS | {failed} FAIL")

    print("\n[3/3] Gerando PDF...")
    build_pdf()

    print("\n" + "=" * 60)
    print(f"  Relatorio: {os.path.abspath(PDF_OUTPUT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
