import re

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ai_providers import ProviderError, ask_ai
from debug_utils import salvar_estado


def _ler_progresso(page: Page, sel: dict) -> tuple[int, int]:
    try:
        page.wait_for_selector(sel["pagination"], timeout=10000)
    except PlaywrightTimeoutError:
        salvar_estado(page, "sem_pagination")
        raise RuntimeError(
            "Tela de questão não carregou (sem progress__pagination). "
            "Veja o HTML/screenshot salvos em bot/debug/."
        )

    texto = page.locator(sel["pagination"]).inner_text()
    match = re.search(r"(\d+).*?de\s+(\d+)", texto, re.DOTALL)
    if not match:
        salvar_estado(page, "progresso_ilegivel")
        raise RuntimeError(f"Não consegui ler o progresso da questão: {texto!r}")
    return int(match.group(1)), int(match.group(2))


_MARCADORES_DE_GABARITO_REVELADO = (
    "Selecione a resposta",
    "Comentários da resposta",
    "Esta é a resposta correta",
)


def _ja_respondida(page: Page) -> bool:
    """Detecta se a questão já foi respondida antes (gabarito/comentários
    revelados no DOM), caso de reexecução do bot em um tópico já concluído."""
    return (
        page.locator("span.correct-answer-indicator").count() > 0
        or page.locator("span.incorrect-answer-indicator").count() > 0
    )


def _limpar_pergunta(texto: str) -> str:
    """Corta qualquer trecho de gabarito/comentário que tenha vindo junto
    no innerText (questão já respondida antes), para não vazar a resposta
    correta no prompt enviado à IA."""
    for marcador in _MARCADORES_DE_GABARITO_REVELADO:
        idx = texto.find(marcador)
        if idx != -1:
            texto = texto[:idx]
    return texto.strip()


def _ler_pergunta_e_alternativas(page: Page, sel: dict):
    pergunta = _limpar_pergunta(page.locator(sel["question_wrapper"]).first.inner_text().strip())

    wrappers = page.locator(sel["option_wrapper"])
    alternativas = []
    for i in range(wrappers.count()):
        texto_opcao = wrappers.nth(i).locator(sel["option_text"]).first.inner_text().strip()
        alternativas.append(_limpar_pergunta(texto_opcao))

    return pergunta, alternativas


def _clicar_alternativa(page: Page, sel: dict, letra: str) -> None:
    indice = ord(letra.lower()) - ord("a")
    wrapper = page.locator(sel["option_wrapper"]).nth(indice)
    wrapper.locator(sel["option_clickable"]).click()


def _verificar_feedback_visual(page: Page) -> str | None:
    """Lê o indicador visual de certo/errado que a própria plataforma mostra
    após responder (span.correct-answer-indicator / incorrect-answer-indicator),
    se ela exibir isso imediatamente. Retorna 'correto', 'incorreto' ou None
    se a plataforma não revelar o gabarito nessa hora."""
    page.wait_for_timeout(400)
    if page.locator("span.correct-answer-indicator").count() > 0:
        return "correto"
    if page.locator("span.incorrect-answer-indicator").count() > 0:
        return "incorreto"
    return None


def responder_modulo(page: Page, config: dict, provider_order: list[str]) -> dict:
    """Responde todas as questões do tópico 'Exercícios' atualmente aberto.

    Retorna um resumo {total, respondidas, erros_ia}.
    """
    sel = config["selectors"]
    resumo = {"total": 0, "respondidas": 0, "erros_ia": 0, "corretas": 0, "incorretas": 0}

    while True:
        atual, total = _ler_progresso(page, sel)
        resumo["total"] = total

        pergunta, alternativas = _ler_pergunta_e_alternativas(page, sel)

        print(f"\n--- Questão {atual}/{total} ---")
        print(f"Enunciado: {pergunta}")
        for i, alt in enumerate(alternativas):
            print(f"  {chr(ord('a') + i)}) {alt}")

        if _ja_respondida(page):
            print("Questão já tinha sido respondida antes (gabarito já revelado), pulando.")
            if atual >= total:
                break
            page.click(sel["next_button"])
            page.wait_for_timeout(500)
            continue

        try:
            letra = ask_ai(pergunta, alternativas, provider_order)
            print(f"IA respondeu: {letra}")
            _clicar_alternativa(page, sel, letra)
            resumo["respondidas"] += 1

            feedback = _verificar_feedback_visual(page)
            if feedback == "correto":
                resumo["corretas"] += 1
                print("Feedback da plataforma: CORRETO")
            elif feedback == "incorreto":
                resumo["incorretas"] += 1
                print("Feedback da plataforma: INCORRETO")
            else:
                print("Plataforma não revelou o gabarito nessa questão.")
        except ProviderError as exc:
            resumo["erros_ia"] += 1
            print(f"[aviso] IA não respondeu a questão {atual}/{total}: {exc}")

        if atual >= total:
            break

        page.click(sel["next_button"])
        page.wait_for_timeout(500)

    return resumo
