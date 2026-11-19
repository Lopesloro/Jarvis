# F1 · Conectores

Skills ECC: `google-workspace-ops`, `email-ops`, `messages-ops`, `api-connector-builder`,
`python-testing`, `tdd-workflow`.

| Trilha | Tarefas | Arquivos |
|---|---|---|
| A · Google | 1.1, 1.2, 1.3, 1.4 | `core/src/jarvis_core/ingest/gmail.py`, `agenda.py`, `contatos.py` |
| B · WhatsApp | 1.5 | `core/src/jarvis_core/ingest/transcricao.py`, `bridge/whatsapp/src/midia.ts` |
| C · Execução | 1.6, 1.7 | `core/src/jarvis_core/agendador.py`, `scripts/launchd/` |

## Prompt da trilha A
```
Você é executor da trilha F1-A do Jarvis. Leia CLAUDE.md, docs/01-arquitetura.md,
docs/05-revisao-openjarvis.md e docs/02-roadmap.md (F1).
Objetivo: tarefas 1.1 a 1.4.
- Adicione openjarvis como extra opcional fixado em core/pyproject.toml.
- Crie ingest/gmail.py convertendo openjarvis.connectors._stubs.Document (source gmail) em
  jarvis_core.models.Item: preencha destinatarios, metadados.labels e
  metadados.list_unsubscribe. Escopo OAuth: somente leitura.
- Crie ingest/agenda.py (gcalendar → Evento) com fuso America/Sao_Paulo correto e eventos de
  dia inteiro.
- Crie ingest/contatos.py unificando e-mail e telefone da mesma pessoa (gcontacts).
Use as skills google-workspace-ops e tdd-workflow do ECC. Testes com fixtures, sem rede.
Termine com `uv run pytest` e `ruff` verdes e abra o PR "F1-A: conectores Google".
```

## Prompt da trilha B
```
Você é executor da trilha F1-B do Jarvis. Leia CLAUDE.md e bridge/whatsapp/README.md.
Objetivo: tarefa 1.5. Na ponte, baixe o áudio de voz (downloadMediaMessage) para
~/.jarvis/whatsapp/midia/ com permissão 600 e registre o caminho numa tabela nova
`midia (jid, id, caminho, transcrito)`. No núcleo, crie ingest/transcricao.py usando
openjarvis.speech.faster_whisper (modelo local, pt) para preencher o texto da mensagem.
Atualize o esquema nos DOIS lados (store.ts e whatsapp_bridge.py) e o teste de integração.
Nada de envio. Skills: messages-ops, python-testing.
```

## Prompt da trilha C
```
Você é executor da trilha F1-C do Jarvis. Leia CLAUDE.md e docs/01-arquitetura.md.
Objetivo: tarefas 1.6 e 1.7.
- core/src/jarvis_core/agendador.py: laço que chama pipeline.processar_whatsapp e os
  conectores Google a cada 60 s, e reage na hora aos eventos {"type":"message"} da ponte
  (stdout JSON). Meta: mensagem triada em até 10 s.
- scripts/launchd/: três plists (ponte, api, agendador) com KeepAlive e logs em
  ~/.jarvis/logs. Script scripts/instalar.sh idempotente.
Skills: autonomous-loops, deployment-patterns. Teste do laço com relógio falso.
```
