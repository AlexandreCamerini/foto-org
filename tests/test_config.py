from pathlib import Path

from fotoorganizer.config.settings import (
    Settings,
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
