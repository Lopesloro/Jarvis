"""Ajudantes compartilhados: wa.db no formato da ponte e itens prontos."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from jarvis_core.models import Canal, Item, Pessoa

MEU_JID = "5519999990000@s.whatsapp.net"
ANA_JID = "5511988887777@s.whatsapp.net"

# Mesmo esquema de bridge/whatsapp/src/store.ts
ESQUEMA_WA = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE chats (jid TEXT PRIMARY KEY, nome TEXT, eh_grupo INTEGER, atualizado_em INTEGER);
CREATE TABLE contatos (jid TEXT PRIMARY KEY, nome TEXT);
CREATE TABLE mensagens (id TEXT, jid TEXT, autor_jid TEXT, de_mim INTEGER, tipo TEXT,
  texto TEXT, menciona_me INTEGER, enviada_em INTEGER, PRIMARY KEY (jid, id));
"""


def criar_wa_db(
    caminho: Path,
    mensagens: list[tuple[str, str, str, int, str, timedelta]],
    meu_jid: str | None = MEU_JID,
    agora: datetime | None = None,
) -> Path:
    """mensagens: (id, jid_da_conversa, autor_jid, de_mim, texto, há quanto tempo)."""
    agora = agora or datetime.now(UTC)
    con = sqlite3.connect(caminho)
    con.executescript(ESQUEMA_WA)
    if meu_jid:
        con.execute("INSERT INTO meta VALUES ('meu_jid', ?)", (meu_jid,))
    for mid, jid, autor, de_mim, texto, ha in mensagens:
        ts = int((agora - ha).timestamp())
        con.execute(
            "INSERT INTO chats VALUES (?, NULL, 0, ?) ON CONFLICT(jid) DO UPDATE SET "
            "atualizado_em = MAX(atualizado_em, excluded.atualizado_em)",
            (jid, ts),
        )
        con.execute(
            "INSERT INTO mensagens VALUES (?, ?, ?, ?, 'texto', ?, 0, ?)",
            (mid, jid, autor, de_mim, texto, ts),
        )
    con.commit()
    con.close()
    return caminho


def item_wa(
    i: str,
    texto: str = "Pode me ligar? É urgente",
    ha: timedelta | None = None,
    agora: datetime | None = None,
) -> Item:
    agora = agora or datetime.now(UTC)
    return Item(
        id=f"whatsapp:{i}",
        canal=Canal.WHATSAPP,
        conversa_id=f"c{i}",
        remetente=Pessoa(id=f"55119{i}@s.whatsapp.net", nome=f"Pessoa {i}"),
        texto=texto,
        recebido_em=agora - (ha or timedelta(minutes=1)),
    )


@pytest.fixture
def jarvis_home(tmp_path, monkeypatch):
    """JARVIS_HOME isolado, com o LLM desligado e a ponte apontando para tmp."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / "jarvis.toml").write_text(
        '[llm]\nligado = false\n[whatsapp]\ndata_dir = "' + str(tmp_path / "wa") + '"\n',
        encoding="utf-8",
    )
    (tmp_path / "jarvis.toml").chmod(0o600)
    (tmp_path / "wa").mkdir()
    return tmp_path
