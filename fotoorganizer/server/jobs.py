"""Trabalhos em background do servidor local (scan, importação).

Um trabalho por vez — a mesma disciplina da UI nativa. O estado é um
snapshot atômico consultável por polling ou SSE; o frontend invalida as
queries quando o status muda para concluído/erro.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import Settings
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.scanner import CatalogScanner, ScanControl
from fotoorganizer.sources import (
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
            self._factory, PurePythonExtractor(), self._settings.scanner,
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
            from fotoorganizer.geolocation import LocationResolver
            from fotoorganizer.geolocation.offline import OfflineGeocoder

            engine = SuggestionEngine(
                self._factory,
                LocationResolver(OfflineGeocoder()),
                advisor=self._advisor(),
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
            self._factory, PurePythonExtractor(), self._settings.scanner,
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
            # Permissão do Fotos, pasta inválida etc. — mensagem clara.
            self._atualizar(status="erro", mensagem=str(exc))
