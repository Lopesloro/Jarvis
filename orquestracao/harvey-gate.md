# Gate do /harvey

## Fluxo
1. `scripts/revisao.sh pedir` → gera `.git/REVISAO_PENDENTE.md` com **todos** os commits
   ainda não revisados (desde a última revisão aprovada).
2. No Claude Code: `/harvey` + o conteúdo desse arquivo.
3. Corrija BLOQUEANTES e IMPORTANTES (novos commits) e peça de novo até vir **APROVADO**.
4. `scripts/revisao.sh aprovar "resumo do que o /harvey verificou"`.
5. O pre-push e o CI recusam qualquer commit fora de uma revisão aprovada.

O que as máquinas já garantem (o /harvey não precisa conferir à mão): lint, formato,
100% de cobertura de linhas e ramos, contratos em dia, segredos óbvios no diff.
O /harvey foca no que só um revisor vê: lógica, segurança, privacidade e clareza.

## Por PR
**Correção**
- [ ] Faz o que a tarefa do roadmap pede, e o aceite está demonstrado (teste ou print)
- [ ] Casos de borda: fuso horário (America/Sao_Paulo × UTC), acentos, conversa vazia, grupo,
      mensagem sua como a mais recente, ids `@lid`

**Segurança (qualquer falha = BLOQUEANTE)**
- [ ] Nenhum caminho de envio de mensagem/e-mail fora de `JARVIS_WA_ALLOW_SEND` + aprovação
- [ ] Nenhum segredo, `*.db`, `auth/` ou dado real no diff
- [ ] Rotas novas exigem token; testes de 401 existem
- [ ] Conteúdo de mensagem nunca é executado nem vira instrução para o LLM sem delimitação
- [ ] Nenhum dado sai do Mac sem configuração explícita

**Prioridade**
- [ ] Sinal novo ou peso alterado → `docs/03-motor-prioridade.md` atualizado + teste
- [ ] Toda nota continua com motivos legíveis

**Qualidade**
- [ ] Os testes novos testam comportamento de verdade (não só passam pela linha para bater 100%)
- [ ] Sem `any`, `# type: ignore` ou `pragma: no cover` novos sem justificativa
- [ ] Concorrência: nada novo compartilhado entre threads sem trava
- [ ] Interface em escala de cinza, sem azul; texto de terceiros sempre escapado

## Por fase
- [ ] Todas as tarefas da fase marcadas no `docs/02-roadmap.md`
- [ ] CI verde na `main`
- [ ] README e docs refletem o que existe (sem promessa do que não existe)
- [ ] Riscos novos registrados em ADR
- [ ] Fase F2 em diante: `pytest -m eval` dentro das metas
