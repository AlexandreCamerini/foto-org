"""Datas escritas no nome da pasta, e o nome que sobra depois de tirá-las.

Caso que originou o módulo: "Visconde de Maua - Abril 2015" era resolvido
como o evento "Portfolio" — o contêiner ganhava da folha e a data era
descartada inteira.
"""

import unicodedata

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
        # D-073: "dia de mês de ano" por extenso — sem este padrão, só a
        # cauda "outubro de 2016" casava e "29 de" sobrava como nome.
        ("29 de outubro de 2016", "", 2016, 10, 29),
        ("5 de janeiro de 2014", "", 2014, 1, 5),
    ],
)
def test_separa_nome_e_data(segmento, nome, ano, mes, dia):
    obtido, data = separar_data(segmento)
    assert obtido == nome
    assert data is not None
    assert (data.ano, data.mes, data.dia) == (ano, mes, dia)


@pytest.mark.parametrize("forma", ["NFC", "NFD"])
def test_marco_em_nfd_bate_igual_a_nfc(forma):
    """O Finder/APFS grava pasta acentuada em NFD (marcador combinante
    decomposto, ex. "c" + U+0327 em vez do "ç" precomposto). "Março" em NFD
    precisa continuar reconhecido como mês, igual à forma NFC digitada no
    dict de `_MESES`."""
    segmento = unicodedata.normalize(forma, "Chapada dos Guimarães Março 2019")
    nome, data = separar_data(segmento)
    assert data is not None
    assert (data.ano, data.mes) == (2019, 3)
    assert nome == unicodedata.normalize("NFC", "Chapada dos Guimarães")


@pytest.mark.parametrize("forma", ["NFC", "NFD"])
def test_data_no_caminho_reconhece_marco_em_nfd(forma):
    caminho = unicodedata.normalize(
        forma, "/Volumes/photo/Viagens/Chapada dos Guimarães Março 2019"
    )
    data = data_no_caminho(caminho)
    assert data is not None
    assert (data.ano, data.mes) == (2019, 3)


@pytest.mark.parametrize(
    "segmento",
    [
        "novembro 30", "julho 15", "setembro 06", "março 20", "dezembro 07",
    ],
)
def test_mes_dia_sem_ano_esvazia_o_nome(segmento):
    """D-073 (achado 5 de D-069): pasta cronológica por dia dentro do ano
    ("2009/novembro 30") — o ano mora na pasta-mãe, não neste segmento, mas
    o segmento continua sendo data, não nome. Sem isto, virava "nome de
    álbum" e a regra 6 da cascata promovia a evento falso — 3.220 fotos
    reais do acervo (grupos como "Eventos/2009/novembro 30")."""
    nome, data = separar_data(segmento)
    assert nome == ""
    # Não há ano neste segmento para montar `DataDaPasta` — quem cruza com
    # o ano da pasta-mãe é `data_no_caminho`, não este teste.
    assert data is None


def test_mes_dia_sem_ano_so_esvazia_o_segmento_inteiro():
    """Âncora no segmento inteiro, de propósito: um nome de verdade que só
    CONTÉM "mês dia" não pode ser esvaziado por acidente."""
    nome, data = separar_data("Viagem novembro 30")
    assert nome == "Viagem novembro 30"
    assert data is None


def test_marco_em_nfd_bate_nos_padroes_novos_tambem():
    """D-073: macOS normaliza nome de pasta pra NFD ("marc" + cedilha
    combinante, não o "ç" precomposto que `_MESES` usa) — visualmente
    idêntico, byte a byte diferente. Sem normalizar, era o único mês do
    calendário que sobrevivia ao resto do fix (todos os outros são ASCII
    puro): 586 fotos reais tinham destino tipo "Eventos/2007/março 10"
    mesmo depois do fix de "mês sem ano" já estar no ar."""
    nfd = unicodedata.normalize("NFD", "março 10")
    assert nfd != "março 10"  # a premissa do teste: são bytes diferentes
    assert separar_data(nfd) == ("", None)

    nfd_longo = unicodedata.normalize("NFD", "17 de março de 2015")
    nome, data = separar_data(nfd_longo)
    assert nome == ""
    assert data is not None and (data.ano, data.mes, data.dia) == (2015, 3, 17)


@pytest.mark.parametrize("segmento", ["Julho 85", "Dezembro 99", "Maio 32"])
def test_mes_dia_sem_ano_valida_faixa_do_dia(segmento):
    """Achado da revisão fresh-eyes: sem validar 1-31, "Julho 85" (não é
    dia nenhum) seria engolido do mesmo jeito que uma data de verdade —
    perdendo o nome à toa. Mesma faixa que `_montar` já valida pros outros
    padrões."""
    nome, data = separar_data(segmento)
    assert nome == segmento
    assert data is None


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


# -- data no nome do ARQUIVO --------------------------------------------------
# WhatsApp, câmera de celular e captura de tela carimbam a data no nome.
# Para foto sem EXIF, esse carimbo é uma testemunha muito melhor que o
# mtime — que muda a cada cópia entre discos.

def _nome(nome):
    from fotoorganizer.grouping.datas import data_no_nome

    return data_no_nome(nome)


def test_nome_whatsapp_carrega_a_data():
    d = _nome("IMG-20240315-WA0012.jpg")
    assert d is not None
    assert (d.data.year, d.data.month, d.data.day) == (2024, 3, 15)
    assert "WhatsApp" in d.padrao
    assert d.texto == "20240315"


def test_nome_de_video_whatsapp_tambem():
    d = _nome("VID-20230801-WA0003.mp4")
    assert d is not None and d.data.year == 2023


def test_nome_compacto_de_camera_de_celular():
    # Samsung/Android: 20240315_123456.jpg; e IMG_20240315_123456.
    for nome in ["20240315_123456.jpg", "IMG_20240315_123456.jpg",
                 "PXL_20240315_123456789.jpg"]:
        d = _nome(nome)
        assert d is not None, nome
        assert (d.data.year, d.data.month, d.data.day) == (2024, 3, 15), nome


def test_nome_iso_de_captura_e_mensageiro():
    for nome in ["Screenshot_2024-03-15-10-30-22.png",
                 "Captura de Tela 2024-03-15 às 10.30.22.png",
                 "photo_2024-03-15_10-30-00.jpg",
                 "WhatsApp Image 2024-03-15 at 10.30.00.jpeg"]:
        d = _nome(nome)
        assert d is not None, nome
        assert (d.data.year, d.data.month, d.data.day) == (2024, 3, 15), nome


def test_nome_sem_data_ou_com_data_impossivel_nao_inventa():
    assert _nome("IMG_1234.jpg") is None          # contador, não data
    assert _nome("Serena 15 Anos.jpg") is None
    assert _nome("096A9198.DNG") is None
    assert _nome("IMG-20241315-WA0001.jpg") is None   # mês 13
    assert _nome("IMG-20990315-WA0001.jpg") is None   # futuro


def test_numero_de_serie_nao_vira_data():
    """8 dígitos que por acaso parecem data válida mas estão colados em
    mais dígitos (número de série, hash) não casam."""
    assert _nome("P1020240315999.jpg") is None
