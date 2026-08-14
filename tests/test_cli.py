"""CLI de importação — a via que funciona quando o Acesso Total ao Disco
foi concedido ao terminal do usuário, e não ao app que abre o servidor."""

from pathlib import Path

import pytest

from fotoorganizer.cli import main
from tests.fixtures import make_jpeg


def _takeout_sintetico(raiz: Path) -> Path:
    """Estrutura mínima do Takeout: mídia + sidecar com data e GPS."""
    import json

    pasta = raiz / "Takeout" / "Google Fotos" / "Photos from 2019"
    make_jpeg(pasta / "IMG_001.jpg", seed=1, data_exif=None)
    (pasta / "IMG_001.jpg.json").write_text(json.dumps({
        "photoTakenTime": {"timestamp": "1563100000"},
        "geoData": {"latitude": 38.72, "longitude": -9.14},
    }))
    return raiz / "Takeout"


def _apontar_catalogo(monkeypatch, tmp_path: Path) -> None:
    """O comando escreve no catálogo real por padrão; aqui vai num temporário."""
    from fotoorganizer.config.settings import Settings

    import fotoorganizer.cli as cli

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "c")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)


def test_verificar_arquivos_reporta_offline_e_online(monkeypatch, tmp_path, capsys):
    """`fotoorganizer verificar-arquivos` — a superfície de CLI da Parte 2
    (fase 12, item B): uma passada da reconciliação, sem depender de scan.

    Um arquivo só no catálogo: o orçamento por percentual padrão da
    reconciliação (uma fração do acervo elegível) sempre cobre 100% dele,
    sem depender da ordem em que o scan indexou vários arquivos.
    """
    _apontar_catalogo(monkeypatch, tmp_path)
    fotos = tmp_path / "fotos"
    alvo = make_jpeg(fotos / "some.jpg", seed=1)
    assert main(["scan", str(fotos)]) == 0
    capsys.readouterr()

    alvo.unlink()
    assert main(["verificar-arquivos"]) == 0
    saida = capsys.readouterr().out
    assert "1 verificado" in saida
    assert "1 ficaram offline" in saida
    assert "0 voltaram online" in saida
    assert "Ciclo completo" in saida


def test_importar_takeout_traz_gps_do_sidecar(monkeypatch, tmp_path, capsys):
    _apontar_catalogo(monkeypatch, tmp_path)
    takeout = _takeout_sintetico(tmp_path / "export")

    assert main(["importar", "takeout", str(takeout)]) == 0
    assert "1 importados" in capsys.readouterr().out


def test_importar_takeout_sem_pasta_avisa_em_vez_de_estourar(
    monkeypatch, tmp_path, capsys
):
    _apontar_catalogo(monkeypatch, tmp_path)
    assert main(["importar", "takeout"]) == 1
    assert "Informe a pasta" in capsys.readouterr().out

    assert main(["importar", "takeout", str(tmp_path / "nao-existe")]) == 1
    assert "não encontrada" in capsys.readouterr().out


def test_erro_do_apple_nomeia_o_app_que_precisa_da_permissao(
    monkeypatch, tmp_path, capsys
):
    """A mensagem tem de dizer QUAL app autorizar: o TCC é por app, e
    autorizar o errado é o jeito mais fácil de perder uma hora."""
    _apontar_catalogo(monkeypatch, tmp_path)
    import fotoorganizer.sources.apple_photos as ap

    monkeypatch.setattr(ap, "_app_responsavel", lambda: "o app «Claude»")
    monkeypatch.setattr(
        ap.ApplePhotosProvider, "iter_assets",
        lambda self: (_ for _ in ()).throw(
            ap.ApplePhotosError(
                f"não consegui ler a biblioteca do Fotos. Quem precisa estar "
                f"na lista é {ap._app_responsavel()}"
            )
        ),
    )
    assert main(["importar", "apple"]) == 1
    saida = capsys.readouterr().out
    assert "«Claude»" in saida


