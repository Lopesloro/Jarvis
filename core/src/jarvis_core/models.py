"""Modelos trocados entre as camadas (espelham contracts/*.schema.json)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Canal(str, Enum):
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    AGENDA = "agenda"


class Faixa(str, Enum):
    AGORA = "agora"
    HOJE = "hoje"
    SEMANA = "semana"
    ARQUIVAR = "arquivar"


class Acao(str, Enum):
    RESPONDER = "responder"
    AGENDAR = "agendar"
    LER = "ler"
    ARQUIVAR = "arquivar"


class Pessoa(BaseModel):
    id: str = Field(description="E-mail, JID do WhatsApp ou id do contato")
    nome: str = ""
    eh_eu: bool = False


class Mensagem(BaseModel):
    """Uma mensagem dentro de uma conversa (usada como contexto)."""

    autor: Pessoa
    texto: str
    enviada_em: datetime


class Item(BaseModel):
    """Unidade que entra na triagem: um e-mail, uma conversa do WhatsApp ou um evento."""

    id: str
    canal: Canal
    conversa_id: str
    remetente: Pessoa
    assunto: str = ""
    texto: str
    recebido_em: datetime
    eh_grupo: bool = False
    mencoes_a_mim: bool = False
    destinatarios: list[Pessoa] = Field(default_factory=list)
    metadados: dict[str, Any] = Field(default_factory=dict)


class Evento(BaseModel):
    id: str
    titulo: str
    inicio: datetime
    fim: datetime
    participantes: list[Pessoa] = Field(default_factory=list)
    local: str = ""


class Motivo(BaseModel):
    sinal: str
    pontos: int
    explicacao: str


class Triagem(BaseModel):
    item_id: str
    nota: int = Field(ge=0, le=100)
    faixa: Faixa
    motivos: list[Motivo]
    acao_sugerida: Acao
    ajuste_llm: int = Field(default=0, ge=-20, le=20)
    motivo_llm: str = ""
    versao_regras: str
