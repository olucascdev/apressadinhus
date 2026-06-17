import time
from pathlib import Path

from playwright.sync_api import Page

DEBUG_DIR = Path(__file__).parent / "debug"


def salvar_estado(page: Page, rotulo: str) -> None:
    """Salva screenshot + HTML da página atual em bot/debug/, para diagnóstico de falhas."""
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    base = DEBUG_DIR / f"{ts}_{rotulo}"

    try:
        page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
    except Exception as exc:
        print(f"[debug] não consegui tirar screenshot: {exc}")

    try:
        base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        print(f"[debug] não consegui salvar HTML: {exc}")

    print(f"[debug] estado salvo em {base}.png / {base}.html")
