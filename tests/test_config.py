from pathlib import Path

from fotoorganizer.config.settings import (
    UNSET,
    Settings,
    aplicar_overrides,
    load_settings,
    write_config_template,
)


def test_defaults_sem_arquivo(tmp_path):
    settings = load_settings(tmp_path / "inexistente.toml")
    assert settings.scanner.workers == 4
    assert settings.scanner.seguir_symlinks is False
    assert settings.privacidade.servicos_externos is False


def test_carrega_toml_com_overrides(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f"""
[geral]
data_dir = "{tmp_path / 'dados'}"

[scanner]
workers = 8
incluir_ocultos = true
""",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    assert settings.data_dir == tmp_path / "dados"
    assert settings.db_path == tmp_path / "dados" / "catalog.db"
    assert settings.scanner.workers == 8
    assert settings.scanner.incluir_ocultos is True
    # Seções não citadas mantêm defaults.
    assert settings.privacidade.servicos_externos is False


def test_chave_desconhecida_nao_quebra(tmp_path, caplog):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[scanner]\nchave_inventada = 1\n", encoding="utf-8")
    settings = load_settings(cfg)
    assert settings.scanner.workers == 4
    assert any("chave_inventada" in r.message for r in caplog.records)


def test_toml_invalido_usa_defaults(tmp_path, caplog):
    cfg = tmp_path / "config.toml"
    cfg.write_text("isto nao é toml [[[", encoding="utf-8")
    settings = load_settings(cfg)
    assert settings == Settings() or settings.scanner.workers == 4


def test_template_nao_sobrescreve(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[scanner]\nworkers = 2\n", encoding="utf-8")
    write_config_template(cfg)
    assert "workers = 2" in cfg.read_text(encoding="utf-8")


def test_template_criado_quando_ausente(tmp_path):
    cfg = tmp_path / "novo" / "config.toml"
    write_config_template(cfg)
    assert cfg.is_file()
    # Template só tem comentários — carregar dele produz defaults.
    assert load_settings(cfg).scanner.workers == 4


def test_expande_home(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[geral]\ndata_dir = "~/FotoTeste"\n', encoding="utf-8")
    settings = load_settings(cfg)
    assert settings.data_dir == Path.home() / "FotoTeste"


# --- terceira camada: aplicar_overrides() (CLI/env explícitos) -----------
#
# Ordem de precedência deliberada: defaults (dataclass) < TOML < overrides.
# Estes testes cobrem a função isoladamente; a integração com argparse/env
# vars fica em tests/test_cli.py.


def test_overrides_sobrescreve_toml(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        "[scanner]\nworkers = 8\nincluir_ocultos = true\n", encoding="utf-8"
    )
    settings = load_settings(cfg)
    assert settings.scanner.workers == 8

    settings = aplicar_overrides(settings, {"scanner": {"workers": 16}})

    assert settings.scanner.workers == 16
    # Campo do TOML que o override não tocou continua valendo — o override
    # não reseta a seção inteira para o default.
    assert settings.scanner.incluir_ocultos is True


def test_campo_nao_tocado_por_nenhuma_camada_fica_no_default(tmp_path):
    settings = load_settings(tmp_path / "inexistente.toml")

    settings = aplicar_overrides(settings, {"scanner": {"workers": 2}})

    assert settings.scanner.workers == 2
    # seguir_symlinks não apareceu nem no TOML (inexistente) nem no
    # override: fica no default da dataclass.
    assert settings.scanner.seguir_symlinks is False


def test_override_explicito_falso_ou_zero_nao_e_confundido_com_ausente(tmp_path):
    """`False`/`0` explícitos têm de vencer o TOML — a sentinela é o que
    torna isso possível: um override que chegou aqui já passou pelo filtro
    de UNSET de quem o montou, então qualquer valor presente no dict
    (inclusive vazio/zero/false) é para valer."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        "[scanner]\nincluir_ocultos = true\nworkers = 8\n", encoding="utf-8"
    )
    settings = load_settings(cfg)
    assert settings.scanner.incluir_ocultos is True
    assert settings.scanner.workers == 8

    settings = aplicar_overrides(
        settings, {"scanner": {"incluir_ocultos": False, "workers": 0}}
    )

    assert settings.scanner.incluir_ocultos is False
    assert settings.scanner.workers == 0


def test_overrides_vazio_nao_altera_nada(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[scanner]\nworkers = 8\n", encoding="utf-8")
    settings = load_settings(cfg)

    assert aplicar_overrides(settings, {}) == settings


def test_secao_desconhecida_em_overrides_avisa_em_vez_de_sumir(tmp_path, caplog):
    """Chave desconhecida *dentro* de uma seção já avisava; a seção inteira
    desconhecida (typo como `[scaner]`, ou uma seção que ainda não existe)
    não avisava nada — o override simplesmente não acontecia e o usuário
    ficava procurando por que o valor não pegou."""
    settings = load_settings(tmp_path / "inexistente.toml")

    resultado = aplicar_overrides(
        settings, {"thumbnails": {"tamanho": 512}, "scaner": {"workers": 2}}
    )

    assert resultado == settings
    avisos = " ".join(r.getMessage() for r in caplog.records)
    assert "thumbnails" in avisos
    assert "scaner" in avisos


def test_secao_desconhecida_no_toml_tambem_avisa(tmp_path, caplog):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[thumbnails]\ntamanho = 512\n", encoding="utf-8")

    settings = load_settings(cfg)

    assert settings.scanner.workers == 4
    assert any("thumbnails" in r.getMessage() for r in caplog.records)


# --- camada derivada: abaixo do TOML, acima dos defaults ----------------
#
# Valor que a CLI *deduz* de outro flag (hoje só `cache_dir` a partir de
# `--data-dir`) não é pedido do usuário e não pode vencer o TOML.


def test_derivado_nao_sobrescreve_valor_explicito_do_toml(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f'[geral]\ncache_dir = "{tmp_path / "do-toml"}"\n', encoding="utf-8"
    )
    settings = load_settings(cfg)

    settings = aplicar_overrides(
        settings,
        {"geral": {"data_dir": str(tmp_path / "novo")}},
        {"geral": {"cache_dir": str(tmp_path / "novo" / "cache")}},
    )

    assert settings.data_dir == tmp_path / "novo"
    assert settings.cache_dir == tmp_path / "do-toml"


def test_derivado_preenche_campo_que_ninguem_definiu(tmp_path):
    settings = load_settings(tmp_path / "inexistente.toml")

    settings = aplicar_overrides(
        settings,
        {"geral": {"data_dir": str(tmp_path / "novo")}},
        {"geral": {"cache_dir": str(tmp_path / "novo" / "cache")}},
    )

    assert settings.cache_dir == tmp_path / "novo" / "cache"


def test_override_explicito_vence_o_derivado(tmp_path):
    settings = load_settings(tmp_path / "inexistente.toml")

    settings = aplicar_overrides(
        settings,
        {"geral": {"cache_dir": str(tmp_path / "pedido")}},
        {"geral": {"cache_dir": str(tmp_path / "deduzido")}},
    )

    assert settings.cache_dir == tmp_path / "pedido"


def test_proveniencia_nao_entra_na_comparacao_de_settings(tmp_path):
    """`campos_explicitos` é metadado, não config: dois `Settings` com os
    mesmos valores continuam iguais, tenham vindo de onde tiverem vindo."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[geral]\ndata_dir = "~/FotoTeste"\n', encoding="utf-8"
    )
    do_toml = load_settings(cfg)

    assert do_toml.campos_explicitos == frozenset({"data_dir"})
    assert do_toml == Settings(data_dir=Path.home() / "FotoTeste")


def test_unset_e_sentinela_distinta_de_none_e_falsy():
    assert UNSET is not None
    assert UNSET != 0
    assert UNSET != False  # noqa: E712 - a comparação é o ponto do teste
    assert UNSET != ""
