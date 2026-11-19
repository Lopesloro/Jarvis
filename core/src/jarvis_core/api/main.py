"""API do Jarvis. Contrato completo em contracts/openapi.yaml."""

from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from jarvis_core import __version__
from jarvis_core.models import Faixa
from jarvis_core.store import Store


class Decisao(BaseModel):
    decisao: Literal["resolver", "adiar", "arquivar"]
    nota_correta: Faixa | None = None  # "isso deveria ser <faixa>": vira rótulo para a F2
    observacao: str | None = None


def create_app(store: Store, token: str) -> FastAPI:
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

    @app.post("/v1/itens/{item_id}/decisao", dependencies=[Depends(autenticar)])
    def decidir(item_id: str, corpo: Decisao) -> dict:
        nota = corpo.nota_correta.value if corpo.nota_correta else None
        if not store.decidir(item_id, corpo.decisao, nota, corpo.observacao):
            raise HTTPException(status_code=404, detail="item não encontrado")
        return {"ok": True}

    return app


def _app_do_ambiente() -> FastAPI:
    base = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = os.environ.get("JARVIS_TOKEN", "")
    return create_app(Store(base / "jarvis.db"), token)


def __getattr__(nome: str):  # `uvicorn jarvis_core.api.main:app` cria a app só quando pedida
    if nome == "app":
        return _app_do_ambiente()
    raise AttributeError(nome)
