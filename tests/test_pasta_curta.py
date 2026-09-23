"""`pasta_curta`: o que sai da máquina é o nome curto que a tela mostra,
nunca o caminho absoluto (M2 da auditoria de 2026-09-19, D-094)."""

from fotoorganizer.classification.pasta_curta import (
    nome_curto,
    nomes_curtos_unicos,
    segmentos_uteis,
)


def test_nome_curto_sao_as_duas_ultimas_pastas():
    assert nome_curto("/Users/eu/Pictures/Viagens/Peru 2023") == "Viagens/Peru 2023"
    assert nome_curto("/Volumes/photo/Portfolio/Amsterdam 2016/Canais") == (
        "Amsterdam 2016/Canais"
    )


def test_nome_curto_nunca_comeca_com_barra_nem_carrega_usuario_ou_volume():
    curto = nome_curto("/Users/acamerini/Pictures/Viagens/Peru 2023")
    assert not curto.startswith("/")
    assert "Users" not in curto and "acamerini" not in curto
    curto = nome_curto("/Volumes/photo/Portfolio/Viagens/Peru 2023")
    assert "Volumes" not in curto and "photo" not in curto


def test_caminho_raso_nao_leva_o_volume_nem_o_usuario():
    """Caso real: `/Volumes/Externo/Estrada Real` (2.624 fotos) ia para o
    advisor como `Externo/Estrada Real` — o nome do volume junto. O corte
    das duas últimas pastas não basta quando o caminho é raso; a raiz de
    infraestrutura e o segmento seguinte saem ANTES do recorte."""
    assert nome_curto("/Volumes/Externo/Estrada Real") == "Estrada Real"
    assert nome_curto("/Users/fulano/Viagem") == "Viagem"
    assert nome_curto("/Volumes/photo") == ""
    assert segmentos_uteis("/Volumes/photo/Portfolio/Peru") == ["Portfolio", "Peru"]


def test_nome_curto_de_caminho_raso_ou_relativo_e_o_proprio():
    assert nome_curto("Peru 2023") == "Peru 2023"
    assert nome_curto("/a/b/") == "a/b"
    assert nome_curto("") == ""


def test_barra_invertida_e_nome_valido_nao_separa_pasta():
    # macOS aceita "\" em nome de pasta; tratá-la como separador fundiria
    # duas pastas distintas do disco numa colisão que não existe.
    assert nome_curto("/x/Fotos\\2016") == "x/Fotos\\2016"
    curtos = nomes_curtos_unicos(["/x/Fotos\\2016", "/x/Fotos/2016"])
    assert len(set(curtos.values())) == 2


def test_nomes_curtos_unicos_desempata_colisao_com_um_segmento_util_a_mais():
    curtos = nomes_curtos_unicos([
        "/Users/eu/Pictures/2015/Fotos",
        "/Volumes/nas/Backup/2015/Fotos",
        "/z/Viagens/Peru 2023",
    ])
    assert curtos["/Users/eu/Pictures/2015/Fotos"] == "Pictures/2015/Fotos"
    assert curtos["/Volumes/nas/Backup/2015/Fotos"] == "Backup/2015/Fotos"
    # Quem não colide fica com o recorte padrão — não paga pela colisão alheia.
    assert curtos["/z/Viagens/Peru 2023"] == "Viagens/Peru 2023"
    assert len(set(curtos.values())) == 3
    # Escalar nunca reintroduz usuário/volume.
    assert not any("eu" in c.split("/") or "nas" in c.split("/") for c in curtos.values())


def test_nomes_curtos_unicos_e_injetivo_mesmo_em_colisao_irredutivel():
    # Só diferem na barra final: não há segmento útil a acrescentar. O
    # mapa de volta (resposta do modelo → pasta local) exige nomes
    # distintos; um sufixo fecha a injetividade em vez de deixar a última
    # sobrescrever a outra.
    curtos = nomes_curtos_unicos(["/a/b", "/a/b/", "/Volumes/x", "/Volumes/y"])
    assert len(set(curtos.values())) == 4
    assert curtos["/a/b"] == "a/b"
    assert curtos["/a/b/"] == "a/b (2)"
