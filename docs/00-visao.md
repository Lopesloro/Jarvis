# 00 · Visão do produto

## Problema
A informação que exige decisão está espalhada: e-mails no Gmail, compromissos na Agenda e a
maior parte da vida no WhatsApp (pessoal, faculdade, clientes, estágio). O custo é perder o
que importa no meio do ruído e gastar tempo triando à mão.

## Proposta
Uma caixa única que responde, a qualquer momento: **"o que eu preciso fazer agora, e por quê?"**

## Usuário
Uma pessoa só (o dono). Não é multiusuário. Isso simplifica autenticação, armazenamento
e privacidade.

## Casos de uso da v1
| # | Caso | Exemplo |
|---|---|---|
| U1 | Ver o que exige ação agora | "Recrutador pediu disponibilidade para entrevista até hoje 18h" → nota 92 |
| U2 | Inbox unificada filtrável | WhatsApp + Gmail na mesma lista, por faixa e por canal |
| U3 | Agenda do dia com contexto | Evento das 14h + mensagens recentes das pessoas que vão estar nele |
| U4 | Pendências de resposta | Conversas em que a última mensagem é de outra pessoa, com pergunta, há mais de X horas |
| U5 | Resumo da manhã | Às 7h30: agenda, top 5 pendências, prazos da semana (por texto ou voz) |
| U6 | Decisão assistida | Para um item: opções (responder / agendar / delegar / arquivar) + rascunho; você aprova |
| U7 | Alerta no celular | Push só para nota ≥ 80 e fora do horário de silêncio |

## Fora da v1
- Enviar mensagens ou e-mails sem aprovação (o envio aprovado entra só depois da F5).
- Multiusuário, times, compartilhamento.
- Outros canais (Telegram, Slack, Instagram): a arquitetura comporta, mas ficam depois.

## Métricas de sucesso
- **Precisão no topo:** dos itens com nota ≥ 80, pelo menos 85% são de fato urgentes
  (medido no conjunto rotulado da F2).
- **Revocação do urgente:** pelo menos 95% dos itens rotulados "agora" ficam com nota ≥ 60.
- **Latência:** mensagem nova aparece triada no celular em até 10 s.
- **Ruído:** no máximo 5 pushes por dia em média.
