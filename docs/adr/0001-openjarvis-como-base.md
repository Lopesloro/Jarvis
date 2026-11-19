# ADR-0001 · OpenJarvis como dependência, não como fork

**Status:** aceito · 19/11/2026

## Contexto
O OpenJarvis já tem conectores do Google, agentes agendados, voz e modelos locais, mas não
tem interface móvel nem motor de prioridade, e a parte de WhatsApp não serve para ler
histórico. O projeto muda muito rápido.

## Decisão
Usar o OpenJarvis como **dependência fixada** (`jarvis-core[openjarvis]`) e escrever o que é
nosso neste repositório: ponte WhatsApp, triagem, API e PWA. Correções úteis para todos
(como o parser pt-BR) viram PR para o projeto original.

## Consequências
- Atualizar o OpenJarvis é um ato deliberado, com os testes de integração rodando.
- Não carregamos 1.300 commits de código que não usamos.
- Se o OpenJarvis mudar de rumo, trocamos a camada de coleta sem mexer em triagem nem em interface.
