# 02 · Roadmap

Cada fase termina num **gate do /harvey** ([checklist](../orquestracao/harvey-gate.md)).
Fase só fecha com o gate aprovado, testes verdes e o README atualizado.

## F0 · Fundação (feito)
- [x] Visão, arquitetura, motor de prioridade, segurança, revisão do OpenJarvis
- [x] ADRs 0001–0005
- [x] Modelos e contratos (`contracts/`) gerados do código
- [x] Motor de prioridade por regras, com motivos e limite para o ajuste do LLM
- [x] Parser de exportação do WhatsApp em pt-BR
- [x] Ponte WhatsApp: histórico, SQLite, só leitura
- [x] API mínima: `/v1/agora`, `/v1/inbox`, `/v1/itens/{id}/decisao`
- [x] 19 testes Python + 6 testes da ponte

## Estado real (revisão de 19/11/2026)
As abas do FCC entregaram uma versão funcional de F1–F5 num commit só, com desvios
registrados no [ADR-0006](adr/0006-coleta-sem-oauth-e-navegador-da-ponte.md). A revisão
corrigiu: falha de concorrência no banco (o `/v1/resumo` quebrava), texto de terceiros
indo para o LLM sem delimitação, log do agendador crescendo 17 mil linhas por dia, backlog
inteiro passando pelo LLM na primeira sincronização e evento sem horário de fim com
duração zero. Cobertura subiu de 82% para 100% (linhas e ramos), com portões que impedem
voltar a cair.

**Ainda não feito:** pareamento do WhatsApp (a ponte está esperando o QR), acesso pelo
celular via Tailscale, push no celular (hoje o aviso é notificação do macOS), transcrição
de áudio, unificação de contatos e conjunto rotulado da F2.

## F1 · Conectores (≈ 1 semana)
| # | Tarefa | Aceite |
|---|---|---|
| 1.1 | Adicionar `openjarvis` fixado como dependência opcional | `uv sync --extra openjarvis` funciona; versão fixa no lock |
| 1.2 | `ingest/gmail.py`: `Document` do OpenJarvis → `Item` | Lê `List-Unsubscribe`, labels e destinatários; testes com fixtures |
| 1.3 | `ingest/agenda.py`: eventos → `Evento` | Participantes por e-mail; eventos de dia inteiro corretos no fuso de SP |
| 1.4 | Ligar e-mail ↔ WhatsApp da mesma pessoa via Google Contatos | `Pessoa` com ids unificados; teste com contato que tem e-mail e celular |
| 1.5 | Transcrição de áudio (faster-whisper local) | `[áudio de voz]` vira texto em até 30 s após chegar |
| 1.6 | Agendador: laço de coleta a cada 60 s + WebSocket da ponte | Mensagem nova triada em até 10 s |
| 1.7 | `launchd` para ponte + API + agendador | Sobrevive a reinício do Mac |

## F2 · Motor de prioridade inteligente (≈ 1 semana)
| # | Tarefa | Aceite |
|---|---|---|
| 2.1 | Conjunto sintético de 150 itens rotulados (versionado) | Cobre as 4 faixas e os 3 canais |
| 2.2 | Ferramenta de rotulagem rápida no PWA (botões "deveria ser…") | Grava em `decisoes.nota_correta` |
| 2.3 | `Refinador` com Ollama (`qwen2.5:7b-instruct`) | JSON validado; tempo limite de 8 s; fallback testado |
| 2.4 | Rascunho de resposta para `acao = responder` | Nunca enviado; só exibido |
| 2.5 | Calibração de pesos com as decisões reais | Script que sugere novos pesos e mostra o ganho nas métricas |
| 2.6 | `pytest -m eval` no CI | precisão@agora ≥ 0,85 e revocação ≥ 0,95 no conjunto sintético |

## F3 · API e segurança (≈ 4 dias)
- Endpoints `/v1/agenda`, `/v1/itens/{id}` (com histórico), `WS /v1/stream`, `/v1/resumo`
- SQLCipher + chave no Keychain; `gitleaks` no pre-commit; rate limit
- WebAuthn (Face ID) para abrir o PWA
- `tailscale serve` com HTTPS
- Aceite: `security-review` do ECC sem achados altos; testes de autorização em todas as rotas

## F4 · PWA (≈ 1 semana)
- Next.js em export estático, servido pela API
- Telas: **Agora** (cartões com nota e motivo), **Inbox** (filtros por faixa e canal),
  **Agenda** (dia com contexto), **Item** (conversa + ações), **Ajustes** (VIPs, silêncio)
- Web Push (VAPID) só para `agora`, respeitando o horário de silêncio
- Escala de cinza, tipografia forte, sem azul; mobile primeiro
- Aceite: Lighthouse PWA ≥ 90; instalável no iPhone e no Android; e2e com Playwright

## F5 · Verificação e entrega (≈ 3 dias)
- E2E: mensagem chega → push → decisão no celular → some do "Agora"
- Resumo da manhã às 7h30 (texto + voz opcional)
- 7 dias de uso real com métricas de ruído e precisão
- `delivery-gate` do ECC + gate final do /harvey
