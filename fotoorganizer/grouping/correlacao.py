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
JANELAS_POR_CAMPO: tuple[tuple[str, timedelta], ...] = (
    ("cidade", timedelta(minutes=10)),
    ("regiao", timedelta(hours=2)),
    ("pais", timedelta(hours=12)),
)
# A busca pela doadora usa a maior das janelas; cada campo é filtrado depois.
JANELA_HERANCA = max(janela for _, janela in JANELAS_POR_CAMPO)
# Mesma coisa, como dict — usado pelo teste de concordância (D-074) uma vez
# por foto candidata; construído aqui, não a cada chamada.
_JANELA_DO_CAMPO = dict(JANELAS_POR_CAMPO)
# Teto para a promoção de "cidade" por cluster do mesmo lado (D-082/Mecanismo
# A) — decisão explícita do dono, NÃO medida contra o acervo como D-025/D-074
# foram. Duas leituras do mesmo lado concordando entre si provam que a
# LEITURA é precisa, não que o alvo ficou parado: `raio_incerteza(delta)` é
# o mesmo com ou sem a segunda leitura (é literalmente o que D-074 testou e
# descartou — "apertar o raio... testado e descartado" — só que ali para o
# raio contínuo, aqui para o grau discreto). Menor que a janela de região
# (2h) de propósito: garante que "cidade" só é promovida quando "região" já
# estava presente no `campos_base` — nunca pula um grau.
JANELA_PROMOCAO_CLUSTER = timedelta(minutes=60)
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
    # "cidade", quando ela só entrou em `campos` por concordância de cluster
    # do MESMO lado (Mecanismo A, D-082) — o Δt sozinho não alcançava a
    # janela de cidade. Vazio no caso comum. Ver `doador_cluster_id` e
    # JANELA_PROMOCAO_CLUSTER: é uma decisão de rótulo do dono, não uma
    # redução medida da incerteza real do alvo — a justificativa
    # (`classification/engine.py`) precisa dizer isso.
    promovido_por_cluster: tuple[str, ...] = ()
    # Id do segundo doador do mesmo lado que corroborou a promoção acima.
    # None quando não houve promoção.
    doador_cluster_id: int | None = None
    # Doadora do OUTRO lado (antes/depois, o que faltar), quando existe —
    # SEMPRE preenchida quando há achado dos dois lados, mesmo sem
    # concordância geométrica testada aqui. `classification/engine.py` usa
    # isto para o Mecanismo B (D-082): duas âncoras que geocodificam para a
    # MESMA cidade nomeada corroboram "cidade" para o alvo, um teste
    # categórico que este módulo — deliberadamente sem geocoding — não pode
    # fazer sozinho.
    doador_outro_lado_id: int | None = None
    delta_outro_lado: timedelta | None = None

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

        Devolve também o índice e o passo — `_proximo_do_mesmo_lado` precisa
        dos dois para continuar a busca de onde esta parou (Mecanismo A).
        """
        j = inicio
        while 0 <= j < len(doadores):
            delta = abs(tempos[j] - alvo)
            if delta > janela:
                return None
            if foto.outra_origem(doadores[j]):
                return delta, doadores[j], j, passo
            j += passo
        return None

    def _proximo_do_mesmo_lado(
        alvo: datetime, foto: FotoRef, a_partir_de: int, passo: int
    ):
        """Segundo doador do MESMO lado, de outra origem que `foto` (mesmo
        critério de `procurar`), continuando a busca de onde o doador
        escolhido parou.

        Só o PRIMEIRO candidato de outra origem conta — não é uma varredura
        à procura de alguém que concorde, o mesmo viés que D-074 já evita do
        lado oposto. Independência exigida só de `foto` (a que está
        herdando), não do doador já escolhido: no acervo real, doadores do
        Apple Fotos importados como par foto+vídeo de uma Live Photo têm
        `camera` idêntico (make/model vazios) entre si — exigir origem
        diferente também do doador excluiria exatamente o par que motivou
        este mecanismo (media_id 7737/35035).
        """
        j = a_partir_de + passo
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
        achados = [
            achado for achado in (
                procurar(alvo, foto, i - 1, -1),   # para trás no tempo
                procurar(alvo, foto, i, +1),       # para frente
            )
            if achado is not None
        ]
        if not achados:
            continue
        delta, doador, idx_doador, passo_doador = min(
            achados, key=lambda c: c[0]
        )
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
        campos_base = campos_confiaveis(delta, incerta)
        if not campos_base:
            continue
        # Mecanismo A (D-082): segundo doador do MESMO lado que corrobora o
        # escolhido pode promover "cidade" mesmo com Δt>10min — dentro do
        # teto de JANELA_PROMOCAO_CLUSTER, decisão do dono, não medida.
        candidato_cluster = _proximo_do_mesmo_lado(
            alvo, foto, idx_doador, passo_doador
        )
        campos_base, promoveu_cluster = _promover_por_cluster(
            campos_base, delta, doador, candidato_cluster, incerta,
        )
        # `outro` carrega índice/passo (para `_proximo_do_mesmo_lado`, que
        # não usa este `outro` — é só para achar `doador`); o teste de
        # concordância só quer (delta, doador).
        outro_par = (outro[0], outro[1]) if outro is not None else None
        campos, concordancia = _confrontar_com_outro_lado(
            campos_base, delta, doador, outro_par, incerta,
        )
        if not campos:
            continue
        cidade_sobreviveu = any(c == "cidade" for c, _ in campos)
        herancas.append(Heranca(
            media_id=foto.media_id, doador_id=doador.media_id,
            lat=doador.lat, lon=doador.lon, delta=delta,
            campos=campos, hora_incerta=incerta,
            concordancia=concordancia,
            doador_concordante_id=(
                outro[1].media_id if outro is not None and concordancia
                else None
            ),
            promovido_por_cluster=(
                ("cidade",) if promoveu_cluster and cidade_sobreviveu else ()
            ),
            doador_cluster_id=(
                candidato_cluster[1].media_id
                if promoveu_cluster and cidade_sobreviveu
                else None
            ),
            doador_outro_lado_id=(
                outro[1].media_id if outro is not None else None
            ),
            delta_outro_lado=outro[0] if outro is not None else None,
        ))
    return herancas


def _confrontar_com_outro_lado(
    campos_base: tuple[tuple[str, float], ...],
    delta: timedelta,
    doador: FotoRef,
    outro: tuple[timedelta, FotoRef] | None,
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
    """
    if outro is None:
        return campos_base, ()
    delta_outro, doador_outro = outro
    if incerta or doador_outro.hora_do_arquivo:
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


