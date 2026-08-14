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
