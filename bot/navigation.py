from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


def ir_para_curso(page: Page, config: dict, course_id: str) -> None:
    url = config["ead_course_url_template"].format(course_id=course_id)
    page.goto(url)
    page.wait_for_load_state("networkidle")


def listar_modulos(page: Page, config: dict):
    """Retorna o locator dos módulos (cards) listados na página do curso.

    Se nenhum módulo aparecer dentro do timeout (curso com layout diferente,
    bloqueado, vazio etc.), retorna um locator vazio em vez de propagar erro.
    """
    sel = config["selectors"]["module_card"]
    try:
        page.wait_for_selector(sel, timeout=15000)
    except PlaywrightTimeoutError:
        pass
    return page.locator(sel)


def abrir_modulo(page: Page, modulos_locator, indice: int) -> None:
    modulos_locator.nth(indice).click()
    page.wait_for_load_state("networkidle")
    # a sidebar de tópicos é renderizada pelo Vue após a navegação client-side,
    # então esperamos o elemento aparecer em vez de confiar só no networkidle
    try:
        page.wait_for_selector("div.list-item-topic", timeout=15000)
    except PlaywrightTimeoutError:
        pass


def listar_topicos_exercicios(page: Page, config: dict):
    """Retorna os locators dos itens de tópico cujo título é 'Exercícios' (dentro de um módulo aberto)."""
    sel = config["selectors"]
    titulo = sel["exercicios_topic_title"]
    return page.locator(f'{sel["topic_list_item"]}:has-text("{titulo}")')


def abrir_topico(page: Page, config: dict, locator, indice: int) -> None:
    locator.nth(indice).click()
    page.wait_for_load_state("networkidle")

    # O conteúdo do tópico usa Vuetify <v-lazy>, que só renderiza quando o
    # elemento entra de fato na viewport (IntersectionObserver). O clique no
    # item da sidebar nem sempre rola o suficiente para disparar isso, então
    # forçamos um scroll explícito até o heading do tópico.
    titulo = config["selectors"]["exercicios_topic_title"]
    try:
        heading = page.locator(f'h2:has-text("{titulo}")').first
        heading.scroll_into_view_if_needed(timeout=10000)
        page.wait_for_timeout(800)
    except PlaywrightTimeoutError:
        pass

    try:
        page.wait_for_selector(config["selectors"]["question_wrapper"], timeout=15000)
    except PlaywrightTimeoutError:
        # ainda não renderizou: tenta um pequeno scroll adicional para forçar
        # o IntersectionObserver, então espera de novo
        try:
            page.mouse.wheel(0, 300)
            page.wait_for_selector(config["selectors"]["question_wrapper"], timeout=10000)
        except PlaywrightTimeoutError:
            pass
