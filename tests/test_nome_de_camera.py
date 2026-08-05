"""O nome da câmera não repete o fabricante que já está no modelo."""

from fotoorganizer.metadata.camera import nome_da_camera


def test_canon_nao_vira_canon_canon():
    # O caso real: toda linha da Revisão dizia "Canon Canon EOS 5D Mark III".
    assert nome_da_camera("Canon", "Canon EOS 5D Mark III") == (
        "Canon EOS 5D Mark III"
    )


def test_fabricante_que_nao_se_repete_continua_inteiro():
    assert nome_da_camera("NIKON CORPORATION", "NIKON D850") == (
        "NIKON CORPORATION NIKON D850"
    )


def test_caixa_diferente_ainda_conta_como_repeticao():
    assert nome_da_camera("CANON", "Canon EOS R5") == "Canon EOS R5"


def test_prefixo_que_so_parece_igual_nao_e_cortado():
    # "Canon" não pode engolir o "Canonical" de um modelo que por acaso
    # comece com as mesmas letras — cortar aqui inventaria um nome.
    assert nome_da_camera("Canon", "Canonical XYZ") == "Canon Canonical XYZ"


def test_so_fabricante():
    assert nome_da_camera("Apple", None) == "Apple"


def test_so_modelo():
    assert nome_da_camera(None, "iPhone 15 Pro") == "iPhone 15 Pro"


def test_nada_e_none_nao_string_vazia():
    assert nome_da_camera(None, None) is None
    assert nome_da_camera("", "  ") is None
