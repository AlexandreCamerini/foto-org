"""Download HTTP com limites explícitos e escrita atômica.

Módulo de infraestrutura para o futuro provider externo *opt-in* de
geocodificação (docs/ROADMAP.md). Hoje **não tem consumidor**: existe
pronto e testado para que, quando o primeiro caso de uso aparecer, ele
não nasça com um `urlopen` cru no meio de um serviço.

Garantias desta versão:

* só `http`/`https` (comparação case-insensitive), verificado antes de
  qualquer atividade de rede e **de novo a cada redirecionamento** —
  `file://` e `ftp://` não são sequer registrados no abridor;
* timeout configurável, aplicado à conexão e às leituras do corpo;
* teto **real** de bytes: o corpo é lido em pedaços e abortado ao passar
  do limite, independentemente do que o `Content-Length` diga (ele pode
  faltar, no caso de resposta *chunked* ou delimitada por fecho de
  conexão, ou simplesmente mentir);
* quando há `Content-Length`, o corpo recebido tem de bater com ele: um
  servidor que declara 100 KB e fecha a conexão nos primeiros 500 bytes
  **não** produz um arquivo de 500 bytes tratado como completo
  (`HTTPResponse.read` não levanta erro nesse caso, por compatibilidade —
  a conferência é nossa);
* escrita atômica: o corpo vai para um temporário 0600 no mesmo diretório
  do destino e só vira o arquivo final por `link`/`replace` depois do
  download inteiro; qualquer erro remove o parcial;
* nunca sobrescreve destino existente por padrão (invariante 3 do
  CLAUDE.md), e a promoção sem sobrescrita usa `os.link`, que é atômico —
  não há janela entre "checar" e "renomear".

O que **não** está aqui, por decisão consciente: (a) proteção contra SSRF
e DNS rebinding (fixar o IP resolvido, recusar faixas privadas/loopback);
(b) orçamento total de tempo — `timeout` vale por operação de socket, não
para o download inteiro, então um servidor que goteje 1 byte a cada 29 s
mantém a transferência viva por horas, limitada só pelo teto de tamanho.
Nada disso se justifica enquanto não houver caso de uso com URL de origem
não confiável — todo consumidor previsto usa endpoint fixo escolhido pelo
usuário. Quando surgir URL vinda de dado de terceiro, ou consumidor que
rode sem alguém olhando, os dois pontos precisam ser revistos antes de
ligar o consumidor.

Biblioteca padrão de propósito: `urllib.request` entrega tudo o que o
escopo pede (leitura incremental, timeout, redirecionamento controlável)
sem acrescentar `httpx` como dependência formal de um módulo que ainda
não tem quem o chame.
"""

from __future__ import annotations

import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

ESQUEMAS_PERMITIDOS = frozenset({"http", "https"})

TIMEOUT_PADRAO = 30.0
"""Segundos. Vale para conectar e para cada leitura do corpo."""

TAMANHO_MAXIMO_PADRAO = 32 * 1024 * 1024
"""32 MiB — folgado para um dataset offline pequeno, apertado o bastante
para que uma resposta inesperadamente grande falhe em vez de encher o
disco."""

_PEDACO = 64 * 1024
_USER_AGENT = "FotoOrganizer/0.1 (local)"


class ErroDeDownload(Exception):
    """Base de todas as falhas de `baixar_arquivo`."""


class EsquemaNaoPermitido(ErroDeDownload, ValueError):
    """URL (ou destino de redirecionamento) fora de http/https."""


class UrlInvalida(ErroDeDownload, ValueError):
    """URL sintaticamente inutilizável (sem host, por exemplo)."""


class TempoEsgotado(ErroDeDownload, TimeoutError):
    """Estourou o timeout ao conectar ou ao ler o corpo."""


class TamanhoExcedido(ErroDeDownload):
    """O corpo passou (ou declarou que passaria) do teto de bytes."""

    def __init__(self, mensagem: str, *, limite: int, lidos: int | None = None) -> None:
        super().__init__(mensagem)
        self.limite = limite
        self.lidos = lidos


class ErroDeRede(ErroDeDownload):
    """Falha de DNS, conexão, TLS ou corpo interrompido."""


class ErroHTTP(ErroDeRede):
    """Status de erro do servidor (4xx/5xx)."""

    def __init__(self, mensagem: str, *, status: int) -> None:
        super().__init__(mensagem)
        self.status = status


