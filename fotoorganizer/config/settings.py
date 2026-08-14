"""Configuração local em TOML.

Leitura via tomllib (stdlib). O arquivo é opcional: na ausência dele valem
os defaults abaixo. Chaves desconhecidas são ignoradas com aviso — nunca
derrubam o app por causa de config.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from fotoorganizer.config import paths

log = logging.getLogger(__name__)


class _Unset:
    """Tipo da sentinela `UNSET` — só existe para dar um repr legível."""

    def __repr__(self) -> str:  # pragma: no cover - só ajuda debug/logs
        return "UNSET"


# Sentinela distinta de `None`/zero-value: representa "esta fonte de config
# não tocou este campo", nunca "o usuário passou um valor vazio/zero/false
# de propósito". Ver `aplicar_overrides()` — é o que evita a ambiguidade que
# o PhotoPrism resolve via reflection sobre zero-values (Go); em Python, com
# argparse, checar identidade contra `UNSET` é suficiente e explícito.
UNSET = _Unset()

CONFIG_TEMPLATE = """\
# Configuração do Foto Organizer. Todas as chaves são opcionais.

[geral]
# data_dir = "~/Library/Application Support/FotoOrganizer"
# cache_dir = "~/Library/Caches/FotoOrganizer"

[scanner]
# workers = 4
# incluir_ocultos = false
# seguir_symlinks = false

