# ADR-0004 · Prioridade por regras explicáveis + ajuste limitado do LLM

**Status:** aceito · 19/11/2026

## Decisão
A nota vem de sinais determinísticos com nome e explicação. O LLM local só ajusta ±20 pontos
e precisa dar o motivo. Falha do LLM = vale a nota das regras.

## Por quê
- Você precisa confiar na nota. "87 porque: VIP, prazo hoje, sem resposta há 12 h" gera
  confiança; "87 porque o modelo disse" não.
- É testável e roda offline em microssegundos.
- O LLM entra onde as regras são fracas: ironia, contexto da conversa, pedidos implícitos.