class CorpoNaoConfere(ErroDeRede):
    """O corpo recebido não bate com o `Content-Length` declarado.

    Cobre as duas direções, porque as duas produzem o mesmo estrago —
    um arquivo no disco que não é o recurso que o servidor tem:

    * **faltando** bytes: o servidor declarou 100 KB e fechou a conexão
      nos primeiros 500. `http.client` não levanta erro nesse caso (o
      próprio CPython documenta a escolha, para não quebrar
      compatibilidade), então a conferência tem de ser nossa;
    * **sobrando** bytes: o servidor declarou 10 e mandou 200 KB. O
      `urllib` corta a leitura nos 10 declarados, e do ponto de vista do
      protocolo o corpo *é* de 10 bytes — mas o arquivo resultante é um
      pedaço mudo do recurso. Detectado por espiada no buffer antes da
      última leitura (melhor esforço, ver `_excedente_visivel`).
    """

    def __init__(self, mensagem: str, *, declarado: int, lidos: int) -> None:
        super().__init__(mensagem)
        self.declarado = declarado
        self.lidos = lidos


class ErroDeArquivo(ErroDeDownload, OSError):
    """Falha de filesystem do nosso lado: não deu para criar o temporário,
    gravar nele ou promovê-lo ao destino.

    Existe para que o contrato "tudo que sai daqui é `ErroDeDownload`"
    valha também quando o destino está num volume que não faz o que
    precisamos — `os.link` devolvendo `EOPNOTSUPP` em exFAT/SMB é o caso
    concreto, e o app já lida com volumes externos (`security/volumes.py`).
    """


class DestinoJaExiste(ErroDeDownload, FileExistsError):
    """O arquivo de destino já existe e `sobrescrever` é falso."""


class _RedirecionamentoRestrito(urllib.request.HTTPRedirectHandler):
    """Revalida o esquema a cada salto: um 302 para `file:///etc/passwd`
    transformaria o downloader em leitor de arquivo local.

    A checagem tem de vir *antes* da do `HTTPRedirectHandler`, que aceita
    `ftp` e reporta a recusa como um `HTTPError` genérico — queremos a
    allow-list deste módulo e uma exceção que diga o que houve.
    """

    def http_error_302(self, req, fp, code, msg, headers):  # noqa: ANN001
        bruto = headers.get("location") or headers.get("uri")
        if bruto is not None:
            esquema = urlsplit(bruto.strip()).scheme.lower()
            # esquema vazio = Location relativo, resolvido contra a URL
            # atual (já validada) e conferido em `redirect_request`.
            if esquema and esquema not in ESQUEMAS_PERMITIDOS:
                fp.close()
                raise EsquemaNaoPermitido(
                    f"redirecionamento: esquema {esquema!r} não permitido "
                    f"— {bruto.strip()!r}"
                )
        return super().http_error_302(req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = (
        http_error_302
    )

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        _validar_url(newurl, contexto="redirecionamento")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validar_url(url: str, *, contexto: str = "url") -> str:
    partes = urlsplit(url)
    esquema = partes.scheme.lower()
    if esquema not in ESQUEMAS_PERMITIDOS:
        raise EsquemaNaoPermitido(
            f"{contexto}: esquema {partes.scheme!r} não permitido "
            f"({', '.join(sorted(ESQUEMAS_PERMITIDOS))} apenas) — {url!r}"
        )
    if not partes.netloc:
        raise UrlInvalida(f"{contexto}: sem host — {url!r}")
    return url


def _abridor() -> urllib.request.OpenerDirector:
    """Abridor com apenas os handlers necessários.

    Construído à mão em vez de `build_opener()` porque o padrão registra
    `FileHandler`, `FTPHandler` e `DataHandler` — quero que esquemas fora
    da allow-list não tenham sequer implementação disponível. `ProxyHandler({})`
    desliga proxies do ambiente: para um app local-first, o tráfego não deve
    desviar para um host que o usuário não escolheu por causa de um
    `HTTP_PROXY` esquecido no shell.
    """
    abridor = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
        _RedirecionamentoRestrito(),
    ):
        abridor.add_handler(handler)
    return abridor


