"""Agendador: fontes, avisos, resumo da manhã e laço principal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from conftest import ANA_JID, MEU_JID, criar_wa_db, item_wa

import jarvis_core.agendador as ag
from jarvis_core.agendador import Agendador, montar_resumo, notificar_mac
from jarvis_core.config import Config
from jarvis_core.models import Canal, Evento, Faixa, Pessoa
from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store

SP = ZoneInfo("America/Sao_Paulo")


@pytest.fixture
def chamadas(monkeypatch):
    """Captura avisos e falas em vez de chamar osascript/say."""
    registro: dict[str, list] = {"aviso": [], "fala": []}
    monkeypatch.setattr(ag, "notificar_mac", lambda t, x: registro["aviso"].append((t, x)))
    monkeypatch.setattr(ag, "falar", lambda t, v: registro["fala"].append((t, v)))
    return registro


@pytest.fixture
def agendador(jarvis_home, chamadas):
    store = Store(jarvis_home / "jarvis.db")
    a = Agendador(store)
    yield a
    store.fechar()


# --- utilitários do sistema -------------------------------------------------------------


def test_notificar_mac_escapa_aspas_e_barras(monkeypatch):
    rodou = {}
    monkeypatch.setattr(ag.subprocess, "run", lambda cmd, **kw: rodou.update(cmd=cmd, kw=kw))
    notificar_mac('Ana "RH"', "a\\b")
    script = rodou["cmd"][2]
    assert 'with title "Ana \\"RH\\""' in script
    assert '"a\\\\b"' in script
    assert rodou["kw"]["check"] is False


def test_falar_usa_say_sem_bloquear(monkeypatch):
    rodou = {}
    monkeypatch.setattr(ag.subprocess, "Popen", lambda cmd: rodou.update(cmd=cmd))
    ag.falar("oi", "Luciana")
    assert rodou["cmd"] == ["say", "-v", "Luciana", "oi"]


# --- resumo -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hora", "saudacao"), [(9, "Bom dia"), (14, "Boa tarde"), (20, "Boa noite")]
)
def test_resumo_saudacao_e_caixa_vazia(tmp_path, hora, saudacao):
    store = Store(tmp_path / "j.db")
    agora = datetime(2026, 11, 19, hora, 0, tzinfo=SP).astimezone(UTC)
    texto = montar_resumo(store, Config(), agora)
    assert texto.startswith(f"{saudacao}, Gabriel.")
    assert "Nada urgente" in texto


def test_resumo_lista_urgentes_e_agenda(tmp_path):
    store = Store(tmp_path / "j.db")
    agora = datetime(2026, 11, 19, 8, 0, tzinfo=SP).astimezone(UTC)
    it = item_wa("1", "URGENTE: entrevista hoje, pode confirmar?", agora=agora)
    store.salvar(it, triar(it, Contexto(agora=agora, vips={it.remetente.id})))
    gm = it.model_copy(update={"id": "gmail:2", "conversa_id": "g2", "canal": Canal.GMAIL})
    store.salvar(gm, triar(gm, Contexto(agora=agora, vips={it.remetente.id})))
    store.substituir_eventos(
        [
            Evento(
                id=f"e{i}",
                titulo=f"Aula {i}",
                inicio=agora + timedelta(hours=i),
                fim=agora + timedelta(hours=i, minutes=50),
            )
            for i in range(1, 5)
        ]
    )
    texto = montar_resumo(store, Config(), agora)
    assert "2 itens urgentes" in texto
    assert "no WhatsApp" in texto and "no e-mail" in texto
    assert "4 compromissos" in texto
    assert "Às 09:00, Aula 1." in texto and "Aula 4" not in texto  # só os 3 primeiros


# --- LLM --------------------------------------------------------------------------------


def test_llm_desligado(agendador):
    assert agendador._llm() is None
    assert agendador.store.get_estado("llm") == {"ok": False, "modelo": "desligado"}


def test_llm_e_consultado_no_maximo_uma_vez_por_minuto(agendador, monkeypatch):
    agendador.cfg.llm_ligado = True
    consultas = []
    monkeypatch.setattr(ag.Ollama, "disponivel", lambda self: consultas.append(1) or True)
    primeiro = agendador._llm()
    assert primeiro is not None and agendador._llm() is primeiro
    assert len(consultas) == 1
    agendador.ultimo["llm"] -= ag.INTERVALO_CHECAR_LLM_S
    monkeypatch.setattr(ag.Ollama, "disponivel", lambda self: False)
    assert agendador._llm() is None
    assert agendador.store.get_estado("llm")["ok"] is False


# --- fontes -----------------------------------------------------------------------------


def test_agenda_configurada_grava_eventos(agendador, monkeypatch):
    agendador.cfg.agenda_ics_urls = ["https://exemplo/agenda.ics"]
    ev = Evento(
        id="e1",
        titulo="PI VI",
        inicio=datetime.now(UTC) + timedelta(hours=1),
        fim=datetime.now(UTC) + timedelta(hours=2),
    )
    monkeypatch.setattr("jarvis_core.ingest.agenda_ics.ler_agendas", lambda urls, fuso: [ev])
    agendador.agenda()
    assert agendador.store.get_estado("fonte:agenda")["ok"] is True
    assert [e.titulo for e in agendador.store.eventos(ev.inicio, ev.fim)] == ["PI VI"]


def test_whatsapp_esperando_pareamento(agendador):
    criar_wa_db(agendador.cfg.wa_data_dir / "wa.db", [], meu_jid=None)
    agendador.whatsapp(datetime.now(UTC), None)
    assert "esperando" in agendador.store.get_estado("fonte:whatsapp")["detalhe"]


def test_whatsapp_pareado_processa_e_avisa(agendador, chamadas, monkeypatch):
    monkeypatch.setattr(ag, "em_silencio", lambda cfg, agora: False)
    agora = datetime.now(UTC)
    criar_wa_db(
        agendador.cfg.wa_data_dir / "wa.db",
        [
            (
                "m1",
                ANA_JID,
                ANA_JID,
                0,
                "URGENTE: entrevista hoje, pode confirmar?",
                timedelta(minutes=2),
            )
        ],
    )
    agendador.cfg.vips = {ANA_JID}
    agendador.whatsapp(agora, None)
    est = agendador.store.get_estado("fonte:whatsapp")
    assert est["ok"] is True and est["novos"] == 1
    assert agendador.store.get_estado("meu_jid") == MEU_JID
    assert len(chamadas["aviso"]) == 1  # faixa "agora", recente e fora do silêncio


def test_gmail_configurado(agendador, monkeypatch):
    agendador.cfg.gmail_usuario, agendador.cfg.gmail_senha_app = "eu@gmail.com", "x" * 16
    monkeypatch.setattr("jarvis_core.ingest.gmail_imap.ler_gmail", lambda u, s, d: [item_wa("9")])
    agendador.gmail(datetime.now(UTC), None)
    est = agendador.store.get_estado("fonte:gmail")
    assert est["ok"] is True and est["novos"] == 1
    assert agendador._contexto(datetime.now(UTC)).minhas_ids == {"eu@gmail.com"}


# --- avisos -----------------------------------------------------------------------------


def _triagem_agora(it):
    t = triar(it, Contexto(agora=datetime.now(UTC), vips={it.remetente.id}))
    assert t.faixa == Faixa.AGORA
    return t


def test_aviso_respeita_config_faixa_idade_e_silencio(agendador, chamadas, monkeypatch):
    it = item_wa("1", "URGENTE hoje, pode confirmar a entrevista?")
    t = _triagem_agora(it)
    monkeypatch.setattr(ag, "em_silencio", lambda cfg, agora: False)

    agendador.cfg.notificar = False
    agendador._ao_salvar(it, t)
    agendador.cfg.notificar = True
    agendador._ao_salvar(it, t.model_copy(update={"faixa": Faixa.HOJE}))
    agendador._ao_salvar(
        it.model_copy(update={"recebido_em": it.recebido_em - timedelta(hours=1)}), t
    )
    assert chamadas["aviso"] == []

    monkeypatch.setattr(ag, "em_silencio", lambda cfg, agora: True)
    agendador._ao_salvar(it, t)
    assert chamadas["aviso"] == []

    monkeypatch.setattr(ag, "em_silencio", lambda cfg, agora: False)
    agendador._ao_salvar(it, t)
    sem_nome = it.model_copy(update={"remetente": Pessoa(id="5511@s.whatsapp.net")})
    agendador._ao_salvar(sem_nome, t.model_copy(update={"motivo_llm": "pediu retorno"}))
    agendador._ao_salvar(it, t.model_copy(update={"motivos": []}))
    titulos = [a[0] for a in chamadas["aviso"]]
    assert titulos == ["Jarvis · Pessoa 1", "Jarvis · 5511", "Jarvis · Pessoa 1"]
    assert chamadas["aviso"][1][1].startswith("pediu retorno")


# --- resumo agendado --------------------------------------------------------------------


def _local(h: int, dia: int = 19) -> datetime:
    return datetime(2026, 11, dia, h, 0, tzinfo=SP).astimezone(UTC)


def test_resumo_antes_da_hora_nao_faz_nada(agendador, chamadas):
    agendador.resumo(_local(6))
    assert agendador.store.get_estado("resumo") is None


def test_resumo_da_manha_avisa_fala_e_so_uma_vez(agendador, chamadas):
    agendador.resumo(_local(8))
    agendador.resumo(_local(9))
    assert len(chamadas["aviso"]) == 1 and len(chamadas["fala"]) == 1
    agendador.cfg.resumo_falado = False
    agendador.resumo(_local(8, dia=20))
    assert len(chamadas["aviso"]) == 2 and len(chamadas["fala"]) == 1


def test_resumo_a_tarde_so_guarda(agendador, chamadas):
    agendador.resumo(_local(15))
    assert agendador.store.get_estado("resumo")
    assert chamadas == {"aviso": [], "fala": []}


# --- ciclo e laço -----------------------------------------------------------------------


def test_ciclo_isola_falhas_de_cada_fonte(agendador, monkeypatch, caplog):
    def explode(*a, **k):
        raise RuntimeError("caiu")

    monkeypatch.setattr(Agendador, "agenda", explode)
    monkeypatch.setattr(Agendador, "resumo", explode)
    agendador.ciclo()
    assert agendador.store.get_estado("fonte:agenda")["detalhe"] == "erro: caiu"
    assert agendador.store.get_estado("fonte:gmail")["detalhe"] == "não configurado"
    assert agendador.store.get_estado("agendador") == {"ok": True}
    assert "falha no resumo" in caplog.text
    agendador.ciclo()  # nada vencido: só o resumo roda de novo


def test_main_roda_o_laco(jarvis_home, monkeypatch, chamadas):
    class Parar(Exception):
        pass

    def dormir(_s):
        raise Parar

    monkeypatch.setattr(ag.time, "sleep", dormir)
    with pytest.raises(Parar):
        ag.main()
    assert (jarvis_home / "jarvis.db").exists()
