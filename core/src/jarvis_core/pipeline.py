"""Liga coleta → triagem → armazenamento. Roda em laço pelo agendador (F1)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from jarvis_core.ingest.whatsapp_bridge import ler_conversas
from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store


def processar_whatsapp(wa_db: Path, store: Store, ctx_base: Contexto, desde: datetime) -> int:
    """Triagem de todas as conversas do WhatsApp com atividade desde `desde`."""
    total = 0
    for item, historico in ler_conversas(wa_db, desde):
        conhecidos = ctx_base.contatos_conhecidos | (
            {item.remetente.id} if any(m.autor.eh_eu for m in historico) else set()
        )
        ctx = replace(ctx_base, historico=historico, contatos_conhecidos=conhecidos)
        store.salvar(item, triar(item, ctx))
        total += 1
    return total
