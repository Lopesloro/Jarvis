from datetime import UTC, datetime, timedelta

import pytest

from jarvis_core.models import Acao, Canal, Evento, Faixa, Item, Mensagem, Pessoa
from jarvis_core.priority import Contexto, triar

AGORA = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)
EU = Pessoa(id="5519999990000@s.whatsapp.net", nome="Gabriel", eh_eu=True)
RECRUTADORA = Pessoa(id="5511988887777@s.whatsapp.net", nome="Ana (RH)")


def item(texto: str, **kw) -> Item:
    base = {
        "id": "x1",
        "canal": Canal.WHATSAPP,
        "conversa_id": "c1",
        "remetente": RECRUTADORA,
        "texto": texto,
        "recebido_em": AGORA - timedelta(minutes=10),
    }
    base.update(kw)
    return Item(**base)


def sinais(t) -> set[str]:
    return {m.sinal for m in t.motivos}


def test_entrevista_com_prazo_vai_para_agora():
    t = triar(
        item("Oi Gabriel! Pode confirmar sua disponibilidade pra entrevista até hoje 18h?"),
        Contexto(agora=AGORA),
    )
    assert t.faixa == Faixa.AGORA
    assert {"oportunidade", "prazo", "aguardando_resposta", "conversa_direta"} <= sinais(t)
    assert t.acao_sugerida == Acao.AGENDAR  # pede horário e não há evento marcado


def test_newsletter_vai_para_arquivar_mesmo_com_palavra_de_prazo():
    t = triar(
        item(
            "Só hoje! 50% de desconto, vence amanhã",
            canal=Canal.GMAIL,
            remetente=Pessoa(id="no-reply@loja.com.br", nome="Loja"),
            metadados={"list_unsubscribe": True},
        ),
        Contexto(agora=AGORA),
    )
    assert t.faixa == Faixa.ARQUIVAR
    assert "prazo" not in sinais(t)
    assert t.acao_sugerida == Acao.ARQUIVAR


def test_grupo_sem_mencao_cai_e_com_mencao_sobe():
    sem = triar(item("bom dia pessoal", eh_grupo=True), Contexto(agora=AGORA))
    com = triar(item("@Gabriel bom dia", eh_grupo=True, mencoes_a_mim=True), Contexto(agora=AGORA))
    assert "grupo" in sinais(sem)
    assert "mencao_em_grupo" in sinais(com)
    assert com.nota > sem.nota


def test_ja_respondido_derruba_a_nota():
    hist = [
        Mensagem(autor=RECRUTADORA, texto="Pode amanhã?", enviada_em=AGORA - timedelta(hours=2)),
        Mensagem(autor=EU, texto="Posso sim", enviada_em=AGORA - timedelta(hours=1)),
    ]
    t = triar(item("Pode amanhã?"), Contexto(agora=AGORA, historico=hist))
    assert "ja_respondido" in sinais(t)
    assert "aguardando_resposta" not in sinais(t)


def test_tempo_sem_resposta_tem_teto():
    t = triar(
        item("Consegue me mandar o relatório?", recebido_em=AGORA - timedelta(hours=40)),
        Contexto(agora=AGORA),
    )
    motivo = next(m for m in t.motivos if m.sinal == "tempo_sem_resposta")
    assert motivo.pontos == 15


def test_vip_e_evento_proximo():
    ev = Evento(
        id="e1",
        titulo="Reunião PI VI",
        inicio=AGORA + timedelta(hours=1),
        fim=AGORA + timedelta(hours=2),
        participantes=[RECRUTADORA],
    )
    t = triar(
        item("Tudo certo?"),
        Contexto(agora=AGORA, vips={RECRUTADORA.id}, eventos=[ev]),
    )
    assert {"vip", "evento_proximo"} <= sinais(t)
    assert next(m for m in t.motivos if m.sinal == "evento_proximo").pontos == 20
    assert t.faixa == Faixa.AGORA


def test_acento_e_maiuscula_nao_atrapalham():
    t = triar(item("URGÊNCIA: preciso do boleto"), Contexto(agora=AGORA))
    assert {"urgencia", "financeiro"} <= sinais(t)


def test_palavra_dentro_de_outra_nao_dispara():
    t = triar(item("vagamente lembro disso"), Contexto(agora=AGORA))
    assert "oportunidade" not in sinais(t)


def test_todo_motivo_tem_explicacao_e_nota_fica_no_intervalo():
    t = triar(item("URGENTE hoje entrevista boleto?"), Contexto(agora=AGORA, vips={RECRUTADORA.id}))
    assert 0 <= t.nota <= 100
    assert all(m.explicacao for m in t.motivos)


class _LLM:
    def __init__(self, ajuste, erro=False):
        self.ajuste, self.erro = ajuste, erro

    def refinar(self, item, ctx, base):
        if self.erro:
            raise TimeoutError
        return self.ajuste, "contexto da conversa"


@pytest.mark.parametrize("ajuste,esperado", [(50, 20), (-99, -20), (7, 7)])
def test_ajuste_do_llm_e_limitado(ajuste, esperado):
    base = triar(item("oi"), Contexto(agora=AGORA))
    t = triar(item("oi"), Contexto(agora=AGORA), refinador=_LLM(ajuste))
    assert t.ajuste_llm == esperado
    assert t.nota == max(0, min(100, base.nota + esperado))


def test_falha_do_llm_mantem_nota_das_regras():
    base = triar(item("oi"), Contexto(agora=AGORA))
    t = triar(item("oi"), Contexto(agora=AGORA), refinador=_LLM(0, erro=True))
    assert t == base