def _traduzir_falha(erro: Exception, url: str) -> ErroDeDownload:
    if isinstance(erro, HTTPError):
        return ErroHTTP(f"{url}: HTTP {erro.code} {erro.reason}", status=erro.code)
    if isinstance(erro, TimeoutError):
        return TempoEsgotado(f"{url}: tempo esgotado")
    if isinstance(erro, URLError):
        if isinstance(erro.reason, TimeoutError):
            return TempoEsgotado(f"{url}: tempo esgotado")
        return ErroDeRede(f"{url}: {erro.reason}")
    return ErroDeRede(f"{url}: {erro}")


def _tamanho_declarado(resposta, limite: int, url: str) -> int | None:
    """Lê o `Content-Length` e falha rápido quando o próprio servidor
    anuncia um corpo grande demais — poupa a transferência. Não substitui
    o teto real.

    Devolve o valor declarado (ou `None` quando não há header utilizável)
    para que o fim do download possa conferir o que chegou contra o que
    foi prometido.
    """
    bruto = resposta.headers.get("Content-Length")
    if bruto is None:
        return None
    try:
        declarado = int(bruto)
    except ValueError:
        return None  # header inútil: o teto real resolve
    if declarado < 0:
        return None  # idem: valor impossível não vira contrato
    if declarado > limite:
        raise TamanhoExcedido(
            f"{url}: Content-Length {declarado} passa do limite de {limite} bytes",
            limite=limite,
        )
    return declarado


def _excedente_visivel(fonte, restante: int) -> bool:
    """O servidor mandou mais bytes do que o `Content-Length` declarou?

    Chamado só antes da leitura que esgota o corpo — depois dela é tarde:
    `HTTPResponse.read` fecha o `fp` no mesmo instante em que zera o
    contador, e aí não sobra nada para inspecionar.

    `peek` devolve o que já está no buffer (fazendo no máximo uma leitura
    crua) sem consumir. Se aparecer mais do que os `restante` bytes que
    ainda cabem no corpo declarado, os bytes extras são lixo que o
    servidor emendou depois do fim anunciado. É **melhor esforço**: pode
    não enxergar o excedente se o buffer estiver justo, mas nunca acusa
    falso positivo — o `urllib` manda `Connection: close`, então não há
    resposta seguinte na conexão para confundir com sobra.
    """
    espiar = getattr(getattr(fonte, "fp", None), "peek", None)
    if espiar is None:
        return False
    try:
        return len(espiar(restante + 1)) > restante
    except (ValueError, OSError):  # fp fechado ou socket já morto
        return False


def _promover(temporario: str, destino: Path, sobrescrever: bool) -> None:
    if sobrescrever:
        try:
            os.replace(temporario, destino)
        except OSError as erro:
            raise ErroDeArquivo(f"não consegui promover {destino}: {erro}") from erro
        return
    # `link` falha com FileExistsError se o destino surgiu enquanto
    # baixávamos — é a checagem e a promoção no mesmo passo atômico.
    try:
        os.link(temporario, destino)
    except FileExistsError as erro:
        raise DestinoJaExiste(f"destino já existe: {destino}") from erro
    except OSError as erro:
        # `link` não é universal: exFAT/SMB devolvem EOPNOTSUPP. Sai como
        # erro do módulo, não como OSError cru no meio do chamador.
        raise ErroDeArquivo(f"não consegui promover {destino}: {erro}") from erro
    finally:
        # o `link` deixou o conteúdo com dois nomes; o temporário sai nos
        # dois desfechos, e uma falha de limpeza não vira exceção crua.
        _remover_silencioso(temporario)


