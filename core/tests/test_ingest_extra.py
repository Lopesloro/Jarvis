"""Casos de borda da coleta: Gmail (IMAP), agenda (.ics) e leitura do wa.db."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import ClassVar

import pytest
from conftest import ANA_JID, MEU_JID, criar_wa_db

from jarvis_core.ingest import agenda_ics, gmail_imap
from jarvis_core.ingest.gmail_imap import _decodificar, _texto_do_corpo, mensagem_para_item
from jarvis_core.ingest.whatsapp_bridge import historico_da_conversa, ler_conversas
from jarvis_core.ingest.whatsapp_export import parse_export

# --- Gmail ------------------------------------------------------------------------------


def test_decodificar_vazio_e_charset_desconhecido():
    assert _decodificar(None) == "" and _decodificar("") == ""
    assert _decodificar("=?x-inexistente?q?oi?=") == "=?x-inexistente?q?oi?="


def test_corpo_so_html_vira_texto_e_ignora_anexo():
    msg = EmailMessage()
    msg.set_content("<p>Ol&aacute; <b>Gabriel</b></p>", subtype="html")
    msg.add_attachment(b"%PDF", maintype="application", subtype="pdf", filename="cv.pdf")
    msg.add_attachment("texto do anexo", filename="nota.txt")
    assert _texto_do_corpo(msg) == "Ol&aacute; Gabriel"


def test_corpo_com_charset_invalido_e_pulado():
    msg = EmailMessage()
    msg.set_content("primeiro")
    msg.add_alternative("<p>segundo</p>", subtype="html")
    msg.get_payload()[0].set_param("charset", "x-nao-existe")
    assert _texto_do_corpo(msg) == "segundo"


def test_email_sem_data_message_id_e_thread():
    msg = EmailMessage()
    msg["From"] = "Ana <ana@x.com>"
    msg.set_content("oi")
    item = mensagem_para_item(msg.as_bytes(), b"", "eu@gmail.com")
    assert item.id.startswith("gmail:ana@x.com-")
    assert item.conversa_id == item.id
    assert abs((item.recebido_em - datetime.now(UTC)).total_seconds()) < 5


class ImapFalso:
    """Imita imaplib.IMAP4_SSL o suficiente para ler_gmail."""

    instancias: ClassVar[list[ImapFalso]] = []

    def __init__(self, host, porta, timeout):
        self.host, self.chamadas = host, []
        ImapFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, u, s):
        self.chamadas.append(("login", u))

    def select(self, caixa, readonly):
        self.chamadas.append(("select", caixa, readonly))

    def search(self, charset, *criterios):
        self.chamadas.append(("search", criterios))
        return "OK", [b"1 2"]

    def fetch(self, num, partes):
        self.chamadas.append(("fetch", num, partes))
        msg = EmailMessage()
        msg["From"] = f"pessoa{num.decode()}@x.com"
        msg["Message-ID"] = f"<{num.decode()}@x>"
        msg.set_content("oi")
        return "OK", [(b"1 (X-GM-THRID 99 X-GM-LABELS (\\\\Inbox))", msg.as_bytes()), b")"]


def test_ler_gmail_so_leitura_e_mais_recentes_primeiro(monkeypatch):
    monkeypatch.setattr(gmail_imap.imaplib, "IMAP4_SSL", ImapFalso)
    itens = gmail_imap.ler_gmail("eu@gmail.com", "senha", dias=2)
    imap = ImapFalso.instancias[-1]
    assert imap.host == "imap.gmail.com"
    assert ("select", "INBOX", True) in imap.chamadas  # readonly
    assert all("BODY.PEEK" in c[2] for c in imap.chamadas if c[0] == "fetch")  # não marca lido
    assert [i.remetente.id for i in itens] == ["pessoa2@x.com", "pessoa1@x.com"]
    assert itens[0].conversa_id == "gmail-thread:99"


# --- agenda -----------------------------------------------------------------------------

ICS_LOCAL = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:a@x
DTSTART:20261120T100000
SUMMARY:Sem fuso e sem fim
END:VEVENT
END:VCALENDAR
"""


