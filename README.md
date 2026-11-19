# Jarvis

Assistente pessoal que junta **agenda, Gmail e WhatsApp** numa só caixa, dá a cada item uma
**nota de importância com o motivo explicado** e propõe a próxima ação: responder, agendar,
delegar ou arquivar. Funciona no Mac e no celular (PWA), com o núcleo rodando localmente no
Mac e o acesso pelo celular feito via Tailscale.

Base: [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) (Apache 2.0), que entra como
dependência para conectores, agentes agendados, voz e modelos locais. O que é nosso está
neste repositório.

## Estado

| Fase | Entrega | Status |
|---|---|---|
| F0 | Spec, ADRs, contratos, núcleo de prioridade, ponte WhatsApp | **feito** |
| F1 | Conectores ligados ao OpenJarvis (Gmail OAuth, Agenda, WhatsApp) | a fazer |
| F2 | Motor de prioridade com LLM + conjunto rotulado e métricas | a fazer |
| F3 | API completa, autenticação, segurança | a fazer |
| F4 | PWA (Agora, Inbox, Agenda, Decisões) + push | a fazer |
| F5 | Verificação ponta a ponta e entrega | a fazer |

Detalhe em [docs/02-roadmap.md](docs/02-roadmap.md). Prompts prontos para cada fase em
[orquestracao/](orquestracao/).

## Estrutura

```
docs/             visão, arquitetura, roadmap, motor de prioridade, segurança, ADRs
contracts/        JSON Schema dos objetos trocados entre camadas
core/             pacote Python jarvis_core (modelos, motor de prioridade, ingestão, API)
bridge/whatsapp/  ponte Baileys estendida: histórico completo, SQLite, só leitura
web/              PWA (fase F4)
orquestracao/     prompts por fase para FCC/ECC e checklist do /harvey
config/           exemplo de configuração
scripts/          geração de contratos e acesso via Tailscale (launchd na F1)
```

## Rodar o que já existe

```bash
# núcleo
cd core && uv sync && uv run pytest
export JARVIS_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
uv run uvicorn jarvis_core.api.main:app --host 127.0.0.1 --port 8765

# ponte do WhatsApp (pareia por QR na primeira vez)
cd bridge/whatsapp && npm install && npm run build
npm start -- --data-dir ~/.jarvis/whatsapp
```

## Regras inegociáveis

1. **Nada é enviado sozinho.** O Jarvis sugere; você aprova. O envio pelo WhatsApp fica
   desligado no código e só liga com `JARVIS_WA_ALLOW_SEND=1`.
2. **Os dados ficam no Mac.** A triagem roda com modelo local (Ollama) por padrão. Um
   modelo na nuvem só entra se você ligar de propósito.
3. **Toda nota tem motivo.** Nenhuma prioridade sem explicação legível.
4. **Interface em preto e branco.** Escala de cinza, sem azul.
