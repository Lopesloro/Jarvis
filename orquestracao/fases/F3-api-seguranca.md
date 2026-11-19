# F3 · API e segurança

Skills ECC: `fastapi-patterns`, `api-design`, `agent-security-hardening`, `security-review`,
`security-scan`, `web-perimeter-owasp-2025-audit`.

| Trilha | Escopo |
|---|---|
| A · Endpoints | `/v1/agenda`, `/v1/itens/{id}` com histórico, `/v1/resumo`, `WS /v1/stream` |
| B · Cofre de dados | SQLCipher + chave no Keychain (`security` CLI), migração do banco atual |
| C · Perímetro | WebAuthn, rate limit, `tailscale serve`, gitleaks no pre-commit |

## Prompt base (troque a trilha)
```
Executor F3-<trilha> do Jarvis. Leia CLAUDE.md, docs/04-seguranca-privacidade.md e
contracts/openapi.yaml. Implemente o escopo da trilha <trilha> descrito em
orquestracao/fases/F3-api-seguranca.md. Toda rota nova exige token e tem teste de 401.
Regere os contratos com scripts/gerar_contratos.py. Ao terminar, rode a skill
security-review do ECC no seu diff e corrija tudo que for alto ou crítico antes do PR.
```
