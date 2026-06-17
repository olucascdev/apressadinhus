#!/usr/bin/env bash
# Builda (se preciso) e abre o configurador interativo do bot.
# Uso: ./setup.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/cli"

if ! command -v go >/dev/null 2>&1; then
  echo "Erro: Go não está instalado. Instale em https://go.dev/dl/ e rode de novo." >&2
  exit 1
fi

if [ ! -f go.sum ]; then
  go mod tidy
fi

go build -o apressadinhus-config .
./apressadinhus-config
