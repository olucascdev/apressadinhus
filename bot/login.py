import os
from pathlib import Path

from playwright.sync_api import BrowserContext, Page


def login_no_portal(context: BrowserContext, page: Page, config: dict) -> None:
    """Faz login no portal acadêmico (SEI), se a sessão salva não estiver válida."""
    sel = config["selectors"]

    page.goto(config["login_url"])

    if page.locator(sel["login_usuario"]).count() == 0:
        # já autenticado via storage_state reaproveitado
        return

    usuario = os.environ["PORTAL_USUARIO"]
    senha = os.environ["PORTAL_SENHA"]

    page.fill(sel["login_usuario"], usuario)
    page.fill(sel["login_senha"], senha)
    page.click(sel["login_botao"])
    page.wait_for_load_state("networkidle")


def abrir_plataforma_a(context: BrowserContext, page: Page, config: dict) -> Page:
    """Clica no botão 'Plataforma A+' do portal e retorna a aba/página do EAD que abre.

    O botão dispara um RichFaces.ajax que abre uma nova aba/janela com a sessão
    da Plataforma A já autenticada via SSO.
    """
    sel = config["selectors"]

    with context.expect_page() as popup_info:
        page.click(sel["abrir_plataforma_a"])

    ead_page = popup_info.value
    ead_page.wait_for_load_state("networkidle")
    return ead_page


def salvar_sessao(context: BrowserContext, auth_path: str) -> None:
    context.storage_state(path=auth_path)
