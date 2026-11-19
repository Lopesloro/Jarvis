# F2 · Motor de prioridade inteligente

Skills ECC: `eval-harness`, `context-and-decisions`, `recursive-decision-ledger`,
`cost-aware-llm-pipeline`, `prompt-optimizer`, `ai-regression-testing`.

| Trilha | Tarefas | Arquivos |
|---|---|---|
| A · Avaliação | 2.1, 2.6 | `core/tests/eval/`, `core/tests/eval/conjunto_sintetico.jsonl` |
| B · LLM | 2.3, 2.4 | `core/src/jarvis_core/priority/refinador_ollama.py` |
| C · Aprendizado | 2.2 (lado API), 2.5 | `core/src/jarvis_core/priority/calibracao.py` |

## Prompt da trilha A
```
Executor F2-A do Jarvis. Leia CLAUDE.md e docs/03-motor-prioridade.md.
Crie core/tests/eval/conjunto_sintetico.jsonl com 150 itens SINTÉTICOS (nada real),
realistas para um estudante de Engenharia de Software em Campinas que busca estágio:
recrutadores, professores, grupos da faculdade, família, bancos, lojas, newsletters.
Cada linha: {item, historico, eventos, rotulo: agora|hoje|semana|arquivar, porque}.
Crie o teste marcado `@pytest.mark.eval` que calcula precisão@agora, revocação de "agora"
com nota ≥ 60 e a matriz de confusão, imprime tudo e falha abaixo das metas.
Skill: eval-harness. Não altere pesos; só meça.
```

## Prompt da trilha B
```
Executor F2-B do Jarvis. Leia docs/03-motor-prioridade.md (Camada LLM) e
priority/scorer.py (protocolo Refinador).
Implemente RefinadorOllama: POST em http://127.0.0.1:11434/api/chat com format=json,
tempo limite de 8 s, modelo configurável (padrão qwen2.5:7b-instruct). O conteúdo das
mensagens entra entre delimitadores como DADO, nunca como instrução. Valide a resposta
contra contracts/triagem.schema.json (ajuste, motivo, acao_sugerida, rascunho).
Para acao=responder, gere um rascunho curto em pt-BR, só exibido, nunca enviado.
Testes com servidor falso: resposta boa, JSON inválido, tempo esgotado, ajuste fora do limite.
Skills: cost-aware-llm-pipeline, prompt-optimizer, agent-security-hardening.
```

## Prompt da trilha C
```
Executor F2-C do Jarvis. A tabela `decisoes` guarda nota_correta quando você corrige a faixa.
Crie priority/calibracao.py: lê decisões + itens, recalcula os sinais e sugere novos pesos
(busca simples em grade ou regressão logística sem dependência pesada), mostrando o antes e o
depois nas métricas da trilha A. Não altera rules.py sozinho: gera um relatório e um diff
sugerido. Skill: recursive-decision-ledger.
```
