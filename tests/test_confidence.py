from fotoorganizer.classification import (
    SCORES_REFERENCIA,
    elo_mais_fraco,
    nivel_para_score,
)
from fotoorganizer.models import ConfidenceLevel


def test_mapeamento_de_niveis():
    assert nivel_para_score(0.95) == ConfidenceLevel.ALTA
    assert nivel_para_score(0.80) == ConfidenceLevel.ALTA
    assert nivel_para_score(0.60) == ConfidenceLevel.MEDIA
    assert nivel_para_score(0.50) == ConfidenceLevel.MEDIA
    assert nivel_para_score(0.40) == ConfidenceLevel.BAIXA


def test_elo_mais_fraco_manda():
    # EXIF alta + pasta média → sugestão média: o campo fraco puxa para baixo.
    nivel, score = elo_mais_fraco([0.95, 0.60])
    assert nivel == ConfidenceLevel.MEDIA
    assert score == 0.60

    nivel, _ = elo_mais_fraco([0.95, 0.85, 0.95])
    assert nivel == ConfidenceLevel.ALTA


def test_sem_evidencia_e_baixa():
    nivel, score = elo_mais_fraco([])
    assert nivel == ConfidenceLevel.BAIXA
    assert score == 0.0


def test_tabela_de_referencia_coerente():
    # Correção do usuário prevalece; visão é a mais fraca; EXIF/GPS são altas.
    assert SCORES_REFERENCIA["usuario"] == 1.0
    assert SCORES_REFERENCIA["exif"] >= 0.8
    assert SCORES_REFERENCIA["gps"] >= 0.8
    assert SCORES_REFERENCIA["visao"] < 0.5
    assert SCORES_REFERENCIA["fs"] < 0.5
