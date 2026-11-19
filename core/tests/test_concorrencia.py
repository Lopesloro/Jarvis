"""Regressão do IndexError visto em produção no /v1/resumo (19/11/2026).

A API roda rotas síncronas em várias threads com a mesma conexão SQLite. Sem trava, uma
consulta lê o cursor da outra.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from conftest import item_wa

from jarvis_core.priority import Contexto, triar
from jarvis_core.store import Store


def test_leituras_e_escritas_simultaneas_nao_embaralham_o_cursor(tmp_path):
    store = Store(tmp_path / "j.db")
    agora = datetime.now(UTC)

    def escrever(i: int) -> None:
        it = item_wa(str(i), agora=agora)
        store.salvar(it, triar(it, Contexto(agora=agora)))
        store.set_estado(f"k{i}", {"i": i})

    def ler(_: int) -> None:
        assert isinstance(store.contagem(), dict)
        store.listar()
        store.estado()

    with ThreadPoolExecutor(max_workers=16) as pool:
        for f in [pool.submit(escrever if i % 2 else ler, i) for i in range(400)]:
            f.result()  # propaga qualquer exceção das threads

    assert sum(store.contagem().values()) == 200
    store.fechar()
