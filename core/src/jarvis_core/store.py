"""Armazenamento local dos itens triados e das suas decisões (SQLite)."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

from jarvis_core.models import Evento, Faixa, Item, Triagem

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS itens (
  id TEXT PRIMARY KEY,
  canal TEXT NOT NULL,
  conversa_id TEXT NOT NULL,
  item_json TEXT NOT NULL,
  triagem_json TEXT NOT NULL,
  nota INTEGER NOT NULL,
  faixa TEXT NOT NULL,
  recebido_em TEXT NOT NULL,
  resolvido INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS itens_faixa ON itens (resolvido, nota DESC);
CREATE TABLE IF NOT EXISTS decisoes (
  item_id TEXT NOT NULL REFERENCES itens(id),
  decisao TEXT NOT NULL,
  nota_correta TEXT,
  observacao TEXT,
  em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eventos (
  id TEXT PRIMARY KEY,
  titulo TEXT NOT NULL,
  inicio TEXT NOT NULL,
  fim TEXT NOT NULL,
  evento_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS eventos_inicio ON eventos (inicio);
CREATE TABLE IF NOT EXISTS rascunhos (
  item_id TEXT PRIMARY KEY,
  texto TEXT NOT NULL,
  em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS estado (
  chave TEXT PRIMARY KEY,
  valor TEXT NOT NULL,
  em TEXT NOT NULL
);
"""


P = ParamSpec("P")
R = TypeVar("R")


def _travado(metodo: Callable[P, R]) -> Callable[P, R]:
    """Serializa o acesso à conexão.

    A API roda as rotas síncronas num pool de threads e todas usam a mesma conexão. Sem a
    trava, duas consultas simultâneas embaralham o cursor (IndexError visto em produção no
    /v1/resumo, 19/11/2026).
    """

    @wraps(metodo)
    def envolvido(*args: P.args, **kwargs: P.kwargs) -> R:
        with args[0]._trava:  # type: ignore[attr-defined]
            return metodo(*args, **kwargs)

    return envolvido


