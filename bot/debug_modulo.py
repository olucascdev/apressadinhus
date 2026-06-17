"""Script de debug: loga, abre um curso, clica no primeiro módulo e salva o HTML resultante."""

from pathlib import Path

import yaml
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from login import abrir_plataforma_a, login_no_portal, salvar_sessao
from navigation import abrir_modulo, ir_para_curso, listar_modulos

BASE_DIR = Path(__file__).parent


def main():
    load_dotenv(BASE_DIR / ".env")
    with open(BASE_DIR / "config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    auth_path = BASE_DIR / config["auth_state_path"]
    course_id = config["course_ids"][1]  # curso com 8 módulos (4665097)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = (
            browser.new_context(storage_state=str(auth_path))
            if auth_path.exists()
            else browser.new_context()
        )
        portal_page = context.new_page()
        login_no_portal(context, portal_page, config)
        ead_page = abrir_plataforma_a(context, portal_page, config)
        salvar_sessao(context, str(auth_path))

        ir_para_curso(ead_page, config, course_id)
        modulos = listar_modulos(ead_page, config)
        print("módulos encontrados:", modulos.count())

        abrir_modulo(ead_page, modulos, 0)
        ead_page.wait_for_timeout(2000)

        out = BASE_DIR.parent / "debug_modulo.html"
        out.write_text(ead_page.content(), encoding="utf-8")
        print("HTML salvo em", out)
        print("URL atual:", ead_page.url)

        input("Pressione ENTER para fechar o navegador...")
        browser.close()


if __name__ == "__main__":
    main()
