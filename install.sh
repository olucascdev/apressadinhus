#!/usr/bin/env bash
# Instalador do Apressadinhus.
#
# Clona o repositório (ou atualiza, se já existir), prepara o ambiente
# Python do bot, builda o CLI e já abre o configurador no final.
#
# IMPORTANTE: rode com "bash -c", não com "| bash" — com pipe o stdin do
# script é consumido pelo próprio curl e o configurador interativo do final
# não consegue ler suas respostas (dá erro de EOF). Com "bash -c" o stdin
# continua sendo o seu terminal de verdade.
#
# Uso:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/olucascdev/apressadinhus/main/install.sh)"
set -euo pipefail

REPO_URL="git@github.com:olucascdev/apressadinhus.git"
REPO_URL_HTTPS="https://github.com/olucascdev/apressadinhus.git"
INSTALL_DIR="${APRESSADINHUS_DIR:-$HOME/.apressadinhus}"
BIN_DIR="$HOME/.local/bin"

info()  { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
erro()  { printf '\033[1;31merro:\033[0m %s\n' "$1" >&2; exit 1; }

command -v git >/dev/null 2>&1 || erro "git não está instalado."
command -v go  >/dev/null 2>&1 || erro "Go não está instalado (https://go.dev/dl/)."
command -v python3 >/dev/null 2>&1 || erro "python3 não está instalado."

if [ -d "$INSTALL_DIR/.git" ]; then
  info "Já existe uma instalação em $INSTALL_DIR, atualizando..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Clonando o repositório em $INSTALL_DIR..."
  if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
    info "Clone via SSH falhou, tentando HTTPS..."
    git clone "$REPO_URL_HTTPS" "$INSTALL_DIR"
  fi
fi

cd "$INSTALL_DIR/bot"
if [ ! -d .venv ]; then
  info "Criando o ambiente virtual do Python..."
  python3 -m venv .venv
fi

info "Instalando dependências Python..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

info "Instalando o navegador do Playwright (Chromium)..."
./.venv/bin/python -m playwright install chromium

info "Compilando o CLI de configuração..."
cd "$INSTALL_DIR/cli"
go build -o apressadinhus-config .

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/apressadinhus" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$INSTALL_DIR/setup.sh" "\$@"
EOF
chmod +x "$BIN_DIR/apressadinhus"

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
  info "Adicione $BIN_DIR ao seu PATH (ex: no ~/.bashrc ou ~/.zshrc):"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi

info "Instalação concluída!"

if [ -t 0 ]; then
  info "Abrindo o configurador..."
  exec "$BIN_DIR/apressadinhus"
fi

echo
echo "Agora rode (em um terminal normal, sem pipe):"
echo
echo "  apressadinhus"
echo
echo "(se o comando não for encontrado, abra um novo terminal ou rode: source ~/.bashrc)"
