"""Datas escritas no nome da pasta, e o nome que sobra depois de tirá-las.

Caso que originou o módulo: "Visconde de Maua - Abril 2015" era resolvido
como o evento "Portfolio" — o contêiner ganhava da folha e a data era
descartada inteira.
"""

import pytest

from fotoorganizer.grouping.datas import data_no_caminho, separar_data
from fotoorganizer.grouping.eventos import extrair_evento, nome_de_album


@pytest.mark.parametrize(
    "segmento,nome,ano,mes,dia",
    [
        ("Visconde de Maua - Abril 2015", "Visconde de Maua", 2015, 4, None),
        ("Pantanal Jul.2023", "Pantanal", 2023, 7, None),
        ("Julho de 2023", "", 2023, 7, None),
        ("Casamento 12-04-2014", "Casamento", 2014, 4, 12),
        ("2025_05_24", "", 2025, 5, 24),
        ("2026", "", 2026, None, None),
        ("Natal 2019", "Natal", 2019, None, None),
    ],
)
def test_separa_nome_e_data(segmento, nome, ano, mes, dia):
    obtido, data = separar_data(segmento)
    assert obtido == nome
    assert data is not None
    assert (data.ano, data.mes, data.dia) == (ano, mes, dia)


@pytest.mark.parametrize(
    "segmento",
    [
        "Serena 15 Anos",     # "15" não é ano: aniversário, não data
        "Dubai, Thai & Viet",
        "Mar del Plata",      # "Mar" só é março com um ano ao lado
        "Teatro",
        "Estrada Real",
    ],
)
def test_nomes_sem_data_ficam_intactos(segmento):
    nome, data = separar_data(segmento)
    assert (nome, data) == (segmento, None)


def test_mes_invalido_nao_vira_data():
    """"2015-13" não é ano-mês; cai para o ano puro em vez de inventar."""
    nome, data = separar_data("2015-13")
    assert data is not None and (data.ano, data.mes) == (2015, None)
    assert nome == "13"


def test_data_no_caminho_prefere_a_mais_especifica():
    caminho = "/Volumes/photo/Portfolio/2015/Visconde de Maua - Abril 2015"
    data = data_no_caminho(caminho)
    assert data is not None
    assert (data.ano, data.mes) == (2015, 4)
    assert data.rotulo() == "2015-04"


# -- integração com a nomeação de evento --------------------------------
def test_folha_vence_conteiner():
    """O caminho vai do geral ao específico: a pasta mais funda nomeia."""
    nome, de_keyword = extrair_evento(
        ["/Volumes/photo/Portfolio/Fotos Organizadas/"
         "Visconde de Maua - Abril 2015"]
    )
    assert (nome, de_keyword) == ("Visconde de Maua", False)


def test_pastas_de_arrumacao_nao_nomeiam():
    for conteiner in ["Portfolio", "Fotos Organizadas", "Acervo", "Diversos"]:
        assert not nome_de_album(conteiner), conteiner


def test_etapa_de_workflow_na_folha_nao_nomeia():
    """"[Developed]" é etapa de revelação, não o assunto da foto."""
    nome, _ = extrair_evento(["/Users/x/Pictures/Dubai, Thai & Viet/[Developed]"])
    assert nome == "Dubai, Thai & Viet"


def test_keyword_vence_album_mesmo_mais_raso():
    nome, de_keyword = extrair_evento(
        ["/Users/x/Pictures/Serena 15 Anos/Quizomba"]
    )
    assert (nome, de_keyword) == ("Serena 15 Anos", True)


def test_conteiner_de_software_com_extensao_e_tecnico():
    """"Pictures.wrp2" e "Backup.photoslibrary" são pacotes, não álbuns."""
    from fotoorganizer.grouping.eventos import pasta_tecnica

    for conteiner in ["Pictures.wrp2", "Backup.photoslibrary", "Fotos.zip"]:
        assert pasta_tecnica(conteiner), conteiner
    # Uma data com ponto não pode ser confundida com extensão.
    assert not pasta_tecnica("Pantanal Jul.2023")


def test_pacote_de_codigo_nao_nomeia_evento():
    """Segunda linha de defesa: mesmo que a pasta entre no catálogo, o nome
    dela não pode virar nome de evento.

    "BoraChurrascoRio.imageset" tem miolo que parece nome de festa — passou
    pelo teste de contêiner (que olha o miolo) e batizou um evento com 1.314
    fotos de um acervo real dentro. Aqui quem decide é o sufixo.
    """
    from fotoorganizer.grouping.eventos import nome_de_album, pasta_tecnica

    for pacote in ["BoraChurrascoRio.imageset", "Assets.xcassets",
                   "Meu App.framework", "Projeto.xcodeproj"]:
        assert pasta_tecnica(pacote), pacote
        assert not nome_de_album(pacote), pacote

    # E o que é festa de verdade continua nomeando.
    assert nome_de_album("Bora Churrasco Rio")
