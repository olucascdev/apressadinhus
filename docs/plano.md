# Plano — Bot de estudo para quizzes da Plataforma A (EAD)

> Contexto: bot **local**, de uso pessoal, para responder quizzes de revisão (sem valor de nota) dos módulos da plataforma EAD da faculdade, usando Playwright + IA. Login é automatizado (sem captcha no formulário).

## 1. Objetivo

Dado uma lista de IDs de cursos, o bot deve:

1. Logar automaticamente no portal acadêmico.
2. Abrir a Plataforma A (EAD).
3. Para cada curso da lista: abrir, percorrer todos os módulos, abrir o tópico "Exercícios" de cada módulo, ler as 5 questões, perguntar a uma IA, clicar na alternativa sugerida e confirmar.
4. Ao terminar todos os módulos de um curso, passar para o próximo ID da lista.

## 2. Stack

- **Linguagem**: Python (ou Node — definir conforme preferência; exemplos abaixo em Python).
- **Automação de navegador**: Playwright (Chromium), sessão persistente via `storage_state` para evitar logar a cada execução.
- **IA**: camada abstrata com providers plugáveis — OpenRouter, Groq, OpenAI (gpt). Configurável via `.env` (chave de API + modelo + ordem de fallback).
- **Config**: arquivo `config.yaml`/`config.json` com lista de course IDs, credenciais (via `.env`, nunca hardcoded) e seletores.

## 3. Fluxo detalhado

### 3.1 Login (automatizado)

URL: `https://<portal-academico>/index.xhtml` (página JSF/RichFaces).

Campos confirmados em `pagina_Login.html`:
- Usuário: `#form\:usuario`
- Senha: `#form\:senha`
- Botão: `#form\:loginBtn\:loginBtn`

Passos:
1. `page.goto(LOGIN_URL)`
2. `page.fill('#form\\:usuario', USUARIO)`
3. `page.fill('#form\\:senha', SENHA)`
4. `page.click('#form\\:loginBtn\\:loginBtn')`
5. Aguardar navegação/elemento pós-login.
6. Salvar `storage_state` em disco (`auth.json`) para reuso nas próximas execuções (evita logar de novo).

### 3.2 Acessar a Plataforma A (EAD)

O link `#clinkPlataformaA` dispara um `RichFaces.ajax` que normalmente abre nova aba/janela. Duas opções:
- **Opção A (mais simples)**: ignorar esse botão e navegar direto para `https://univc.grupoa.education/plataforma/my-enrollments/courses`, já que a sessão (cookie) deve ser compartilhada por domínio/SSO. **Precisa validar isso na prática** — pode haver um redirecionamento SSO que só ocorre clicando o botão.
- **Opção B**: clicar o botão, capturar o evento `page.on("popup")` do Playwright para pegar a nova aba/contexto e continuar nela.

➡ Ação no dia da implementação: testar Opção A primeiro; se a sessão não for válida direto na URL, cair para Opção B.

### 3.3 Navegar pelos cursos

Para cada `course_id` na lista configurada:
```
https://univc.grupoa.education/plataforma/course/{course_id}
```
Listar os módulos da página (estrutura Vuetify `v-list-item`, mesma família de classes do sidebar de tópicos já mapeado: `.list-item-topic`).

### 3.4 Abrir módulo → localizar "Exercícios"

Dentro de cada módulo, é uma SPA (Vue/Nuxt) com sidebar de tópicos — o item já mapeado em `ideia.md`:
```html
<div class="list-item-topic ..." title="Exercícios">...<span class="list-topic-title">Exercícios</span>...</div>
```
Seletor: `page.click('div.list-item-topic:has-text("Exercícios")')`.

**Importante (achado na análise)**: a tela real de pergunta/alternativas **não aparece no HTML estático salvo** (`dentro_do_modulo.html`) — ela só deve ser renderizada após o clique em "Exercícios", carregada via chamada à API interna da SPA. Isso significa que os seletores de pergunta/alternativa/botão "confirmar" **ainda precisam ser capturados ao vivo**, abrindo o DevTools no navegador real durante uma sessão de teste.

