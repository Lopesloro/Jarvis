"""Rotas da API que faltavam cobrir: interface, resumo, voz, rascunho com histórico, app do ambiente."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from conftest import ANA_JID, criar_wa_db, item_wa
from fastapi.testclient import TestClient

import jarvis_core.agendador as ag
from jarvis_core.api import main as api_main
from jarvis_core.api.main import _ponte, create_app
from jarvis_core.config import Config
from jarvis_core.models import Item
from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store

TOKEN = "t" * 40
H = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def montar(tmp_path):
    def _montar(itens: list[Item] = ()) -> tuple[TestClient, Store, Config]:
        store = Store(tmp_path / "j.db")
        for it in itens:
            store.salvar(it, triar(it, Contexto(agora=it.recebido_em)))
        cfg = Config(wa_data_dir=tmp_path / "wa")
        cfg.wa_data_dir.mkdir(exist_ok=True)
        return TestClient(create_app(store, TOKEN, cfg_loader=lambda: cfg)), store, cfg

    return _montar


def test_ponte_sem_status_com_status_invalido_e_qr_ausente(tmp_path):
    cfg = Config(wa_data_dir=tmp_path)
    assert _ponte(cfg) == {"status": "parada", "qr_svg": None}
    (tmp_path / "status.json").write_text("{quebrado")
    assert _ponte(cfg)["status"] == "parada"
    (tmp_path / "status.json").write_text('{"status": "qr"}')
    assert _ponte(cfg)["qr_svg"] is None  # QR ainda não gravado
    (tmp_path / "status.json").write_text('{"status": "connected"}')
    (tmp_path / "qr.txt").write_text("velho")
    assert _ponte(cfg)["qr_svg"] is None  # conectado: QR antigo é ignorado


def test_interface_manifesto_e_icone_sem_token(montar):
    c, _, _ = montar()
    assert "<html" in c.get("/").text.lower()
    assert (
        c.get("/manifest.webmanifest")
        .headers["content-type"]
        .startswith("application/manifest+json")
    )
    assert c.get("/icone.svg").headers["content-type"].startswith("image/svg+xml")


def test_decisao_em_item_inexistente(montar):
    c, _, _ = montar()
    r = c.post("/v1/itens/nao-existe/decisao", headers=H, json={"decisao": "resolver"})
    assert r.status_code == 404


def test_rascunho_de_item_inexistente(montar):
    c, _, _ = montar()
    assert c.post("/v1/itens/nao-existe/rascunho", headers=H).status_code == 404


def test_rascunho_do_whatsapp_usa_historico_da_conversa(montar, monkeypatch):
    it = item_wa("1").model_copy(update={"conversa_id": ANA_JID})
    c, _, cfg = montar([it])
    criar_wa_db(
        cfg.wa_data_dir / "wa.db",
        [
            ("a", ANA_JID, ANA_JID, 0, "Oi", timedelta(minutes=5)),
            ("b", ANA_JID, "eu", 1, "Fala", timedelta(minutes=4)),
        ],
    )
    visto = {}

    def rascunho(self, item, ctx):
        visto["historico"] = [m.texto for m in ctx.historico]
        return "Pode sim"

    monkeypatch.setattr("jarvis_core.llm.Ollama.rascunho", rascunho)
    assert c.post(f"/v1/itens/{it.id}/rascunho", headers=H).json() == {"rascunho": "Pode sim"}
    assert visto["historico"] == ["Oi", "Fala"]


def test_resumo_e_falar(montar, monkeypatch):
    c, _, _ = montar([item_wa("1")])
    falas = []
    monkeypatch.setattr(ag, "falar", lambda texto, voz: falas.append(voz))
    assert "Gabriel" in c.get("/v1/resumo", headers=H).json()["texto"]
    assert "Gabriel" in c.post("/v1/falar", headers=H).json()["texto"]
    assert falas == ["Luciana"]


def test_resumo_e_status_em_paralelo_nao_quebram(montar):
    """Regressão: IndexError no /v1/resumo com requisições simultâneas."""
    c, _, _ = montar([item_wa(str(i)) for i in range(20)])
    rotas = ["/v1/resumo", "/v1/status", "/v1/inbox", "/v1/agora"] * 25
    with ThreadPoolExecutor(max_workers=8) as pool:
        codigos = list(pool.map(lambda r: c.get(r, headers=H).status_code, rotas))
    assert set(codigos) == {200}


def test_app_do_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_TOKEN", TOKEN)
    app = api_main.app  # criada na hora pelo __getattr__ do módulo
    assert TestClient(app).get("/saude").json()["ok"] is True
    assert (tmp_path / "jarvis.db").exists()
    with pytest.raises(AttributeError):
        api_main.nao_existe  # noqa: B018
