import os
import re

import httpx


class ProviderError(Exception):
    pass


def _extract_letter(text: str) -> str:
    match = re.search(r"\b([a-hA-H])\b", text.strip())
    if not match:
        raise ProviderError(f"Resposta da IA não contém uma letra válida: {text!r}")
    return match.group(1).lower()


def _build_prompt(pergunta: str, alternativas: list[str]) -> str:
    letras = "abcdefgh"
    linhas = [f"{letras[i]}) {texto}" for i, texto in enumerate(alternativas)]
    return (
        f"Enunciado: {pergunta}\n\n"
        f"Alternativas:\n" + "\n".join(linhas) + "\n\n"
        "Responda APENAS com a letra da alternativa correta (ex: a)."
    )


class _ChatCompletionProvider:
    """Provider genérico para APIs compatíveis com o formato chat/completions da OpenAI."""

    name = "generic"

    def __init__(self, base_url: str, api_key_env: str, model_env: str, default_model: str):
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env, "")
        self.model = os.getenv(model_env, default_model)

    def ask(self, pergunta: str, alternativas: list[str]) -> str:
        if not self.api_key:
            raise ProviderError(f"{self.name}: API key não configurada")

        prompt = _build_prompt(pergunta, alternativas)
        try:
            response = httpx.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name}: erro de requisição: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"{self.name}: resposta inesperada: {data}") from exc

        return _extract_letter(content)


class GroqProvider(_ChatCompletionProvider):
    name = "groq"

    def __init__(self):
        super().__init__(
            base_url="https://api.groq.com/openai/v1/chat/completions",
            api_key_env="GROQ_API_KEY",
            model_env="GROQ_MODEL",
            default_model="llama-3.3-70b-versatile",
        )


class OpenRouterProvider(_ChatCompletionProvider):
    name = "openrouter"

    def __init__(self):
        super().__init__(
            base_url="https://openrouter.ai/api/v1/chat/completions",
            api_key_env="OPENROUTER_API_KEY",
            model_env="OPENROUTER_MODEL",
            default_model="meta-llama/llama-3.3-70b-instruct:free",
        )


class OpenAIProvider(_ChatCompletionProvider):
    name = "openai"

    def __init__(self):
        super().__init__(
            base_url="https://api.openai.com/v1/chat/completions",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            default_model="gpt-4o-mini",
        )


PROVIDERS = {
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "openai": OpenAIProvider,
}


def ask_ai(pergunta: str, alternativas: list[str], provider_order: list[str]) -> str:
    """Tenta cada provider na ordem configurada, retorna a letra da alternativa (ex: 'b')."""
    erros = []
    for nome in provider_order:
        provider_cls = PROVIDERS.get(nome)
        if provider_cls is None:
            continue
        try:
            provider = provider_cls()
            return provider.ask(pergunta, alternativas)
        except ProviderError as exc:
            erros.append(str(exc))
            continue

    raise ProviderError(f"Nenhum provider respondeu. Erros: {erros}")
