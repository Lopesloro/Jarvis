# Acesso pelo celular (Tailscale)

1. Instale o Tailscale no Mac e no celular, com a mesma conta.
2. No Mac, com a API rodando na porta 8765:
   ```bash
   tailscale serve --bg --https=443 http://127.0.0.1:8765
   ```
3. No celular, abra `https://<nome-do-mac>.<tailnet>.ts.net` e instale na tela inicial
   (Safari → Compartilhar → Adicionar à Tela de Início). O push no iPhone exige esse passo.
4. Nos Ajustes do macOS → Bateria → Adaptador de energia: ative "Evitar repouso automático
   quando a tela estiver desligada".

Os plists do `launchd` chegam na F1 (trilha C).
