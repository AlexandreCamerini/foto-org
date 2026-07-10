"""Gera uma biblioteca de demonstração 100% sintética (nenhuma foto real).

Uso:
    .venv/bin/python scripts/gerar_demo.py [pasta_destino]

Cria JPEGs com EXIF variado (datas, GPS de Avignon/Tóquio, câmera), uma
pasta de família sem GPS, um PNG sem EXIF, um arquivo corrompido e
duplicatas (cópia exata + reexport) — o suficiente para exercitar scan,
sugestões, duplicatas e operações.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from tests.fixtures import make_corrupt_jpeg, make_jpeg, make_png


def _gradiente(size=(320, 240)) -> Image.Image:
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            px[x, y] = ((x * 2) % 256, (y * 3) % 256, (x + y) % 256)
    return img


def gerar(destino: Path) -> None:
    cenarios = [
        ("Viagens/2024 - França/Avignon", "2024:05:%02d 10:%02d:00",
         (43.95, 4.81), 18),
        ("Viagens/2023 - Japão/Tóquio", "2023:11:%02d 15:%02d:00",
         (35.68, 139.69), 18),
        ("Família/Aniversários", "2022:08:%02d 19:%02d:00", None, 18),
    ]
    seed = 0
    for pasta, fmt, gps, n in cenarios:
        for i in range(1, n + 1):
            seed += 1
            make_jpeg(
                destino / pasta / f"IMG_{seed:04d}.jpg", seed=seed * 7,
                data_exif=fmt % (i % 27 + 1, i % 59), gps=gps,
                make="Canon", model="EOS R6", size=(320, 240),
            )

    make_png(destino / "Diversos/captura.png")
    make_corrupt_jpeg(destino / "Diversos/corrompida.jpg")

    # Duplicatas: original em Avignon + cópia exata + reexport comprimido.
    original = destino / "Viagens/2024 - França/Avignon/IMG_0100.jpg"
    _gradiente().save(original, quality=92)
    shutil.copy(original, destino / "Diversos/IMG_0100 copy.jpg")
    _gradiente().save(destino / "Diversos/IMG_0100_export.jpg", quality=30)

    total = sum(1 for _ in destino.rglob("*") if _.is_file())
    print(f"{total} arquivos de demonstração em {destino}")


if __name__ == "__main__":
    alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_fotos")
    gerar(alvo.expanduser())