# --- terceira camada de config: CLI/env explícitos vencem o TOML ---------
#
# `_apontar_catalogo` (acima) monkeypatcha `cli.load_settings` para devolver
# um `Settings` fixo — nestes testes ele faz o papel de "defaults + TOML já
# resolvidos" (camadas 1 e 2), e o que se verifica é a camada 3 por cima
# dele, via `cli._settings(args)` com um `argparse.Namespace` real produzido
# pelo parser de verdade (`cli._build_parser()`).


def _settings_base(tmp_path: Path, **scanner_kwargs):
    from fotoorganizer.config.settings import ScannerSettings, Settings

    return Settings(
        data_dir=tmp_path / "dados",
        cache_dir=tmp_path / "cache",
        scanner=ScannerSettings(**scanner_kwargs),
    )


def test_flag_cli_sobrescreve_toml(monkeypatch, tmp_path):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _settings_base(tmp_path, workers=8)
    )
    args = cli._build_parser().parse_args(["--workers", "16", "scan", "x"])

    assert cli._settings(args).scanner.workers == 16


def test_campo_nao_tocado_por_cli_nem_env_fica_no_valor_herdado(monkeypatch, tmp_path):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings",
        lambda: _settings_base(tmp_path, workers=8, seguir_symlinks=True),
    )
    args = cli._build_parser().parse_args(["scan", "x"])

    resolved = cli._settings(args)
    assert resolved.scanner.workers == 8
    assert resolved.scanner.seguir_symlinks is True


def test_flag_booleano_explicito_falso_nao_e_confundido_com_nao_passado(
    monkeypatch, tmp_path
):
    """`--no-seguir-symlinks` tem de vencer um TOML com `seguir_symlinks =
    true` — se a camada de CLI tratasse "não veio" e "veio como False" do
    mesmo jeito, esse flag nunca conseguiria desligar o que o TOML ligou."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _settings_base(tmp_path, seguir_symlinks=True)
    )
    args = cli._build_parser().parse_args(["--no-seguir-symlinks", "scan", "x"])

    assert cli._settings(args).scanner.seguir_symlinks is False


def test_workers_zero_explicito_nao_e_confundido_com_nao_passado(monkeypatch, tmp_path):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _settings_base(tmp_path, workers=8)
    )
    args = cli._build_parser().parse_args(["--workers", "0", "scan", "x"])

    assert cli._settings(args).scanner.workers == 0


def test_env_var_usada_quando_flag_nao_veio_mas_flag_explicito_vence_env(
    monkeypatch, tmp_path
):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _settings_base(tmp_path, workers=8)
    )
    monkeypatch.setenv("FOTOORG_WORKERS", "5")

    sem_flag = cli._build_parser().parse_args(["scan", "x"])
    assert cli._settings(sem_flag).scanner.workers == 5

    com_flag = cli._build_parser().parse_args(["--workers", "9", "scan", "x"])
    assert cli._settings(com_flag).scanner.workers == 9


def test_cache_dir_explicito_vence_o_derivado_de_data_dir(monkeypatch, tmp_path):
    """`--data-dir` sozinho isola o cache junto (herança do comportamento
    antigo, ver `cli._overrides_de_cli_e_env`); mas `--cache-dir` explícito
    tem de prevalecer sobre esse derivado, não ser sobrescrito por ele."""
    import fotoorganizer.cli as cli
    from fotoorganizer.config.settings import Settings

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    args = cli._build_parser().parse_args([
        "--data-dir", str(tmp_path / "d"),
        "--cache-dir", str(tmp_path / "outro-cache"),
        "scan", "x",
    ])

    resolved = cli._settings(args)
    assert resolved.data_dir == tmp_path / "d"
    assert resolved.cache_dir == tmp_path / "outro-cache"


# --- env vars: as três camadas valem igual para elas ---------------------
#
# Os seis campos com env var (`FOTOORG_DATA_DIR`, `_CACHE_DIR`, `_WORKERS`,
# `_INCLUIR_OCULTOS`, `_SEGUIR_SYMLINKS`, `_SERVICOS_EXTERNOS`) precisam se
# comportar como os flags equivalentes — inclusive ao errar. Env var não
# tem parser: quem valida é `cli._bool_env`/`cli._valor_env`.
#
# `privacidade.reconhecimento_facial` não aparece aqui de propósito: é o
# único campo sem superfície de CLI/env (invariante 6 — ver comentário em
# `cli._build_parser`).

_BOOLEANOS_COM_ENV = [
    ("INCLUIR_OCULTOS", "incluir_ocultos", "scanner"),
    ("SEGUIR_SYMLINKS", "seguir_symlinks", "scanner"),
    ("SERVICOS_EXTERNOS", "servicos_externos", "privacidade"),
]


def _resolvido(cli, args, secao: str, campo: str):
    return getattr(getattr(cli._settings(args), secao), campo)


def _base_com(tmp_path: Path, secao: str, campo: str, valor: bool):
    from fotoorganizer.config.settings import (
        PrivacySettings,
        ScannerSettings,
        Settings,
    )

    tipo = ScannerSettings if secao == "scanner" else PrivacySettings
    return Settings(
        data_dir=tmp_path / "dados",
        cache_dir=tmp_path / "cache",
        **{secao: tipo(**{campo: valor})},
    )


@pytest.mark.parametrize("env_nome,campo,secao", _BOOLEANOS_COM_ENV)
@pytest.mark.parametrize("texto", ["1", "true", "TRUE", "sim", "yes", "YES", "on"])
def test_env_booleana_liga_o_campo_em_qualquer_grafia(
    monkeypatch, tmp_path, env_nome, campo, secao, texto
):
    """`yes`/`YES` viravam `False` em silêncio — nem erro, nem True."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _base_com(tmp_path, secao, campo, False)
    )
    monkeypatch.setenv(f"FOTOORG_{env_nome}", texto)
    args = cli._build_parser().parse_args(["scan", "x"])

    assert _resolvido(cli, args, secao, campo) is True


