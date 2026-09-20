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
   Quando existe doadora dos DOIS lados (antes e depois), a mais distante
   não é só descartada: se as duas concordam geograficamente, a granularidade
   fica corroborada por duas evidências independentes; se discordam, essa
   granularidade não é herdada por ninguém — nem pela mais próxima. Ver
   `herdar_gps` e D-074.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

# Quanto tempo de distância cada granularidade aguenta (D-025). Em duas horas
# se troca de cidade, não de país — uma janela única seria obrigada a adotar o
# limite da cidade e jogaria fora a informação de país que é segura por muito
# mais tempo. Do mais fino para o mais grosso.
#
# País em 48 h (D-085, estende D-025): medido por doadora hipotética contra
# o acervo real — a 24-48h, 93,6% dos pares concordam de país (86,9% por
# dia, cada viagem pesando igual); os discordantes se concentram em
# travessia real de fronteira (Patagônia/Tierra del Fuego fev/2020,
# Brasil-Bolívia jul/2023), não em erro de geocodificação. Decisão do
# dono, informado do trade-off contra a janela de 24h (95,7%/dia, ganho
# menor). `scripts/calibrar_janela_pais.py` refaz a medição.
JANELAS_POR_CAMPO: tuple[tuple[str, timedelta], ...] = (
    ("cidade", timedelta(minutes=10)),
    ("regiao", timedelta(hours=2)),
    ("pais", timedelta(hours=48)),
)
# A busca pela doadora usa a maior das janelas; cada campo é filtrado depois.
JANELA_HERANCA = max(janela for _, janela in JANELAS_POR_CAMPO)
# Mesma coisa, como dict — usado pelo teste de concordância (D-074) uma vez
# por foto candidata; construído aqui, não a cada chamada.
_JANELA_DO_CAMPO = dict(JANELAS_POR_CAMPO)
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

