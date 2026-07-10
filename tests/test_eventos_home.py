from fotoorganizer.classification.eventos import (
    extrair_evento,
    keyword_de_evento,
    nome_de_album,
    pasta_tecnica,
)
from fotoorganizer.geolocation.home import detectar_casa, distancia_km


# -- eventos ------------------------------------------------------------
def test_keywords_de_evento():
    assert keyword_de_evento("Serena 15 Anos")
    assert keyword_de_evento("Casamento de João e Maria")
    assert keyword_de_evento("aniversario da ana")
    assert keyword_de_evento("Réveillon 2025")
    assert not keyword_de_evento("Avignon")
    assert not keyword_de_evento("2025_05_24")


def test_pastas_tecnicas_nao_sao_album():
    for tecnica in ["2025_05_24", "[Originals]", "2026", "IMG_0001", "RAW",
                    "exports", "Fotos", "DCIM", "05-24"]:
        assert pasta_tecnica(tecnica), tecnica
        assert not nome_de_album(tecnica), tecnica


def test_nomes_de_album():
    assert nome_de_album("Quizomba")
    assert nome_de_album("Serena 15 Anos")
    assert not nome_de_album("França")   # país não é álbum
    assert not nome_de_album("Viagens")  # categoria não é álbum


def test_extrair_evento_prefere_keyword():
    nome, de_keyword = extrair_evento(
        ["/Users/x/Pictures/2026/Serena 15 Anos"]
    )
    assert (nome, de_keyword) == ("Serena 15 Anos", True)

    nome, de_keyword = extrair_evento(["/Users/x/Pictures/2026/Quizomba"])
    assert (nome, de_keyword) == ("Quizomba", False)

    nome, de_keyword = extrair_evento(
        ["/Users/x/Pictures/2025_05_24/[Originals]"]
    )
    assert nome is None and de_keyword is False


# -- casa -------------------------------------------------------------
def test_distancia_km():
    # São Paulo → Rio ≈ 360 km
    d = distancia_km(-23.55, -46.63, -22.91, -43.17)
    assert 330 < d < 400
    assert distancia_km(10.0, 10.0, 10.0, 10.0) == 0.0


def test_detectar_casa_exige_massa_minima():
    # Poucas fotos com GPS: casa desconhecida (não chuta).
    assert detectar_casa([(-23.55, -46.63)] * 10) is None


def test_detectar_casa_celula_modal():
    casa = [(-23.55 + i * 0.001, -46.63) for i in range(30)]  # mesmo bairro
    viagem = [(48.85, 2.35)] * 5
    resultado = detectar_casa(casa + viagem)
    assert resultado is not None
    lat, lon = resultado
    assert abs(lat - (-23.5)) < 0.2 and abs(lon - (-46.6)) < 0.2


def test_detectar_casa_sem_moda_clara():
    espalhadas = [(float(i), float(i)) for i in range(30)]  # tudo diferente
    assert detectar_casa(espalhadas) is None


def test_nome_de_usuario_nao_e_album():
    # /Users/<login>/Pictures/<data>: nada nomeável — não inventa evento.
    nome, _ = extrair_evento(["/Users/acamerini/Pictures/2025_05_24"])
    assert nome is None
    nome, _ = extrair_evento(["/home/maria/fotos/2024_01_01"])
    assert nome is None
