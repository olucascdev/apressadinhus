# Apressadinhus

Bot local de apoio aos estudos para a plataforma EAD da faculdade ("Plataforma A" / Grupo A). Ele navega pelos seus cursos, abre os quizzes de revisão de cada módulo (os exercícios **sem valor de nota**, usados só para fixar conteúdo) e usa uma IA para sugerir/marcar a resposta — tudo rodando no seu navegador local, com a sua própria sessão.

> ⚠️ Use isso só para quizzes de prática que não contam nota. Não foi feito (e não deve ser usado) para responder provas avaliativas.

## Como funciona

1. Faz login no portal acadêmico (JSF/RichFaces) com suas credenciais.
2. Abre a Plataforma A através do botão de SSO, capturando a sessão.
3. Para cada curso configurado: entra, percorre todos os módulos, abre o tópico "Exercícios" de cada um.
4. Extrai o enunciado e as alternativas da questão (scraping local, via Playwright).
5. Manda para uma IA (OpenAI, Groq ou OpenRouter, com fallback entre elas) e pede a alternativa correta.
6. Clica na alternativa sugerida, confere o feedback que a própria plataforma mostra (certo/errado) e avança.
7. Detecta questões já respondidas antes (gabarito já revelado na tela) e pula em vez de reenviar.
8. Ao terminar os módulos de um curso, passa para o próximo da lista.

## Estrutura do projeto

```
apressadinhus/
  bot/                  # bot em Python (Playwright)
    main.py             # orquestrador principal
    login.py            # login no portal + handoff para a Plataforma A
    navigation.py        # navegação entre curso → módulo → tópico
    quiz.py              # extração de pergunta/alternativas e resposta
    ai_providers/        # camada de IA com fallback (OpenAI/Groq/OpenRouter)
    config.yaml           # seletores, IDs de curso, ordem dos providers
    .env                  # credenciais e chaves de API (não versionado)
  cli/                   # CLI em Go para configurar tudo interativamente
  setup.sh                # builda e abre o CLI
  install.sh              # instalador one-shot (clona + configura tudo)
  docs/                   # notas de planejamento
```

## Instalação rápida

Se você já tem `git`, `go` e `python3` instalados, um único comando configura tudo (clona o repositório, monta o ambiente Python, instala o Chromium do Playwright, builda o CLI) **e já abre o configurador**:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/olucascdev/apressadinhus/main/install.sh)"
```

> Use exatamente esse formato (`bash -c "$(curl ...)"`), não `curl ... | bash` — com pipe o terminal interativo do final não funciona (dá erro de EOF), porque o stdin fica ocupado pelo próprio curl.

Isso deixa o comando `apressadinhus` disponível no seu terminal (em `~/.local/bin`) para usar depois sempre que quiser:

```bash
apressadinhus
```

### Instalação manual (sem o script)

```bash
git clone git@github.com:olucascdev/apressadinhus.git
cd apressadinhus/bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
cd ../cli
go build -o apressadinhus-config .
./apressadinhus-config
```

## Usando o configurador

Rodar `apressadinhus` (ou `./setup.sh` dentro do repo) abre um CLI interativo que pergunta:

- URL de login do portal, usuário e senha (senha mascarada, nunca aparece na tela).
- Qual provedor de IA é o principal e quais usar como fallback (setas para escolher, espaço para marcar múltiplos).
- Qual modelo usar de cada provedor (ex: `gpt-4.1-mini`, `gpt-4o`, `llama-3.3-70b-versatile`...).
- Os IDs dos cursos a processar.
- Se quer rodar o navegador em modo headless.

No final, ele já oferece para rodar o bot na hora. Tudo é gravado em `bot/.env` (credenciais/chaves) e `bot/config.yaml` (IDs de curso, provider de IA, etc.) — esses dois arquivos **não são versionados** (estão no `.gitignore`).

## Requisitos

- [Go](https://go.dev/dl/) 1.21+
- Python 3.10+
- Pelo menos uma chave de API de IA: [OpenAI](https://platform.openai.com/api-keys), [Groq](https://console.groq.com/keys) (tem camada gratuita) ou [OpenRouter](https://openrouter.ai/keys) (tem modelos gratuitos)

## Avisos

- A sessão de login fica salva localmente em `bot/auth.json` para não precisar logar de novo a cada execução — não compartilhe esse arquivo.
- Em caso de falha ao carregar uma tela de exercício, o bot salva screenshot + HTML em `bot/debug/` para facilitar o diagnóstico.
