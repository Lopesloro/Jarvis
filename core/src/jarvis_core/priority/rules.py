"""Sinais determinísticos do motor de prioridade.

Cada sinal recebe o item e o contexto e devolve zero ou um Motivo. A tabela de pesos
está documentada em docs/03-motor-prioridade.md e deve mudar junto com este arquivo.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from jarvis_core.models import Canal, Evento, Item, Mensagem, Motivo

VERSAO_REGRAS = "2026.11-v1"


@dataclass
class Contexto:
    """O que o motor sabe além do item em si."""

    agora: datetime
    minhas_ids: set[str] = field(default_factory=set)
    vips: set[str] = field(default_factory=set)
    contatos_conhecidos: set[str] = field(default_factory=set)
    historico: list[Mensagem] = field(default_factory=list)  # ordem cronológica
    eventos: list[Evento] = field(default_factory=list)


def normalizar(texto: str) -> str:
    """Minúsculas e sem acento, para casar 'Reunião' com 'reuniao'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


def _regex(*termos: str) -> re.Pattern[str]:
    return re.compile(r"(?<!\w)(" + "|".join(termos) + r")(?!\w)")


RE_URGENCIA = _regex(
    "urgente",
    "urgencia",
    "emergencia",
    "asap",
    "o quanto antes",
    "agora mesmo",
    "pra ja",
    "para ja",
    "imediato",
    "imediatamente",
)
RE_PRAZO = re.compile(
    r"(?<!\w)(hoje|amanha|prazo|vence|vencimento|deadline|ate (o fim do dia|amanha|hoje|segunda|"
    r"terca|quarta|quinta|sexta|sabado|domingo)|ate \d{1,2}(/\d{1,2}|h))(?!\w)"
)
RE_OPORTUNIDADE = _regex(
    "entrevista",
    "vaga",
    "estagio",
    "proposta",
    "contrato",
    "processo seletivo",
    "oferta",
    "recrutador",
    "recrutadora",
)
RE_FINANCEIRO = _regex("boleto", "pix", "fatura", "cobranca", "pagamento", "pagar")
RE_PEDIDO = _regex(
    "pode",
    "podes",
    "poderia",
    "consegue",
    "conseguiria",
    "preciso",
    "precisamos",
    "por favor",
    "favor",
    "me manda",
    "me envia",
    "aguardo",
    "confirma",
    "confirme",
)
RE_AGENDAR = _regex(
    "reuniao",
    "marcar",
    "horario",
    "disponibilidade",
    "call",
    "encontro",
    "agendar",
)
RE_AUTOMATICO_REMETENTE = re.compile(
    r"(no-?reply|nao-?responda|naoresponda|notifications?|notificacoes|mailer-daemon|newsletter)"
)
LABELS_AUTOMATICAS = {"CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"}


def _texto(item: Item) -> str:
    return normalizar(f"{item.assunto}\n{item.texto}")


def _m(sinal: str, pontos: int, explicacao: str) -> Motivo:
    return Motivo(sinal=sinal, pontos=pontos, explicacao=explicacao)


def _ultima_mensagem_eh_minha(ctx: Contexto) -> bool:
    return bool(ctx.historico) and ctx.historico[-1].autor.eh_eu


def eh_automatico(item: Item) -> bool:
    if RE_AUTOMATICO_REMETENTE.search(normalizar(item.remetente.id)):
        return True
    if item.metadados.get("list_unsubscribe"):
        return True
    labels = set(item.metadados.get("labels", []))
    return bool(labels & LABELS_AUTOMATICAS)


def aguardando_resposta(item: Item, ctx: Contexto) -> bool:
    if item.remetente.eh_eu or _ultima_mensagem_eh_minha(ctx) or eh_automatico(item):
        return False
    texto = _texto(item)
    return "?" in texto or bool(RE_PEDIDO.search(texto))


# --- sinais -------------------------------------------------------------------------------


def s_vip(item: Item, ctx: Contexto) -> Motivo | None:
    if item.remetente.id in ctx.vips:
        return _m("vip", 30, f"{item.remetente.nome or item.remetente.id} está na sua lista VIP")
    return None


