// CLI de configuração do APRESSADINHUS — o bot de exercícios.
//
// Pergunta interativamente login do portal, chaves de IA e os IDs dos
// cursos, e grava isso em bot/.env e bot/config.yaml — sem precisar editar
// os arquivos na mão.
package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/AlecAivazis/survey/v2"
	"github.com/pterm/pterm"
	"golang.org/x/term"
)

const (
	urlLoginPadrao = "https://sei.ivc.br/index.xhtml"

	corReset    = "\033[0m"
	corTitulo   = "\033[1;36m"
	corOk       = "\033[1;32m"
	corAviso    = "\033[1;33m"
	corCampo    = "\033[1;37m"
	corDestaque = "\033[1;35m"
	corApagado  = "\033[2m"
)

type respostas struct {
	loginURL        string
	usuario         string
	senha           string
	openaiKey       string
	openaiModel     string
	groqKey         string
	groqModel       string
	openrouterKey   string
	openrouterModel string
	providerOrder   []string
	courseIDs       []string
	headless        bool
}

var nomeProvider = map[string]string{
	"openai":     "OpenAI (ChatGPT)",
	"groq":       "Groq (gratuito)",
	"openrouter": "OpenRouter (gratuito)",
}

var modelosOpenAI = []string{
	"gpt-4.1",
	"gpt-4.1-mini",
	"gpt-4.1-nano",
	"gpt-4o",
	"gpt-4o-mini",
	"o4-mini",
}

var modelosGroq = []string{
	"llama-3.3-70b-versatile",
	"llama-3.1-8b-instant",
	"mixtral-8x7b-32768",
}

var modelosOpenRouter = []string{
	"meta-llama/llama-3.3-70b-instruct:free",
	"google/gemini-2.0-flash-exp:free",
	"deepseek/deepseek-chat:free",
}

func main() {
	leitor := bufio.NewReader(os.Stdin)

	botDir, err := localizarBotDir()
	if err != nil {
		fatal(err)
	}

	banner()
	fmt.Printf("  Configurando o bot em: %s%s%s\n\n", corCampo, botDir, corReset)

	r := respostas{}

	secao("Login do portal")
	r.loginURL = perguntar(leitor, "URL de login do portal acadêmico", urlLoginPadrao)
	r.usuario = perguntar(leitor, "Usuário do portal", "")
	r.senha = perguntarSenha(leitor, "Senha do portal (fica salva só localmente em .env, nunca commitar)")

	secao("Inteligência Artificial")
	r.providerOrder = perguntarProviders()

	for _, p := range r.providerOrder {
		switch p {
		case "openai":
			r.openaiKey = perguntar(leitor, "Chave de API da OpenAI", "")
			r.openaiModel = perguntarModelo("Qual modelo da OpenAI usar?", modelosOpenAI)
		case "groq":
			r.groqKey = perguntar(leitor, "Chave de API da Groq", "")
			r.groqModel = perguntarModelo("Qual modelo da Groq usar?", modelosGroq)
		case "openrouter":
			r.openrouterKey = perguntar(leitor, "Chave de API da OpenRouter", "")
			r.openrouterModel = perguntarModelo("Qual modelo da OpenRouter usar?", modelosOpenRouter)
		}
	}

	if len(r.providerOrder) == 0 {
		aviso("Nenhum provedor de IA selecionado — o bot não vai conseguir responder nada até você editar o .env/config.yaml depois.")
	}

	secao("Cursos")
	r.courseIDs = perguntarCourseIDs(leitor)

	secao("Execução")
	r.headless = perguntarConfirmacao("Rodar o navegador em modo invisível (headless)?", false)

	if err := gravarEnv(botDir, r); err != nil {
		fatal(err)
	}
	if err := atualizarConfigYaml(botDir, r); err != nil {
		fatal(err)
	}

	fmt.Println()
	ok(fmt.Sprintf("Tudo certo! Configuração gravada em %s e %s", filepath.Join(botDir, ".env"), filepath.Join(botDir, "config.yaml")))

	fmt.Println()
	if perguntarConfirmacao("Rodar o bot agora?", true) {
		rodarBot(botDir)
		return
	}

	fmt.Println(corApagado + "  Quando quiser rodar depois: cd bot && .venv/bin/python main.py" + corReset)
}

// rodarBot executa o bot usando o Python do venv dentro de bot/, herdando
// stdin/stdout/stderr para você ver o navegador e os logs em tempo real.
func rodarBot(botDir string) {
	python := filepath.Join(botDir, ".venv", "bin", "python")
	if _, err := os.Stat(python); err != nil {
		aviso(fmt.Sprintf("Não encontrei %s — crie o venv primeiro (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt).", python))
		return
	}

	secao("Rodando o bot")
	cmd := exec.Command(python, "main.py")
	cmd.Dir = botDir
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fatal(fmt.Errorf("o bot terminou com erro: %w", err))
	}
}

