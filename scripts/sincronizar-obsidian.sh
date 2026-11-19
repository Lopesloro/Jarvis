#!/usr/bin/env bash
# Copia a documentação do Jarvis para o cofre do Obsidian (só docs: nunca dados, banco ou segredos).
# Roda sozinho depois de cada commit (.githooks/post-commit). Destino configurável:
#   JARVIS_COFRE=/caminho/para/_ai/projects/jarvis
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
DESTINO="${JARVIS_COFRE:-$HOME/Documents/Cofre/_ai/projects/jarvis}"
L="${JARVIS_COFRE_LINK:-_ai/projects/jarvis}"   # caminho dentro do cofre, para os [[links]]
[ -d "$(dirname "$DESTINO")" ] || exit 0   # cofre ausente nesta máquina: nada a fazer
mkdir -p "$DESTINO/docs" "$DESTINO/orquestracao"
cp -R docs/. "$DESTINO/docs/"
cp -R orquestracao/. "$DESTINO/orquestracao/"
cp README.md "$DESTINO/README-do-repositorio.md"
cp CLAUDE.md "$DESTINO/CLAUDE-do-repositorio.md"
{
  echo "---"
  echo "status: em desenvolvimento"
  echo "repositorio: ~/jarvis"
  echo "atualizado: $(date '+%Y-%m-%d %H:%M')"
  echo "commit: $(git log -1 --format='%h %s')"
  echo "---"
  echo "# Projeto: Jarvis — assistente pessoal (agenda, Gmail, WhatsApp)"
  echo
  echo "> Cópia automática da documentação do repositório. **Não edite aqui:** edite em"
  echo "> \`~/jarvis\` e faça commit; esta pasta é regravada a cada commit."
  echo
  echo "## Revisão"
  scripts/revisao.sh checar 2>/dev/null | sed 's/^/    /' || true
  echo
  echo "## Últimos commits"
  git log -8 --format='- %h %s (%cr)'
  echo
  echo "## Documentação"
  echo "- [[$L/docs/README|Índice]] · [[$L/docs/00-visao|Visão]] · [[$L/docs/01-arquitetura|Arquitetura]] · [[$L/docs/02-roadmap|Roadmap]]"
  echo "- [[$L/docs/03-motor-prioridade|Motor de prioridade]] · [[$L/docs/04-seguranca-privacidade|Segurança]] · [[$L/docs/05-revisao-openjarvis|Revisão do OpenJarvis]]"
  echo "- Decisões: $(ls docs/adr | sed 's/\.md$//' | sed "s#.*#[[$L/docs/adr/&]]#" | paste -sd ' ' -)"
  echo "- Execução: [[$L/orquestracao/README|Orquestração FCC/ECC]] · [[$L/orquestracao/harvey-gate|Gate do /harvey]]"
} > "$DESTINO/estado.md"
echo "✓ documentação copiada para $DESTINO"