def s_contato_conhecido(item: Item, ctx: Contexto) -> Motivo | None:
    if item.remetente.id in ctx.contatos_conhecidos and item.remetente.id not in ctx.vips:
        return _m("contato_conhecido", 5, "Vocês já conversaram antes")
    return None


def s_automatico(item: Item, ctx: Contexto) -> Motivo | None:
    if eh_automatico(item):
        return _m(
            "automatico", -40, "Parece envio automático (newsletter, notificação ou promoção)"
        )
    return None


def s_formato_conversa(item: Item, ctx: Contexto) -> Motivo | None:
    if item.eh_grupo:
        if item.mencoes_a_mim:
            return _m("mencao_em_grupo", 20, "Você foi mencionado no grupo")
        return _m("grupo", -10, "Mensagem de grupo sem menção a você")
    direta = item.canal == Canal.WHATSAPP or len(item.destinatarios) <= 1
    if direta and item.canal != Canal.AGENDA:
        return _m("conversa_direta", 10, "Conversa direta com você")
    return None


def s_aguardando(item: Item, ctx: Contexto) -> Motivo | None:
    if aguardando_resposta(item, ctx):
        return _m("aguardando_resposta", 15, "Tem pergunta ou pedido esperando sua resposta")
    return None


def s_tempo_sem_resposta(item: Item, ctx: Contexto) -> Motivo | None:
    if not aguardando_resposta(item, ctx):
        return None
    horas = (ctx.agora - item.recebido_em).total_seconds() / 3600
    pontos = min(15, int(horas // 6) * 5)
    if pontos > 0:
        return _m("tempo_sem_resposta", pontos, f"Sem resposta há {int(horas)} h")
    return None


def s_ja_respondido(item: Item, ctx: Contexto) -> Motivo | None:
    if _ultima_mensagem_eh_minha(ctx):
        return _m("ja_respondido", -30, "Sua mensagem é a mais recente da conversa")
    return None


def _por_regex(sinal: str, pontos: int, regex: re.Pattern[str], frase: str):
    def sinal_fn(item: Item, ctx: Contexto) -> Motivo | None:
        if eh_automatico(item):
            return None  # promoção com "só hoje!" não é prazo seu
        achado = regex.search(_texto(item))
        if achado:
            return _m(sinal, pontos, f'{frase} ("{achado.group(0)}")')
        return None

    sinal_fn.__name__ = f"s_{sinal}"
    return sinal_fn


s_urgencia = _por_regex("urgencia", 20, RE_URGENCIA, "Pedido marcado como urgente")
s_prazo = _por_regex("prazo", 20, RE_PRAZO, "Menciona prazo")
s_oportunidade = _por_regex("oportunidade", 15, RE_OPORTUNIDADE, "Envolve oportunidade")
s_financeiro = _por_regex("financeiro", 10, RE_FINANCEIRO, "Assunto financeiro")


def evento_com_remetente(item: Item, ctx: Contexto, janela: timedelta) -> Evento | None:
    for ev in sorted(ctx.eventos, key=lambda e: e.inicio):
        if ctx.agora <= ev.inicio <= ctx.agora + janela and any(
            p.id == item.remetente.id for p in ev.participantes
        ):
            return ev
    return None


def s_evento_proximo(item: Item, ctx: Contexto) -> Motivo | None:
    ev = evento_com_remetente(item, ctx, timedelta(hours=2))
    if ev:
        return _m("evento_proximo", 20, f'Vocês têm "{ev.titulo}" nas próximas 2 h')
    ev = evento_com_remetente(item, ctx, timedelta(hours=24))
    if ev:
        return _m("evento_proximo", 10, f'Vocês têm "{ev.titulo}" nas próximas 24 h')
    return None


def s_antigo(item: Item, ctx: Contexto) -> Motivo | None:
    if ctx.agora - item.recebido_em > timedelta(days=7):
        return _m("antigo", -20, "Mais de 7 dias sem atividade")
    return None


SINAIS: list[Callable[[Item, Contexto], Motivo | None]] = [
    s_vip,
    s_contato_conhecido,
    s_automatico,
    s_formato_conversa,
    s_aguardando,
    s_tempo_sem_resposta,
    s_ja_respondido,
    s_urgencia,
    s_prazo,
    s_oportunidade,
    s_financeiro,
    s_evento_proximo,
    s_antigo,
]