const bannerASCII = `  _                                     _ _       _
 /_\  _ __  _ __ ___  ___ ___  __ _  __| (_)_ __ | |__  _   _ ___
//_\\| '_ \| '__/ _ \/ __/ __|/ _` + "`" + ` |/ _` + "`" + ` | | '_ \| '_ \| | | / __|
/  _  \ |_) | | |  __/\__ \__ \ (_| | (_| | | | | | | | | |_| \__ \
\_/ \_/ .__/|_|  \___||___/___/\__,_|\__,_|_|_| |_|_| |_|\__,_|___/
      |_|                                                          `

// paletaArcoIris é a sequência de cores ANSI usada para pintar o banner em
// "rainbow", uma cor por coluna de caractere (estilo lolcat).
var paletaArcoIris = []string{
	"\033[1;31m", // vermelho
	"\033[1;33m", // amarelo
	"\033[1;32m", // verde
	"\033[1;36m", // ciano
	"\033[1;34m", // azul
	"\033[1;35m", // magenta
}

func imprimirArcoIris(texto string) {
	col := 0
	for _, linha := range strings.Split(texto, "\n") {
		for _, r := range linha {
			if r != ' ' {
				fmt.Print(paletaArcoIris[col%len(paletaArcoIris)])
			}
			fmt.Printf("%c", r)
			fmt.Print(corReset)
			col++
		}
		fmt.Println()
	}
}

func banner() {
	imprimirArcoIris(bannerASCII)
	fmt.Println()
	pterm.DefaultCenter.Println(pterm.Gray("configurador interativo do bot de exercícios"))
	fmt.Println()
}

func secao(titulo string) {
	fmt.Println()
	fmt.Println(corTitulo + "── " + titulo + " " + strings.Repeat("─", 40-len(titulo)) + corReset)
}

func ok(s string) {
	fmt.Println(corOk + "✔ " + s + corReset)
}

func aviso(s string) {
	fmt.Println(corAviso + "⚠ " + s + corReset)
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "\033[1;31merro: "+err.Error()+"\033[0m")
	os.Exit(1)
}

// localizarBotDir tenta achar a pasta bot/ tanto rodando da raiz do projeto
// quanto rodando de dentro de cli/.
func localizarBotDir() (string, error) {
	candidatos := []string{"bot", "../bot"}
	for _, c := range candidatos {
		if info, err := os.Stat(filepath.Join(c, "config.yaml")); err == nil && !info.IsDir() {
			return c, nil
		}
	}
	return "", fmt.Errorf("não encontrei bot/config.yaml (tentei: %s) — rode esse CLI de dentro da raiz do projeto ou de cli/", strings.Join(candidatos, ", "))
}

func perguntar(leitor *bufio.Reader, label, padrao string) string {
	if padrao != "" {
		fmt.Printf("%s%s%s [%s]: ", corCampo, label, corReset, padrao)
	} else {
		fmt.Printf("%s%s%s: ", corCampo, label, corReset)
	}
	linha, _ := leitor.ReadString('\n')
	linha = strings.TrimSpace(linha)
	if linha == "" {
		return padrao
	}
	return linha
}

// perguntarSenha lê a senha sem ecoar na tela (modo raw do terminal).
// Se a entrada não for um terminal real (ex: pipe), cai para leitura normal.
func perguntarSenha(leitor *bufio.Reader, label string) string {
	fmt.Printf("%s%s%s: ", corCampo, label, corReset)

	fd := int(os.Stdin.Fd())
	if !term.IsTerminal(fd) {
		linha, _ := leitor.ReadString('\n')
		return strings.TrimSpace(linha)
	}

	bytes, err := term.ReadPassword(fd)
	fmt.Println()
	if err != nil {
		aviso("não consegui ocultar a digitação, lendo em texto puro")
		linha, _ := leitor.ReadString('\n')
		return strings.TrimSpace(linha)
	}
	return strings.TrimSpace(string(bytes))
}

// perguntarProviders mostra um seletor com setinhas para o provedor
// principal, depois um multiselect (espaço para marcar, enter para
// confirmar) para os fallbacks, na ordem em que devem ser tentados.
func perguntarProviders() []string {
	todos := []string{"openai", "groq", "openrouter"}
	opcoes := make([]string, len(todos))
	for i, p := range todos {
		opcoes[i] = nomeProvider[p]
	}

	var principalLabel string
	perguntaPrincipal := &survey.Select{
		Message: "Qual provedor de IA é o principal (tentado primeiro)?",
		Options: opcoes,
		Default: nomeProvider["openai"],
	}
	if err := survey.AskOne(perguntaPrincipal, &principalLabel); err != nil {
		fatal(err)
	}

	principal := chaveDoLabel(principalLabel)

	var restantesLabels []string
	for _, p := range todos {
		if p != principal {
			restantesLabels = append(restantesLabels, nomeProvider[p])
		}
	}

	var fallbacksLabels []string
	perguntaFallback := &survey.MultiSelect{
		Message: "Quais outros usar como fallback? (espaço marca, enter confirma)",
		Options: restantesLabels,
	}
	if err := survey.AskOne(perguntaFallback, &fallbacksLabels); err != nil {
		fatal(err)
	}

	ordem := []string{principal}
	for _, label := range fallbacksLabels {
		ordem = append(ordem, chaveDoLabel(label))
	}
	return ordem
}

