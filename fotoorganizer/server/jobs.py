"""Trabalhos em background do servidor local (scan, importação, execução).

Um trabalho por vez — a mesma disciplina da UI nativa. O estado é um
snapshot atômico consultável por polling ou SSE; o frontend invalida as
queries quando o status muda para concluído/erro.

A execução de plano é o único trabalho que escreve fora do catálogo. Ela
mantém seu próprio controle de cancelamento (`ExecutionControl`), porque
parar uma cópia no meio exige remover o parcial — não basta o
`ScanControl` cooperativo dos demais.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import Settings
from fotoorganizer.metadata import criar_extrator
from fotoorganizer.operations import (
    DryRunObrigatorio,
    ExecutionControl,
    OperationExecutor,
)
from fotoorganizer.scanner import CatalogScanner, ScanControl
from fotoorganizer.sources import (
    ApplePhotosError,
    ApplePhotosProvider,
    ExternalCatalogImporter,
    GoogleTakeoutProvider,
)
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)


class JobManager:
    def __init__(
        self, settings: Settings, session_factory: sessionmaker[Session]
    ) -> None:
        self._settings = settings
        self._factory = session_factory
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._control = ScanControl()
        self._exec_control: ExecutionControl | None = None
        self._estado: dict = {"status": "nenhum"}

    # -- consulta -----------------------------------------------------------
    def estado(self) -> dict:
        with self._lock:
            return dict(self._estado)

    def ocupado(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancelar(self) -> None:
        self._control.continuar()
        self._control.cancelar()
        if self._exec_control is not None:
            self._exec_control.cancelar()

    def pausar(self) -> bool:
        """Pausa o scan em andamento. Só existe pausa cooperativa para
        scan (`ScanControl`) — importação e execução de plano não a
        oferecem. Devolve False sem efeito colateral se não houver o que
        pausar, para a rota responder 409 em vez de estourar."""
        estado = self.estado()
        if (not self.ocupado() or estado.get("tipo") != "scan"
                or estado.get("status") != "rodando"):
            return False
        self._control.pausar()
        self._atualizar(status="pausado")
        return True

    def continuar(self) -> bool:
        estado = self.estado()
        if (not self.ocupado() or estado.get("tipo") != "scan"
                or estado.get("status") != "pausado"):
            return False
        self._control.continuar()
        self._atualizar(status="rodando")
        return True

    # -- partida ---------------------------------------------------------------
    def iniciar_scan(self, caminho: Path) -> bool:
        return self._iniciar("scan", str(caminho), self._rodar_scan, caminho)

    def iniciar_import_apple(self) -> bool:
        provider = ApplePhotosProvider()
        return self._iniciar(
            "import", provider.apelido, self._rodar_import, provider
        )

    def iniciar_import_takeout(self, caminho: Path) -> bool:
        provider = GoogleTakeoutProvider(caminho)
        return self._iniciar(
            "import", provider.apelido, self._rodar_import, provider
        )

    def iniciar_sugestoes(self) -> bool:
        return self._iniciar(
            "sugestoes", "catálogo inteiro", self._rodar_sugestoes
        )

    def iniciar_duplicatas(self) -> bool:
        return self._iniciar(
            "duplicatas", "catálogo inteiro", self._rodar_duplicatas
        )

    def iniciar_reconciliacao(self) -> bool:
        """Uma passada da varredura de alcance (fase 12, item B): confere se
        arquivos catalogados ainda existem, sem reler metadado nem hash.
        Auto-limitada por tempo/percentual — o job termina sozinho dentro
        do orçamento, não varre o catálogo inteiro de uma vez."""
        return self._iniciar(
            "reconciliacao", "catálogo inteiro", self._rodar_reconciliacao
        )

    def iniciar_execucao(self, plan_id: int) -> bool:
        """Executa um plano aprovado. O controle nasce aqui, na thread do
        pedido, para que um cancelamento imediato não se perca."""
        if self.ocupado():
            return False
        controle = ExecutionControl()
        self._exec_control = controle
        return self._iniciar(
            "operacao", f"plano {plan_id}", self._rodar_execucao,
            plan_id, controle,
        )

    def _iniciar(self, tipo: str, alvo: str, funcao, *args) -> bool:
        if self.ocupado():
            return False
        self._control = ScanControl()
        with self._lock:
            self._estado = {
                "status": "rodando", "tipo": tipo, "alvo": alvo,
                "vistos": 0, "processados": 0, "pulados": 0, "erros": 0,
                "arquivos_por_segundo": 0.0,
            }
        self._thread = threading.Thread(
            target=funcao, args=args, daemon=True, name=f"job-{tipo}"
        )
        self._thread.start()
        return True

    def _atualizar(self, **campos) -> None:
        with self._lock:
            self._estado.update(campos)

    # -- execução ---------------------------------------------------------------
    def _rodar_scan(self, caminho: Path) -> None:
        scanner = CatalogScanner(
            self._factory, criar_extrator(), self._settings.scanner,
            thumb_cache=ThumbnailCache(self._settings.cache_dir),
        )

        def progresso(metrics, _caminho: str) -> None:
            self._atualizar(
                vistos=metrics.vistos, processados=metrics.indexados,
                pulados=metrics.pulados, erros=metrics.erros,
                arquivos_por_segundo=round(metrics.arquivos_por_segundo, 1),
            )

        try:
            scan, metrics = scanner.scan_source(
                caminho, progress=progresso, control=self._control
            )
            self._atualizar(
                status=scan.status.value, vistos=metrics.vistos,
                processados=metrics.indexados, pulados=metrics.pulados,
                erros=metrics.erros,
            )
        except Exception as exc:
            log.exception("job scan falhou")
            self._atualizar(status="erro", mensagem=str(exc))

    def _rodar_sugestoes(self) -> None:
        try:
            from fotoorganizer.classification import SuggestionEngine
            from fotoorganizer.classification.templates import TEMPLATE_PADRAO
            from fotoorganizer.geolocation import LocationResolver
            from fotoorganizer.geolocation.offline import OfflineGeocoder
            from fotoorganizer.repositories.lexico import LexicoRepository
            from fotoorganizer.repositories.settings import SettingsRepository

            # Sem preferência salva, o comportamento é idêntico a antes desta
            # fase: TEMPLATE_PADRAO.
            template = SettingsRepository(self._factory).obter_template(
                TEMPLATE_PADRAO
            )
            # O que cada nome significa, lido do CACHE — nada sai da máquina
            # aqui. A classificação em si é ação separada e explícita
            # (`scripts/classificar_nomes.py`). Léxico vazio = cascata
            # decide como sempre decidiu.
            lexico = LexicoRepository(self._factory).conhecidos()
            engine = SuggestionEngine(
                self._factory,
                LocationResolver(OfflineGeocoder()),
                template=template,
                advisor=self._advisor(),
                lexico=lexico,
            )
            resultado = engine.gerar()
            self._atualizar(
                status="concluido",
                processados=resultado.get("sugestoes", 0),
                resultado=resultado,
            )
        except Exception as exc:
            log.exception("job sugestões falhou")
            self._atualizar(status="erro", mensagem=str(exc))

    def _rodar_execucao(self, plan_id: int, controle: ExecutionControl) -> None:
        executor = OperationExecutor(self._factory)

        def progresso(n: int, total: int, origem: str) -> None:
            self._atualizar(vistos=total, processados=n,
                            arquivo=Path(origem).name)

        try:
            stats = executor.executar(
                plan_id, progress=progresso, control=controle
            )
            self._atualizar(
                status="cancelado" if stats["cancelado"] else "concluido",
                processados=stats["copiados"], pulados=stats["pulados"],
                erros=stats["erros"], resultado=stats,
            )
        except DryRunObrigatorio as exc:
            self._atualizar(status="erro", mensagem=str(exc))
        except Exception as exc:
            log.exception("job execução falhou")
            self._atualizar(status="erro", mensagem=str(exc))

    def _rodar_duplicatas(self) -> None:
        try:
            from fotoorganizer.duplicates import DuplicateDetector

            detector = DuplicateDetector(
                self._factory, ThumbnailCache(self._settings.cache_dir)
            )
            stats = detector.detectar(
                progress=lambda etapa: self._atualizar(etapa=etapa)
            )
            self._atualizar(
                status="concluido",
                processados=sum(
                    v for k, v in stats.items() if k != "preservados"
                ),
                resultado=stats,
            )
        except Exception as exc:
            log.exception("job duplicatas falhou")
            self._atualizar(status="erro", mensagem=str(exc))

    def _rodar_reconciliacao(self) -> None:
        try:
            from fotoorganizer.scanner.reconciliacao import reconciliar

            resultado = reconciliar(self._factory)
            self._atualizar(
                status="concluido",
                processados=resultado.verificados,
                resultado={
                    "verificados": resultado.verificados,
                    "marcados_offline": resultado.marcados_offline,
                    "marcados_online": resultado.marcados_online,
                    "ciclo_concluido": resultado.ciclo_concluido,
                },
            )
        except Exception as exc:
            log.exception("job reconciliação falhou")
            self._atualizar(status="erro", mensagem=str(exc))

    def _advisor(self):
        """Advisor LLM só com opt-in explícito — sem ele, 100% local."""
        if not self._settings.privacidade.servicos_externos:
            return None
        try:
            from fotoorganizer.classification.advisor import ClaudeAdvisor

            return ClaudeAdvisor()
        except Exception as exc:
            log.warning("advisor indisponível (%s); seguindo local", exc)
            return None

    def _rodar_import(self, provider) -> None:
        importer = ExternalCatalogImporter(
            self._factory, criar_extrator(), self._settings.scanner,
            thumb_cache=ThumbnailCache(self._settings.cache_dir),
        )

        def progresso(metrics, _caminho: str) -> None:
            self._atualizar(
                vistos=metrics.vistos, processados=metrics.importados,
                pulados=metrics.pulados, erros=metrics.erros,
            )

        try:
            metrics = importer.importar(provider, progress=progresso)
            self._atualizar(
                status="concluido", vistos=metrics.vistos,
                processados=metrics.importados, pulados=metrics.pulados,
                erros=metrics.erros,
            )
        except Exception as exc:
            self._atualizar(
                status="erro", mensagem=_mensagem_falha_import(provider, exc)
            )


def _erro_de_permissao(exc: BaseException | None) -> bool:
    """PermissionError em qualquer ponto da cadeia de causas (`__cause__`/
    `__context__`) — sinal robusto de falta de permissão do SO (EACCES/
    EPERM viram PermissionError automaticamente ao serem levantados),
    melhor que caçar substring de mensagem específica de uma lib."""
    vistos: set[int] = set()
    while exc is not None and id(exc) not in vistos:
        vistos.add(id(exc))
        if isinstance(exc, PermissionError):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def _mensagem_falha_import(provider, exc: Exception) -> str:
    """`ApplePhotosError` já vem com a orientação completa (inclusive o
    app responsável pelo TCC) — repeti-la aqui jogaria fora esse detalhe.
    O buraco é outra classe de erro (ex.: PermissionError levantado
    durante a iteração da biblioteca, não na abertura dela) chegando cru
    até o usuário sem dizer o que fazer."""
    if isinstance(exc, ApplePhotosError):
        return str(exc)
    if isinstance(provider, ApplePhotosProvider) and _erro_de_permissao(exc):
        return (
            f"{exc} — provável falta de Acesso Total ao Disco para ler a "
            "biblioteca do Apple Fotos. Ajustes → Privacidade e Segurança → "
            "Acesso Total ao Disco, marque o app responsável e importe de "
            "novo."
        )
    return str(exc)
