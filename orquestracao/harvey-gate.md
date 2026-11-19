# Gate do /harvey

Cole no /harvey: `Revise <PR #N | fase Fx> do Jarvis usando orquestracao/harvey-gate.md.
Classifique cada achado como BLOQUEANTE, IMPORTANTE ou MENOR, com arquivo e linha.`

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
- [ ] `ruff`/`tsc strict` limpos; sem `any`/`# type: ignore` novos sem justificativa
- [ ] Contratos regenerados se `models.py` ou a API mudaram
- [ ] Interface em escala de cinza, sem azul

## Por fase
- [ ] Todas as tarefas da fase marcadas no `docs/02-roadmap.md`
- [ ] CI verde na `main`
- [ ] README e docs refletem o que existe (sem promessa do que não existe)
- [ ] Riscos novos registrados em ADR
- [ ] Fase F2 em diante: `pytest -m eval` dentro das metas
