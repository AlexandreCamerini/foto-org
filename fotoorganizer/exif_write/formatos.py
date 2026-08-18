"""Allowlist de formatos com suporte de escrita — decisão medida, não suposição.

O valor inicial vem de D-09 (`06-CONTEXT.md`): o `catalog.db` real de hoje
só tem `.jpg`, `.cr2`, `.dng` e `.tif` — CR3/HEIC não têm amostra testável
neste acervo, então entram como "não suportado" por falta de teste, não por
reprovação, e vão para o fallback de sidecar XMP (D-06/EXIF-05).

`scripts/testar_escrita_exif.py` (plano 06-04) roda o teste empírico de
D-03/D-04 e atualiza este arquivo com o resultado medido.
"""

from __future__ import annotations

from pathlib import Path

# `None` = provisório, ainda não medido contra o acervo real por
# scripts/testar_escrita_exif.py. O plano 06-04 preenche com a data da
# medição.
MEDIDO_EM: str | None = None

# Provisório até a medição de D-03 — formatos presentes no catalog.db real
# hoje (D-09), sem histórico de corrupção documentado em escrita.
FORMATOS_APROVADOS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".cr2", ".dng", ".tif", ".tiff",
})

# Motivo específico por extensão — D-05 exige motivo visível em toda linha
# não suportada, nunca desaparecimento silencioso.
MOTIVOS_NAO_SUPORTADO: dict[str, str] = {
    ".cr3": "CR3 — sem teste de escrita neste acervo (zero arquivos .cr3 no catálogo hoje, D-09)",
    ".heic": "HEIC — sem teste de escrita neste acervo (zero arquivos .heic no catálogo hoje, D-09)",
    ".heif": "HEIF — sem teste de escrita neste acervo (zero arquivos .heif no catálogo hoje, D-09)",
}


def suportado(extensao: str) -> bool:
    """`True` se `extensao` está na allowlist medida. Case-insensitive."""
    return extensao.lower() in FORMATOS_APROVADOS


def motivo(extensao: str) -> str | None:
    """Motivo de não-suporte, ou `None` para formato aprovado.

    Nunca devolve string vazia para formato não suportado — D-05 exige
    motivo visível em toda linha não suportada do plano dry-run.
    """
    ext = extensao.lower()
    if ext in FORMATOS_APROVADOS:
        return None
    if ext in MOTIVOS_NAO_SUPORTADO:
        return MOTIVOS_NAO_SUPORTADO[ext]
    return f"{ext.lstrip('.').upper()} — sem teste de escrita neste acervo"


def caminho_sidecar(origem: Path) -> Path:
    """`foto.<ext>.xmp` — convenção que o leitor já procura primeiro.

    `metadata/exiftool.py::_sidecar_de` já checa `foto.<ext>.xmp` (convenção
    Adobe) antes de `foto.xmp` (convenção darktable/Lightroom) ao ler. Um
    sidecar novo escrito com este nome é pego pela próxima varredura sem
    nenhuma mudança no lado da leitura.
    """
    return Path(str(origem) + ".xmp")
