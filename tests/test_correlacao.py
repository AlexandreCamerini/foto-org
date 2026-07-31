"""Correlação temporal entre fontes: deriva de relógio e herança de GPS."""

from datetime import datetime, timedelta

from fotoorganizer.grouping import (
    FotoRef,
    estimar_offsets,
    herdar_gps,
)

CANON = ("Canon", "EOS R6")
IPHONE = ("Apple", "iPhone 15 Pro")
T0 = datetime(2025, 11, 1, 10, 0, 0)


def _canon(mid, segundos, **kw):
    return FotoRef(media_id=mid, source_id=1, camera=CANON,
                   quando=T0 + timedelta(seconds=segundos), **kw)


def _iphone(mid, segundos, lat=25.2, lon=55.3, **kw):
    return FotoRef(media_id=mid, source_id=2, camera=IPHONE,
                   quando=T0 + timedelta(seconds=segundos),
                   lat=lat, lon=lon, **kw)


def _de(herancas, media_id):
    """A herança de uma foto específica. Toda foto sem GPS tenta herdar, e
    o retorno traz todas — filtrar deixa a asserção falar de uma só."""
    return next((h for h in herancas if h.media_id == media_id), None)


# -- herança de GPS ----------------------------------------------------------
def test_heranca_do_doador_mais_proximo():
    fotos = [
        _canon(1, 0),                       # sem GPS
        _iphone(2, -42),                    # doadora 42s antes
        _iphone(3, 600, lat=25.9, lon=55.9),
    ]
    (h,) = herdar_gps(fotos)
    assert h.media_id == 1 and h.doador_id == 2
    assert h.lat == 25.2
    assert h.delta == timedelta(seconds=42)
    assert h.score_fator == 1.0  # dentro da janela curta


def test_fora_da_janela_nao_herda():
    fotos = [_canon(1, 0), _iphone(2, 11 * 60)]
    assert herdar_gps(fotos) == []


def test_confianca_decai_com_delta():
    fotos = [_canon(1, 0), _iphone(2, 6 * 60)]  # 6 min: meio da rampa
    (h,) = herdar_gps(fotos)
    assert 0.7 < h.score_fator < 0.9


def test_mesma_camera_na_mesma_fonte_nao_doa():
    # Duas fotos da MESMA câmera/fonte: uma com GPS não doa pra outra
    # (não é outra origem de informação).
    fotos = [
        _canon(1, 0),
        FotoRef(media_id=2, source_id=1, camera=CANON,
                quando=T0 + timedelta(seconds=30), lat=1.0, lon=2.0),
    ]
    assert herdar_gps(fotos) == []


