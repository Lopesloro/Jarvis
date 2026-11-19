# 04 · Segurança e privacidade

O Jarvis lê tudo da sua vida digital. Um vazamento aqui é pior que em qualquer outro projeto.

## Modelo de ameaça
| Ameaça | Controle |
|---|---|
| Alguém na internet acessa a API | Sem porta aberta: acesso só pela rede Tailscale. Token Bearer de 32+ caracteres. A API escuta só em `127.0.0.1` e na interface do Tailscale. |
| Celular perdido | PWA com bloqueio por Face ID/PIN (WebAuthn, F3). Token revogável. Tailscale permite remover o aparelho. |
| Sessão do WhatsApp roubada | `~/.jarvis/whatsapp/auth` com `700`, fora de pastas sincronizadas e do git. Rotina mensal: conferir "Aparelhos conectados" no celular. |
| Banco copiado | SQLCipher a partir da F3, com chave no Keychain do macOS. |
| Dados enviados para a nuvem | Triagem com modelo local por padrão. Provedor de nuvem só com `llm.provedor` explícito no config, e o log registra cada chamada. |
| Envio indevido | Envio desligado no código (ponte + API). Pós-v1: só com aprovação explícita item a item. |
| Prompt injection (mensagem tentando mandar no Jarvis) | O LLM só devolve JSON validado (`ajuste`, `motivo`, `acao`). Não tem ferramentas, não envia e não chama URLs. Conteúdo das mensagens entra delimitado como dado. |
| Segredo no git | `.gitignore` cobre `.env`, `auth/`, `*.db`. Hook `gitleaks` no pre-commit (F3). |

## O que nunca entra no repositório
`.env`, tokens do Google, `auth/` do WhatsApp, qualquer `*.db`, conjuntos rotulados reais e
exportações de conversa. O conjunto de avaliação versionado é **sintético**.

## Cofre do Obsidian
Pode receber **documentação** (estas páginas). **Nunca** recebe dados: nem conversas, nem
e-mails, nem o banco. O cofre sincroniza e não é protegido como o Jarvis.
