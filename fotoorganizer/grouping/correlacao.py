"""Correlação temporal entre fontes: a informação mais correta disponível.

A câmera boa não grava GPS; o telefone grava. Quando as duas fotografam a
mesma cena com minutos de diferença, a foto da câmera pode HERDAR a
localização da foto do telefone — como evidência com origem, confiança
por Δt e justificativa legível, nunca como escrita no arquivo.

Dois problemas resolvidos aqui, ambos como funções puras:

1. Deriva de relógio: câmeras dedicadas vivem com o relógio errado (fuso
   não ajustado na viagem, minutos de atraso). Pares-âncora — a MESMA
   foto presente em duas fontes (mesmo hash rápido ou mesmo phash) —
   revelam o desvio: a mediana de (hora na fonte de referência − hora na
   câmera) por câmera corrige a linha do tempo antes do cruzamento.

2. Herança de GPS: para cada foto sem GPS, a foto COM GPS de outra
   origem (fonte ou câmera diferente) mais próxima na linha do tempo
   corrigida doa suas coordenadas, dentro de uma janela de tolerância.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

# Quanto tempo de distância cada granularidade aguenta (D-025). Em duas horas
# se troca de cidade, não de país — uma janela única seria obrigada a adotar o
# limite da cidade e jogaria fora a informação de país que é segura por muito
# mais tempo. Do mais fino para o mais grosso.
JANELAS_POR_CAMPO: tuple[tuple[str, timedelta], ...] = (
    ("cidade", timedelta(minutes=10)),
    ("regiao", timedelta(hours=2)),
    ("pais", timedelta(hours=12)),
)
# A busca pela doadora usa a maior das janelas; cada campo é filtrado depois.
JANELA_HERANCA = max(janela for _, janela in JANELAS_POR_CAMPO)
# Δt até este limite: confiança cheia da origem; acima, decai até a borda.
_JANELA_CURTA = timedelta(minutes=2)
# Âncoras com desvios muito espalhados indicam pareamento ruim — descarta.
_DISPERSAO_MAX = timedelta(minutes=3)
_MIN_ANCORAS = 2
# Multiplicador quando a hora de alguma das duas fotos veio do mtime. Escolhido
# para derrubar a herança de "alta" para "média" mesmo com Δt curto: 1.0×0.6
# fica abaixo do piso de alta, e a diferença entre medir e supor a hora tem de
# aparecer na badge, não só na justificativa.
_PENALIDADE_HORA_DE_ARQUIVO = 0.6

# — raio de incerteza do lugar herdado (docs/LOCAL_ESTIMADO.md) —
# A coordenada herdada é a da DOADORA, não a da foto. Desenhá-la como ponto
# afirma uma precisão que o dado não tem; o raio é o tamanho honesto dessa
# afirmação. Os três números abaixo foram CALIBRADOS contra 2.083 pares reais
# do acervo em que as duas fotos têm GPS próprio e origens diferentes —
# `scripts/calibrar_raio_incerteza.py` refaz a medição.
#
# Velocidade plausível de deslocamento: ~22 km/h, a média de quem se move numa
# cidade contando as paradas. Não é a velocidade de um carro: é a taxa com que
# a distância até a doadora cresce no acervo medido.
VELOCIDADE_PLAUSIVEL_MS = 6.0
# Piso: nem com Δt zero o círculo vira ponto — a própria coordenada da doadora
# tem a imprecisão do receptor de GPS (5–15 m em céu aberto).
RAIO_PISO_M = 15.0
# Teto: a distância à doadora para de crescer. Medido, não suposto — o p90 da
# banda de 6–12 h (25 km) é MENOR que o da banda de 30 min–2 h (39 km): quem
# fotografa o dia inteiro passa o dia na mesma região. 50 km cobre o p90 de
# todas as bandas de deslocamento real; continuar linear até as 12 h da janela
# de país daria 259 km de raio e não informaria nada.
RAIO_TETO_M = 50_000.0


@dataclass(frozen=True, slots=True)
class FotoRef:
    """Projeção mínima de uma foto para correlação (independente do ORM)."""

    media_id: int
    source_id: int
    quando: datetime
    camera: tuple[str | None, str | None] = (None, None)
    lat: float | None = None
    lon: float | None = None
    hash_rapido: str | None = None
    hash_perceptual: str | None = None
    # `quando` veio do EXIF ou do mtime do arquivo? O mtime costuma ser a
    # hora em que o arquivo foi COPIADO, não em que a foto foi tirada — usar
    # os dois como se valessem o mesmo põe a foto no ponto errado da linha
    # do tempo e produz vizinhança que nunca existiu.
    hora_do_arquivo: bool = False

    @property
    def tem_gps(self) -> bool:
        return self.lat is not None and self.lon is not None

    def outra_origem(self, outra: "FotoRef") -> bool:
        """Fonte ou câmera diferente: duas fotos da mesma câmera na mesma
        fonte já vivem na mesma linha do tempo e não acrescentam nada."""
        return (self.source_id != outra.source_id
                or self.camera != outra.camera)


@dataclass(frozen=True, slots=True)
class Heranca:
    media_id: int
    doador_id: int
    lat: float
    lon: float
    delta: timedelta
    # O que dá para afirmar com este Δt, do mais grosso para o mais fino,
    # com o fator de confiança de cada um. Vazio nunca acontece: uma herança
    # sem nenhum campo confiável não é criada.
    campos: tuple[tuple[str, float], ...]
    # True quando alguma das duas horas veio do mtime do arquivo. A herança
    # continua valendo — é melhor que nada — mas com score menor e dizendo
    # isso na justificativa.
    hora_incerta: bool = False

    def fator_de(self, campo: str) -> float | None:
        """O fator do campo, ou None quando o Δt não permite afirmá-lo."""
        return next((f for c, f in self.campos if c == campo), None)

    @property
    def granularidade(self) -> str:
        """O campo mais fino que este Δt sustenta — o que a justificativa
        precisa dizer para não prometer precisão que não existe."""
        return self.campos[-1][0]

    @property
    def raio_m(self) -> float:
        """Raio, em metros, da região onde esta foto plausivelmente está.

        O mapa desenha isto como círculo; o ponto no centro é da doadora.
        """
        return raio_incerteza(self.delta)


def estimar_offsets(
    fotos: list[FotoRef],
) -> dict[tuple[str | None, str | None], timedelta]:
    """Deriva de relógio por câmera, via pares-âncora entre fontes.

    Âncora = mesma foto em duas fontes (hash rápido igual, ou phash igual
    quando o export foi recomprimido). A fonte que conhece GPS é tratada
    como referência de relógio (Google/Apple normalizam a hora real).
    Devolve {câmera: offset} tal que `quando + offset` aproxima a linha
    do tempo da referência. Câmeras sem âncoras suficientes ou com
    desvios dispersos ficam de fora (offset implícito zero).
    """
    por_conteudo: dict[str, list[FotoRef]] = {}
    for foto in fotos:
        for chave in (foto.hash_rapido, foto.hash_perceptual):
            if chave:
                por_conteudo.setdefault(chave, []).append(foto)

    desvios: dict[tuple[str | None, str | None], list[timedelta]] = {}
    vistos: set[tuple[int, int]] = set()
    for grupo in por_conteudo.values():
        if len(grupo) < 2:
            continue
        for a in grupo:
            for b in grupo:
                if a.media_id >= b.media_id or a.source_id == b.source_id:
                    continue
                if (a.media_id, b.media_id) in vistos:
                    continue
                vistos.add((a.media_id, b.media_id))
                # Referência = quem tem GPS (catálogo de telefone);
                # câmera = quem não tem.
                if a.tem_gps == b.tem_gps:
                    continue
                referencia, camera = (a, b) if a.tem_gps else (b, a)
                if camera.camera == (None, None):
                    continue
                desvios.setdefault(camera.camera, []).append(
                    referencia.quando - camera.quando
                )

    offsets: dict[tuple[str | None, str | None], timedelta] = {}
    for camera, lista in desvios.items():
        if len(lista) < _MIN_ANCORAS:
            continue
        segundos = sorted(d.total_seconds() for d in lista)
        med = median(segundos)
        # Dispersão (mediana dos desvios absolutos em torno da mediana).
        mad = median(abs(s - med) for s in segundos)
        if mad > _DISPERSAO_MAX.total_seconds():
            continue
        offsets[camera] = timedelta(seconds=med)
    return offsets


def herdar_gps(
    fotos: list[FotoRef],
    offsets: dict[tuple[str | None, str | None], timedelta] | None = None,
    janela: timedelta = JANELA_HERANCA,
) -> list[Heranca]:
    """Para cada foto sem GPS, herda a localização da foto com GPS de
    OUTRA origem (fonte ou câmera diferente) mais próxima na linha do
    tempo corrigida, dentro da janela."""
    offsets = offsets or {}

    def corrigida(foto: FotoRef) -> datetime:
        return foto.quando + offsets.get(foto.camera, timedelta())

    doadores = sorted(
        (foto for foto in fotos if foto.tem_gps),
        key=corrigida,
    )
    if not doadores:
        return []
    tempos = [corrigida(d) for d in doadores]

    def procurar(alvo: datetime, foto: FotoRef, inicio: int, passo: int):
        """O doador de OUTRA origem mais próximo, indo para um lado só.

        Os doadores estão ordenados no tempo, então o primeiro que serve
        deste lado é o mais próximo deste lado — e assim que o Δt passa da
        janela, ninguém mais adiante serve. A versão anterior olhava apenas
        os dois vizinhos imediatos e desistia quando ambos eram da mesma
        origem, sem nunca alcançar o terceiro: num acervo real isso barrou
        27.117 candidatos que tinham doador válido logo atrás deles.
        """
        j = inicio
        while 0 <= j < len(doadores):
            delta = abs(tempos[j] - alvo)
            if delta > janela:
                return None
            if foto.outra_origem(doadores[j]):
                return delta, doadores[j]
            j += passo
        return None

    herancas: list[Heranca] = []
    for foto in fotos:
        if foto.tem_gps:
            continue
        alvo = corrigida(foto)
        i = bisect_left(tempos, alvo)
        candidatos = [
            achado for achado in (
                procurar(alvo, foto, i - 1, -1),   # para trás no tempo
                procurar(alvo, foto, i, +1),       # para frente
            )
            if achado is not None
        ]
        if not candidatos:
            continue
        delta, doador = min(candidatos, key=lambda c: c[0])
        # Hora de arquivo em qualquer um dos lados enfraquece a proximidade:
        # "2 minutos de distância" só significa alguma coisa se as duas horas
        # forem de captura. Vale menos, não vale zero — num acervo onde a
        # câmera não gravou data, é a única pista que sobra.
        incerta = foto.hora_do_arquivo or doador.hora_do_arquivo
        campos = campos_confiaveis(delta, incerta)
        if not campos:
            continue
        herancas.append(Heranca(
            media_id=foto.media_id, doador_id=doador.media_id,
            lat=doador.lat, lon=doador.lon, delta=delta,
            campos=campos, hora_incerta=incerta,
        ))
    return herancas


def campos_confiaveis(
    delta: timedelta, hora_incerta: bool = False
) -> tuple[tuple[str, float], ...]:
    """O que dá para afirmar com este Δt, do mais grosso ao mais fino.

    Cada campo decai dentro da PRÓPRIA janela: 1.0 até a janela curta, caindo
    a 0.6 na borda dele. Assim "país a 6 h" e "cidade a 6 min" não competem
    na mesma escala — cada um é medido contra o que a sua granularidade
    aguenta.
    """
    resultado: list[tuple[str, float]] = []
    for campo, janela in sorted(JANELAS_POR_CAMPO, key=lambda cj: -cj[1]):
        if delta > janela:
            continue
        if delta <= _JANELA_CURTA:
            fator = 1.0
        else:
            resto = (delta - _JANELA_CURTA) / (janela - _JANELA_CURTA)
            fator = 1.0 - 0.4 * resto
        if hora_incerta:
            fator *= _PENALIDADE_HORA_DE_ARQUIVO
        resultado.append((campo, round(fator, 3)))
    return tuple(resultado)


def raio_incerteza(delta: timedelta) -> float:
    """Até onde, em metros, a foto pode estar da doadora com este Δt.

    `raio = velocidade plausível × Δt`, preso entre um piso (a imprecisão do
    próprio receptor de GPS) e um teto (a distância em que, no acervo medido,
    o crescimento para). É a mesma frase de D-025 dita em metros: em dez
    minutos não se troca de cidade, em doze horas não se troca de país.

    Cobre 93,6% dos pares medidos do acervo real — a calibração inteira está
    em `docs/LOCAL_ESTIMADO.md`, e `scripts/calibrar_raio_incerteza.py` a
    refaz. Vale para um Δt confiável: quando a hora de um dos lados veio do
    mtime do arquivo (`Heranca.hora_incerta`), o Δt pode estar errado por
    muito mais do que qualquer raio — quem avisa disso é a confiança, não o
    círculo.

    O sinal do Δt não importa: doadora antes ou depois erra igual.
    """
    segundos = abs(delta.total_seconds())
    return min(RAIO_TETO_M,
               max(RAIO_PISO_M, VELOCIDADE_PLAUSIVEL_MS * segundos))
