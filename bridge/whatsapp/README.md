# Ponte WhatsApp

Conecta como **aparelho conectado** (igual ao WhatsApp Web) e grava tudo em
`~/.jarvis/whatsapp/wa.db`, que o núcleo lê em `jarvis_core/ingest/whatsapp_bridge.py`.

## Primeira vez
```bash
npm install && npm run build
npm start -- --data-dir ~/.jarvis/whatsapp
```
O QR aparece no terminal. No celular: **WhatsApp → Configurações → Aparelhos conectados →
Conectar aparelho**. A sincronização do histórico pode levar alguns minutos. Acompanhe pelos
eventos `{"type":"history",...}` no stdout.

## O que é gravado
| Tabela | Conteúdo |
|---|---|
| `chats` | conversas e grupos, com nome e última atividade |
| `contatos` | nomes salvos ou o nome público |
| `mensagens` | texto, legenda ou marcador de mídia, autor, se é sua, se te menciona |
| `lid_pn` | equivalência entre ids novos do WhatsApp (`@lid`) e números |
| `meta` | seu próprio jid |

## Segurança
- **Só leitura:** o comando `send` é recusado. Para liberar (fase posterior, com aprovação
  no app), defina `JARVIS_WA_ALLOW_SEND=1`.
- A pasta `auth/` **equivale a ter seu WhatsApp aberto**. Fica em `700`, fora do iCloud,
  do Drive e do Obsidian, e nunca vai para o git.
- Não marca você como online nem envia confirmação de leitura.

## Risco
Esta conexão não é oficial e viola os termos de uso do WhatsApp. O número pode ser banido
sem aviso. Usar só leitura reduz o risco, mas não o elimina. Ver
[ADR-0002](../../docs/adr/0002-whatsapp-aparelho-conectado.md).

## Testes
```bash
npm test
```
