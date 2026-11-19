# ADR-0002 · WhatsApp como aparelho conectado, só leitura

**Status:** aceito com risco conhecido · 19/11/2026

## Contexto
O objetivo é ler **todas** as conversas pessoais. A API oficial (Cloud API) só funciona
com número comercial e não lê conversas pessoais. A única forma de ler o histórico é se
conectar como aparelho (protocolo do WhatsApp Web, biblioteca Baileys).

## Decisão
Ponte própria com Baileys, em **modo só leitura**: sem envio, sem presença online, sem
confirmação de leitura e com reconexão com backoff.

## Riscos
- **Viola os termos de uso do WhatsApp.** O número pode ser banido sem aviso e sem recurso.
- A Baileys quebra quando o WhatsApp muda o protocolo. Versão fixada; atualizar com cuidado.

## Mitigação
- Só leitura reduz bastante o padrão que a Meta detecta (envio em massa e automação).
- Exportação manual (`.txt`) como plano B, com o parser pt-BR.
- Se o número for banido: desligar a ponte e seguir com Gmail + Agenda + exportações.
