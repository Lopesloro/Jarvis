"""Gmail por IMAP com senha de app, só leitura (BODY.PEEK não marca como lido).

Escolhido em vez do OAuth do OpenJarvis para não exigir projeto no Google Cloud: basta
ativar a verificação em duas etapas e gerar uma senha de app em
https://myaccount.google.com/apppasswords.
"""

from __future__ import annotations

import email
import imaplib
import re
from datetime import UTC, datetime, timedelta
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

from jarvis_core.models import Canal, Item, Pessoa

_RE_TAGS = re.compile(r"<[^>]+>")
_RE_ESPACO = re.compile(r"[ \t\r\f\v]+")
_RE_LABELS = re.compile(rb"X-GM-LABELS \(([^)]*)\)")
_RE_THRID = re.compile(rb"X-GM-THRID (\d+)")


def _decodificar(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except (UnicodeDecodeError, LookupError):
        return valor


def _texto_do_corpo(msg: Message, limite: int = 3000) -> str:
    texto_html = ""
    for parte in msg.walk() if msg.is_multipart() else [msg]:
        if parte.get_content_maintype() != "text" or parte.get_filename():
            continue
        try:
            bruto = parte.get_payload(decode=True) or b""
            conteudo = bruto.decode(parte.get_content_charset() or "utf-8", errors="replace")
        except LookupError:
            continue
        if parte.get_content_subtype() == "plain":
            return _RE_ESPACO.sub(" ", conteudo).strip()[:limite]
        if not texto_html:
            texto_html = _RE_ESPACO.sub(" ", _RE_TAGS.sub(" ", conteudo)).strip()
    return texto_html[:limite]


def mensagem_para_item(bruto: bytes, meta: bytes, meu_email: str) -> Item:
    msg = email.message_from_bytes(bruto)
    nome, endereco = parseaddr(_decodificar(msg.get("From")))
    destinatarios = [
        Pessoa(id=e.lower(), nome=n, eh_eu=e.lower() == meu_email.lower())
        for n, e in getaddresses([msg.get("To", ""), msg.get("Cc", "")])
        if e
    ]
    try:
        recebido = parsedate_to_datetime(msg.get("Date", "")).astimezone(UTC)
    except (TypeError, ValueError):
        recebido = datetime.now(UTC)
    labels_m = _RE_LABELS.search(meta)
    labels = (
        [lb.strip('"\\') for lb in labels_m.group(1).decode(errors="replace").split()]
        if labels_m
        else []
    )
    thr = _RE_THRID.search(meta)
    msg_id = (msg.get("Message-ID") or "").strip("<> ") or f"{endereco}-{recebido.timestamp()}"
    return Item(
        id=f"gmail:{msg_id}",
        canal=Canal.GMAIL,
        conversa_id=f"gmail-thread:{thr.group(1).decode()}" if thr else f"gmail:{msg_id}",
        remetente=Pessoa(
            id=endereco.lower(), nome=nome, eh_eu=endereco.lower() == meu_email.lower()
        ),
        assunto=_decodificar(msg.get("Subject")),
        texto=_texto_do_corpo(msg),
        recebido_em=recebido,
        destinatarios=destinatarios,
        metadados={
            "origem": "imap",
            "labels": labels,
            "list_unsubscribe": bool(msg.get("List-Unsubscribe")),
        },
    )


def ler_gmail(usuario: str, senha_app: str, dias: int = 3, maximo: int = 200) -> list[Item]:
    """E-mails da caixa de entrada dos últimos `dias` (os mais recentes primeiro)."""
    desde = (datetime.now(UTC) - timedelta(days=dias)).strftime("%d-%b-%Y")
    itens: list[Item] = []
    with imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30) as imap:
        imap.login(usuario, senha_app)
        imap.select("INBOX", readonly=True)
        _, dados = imap.search(None, "SINCE", desde)
        ids = (dados[0] or b"").split()[-maximo:]
        for num in reversed(ids):
            _, partes = imap.fetch(num, "(X-GM-LABELS X-GM-THRID BODY.PEEK[])")
            for parte in partes:
                if isinstance(parte, tuple):
                    itens.append(mensagem_para_item(parte[1], parte[0], usuario))
    return itens