# Câmeras cujo GPS vem de um receptor embutido de verdade, não de pareamento
# com celular (D-029, D-086): confirmado no catálogo, a EOS 5D Mark IV grava
# coordenada própria em 2.878/3.633 fotos (79%) e as origens ficam
# coerentes entre si; a R6m2 (3%, 248/8.366) e as demais câmeras do acervo
# derivam de pareamento ou não gravam nada. Só entra aqui quem tem essa
# confirmação — não é "toda Canon", é a que foi medida.
CAMERAS_RECEPTOR_GPS_CONFIAVEL: frozenset[tuple[str | None, str | None]] = (
    frozenset({("Canon", "Canon EOS 5D Mark IV")})
)
# Penalidade da doação same-câmera (D-086): mesmo mecanismo de
# `_PENALIDADE_HORA_DE_ARQUIVO` (mesma constante, motivo diferente) — aqui
# o Δt é confiável, mas a ACURÁCIA da doação em si não foi medida. A
# calibração por doadora hipotética (mesma técnica de D-032/074/085) não
# rendeu amostra: das 3.277 fotos da 5D Mark IV com GPS próprio, 99,8% têm
# a doadora same-câmera mais próxima a ≤10 min (fotos em rajada/sessão) —
# sobram só 5 pares na faixa de 10min-2h, a faixa que a regra precisa
# justificar. Sem amostra, a confiança não pode alegar o mesmo patamar de
# uma herança medida (`vizinhanca_temporal`, teto 0.75 já nunca chega a
# alta) — este fator derruba o teto para 0.45, abaixo do piso de média
# (0.5): o motivo é mecanismo (D-029), não medição, e a badge tem de
# mostrar isso.
_PENALIDADE_MESMA_CAMERA = 0.6

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
# todas as bandas de deslocamento real; continuar linear até a janela de país
# (48 h, D-085) daria mais de 1.000 km de raio e não informaria nada. Este
# teto não muda com a janela de país — as duas coisas medem coisas diferentes
# (deslocamento plausível de pessoa vs. até onde vale afirmar um país).
RAIO_TETO_M = 50_000.0
# Fração dos 2.083 pares medidos em que o lugar verdadeiro coube dentro do
# raio proposto (ponderada pelas bandas de Δt do acervo). Mora aqui, ao lado
# das constantes que a produziram: cobertura declarada longe da fórmula é
# número que envelhece sem ninguém perceber — e a interface promete
# honestidade em cima dele.
COBERTURA_MEDIDA = 0.936


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

    def mesma_camera_confiavel(self, outra: "FotoRef") -> bool:
        """Mesma fonte e câmera, mas com receptor de GPS embutido
        confirmado (`CAMERAS_RECEPTOR_GPS_CONFIAVEL`, D-029/D-086): uma
        foto sem coordenada (falha pontual do receptor) pode herdar de
        outra do MESMO rolo, porque a informação não veio do relógio de
        outra fonte — veio do próprio receptor, que sabe onde a câmera
        estava. Fallback de `procurar` (regra 1): só entra quando não há
        doadora de outra origem no mesmo lado dentro da janela — nunca
        desloca uma doadora medida por uma sem amostra (D-086)."""
        return (self.source_id == outra.source_id
                and self.camera == outra.camera
                and self.camera in CAMERAS_RECEPTOR_GPS_CONFIAVEL)


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
    # Granularidades (subconjunto de "cidade"/"regiao") em que existia
    # doadora dos DOIS lados e as duas concordaram geograficamente — os
    # círculos de incerteza de cada lado se sobrepõem (D-074). Vazio é o
    # caso comum: só uma doadora, ou a segunda longe demais para valer para
    # aquele campo. "pais" nunca aparece aqui de propósito — ver
    # `herdar_gps`.
    concordancia: tuple[str, ...] = ()
    # Id da doadora do outro lado, só quando ela participou de ao menos uma
    # concordância acima. None no caso comum de âncora única.
    doador_concordante_id: int | None = None
    # True quando a doadora é a mesma câmera/fonte (regra 1, D-086) — só
    # possível para `CAMERAS_RECEPTOR_GPS_CONFIAVEL`. O Δt é confiável (não
    # é o mesmo problema de `hora_incerta`), mas a acurácia da doação não
    # foi medida — só o mecanismo (D-029) sustenta a herança.
    mesma_camera: bool = False

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
        `self.delta` já é o menor dos dois lados quando existem os dois (a
        escolha de doadora sempre prefere o mais próximo) — como
        `raio_incerteza` é monótona em Δt, isto já é o menor raio possível
        entre os dois lados, concordando ou não. Ver D-074: apertar o raio
        além disso exigiria uma geometria de interseção que a medição não
        pediu.
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
    tempo corrigida, dentro da janela.

    Quando existe doadora dos dois lados (antes e depois), a mais distante
    não é só descartada — ela testemunha a favor ou contra a mais próxima
    (D-074), campo a campo:

    - Se o Δt do lado mais distante também cabe na janela daquele campo, as
      duas coordenadas são comparadas: concordam se a distância geométrica
      entre elas cabe dentro da soma dos dois raios de incerteza
      (`raio_incerteza`, já calibrados — nenhuma constante nova). Concordar
      não aumenta o fator do campo (seria bônus inventado); o Δt usado
      continua sendo o do lado mais próximo, igual antes.
    - Se discordam, esse campo NÃO é herdado por ninguém — nem pelo lado
      mais próximo. Duas doadoras a horas de distância uma da outra, uma de
      cada lado, é o sinal de que a foto do meio está EM TRÂNSITO: nenhuma
      das duas sabe onde ela estava.
    - Se o lado mais distante está fora da janela daquele campo (só um lado
      tem opinião), o campo segue como sempre seguiu — âncora única, sem
      teste, sem regressão.

    `pais` fica de fora deste teste de propósito: `raio_incerteza` é
    calibrado para deslocamento de pessoa em até 12 h (teto 50 km), não
    para o tamanho de um país (centenas/milhares de km) — reaplicar o
    mesmo raio quebraria casos óbvios (duas doadoras a 300 km, claramente
    no mesmo país, falhariam o teste). Resolver isso direito pede
    geocodificação, que este módulo deliberadamente não tem (D-074).

    Limitação conhecida, não escondida: uma ida e volta no mesmo dia entre
    duas âncoras concordantes (casa → cidade vizinha → casa, sem foto com
    GPS na cidade vizinha) produz falso-negativo — a foto do meio herda
    "casa" com a confiança de concordância, mesmo tendo sido tirada em
    outro lugar. Aceitável dado o teto de granularidade e o próprio raio de
    incerteza, mas precisa estar escrito, não escondido.
    """
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

        Regra 1 (D-086): uma doadora da MESMA câmera com receptor
        confirmado nunca vence uma doadora de outra origem — só serve como
        fallback quando não existe nenhuma de outra origem deste lado
        dentro da janela. Por isso o laço não pode parar no primeiro
        candidato de mecanismo: precisa varrer o lado inteiro à procura de
        uma cross-source antes de aceitar o fallback (medido: sem isso,
        296 heranças cross-source existentes eram deslocadas por uma
        same-câmera mais próxima, sem amostra, rebaixando a badge de
        média para baixa sem motivo).

        Devolve `(delta, candidata, cross)` — `cross=False` marca o
        fallback. O terceiro elemento existe porque preferir cross-source
        é uma decisão de DOIS lados, não de um: `min(achados)` por Δt cru
        deixaria uma same-câmera de um lado vencer uma cross-source do
        OUTRO lado só por estar mais perto — a revisão que achou o bug
        original também achou esta segunda metade dele (media real
        perdendo uma oferta de região que tinha antes desta fatia).
        """
        fallback = None
        j = inicio
        while 0 <= j < len(doadores):
            delta = abs(tempos[j] - alvo)
            if delta > janela:
                break
            candidata = doadores[j]
            if foto.outra_origem(candidata):
                return delta, candidata, True
            if fallback is None and foto.mesma_camera_confiavel(candidata):
                fallback = (delta, candidata, False)
            j += passo
        return fallback

    herancas: list[Heranca] = []
    for foto in fotos:
        if foto.tem_gps:
            continue
        alvo = corrigida(foto)
        i = bisect_left(tempos, alvo)
        achados = [
            achado for achado in (
                procurar(alvo, foto, i - 1, -1),   # para trás no tempo
                procurar(alvo, foto, i, +1),       # para frente
            )
            if achado is not None
        ]
        if not achados:
            continue
        # Cross-source de QUALQUER lado vence same-câmera de QUALQUER lado,
        # não só dentro do mesmo lado — só quando os dois lados são
        # fallback (nenhuma cross-source em nenhum dos dois) é que o
        # fallback mais próximo é aceito.
        cross_achados = [a for a in achados if a[2]]
        candidatos = cross_achados or achados
        delta, doador, cross = min(candidatos, key=lambda c: c[0])
        # O outro lado, quando existe (diferente do escolhido acima) — quem
        # testemunha a favor ou contra a proximidade encontrada. Comparado
        # por media_id, não pela tupla inteira: os dois lados nunca podem
        # ser fisicamente o mesmo registro (índices disjuntos em `procurar`),
        # mas media_id é a identidade real, não uma coincidência de campos.
        outro = next(
            (a for a in achados if a[1].media_id != doador.media_id), None
        )
        # Hora de arquivo em qualquer um dos lados enfraquece a proximidade:
        # "2 minutos de distância" só significa alguma coisa se as duas horas
        # forem de captura. Vale menos, não vale zero — num acervo onde a
        # câmera não gravou data, é a única pista que sobra.
        incerta = foto.hora_do_arquivo or doador.hora_do_arquivo
        # Regra 1 (D-086): a doadora escolhida é a própria câmera/fonte —
        # só possível quando `cross` é False (fallback de mecanismo).
        mesma_cam = not cross
        campos_base = campos_confiaveis(delta, incerta, mesma_cam)
        if not campos_base:
            continue
        campos, concordancia = _confrontar_com_outro_lado(
            campos_base, delta, doador, outro, incerta,
        )
        if not campos:
            continue
        # Regra 1 (D-086): herança same-câmera só sustenta país — capar
        # aqui (não só filtrar drafts em `_evidencias_geo`) faz
        # `Heranca.granularidade` refletir a verdade, então a cláusula
        # existente de "essa distância não sustenta a cidade" dispara
        # sozinha na justificativa, sem precisar de uma segunda guarda
        # duplicada (achado da 3ª rodada de revisão). "pais" nunca falta
        # aqui (sempre dentro da própria janela, D-025) e nunca entra em
        # `concordancia` (excluído do teste geométrico, ver acima) — sem
        # `if not campos` nem filtro de concordância: os dois seriam
        # ramos inalcançáveis (achado da 4ª rodada de revisão).
        if mesma_cam:
            campos = tuple((c, f) for c, f in campos if c == "pais")
        herancas.append(Heranca(
            media_id=foto.media_id, doador_id=doador.media_id,
            lat=doador.lat, lon=doador.lon, delta=delta,
            campos=campos, hora_incerta=incerta,
            concordancia=concordancia,
            mesma_camera=mesma_cam,
            doador_concordante_id=(
                outro[1].media_id if outro is not None and concordancia
                else None
            ),
        ))
    return herancas


