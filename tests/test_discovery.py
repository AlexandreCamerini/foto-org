import os

from fotoorganizer.scanner import DiscoveryConfig, iter_media_files
from fotoorganizer.scanner.discovery import dentro_de_pacote
from tests.fixtures import make_jpeg

EXTS = frozenset({".jpg", ".jpeg", ".png"})


def _paths(root, config):
    return sorted(str(p.relative_to(root)) for p in iter_media_files(root, config))


def test_encontra_recursivo_com_unicode(tmp_path):
    make_jpeg(tmp_path / "a.jpg")
    make_jpeg(tmp_path / "Viagens" / "日本" / "fotografía é vida.jpg")
    found = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert found == ["Viagens/日本/fotografía é vida.jpg", "a.jpg"]


def test_ignora_ocultos_por_padrao(tmp_path):
    make_jpeg(tmp_path / ".escondida.jpg")
    make_jpeg(tmp_path / ".pasta_oculta" / "dentro.jpg")
    make_jpeg(tmp_path / "normal.jpg")

    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == ["normal.jpg"]
    com_ocultos = _paths(
        tmp_path, DiscoveryConfig(extensoes=EXTS, incluir_ocultos=True)
    )
    assert len(com_ocultos) == 3


def test_nao_atravessa_symlink_e_evita_ciclo(tmp_path):
    real = tmp_path / "real"
    make_jpeg(real / "foto.jpg")
    # Symlink de diretório apontando para o pai — ciclo clássico.
    os.symlink(tmp_path, real / "loop")
    # Symlink de arquivo também não deve ser seguido por padrão.
    os.symlink(real / "foto.jpg", tmp_path / "atalho.jpg")

    found = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert found == ["real/foto.jpg"]


def test_padroes_ignorados(tmp_path):
    make_jpeg(tmp_path / "Exportadas" / "e.jpg")
    make_jpeg(tmp_path / "Viagens" / "v.jpg")
    config = DiscoveryConfig(extensoes=EXTS, padroes_ignorados=("Exportadas",))
    assert _paths(tmp_path, config) == ["Viagens/v.jpg"]


def test_extensao_desconhecida_ignorada(tmp_path):
    make_jpeg(tmp_path / "foto.jpg")
    (tmp_path / "video.mp4").write_bytes(b"nao e foto")
    (tmp_path / "Thumbs.db").write_bytes(b"lixo de sistema")
    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == ["foto.jpg"]


def test_pacote_de_biblioteca_e_reconhecido_pelo_sufixo(tmp_path):
    """O nome real é "<Qualquer Nome>.photoslibrary", nunca ".photoslibrary".

    A versão anterior comparava o nome inteiro contra um conjunto e nunca
    casava: um acervo real entrou com 45.822 miniaturas internas do Apple
    Fotos catalogadas como se fossem fotos do usuário.
    """
    dentro = (tmp_path / "Photos Library.photoslibrary" / "resources"
              / "derivatives" / "masters" / "ABC_4_5005_c.jpeg")
    make_jpeg(dentro)
    make_jpeg(tmp_path / "Viagens" / "foto.jpg")

    assert dentro_de_pacote(dentro) is True
    assert dentro_de_pacote(tmp_path / "Viagens" / "foto.jpg") is False
    # Continua sendo descoberto: o derivado carrega o GPS que o catálogo
    # externo não reporta. O que muda é o papel, não a visibilidade.
    assert len(_paths(tmp_path, DiscoveryConfig(extensoes=EXTS))) == 2


def test_pacote_reconhecido_em_qualquer_nivel_do_caminho(tmp_path):
    """Os derivados ficam vários níveis abaixo da raiz do pacote."""
    fundo = (tmp_path / "Fotos.photolibrary" / "a" / "b" / "c" / "d" / "x.jpg")
    make_jpeg(fundo)
    assert dentro_de_pacote(fundo) is True
    # Pasta que só *menciona* o sufixo no meio do nome não é pacote.
    assert dentro_de_pacote(tmp_path / "backup photoslibrary antiga" / "x.jpg") is False


def test_pasta_de_codigo_nao_e_varrida(tmp_path):
    """`node_modules` e asset catalog não são acervo nem testemunha.

    Num acervo real entraram 499 ícones de app e skins de emulador — e uma
    pasta `BoraChurrascoRio.imageset` acabou batizando um evento com 1.314
    fotos de verdade dentro.
    """
    make_jpeg(tmp_path / "Viagens" / "real.jpg")
    make_jpeg(tmp_path / "projeto" / "node_modules" / "pacote" / "icone.png")
    make_jpeg(tmp_path / "app" / "Assets.xcassets" / "Splash.imageset" / "s.png")
    make_jpeg(tmp_path / "app" / "Meu.framework" / "recurso.jpg")

    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == [
        "Viagens/real.jpg"
    ]


def test_pasta_de_fotos_com_nome_parecido_continua_valendo(tmp_path):
    """O casamento é por nome inteiro ou sufixo de pacote, não por pedaço:
    uma pasta chamada "Vendor Feira" ou "App do Casamento" é foto."""
    make_jpeg(tmp_path / "Vendor Feira" / "a.jpg")
    make_jpeg(tmp_path / "App do Casamento" / "b.jpg")
    achados = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert achados == ["App do Casamento/b.jpg", "Vendor Feira/a.jpg"]


