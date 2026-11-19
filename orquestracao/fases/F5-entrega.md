# F5 · Verificação e entrega

Skills ECC: `verification-loop`, `e2e-testing`, `delivery-gate`, `production-audit`,
`canary-watch`.

1. E2E completo com a ponte simulada: mensagem → triagem → push → decisão no celular.
2. Resumo da manhã (7h30): agenda + top 5 + prazos da semana; voz opcional (kokoro TTS).
3. Semana de uso real: registrar pushes por dia, falsos positivos e falsos negativos em
   `docs/06-relatorio-uso.md`.
4. `delivery-gate` do ECC e gate final do /harvey.

## Prompt
```
Executor F5 do Jarvis. Leia docs/00-visao.md (métricas de sucesso) e docs/02-roadmap.md.
Monte o teste e2e completo com Playwright (viewport de celular) e a ponte simulada.
Implemente /v1/resumo e o agendamento das 7h30. Depois rode verification-loop e
delivery-gate do ECC e registre o resultado em docs/06-relatorio-uso.md.
```
