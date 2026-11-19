# ADR-0005 · Um PWA para Mac e celular

**Status:** aceito · 19/11/2026

## Opções
1. App nativo (Expo/React Native): melhor push no iOS, mas exige loja ou TestFlight e mantém dois alvos.
2. **PWA (Next.js export estático)**: um código só, instalável, Web Push funciona no iOS 16.4+ quando instalado na tela inicial.
3. Bot no Telegram: rápido, mas os dados passariam por um servidor de terceiros.

## Decisão
PWA. O próprio servidor da API serve os arquivos, então não há segunda hospedagem.

## Consequências
- No iPhone, o push só funciona com o PWA **instalado** na tela inicial e servido por HTTPS (Tailscale).
- Se o push no iOS se mostrar instável, a saída é empacotar o mesmo front com Capacitor.
