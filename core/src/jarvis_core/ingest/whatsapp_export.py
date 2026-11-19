"""Parser de exportação do WhatsApp em português (Android e iPhone).

O conector do OpenJarvis (connectors/whatsapp.py) só entende o formato americano com
AM/PM. Este cobre as duas variantes brasileiras:

    Android: 15/01/2024 10:30 - Alice: texto
    iPhone:  [15/01/2024, 10:30:12] Alice: texto

Mensagens com várias linhas continuam nas linhas seguintes sem carimbo de data. Linhas de
sistema (criptografia, "fulano entrou") não têm "Nome:" e são ignoradas.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis_core.models import Canal, Item, Mensagem, Pessoa

_INVISIVEIS = dict.fromkeys(map(ord, "\u200e\u200f\u202a\u202c\ufeff"), None)

_ANDROID = re.compile(
    r"^(?P<data>\d{1,2}/\d{1,2}/\d{2,4}),? (?P<hora>\d{1,2}:\d{2})(?::\d{2})? - (?P<resto>.*)$"
)
_IPHONE = re.compile(
    r"^\[(?P<data>\d{1,2}/\d{1,2}/\d{2,4}),? (?P<hora>\d{1,2}:\d{2})(?::\d{2})?\] (?P<resto>.*)$"
)
_AUTOR = re.compile(r"^(?P<autor>[^:]{1,80}): (?P<texto>.*)$")


def _data(data: str, hora: str, tz: ZoneInfo) -> datetime:
    dia, mes, ano = data.split("/")
    ano_i = int(ano) + 2000 if len(ano) == 2 else int(ano)
    h, mi = hora.split(":")
    return datetime(ano_i, int(mes), int(dia), int(h), int(mi), tzinfo=tz)


def parse_export(conteudo: str, meu_nome: str, fuso: str = "America/Sao_Paulo") -> list[Mensagem]:
    tz = ZoneInfo(fuso)
    mensagens: list[Mensagem] = []
    atual: Mensagem | None = None

    for bruta in conteudo.splitlines():
        linha = bruta.translate(_INVISIVEIS).rstrip()
        cab = _ANDROID.match(linha) or _IPHONE.match(linha)
        if cab:
            autor = _AUTOR.match(cab.group("resto"))
            if not autor:  # linha de sistema
                atual = None
                continue
            nome = autor.group("autor").strip()
            atual = Mensagem(
                autor=Pessoa(id=f"export:{nome}", nome=nome, eh_eu=nome == meu_nome),
                texto=autor.group("texto"),
                enviada_em=_data(cab.group("data"), cab.group("hora"), tz),
            )
            mensagens.append(atual)
        elif atual is not None and linha:
            atual.texto += "\n" + linha
    return mensagens


def item_da_conversa(nome_conversa: str, mensagens: list[Mensagem]) -> Item | None:
    """Gera o Item da conversa a partir da última mensagem recebida."""
    recebidas = [m for m in mensagens if not m.autor.eh_eu]
    if not recebidas:
        return None
    ultima = recebidas[-1]
    autores = {m.autor.id for m in mensagens if not m.autor.eh_eu}
    return Item(
        id=f"whatsapp-export:{nome_conversa}:{int(ultima.enviada_em.timestamp())}",
        canal=Canal.WHATSAPP,
        conversa_id=f"export:{nome_conversa}",
        remetente=ultima.autor,
        texto=ultima.texto,
        recebido_em=ultima.enviada_em,
        eh_grupo=len(autores) > 1,
        metadados={"origem": "exportacao"},
    )
