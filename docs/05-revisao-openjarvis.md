# 05 · Revisão do OpenJarvis (base técnica)

Revisado em 19/11/2026, na branch `main` de https://github.com/open-jarvis/OpenJarvis.

## O que aproveitamos
| Peça | Caminho | Uso no Jarvis |
|---|---|---|
| Gmail via API + OAuth | `src/openjarvis/connectors/gmail.py`, `google_auth.py`, `oauth.py` | Coleta de e-mail (F1) |
| Google Calendar | `connectors/gcalendar.py` | Coleta da agenda (F1) |
| Google Contatos | `connectors/gcontacts.py` | Nomes e lista de contatos conhecidos |
| Transcrição | `speech/faster_whisper.py` | Áudio do WhatsApp vira texto (F1) |
| Voz (TTS) | `speech/kokoro_tts.py` e outros | Resumo da manhã falado (F5) |
| Fila de aprovação | `server/approval_routes.py` | Modelo para aprovar envios (pós-v1) |
| Modelos locais | Ollama via `engine/` | Camada LLM da triagem (F2) |

## Limitações encontradas no WhatsApp
| Peça | Problema | Nossa solução |
|---|---|---|
| `connectors/whatsapp.py` (exportação) | Regex só aceita `1/15/24, 10:30 AM`. **Exportação em português não é lida.** Também trata horário local como UTC. | `jarvis_core/ingest/whatsapp_export.py`: Android e iPhone pt-BR, multilinha, fuso correto. Vale abrir um PR para o OpenJarvis. |
| `channels/whatsapp.py` | Cloud API oficial, **só envia** | Não usamos |
| `channels/whatsapp_baileys_bridge` | Só repassa texto **novo recebido**. Sem histórico, sem as suas mensagens, sem mídia, sem nomes de grupo, sem persistência. Envio sempre liberado. Reconecta sem espera. | `bridge/whatsapp`: histórico completo, SQLite, suas mensagens, legendas, áudio, menções, só leitura por padrão, reconexão com backoff |

## Outras observações
- Gmail tem dois caminhos (`gmail.py` com OAuth e `gmail_imap.py` com senha de app). O guia
  oficial mostra o IMAP. Usaremos **OAuth com escopo só leitura**.
- O projeto se move rápido (mais de 1.300 commits). **Fixar a versão** no `pyproject` e
  atualizar de propósito, com os testes de integração rodando.
- Não há interface móvel nem motor de prioridade. Essa é a parte que construímos.