[privacidade]
# servicos_externos = false
"""


@dataclass(frozen=True)
class ScannerSettings:
    workers: int = 4
    incluir_ocultos: bool = False
    seguir_symlinks: bool = False


@dataclass(frozen=True)
class PrivacySettings:
    # Nenhum dado sai da máquina enquanto isto for False (invariante 4).
    servicos_externos: bool = False
    # Reconhecimento facial: opcional e desativado por padrão (invariante 6).
    reconhecimento_facial: bool = False


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=paths.default_data_dir)
    cache_dir: Path = field(default_factory=paths.default_cache_dir)
    scanner: ScannerSettings = field(default_factory=ScannerSettings)
    privacidade: PrivacySettings = field(default_factory=PrivacySettings)
    # Proveniência, não valor: quais campos de `[geral]` uma camada anterior
    # definiu *explicitamente* (hoje só o TOML preenche isto). É o que
    # permite a `aplicar_overrides()` saber que um valor derivado de outro
    # flag (`cache_dir` deduzido de `--data-dir`) não pode passar por cima
    # de um `cache_dir` que o usuário escreveu no TOML — sem inferir isso
    # do valor, pela mesma razão que `UNSET` existe. Fica fora da
    # comparação: dois `Settings` com os mesmos valores são a mesma config,
    # tenham vindo de onde tiverem vindo.
    campos_explicitos: frozenset[str] = field(
        default=frozenset(), compare=False, repr=False
    )

    @property
    def db_path(self) -> Path:
        return paths.default_db_path(self.data_dir)

    @property
    def log_dir(self) -> Path:
        return paths.default_log_dir(self.data_dir)

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)


# Seções reconhecidas no TOML e no dict de overrides. Uma seção fora desta
# lista (typo como `[scaner]`, ou uma seção que ainda não existe como
# `[thumbnails]`) é ignorada com aviso, nunca em silêncio — mesmo tratamento
# que `_apply_section()` já dava a chave desconhecida *dentro* de uma seção.
_SECOES = ("geral", "scanner", "privacidade")
_GERAL_CAMINHOS = ("data_dir", "cache_dir")


def _avisar_secoes_desconhecidas(
    data: dict, origem: str, permitidas: tuple[str, ...] = _SECOES
) -> None:
    for secao in data:
        if secao not in permitidas:
            log.warning(
                "config: seção desconhecida ignorada (%s): [%s]", origem, secao
            )


def _aplicar_geral(settings, geral: dict, *, explicito: bool = True):
    """Aplica `[geral]` (só caminhos, hoje) e registra a proveniência.

    Com `explicito=False` a camada é *derivada* (valor deduzido de outro
    flag, não escrito pelo usuário): ela só preenche campo que nenhuma
    camada anterior tenha definido de propósito.
    """
    campos = set(settings.campos_explicitos)
    for chave, valor in geral.items():
        if chave not in _GERAL_CAMINHOS:
            log.warning("config: chave desconhecida ignorada: [geral] %s", chave)
            continue
        if not explicito and chave in settings.campos_explicitos:
            continue
        settings = replace(settings, **{chave: Path(valor).expanduser()})
        if explicito:
            campos.add(chave)
    return replace(settings, campos_explicitos=frozenset(campos))


def _apply_section(instance, data: dict, section: str):
    known = {f.name for f in fields(instance)}
    updates = {}
    for key, value in data.items():
        if key not in known:
            log.warning("config: chave desconhecida ignorada: [%s] %s", section, key)
            continue
        updates[key] = value
    return replace(instance, **updates)


def load_settings(config_file: Path | None = None) -> Settings:
    """Carrega o TOML se existir; caso contrário retorna os defaults.

    Esta função só resolve as duas primeiras camadas de config — defaults da
    dataclass e arquivo TOML. A terceira camada (CLI/env explícitos na
    invocação atual) é aplicada depois, por quem chama, via
    `aplicar_overrides()`. Ordem de precedência final, deliberada:

        defaults (dataclass) < arquivo TOML < CLI/env explícito

    Um flag de CLI ou env var reconhecida, setados *nesta* invocação, sempre
    vencem o TOML; o TOML vence os defaults; um campo que nenhuma das três
    fontes tocou fica no default. Isto difere do PhotoPrism (que resolve
    "não veio de lugar nenhum" vs. "veio como zero-value" via reflection)
    porque aqui a ausência é modelada explicitamente pela sentinela `UNSET`
    em vez de inferida do valor.
    """
    config_file = config_file or paths.default_config_file()
    settings = Settings()
    if not config_file.is_file():
        return settings

    try:
        with open(config_file, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.error("config: erro lendo %s (%s); usando defaults", config_file, exc)
        return settings

    _avisar_secoes_desconhecidas(data, str(config_file))
    settings = _aplicar_geral(settings, data.get("geral", {}))

    settings = replace(
        settings,
        scanner=_apply_section(settings.scanner, data.get("scanner", {}), "scanner"),
        privacidade=_apply_section(
            settings.privacidade, data.get("privacidade", {}), "privacidade"
        ),
    )
    return settings


def aplicar_overrides(
    settings: Settings, overrides: dict, derivados: dict | None = None
) -> Settings:
    """Terceira camada de precedência: CLI/env explícitos nesta invocação.

    `overrides` já vem *resolvido* (sem `UNSET`) — quem monta o dict (hoje,
    `fotoorganizer.cli`) é responsável por filtrar os campos que o usuário
    não tocou nesta chamada, usando a sentinela `UNSET` para distinguir isso
    de um valor vazio/zero/false passado de propósito (ex.: `--workers 0`
    ou `--no-seguir-symlinks`). Esta função só sabe aplicar o que recebeu.

    `derivados` tem o mesmo formato, mas é uma camada de precedência
    *abaixo* do TOML: valores que a CLI deduz de outro flag em vez de
    receber do usuário — hoje só o `cache_dir` deduzido de `--data-dir`.
    Um derivado nunca passa por cima de um campo que o TOML definiu
    explicitamente (`Settings.campos_explicitos`); a ordem completa é

        defaults < derivados de outro flag < TOML < CLI/env explícito

    O formato espelha o das seções do TOML, para reusar `_apply_section()`:
    `{"geral": {"data_dir": ..., "cache_dir": ...},
      "scanner": {"workers": ..., ...}, "privacidade": {...}}`.
    Seções ou chaves ausentes do dict simplesmente não sobrescrevem nada;
    seção ou chave desconhecida é ignorada com aviso.
    """
    if derivados:
        # Só `[geral]` tem valor derivado hoje; qualquer outra seção aqui é
        # engano de quem chamou e merece o mesmo aviso.
        _avisar_secoes_desconhecidas(derivados, "derivados de CLI", ("geral",))
        settings = _aplicar_geral(
            settings, derivados.get("geral", {}), explicito=False
        )
    if not overrides:
        return settings

    _avisar_secoes_desconhecidas(overrides, "overrides de CLI/env")
    settings = _aplicar_geral(settings, overrides.get("geral", {}))

    settings = replace(
        settings,
        scanner=_apply_section(
            settings.scanner, overrides.get("scanner", {}), "scanner"
        ),
        privacidade=_apply_section(
            settings.privacidade, overrides.get("privacidade", {}), "privacidade"
        ),
    )
    return settings


def write_config_template(config_file: Path) -> None:
    """Grava um template comentado, sem sobrescrever config existente."""
    if config_file.exists():
        return
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(CONFIG_TEMPLATE, encoding="utf-8")