def _confrontar_com_outro_lado(
    campos_base: tuple[tuple[str, float], ...],
    delta: timedelta,
    doador: FotoRef,
    outro: tuple[timedelta, FotoRef, bool] | None,
    incerta: bool,
) -> tuple[tuple[tuple[str, float], ...], tuple[str, ...]]:
    """Testa cada campo (exceto país) contra a doadora do outro lado.

    Sem outro lado (achado único), nada muda — devolve `campos_base` como
    veio. Com os dois lados, cada campo cujo Δt do lado mais distante
    também cabe na janela daquele campo é confrontado: concordam se os
    círculos de incerteza (`raio_incerteza` de cada lado) se sobrepõem;
    discordam se não. Campo discordante é removido — não herdado por
    ninguém, nem pelo lado mais próximo (D-074).

    Hora de QUALQUER um dos três lados envolvidos (a foto que herda, o
    doador escolhido — juntos, `incerta` — ou o doador do outro lado)
    vinda do mtime do arquivo derruba a confiabilidade do Δt usado no
    teste geométrico: um raio calculado sobre um Δt que pode estar
    arbitrariamente errado não prova nada. O campo simplesmente não é
    testado (fica como se só houvesse um lado) — e por construção nunca
    entra em `concordancia`, então a justificativa nunca pode dizer
    "confirmada" na mesma frase em que já avisa que a hora é incerta.

    Testemunha same-câmera (regra 1, D-086, `outro[2] is False`) entra na
    mesma categoria: a corroboração geométrica foi calibrada para doadora
    de OUTRA origem (D-074), não para este caso — sem isso, uma
    testemunha sem amostra podia conceder "confirmada" a uma herança
    cross-source medida (achado da 3ª rodada de revisão).
    """
    if outro is None:
        return campos_base, ()
    delta_outro, doador_outro, cross_outro = outro
    if incerta or doador_outro.hora_do_arquivo or not cross_outro:
        return campos_base, ()

    resultado: list[tuple[str, float]] = []
    concordancia: list[str] = []
    for campo, fator in campos_base:
        if campo == "pais" or delta_outro > _JANELA_DO_CAMPO[campo]:
            resultado.append((campo, fator))
            continue
        distancia = _distancia_m(
            (doador.lat, doador.lon), (doador_outro.lat, doador_outro.lon)
        )
        raio_combinado = raio_incerteza(delta) + raio_incerteza(delta_outro)
        if distancia <= raio_combinado:
            resultado.append((campo, fator))
            concordancia.append(campo)
        # else: discordam — este campo não sobrevive, nem para o lado mais
        # próximo. Duas doadoras a horas uma da outra, dos dois lados,
        # significam que a foto do meio está em trânsito.
    return tuple(resultado), tuple(concordancia)


