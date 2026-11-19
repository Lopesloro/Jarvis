"""Configuração do Jarvis lida de ~/.jarvis/jarvis.toml (nunca versionada)."""

from __future__ import annotations

import logging
import os
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def home() -> Path:
    base = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis")).expanduser()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base


@dataclass
class Config:
    fuso: str = "America/Sao_Paulo"
    meu_nome_whatsapp: str = ""
    vips: set[str] = field(default_factory=set)
    silencio_inicio: str = "23:00"
    silencio_fim: str = "07:00"
    llm_ligado: bool = True
    llm_url: str = "http://127.0.0.1:11434"
    llm_modelo: str = "qwen2.5:3b"
    llm_tempo_limite_s: float = 20
    wa_data_dir: Path = field(default_factory=lambda: home() / "whatsapp")
    gmail_usuario: str = ""
    gmail_senha_app: str = ""  # senha de app do Google (não é a senha da conta)
    gmail_dias: int = 3
    agenda_ics_urls: list[str] = field(default_factory=list)
    resumo_hora: str = "07:30"
    resumo_falado: bool = True
    voz: str = "Luciana"
    notificar: bool = True
    porta: int = 8765


def carregar(caminho: Path | None = None) -> Config:
    caminho = caminho or home() / "jarvis.toml"
    if not caminho.exists():
        return Config()
    if caminho.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        # O arquivo guarda a senha de app do Gmail: só o dono pode ler.
        logging.getLogger("jarvis.config").warning(
            "%s está legível por outros usuários; corrigindo para 600", caminho
        )
        caminho.chmod(0o600)
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
    g = dados.get("geral", {})
    p = dados.get("prioridade", {})
    llm = dados.get("llm", {})
    wa = dados.get("whatsapp", {})
    gm = dados.get("gmail", {})
    ag = dados.get("agenda", {})
    rs = dados.get("resumo", {})
    api = dados.get("api", {})
    base = Config()
    return Config(
        fuso=g.get("fuso", base.fuso),
        meu_nome_whatsapp=g.get("meu_nome_whatsapp", ""),
        vips=set(p.get("vips", [])),
        silencio_inicio=p.get("silencio_inicio", base.silencio_inicio),
        silencio_fim=p.get("silencio_fim", base.silencio_fim),
        llm_ligado=llm.get("ligado", True),
        llm_url=llm.get("url", base.llm_url),
        llm_modelo=llm.get("modelo", base.llm_modelo),
        llm_tempo_limite_s=float(llm.get("tempo_limite_s", base.llm_tempo_limite_s)),
        wa_data_dir=Path(wa.get("data_dir", str(base.wa_data_dir))).expanduser(),
        gmail_usuario=gm.get("usuario", ""),
        gmail_senha_app=gm.get("senha_app", "").replace(" ", ""),
        gmail_dias=int(gm.get("dias", 3)),
        agenda_ics_urls=list(ag.get("ics_urls", [])),
        resumo_hora=rs.get("hora", base.resumo_hora),
        resumo_falado=rs.get("falado", True),
        voz=rs.get("voz", base.voz),
        notificar=rs.get("notificar", True),
        porta=int(api.get("porta", base.porta)),
    )
