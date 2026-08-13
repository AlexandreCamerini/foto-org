"""Modelo de confiança — implementação de docs/CONFIANCA.md.

Cada evidência carrega o score de referência da sua origem; a confiança de
uma sugestão é a do elo mais fraco entre os campos usados no destino.
Nada de somas arbitrárias.
"""

from __future__ import annotations

from fotoorganizer.models import ConfidenceLevel

# Tabela de referência (docs/CONFIANCA.md). Origem → score.
SCORES_REFERENCIA: dict[str, float] = {
    "exif": 0.95,          # data DateTimeOriginal coerente
    "gps": 0.95,           # coordenadas GPS EXIF válidas
    "geocoding_offline": 0.85,
    "geocoding_externo": 0.75,
    "pasta": 0.60,         # país/cidade extraído do nome da pasta
    # GPS herdado de foto de OUTRA fonte tirada a minutos de distância
    # (correlação temporal entre fontes). Mais forte que a vizinhança de
    # sessão: o vínculo é foto-a-foto e a janela é de minutos, não dias.
    "vizinhanca_temporal": 0.75,
    "vizinhanca": 0.55,    # inferido de fotos próximas no tempo
    # Nome de álbum de catálogo externo (Apple Fotos, Lightroom) que cobre o
    # período da sessão. É intenção declarada pelo dono, como o nome de
    # pasta — mas fica ABAIXO de `pasta` (0.60) porque o vínculo é de
    # contemporaneidade, não de pertencimento: a foto está na pasta, e
    # apenas coincide no tempo com o álbum. Mesma natureza (e mesmo score)
    # de `vizinhanca`, com a diferença de que o valor aqui é uma palavra que
    # o dono escreveu, não uma dedução nossa.
    "album_externo": 0.55,
    # Palavra-chave humana em XMP/IPTC (Lightroom, digiKam, Photoshop —
    # `NAMESPACE_CURADORIA`, D-051) que bate com o mesmo vocabulário da
    # pasta ("Viagem", "Família", "Evento"). Mesmo score de `album_externo`
    # e mesmo motivo: é palavra do dono, mas não é a organização dele em
    # diretório — pode ter vindo de um editor de terceiro sem a mesma
    # intenção de classificar o acervo.
    "curadoria": 0.55,
    "agrupamento": 0.70,   # viagem por lacuna temporal
    "llm": 0.55,           # sugerido por LLM a partir de metadados (opt-in)
    # O que a PALAVRA significa — "Pantanal" é lugar, "Quizomba" é festa
    # (classification/lexico.py, opt-in). Acima de `llm` (0.55) porque a
    # pergunta é muito mais estreita: classificar um substantivo em quatro
    # categorias, sem olhar data, GPS nem contagem. Abaixo de `pasta`
    # (0.60) porque a palavra continua sendo do dono e o significado é
    # nosso — quando a pasta decide sozinha, ela decide.
    "lexico": 0.58,
    # Tipo da imagem por sinais de arquivo (nome, pasta, resolução de
    # tela). O score real vem do detector, por sinal — este é só o piso
    # para quando nenhum override chegar.
    "arquivo": 0.70,
    # Data carimbada no nome do arquivo por convenção (IMG-20240315-WA…,
    # Screenshot_2024-03-15…, 20240315_123456). Mais forte que o mtime,
    # que muda a cada cópia entre discos; mais fraca que o EXIF, porque a
    # data do WhatsApp é a do RECEBIMENTO, não a do clique.
    "nome_arquivo": 0.65,
    "fs": 0.40,            # data do filesystem (sem EXIF)
    "visao": 0.30,         # apenas análise visual
    "usuario": 1.00,       # correção manual prevalece sobre tudo
}

_LIMIAR_ALTA = 0.8
_LIMIAR_MEDIA = 0.5


def nivel_para_score(score: float) -> ConfidenceLevel:
    if score >= _LIMIAR_ALTA:
        return ConfidenceLevel.ALTA
    if score >= _LIMIAR_MEDIA:
        return ConfidenceLevel.MEDIA
    return ConfidenceLevel.BAIXA


def elo_mais_fraco(scores: list[float]) -> tuple[ConfidenceLevel, float]:
    """Confiança agregada = menor score entre os campos usados."""
    if not scores:
        return ConfidenceLevel.BAIXA, 0.0
    menor = min(scores)
    return nivel_para_score(menor), menor
