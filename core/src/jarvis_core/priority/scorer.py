"""Combina os sinais em nota, faixa e ação sugerida."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from jarvis_core.models import Acao, Faixa, Item, Motivo, Triagem
from jarvis_core.priority.rules import (
    RE_AGENDAR,
    SINAIS,
    VERSAO_REGRAS,
    Contexto,
    aguardando_resposta,
    eh_automatico,
    evento_com_remetente,
    normalizar,
)

BASE = 20
LIMITE_AJUSTE_LLM = 20


class Refinador(Protocol):
    """Camada LLM opcional (F2). Recebe a triagem das regras e devolve (ajuste, motivo)."""

    def refinar(self, item: Item, ctx: Contexto, base: Triagem) -> tuple[int, str]: ...


def faixa_da_nota(nota: int) -> Faixa:
    if nota >= 80:
        return Faixa.AGORA
    if nota >= 60:
        return Faixa.HOJE
    if nota >= 35:
        return Faixa.SEMANA
    return Faixa.ARQUIVAR


def _acao(item: Item, ctx: Contexto, nota: int) -> Acao:
    if eh_automatico(item) or nota < 35:
        return Acao.ARQUIVAR
    pede_agenda = RE_AGENDAR.search(normalizar(f"{item.assunto} {item.texto}"))
    if pede_agenda and not evento_com_remetente(item, ctx, timedelta(days=14)):
        return Acao.AGENDAR
    if aguardando_resposta(item, ctx):
        return Acao.RESPONDER
    return Acao.LER


def triar(item: Item, ctx: Contexto, refinador: Refinador | None = None) -> Triagem:
    motivos: list[Motivo] = [m for sinal in SINAIS if (m := sinal(item, ctx)) is not None]
    nota = max(0, min(100, BASE + sum(m.pontos for m in motivos)))
    triagem = Triagem(
        item_id=item.id,
        nota=nota,
        faixa=faixa_da_nota(nota),
        motivos=motivos,
        acao_sugerida=_acao(item, ctx, nota),
        versao_regras=VERSAO_REGRAS,
    )
    if refinador is None:
        return triagem

    try:
        ajuste, motivo = refinador.refinar(item, ctx, triagem)
    except Exception:  # noqa: BLE001 (o LLM nunca derruba a triagem)
        return triagem
    ajuste = max(-LIMITE_AJUSTE_LLM, min(LIMITE_AJUSTE_LLM, int(ajuste)))
    nota_final = max(0, min(100, nota + ajuste))
    return triagem.model_copy(
        update={
            "nota": nota_final,
            "faixa": faixa_da_nota(nota_final),
            "ajuste_llm": ajuste,
            "motivo_llm": motivo,
            "acao_sugerida": _acao(item, ctx, nota_final),
        }
    )
