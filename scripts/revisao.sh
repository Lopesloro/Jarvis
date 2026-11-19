#!/usr/bin/env bash
# Revisão obrigatória pelo /harvey: nenhum commit chega ao GitHub sem estar coberto por uma.
#
#   scripts/revisao.sh pedir            mostra o que falta revisar e gera o pedido para o /harvey
#   scripts/revisao.sh aprovar "nota"   registra que o /harvey aprovou tudo até o HEAD
#   scripts/revisao.sh checar [base] [topo]
#                                       falha se houver commit depois da última revisão
#
# Uma revisão é um commit vazio com o trailer "Revisado-por: /harvey". Ela cobre todos os
# commits anteriores a ela. O pre-push e o CI exigem que o topo do que vai para o GitHub
# seja uma revisão.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
TRAILER="Revisado-por: /harvey"

ultima_revisao() {
  git log --format=%H --grep="^${TRAILER}$" -n 1 "${1:-HEAD}" 2>/dev/null || true
}

pendentes() {  # commits depois da última revisão (até $1)
  local topo="${1:-HEAD}" rev
  rev=$(ultima_revisao "$topo")
  if [ -n "$rev" ]; then git rev-list "$rev..$topo"; else git rev-list "$topo"; fi
}

case "${1:-}" in
  pedir)
    rev=$(ultima_revisao)
    intervalo=${rev:+$rev..}HEAD
    n=$(pendentes | wc -l | tr -d ' ')
    if [ "$n" = 0 ]; then echo "Nada pendente: tudo até o HEAD já foi revisado."; exit 0; fi
    saida=.git/REVISAO_PENDENTE.md
    {
      echo "Revise os commits ${intervalo} do Jarvis usando orquestracao/harvey-gate.md."
      echo "Classifique cada achado como BLOQUEANTE, IMPORTANTE ou MENOR, com arquivo e linha."
      echo "Termine com APROVADO ou REPROVADO."
      echo
      echo "## Commits ($n)"
      git log --format='- %h %s' "$intervalo"
      echo
      echo "## Arquivos"
      git diff --stat "${rev:-$(git hash-object -t tree /dev/null)}" HEAD
    } > "$saida"
    cat "$saida"
    echo
    echo "→ Cole o texto acima no /harvey (ou: /harvey \$(cat $saida))."
    echo "→ Corrija os BLOQUEANTES e IMPORTANTES; depois: scripts/revisao.sh aprovar \"resumo\""
    ;;
  aprovar)
    nota="${2:?uso: scripts/revisao.sh aprovar \"resumo da revisão\"}"
    n=$(pendentes | wc -l | tr -d ' ')
    [ "$n" = 0 ] && { echo "Nada pendente para aprovar."; exit 1; }
    git diff --quiet && git diff --cached --quiet || {
      echo "Há mudanças não commitadas: commite antes de aprovar."; exit 1; }
    rev=$(ultima_revisao)
    git commit --allow-empty -q -m "Revisão /harvey: $n commit(s)" -m "$nota" \
      --trailer "Revisao-intervalo: ${rev:-inicio}..$(git rev-parse --short HEAD)" \
      --trailer "$TRAILER"
    echo "✓ Revisão registrada ($n commits)."
    ;;
  checar)
    base="${2:-}" topo="${3:-HEAD}"
    faltando=$(pendentes "$topo")
    if [ -n "$base" ] && [ -n "$faltando" ]; then
      faltando=$(git rev-list "$base..$topo" | grep -Fx -f <(echo "$faltando") || true)
    fi
    if [ -n "$faltando" ]; then
      echo "✗ Commits sem revisão do /harvey:"
      git log --no-walk --format='  %h %s' $faltando
      echo "Rode: scripts/revisao.sh pedir   (e depois aprovar)"
      exit 1
    fi
    echo "✓ Tudo coberto por revisão do /harvey."
    ;;
  *)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
