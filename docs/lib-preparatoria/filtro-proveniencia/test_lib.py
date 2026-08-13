from __future__ import annotations

import pytest
from lib import (
    Condicao,
    FiltroInvalido,
    FiltroProveniencia,
    com_campo,
    para_condicoes,
    parse,
    serialize,
)

# --- parse: caminho feliz -------------------------------------------------


def test_parse_um_campo_estruturado():
    f = parse("confianca:baixa")
    assert f == FiltroProveniencia(confianca="baixa")


def test_parse_varios_campos_e_texto_livre():
    f = parse("confianca:baixa papel:sinal lugar:estimado pantanal")
    assert f.confianca == "baixa"
    assert f.papel == "sinal"
    assert f.lugar == "estimado"
    assert f.busca == ("pantanal",)


def test_parse_origem_preserva_caixa_mas_confianca_normaliza():
    # confianca/papel/lugar são vocabulário fechado (normaliza para minúsculo);
    # origem é texto livre do schema (Evidence.origem), preserva como digitado.
    f = parse("origem:Vizinhanca_Temporal confianca:BAIXA")
    assert f.origem == "Vizinhanca_Temporal"
    assert f.confianca == "baixa"


def test_parse_texto_livre_com_aspas_multi_palavra():
    f = parse('"praia grande" confianca:alta')
    assert f.busca == ("praia grande",)
    assert f.confianca == "alta"


def test_parse_string_vazia_devolve_filtro_vazio():
    f = parse("")
    assert f.vazio()


def test_parse_so_espacos_devolve_filtro_vazio():
    assert parse("   ").vazio()


# --- parse: erro reportado, nunca engolido --------------------------------


def test_parse_campo_desconhecido_levanta_erro_com_o_token():
    with pytest.raises(FiltroInvalido, match="campo desconhecido"):
        parse("cor:vermelho")


def test_parse_valor_fora_do_vocabulario_levanta_erro():
    with pytest.raises(FiltroInvalido, match="confianca"):
        parse("confianca:altissima")


def test_parse_papel_invalido_levanta_erro():
    with pytest.raises(FiltroInvalido):
        parse("papel:usuario")


def test_parse_lugar_invalido_levanta_erro():
    with pytest.raises(FiltroInvalido):
        parse("lugar:desconhecido")


def test_parse_campo_repetido_levanta_erro():
    with pytest.raises(FiltroInvalido, match="repetido"):
        parse("confianca:baixa confianca:alta")


def test_parse_valor_vazio_levanta_erro():
    with pytest.raises(FiltroInvalido):
        parse("confianca:")


def test_parse_aspas_nao_fechadas_levanta_erro():
    with pytest.raises(FiltroInvalido, match="sintaxe"):
        parse('origem:"vizinhanca')


# --- serialize + round-trip simétrico -------------------------------------


def test_serialize_filtro_vazio_e_string_vazia():
    assert serialize(FiltroProveniencia()) == ""


def test_serialize_ordem_fixa_independente_da_ordem_de_construcao():
    a = FiltroProveniencia(confianca="baixa", papel="sinal")
    b = replace_via_com_campo_ordem_inversa()
    assert serialize(a) == serialize(b)


def replace_via_com_campo_ordem_inversa() -> FiltroProveniencia:
    f = FiltroProveniencia()
    f = com_campo(f, "papel", "sinal")
    f = com_campo(f, "confianca", "baixa")
    return f


@pytest.mark.parametrize(
    "texto",
    [
        "confianca:baixa",
        "papel:sinal",
        "lugar:estimado",
        "confianca:baixa papel:sinal lugar:estimado",
        "origem:vizinhanca_temporal",
        "pantanal",
        '"praia grande"',
        "confianca:media pantanal",
    ],
)
def test_round_trip_parse_serialize_parse_e_estavel(texto):
    f1 = parse(texto)
    serializado = serialize(f1)
    f2 = parse(serializado)
    assert f1 == f2
    # aplicar serialize de novo no resultado reparseado é idempotente —
    # é o que torna o link salvo estável para sempre, não só na primeira volta.
    assert serialize(f2) == serializado


def test_round_trip_preserva_texto_livre_multi_palavra():
    original = FiltroProveniencia(busca=("praia grande", "sul"))
    de_volta = parse(serialize(original))
    assert de_volta.busca == ("praia grande", "sul")


# --- com_campo: caminho da UI estruturada escreve no mesmo objeto --------


def test_com_campo_escreve_e_le_do_mesmo_objeto():
    f = FiltroProveniencia()
    f2 = com_campo(f, "confianca", "alta")
    assert f.confianca is None  # imutável — não masca o original
    assert f2.confianca == "alta"


def test_com_campo_remove_com_valor_none():
    f = FiltroProveniencia(confianca="alta")
    assert com_campo(f, "confianca", None).confianca is None


def test_com_campo_valida_o_vocabulario_tambem():
    with pytest.raises(FiltroInvalido):
        com_campo(FiltroProveniencia(), "confianca", "ultra")


def test_com_campo_campo_desconhecido_levanta_erro():
    with pytest.raises(FiltroInvalido):
        com_campo(FiltroProveniencia(), "cor", "vermelho")


# --- para_condicoes: composição em N predicados, sempre AND --------------


def test_para_condicoes_filtro_vazio_nao_gera_predicado():
    assert para_condicoes(FiltroProveniencia()) == ()


def test_para_condicoes_confianca_mira_evidence():
    (c,) = para_condicoes(FiltroProveniencia(confianca="baixa"))
    assert c == Condicao("evidence", "nivel", "=", "baixa")


def test_para_condicoes_papel_mira_media_files():
    (c,) = para_condicoes(FiltroProveniencia(papel="sinal"))
    assert c == Condicao("media_files", "papel", "=", "sinal")


def test_para_condicoes_lugar_estimado_vs_medido_sao_colunas_diferentes():
    estimado = para_condicoes(FiltroProveniencia(lugar="estimado"))[0]
    medido = para_condicoes(FiltroProveniencia(lugar="medido"))[0]
    assert estimado.campo == "gps_lat_estimado"
    assert medido.campo == "gps_lat"


def test_para_condicoes_compoe_multiplos_campos_em_and_implicito():
    filtro = FiltroProveniencia(confianca="baixa", papel="sinal", lugar="estimado")
    condicoes = para_condicoes(filtro)
    assert len(condicoes) == 3
    tabelas = {c.tabela for c in condicoes}
    assert tabelas == {"evidence", "media_files"}


# --- caso de uso do prompt de origem, ponta a ponta -----------------------


def test_caso_de_uso_heranca_confianca_baixa_sem_camera():
    # "as 4.944 fotos cujo lugar veio de herança (D-025) com confiança
    # baixa" -- sem_camera é predicado de repositories/media.py já existente
    # (LACUNAS["sem_camera"]), fora do escopo de evidence deste item; aqui
    # provamos que o vocabulário novo compõe com texto livre remanescente.
    texto = "confianca:baixa origem:vizinhanca_temporal lugar:estimado"
    f = parse(texto)
    assert serialize(f) == texto
    condicoes = para_condicoes(f)
    assert len(condicoes) == 3
