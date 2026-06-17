from pathlib import Path

import yaml
from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError, sync_playwright

from login import abrir_plataforma_a, login_no_portal, salvar_sessao
from navigation import (
    abrir_modulo,
    abrir_topico,
    ir_para_curso,
    listar_modulos,
    listar_topicos_exercicios,
)
from quiz import responder_modulo

BASE_DIR = Path(__file__).parent


def carregar_config() -> dict:
    with open(BASE_DIR / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _pagina_fechada(exc: Exception) -> bool:
    return isinstance(exc, PlaywrightError) and "closed" in str(exc).lower()


def processar_curso(page, config: dict, course_id: str) -> None:
    print(f"\n=== Curso {course_id} ===")
    ir_para_curso(page, config, course_id)

    total_modulos = listar_modulos(page, config).count()
    print(f"{total_modulos} módulo(s) encontrados no curso.")

    for i in range(total_modulos):
        modulos = listar_modulos(page, config)
        abrir_modulo(page, modulos, i)

        topicos = listar_topicos_exercicios(page, config)
        total_topicos = topicos.count()

        if total_topicos == 0:
            print(f"Módulo {i + 1}/{total_modulos}: sem tópico de Exercícios, pulando.")
            ir_para_curso(page, config, course_id)
            continue

        for j in range(total_topicos):
            topicos_atualizados = listar_topicos_exercicios(page, config)
            abrir_topico(page, config, topicos_atualizados, j)

            try:
                resumo = responder_modulo(page, config, config["ai_provider_order"])
                print(
                    f"\n>>> Módulo {i + 1}/{total_modulos}, tópico {j + 1}/{total_topicos}: "
                    f"{resumo['respondidas']}/{resumo['total']} respondidas "
                    f"({resumo['corretas']} certas, {resumo['incorretas']} erradas, "
                    f"{resumo['erros_ia']} erro(s) de IA)"
                )
            except Exception as exc:
                if _pagina_fechada(exc):
                    raise  # não tem como recuperar, propaga até o main parar tudo
                print(
                    f"Módulo {i + 1}/{total_modulos}, tópico {j + 1}/{total_topicos}: "
                    f"falhou ao processar ({exc})"
                )

        ir_para_curso(page, config, course_id)


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    config = carregar_config()

    auth_path = BASE_DIR / config["auth_state_path"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.get("headless", False))

        if auth_path.exists():
            context = browser.new_context(storage_state=str(auth_path))
        else:
            context = browser.new_context()

        portal_page = context.new_page()

        login_no_portal(context, portal_page, config)
        ead_page = abrir_plataforma_a(context, portal_page, config)
        salvar_sessao(context, str(auth_path))

        for course_id in config["course_ids"]:
            try:
                processar_curso(ead_page, config, course_id)
            except PlaywrightError as exc:
                print(f"\n[erro fatal] A página/navegador fechou inesperadamente: {exc}")
                print("Parando a execução. Rode novamente — a sessão salva evita logar de novo.")
                break

        try:
            if not ead_page.is_closed():
                browser.close()
        except PlaywrightError:
            pass

    print("\nConcluído.")


if __name__ == "__main__":
    main()
