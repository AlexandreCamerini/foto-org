"""Log estruturado em arquivo — o rastro que sobrevive à morte do processo.

Dois scans do acervo real (93 mil e 225 mil arquivos vistos) morreram sem
uma linha de log que dissesse por quê: o modo web rodava só com
basicConfig(WARNING) no stderr do terminal que o abriu.
"""

import json
import logging

from fotoorganizer.app.logsetup import setup_logging


def _limpar_root():
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def test_info_vai_para_o_jsonl(tmp_path):
    """INFO persiste: é o nível do resumo de scan ('vistos=… indexados=…'),
    exatamente o que faltou para diagnosticar as mortes."""
    try:
        setup_logging(tmp_path)
        logging.getLogger("fotoorganizer.scanner").info(
            "scan /x: concluido — vistos=%d", 42
        )
        for h in logging.getLogger().handlers:
            h.flush()

        linhas = [
            json.loads(l)
            for l in (tmp_path / "fotoorganizer.jsonl")
            .read_text().strip().splitlines()
        ]
        assert any("vistos=42" in linha["msg"] for linha in linhas)
        assert all({"ts", "nivel", "logger", "msg"} <= set(l) for l in linhas)
    finally:
        _limpar_root()


def test_excecao_de_thread_cai_no_arquivo(tmp_path):
    """Os jobs rodam em thread: uma exceção lá era invisível fora do
    terminal. O threading.excepthook a leva para o arquivo."""
    import threading

    try:
        setup_logging(tmp_path)

        def explode():
            raise RuntimeError("job morreu")

        t = threading.Thread(target=explode, name="job-scan")
        t.start()
        t.join()
        for h in logging.getLogger().handlers:
            h.flush()

        conteudo = (tmp_path / "fotoorganizer.jsonl").read_text()
        assert "job-scan" in conteudo and "job morreu" in conteudo
    finally:
        _limpar_root()
