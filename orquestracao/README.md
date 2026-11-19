# Orquestração FCC + ECC + /harvey

## Papéis
| Papel | Quem | Faz |
|---|---|---|
| **Maestro** | Você (ou a aba principal do FCC) | Abre as fases, distribui as trilhas, aprova merges |
| **Executores** | Abas/subagentes do FCC (Claude Code via Free Claude Code → NVIDIA NIM, modelos fortes) | Implementam uma trilha cada, numa branch própria |
| **Especialistas** | Skills do ECC (`~/ECC/skills`) | Padrões de cada assunto (FastAPI, segurança, testes…) |
| **Revisor** | `/harvey` | Revisa cada PR e faz o gate de fim de fase |

## Fluxo por fase
```
Maestro lê fases/Fx.md
   │
   ├── trilha A ──▶ executor 1 (branch fx-a) ─┐
   ├── trilha B ──▶ executor 2 (branch fx-b) ─┼──▶ PR ──▶ /harvey revisa ──▶ merge
   └── trilha C ──▶ executor 3 (branch fx-c) ─┘
                                                     │
                              fim da fase ──▶ /harvey gate (harvey-gate.md) ──▶ próxima fase
```

## Como abrir uma trilha no FCC
1. `git worktree add ../jarvis-fx-a -b fx-a` (uma pasta por executor evita conflito)
2. Abra o FCC nessa pasta e cole o bloco **"Prompt da trilha"** do arquivo da fase.
3. O executor termina com testes verdes e abre o PR.
4. Na aba do revisor: `/harvey revisar PR #N` usando `harvey-gate.md`.

## Paralelismo seguro
As trilhas de cada fase foram divididas para **não mexer nos mesmos arquivos**. Quando
duas trilhas precisam de um contrato novo, a trilha A cria o contrato primeiro e as outras
partem da branch dela.

## Arquivos
- `fases/F1-conectores.md` … `fases/F5-entrega.md`: trilhas, skills do ECC e prompts prontos
- `harvey-gate.md`: checklist de revisão por PR e por fase
