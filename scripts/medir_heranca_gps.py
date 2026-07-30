"""Gera o cenário mínimo que dispara herança de GPS entre dispositivos.

Somente leitura sobre qualquer acervo real: cria fixtures sintéticas novas.
Uso: .venv/bin/python scripts/medir_heranca_gps.py <pasta_destino>

Cenário: o iPhone fotografa com GPS às 10:30; a câmera (outro make/model,
outra pasta/fonte) fotografa às 10:32, sem GPS. É o caso descrito pelo dono
do produto.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.fixtures import make_jpeg

AVIGNON = (43.9493, 4.8055)


def main(destino: Path) -> None:
    telefone = destino / "iPhone"
    camera = destino / "Camera"
    telefone.mkdir(parents=True, exist_ok=True)
    camera.mkdir(parents=True, exist_ok=True)

    # iPhone: com GPS, 10:30 e 10:40 (duas âncoras de tempo)
    for i, hora in enumerate(("10:30:00", "10:40:00")):
        make_jpeg(telefone / f"IMG_910{i}.jpg", seed=90 + i,
                  data_exif=f"2024:05:04 {hora}", gps=AVIGNON,
                  make="Apple", model="iPhone 15 Pro")

    # Câmera: sem GPS, 10:32 (2 min depois) e 10:38
    for i, hora in enumerate(("10:32:00", "10:38:00")):
        make_jpeg(camera / f"DSC_010{i}.jpg", seed=95 + i,
                  data_exif=f"2024:05:04 {hora}", gps=None,
                  make="Canon", model="EOS R5")

    print(f"cenário de herança criado em {destino}")
    print("  iPhone/  2 fotos COM GPS (Avignon), 10:30 e 10:40")
    print("  Camera/  2 fotos SEM GPS, 10:32 e 10:38 — devem herdar")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "demo_heranca").expanduser())
