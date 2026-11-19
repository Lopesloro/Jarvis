"""Liga coleta → triagem → armazenamento. Roda em laço pelo agendador."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from jarvis_core.ingest.whatsapp_bridge import ler_conversas
from jarvis_core.models import Item, Mensagem, Triagem
from jarvis_core.priority import Contexto, triar
from jarvis_core.priority.scorer import Refinador
from jarvis_core.store import Store

# Só gasta tempo do modelo local com o que as regras não descartaram de cara.
NOTA_MINIMA_PARA_LLM = 30
# Na primeira sincronização chegam dias de conversa: o modelo local levaria horas. Só o que
# é recente passa pelo LLM; o resto fica com a nota das regras.
JANELA_LLM = timedelta(hours=12)

AoSalvar = Callable[[Item, Triagem], None]


def processar(
    lote: Iterable[tuple[Item, list[Mensagem]]],
    store: Store,
    ctx_base: Contexto,
    refinador: Refinador | None = None,
    pular_existentes: bool = False,
    ao_salvar: AoSalvar | None = None,
) -> int:
    total = 0
    for item, historico in lote:
        if pular_existentes and store.existe(item.id):
            continue
        conhecidos = ctx_base.contatos_conhecidos | (
            {item.remetente.id} if any(m.autor.eh_eu for m in historico) else set()
        )
        ctx = replace(ctx_base, historico=historico, contatos_conhecidos=conhecidos)
        triagem = triar(item, ctx)
        recente = ctx_base.agora - item.recebido_em <= JANELA_LLM
        if refinador is not None and recente and triagem.nota >= NOTA_MINIMA_PARA_LLM:
            triagem = triar(item, ctx, refinador)
        store.salvar(item, triagem)
        if ao_salvar:
            ao_salvar(item, triagem)
        total += 1
    return total


def processar_whatsapp(
    wa_db: Path,
    store: Store,
    ctx_base: Contexto,
    desde: datetime,
    refinador: Refinador | None = None,
    pular_existentes: bool = False,
    ao_salvar: AoSalvar | None = None,
) -> int:
    """Triagem de todas as conversas do WhatsApp com atividade desde `desde`."""
    return processar(
        ler_conversas(wa_db, desde), store, ctx_base, refinador, pular_existentes, ao_salvar
    )
