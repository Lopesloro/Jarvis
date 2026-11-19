"""API do Jarvis. Contrato completo em contracts/openapi.yaml."""

from __future__ import annotations

import hmac
import io
import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jarvis_core import __version__
from jarvis_core.config import Config, carregar, home
from jarvis_core.models import Canal, Faixa
from jarvis_core.priority import Contexto
from jarvis_core.store import Store

WEB = Path(__file__).resolve().parents[4] / "web"


class Decisao(BaseModel):
    decisao: Literal["resolver", "adiar", "arquivar"]
    nota_correta: Faixa | None = None  # "isso deveria ser <faixa>": vira rótulo para a F2
    observacao: str | None = None


def _qr_svg(texto: str) -> str:
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


def _ponte(cfg: Config) -> dict:
    d = cfg.wa_data_dir
    saida: dict = {"status": "parada", "qr_svg": None}
    try:
        saida.update(json.loads((d / "status.json").read_text()))
    except (OSError, ValueError):
        pass
    qr = d / "qr.txt"
    if saida.get("status") == "qr" and qr.exists():
        saida["qr_svg"] = _qr_svg(qr.read_text().strip())
    return saida


def create_app(store: Store, token: str, cfg_loader=carregar) -> FastAPI:
    if len(token) < 32:
        raise ValueError("JARVIS_TOKEN precisa ter pelo menos 32 caracteres")

    app = FastAPI(title="Jarvis", version=__version__)

    def autenticar(authorization: str = Header(default="")) -> None:
        esperado = f"Bearer {token}"
        if not hmac.compare_digest(authorization.encode(), esperado.encode()):
            raise HTTPException(status_code=401, detail="token inválido")

    @app.get("/saude")
    def saude() -> dict:
        return {"ok": True, "versao": __version__}

    @app.get("/", include_in_schema=False)
    def interface() -> FileResponse:
        return FileResponse(WEB / "index.html", media_type="text/html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifesto() -> FileResponse:
        return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/icone.svg", include_in_schema=False)
    def icone() -> FileResponse:
        return FileResponse(WEB / "icone.svg", media_type="image/svg+xml")

    @app.get("/v1/agora", dependencies=[Depends(autenticar)])
    def agora() -> list[dict]:
        return store.listar([Faixa.AGORA])

    @app.get("/v1/inbox", dependencies=[Depends(autenticar)])
    def inbox(
        faixa: list[Faixa] | None = Query(default=None),  # noqa: B008 (padrão do FastAPI)
        canal: Literal["gmail", "whatsapp", "agenda"] | None = None,
        limite: int = Query(default=100, ge=1, le=500),
    ) -> list[dict]:
        return store.listar(faixa, canal, limite)

    @app.get("/v1/itens/{item_id}", dependencies=[Depends(autenticar)])
    def item(item_id: str) -> dict:
        dados = store.obter(item_id)
        if dados is None:
            raise HTTPException(status_code=404, detail="item não encontrado")
        return dados

    @app.post("/v1/itens/{item_id}/decisao", dependencies=[Depends(autenticar)])
    def decidir(item_id: str, corpo: Decisao) -> dict:
        nota = corpo.nota_correta.value if corpo.nota_correta else None
        if not store.decidir(item_id, corpo.decisao, nota, corpo.observacao):
            raise HTTPException(status_code=404, detail="item não encontrado")
        return {"ok": True}

    @app.post("/v1/itens/{item_id}/rascunho", dependencies=[Depends(autenticar)])
    def rascunho(item_id: str) -> dict:
        """Gera um rascunho com o modelo local. Nunca envia: só devolve o texto."""
        from jarvis_core.ingest.whatsapp_bridge import historico_da_conversa
        from jarvis_core.llm import Ollama

        it = store.item_modelo(item_id)
        if it is None:
            raise HTTPException(status_code=404, detail="item não encontrado")
        cfg = cfg_loader()
        ctx = Contexto(agora=datetime.now(UTC))
        wa_db = cfg.wa_data_dir / "wa.db"
        if it.canal == Canal.WHATSAPP and wa_db.exists():
            ctx.historico = historico_da_conversa(wa_db, it.conversa_id, 12)
        llm = Ollama(cfg.llm_url, cfg.llm_modelo, max(cfg.llm_tempo_limite_s, 60))
        try:
            texto = llm.rascunho(it, ctx)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"modelo local indisponível: {e}") from e
        store.salvar_rascunho(item_id, texto)
        return {"rascunho": texto}

    @app.get("/v1/agenda", dependencies=[Depends(autenticar)])
    def agenda(dia: date | None = None) -> list[dict]:
        cfg = cfg_loader()
        tz = ZoneInfo(cfg.fuso)
        dia = dia or datetime.now(tz).date()
        inicio = datetime.combine(dia, datetime.min.time(), tzinfo=tz).astimezone(UTC)
        return [
            e.model_dump(mode="json") for e in store.eventos(inicio, inicio + timedelta(days=1))
        ]

    @app.get("/v1/resumo", dependencies=[Depends(autenticar)])
    def resumo() -> dict:
        from jarvis_core.agendador import montar_resumo

        return {"texto": montar_resumo(store, cfg_loader(), datetime.now(UTC))}

    @app.post("/v1/falar", dependencies=[Depends(autenticar)])
    def falar_resumo() -> dict:
        from jarvis_core.agendador import falar, montar_resumo

        cfg = cfg_loader()
        texto = montar_resumo(store, cfg, datetime.now(UTC))
        falar(texto, cfg.voz)
        return {"texto": texto}

    @app.get("/v1/status", dependencies=[Depends(autenticar)])
    def status() -> dict:
        cfg = cfg_loader()
        return {
            "versao": __version__,
            "contagem": store.contagem(),
            "estado": store.estado(),
            "ponte": _ponte(cfg),
            "config": {
                "gmail": bool(cfg.gmail_usuario and cfg.gmail_senha_app),
                "agenda": bool(cfg.agenda_ics_urls),
                "modelo": cfg.llm_modelo,
                "vips": len(cfg.vips),
            },
        }

    return app


def _app_do_ambiente() -> FastAPI:
    token = os.environ.get("JARVIS_TOKEN", "")
    return create_app(Store(home() / "jarvis.db"), token)


def __getattr__(nome: str):  # `uvicorn jarvis_core.api.main:app` cria a app só quando pedida
    if nome == "app":
        return _app_do_ambiente()
    raise AttributeError(nome)
