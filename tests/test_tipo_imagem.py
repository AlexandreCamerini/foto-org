"""Foto de câmera x captura de tela x imagem recebida.

A regra de ouro do módulo é "na dúvida, é foto": marcar foto legítima como
lixo custa mais caro que deixar um screenshot passar. Vários testes aqui
existem para garantir justamente que o detector NÃO condena.
"""

import pytest

from fotoorganizer.classification.tipo_imagem import (
    BAIXADA,
    CAPTURA,
    FOTO,
    RECEBIDA,
    classificar,
)


def _cls(**kw):
    base = dict(nome="x.jpg", pasta="/fotos", extensao="jpg")
    return classificar(**{**base, **kw})


class TestReconhece:
    def test_whatsapp_pelo_nome(self):
        v = _cls(nome="IMG-20240504-WA0012.jpg")
        assert v.tipo == RECEBIDA
        assert "WhatsApp" in v.justificativa

    def test_whatsapp_do_desktop(self):
        assert _cls(nome="WhatsApp Image 2024-05-04 at 10.30.00.jpeg").tipo == RECEBIDA

    def test_telegram(self):
        assert _cls(nome="photo_2024-05-04_10-30-00.jpg").tipo == RECEBIDA

    @pytest.mark.parametrize("nome", [
        "Captura de Tela 2024-05-04 às 10.30.00.png",
        "Screenshot 2024-05-04 at 10.30.00.png",
        "Screen Shot 2024-05-04 at 10.30.00.png",
    ])
    def test_captura_pelo_nome(self, nome):
        assert _cls(nome=nome, extensao="png").tipo == CAPTURA

    def test_pasta_de_mensageiro(self):
        v = _cls(nome="foto.jpg", pasta="/Users/eu/WhatsApp/Media/WhatsApp Images")
        assert v.tipo == RECEBIDA

    def test_resolucao_exata_de_tela_sem_camera(self):
        v = _cls(nome="a.png", extensao="png", largura=2556, altura=1179)
        assert v.tipo == CAPTURA
        assert "2556×1179" in v.justificativa

    def test_download_por_pasta(self):
        v = _cls(nome="banner.jpg", pasta="/Users/eu/Downloads")
        assert v.tipo == BAIXADA

    def test_download_por_nome_generico(self):
        assert _cls(nome="image (3).png", extensao="png").tipo == BAIXADA
        assert _cls(nome="unnamed.jpg").tipo == BAIXADA

    def test_png_sem_camera_e_captura_com_confianca_media(self):
        v = _cls(nome="diagrama.png", extensao="png")
        assert v.tipo == CAPTURA
        assert v.score < 0.8  # sinal fraco não vira alta confiança

    def test_resolucao_muito_baixa_sem_camera_parece_recomprimida(self):
        v = _cls(nome="qualquer.jpg", largura=640, altura=480)
        assert v.tipo == RECEBIDA
        assert v.score < 0.8


class TestNaoCondena:
    """Na dúvida, é foto — estes são os casos em que errar dói."""

    def test_foto_com_camera_e_foto(self):
        v = _cls(nome="DSC_0100.jpg", make="Canon", model="EOS R5",
                 largura=8192, altura=5464)
        assert v.tipo == FOTO
        assert v.score >= 0.8

    def test_gps_vence_nome_de_whatsapp(self):
        """A foto que você tirou e mandou para si mesmo continua sua: nenhum
        app de mensagem devolve coordenada."""
        v = _cls(nome="IMG-20240504-WA0012.jpg", tem_gps=True)
        assert v.tipo == FOTO
        assert "GPS" in v.justificativa

    def test_resolucao_de_tela_com_camera_nao_e_captura(self):
        """Câmera que por acaso dispara em 1920×1080 não vira screenshot."""
        v = _cls(nome="DSC_1.jpg", largura=1920, altura=1080,
                 make="Sony", model="A7")
        assert v.tipo == FOTO

    def test_png_de_camera_nao_e_captura(self):
        v = _cls(nome="scan.png", extensao="png", make="Epson", model="V600")
        assert v.tipo == FOTO

    def test_pasta_downloads_com_camera_continua_foto(self):
        """Foto de câmera que você baixou de um backup continua foto."""
        v = _cls(nome="DSC_9.jpg", pasta="/Users/eu/Downloads",
                 make="Nikon", model="Z6")
        assert v.tipo == FOTO

    def test_foto_de_camera_antiga_sem_exif_continua_foto(self):
        """Compacta de 1999 tirava 1024×768, e JPEG antigo perde EXIF ao ser
        copiado. Marcar a foto de infância de alguém como lixo custa a
        confiança no catálogo inteiro."""
        v = _cls(nome="DSCN0042.JPG", largura=1024, altura=768)
        assert v.tipo == FOTO

    def test_sem_nada_nao_condena(self):
        """Arquivo sem sinal nenhum e em boa resolução: fica foto, com
        confiança baixa — não vira lixo por omissão."""
        v = _cls(nome="qualquer.jpg", largura=4000, altura=3000)
        assert v.tipo == FOTO
        assert v.score <= 0.6


def test_justificativa_sempre_existe_e_e_legivel():
    for kw in ({}, {"nome": "IMG-20240504-WA0001.jpg"},
               {"nome": "Screenshot 1.png", "extensao": "png"},
               {"make": "Canon", "model": "R5"}):
        v = _cls(**kw)
        assert v.justificativa and not v.justificativa.endswith(" ")
        assert 0.0 < v.score <= 1.0