_RAIO_TERRA_M = 6_371_008.8


def _distancia_m(
    a: tuple[float, float], b: tuple[float, float]
) -> float:
    """Distância haversine entre duas coordenadas, em metros.

    Mesma fórmula de `scripts/calibrar_raio_incerteza.py`: duplicada de
    propósito, não importada — o script é uma ferramenta de calibração
    offline, e este módulo puro não deveria depender dele.
    """
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * _RAIO_TERRA_M * math.asin(min(1.0, math.sqrt(h)))


def campos_confiaveis(
    delta: timedelta, hora_incerta: bool = False, mesma_camera: bool = False
) -> tuple[tuple[str, float], ...]:
    """O que dá para afirmar com este Δt, do mais grosso ao mais fino.

    Cada campo decai dentro da PRÓPRIA janela: 1.0 até a janela curta, caindo
    a 0.6 na borda dele. Assim "país a 6 h" e "cidade a 6 min" não competem
    na mesma escala — cada um é medido contra o que a sua granularidade
    aguenta.

    `mesma_camera` (regra 1, D-086) é independente de `hora_incerta`: o Δt
    continua confiável, mas a doação em si (mesmo rolo, mesma câmera) não
    tem amostra medida de acurácia — só o mecanismo do receptor (D-029).
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
        if mesma_camera:
            fator *= _PENALIDADE_MESMA_CAMERA
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


def _metros_legiveis(metros: float) -> str:
    """Metros até o quilômetro, quilômetros depois — com vírgula decimal."""
    if metros < 1000:
        return f"{round(metros)} m"
    km = f"{metros / 1000:.1f}".rstrip("0").rstrip(".")
    return f"{km.replace('.', ',')} km"


def _tempo_legivel(delta: timedelta) -> str:
    segundos = int(abs(delta.total_seconds()))
    if segundos < 60:
        return f"{segundos} s"
    if segundos < 3600:
        return f"{segundos // 60} min"
    horas, minutos = divmod(segundos // 60, 60)
    return f"{horas} h" if minutos == 0 else f"{horas} h {minutos} min"


# A cobertura dita uma vez, para a legenda — e não repetida em cada um dos
# milhares de pontos do mapa. É a mesma promessa de `COBERTURA_MEDIDA`, em
# português.
#
# `COBERTURA_MEDIDA` só vale para o domínio que `calibrar_raio_incerteza.py`
# mede: doadora dentro de `_JANELA_MOVIMENTO` (12h, D-085) — deslocamento de
# pessoa, onde `raio_incerteza` já satura. Herança de país de 12h a 48h
# (D-085) cai fora dessa medição por desenho (`raio_incerteza` não é
# calibrado para escala de país, D-074/D-025); medido à parte para esta
# nota (`scripts/calibrar_raio_incerteza.py` sobre pares de 12–48h): 70,7%
# bruta / 59,0% por dia — bem abaixo da promessa de 12h. Repetir o mesmo
# número para os dois casos mentiria sobre o círculo justamente onde D-085
# alarga o alcance.
JANELA_COBERTURA_MEDIDA_S = 12 * 3600
NOTA_DO_RAIO = (
    f"O círculo é o tamanho da dúvida, não um erro de medição: em "
    f"{COBERTURA_MEDIDA * 100:.1f}".replace(".", ",")
    + "% dos pares medidos neste acervo, o lugar verdadeiro cabe dentro dele."
)
NOTA_DO_RAIO_ALEM_DA_MEDICAO = (
    "O círculo é o tamanho da dúvida, não um erro de medição — mas alguma "
    "foto deste grupo herdou de uma doadora a mais de 12 h de distância: a "
    "fórmula do raio não foi medida nessa escala (ela mede deslocamento de "
    "pessoa, não travessia de fronteira), e o lugar verdadeiro pode estar "
    "fora do círculo."
)
# Regra 1 da herança (D-086): a doadora é a própria câmera, com receptor
# GPS confirmado (D-029) — Δt confiável, mas SEM amostra medida de
# acurácia (a diferença de `NOTA_DO_RAIO_ALEM_DA_MEDICAO`: aqui não é
# escala de tempo, é falta de medição mesmo dentro da janela normal).
NOTA_DO_RAIO_MESMA_CAMERA = (
    "O círculo é o tamanho da dúvida, não um erro de medição — mas alguma "
    "foto deste grupo herdou da própria câmera (receptor de GPS embutido "
    "confirmado, sem doadora de outra fonte por perto): a fórmula do raio "
    "não foi calibrada para este caso, só o mecanismo do receptor "
    "sustenta a herança."
)
# As duas ressalvas acima respondem perguntas diferentes (escala de tempo
# vs. falta de medição) e podem coexistir no mesmo grupo — perder uma
# delas por "a outra venceu" escondia um risco real (achado da 2ª rodada
# de revisão).
NOTA_DO_RAIO_MESMA_CAMERA_E_ALEM_DA_MEDICAO = (
    "O círculo é o tamanho da dúvida, não um erro de medição — mas este "
    "grupo tem DUAS heranças fora do que foi medido: alguma foto herdou "
    "da própria câmera (receptor de GPS embutido, sem amostra de "
    "acurácia) e alguma foto herdou de uma doadora a mais de 12 h de "
    "distância (fora da escala de deslocamento que a fórmula mede). O lugar "
    "verdadeiro pode estar fora do círculo nos dois casos, por motivos "
    "diferentes."
)


def frase_do_raio(
    delta: timedelta, doadora: str | None = None, mesma_camera: bool = False,
) -> str:
    """Por que este círculo tem este tamanho, em uma frase para a tela.

    Nasce aqui, e não em TypeScript, pelo mesmo motivo que `raio_incerteza`:
    a frase cita o raio e a velocidade que o produziram. Remontá-la do outro
    lado da API duplicaria as constantes — e constante duplicada é constante
    que diverge no dia em que a calibração for refeita.

    Três formas, porque a fórmula tem três regimes e cada um explica o
    tamanho por um motivo diferente: no piso o círculo é o erro do receptor,
    no teto ele parou de crescer, no meio ele é velocidade × tempo.

    `mesma_camera` (regra 1, D-086) acrescenta uma ressalva: o raio usa a
    MESMA fórmula (não há uma calibrada só para este caso), mas a doadora é
    a própria câmera, sem amostra medida de acurácia.
    """
    raio = raio_incerteza(delta)
    quem = f"de {doadora}" if doadora else "de outra foto"
    if raio <= RAIO_PISO_M:
        frase = (
            f"Lugar herdado {quem}, no mesmo instante — o raio de "
            f"{_metros_legiveis(raio)} é só a imprecisão do receptor de GPS "
            "que emprestou a coordenada."
        )
    else:
        quando = _tempo_legivel(delta)
        if raio >= RAIO_TETO_M:
            frase = (
                f"Lugar herdado {quem}, a {quando} de distância — o raio "
                f"para de crescer em {_metros_legiveis(raio)}: neste "
                "acervo, quem fotografa o dia inteiro passa o dia na "
                "mesma região."
            )
        else:
            frase = (
                f"Lugar herdado {quem}, a {quando} de distância — a "
                f"{round(VELOCIDADE_PLAUSIVEL_MS * 3.6)} km/h, a "
                "velocidade de quem anda por uma cidade contando as "
                f"paradas, isso dá {_metros_legiveis(raio)} de dúvida."
            )
    if mesma_camera:
        frase += (
            "; a doadora é a própria câmera (receptor de GPS embutido) — "
            "sem amostra medida de acurácia para este caso"
        )
    return frase
