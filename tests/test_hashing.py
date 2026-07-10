import hashlib

from fotoorganizer.security.hashing import quick_signature, sha256_full


def test_assinatura_igual_para_conteudo_igual(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"x" * 300_000)
    b.write_bytes(b"x" * 300_000)
    assert quick_signature(a) == quick_signature(b)


def test_assinatura_muda_com_conteudo(tmp_path):
    a = tmp_path / "a.bin"
    a.write_bytes(b"x" * 300_000)
    sig1 = quick_signature(a)
    # Mudança no fim do arquivo (fora dos primeiros 64K) precisa ser detectada.
    a.write_bytes(b"x" * 299_999 + b"y")
    assert quick_signature(a) != sig1


def test_assinatura_muda_com_tamanho(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"x" * 100)
    b.write_bytes(b"x" * 101)
    assert quick_signature(a) != quick_signature(b)


def test_sha256_bate_com_hashlib(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"conteudo de teste" * 1000)
    esperado = hashlib.sha256(f.read_bytes()).hexdigest()
    assert sha256_full(f) == f"sha256:{esperado}"
