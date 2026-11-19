from jarvis_core.ingest.whatsapp_export import item_da_conversa, parse_export

ANDROID = """15/01/2024 10:29 - As mensagens e as ligações são protegidas com a criptografia de ponta a ponta.
15/01/2024 10:30 - Ana: Oi, tudo bem?
15/01/2024 10:31 - Gabriel: Tudo! E aí?
15/01/2024 10:35 - Ana: Consegue mandar o currículo
atualizado até amanhã?
"""

IPHONE = """‎[15/01/24, 10:30:12] Ana: Oi, tudo bem?
[15/01/24, 22:05:59] Gabriel: Tudo sim
"""


def test_android_ptbr_com_multilinha_e_linha_de_sistema():
    msgs = parse_export(ANDROID, meu_nome="Gabriel")
    assert [m.autor.nome for m in msgs] == ["Ana", "Gabriel", "Ana"]
    assert msgs[1].autor.eh_eu
    assert msgs[2].texto == "Consegue mandar o currículo\natualizado até amanhã?"
    assert msgs[2].enviada_em.hour == 10 and msgs[2].enviada_em.day == 15


def test_iphone_ptbr_com_segundos_ano_curto_e_caractere_invisivel():
    msgs = parse_export(IPHONE, meu_nome="Gabriel")
    assert len(msgs) == 2
    assert msgs[0].enviada_em.year == 2024
    assert msgs[1].enviada_em.hour == 22


def test_item_da_conversa_usa_ultima_recebida():
    item = item_da_conversa("Ana", parse_export(ANDROID, meu_nome="Gabriel"))
    assert item is not None
    assert item.remetente.nome == "Ana"
    assert "currículo" in item.texto
    assert not item.eh_grupo


def test_conversa_so_com_mensagens_minhas_nao_gera_item():
    assert item_da_conversa("x", parse_export("15/01/2024 10:30 - Gabriel: oi", "Gabriel")) is None
