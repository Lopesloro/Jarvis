# ADR-0006 · Gmail por IMAP, agenda por .ics e ponte como "Chrome"

**Status:** aceito com ressalvas · 19/11/2026 (registrado na revisão das abas do FCC)

## Contexto
A F1 previa Gmail e Agenda via OAuth do OpenJarvis. As abas do FCC implementaram outra coisa,
para não exigir um projeto no Google Cloud:
- **Gmail por IMAP** com senha de app (`ingest/gmail_imap.py`), em modo só leitura
  (`readonly` + `BODY.PEEK`).
- **Agenda pelo endereço secreto iCal** (`ingest/agenda_ics.py`).
- **Ponte identificada como Chrome** em vez de Desktop, porque o WhatsApp recusou o "Desktop"
  com erro 428 antes de mostrar o QR.

## Decisão
Manter as três escolhas na v1, com as proteções abaixo.

## Consequências e proteções
| Escolha | Custo | Proteção |
|---|---|---|
| Senha de app no `~/.jarvis/jarvis.toml` | Senha em texto no disco; dá acesso total ao e-mail por IMAP | `config.py` força permissão 600 e avisa no log; revogável a qualquer momento em myaccount.google.com/apppasswords |
| URL secreta do iCal | Quem tiver a URL lê a agenda | Fica só no `jarvis.toml` (600); pode ser redefinida no Google Agenda |
| IMAP não traz as categorias do Gmail (Promoções/Social) | Menos sinal de "automático" | `List-Unsubscribe` e remetente noreply continuam valendo |
| Ponte como Chrome | O WhatsApp manda **menos histórico** do que para "Desktop" | `JARVIS_WA_NAVEGADOR=Desktop` permite testar de novo sem mudar código |

## Quando revisitar
Antes de abrir o Jarvis para outra pessoa ou guardar dados na nuvem: migrar para OAuth
com escopo só leitura (`gmail.readonly`, `calendar.readonly`) e guardar segredos no Keychain.
