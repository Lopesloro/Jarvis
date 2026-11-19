"""Testes das peças adicionadas para rodar o Jarvis no Mac: config, Gmail, agenda,
refinador local, agendador e rotas novas da API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from jarvis_core.agendador import Agendador, em_silencio, montar_resumo
from jarvis_core.api.main import create_app
from jarvis_core.config import Config, carregar
from jarvis_core.ingest.agenda_ics import eventos_do_ics
from jarvis_core.ingest.gmail_imap import mensagem_para_item
from jarvis_core.models import Canal, Faixa, Item, Pessoa
from jarvis_core.pipeline import processar
from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store

TOKEN = "t" * 40
AGORA = datetime.now(UTC)


# --- config ----------------------------------------------------------------------------


def test_config_le_toml_e_tem_padroes(tmp_path):
    assert carregar(tmp_path / "nao-existe.toml").llm_modelo == "qwen2.5:3b"
    arq = tmp_path / "jarvis.toml"
    arq.write_text(
        '[prioridade]\nvips = ["ana@x.com"]\n[gmail]\nusuario = "eu@gmail.com"\n'
        'senha_app = "abcd efgh ijkl mnop"\n[agenda]\nics_urls = ["https://x/a.ics"]\n',
        encoding="utf-8",
    )
    cfg = carregar(arq)
    assert cfg.vips == {"ana@x.com"}
    assert cfg.gmail_senha_app == "abcdefghijklmnop"  # espaços da senha de app saem
    assert cfg.agenda_ics_urls == ["https://x/a.ics"]


# --- gmail -----------------------------------------------------------------------------


def _email(**cab: str) -> bytes:
    msg = EmailMessage()
    for k, v in cab.items():
        msg[k.replace("_", "-")] = v
    msg.set_content("Oi Gabriel, consegue me mandar a proposta até amanhã?")
    return msg.as_bytes()


def test_gmail_vira_item_com_thread_e_labels():
    bruto = _email(
        From="Ana Souza <Ana@Empresa.com>",
        To="eu@gmail.com",
        Subject="=?utf-8?q?Proposta_revis=C3=A3o?=",
        Date="Wed, 19 Nov 2026 10:00:00 -0300",
        Message_ID="<abc@empresa.com>",
    )
    meta = b'1 (X-GM-THRID 999 X-GM-LABELS ("\\\\Inbox") '
    item = mensagem_para_item(bruto, meta, "eu@gmail.com")
    assert item.canal == Canal.GMAIL
    assert item.remetente.id == "ana@empresa.com"
    assert item.assunto == "Proposta revisão"
    assert item.conversa_id == "gmail-thread:999"
    assert item.recebido_em == datetime(2026, 11, 19, 13, 0, tzinfo=UTC)
    assert "proposta" in item.texto
    assert item.metadados["list_unsubscribe"] is False


def test_gmail_newsletter_e_marcado_automatico():
    bruto = _email(
        From="loja@promo.com", To="eu@gmail.com", Subject="Só hoje!", List_Unsubscribe="<x>"
    )
    item = mensagem_para_item(bruto, b"", "eu@gmail.com")
    triagem = triar(item, Contexto(agora=AGORA))
    assert triagem.faixa == Faixa.ARQUIVAR
    assert any(m.sinal == "automatico" for m in triagem.motivos)


# --- agenda ----------------------------------------------------------------------------

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:1@x
DTSTART:20261120T130000Z
DTEND:20261120T140000Z
SUMMARY:Reuniao com Ana
ATTENDEE;CN=Ana:mailto:ana@empresa.com
END:VEVENT
BEGIN:VEVENT
UID:2@x
DTSTART;VALUE=DATE:20261121
DTEND;VALUE=DATE:20261122
SUMMARY:Feriado
END:VEVENT
BEGIN:VEVENT
UID:3@x
DTSTART:20261117T120000Z
DTEND:20261117T123000Z
RRULE:FREQ=DAILY;COUNT=10
SUMMARY:Daily
END:VEVENT
END:VCALENDAR
"""


def test_agenda_ics_participantes_dia_inteiro_e_recorrencia():
    ini = datetime(2026, 11, 20, tzinfo=UTC)
    evs = eventos_do_ics(ICS, ini, ini + timedelta(days=2), "America/Sao_Paulo")
    titulos = [e.titulo for e in evs]
    assert titulos.count("Daily") == 2  # 20 e 21
    reuniao = next(e for e in evs if e.titulo == "Reuniao com Ana")
    assert reuniao.participantes[0].id == "ana@empresa.com"
    feriado = next(e for e in evs if e.titulo == "Feriado")
    assert feriado.inicio == datetime(2026, 11, 21, 3, 0, tzinfo=UTC)  # meia-noite em SP


# --- refinador e pipeline --------------------------------------------------------------


class RefinadorFalso:
    def __init__(self, ajuste: int) -> None:
        self.ajuste = ajuste
        self.chamadas = 0

    def refinar(self, item, ctx, base):
        self.chamadas += 1
        return self.ajuste, "teste"


def _item(i: str, texto: str = "Pode me ligar? É urgente", minutos: int = 1) -> Item:
    return Item(
        id=f"whatsapp:{i}",
        canal=Canal.WHATSAPP,
        conversa_id=f"c{i}",
        remetente=Pessoa(id=f"55119{i}@s.whatsapp.net", nome=f"Pessoa {i}"),
        texto=texto,
        recebido_em=AGORA - timedelta(minutes=minutos),
    )


