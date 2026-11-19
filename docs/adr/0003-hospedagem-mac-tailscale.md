# ADR-0003 · Rodar no Mac, acesso pelo celular via Tailscale

**Status:** aceito · 19/11/2026

## Decisão
Núcleo, ponte e API rodam no Mac sob `launchd`. O celular acessa pela rede privada do
Tailscale com HTTPS (`tailscale serve`). Nenhuma porta fica aberta na internet.

## Consequências
- Privacidade máxima e custo zero.
- Com o Mac desligado ou dormindo, não há Jarvis. Mitigação: "Evitar repouso automático
  com a tela desligada" na tomada.
- **Migração futura:** tudo está em `~/.jarvis` e em processos independentes, então mudar
  para uma VPS é copiar a pasta e trocar o `launchd` por `systemd`. A sessão do WhatsApp
  precisa ser pareada de novo.