class Store:
    def __init__(self, caminho: Path | str) -> None:
        self._trava = threading.RLock()
        self.con = sqlite3.connect(str(caminho), check_same_thread=False, timeout=15)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode = WAL")  # API e agendador abrem o mesmo banco
        self.con.executescript(_ESQUEMA)

    @_travado
    def fechar(self) -> None:
        self.con.close()

    # --- itens ----------------------------------------------------------------------------

    @_travado
    def existe(self, item_id: str) -> bool:
        return (
            self.con.execute("SELECT 1 FROM itens WHERE id = ?", (item_id,)).fetchone() is not None
        )

    @_travado
    def obter(self, item_id: str) -> dict | None:
        r = self.con.execute(
            "SELECT item_json, triagem_json, resolvido FROM itens WHERE id = ?", (item_id,)
        ).fetchone()
        if r is None:
            return None
        rasc = self.con.execute(
            "SELECT texto FROM rascunhos WHERE item_id = ?", (item_id,)
        ).fetchone()
        return {
            "item": json.loads(r["item_json"]),
            "triagem": json.loads(r["triagem_json"]),
            "resolvido": bool(r["resolvido"]),
            "rascunho": rasc["texto"] if rasc else None,
        }

    @_travado
    def item_modelo(self, item_id: str) -> Item | None:
        r = self.con.execute("SELECT item_json FROM itens WHERE id = ?", (item_id,)).fetchone()
        return Item.model_validate_json(r["item_json"]) if r else None

    @_travado
    def contagem(self) -> dict[str, int]:
        linhas = self.con.execute(
            "SELECT faixa, COUNT(*) AS n FROM itens WHERE resolvido = 0 GROUP BY faixa"
        ).fetchall()
        return {r["faixa"]: r["n"] for r in linhas}

    # --- rascunhos ------------------------------------------------------------------------

    @_travado
    def salvar_rascunho(self, item_id: str, texto: str) -> None:
        with self.con:
            self.con.execute(
                "INSERT OR REPLACE INTO rascunhos VALUES (?, ?, ?)",
                (item_id, texto, datetime.now(UTC).isoformat()),
            )

    # --- agenda ---------------------------------------------------------------------------

    @_travado
    def substituir_eventos(self, eventos: list[Evento]) -> None:
        with self.con:
            self.con.execute("DELETE FROM eventos")
            self.con.executemany(
                "INSERT OR REPLACE INTO eventos VALUES (?, ?, ?, ?, ?)",
                [
                    (e.id, e.titulo, e.inicio.isoformat(), e.fim.isoformat(), e.model_dump_json())
                    for e in eventos
                ],
            )

    @_travado
    def eventos(self, inicio: datetime, fim: datetime) -> list[Evento]:
        linhas = self.con.execute(
            "SELECT evento_json FROM eventos WHERE inicio < ? AND fim > ? ORDER BY inicio",
            (fim.isoformat(), inicio.isoformat()),
        ).fetchall()
        return [Evento.model_validate_json(r["evento_json"]) for r in linhas]

    # --- estado dos coletores -------------------------------------------------------------

    @_travado
    def set_estado(self, chave: str, valor: object) -> None:
        with self.con:
            self.con.execute(
                "INSERT OR REPLACE INTO estado VALUES (?, ?, ?)",
                (chave, json.dumps(valor, ensure_ascii=False), datetime.now(UTC).isoformat()),
            )

    @_travado
    def estado(self) -> dict[str, dict]:
        return {
            r["chave"]: {"valor": json.loads(r["valor"]), "em": r["em"]}
            for r in self.con.execute("SELECT chave, valor, em FROM estado")
        }

    @_travado
    def get_estado(self, chave: str, padrao: object = None) -> object:
        r = self.con.execute("SELECT valor FROM estado WHERE chave = ?", (chave,)).fetchone()
        return json.loads(r["valor"]) if r else padrao

    @_travado
    def salvar(self, item: Item, triagem: Triagem) -> None:
        # Mensagem nova na mesma conversa substitui o item anterior dela.
        with self.con:
            self.con.execute(
                "DELETE FROM itens WHERE conversa_id = ? AND id <> ? AND resolvido = 0",
                (item.conversa_id, item.id),
            )
            self.con.execute(
                """INSERT INTO itens (id, canal, conversa_id, item_json, triagem_json, nota,
                                      faixa, recebido_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET triagem_json = excluded.triagem_json,
                       nota = excluded.nota, faixa = excluded.faixa""",
                (
                    item.id,
                    item.canal.value,
                    item.conversa_id,
                    item.model_dump_json(),
                    triagem.model_dump_json(),
                    triagem.nota,
                    triagem.faixa.value,
                    item.recebido_em.isoformat(),
                ),
            )

    @_travado
    def listar(
        self, faixas: list[Faixa] | None = None, canal: str | None = None, limite: int = 100
    ) -> list[dict]:
        sql = "SELECT item_json, triagem_json FROM itens WHERE resolvido = 0"
        args: list = []
        if faixas:
            sql += f" AND faixa IN ({','.join('?' * len(faixas))})"
            args += [f.value for f in faixas]
        if canal:
            sql += " AND canal = ?"
            args.append(canal)
        sql += " ORDER BY nota DESC, recebido_em DESC LIMIT ?"
        args.append(limite)
        return [
            {"item": json.loads(r["item_json"]), "triagem": json.loads(r["triagem_json"])}
            for r in self.con.execute(sql, args)
        ]

    @_travado
    def decidir(
        self, item_id: str, decisao: str, nota_correta: str | None, observacao: str | None
    ) -> bool:
        with self.con:
            cur = self.con.execute(
                "UPDATE itens SET resolvido = ? WHERE id = ?",
                (0 if decisao == "adiar" else 1, item_id),
            )
            if cur.rowcount == 0:
                return False
            self.con.execute(
                "INSERT INTO decisoes VALUES (?, ?, ?, ?, ?)",
                (item_id, decisao, nota_correta, observacao, datetime.now(UTC).isoformat()),
            )
        return True