@pytest.mark.parametrize("env_nome,campo,secao", _BOOLEANOS_COM_ENV)
@pytest.mark.parametrize("texto", ["0", "false", "FALSE", "nao", "não", "no", "off"])
def test_env_booleana_desliga_o_campo_e_vence_o_toml(
    monkeypatch, tmp_path, env_nome, campo, secao, texto
):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _base_com(tmp_path, secao, campo, True)
    )
    monkeypatch.setenv(f"FOTOORG_{env_nome}", texto)
    args = cli._build_parser().parse_args(["scan", "x"])

    assert _resolvido(cli, args, secao, campo) is False


@pytest.mark.parametrize("env_nome,campo,secao", _BOOLEANOS_COM_ENV)
def test_env_booleana_vazia_nao_derruba_o_valor_do_toml(
    monkeypatch, tmp_path, env_nome, campo, secao
):
    """Variável exportada vazia é ausência, não um `False` implícito: senão
    um `FOTOORG_SEGUIR_SYMLINKS=` herdado do ambiente desliga em silêncio o
    que o usuário ligou no TOML."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _base_com(tmp_path, secao, campo, True)
    )
    monkeypatch.setenv(f"FOTOORG_{env_nome}", "")
    args = cli._build_parser().parse_args(["scan", "x"])

    assert _resolvido(cli, args, secao, campo) is True


@pytest.mark.parametrize("env_nome,campo,secao", _BOOLEANOS_COM_ENV)
def test_env_booleana_irreconhecivel_e_erro_de_uso_e_nao_palpite(
    monkeypatch, tmp_path, env_nome, campo, secao, capsys
):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _base_com(tmp_path, secao, campo, True)
    )
    monkeypatch.setenv(f"FOTOORG_{env_nome}", "talvez")

    with pytest.raises(SystemExit) as saida:
        cli.main(["scan", "x"])

    assert saida.value.code == 2
    erro = capsys.readouterr().err
    assert f"FOTOORG_{env_nome}" in erro
    assert "talvez" in erro


@pytest.mark.parametrize("flag,env_nome,campo,do_env,esperado", [
    ("--incluir-ocultos", "FOTOORG_INCLUIR_OCULTOS", "incluir_ocultos",
     "false", True),
    ("--no-seguir-symlinks", "FOTOORG_SEGUIR_SYMLINKS", "seguir_symlinks",
     "true", False),
])
def test_flag_booleano_vence_a_env_var(
    monkeypatch, tmp_path, flag, env_nome, campo, do_env, esperado
):
    """Convivência das duas fontes da mesma camada: o flag é mais explícito
    (foi digitado nesta invocação), então ganha da env var herdada."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(cli, "load_settings", lambda: _settings_base(tmp_path))
    monkeypatch.setenv(env_nome, do_env)
    args = cli._build_parser().parse_args([flag, "scan", "x"])

    assert getattr(cli._settings(args).scanner, campo) is esperado