def _promover_por_cluster(
    campos_base: tuple[tuple[str, float], ...],
    delta: timedelta,
    doador: FotoRef,
    candidato: tuple[timedelta, FotoRef] | None,
    incerta: bool,
) -> tuple[tuple[tuple[str, float], ...], bool]:
    """Mecanismo A (D-082): promove "cidade" quando um segundo doador do
    MESMO lado, de outra origem que o alvo, concorda geograficamente com o
    doador escolhido — mesmo que `delta` sozinho não alcance a janela de
    cidade (D-025).

    Decisão explícita do dono, NÃO calibrada como D-025/D-074: duas leituras
    que concordam entre si provam que a LEITURA é precisa, não que o alvo
    ficou parado — `raio_incerteza(delta)` é o mesmo com ou sem a segunda
    leitura (D-074 testou e descartou apertar o raio contínuo pelo mesmo
    motivo; aqui é o grau discreto, não o raio, mas o argumento é idêntico).
    A justificativa em `classification/engine.py` precisa dizer isso —
    muda o RÓTULO mostrado, não a incerteza real.

    `JANELA_PROMOCAO_CLUSTER` (60 min) é menor que a janela de região (2h)
    de propósito: quando este teto é respeitado, "região" já está em
    `campos_base` por construção — a promoção nunca pula um grau.
    """
    if candidato is None or incerta:
        return campos_base, False
    if any(campo == "cidade" for campo, _ in campos_base):
        return campos_base, False
    if delta > JANELA_PROMOCAO_CLUSTER:
        return campos_base, False
    delta_candidato, doador_candidato = candidato
    if doador_candidato.hora_do_arquivo:
        return campos_base, False
    distancia = _distancia_m(
        (doador.lat, doador.lon), (doador_candidato.lat, doador_candidato.lon)
    )
    raio_combinado = raio_incerteza(delta) + raio_incerteza(delta_candidato)
    if distancia > raio_combinado:
        return campos_base, False
    janela_cidade = _JANELA_DO_CAMPO["cidade"]
    # Fator de borda da própria janela de cidade — o piso que
    # `campos_confiaveis` já dá a um Δt no limite dela. Nunca mais confiável
    # que um doador único genuinamente dentro da janela.
    fator = _fator_por_delta(janela_cidade, janela_cidade)
    return (*campos_base, ("cidade", fator)), True


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