def baixar_arquivo(
    url: str,
    destino: Path | str,
    *,
    timeout: float = TIMEOUT_PADRAO,
    tamanho_maximo_bytes: int = TAMANHO_MAXIMO_PADRAO,
    sobrescrever: bool = False,
    cabecalhos: dict[str, str] | None = None,
) -> int:
    """Baixa `url` para `destino` e devolve quantos bytes foram gravados.

    O destino só passa a existir se o download terminou inteiro e dentro
    do limite; em qualquer falha nada é deixado para trás. Permissão do
    arquivo final: 0600.

    Levanta `EsquemaNaoPermitido`, `UrlInvalida`, `TempoEsgotado`,
    `TamanhoExcedido`, `ErroHTTP`, `ErroDeRede`, `CorpoNaoConfere`,
    `ErroDeArquivo` ou `DestinoJaExiste` — todas subclasses de
    `ErroDeDownload`. Nenhum `OSError` de filesystem escapa cru.
    """
    if tamanho_maximo_bytes <= 0:
        raise ValueError("tamanho_maximo_bytes precisa ser positivo")
    if timeout <= 0:
        raise ValueError("timeout precisa ser positivo")

    _validar_url(url)
    destino = Path(destino).expanduser()
    if destino.is_dir():
        raise ErroDeDownload(f"destino é um diretório: {destino}")
    if destino.exists() and not sobrescrever:
        raise DestinoJaExiste(f"destino já existe: {destino}")
    destino.parent.mkdir(parents=True, exist_ok=True)

    requisicao = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, **(cabecalhos or {})},
        method="GET",
    )
    try:
        resposta = _abridor().open(requisicao, timeout=timeout)
    except ErroDeDownload:
        raise  # esquema barrado no redirecionamento, já traduzido
    except (HTTPError, URLError, TimeoutError, OSError) as erro:
        raise _traduzir_falha(erro, url) from erro

    with resposta:
        declarado = _tamanho_declarado(resposta, tamanho_maximo_bytes, url)
        gravados = _escrever_atomico(
            resposta,
            destino,
            tamanho_maximo_bytes,
            sobrescrever,
            url,
            declarado=declarado,
        )
    log.debug("baixado %s (%d bytes) → %s", url, gravados, destino)
    return gravados


def _escrever_atomico(
    fonte,
    destino: Path,
    limite: int,
    sobrescrever: bool,
    url: str,
    *,
    declarado: int | None = None,
) -> int:
    # mkstemp já cria com 0600 e no mesmo diretório do destino, o que
    # mantém o rename final dentro do mesmo filesystem (atômico).
    try:
        descritor, temporario = tempfile.mkstemp(
            dir=destino.parent, prefix=f".{destino.name}.", suffix=".part"
        )
    except OSError as erro:
        # diretório sem escrita, disco cheio, volume desmontado…
        raise ErroDeArquivo(
            f"não consegui criar o temporário em {destino.parent}: {erro}"
        ) from erro
    total = 0
    try:
        with os.fdopen(descritor, "wb") as arquivo:
            while True:
                if declarado is not None:
                    restante = declarado - total
                    if 0 < restante <= _PEDACO and _excedente_visivel(fonte, restante):
                        raise CorpoNaoConfere(
                            f"{url}: servidor mandou mais bytes do que o "
                            f"Content-Length de {declarado} declarou",
                            declarado=declarado,
                            lidos=total,
                        )
                try:
                    pedaco = fonte.read(_PEDACO)
                except (URLError, TimeoutError, OSError, HTTPError) as erro:
                    raise _traduzir_falha(erro, url) from erro
                except Exception as erro:  # http.client.IncompleteRead & cia.
                    raise ErroDeRede(f"{url}: corpo interrompido — {erro}") from erro
                if not pedaco:
                    break
                total += len(pedaco)
                if total > limite:
                    raise TamanhoExcedido(
                        f"{url}: corpo passou do limite de {limite} bytes",
                        limite=limite,
                        lidos=total,
                    )
                try:
                    arquivo.write(pedaco)
                except OSError as erro:
                    raise ErroDeArquivo(
                        f"não consegui gravar {temporario}: {erro}"
                    ) from erro
            # Fim de corpo não é prova de corpo inteiro: `read` devolve b""
            # tanto no fim honesto quanto na conexão cortada no meio.
            if declarado is not None and total != declarado:
                raise CorpoNaoConfere(
                    f"{url}: recebi {total} bytes de um Content-Length de "
                    f"{declarado} — corpo incompleto",
                    declarado=declarado,
                    lidos=total,
                )
            try:
                arquivo.flush()
                os.fsync(arquivo.fileno())
            except OSError as erro:
                raise ErroDeArquivo(f"não consegui gravar {temporario}: {erro}") from erro
        try:
            os.chmod(temporario, 0o600)
        except OSError as erro:
            raise ErroDeArquivo(f"não consegui ajustar {temporario}: {erro}") from erro
        _promover(temporario, destino, sobrescrever)
    except BaseException:
        _remover_silencioso(temporario)
        raise
    return total


def _remover_silencioso(caminho: str) -> None:
    try:
        os.unlink(caminho)
    except FileNotFoundError:
        pass
    except OSError:  # pragma: no cover - erro de limpeza não mascara o original
        log.warning("não consegui remover o parcial %s", caminho, exc_info=True)