### 3.5 Extrair pergunta e alternativas

Passo manual de descoberta (pré-requisito antes de codar esta parte):
1. Abrir um módulo de exemplo, abrir DevTools → aba Network, clicar em "Exercícios".
2. Identificar se a pergunta vem por uma chamada XHR/fetch (JSON) ou é renderizada direto no DOM.
   - Se vier por **JSON da API**: o bot pode interceptar a resposta via `page.on("response")` — mais robusto e rápido que parsear HTML.
   - Se for **DOM puro**: usar `page.locator(...)` para extrair `textContent` do enunciado e de cada alternativa (provavelmente dentro de `v-radio`/`v-list-item` do Vuetify).
3. Mapear o seletor do botão "Confirmar/Responder" e o de "Próxima questão".

### 3.6 Perguntar à IA

Prompt sugerido (a calibrar):
```
Enunciado: {pergunta}
Alternativas:
A) {opcao_a}
B) {opcao_b}
C) {opcao_c}
D) {opcao_d}

Responda APENAS com a letra da alternativa correta.
```
Camada de provider:
```python
def ask_ai(pergunta, alternativas) -> str:
    for provider in [groq, openrouter, openai]:
        try:
            return provider.ask(pergunta, alternativas)
        except ProviderError:
            continue
    raise RuntimeError("Nenhum provider respondeu")
```
Fallback entre providers evita travar o bot se uma API estiver fora do ar / sem créditos.

### 3.7 Clicar na alternativa e confirmar

- Mapear texto da resposta da IA (ex.: "B") para o elemento correspondente na página (por posição ou por texto da alternativa, comparando string).
- Clicar, confirmar, aguardar feedback (correto/errado) — logar resultado (acertou/errou) para você acompanhar a taxa de acerto da IA.
- Repetir até as 5 questões do módulo.

### 3.8 Avançar

- Fechar/voltar do tópico "Exercícios" → próximo módulo da sidebar.
- Quando não houver mais módulos → voltar para `my-enrollments/courses` → próximo `course_id` da lista.
- Ao terminar todos os IDs configurados → finalizar com log-resumo (cursos/módulos processados, taxa de acerto).

## 4. Estrutura de arquivos sugerida

```
apressadinhus/
  bot/
    main.py              # orquestrador do fluxo (login → cursos → módulos → exercícios)
    login.py             # automação do login + persistência de storage_state
    navigation.py        # navegação entre cursos/módulos
    quiz.py              # extração de pergunta/alternativas + clique na resposta
    ai_providers/
      __init__.py
      groq_provider.py
      openrouter_provider.py
      openai_provider.py
    config.yaml           # lista de course_ids, seletores, ordem de providers
    .env                  # credenciais e API keys (git-ignored)
  docs/
    ideia.md
    plano.md
```

## 5. Riscos / pontos de atenção

- **Validar de fato que os quizzes não valem nota** — se em algum curso isso mudar (prova valendo nota), o bot não deve ser usado lá.
- Mudança de versão do front (Vuetify/Nuxt) pode quebrar seletores — isolar seletores em `config.yaml` facilita manutenção.
- Tratar timeouts/erros de rede da plataforma e das APIs de IA (retry com backoff).
- Rate limit das APIs de IA gratuitas (Groq/OpenRouter free tier) — adicionar delay entre chamadas se necessário.
- Guardar `.env` e `auth.json` fora do controle de versão (gitignore).

## 6. Próximos passos imediatos

1. **Descoberta ao vivo**: abrir DevTools no módulo real, capturar os seletores/JSON da tela de exercícios (passo 3.5) — sem isso não dá para codar a parte mais importante.
2. Validar se a navegação direto por URL mantém a sessão (passo 3.2, Opção A) ou se precisa do fluxo de popup (Opção B).
3. Criar protótipo do login automatizado + salvar `storage_state`.
4. Criar a camada de providers de IA com fallback.
5. Integrar tudo no fluxo principal (`main.py`) para 1 curso/1 módulo antes de generalizar para a lista completa.