def _fator_por_delta(delta: timedelta, janela: timedelta) -> float:
    """1.0 até a janela curta, decaindo a 0.6 na borda de `janela`.

    Extraída de `campos_confiaveis` para ser reusada por
    `_promover_por_cluster` (D-082): chamada com `delta == janela` devolve
    sempre o piso de borda (0.6) — não é uma constante nova, é a mesma
    fórmula avaliada no seu próprio limite.
    """
    if delta <= _JANELA_CURTA:
        return 1.0
    resto = (delta - _JANELA_CURTA) / (janela - _JANELA_CURTA)
    return 1.0 - 0.4 * resto


# O piso que QUALQUER campo recebe no limite da própria janela — a fórmula
# de `_fator_por_delta` dá o mesmo valor (0.6) para as três janelas quando
# delta==janela, então basta calcular uma vez. `_promover_por_cluster` usa
# isto para "cidade" (Mecanismo A); `classification/engine.py` importa o
# mesmo valor para o Mecanismo B (D-082) — nenhuma das duas promoções por
# corroboração é mais confiável que um doador único genuinamente dentro da
# janela.
FATOR_BORDA_JANELA = _fator_por_delta(
    _JANELA_DO_CAMPO["cidade"], _JANELA_DO_CAMPO["cidade"]
)


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
        fator = _fator_por_delta(delta, janela)
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
NOTA_DO_RAIO = (
    f"O círculo é o tamanho da dúvida, não um erro de medição: em "
    f"{COBERTURA_MEDIDA * 100:.1f}".replace(".", ",")
    + "% dos pares medidos neste acervo, o lugar verdadeiro cabe dentro dele."
)


def frase_do_raio(delta: timedelta, doadora: str | None = None) -> str:
    """Por que este círculo tem este tamanho, em uma frase para a tela.

    Nasce aqui, e não em TypeScript, pelo mesmo motivo que `raio_incerteza`:
    a frase cita o raio e a velocidade que o produziram. Remontá-la do outro
    lado da API duplicaria as constantes — e constante duplicada é constante
    que diverge no dia em que a calibração for refeita.

    Três formas, porque a fórmula tem três regimes e cada um explica o
    tamanho por um motivo diferente: no piso o círculo é o erro do receptor,
    no teto ele parou de crescer, no meio ele é velocidade × tempo.
    """
    raio = raio_incerteza(delta)
    quem = f"de {doadora}" if doadora else "de outra foto"
    if raio <= RAIO_PISO_M:
        return (
            f"Lugar herdado {quem}, no mesmo instante — o raio de "
            f"{_metros_legiveis(raio)} é só a imprecisão do receptor de GPS "
            "que emprestou a coordenada."
        )
    quando = _tempo_legivel(delta)
    if raio >= RAIO_TETO_M:
        return (
            f"Lugar herdado {quem}, a {quando} de distância — o raio para de "
            f"crescer em {_metros_legiveis(raio)}: neste acervo, quem "
            "fotografa o dia inteiro passa o dia na mesma região."
        )
    return (
        f"Lugar herdado {quem}, a {quando} de distância — a "
        f"{round(VELOCIDADE_PLAUSIVEL_MS * 3.6)} km/h, a velocidade de quem "
        f"anda por uma cidade contando as paradas, isso dá "
        f"{_metros_legiveis(raio)} de dúvida."
    )
