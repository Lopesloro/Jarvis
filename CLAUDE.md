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
cd core && uv sync --extra dev && uv run pytest && uv run ruff check src tests
cd bridge/whatsapp && npm ci && npm test
```

## Gate de fase
No fim de cada fase, rode `/harvey` com o checklist de `orquestracao/harvey-gate.md`. Achado
**bloqueante** = a fase não fecha.
