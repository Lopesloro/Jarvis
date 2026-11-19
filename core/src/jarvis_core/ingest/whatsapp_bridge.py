"""Lê o wa.db gravado pela ponte (bridge/whatsapp) e gera Itens com histórico.

O esquema do banco é definido em bridge/whatsapp/src/store.ts; mudar um exige mudar o outro.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from jarvis_core.models import Canal, Item, Mensagem, Pessoa

HISTORICO = 20


def _pessoa(jid: str, nome: str | None, meu_jid: str) -> Pessoa:
    return Pessoa(id=jid, nome=nome or jid.split("@")[0], eh_eu=jid == meu_jid)


def ler_conversas(db: Path, desde: datetime) -> list[tuple[Item, list[Mensagem]]]:
    """Conversas com mensagem recebida depois de `desde`, cada uma com seu histórico."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        meu = con.execute("SELECT valor FROM meta WHERE chave = 'meu_jid'").fetchone()
        meu_jid = meu["valor"] if meu else ""
        chats = con.execute(
            "SELECT jid, nome, eh_grupo FROM chats WHERE atualizado_em >= ?",
            (int(desde.timestamp()),),
        ).fetchall()
        saida: list[tuple[Item, list[Mensagem]]] = []
        for chat in chats:
            linhas = con.execute(
                """SELECT m.id, m.autor_jid, m.de_mim, m.texto, m.menciona_me, m.enviada_em,
                          c.nome AS autor_nome
                     FROM mensagens m LEFT JOIN contatos c ON c.jid = m.autor_jid
                    WHERE m.jid = ? AND m.texto <> ''
                 ORDER BY m.enviada_em DESC LIMIT ?""",
                (chat["jid"], HISTORICO),
            ).fetchall()[::-1]
            historico = [
                Mensagem(
                    autor=_pessoa(
                        meu_jid if r["de_mim"] else r["autor_jid"], r["autor_nome"], meu_jid
                    ),
                    texto=r["texto"],
                    enviada_em=datetime.fromtimestamp(r["enviada_em"], UTC),
                )
                for r in linhas
            ]
            recebidas = [r for r in linhas if not r["de_mim"]]
            if not recebidas:
                continue
            ultima = recebidas[-1]
            item = Item(
                id=f"whatsapp:{chat['jid']}:{ultima['id']}",
                canal=Canal.WHATSAPP,
                conversa_id=chat["jid"],
                remetente=_pessoa(ultima["autor_jid"], ultima["autor_nome"], meu_jid),
                assunto=chat["nome"] or "",
                texto=ultima["texto"],
                recebido_em=datetime.fromtimestamp(ultima["enviada_em"], UTC),
                eh_grupo=bool(chat["eh_grupo"]),
                mencoes_a_mim=bool(ultima["menciona_me"]),
                metadados={"origem": "ponte"},
            )
            saida.append((item, historico))
        return saida
    finally:
        con.close()
