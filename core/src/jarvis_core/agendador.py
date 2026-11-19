"""Agendador do Jarvis: coleta, triagem, aviso no Mac e resumo da manhã.

Roda sob launchd (`python -m jarvis_core.agendador`). Cada fonte é opcional: o que não
estiver configurado fica parado, e uma fonte com erro não derruba as outras.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
import time
from datetime import UTC, datetime, timedelta
from datetime import time as hora
from zoneinfo import ZoneInfo

from jarvis_core.config import Config, carregar, home
from jarvis_core.llm import Ollama
from jarvis_core.models import Faixa, Item, Triagem
from jarvis_core.pipeline import processar, processar_whatsapp
from jarvis_core.priority import Contexto
from jarvis_core.store import Store

log = logging.getLogger("jarvis.agendador")

INTERVALO_WHATSAPP_S = 20
INTERVALO_GMAIL_S = 120
INTERVALO_AGENDA_S = 600
JANELA_COLETA = timedelta(days=3)
AVISO_SO_SE_MAIS_NOVO_QUE = timedelta(minutes=30)
INTERVALO_CHECAR_LLM_S = 60


def _hhmm(valor: str) -> hora:
    h, m = valor.split(":")
    return hora(int(h), int(m))


def em_silencio(cfg: Config, agora_local: datetime) -> bool:
    ini, fim, t = _hhmm(cfg.silencio_inicio), _hhmm(cfg.silencio_fim), agora_local.time()
    return (t >= ini or t < fim) if ini > fim else (ini <= t < fim)


def notificar_mac(titulo: str, texto: str) -> None:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')[:220]

    script = f'display notification "{esc(texto)}" with title "{esc(titulo)}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False, timeout=10)


def falar(texto: str, voz: str) -> None:
    subprocess.Popen(["say", "-v", voz, texto])


def montar_resumo(store: Store, cfg: Config, agora: datetime) -> str:
    tz = ZoneInfo(cfg.fuso)
    local = agora.astimezone(tz)
    saud = "Bom dia" if local.hour < 12 else ("Boa tarde" if local.hour < 18 else "Boa noite")
    cont = store.contagem()
    partes = [f"{saud}, Gabriel."]
    n_agora, n_hoje = cont.get("agora", 0), cont.get("hoje", 0)
    if n_agora or n_hoje:
        partes.append(f"Você tem {n_agora} itens urgentes e {n_hoje} para hoje.")
    else:
        partes.append("Nada urgente na caixa.")
    for linha in store.listar([Faixa.AGORA], limite=3):
        it, tr = linha["item"], linha["triagem"]
        quem = it["remetente"].get("nome") or it["remetente"]["id"].split("@")[0]
        canal = {"gmail": "e-mail", "whatsapp": "WhatsApp"}.get(it["canal"], it["canal"])
        motivo = tr["motivos"][0]["explicacao"] if tr["motivos"] else ""
        partes.append(f"{quem}, no {canal}: {motivo}.")
    inicio_dia = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    eventos = store.eventos(max(agora, inicio_dia), inicio_dia + timedelta(days=1))
    if eventos:
        partes.append(f"Na agenda de hoje, {len(eventos)} compromissos.")
        for ev in eventos[:3]:
            partes.append(f"Às {ev.inicio.astimezone(tz):%H:%M}, {ev.titulo}.")
    return " ".join(partes)


class Agendador:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.ultimo: dict[str, float] = {}
        self.cfg = carregar()
        self._llm_cache: Ollama | None = None

    def _vencido(self, chave: str, intervalo: float) -> bool:
        agora = time.monotonic()
        if agora - self.ultimo.get(chave, -1e9) >= intervalo:
            self.ultimo[chave] = agora
            return True
        return False

    def _llm(self) -> Ollama | None:
        if not self.cfg.llm_ligado:
            self.store.set_estado("llm", {"ok": False, "modelo": "desligado"})
            return None
        # Perguntar ao Ollama a cada ciclo de 5 s enchia o log (17 mil linhas por dia).
        if not self._vencido("llm", INTERVALO_CHECAR_LLM_S):
            return self._llm_cache
        o = Ollama(self.cfg.llm_url, self.cfg.llm_modelo, self.cfg.llm_tempo_limite_s)
        disponivel = o.disponivel()
        self.store.set_estado("llm", {"ok": disponivel, "modelo": self.cfg.llm_modelo})
        self._llm_cache = o if disponivel else None
        return self._llm_cache

    def _contexto(self, agora: datetime) -> Contexto:
        minhas = {self.cfg.gmail_usuario.lower()} if self.cfg.gmail_usuario else set()
        meu_jid = self.store.get_estado("meu_jid")
        if meu_jid:
            minhas.add(str(meu_jid))
        eventos = self.store.eventos(agora - timedelta(hours=1), agora + timedelta(days=14))
        return Contexto(agora=agora, minhas_ids=minhas, vips=self.cfg.vips, eventos=eventos)

    def _ao_salvar(self, item: Item, triagem: Triagem) -> None:
        agora = datetime.now(UTC)
        if (
            not self.cfg.notificar
            or triagem.faixa != Faixa.AGORA
            or agora - item.recebido_em > AVISO_SO_SE_MAIS_NOVO_QUE
            or em_silencio(self.cfg, agora.astimezone(ZoneInfo(self.cfg.fuso)))
        ):
            return
        quem = item.remetente.nome or item.remetente.id.split("@")[0]
        motivo = triagem.motivo_llm or (triagem.motivos[0].explicacao if triagem.motivos else "")
        notificar_mac(f"Jarvis · {quem}", f"{motivo} — {item.texto[:120]}")

    def _registrar(self, fonte: str, ok: bool, detalhe: str = "", n: int = 0) -> None:
        self.store.set_estado(f"fonte:{fonte}", {"ok": ok, "detalhe": detalhe[:300], "novos": n})

    # --- fontes ---------------------------------------------------------------------------

    def agenda(self) -> None:
        if not self.cfg.agenda_ics_urls:
            return self._registrar("agenda", False, "não configurada")
        from jarvis_core.ingest.agenda_ics import ler_agendas

        eventos = ler_agendas(self.cfg.agenda_ics_urls, self.cfg.fuso)
        self.store.substituir_eventos(eventos)
        self._registrar("agenda", True, f"{len(eventos)} eventos nos próximos 14 dias")

    def whatsapp(self, agora: datetime, llm: Ollama | None) -> None:
        wa_db = self.cfg.wa_data_dir / "wa.db"
        if not wa_db.exists():
            return self._registrar("whatsapp", False, "ponte ainda não pareada")
        con = sqlite3.connect(f"file:{wa_db}?mode=ro", uri=True)
        try:
            meu = con.execute("SELECT valor FROM meta WHERE chave = 'meu_jid'").fetchone()
        finally:
            con.close()
        if not meu:
            return self._registrar("whatsapp", False, "esperando o pareamento por QR")
        self.store.set_estado("meu_jid", meu[0])
        n = processar_whatsapp(
            wa_db,
            self.store,
            self._contexto(agora),
            agora - JANELA_COLETA,
            refinador=llm,
            pular_existentes=True,
            ao_salvar=self._ao_salvar,
        )
        self._registrar("whatsapp", True, "conectado e lendo as conversas", n)

    def gmail(self, agora: datetime, llm: Ollama | None) -> None:
        if not (self.cfg.gmail_usuario and self.cfg.gmail_senha_app):
            return self._registrar("gmail", False, "não configurado")
        from jarvis_core.ingest.gmail_imap import ler_gmail

        itens = ler_gmail(self.cfg.gmail_usuario, self.cfg.gmail_senha_app, self.cfg.gmail_dias)
        n = processar(
            ((i, []) for i in itens),
            self.store,
            self._contexto(agora),
            refinador=llm,
            pular_existentes=True,
            ao_salvar=self._ao_salvar,
        )
        self._registrar("gmail", True, f"{len(itens)} e-mails nos últimos dias", n)

    def resumo(self, agora: datetime) -> None:
        tz = ZoneInfo(self.cfg.fuso)
        local = agora.astimezone(tz)
        hoje = local.date().isoformat()
        if (
            local.time() < _hhmm(self.cfg.resumo_hora)
            or self.store.get_estado("resumo_dia") == hoje
        ):
            return
        texto = montar_resumo(self.store, self.cfg, agora)
        self.store.set_estado("resumo", texto)
        self.store.set_estado("resumo_dia", hoje)
        if local.hour >= 12:  # ligou o Mac à tarde: guarda o resumo sem falar
            return
        notificar_mac("Jarvis · resumo da manhã", texto)
        if self.cfg.resumo_falado:
            falar(texto, self.cfg.voz)

    # --- laço -----------------------------------------------------------------------------

    def ciclo(self) -> None:
        self.cfg = carregar()  # editar o jarvis.toml vale sem reiniciar
        agora = datetime.now(UTC)
        llm = self._llm()
        tarefas = [
            ("agenda", INTERVALO_AGENDA_S, self.agenda),
            ("whatsapp", INTERVALO_WHATSAPP_S, lambda: self.whatsapp(agora, llm)),
            ("gmail", INTERVALO_GMAIL_S, lambda: self.gmail(agora, llm)),
        ]
        for nome, intervalo, fn in tarefas:
            if self._vencido(nome, intervalo):
                try:
                    fn()
                except Exception as e:
                    log.exception("falha na fonte %s", nome)
                    self._registrar(nome, False, f"erro: {e}")
        try:
            self.resumo(agora)
        except Exception:
            log.exception("falha no resumo")
        self.store.set_estado("agendador", {"ok": True})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # uma linha por requisição é ruído
    store = Store(home() / "jarvis.db")
    ag = Agendador(store)
    log.info("agendador iniciado")
    while True:
        ag.ciclo()
        time.sleep(5)


if __name__ == "__main__":
    main()
