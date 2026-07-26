"""Provider do Apple Fotos: conversão de PhotoInfo e falhas limpas."""

from datetime import datetime, timezone
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


def test_sem_arquivo_e_sem_uuid_nao_da_para_referenciar():
    assert _asset_de(_photo(path=None, uuid=None)) is None


def test_sem_gps_e_sem_data():
    asset = _asset_de(_photo(location=None, date=None))
    assert asset.gps_lat is None and asset.data_capturada is None


def test_biblioteca_inacessivel_da_erro_claro(tmp_path):
    provider = ApplePhotosProvider(tmp_path / "Nao Existe.photoslibrary")
    with pytest.raises(ApplePhotosError, match="Acesso Total ao Disco"):
        list(provider.iter_assets())