def test_evento_sem_fuso_usa_o_local_e_sem_fim_dura_uma_hora():
    ini = datetime(2026, 11, 20, tzinfo=UTC)
    (ev,) = agenda_ics.eventos_do_ics(ICS_LOCAL, ini, ini + timedelta(days=1), "America/Sao_Paulo")
    assert ev.inicio == datetime(2026, 11, 20, 13, 0, tzinfo=UTC)
    assert ev.fim - ev.inicio == timedelta(hours=1)


def test_componente_sem_inicio_e_ignorado(monkeypatch):
    class SemInicio(dict):
        pass

    class Falso:
        def between(self, a, b):
            return [SemInicio()]

    monkeypatch.setattr(agenda_ics.recurring_ical_events, "of", lambda cal: Falso())
    ini = datetime(2026, 11, 20, tzinfo=UTC)
    assert agenda_ics.eventos_do_ics(ICS_LOCAL, ini, ini, "America/Sao_Paulo") == []


def test_ler_agendas_baixa_cada_url(monkeypatch):
    urls = []

    class Resp:
        content = ICS_LOCAL

        def raise_for_status(self):
            pass

    def get(url, timeout, follow_redirects):
        urls.append(url)
        return Resp()

    monkeypatch.setattr(agenda_ics.httpx, "get", get)
    agenda_ics.ler_agendas(["https://a", "https://b"], "America/Sao_Paulo", dias=10_000)
    assert urls == ["https://a", "https://b"]


# --- WhatsApp ---------------------------------------------------------------------------


def test_conversa_so_com_mensagens_minhas_nao_vira_item(tmp_path):
    db = criar_wa_db(tmp_path / "wa.db", [("a", ANA_JID, MEU_JID, 1, "oi", timedelta(minutes=1))])
    assert ler_conversas(db, datetime.now(UTC) - timedelta(days=1)) == []


def test_wa_db_sem_meu_jid(tmp_path):
    db = criar_wa_db(
        tmp_path / "wa.db", [("a", ANA_JID, ANA_JID, 0, "oi", timedelta(minutes=1))], meu_jid=None
    )
    ((item, _),) = ler_conversas(db, datetime.now(UTC) - timedelta(days=1))
    assert item.remetente.eh_eu is False
    assert historico_da_conversa(db, ANA_JID)[0].texto == "oi"


def test_historico_em_ordem_e_com_limite(tmp_path):
    msgs = [
        (f"m{i}", ANA_JID, MEU_JID if i % 2 else ANA_JID, i % 2, f"t{i}", timedelta(minutes=10 - i))
        for i in range(6)
    ]
    db = criar_wa_db(tmp_path / "wa.db", msgs)
    hist = historico_da_conversa(db, ANA_JID, limite=3)
    assert [m.texto for m in hist] == ["t3", "t4", "t5"]
    assert [m.autor.eh_eu for m in hist] == [True, False, True]


def test_exportacao_com_linha_em_branco_no_meio_da_mensagem():
    msgs = parse_export("15/01/2024 10:30 - Ana: linha 1\n\nlinha 2", meu_nome="Gabriel")
    assert msgs[0].texto == "linha 1\nlinha 2"


@pytest.mark.parametrize("linha", ["sem cabeçalho antes", ""])
def test_exportacao_ignora_texto_solto_no_inicio(linha):
    assert parse_export(linha, meu_nome="Gabriel") == []


def test_corpo_com_dois_html_usa_o_primeiro():
    msg = EmailMessage()
    msg.set_content("<p>primeiro</p>", subtype="html")
    msg.add_alternative("<p>segundo</p>", subtype="html")
    assert _texto_do_corpo(msg) == "primeiro"
