"""Sugestão de agrupamento: hierarquia geográfica (a partir do nome das
pastas) + agrupamento por viagem (a partir de lacunas na linha do tempo) +
score de confiança pra cada sugestão."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.geo_data import identificar_pais
from app.models import Photo

# Lacuna mínima entre duas fotos consecutivas pra considerar que começou uma
# viagem nova — 3 dias sem foto nenhuma é um bom sinal de "voltou pra casa".
_GAP_MINIMO_NOVA_VIAGEM = timedelta(days=3)


@dataclass
class HierarquiaGeografica:
    pais: str | None
    regiao: str | None
    cidade: str | None

    def label(self) -> str:
        partes = [p for p in (self.pais, self.regiao, self.cidade) if p]
        return " > ".join(partes) if partes else "Local não identificado"


def extrair_hierarquia_geografica(pasta_fonte: str) -> HierarquiaGeografica:
    """Analisa os segmentos do caminho da pasta em busca de um país
    conhecido; o que vem depois dele vira região/cidade."""
    segmentos = [s for s in Path(pasta_fonte).parts if s not in ("/", "\\")]

    indice_pais = None
    pais_canonico = None
    for i, segmento in enumerate(segmentos):
        encontrado = identificar_pais(segmento)
        if encontrado:
            indice_pais, pais_canonico = i, encontrado
            break

    if indice_pais is None:
        # Sem país reconhecido: melhor esforço é a pasta mais funda como
        # "cidade" — sugestão de baixa confiança, não inventa país.
        cidade = segmentos[-1] if segmentos else None
        return HierarquiaGeografica(pais=None, regiao=None, cidade=cidade)

    resto = segmentos[indice_pais + 1 :]
    if not resto:
        return HierarquiaGeografica(pais=pais_canonico, regiao=None, cidade=None)
    if len(resto) == 1:
        return HierarquiaGeografica(pais=pais_canonico, regiao=None, cidade=resto[0])
    # Mais de um nível abaixo do país: o penúltimo é tratado como região, o
    # último (mais fundo) como cidade.
    return HierarquiaGeografica(pais=pais_canonico, regiao=resto[-2], cidade=resto[-1])


def _data_de_referencia(foto: Photo) -> datetime:
    return foto.data_exif or foto.data_arquivo


def agrupar_por_viagem(photos: list[Photo]) -> dict[int, str]:
    """Devolve `{photo.id: rótulo_da_viagem}`, clusterizando por data com o
    limiar `_GAP_MINIMO_NOVA_VIAGEM`. Fotos sem nenhuma data ficam de fora
    (não dá pra saber em que viagem entram)."""
    com_data = [(foto, _data_de_referencia(foto)) for foto in photos]
    com_data.sort(key=lambda par: par[1])

    rotulo_por_id: dict[int, str] = {}
    viagem_atual: list[tuple[Photo, datetime]] = []
    numero_viagem = 0

    def _fechar_viagem():
        nonlocal numero_viagem
        if not viagem_atual:
            return
        numero_viagem += 1
        inicio = viagem_atual[0][1].strftime("%d/%m/%Y")
        fim = viagem_atual[-1][1].strftime("%d/%m/%Y")
        rotulo = f"Viagem {numero_viagem} ({inicio} – {fim})" if inicio != fim else f"Viagem {numero_viagem} ({inicio})"
        for foto, _ in viagem_atual:
            rotulo_por_id[foto.id] = rotulo

    for foto, data in com_data:
        if viagem_atual and (data - viagem_atual[-1][1]) > _GAP_MINIMO_NOVA_VIAGEM:
            _fechar_viagem()
            viagem_atual = []
        viagem_atual.append((foto, data))
    _fechar_viagem()

    return rotulo_por_id


def calcular_score_confianca(foto: Photo, hierarquia: HierarquiaGeografica) -> float:
    score = 0.0
    if hierarquia.pais:
        score += 0.4
    if hierarquia.cidade and hierarquia.cidade != hierarquia.pais:
        score += 0.2
    if foto.data_exif is not None:
        score += 0.2
    if foto.localizacao_exif:
        score += 0.2
    return round(min(score, 1.0), 2)


def gerar_sugestoes(photos: list[Photo]) -> list[dict]:
    """Calcula (sem persistir) a sugestão de agrupamento + score pra cada
    foto. Quem chama decide se grava isso em `sugestao_agrupamento`/
    `score_confianca` ou só devolve pro cliente."""
    rotulos_viagem = agrupar_por_viagem(photos)

    resultado = []
    for foto in photos:
        hierarquia = extrair_hierarquia_geografica(foto.pasta_fonte)
        viagem = rotulos_viagem.get(foto.id)
        partes_label = [viagem, hierarquia.label()] if viagem else [hierarquia.label()]
        sugestao = " · ".join(p for p in partes_label if p)

        resultado.append(
            {
                "photo_id": foto.id,
                "sugestao_agrupamento": sugestao,
                "score_confianca": calcular_score_confianca(foto, hierarquia),
                "pais": hierarquia.pais,
                "regiao": hierarquia.regiao,
                "cidade": hierarquia.cidade,
                "viagem": viagem,
            }
        )
    return resultado
