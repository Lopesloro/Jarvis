"""Armazenamento local dos itens triados e das suas decisões (SQLite)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from jarvis_core.models import Faixa, Item, Triagem

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
"""


class Store:
    def __init__(self, caminho: Path | str) -> None:
        self.con = sqlite3.connect(str(caminho), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(_ESQUEMA)

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
