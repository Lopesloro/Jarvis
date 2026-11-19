"""Integração: wa.db no formato da ponte → pipeline → store → API."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from jarvis_core.api.main import create_app
from jarvis_core.pipeline import processar_whatsapp
from jarvis_core.priority import Contexto
from jarvis_core.store import Store

TOKEN = "t" * 40
AGORA = datetime.now(UTC)
MEU = "5519999990000@s.whatsapp.net"
ANA = "5511988887777@s.whatsapp.net"

# Mesmo esquema de bridge/whatsapp/src/store.ts
ESQUEMA = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE chats (jid TEXT PRIMARY KEY, nome TEXT, eh_grupo INTEGER, atualizado_em INTEGER);
CREATE TABLE contatos (jid TEXT PRIMARY KEY, nome TEXT);
CREATE TABLE mensagens (id TEXT, jid TEXT, autor_jid TEXT, de_mim INTEGER, tipo TEXT,
  texto TEXT, menciona_me INTEGER, enviada_em INTEGER, PRIMARY KEY (jid, id));
"""


@pytest.fixture
def wa_db(tmp_path):
    caminho = tmp_path / "wa.db"
    con = sqlite3.connect(caminho)
    con.executescript(ESQUEMA)

    def ts(d):
        return int((AGORA - d).timestamp())

    con.execute("INSERT INTO meta VALUES ('meu_jid', ?)", (MEU,))
    con.execute("INSERT INTO chats VALUES (?, 'Ana (RH)', 0, ?)", (ANA, ts(timedelta(minutes=5))))
    con.execute("INSERT INTO contatos VALUES (?, 'Ana (RH)')", (ANA,))
    con.executemany(
        "INSERT INTO mensagens VALUES (?, ?, ?, ?, 'texto', ?, 0, ?)",
        [
            ("m1", ANA, ANA, 0, "Oi Gabriel, tudo bem?", ts(timedelta(hours=3))),
            ("m2", ANA, MEU, 1, "Tudo! Pode falar", ts(timedelta(hours=2))),
            (
                "m3",
                ANA,
                ANA,
                0,
                "Pode confirmar a entrevista até hoje 18h?",
                ts(timedelta(minutes=5)),
            ),
        ],
    )
    con.commit()
    con.close()
    return caminho


def test_ponta_a_ponta(wa_db, tmp_path):
    store = Store(tmp_path / "jarvis.db")
    n = processar_whatsapp(wa_db, store, Contexto(agora=AGORA), AGORA - timedelta(days=1))
    assert n == 1

    api = TestClient(create_app(store, TOKEN))
    assert api.get("/v1/agora").status_code == 401

    cab = {"Authorization": f"Bearer {TOKEN}"}
    agora = api.get("/v1/agora", headers=cab).json()
    assert len(agora) == 1
    triagem = agora[0]["triagem"]
    assert triagem["faixa"] == "agora"
    sinais = {m["sinal"] for m in triagem["motivos"]}
    assert "contato_conhecido" in sinais  # você já respondeu essa pessoa antes

    item_id = agora[0]["item"]["id"]
    r = api.post(f"/v1/itens/{item_id}/decisao", headers=cab, json={"decisao": "resolver"})
    assert r.status_code == 200
    assert api.get("/v1/agora", headers=cab).json() == []


def test_token_curto_e_recusado(tmp_path):
    with pytest.raises(ValueError):
        create_app(Store(tmp_path / "j.db"), "curto")
