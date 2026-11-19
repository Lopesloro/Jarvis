"""Ramos restantes do motor de prioridade, do store e da config."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from conftest import item_wa

from jarvis_core.config import carregar
from jarvis_core.models import Canal, Evento, Faixa, Pessoa
from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store

AGORA = datetime.now(UTC)


def sinais(t):
    return {m.sinal: m.pontos for m in t.motivos}


def test_email_para_varias_pessoas_nao_e_conversa_direta():
    it = item_wa("1", "oi").model_copy(
        update={
            "canal": Canal.GMAIL,
            "destinatarios": [Pessoa(id="eu@x.com"), Pessoa(id="outro@x.com")],
        }
    )
    assert "conversa_direta" not in sinais(triar(it, Contexto(agora=AGORA)))


def test_item_de_agenda_nao_e_conversa_direta():
    it = item_wa("1", "oi").model_copy(update={"canal": Canal.AGENDA})
    assert "conversa_direta" not in sinais(triar(it, Contexto(agora=AGORA)))


def test_evento_nas_proximas_24h_vale_10_e_ignora_outros_participantes():
    it = item_wa("1", "oi")
    outro = Evento(
        id="e0",
        titulo="Outra",
        inicio=AGORA + timedelta(hours=1),
        fim=AGORA + timedelta(hours=2),
        participantes=[Pessoa(id="x")],
    )
    ev = Evento(
        id="e1",
        titulo="Aula",
        inicio=AGORA + timedelta(hours=5),
        fim=AGORA + timedelta(hours=6),
        participantes=[it.remetente],
    )
    assert sinais(triar(it, Contexto(agora=AGORA, eventos=[outro, ev])))["evento_proximo"] == 10


def test_listar_filtra_por_canal_e_decisao_adiar_mantem_item(tmp_path):
    store = Store(tmp_path / "j.db")
    wa = item_wa("1")
    gm = item_wa("2").model_copy(update={"canal": Canal.GMAIL})
    for it in (wa, gm):
        store.salvar(it, triar(it, Contexto(agora=AGORA)))
    assert [r["item"]["id"] for r in store.listar(canal="gmail")] == [gm.id]
    assert store.decidir(wa.id, "adiar", Faixa.SEMANA.value, "depois") is True
    assert store.obter(wa.id)["resolvido"] is False
    assert store.item_modelo("nao-existe") is None and store.obter("nao-existe") is None
    assert store.get_estado("nada", padrao=7) == 7
    store.fechar()


def test_config_com_permissao_aberta_e_corrigida(tmp_path, caplog):
    arq = tmp_path / "jarvis.toml"
    arq.write_text('[gmail]\nsenha_app = "x"\n', encoding="utf-8")
    arq.chmod(0o644)
    with caplog.at_level(logging.WARNING):
        carregar(arq)
    assert "legível por outros" in caplog.text
    assert arq.stat().st_mode & 0o777 == 0o600
