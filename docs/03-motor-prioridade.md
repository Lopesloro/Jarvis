# 03 · Motor de prioridade

## Princípios
1. **Explicável:** a nota é a soma de sinais com nome, pontos e frase. A interface mostra
   "por que 87?" sem precisar de LLM.
2. **Determinístico primeiro:** as regras rodam em microssegundos, offline e testáveis. O
   LLM refina, mas não decide sozinho.
3. **Ajuste limitado:** o LLM pode mover a nota no máximo ±20 pontos e precisa justificar.
4. **Aprende com você:** cada decisão sua (resolveu, adiou, arquivou, "isso não era
   importante") vira um exemplo rotulado para recalibrar pesos (F2).

## Fórmula

```
nota = clamp(0, 100, BASE + Σ sinais + ajuste_llm)        BASE = 20
```

| Faixa | Nota | Comportamento |
|---|---|---|
| `agora` | 80–100 | Aparece em "Agora" e gera push (fora do horário de silêncio) |
| `hoje` | 60–79 | Topo da inbox |
| `semana` | 35–59 | Inbox normal |
| `arquivar` | 0–34 | Some da inbox; fica pesquisável |

## Sinais (v1, código em `core/jarvis_core/priority/rules.py`)

| Sinal | Pontos | Quando |
|---|---|---|
| `vip` | +30 | Remetente na lista VIP (`config: prioridade.vips`) |
| `contato_conhecido` | +5 | Já houve conversa nos dois sentidos |
| `automatico` | −40 | noreply, `List-Unsubscribe`, Promoções/Social do Gmail |
| `conversa_direta` | +10 | Conversa individual no WhatsApp ou e-mail só para você |
| `grupo` | −10 | Grupo sem menção a você |
| `mencao_em_grupo` | +20 | Grupo com @você ou resposta a mensagem sua |
| `aguardando_resposta` | +15 | Última mensagem é de outra pessoa e tem pergunta ou pedido |
| `tempo_sem_resposta` | +5 a cada 6 h (máx. +15) | Junto com `aguardando_resposta` |
| `ja_respondido` | −30 | Sua mensagem é a mais recente da conversa |
| `urgencia` | +20 | "urgente", "agora", "o quanto antes", "emergência", "asap" |
| `prazo` | +20 | "hoje", "amanhã", "até dd/mm", "prazo", "vence", "deadline" |
| `oportunidade` | +15 | "entrevista", "vaga", "estágio", "proposta", "contrato", "processo seletivo" |
| `financeiro` | +10 | "boleto", "pix", "fatura", "cobrança", "pagamento" |
| `evento_proximo` | +10 (24 h) / +20 (2 h) | Remetente participa de um evento da Agenda nesse intervalo |
| `antigo` | −20 | Mais de 7 dias sem atividade |

Os pesos são um ponto de partida. A F2 os recalibra com o conjunto rotulado.

## Ação sugerida
| Condição | Ação |
|---|---|
| `automatico` ou nota < 35 | `arquivar` |
| `aguardando_resposta` | `responder` (com rascunho na F2) |
| texto pede reunião/horário e não há evento | `agendar` |
| demais | `ler` |

## Camada LLM (F2)
- Modelo local via Ollama (padrão `qwen2.5:7b-instruct`, configurável).
- Entrada: item, as 10 últimas mensagens da conversa, sinais disparados e nota base.
- Saída JSON validada por [`triagem.schema.json`](../contracts/triagem.schema.json):
  `ajuste` (−20…+20), `motivo`, `acao_sugerida` e `rascunho` opcional.
- Se o LLM falhar ou passar do tempo limite, vale a nota das regras. Nada trava.

## Avaliação (F2)
- Conjunto rotulado: 300 itens reais anonimizados, rotulados em `agora/hoje/semana/arquivar`.
- Métricas: precisão@agora, revocação de "agora" em ≥ 60, matriz de confusão por faixa.
- Roda no CI (`pytest -m eval`) com o conjunto sintético que acompanha o repositório. O
  conjunto real fica só no Mac.