// perguntarModelo mostra um seletor com setinhas para escolher o modelo
// dentro da lista de modelos conhecidos do provedor.
func perguntarModelo(mensagem string, modelos []string) string {
	var escolha string
	prompt := &survey.Select{
		Message: mensagem,
		Options: modelos,
		Default: modelos[0],
	}
	if err := survey.AskOne(prompt, &escolha); err != nil {
		fatal(err)
	}
	return escolha
}

func chaveDoLabel(label string) string {
	for chave, l := range nomeProvider {
		if l == label {
			return chave
		}
	}
	return label
}

func perguntarConfirmacao(pergunta string, padrao bool) bool {
	resp := padrao
	prompt := &survey.Confirm{
		Message: pergunta,
		Default: padrao,
	}
	if err := survey.AskOne(prompt, &resp); err != nil {
		fatal(err)
	}
	return resp
}

func perguntarCourseIDs(leitor *bufio.Reader) []string {
	fmt.Println("Digite os IDs dos cursos, um por linha. Linha vazia para terminar.")
	var ids []string
	for {
		fmt.Printf("%sID do curso #%d (ou ENTER para terminar)%s: ", corCampo, len(ids)+1, corReset)
		linha, _ := leitor.ReadString('\n')
		linha = strings.TrimSpace(linha)
		if linha == "" {
			break
		}
		ids = append(ids, linha)
	}
	if len(ids) == 0 {
		aviso("Nenhum ID de curso informado — a lista ficará vazia, edite config.yaml depois se precisar.")
	}
	return ids
}

func gravarEnv(botDir string, r respostas) error {
	var b strings.Builder
	fmt.Fprintf(&b, "PORTAL_USUARIO=%s\n", r.usuario)
	fmt.Fprintf(&b, "PORTAL_SENHA=%s\n", r.senha)
	fmt.Fprintln(&b)
	fmt.Fprintf(&b, "OPENAI_API_KEY=%s\n", r.openaiKey)
	fmt.Fprintf(&b, "OPENAI_MODEL=%s\n", r.openaiModel)
	fmt.Fprintln(&b)
	fmt.Fprintf(&b, "GROQ_API_KEY=%s\n", r.groqKey)
	fmt.Fprintf(&b, "GROQ_MODEL=%s\n", r.groqModel)
	fmt.Fprintln(&b)
	fmt.Fprintf(&b, "OPENROUTER_API_KEY=%s\n", r.openrouterKey)
	fmt.Fprintf(&b, "OPENROUTER_MODEL=%s\n", r.openrouterModel)

	caminho := filepath.Join(botDir, ".env")
	return os.WriteFile(caminho, []byte(b.String()), 0600)
}

var (
	reLoginURL      = regexp.MustCompile(`(?m)^login_url:.*$`)
	reHeadless      = regexp.MustCompile(`(?m)^headless:.*$`)
	reCourseIDs     = regexp.MustCompile(`(?m)^course_ids:\n(?:[ \t]+-[^\n]*\n?)*`)
	reProviderOrder = regexp.MustCompile(`(?m)^ai_provider_order:\n(?:[ \t]+-[^\n]*\n?)*`)
)

// atualizarConfigYaml faz substituições pontuais no config.yaml existente
// (login_url, headless, course_ids, ai_provider_order), preservando o
// resto do arquivo (seletores, comentários etc.) como está.
func atualizarConfigYaml(botDir string, r respostas) error {
	caminho := filepath.Join(botDir, "config.yaml")
	conteudo, err := os.ReadFile(caminho)
	if err != nil {
		return err
	}
	texto := string(conteudo)

	texto = reLoginURL.ReplaceAllString(texto, fmt.Sprintf("login_url: %q", r.loginURL))
	texto = reHeadless.ReplaceAllString(texto, fmt.Sprintf("headless: %t", r.headless))

	var bloco strings.Builder
	bloco.WriteString("course_ids:\n")
	for _, id := range r.courseIDs {
		fmt.Fprintf(&bloco, "  - %q\n", id)
	}
	if len(r.courseIDs) == 0 {
		bloco.WriteString("  []\n")
	}
	texto = reCourseIDs.ReplaceAllString(texto, bloco.String())

	if len(r.providerOrder) > 0 {
		var blocoProviders strings.Builder
		blocoProviders.WriteString("ai_provider_order:\n")
		for _, p := range r.providerOrder {
			fmt.Fprintf(&blocoProviders, "  - %s\n", p)
		}
		texto = reProviderOrder.ReplaceAllString(texto, blocoProviders.String())
	}

	return os.WriteFile(caminho, []byte(texto), 0644)
}
