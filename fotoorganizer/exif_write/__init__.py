"""Escrita EXIF/IPTC/XMP de localização (D-075) — módulo paralelo, não filho.

`fotoorganizer/operations/` protege a cópia criando um caminho novo que
ainda não existe (`open('xb')`, "exclusive create"): se o destino já
existir, a operação falha sozinha, sem tocar em nada. Mutação in-place não
tem equivalente disso — não existe "criar exclusivamente" um arquivo que já
existe. Por isso o modelo de segurança deste pacote é outro: diff completo
de tags antes/depois (`verificacao.diferenca`) como único critério de
sucesso, e o backup `_original` do próprio exiftool como rede de recuperação
durante a janela entre escrita e verificação (ver `writer.py`).

Nada de `fotoorganizer/operations/` é herdado por este pacote — nem classe,
nem exceção, nem convenção de status. Os dois módulos são estruturalmente
parecidos (plano → dry-run → aprovação → execução → auditoria) porque
seguem o mesmo padrão de rigor do produto, não porque compartilham código.
"""

from __future__ import annotations