def test_env_var_numerica_invalida_vira_erro_de_uso_e_nao_traceback(
    monkeypatch, tmp_path, capsys
):
    """`--workers abc` já saía como erro limpo do argparse; a env var
    equivalente saía como `ValueError` cru na cara do usuário."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(cli, "load_settings", lambda: _settings_base(tmp_path))
    monkeypatch.setenv("FOTOORG_WORKERS", "abc")

    with pytest.raises(SystemExit) as saida:
        cli.main(["scan", "x"])

    assert saida.value.code == 2
    erro = capsys.readouterr().err
    assert "FOTOORG_WORKERS" in erro
    assert "abc" in erro


def test_env_var_de_caminho_vazia_nao_reaponta_o_catalogo_para_o_cwd(
    monkeypatch, tmp_path
):
    """`FOTOORG_DATA_DIR=` fazia `data_dir` virar `Path('.')`: um `scan`
    criava catálogo, cache e logs no diretório corrente do shell e indexava
    ali, enquanto o catálogo real ficava intacto e sumia da vista."""
    import fotoorganizer.cli as cli

    base = _settings_base(tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda: base)
    monkeypatch.setenv("FOTOORG_DATA_DIR", "")
    monkeypatch.setenv("FOTOORG_CACHE_DIR", "   ")
    args = cli._build_parser().parse_args(["scan", "x"])

    resolved = cli._settings(args)
    assert resolved.data_dir == base.data_dir
    assert resolved.cache_dir == base.cache_dir


def test_env_vars_de_caminho_e_numero_valem_quando_preenchidas(
    monkeypatch, tmp_path
):
    import fotoorganizer.cli as cli

    monkeypatch.setattr(cli, "load_settings", lambda: _settings_base(tmp_path))
    monkeypatch.setenv("FOTOORG_DATA_DIR", str(tmp_path / "env-dados"))
    monkeypatch.setenv("FOTOORG_CACHE_DIR", str(tmp_path / "env-cache"))
    monkeypatch.setenv("FOTOORG_WORKERS", "7")
    args = cli._build_parser().parse_args(["scan", "x"])

    resolved = cli._settings(args)
    assert resolved.data_dir == tmp_path / "env-dados"
    assert resolved.cache_dir == tmp_path / "env-cache"
    assert resolved.scanner.workers == 7


def test_data_dir_sozinho_nao_descarta_cache_dir_escrito_no_toml(
    monkeypatch, tmp_path
):
    """O cache derivado de `--data-dir` é dedução da CLI, não pedido do
    usuário: tem de perder para um `cache_dir` que ele escreveu no TOML.
    Aqui o TOML é real (não um `Settings` montado à mão) porque é o que
    carrega a proveniência que decide isto."""
    import fotoorganizer.cli as cli
    from fotoorganizer.config.settings import load_settings

    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f'[geral]\ncache_dir = "{tmp_path / "cache-do-toml"}"\n', encoding="utf-8"
    )
    monkeypatch.setattr(cli, "load_settings", lambda: load_settings(cfg))
    args = cli._build_parser().parse_args([
        "--data-dir", str(tmp_path / "novo"), "scan", "x",
    ])

    resolved = cli._settings(args)
    assert resolved.data_dir == tmp_path / "novo"
    assert resolved.cache_dir == tmp_path / "cache-do-toml"


def test_data_dir_sozinho_ainda_isola_o_cache_quando_o_toml_nao_opinou(
    monkeypatch, tmp_path
):
    """Sem `cache_dir` no TOML, a dedução continua valendo — senão o
    catálogo iria para o diretório alternativo e os thumbnails para o cache
    real do usuário."""
    import fotoorganizer.cli as cli
    from fotoorganizer.config.settings import load_settings

    cfg = tmp_path / "config.toml"
    cfg.write_text("[scanner]\nworkers = 3\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_settings", lambda: load_settings(cfg))
    args = cli._build_parser().parse_args([
        "--data-dir", str(tmp_path / "novo"), "scan", "x",
    ])

    assert cli._settings(args).cache_dir == tmp_path / "novo" / "cache"


def test_bench_passa_pela_camada_de_cli_e_env(monkeypatch, tmp_path):
    """`bench` chamava `_build_scanner` sem settings e caía em
    `load_settings()` — media o `workers` do TOML, não o pedido."""
    import fotoorganizer.cli as cli

    monkeypatch.setattr(
        cli, "load_settings", lambda: _settings_base(tmp_path, workers=2)
    )
    vistos = {}

    class _MetricasFalsas:
        indexados = pulados = vistos = 1

    class _ScannerFalso:
        def scan_source(self, _pasta):
            return None, _MetricasFalsas()

    def _falso_build_scanner(db_path, settings=None):
        vistos["workers"] = settings.scanner.workers
        return _ScannerFalso()

    monkeypatch.setattr(cli, "_build_scanner", _falso_build_scanner)
    assert cli.main(["--workers", "16", "bench", "-n", "1"]) == 0
    assert vistos["workers"] == 16


def test_data_dir_isola_o_catalogo_do_padrao(tmp_path, capsys):
    """Sem esta flag, a única forma de rodar contra um catálogo limpo era
    editar a config real do usuário ou trocar o HOME do processo. Suporte
    não consegue pedir isso a ninguém."""
    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "a.jpg", seed=1)
    alternativo = tmp_path / "catalogo-de-teste"

    assert main(["--data-dir", str(alternativo), "scan", str(fotos)]) == 0

    assert (alternativo / "catalog.db").is_file()
    saida = capsys.readouterr().out
    assert str(alternativo / "catalog.db") in saida
    # E o padrão do usuário não foi tocado.
    from fotoorganizer.config import paths
    assert paths.default_data_dir() not in alternativo.parents


def test_bench_nao_grava_miniaturas_no_cache_real_do_usuario(
    monkeypatch, tmp_path, capsys
):
    """`bench` usa um banco temporário (`tmp_path / "bench.db"`) para não
    tocar no catálogo real — o cache de miniaturas tinha o mesmo objetivo
    mas caía no padrão de `Settings` quando ``--cache-dir`` não era passado,
    misturando miniaturas sintéticas ao cache de produção."""
    from fotoorganizer.config.settings import Settings

    import fotoorganizer.cli as cli

    cache_real = tmp_path / "cache-real-do-usuario"
    settings = Settings(data_dir=tmp_path / "dados", cache_dir=cache_real)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert main(["bench", "-n", "3"]) == 0

    assert not cache_real.exists()


def test_bench_com_cache_dir_explicito_usa_a_pasta_escolhida(
    monkeypatch, tmp_path, capsys
):
    """``--cache-dir`` é para medir com o cache real de propósito — quando
    passado, o benchmark deve respeitar a escolha em vez de isolar."""
    from fotoorganizer.config.settings import Settings

    import fotoorganizer.cli as cli

    cache_alvo = tmp_path / "cache-de-teste"
    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "nao-usado")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert main(["bench", "-n", "3", "--cache-dir", str(cache_alvo)]) == 0

    assert cache_alvo.exists()
