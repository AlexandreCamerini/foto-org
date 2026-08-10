"""Provider do Apple Fotos: conversão de PhotoInfo e falhas limpas."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from fotoorganizer.sources import ApplePhotosError, ApplePhotosProvider
from fotoorganizer.sources.apple_photos import _asset_de


def _photo(**kw):
    padrao = dict(
        path="/lib/originals/A/foto.heic",
        date=datetime(2025, 11, 1, 9, 30, tzinfo=timezone.utc),
        location=(25.2, 55.3),
        title=None, description=None, favorite=False,
        albums=[], persons=[],
    )
    padrao.update(kw)
    return SimpleNamespace(**padrao)


def test_conversao_completa():
    asset = _asset_de(_photo(
        title="Burj", description="No topo", favorite=True,
        albums=["Dubai", "Dubai"], persons=["Serena", ""],
    ))
    assert asset.caminho == Path("/lib/originals/A/foto.heic")
    assert asset.data_capturada == datetime(2025, 11, 1, 9, 30)  # naive
    assert asset.gps_lat == 25.2
    assert asset.titulo == "Burj" and asset.favorito is True
    assert asset.albuns == ("Dubai",)   # sem duplicatas
    assert asset.pessoas == ("Serena",)  # vazios fora


def test_original_so_no_icloud_vira_referencia():
    """Biblioteca em 'Otimizar armazenamento' quase não tem arquivo local, e
    é dela que vem o GPS de celular. Descartar seria jogar fora o doador."""
    asset = _asset_de(_photo(path=None, uuid="ABC-123"))
    assert asset is not None
    assert asset.caminho is None
    assert asset.referencia == "ABC-123"
    assert asset.gps_lat == 25.2
    assert asset.data_capturada == datetime(2025, 11, 1, 9, 30)


def test_fuso_por_foto_do_apple_vira_o_segundo_instante():
    """O Apple Fotos é o único lugar deste acervo que sabe o fuso de cada
    foto (ZTIMEZONEOFFSET/ZTIMEZONENAME, entregue pelo osxphotos já aplicado
    a `photo.date`). A hora de parede continua sendo a que o relógio marcava
    ali — o que muda é que o instante absoluto para de ser jogado fora."""
    roma = timezone(timedelta(hours=2))
    asset = _asset_de(_photo(
        date=datetime(2019, 7, 14, 14, 0, tzinfo=roma)
    ))
    # Hora de parede: 14h em Roma, sem fuso (sem regressão).
    assert asset.data_capturada == datetime(2019, 7, 14, 14, 0)
    # Mesmo instante, absoluto: 12h UTC.
    assert asset.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_sem_fuso_o_provider_nao_inventa_instante_absoluto():
    """`photo.date` naive (ou ausente) não vira UTC por decreto: o provider
    devolve `None` e quem grava iguala os dois — igualdade é como se diz
    "fuso desconhecido", e vem sempre de quem grava, nunca de um palpite
    daqui.

    Contrato defensivo: o osxphotos chama `photos_datetime(default=True)`, e
    em Photos 5+ isso nunca devolve `None` nem naive (foto sem data vira
    1970-01-01+00:00). `_asset_de` é duck-typed e testado com fakes; a
    garantia vale para qualquer coisa que se pareça com um `PhotoInfo`."""
    naive = _asset_de(_photo(date=datetime(2019, 7, 14, 14, 0)))
    assert naive.data_capturada == datetime(2019, 7, 14, 14, 0)
    assert naive.data_capturada_utc is None

    assert _asset_de(_photo(date=None)).data_capturada_utc is None


def test_sem_arquivo_e_sem_uuid_nao_da_para_referenciar():
    assert _asset_de(_photo(path=None, uuid=None)) is None


def test_sem_gps_e_sem_data():
    asset = _asset_de(_photo(location=None, date=None))
    assert asset.gps_lat is None and asset.data_capturada is None


def test_biblioteca_inacessivel_da_erro_claro(tmp_path):
    """Este caminho de erro só existe DEPOIS do import de osxphotos: sem o
    extra [apple], o provider para antes, com outra mensagem (testada
    abaixo). Sem o skip, uma instalação limpa recebe a suíte vermelha por
    causa de uma dependência opcional."""
    pytest.importorskip("osxphotos", reason="erro de TCC só existe com o extra [apple]")

    provider = ApplePhotosProvider(tmp_path / "Nao Existe.photoslibrary")
    with pytest.raises(ApplePhotosError, match="Acesso Total ao Disco"):
        list(provider.iter_assets())


def test_sem_o_extra_apple_a_mensagem_diz_o_que_instalar(tmp_path, monkeypatch):
    """O outro lado: sem osxphotos, o erro tem de ensinar a resolver — e
    não pode derrubar o resto do app."""
    import builtins

    real_import = builtins.__import__

    def sem_osxphotos(nome, *args, **kwargs):
        if nome == "osxphotos":
            raise ImportError("simulado: extra [apple] ausente")
        return real_import(nome, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sem_osxphotos)

    provider = ApplePhotosProvider(tmp_path / "Qualquer.photoslibrary")
    with pytest.raises(ApplePhotosError, match=r"fotoorganizer\[apple\]"):
        list(provider.iter_assets())


def test_palavras_chave_do_apple_sao_lidas():
    """Palavra-chave é intenção declarada pelo dono, como álbum e pessoa.
    O provider lia álbum e pessoa e descartava a palavra-chave — enquanto o
    Lightroom já preenchia o mesmo campo do `ExternalAsset`."""
    asset = _asset_de(_photo(keywords=["Praia", "Praia", "Família", ""]))
    assert asset.palavras_chave == ("Praia", "Família")


def test_photo_sem_keywords_nao_quebra():
    """`_asset_de` é duck-typed: um PhotoInfo de outra versão do osxphotos —
    ou um fake destes testes — pode não ter o atributo. O fake padrão não
    tem, e é essa a garantia que interessa."""
    assert _asset_de(_photo()).palavras_chave == ()
    assert _asset_de(_photo(keywords=None)).palavras_chave == ()


def test_video_entra_junto_com_a_foto(tmp_path, monkeypatch):
    """`movies=False` descartava o vídeo — que numa biblioteca de iPhone é
    metade de cada Live Photo e carrega GPS quando a foto não carrega.

    O teste fixa o CONTRATO com o osxphotos (qual argumento é pedido), que é
    exatamente o que a regressão trocou."""
    import osxphotos  # noqa: F401  (pulado abaixo se ausente)

    pedidos = {}

    class FakeDB:
        def __init__(self, *_a, **_k):
            pass

        def photos(self, movies=False):
            pedidos["movies"] = movies
            return [
                _photo(uuid="FOTO-1"),
                _photo(uuid="VIDEO-1", path="/lib/originals/A/clip.mov"),
            ]

    monkeypatch.setattr("osxphotos.PhotosDB", FakeDB)
    assets = list(ApplePhotosProvider(tmp_path / "L.photoslibrary").iter_assets())

    assert pedidos["movies"] is True
    assert {a.referencia for a in assets} == {"FOTO-1", "VIDEO-1"}
