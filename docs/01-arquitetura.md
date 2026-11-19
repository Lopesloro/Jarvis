# 01 · Arquitetura

```
 ┌──────────── Mac (sempre ligado, launchd) ────────────────────────────────┐
 │                                                                          │
 │  COLETA                     TRIAGEM                    API               │
 │  ┌──────────────┐          ┌──────────────────┐       ┌──────────────┐   │
 │  │ Gmail (OAuth)│──┐       │ regras           │       │ FastAPI      │   │
 │  │ Agenda       │──┼─────▶ │  + sinais        │──────▶│ REST + WS    │◀──┼── PWA no Mac
 │  │ WhatsApp     │──┘ Item  │  + LLM (Ollama)  │ Item  │ token + TLS  │   │
 │  │ (ponte)      │          │ = nota + motivo  │triado └──────┬───────┘   │
 │  └──────┬───────┘          └──────────────────┘              │           │
 │         │                                                    │           │
 │         ▼                SQLite (jarvis.db, criptografado)   │           │
 │   wa.db (ponte)  ───────────────────────────────────────────┘            │
 └──────────────────────────────────────────────────────────────┼───────────┘
                                                                │ Tailscale (rede privada)
                                                                ▼
                                                        PWA no celular + push
```

## Camadas

### 1. Coleta
| Fonte | Como | Reaproveita do OpenJarvis | O que é nosso |
|---|---|---|---|
| Gmail | API REST com OAuth (`gmail.readonly`) | `connectors/gmail.py`, `google_auth.py` | normalização para `Item`, leitura de `List-Unsubscribe` e categorias |
| Agenda | Google Calendar API (`calendar.readonly`) | `connectors/gcalendar.py` | `Evento` + vínculo com participantes |
| WhatsApp | Ponte Baileys (aparelho conectado) | ideia da `whatsapp_baileys_bridge` | **ponte reescrita**: histórico, SQLite, mensagens próprias, mídia, só leitura |
| WhatsApp (backup) | Exportação `.txt` | `connectors/whatsapp.py` | **parser pt-BR** (o original só entende data americana) |

Todo conector entrega o mesmo objeto: [`Item`](../contracts/item.schema.json).

### 2. Triagem
Explicada em [03-motor-prioridade.md](03-motor-prioridade.md). Em resumo: as regras
determinísticas dão a nota base e os motivos, e o LLM local só pode ajustar ±20 pontos,
sempre dizendo por quê.

### 3. API
FastAPI (`core/jarvis_core/api`). Endpoints em [contracts/openapi.yaml](../contracts/openapi.yaml):
- `GET /v1/agora` itens com nota ≥ 80 e não resolvidos
- `GET /v1/inbox?faixa=&canal=&q=` inbox unificada
- `GET /v1/agenda?dia=` eventos com contexto
- `POST /v1/itens/{id}/decisao` registra a decisão (resolver, adiar, arquivar, rascunho)
- `WS /v1/stream` itens novos em tempo real

### 4. Interface
Um PWA (Next.js, export estático servido pela própria API) que funciona igual no Mac e no
celular. É instalável na tela inicial e recebe push via Web Push (VAPID). Visual em escala de
cinza.

## Por que local + Tailscale
- Os e-mails e as conversas não saem do Mac.
- O Tailscale cria uma rede privada entre Mac e celular sem abrir porta na internet. O
  certificado HTTPS (`tailscale cert`) é necessário para o PWA instalar e receber push.
- A limitação é que, com o Mac desligado, o celular fica sem Jarvis. O launchd mantém o
  processo vivo e `caffeinate`/"Evitar repouso" mantém o Mac acordado na tomada. A migração
  para um servidor está prevista no [ADR-0003](adr/0003-hospedagem-mac-tailscale.md).

## Armazenamento
- `~/.jarvis/jarvis.db`: SQLite com itens, eventos, decisões e notas. Criptografado em
  repouso (SQLCipher) a partir da F3.
- `~/.jarvis/whatsapp/`: credenciais da ponte e `wa.db`. **Equivale a ter o WhatsApp
  aberto**: permissão `700`, fora de qualquer pasta sincronizada (iCloud, Drive, Obsidian).
