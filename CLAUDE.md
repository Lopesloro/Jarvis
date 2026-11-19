# Instruções para agentes (FCC / ECC / Claude Code)

## Antes de qualquer tarefa
1. Leia `docs/01-arquitetura.md`, `docs/03-motor-prioridade.md` e o arquivo da fase em
   `orquestracao/fases/`.
2. Confira o contrato em `contracts/`. Se precisar mudar um modelo, mude `core/src/jarvis_core/models.py`
   e rode `scripts/gerar_contratos.py`. Nunca edite `contracts/` à mão.

## Regras
- **Nunca** implemente envio automático de mensagem ou e-mail. Envio só existe atrás de
  `JARVIS_WA_ALLOW_SEND=1` e, depois da v1, com aprovação item a item.
- **Nunca** versione segredos, `*.db`, `auth/`, `.env` ou dados reais de conversa/e-mail.
- Todo sinal novo de prioridade: entrada na tabela de `docs/03-motor-prioridade.md` + teste.
- Interface: escala de cinza, sem azul. Siga `web/DESIGN.md`.
- Textos de interface e documentação em português do Brasil.
- Python: `ruff check` e `ruff format` limpos; tipagem em tudo que é público.
- TypeScript: `strict`, sem `any` novo.
- Cada PR fecha uma tarefa do roadmap (`F1.2`, `F2.3`…) e cita o número no título.

## Comandos
```bash
git config core.hooksPath .githooks   # uma vez por clone: liga os portões locais
scripts/checar.sh                     # tudo que o CI roda
```

## Portões de revisão (100% do código passa por eles)
1. **pre-commit:** segredos e arquivos proibidos, `ruff`, formato, testes com **100% de
   cobertura de linhas e ramos** (Python e ponte), contratos em dia. Falhou, não commita.
2. **Revisão do /harvey:** `scripts/revisao.sh pedir` gera o pedido com todos os commits
   ainda não revisados; cole no `/harvey` com `orquestracao/harvey-gate.md`. Corrija os
   achados BLOQUEANTES e IMPORTANTES e só então rode `scripts/revisao.sh aprovar "resumo"`.
3. **pre-push:** recusa o push se algum commit não estiver coberto por uma revisão.
4. **CI:** repete tudo, inclusive a checagem de revisão, então `--no-verify` não fura nada.

Agentes **não** rodam `revisao.sh aprovar` sozinhos: a aprovação é do /harvey.
Não use `# pragma: no cover` nem exclusões de cobertura novas sem um ADR justificando.
