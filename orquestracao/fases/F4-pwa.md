# F4 · PWA (Mac + celular)

Skills ECC: `frontend-design-direction`, `react-patterns`, `nextjs-turbopack`,
`frontend-a11y`, `unified-notifications-ops`, `make-interfaces-feel-better`, `e2e-testing`.
Siga `web/DESIGN.md` (escala de cinza, sem azul).

| Trilha | Escopo |
|---|---|
| A · Base | Next.js export estático, cliente tipado gerado de `contracts/openapi.yaml`, auth, service worker |
| B · Telas | Agora, Inbox, Agenda, Item, Ajustes |
| C · Push | Web Push VAPID na API + inscrição no PWA + horário de silêncio |

## Prompt da trilha B
```
Executor F4-B do Jarvis. Leia web/DESIGN.md e docs/00-visao.md (casos U1–U7).
Construa as telas mobile primeiro, em escala de cinza:
- Agora: cartões com nota grande, faixa, remetente, canal, os 2 motivos principais e as
  ações (resolver, adiar, arquivar, "deveria ser…").
- Inbox: lista com filtros por faixa e canal e busca.
- Agenda: dia atual com as mensagens recentes de quem participa de cada evento.
- Item: conversa (últimas 20), todos os motivos, rascunho sugerido (só copiar), decisão.
- Ajustes: VIPs, horário de silêncio, conexões (status da ponte e do Google).
Estados de carregando, vazio e erro em todas. Skills: frontend-design-direction,
make-interfaces-feel-better, frontend-a11y. Teste e2e do fluxo Agora → resolver.
```
