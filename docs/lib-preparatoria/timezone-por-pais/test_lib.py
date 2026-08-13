from __future__ import annotations

import zoneinfo

from lib import TZ_POR_PAIS, ResultadoTzEstimado, calcular_tz_estimado, tz_estimado_para_pais

# --- aceite explícito da fase-11: toda a tabela é IANA válida ---------------


def test_todo_valor_da_tabela_e_um_identificador_iana_valido():
    disponiveis = zoneinfo.available_timezones()
    invalidos = {pais: tz for pais, tz in TZ_POR_PAIS.items() if tz not in disponiveis}
    assert invalidos == {}, f"identificadores IANA inválidos: {invalidos}"


def test_zoneinfo_consegue_instanciar_cada_valor():
    # available_timezones() pode listar algo que ZoneInfo() ainda rejeita
    # em runtimes exóticos (ex.: sem tzdata do sistema) — instanciar de
    # verdade é a prova mais forte que zoneinfo aceita o identificador.
    for tz in TZ_POR_PAIS.values():
        zoneinfo.ZoneInfo(tz)  # levanta se inválido


def test_tabela_nao_esta_vazia():
    assert len(TZ_POR_PAIS) > 0


def test_tabela_nao_tem_chave_vazia_nem_valor_vazio():
    assert all(pais and tz for pais, tz in TZ_POR_PAIS.items())


def test_tabela_cobre_o_vocabulario_real_de_paises_pt():
    # Import direto do módulo real (só leitura, dentro da fronteira
    # permitida) — a tabela deste item tem que cobrir CADA nome que
    # PAISES_PT pode produzir, não uma amostra.
    import sys
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    from fotoorganizer.geolocation.paises import PAISES_PT

    faltando = set(PAISES_PT.values()) - set(TZ_POR_PAIS)
    assert faltando == set(), f"países sem fuso na tabela: {sorted(faltando)}"


# --- tz_estimado_para_pais: caminho feliz e bordas --------------------------


def test_pais_conhecido_devolve_fuso():
    assert tz_estimado_para_pais("Brasil") == "America/Sao_Paulo"


def test_pais_none_devolve_none():
    assert tz_estimado_para_pais(None) is None


def test_pais_string_vazia_devolve_none():
    assert tz_estimado_para_pais("") is None


def test_pais_desconhecido_devolve_none_nunca_inventa():
    assert tz_estimado_para_pais("Atlântida") is None


def test_pais_e_case_sensitive_por_design():
    # o valor de Evidence.valor já chega no vocabulário canônico de
    # PAISES_PT (nomes com a caixa exata); não é responsabilidade deste
    # módulo normalizar entrada fora desse contrato.
    assert tz_estimado_para_pais("brasil") is None
    assert tz_estimado_para_pais("Brasil") == "America/Sao_Paulo"


# --- caso do prompt de origem: país com mais de um fuso ---------------------


def test_paises_multi_fuso_usam_a_regra_documentada_capital_ou_maior_populacao():
    # Brasil: maior população (São Paulo), não a capital (Brasília) —
    # mesmo fuso na prática (America/Sao_Paulo cobre a hora oficial do
    # Brasil inteiro para fins deste app), documentado no comentário da
    # tabela.
    assert tz_estimado_para_pais("Brasil") == "America/Sao_Paulo"
    assert tz_estimado_para_pais("Estados Unidos") == "America/New_York"
    assert tz_estimado_para_pais("Rússia") == "Europe/Moscow"
    assert tz_estimado_para_pais("Canadá") == "America/Toronto"
    assert tz_estimado_para_pais("Austrália") == "Australia/Sydney"


# --- calcular_tz_estimado: junta resolução + proveniência -------------------


def test_calcular_com_pais_de_gps_proprio_nao_e_heranca():
    r = calcular_tz_estimado("Portugal", origem_pais="geocoding_offline")
    assert r == ResultadoTzEstimado(tz_estimado="Europe/Lisbon", veio_de_heranca=False)


def test_calcular_com_pais_so_herdado_marca_heranca():
    r = calcular_tz_estimado("Itália", origem_pais="vizinhanca_temporal")
    assert r.tz_estimado == "Europe/Rome"
    assert r.veio_de_heranca is True


def test_calcular_com_pais_de_pasta_nao_e_heranca_temporal():
    r = calcular_tz_estimado("França", origem_pais="pasta")
    assert r.tz_estimado == "Europe/Paris"
    assert r.veio_de_heranca is False


def test_calcular_sem_pais_nenhum_nao_marca_heranca():
    r = calcular_tz_estimado(None, origem_pais="vizinhanca_temporal")
    assert r == ResultadoTzEstimado(tz_estimado=None, veio_de_heranca=False)


def test_calcular_pais_desconhecido_da_tabela_nao_marca_heranca():
    # tz None -> mesmo que a origem diga vizinhança, não há o que contar
    # como "ganhou tz por herança".
    r = calcular_tz_estimado("Atlântida", origem_pais="vizinhanca_temporal")
    assert r.tz_estimado is None
    assert r.veio_de_heranca is False


# --- cenário do prompt de origem, ponta a ponta -----------------------------


def test_cenario_viagem_internacional_sem_gps_ganha_tz_por_heranca():
    # "as ~2.235 fotos que hoje só conseguem afirmar país" (ROADMAP.md,
    # item 5) — reconstituído aqui como o caso de uma foto de Portugal/
    # Itália (2001-2018, sem GPS) cujo país só existe por herança temporal.
    resultado = calcular_tz_estimado("Itália", origem_pais="vizinhanca_temporal")
    assert resultado.tz_estimado is not None
    assert resultado.veio_de_heranca is True
