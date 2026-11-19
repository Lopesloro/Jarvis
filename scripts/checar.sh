#!/usr/bin/env bash
# Todas as checagens automáticas (as mesmas do CI). Usado pelo pre-commit.
#   scripts/checar.sh          tudo
#   scripts/checar.sh rapido   sem a ponte (quando só Python mudou)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
falhou=0
passo() { printf '\n▶ %s\n' "$1"; }

passo "segredos e arquivos proibidos no que vai ser commitado"
proibidos=$(git diff --cached --name-only --diff-filter=AM | grep -E '(^|/)(\.env|auth/|.*\.db(-wal|-shm)?$|jarvis\.toml$|env$)' || true)
if [ -n "$proibidos" ]; then echo "✗ arquivos que nunca vão para o git:"; echo "$proibidos"; falhou=1; fi
if git diff --cached -U0 | grep -E '^\+' | grep -v '^+++' \
   | grep -nE '(JARVIS_TOKEN=[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[bp]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{30,})'; then
  echo "✗ parece haver um segredo no diff"; falhou=1
fi

passo "Python: lint, formato, testes com cobertura de 100%"
(cd core && uv run --extra dev ruff check -q src tests && uv run --extra dev ruff format --check -q src tests \
  && uv run --extra dev pytest -q -p no:cacheprovider) || falhou=1

passo "contratos em dia com o código"
(cd core && uv run --extra dev --with pyyaml python ../scripts/gerar_contratos.py) \
  && git diff --quiet -- contracts || { echo "✗ contracts/ desatualizado: regere e commite"; falhou=1; }

if [ "${1:-}" != rapido ]; then
  passo "Ponte: tipos e testes com cobertura de 100%"
  if [ -d bridge/whatsapp/node_modules ]; then
    (cd bridge/whatsapp && npm test --silent) || falhou=1
  else
    echo "  (pulado: rode npm ci em bridge/whatsapp)"
  fi
fi

[ $falhou = 0 ] && echo -e "\n✓ todas as checagens passaram" || { echo -e "\n✗ checagens falharam"; exit 1; }
