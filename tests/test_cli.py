"""CLI de importação — a via que funciona quando o Acesso Total ao Disco
foi concedido ao terminal do usuário, e não ao app que abre o servidor."""

from pathlib import Path

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