def test_smart_previews_do_lightroom_entram_como_testemunha(tmp_path):
    """`.lrdata` é derivado, e derivado não é acervo — mas continua no
    catálogo doando sinal (invariante 8, mesmo tratamento de D-024).

    Medido no acervo do dono: 14.755 DNG de pré-visualização dentro de
    "Lightroom Catalog Smart Previews.lrdata" eram 57% de tudo que o app
    dizia ser organizável, e 100% deles são ilegíveis — não são RAW de
    verdade. Carregam 1.113 coordenadas, então rebaixar, nunca pular.
    """
    dentro = (
        tmp_path / "Lightroom" / "Catalogo Smart Previews.lrdata"
        / "0" / "0000" / "preview.dng"
    )
    # Conteúdo não importa: a descoberta decide por caminho e extensão, e o
    # DNG real destes arquivos é justamente o que nenhuma biblioteca abre.
    dentro.parent.mkdir(parents=True, exist_ok=True)
    dentro.write_bytes(b"nao e um RAW de verdade")
    make_jpeg(tmp_path / "Viagens" / "real.jpg")

    # Desce (o arquivo é encontrado)…
    assert "Lightroom/Catalogo Smart Previews.lrdata/0/0000/preview.dng" in _paths(
        tmp_path, DiscoveryConfig(extensoes=EXTS | {".dng"})
    )
    # …e é reconhecido como conteúdo de pacote, que o scanner marca SINAL.
    assert dentro_de_pacote(dentro) is True
    assert dentro_de_pacote(tmp_path / "Viagens" / "real.jpg") is False


def test_original_dentro_do_pacote_nao_e_rebaixado(tmp_path):
    """"originals" (Apple Fotos) e "Masters" (Aperture/iPhoto) são a pasta
    que o pacote existe para preservar — o arquivo ali É o original, não
    um derivado. `dentro_de_pacote` tratava tudo dentro do pacote igual, e
    um acervo real tinha 21.387 originais assim rebaixados a testemunha —
    8.419 deles sem cópia em lugar nenhum, nunca vistos em Revisão, Viagens
    ou Operações (docs/AVALIACAO_UX.md, seção C.2, medido em 2026-08-06).
    """
    original_apple = (
        tmp_path / "Photos Library.photoslibrary" / "originals" / "0"
        / "ABCDE.heic"
    )
    original_aperture = (
        tmp_path / "Walter.aplibrary" / "Masters" / "2010" / "10" / "30"
        / "IMG_0941.jpg"
    )
    derivado = (
        tmp_path / "Photos Library.photoslibrary" / "resources"
        / "derivatives" / "masters" / "x.jpeg"
    )
    assert dentro_de_pacote(original_apple) is False
    assert dentro_de_pacote(original_aperture) is False
    assert dentro_de_pacote(derivado) is True  # continua testemunha


def test_pasta_chamada_originals_fora_de_pacote_continua_normal(tmp_path):
    """Sem estar dentro de um pacote, "originals" é só um nome de pasta
    comum — não deve virar caso especial."""
    assert dentro_de_pacote(
        tmp_path / "Viagens" / "originals" / "x.jpg"
    ) is False


def test_original_do_lrdata_continua_testemunha(tmp_path):
    """`.lrdata` não tem a distinção original/derivado: é sempre preview
    de pré-visualização, mesmo que uma subpasta por acaso se chame
    'originals' ou 'masters' dentro dele."""
    dentro = (
        tmp_path / "Catalogo Smart Previews.lrdata" / "originals"
        / "0" / "preview.dng"
    )
    assert dentro_de_pacote(dentro) is True


def test_biblioteca_do_lightroom_nao_e_derivado(tmp_path):
    """`.lrlibrary` guarda ORIGINAL, ao contrário de `.lrdata`. Confundir os
    dois rebaixaria foto de verdade a testemunha."""
    original = (
        tmp_path / "Lightroom Library.lrlibrary" / "abc" / "originals"
        / "2025" / "DJI_0001.dng"
    )
    assert dentro_de_pacote(original) is False


def test_cache_de_aplicativo_nao_e_varrido(tmp_path):
    """Ninguém guarda acervo numa pasta chamada "Cache".

    Medido: 1.840 texturas de efeito do CapCut
    (~/Movies/CapCut/User Data/Cache) entraram como ACERVO com 0 GPS,
    0 câmera e nunca doaram lugar a foto nenhuma.
    """
    make_jpeg(tmp_path / "CapCut" / "User Data" / "Cache" / "effect" / "t.png")
    make_jpeg(tmp_path / "app" / "Caches" / "x.jpg")
    make_jpeg(tmp_path / "Viagens" / "real.jpg")

    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == ["Viagens/real.jpg"]


def test_pasta_de_fotos_com_cache_no_nome_continua_valendo(tmp_path):
    """O casamento é por nome inteiro: "Cachefotos" ou "Cache Bar" é foto."""
    make_jpeg(tmp_path / "Cachoeira" / "a.jpg")
    make_jpeg(tmp_path / "Cache Bar" / "b.jpg")
    achados = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert achados == ["Cache Bar/b.jpg", "Cachoeira/a.jpg"]
