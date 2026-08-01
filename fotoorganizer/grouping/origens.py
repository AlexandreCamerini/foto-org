"""Nomes que descrevem por ONDE a foto passou, não o que aconteceu.

"WhatsApp", "Screenshots" e "Downloads" aparecem como pasta e como álbum, e
nos dois casos significam a mesma coisa: origem, não acontecimento. O detector
de tipo de imagem precisa deles para saber que a foto foi recebida ou baixada;
o filtro de álbum precisa deles para não batizar uma viagem de "WhatsApp".

Mora em `grouping` porque `classification` já depende de `grouping` — o
caminho contrário fecharia um ciclo de import. Um vocabulário, dois usos.
"""

from __future__ import annotations

PASTAS_RECEBIDA = ("whatsapp", "telegram", "signal", "messenger")
PASTAS_CAPTURA = ("screenshots", "capturas de tela", "capturas")
PASTAS_BAIXADA = ("downloads", "transferências", "transferencias")
