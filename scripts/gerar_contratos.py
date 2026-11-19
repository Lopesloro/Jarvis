"""Regera contracts/ a partir do código. Rode depois de mudar models.py ou a API.

    cd core && uv run --with pyyaml python ../scripts/gerar_contratos.py

O CI falha se contracts/ estiver diferente do que este script gera.
"""

import json
from pathlib import Path

import yaml

from jarvis_core.api.main import create_app
from jarvis_core.models import Evento, Item, Triagem
from jarvis_core.store import Store

SAIDA = Path(__file__).resolve().parents[1] / "contracts"

for nome, modelo in [("item", Item), ("evento", Evento), ("triagem", Triagem)]:
    esquema = modelo.model_json_schema()
    esquema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    esquema["$id"] = f"jarvis/{nome}.schema.json"
    (SAIDA / f"{nome}.schema.json").write_text(
        json.dumps(esquema, ensure_ascii=False, indent=2) + "\n"
    )

app = create_app(Store(":memory:"), "x" * 40)
(SAIDA / "openapi.yaml").write_text(
    "# Gerado de core/jarvis_core/api/main.py: rode scripts/gerar_contratos.py\n"
    + yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False)
)