def test_doadora_de_outra_fonte_mesmo_sem_camera():
    # Takeout sem make/model ainda doa (fonte diferente).
    fotos = [
        _canon(1, 0),
        FotoRef(media_id=2, source_id=3, camera=(None, None),
                quando=T0 + timedelta(seconds=60), lat=9.0, lon=8.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2


# -- deriva de relógio --------------------------------------------------------
def _ancoras_camera_3h_atrasada():
    """Mesma foto em 2 fontes: câmera marca 3h a menos que a referência."""
    fotos = []
    for i in range(3):
        fotos.append(FotoRef(
            media_id=10 + i, source_id=1, camera=CANON,
            quando=T0 + timedelta(minutes=i), hash_perceptual=f"ph{i}",
        ))
        fotos.append(FotoRef(
            media_id=20 + i, source_id=2, camera=(None, None),
            quando=T0 + timedelta(hours=3, minutes=i, seconds=5),
            lat=25.2, lon=55.3, hash_perceptual=f"ph{i}",
        ))
    return fotos


def test_offset_estimado_pelas_ancoras():
    offsets = estimar_offsets(_ancoras_camera_3h_atrasada())
    assert CANON in offsets
    assert abs(offsets[CANON] - timedelta(hours=3, seconds=5)) \
        < timedelta(seconds=1)


def test_offset_corrige_a_heranca():
    fotos = _ancoras_camera_3h_atrasada()
    # Foto nova da Canon sem cópia no Takeout: às 10:30 no relógio da
    # câmera = 13:30 reais; doadora do iPhone às 13:31 real.
    fotos.append(_canon(1, 30 * 60))
    fotos.append(FotoRef(
        media_id=2, source_id=2, camera=(None, None),
        quando=T0 + timedelta(hours=3, minutes=31), lat=13.75, lon=100.5,
    ))
    offsets = estimar_offsets(fotos)
    herancas = {h.media_id: h for h in herdar_gps(fotos, offsets)}
    assert 1 in herancas
    assert herancas[1].lat == 13.75
    # Sem a correção, os 3h de deriva estourariam a janela de 10 min.
    sem_offset = {h.media_id for h in herdar_gps(fotos)}
    assert 1 not in sem_offset


def test_ancoras_dispersas_sao_descartadas():
    fotos = []
    deltas = [0, 50 * 60, 200 * 60]  # desvios incoerentes entre si
    for i, d in enumerate(deltas):
        fotos.append(FotoRef(
            media_id=10 + i, source_id=1, camera=CANON,
            quando=T0 + timedelta(minutes=i), hash_rapido=f"x{i}",
        ))
        fotos.append(FotoRef(
            media_id=20 + i, source_id=2, camera=(None, None),
            quando=T0 + timedelta(minutes=i, seconds=d),
            lat=1.0, lon=1.0, hash_rapido=f"x{i}",
        ))
    assert estimar_offsets(fotos) == {}


def test_ancora_unica_nao_basta():
    fotos = _ancoras_camera_3h_atrasada()[:2]  # só 1 par
    assert estimar_offsets(fotos) == {}


def test_procura_alem_dos_dois_vizinhos_imediatos():
    """Os vizinhos mais próximos COM GPS são da mesma origem da foto.

    Só doador de outra origem acrescenta informação, e a versão anterior
    olhava apenas os dois vizinhos imediatos: quando os dois eram da mesma
    origem, ela desistia sem nunca alcançar o terceiro. Num acervo real isso
    barrou 27.117 candidatos — a biblioteca do Apple Fotos é uma fonte só,
    e uma referência sem GPS fica cercada de referências com GPS.
    """
    fotos = [
        _canon(1, 0),                                  # quem precisa herdar
        _canon(2, -5, lat=1.0, lon=1.0),               # tem GPS, MESMA origem
        _canon(3, 5, lat=2.0, lon=2.0),                # idem, do outro lado
        _iphone(4, 30, lat=25.2, lon=55.3),            # a única que serve
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 4
    assert (h.lat, h.lon) == (25.2, 55.3)
    assert h.delta == timedelta(seconds=30)


def test_a_busca_para_na_borda_da_janela():
    """Varrer além da janela seria trabalho jogado fora — e traria doador
    que a regra de tolerância já rejeita."""
    fotos = [_canon(1, 0)]
    fotos += [_canon(10 + i, 60 * i) for i in range(1, 12)]  # 11 min de irmãs
    fotos.append(_iphone(99, 11 * 60))                       # doadora fora
    # As irmãs perto do fim herdam (estão a menos de 10 min da doadora); a
    # foto 1, a 11 minutos dela, não.
    assert _de(herdar_gps(fotos), 1) is None


def test_o_mais_proximo_vence_mesmo_vindo_do_outro_lado():
    fotos = [
        _canon(1, 0),
        _canon(2, -20),
        _iphone(3, -100, lat=10.0, lon=10.0),   # atrás, mais longe
        _iphone(4, 40, lat=20.0, lon=20.0),     # à frente, mais perto
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 4 and h.lat == 20.0


def test_hora_vinda_do_arquivo_vale_menos():
    """`mtime` costuma ser a hora da cópia, não a do disparo: a vizinhança
    pode ser coincidência de quando os arquivos foram parar no disco."""
    certa = _de(herdar_gps([_canon(1, 0), _iphone(2, 30)]), 1)
    incerta = _de(herdar_gps(
        [_canon(1, 0, hora_do_arquivo=True), _iphone(2, 30)]
    ), 1)

    assert certa.hora_incerta is False
    assert incerta.hora_incerta is True
    assert incerta.score_fator < certa.score_fator
    # A herança continua acontecendo — vale menos, não vale zero.
    assert incerta.doador_id == 2

    # Basta um dos dois lados ser incerto.
    pelo_doador = _de(herdar_gps(
        [_canon(1, 0), _iphone(2, 30, hora_do_arquivo=True)]
    ), 1)
    assert pelo_doador.hora_incerta is True
