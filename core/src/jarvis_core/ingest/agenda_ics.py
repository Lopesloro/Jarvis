"""Agenda pelo "endereço secreto no formato iCal" do Google Agenda (ou qualquer .ics).

Sem OAuth: em Google Agenda → Configurações → (sua agenda) → Integrar agenda, copie o
"Endereço secreto no formato iCal" para [agenda] ics_urls no jarvis.toml.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import icalendar
import recurring_ical_events

from jarvis_core.models import Evento, Pessoa


def _para_utc(valor: date | datetime, fuso: ZoneInfo) -> datetime:
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=fuso)
        return valor.astimezone(UTC)
    # evento de dia inteiro: meia-noite no fuso local
    return datetime.combine(valor, time.min, tzinfo=fuso).astimezone(UTC)


def _participantes(comp: icalendar.cal.Component) -> list[Pessoa]:
    bruto = comp.get("ATTENDEE")
    lista = bruto if isinstance(bruto, list) else ([bruto] if bruto else [])
    saida = []
    for att in lista:
        endereco = str(att).split(":", 1)[-1].lower()
        saida.append(Pessoa(id=endereco, nome=str(att.params.get("CN", ""))))
    return saida


def eventos_do_ics(conteudo: bytes, inicio: datetime, fim: datetime, fuso: str) -> list[Evento]:
    tz = ZoneInfo(fuso)
    cal = icalendar.Calendar.from_ical(conteudo)
    saida: list[Evento] = []
    for comp in recurring_ical_events.of(cal).between(inicio, fim):
        ini = comp.get("DTSTART")
        if ini is None:
            continue
        fim_ev = comp.get("DTEND")
        ini_utc = _para_utc(ini.dt, tz)
        fim_utc = _para_utc(fim_ev.dt, tz) if fim_ev else ini_utc
        if fim_utc <= ini_utc:
            # Sem DTEND a biblioteca repete o início (duração zero): assume 1 h.
            fim_utc = ini_utc + timedelta(hours=1)
        uid = str(comp.get("UID", ""))
        chave = hashlib.sha1(f"{uid}|{ini_utc.isoformat()}".encode()).hexdigest()[:16]
        saida.append(
            Evento(
                id=f"agenda:{chave}",
                titulo=str(comp.get("SUMMARY", "(sem título)")),
                inicio=ini_utc,
                fim=fim_utc,
                participantes=_participantes(comp),
                local=str(comp.get("LOCATION", "")),
            )
        )
    return sorted(saida, key=lambda e: e.inicio)


def ler_agendas(urls: list[str], fuso: str, dias: int = 14) -> list[Evento]:
    agora = datetime.now(UTC)
    inicio, fim = agora - timedelta(days=1), agora + timedelta(days=dias)
    eventos: list[Evento] = []
    for url in urls:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        r.raise_for_status()
        eventos += eventos_do_ics(r.content, inicio, fim, fuso)
    return sorted(eventos, key=lambda e: e.inicio)
