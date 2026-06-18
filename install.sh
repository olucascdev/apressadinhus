#!/usr/bin/env bash
# Instalador do Apressadinhus.
#
# Clona o repositório (ou atualiza, se já existir), prepara o ambiente
# Python do bot e deixa o comando `apressadinhus` disponível no PATH,
# já abrindo o configurador no final.
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/olucascdev/apressadinhus/main/install.sh | bash
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

# Quando o instalador é rodado via "curl ... | bash", o stdin do script é o
# próprio pipe do curl, não o terminal — então não dá para abrir um CLI
# interativo aqui (ele leria EOF na hora). Nesse caso, tentamos reabrir o
# terminal do usuário (/dev/tty); se não der, só orientamos a rodar depois.
if [ -t 1 ] && [ -r /dev/tty ]; then
  info "Abrindo o configurador..."
  exec "$BIN_DIR/apressadinhus" < /dev/tty
else
  echo
  echo "Rode \"apressadinhus\" para abrir o configurador (pode ser preciso abrir um novo terminal ou rodar: source ~/.bashrc)."
fi