def test_pipeline_usa_llm_limitado_e_pula_existentes(tmp_path):
    store = Store(tmp_path / "j.db")
    ref = RefinadorFalso(99)
    salvos: list[str] = []
    ctx = Contexto(agora=AGORA)
    n = processar([(_item("1"), [])], store, ctx, ref, True, lambda i, t: salvos.append(i.id))
    assert n == 1 and salvos == ["whatsapp:1"]
    tr = store.obter("whatsapp:1")["triagem"]
    assert tr["ajuste_llm"] == 20  # limitado a ±20
    assert processar([(_item("1"), [])], store, ctx, ref, True) == 0
    assert ref.chamadas == 1


def test_pipeline_nao_gasta_llm_com_ruido(tmp_path):
    store = Store(tmp_path / "j.db")
    ref = RefinadorFalso(5)
    item = _item("2", texto="kkk", minutos=60 * 24 * 10).model_copy(update={"eh_grupo": True})
    processar([(item, [])], store, Contexto(agora=AGORA), ref)
    assert ref.chamadas == 0


# --- agendador -------------------------------------------------------------------------


def test_silencio_atravessa_meia_noite():
    cfg = Config(silencio_inicio="23:00", silencio_fim="07:00")
    assert em_silencio(cfg, datetime(2026, 11, 19, 23, 30))
    assert em_silencio(cfg, datetime(2026, 11, 19, 6, 59))
    assert not em_silencio(cfg, datetime(2026, 11, 19, 12, 0))


def test_resumo_cita_urgentes(tmp_path):
    store = Store(tmp_path / "j.db")
    processar([(_item("3"), [])], store, Contexto(agora=AGORA))
    texto = montar_resumo(store, Config(), AGORA)
    assert "Gabriel" in texto


def test_agendador_registra_fontes_nao_configuradas(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / "jarvis.toml").write_text(
        '[llm]\nligado = false\n[whatsapp]\ndata_dir = "' + str(tmp_path / "wa") + '"\n',
        encoding="utf-8",
    )
    store = Store(tmp_path / "j.db")
    monkeypatch.setattr("jarvis_core.agendador.notificar_mac", lambda *a: None)
    monkeypatch.setattr("jarvis_core.agendador.falar", lambda *a: None)
    Agendador(store).ciclo()
    est = store.estado()
    assert est["fonte:gmail"]["valor"]["detalhe"] == "não configurado"
    assert est["fonte:agenda"]["valor"]["ok"] is False
    assert est["fonte:whatsapp"]["valor"]["ok"] is False


# --- API -------------------------------------------------------------------------------


@pytest.fixture
def cliente(tmp_path):
    store = Store(tmp_path / "j.db")
    processar([(_item("4"), [])], store, Contexto(agora=AGORA))
    cfg = Config(wa_data_dir=tmp_path / "wa")
    (tmp_path / "wa").mkdir()
    (tmp_path / "wa" / "status.json").write_text('{"status": "qr"}')
    (tmp_path / "wa" / "qr.txt").write_text("2@abc,def")
    app = create_app(store, TOKEN, cfg_loader=lambda: cfg)
    return TestClient(app), {"Authorization": f"Bearer {TOKEN}"}


ROTAS_PROTEGIDAS = [
    ("get", "/v1/status"),
    ("get", "/v1/agenda"),
    ("get", "/v1/resumo"),
    ("get", "/v1/itens/whatsapp:4"),
    ("post", "/v1/itens/whatsapp:4/rascunho"),
    ("post", "/v1/falar"),
]


@pytest.mark.parametrize(("metodo", "rota"), ROTAS_PROTEGIDAS)
def test_rotas_novas_exigem_token(cliente, metodo, rota):
    c, _ = cliente
    assert getattr(c, metodo)(rota).status_code == 401


def test_interface_e_servida_sem_token(cliente):
    c, _ = cliente
    r = c.get("/")
    assert r.status_code == 200 and "JARVIS" in r.text
    assert c.get("/manifest.webmanifest").status_code == 200


def test_status_mostra_qr_da_ponte(cliente):
    c, h = cliente
    s = c.get("/v1/status", headers=h).json()
    assert s["ponte"]["status"] == "qr"
    assert "<svg" in s["ponte"]["qr_svg"]
    assert s["contagem"]


def test_item_detalhe_e_agenda_vazia(cliente):
    c, h = cliente
    d = c.get("/v1/itens/whatsapp:4", headers=h).json()
    assert d["item"]["id"] == "whatsapp:4" and d["rascunho"] is None
    assert c.get("/v1/itens/nao-existe", headers=h).status_code == 404
    assert c.get("/v1/agenda", headers=h).json() == []


def test_rascunho_sem_ollama_responde_503(cliente, monkeypatch):
    c, h = cliente

    def falha(self, item, ctx):
        raise ConnectionError("sem ollama")

    monkeypatch.setattr("jarvis_core.llm.Ollama.rascunho", falha)
    assert c.post("/v1/itens/whatsapp:4/rascunho", headers=h).status_code == 503


def test_rascunho_e_salvo_e_nunca_enviado(cliente, monkeypatch):
    c, h = cliente
    monkeypatch.setattr("jarvis_core.llm.Ollama.rascunho", lambda self, i, ctx: "Oi! [hora]")
    r = c.post("/v1/itens/whatsapp:4/rascunho", headers=h)
    assert r.json() == {"rascunho": "Oi! [hora]"}
    assert c.get("/v1/itens/whatsapp:4", headers=h).json()["rascunho"] == "Oi! [hora]"
