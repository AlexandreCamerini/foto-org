"""Allowlist de formatos com suporte de escrita — decisão medida, não suposição.

**Medido em 2026-08-18** por `scripts/testar_escrita_exif.py` (plano 06-04)
contra o `catalog.db` de produção real (1.399 arquivos de acervo: 1.384
`.jpg`, 12 `.cr2`, 2 `.dng`, 1 `.tif`) — ver `docs/DECISOES.md` D-076 para a
tabela completa e os três critérios de D-04.

**Resultado: nenhum formato aprovou.** Os quatro formatos com amostra no
acervo real (`.jpg`, `.cr2`, `.dng`, `.tif`) reprovaram por deslocarem
offsets de blocos binários já existentes no arquivo (miniatura embutida,
segunda imagem MPF, dados RAW/tiles) — efeito colateral estrutural
inevitável de inserir um bloco IPTC/XMP novo num arquivo que já tinha
esses blocos, mas fora do escopo hoje reconhecido por
`verificacao.TAGS_ESTRUTURAIS_ESPERADAS`, que só cobre o caso "arquivo
nunca teve bloco nenhum". `.tif` reprova por um segundo motivo
independente: tag `IPTC:EnvelopeRecordVersion` nova + 2 avisos novos do
exiftool. `.cr3`/`.heic`/`.heif` continuam sem amostra no acervo (D-09),
"não testado" — categoria diferente de "reprovado".

Todo arquivo, de todo formato, cai hoje no fallback de sidecar XMP
(D-06/EXIF-05) até uma decisão futura do dono sobre estender
`TAGS_ESTRUTURAIS_ESPERADAS` para cobrir deslocamento de offset (D-076).
"""

from __future__ import annotations

from pathlib import Path

MEDIDO_EM: str | None = "2026-08-18"

# Medido: zero formatos passaram no critério de D-04 (diff sem tags
# inesperadas E delta de avisos vazio E releitura estrutural idêntica).
# Ver docstring do módulo e docs/DECISOES.md D-076.
FORMATOS_APROVADOS: frozenset[str] = frozenset()

# Motivo específico por extensão — D-05 exige motivo visível em toda linha
# não suportada, nunca desaparecimento silencioso. Distingue "reprovado no
# teste" (D-04) de "sem amostra para testar" (D-09) — são coisas
# diferentes e o texto é literal na UI.
MOTIVOS_NAO_SUPORTADO: dict[str, str] = {
    ".jpg": (
        "JPG — reprovado em 3/3 amostras medidas (2026-08-18): escrita "
        "desloca offsets de blocos binários já existentes (miniatura "
        "IFD1:ThumbnailOffset, segunda imagem MPImage2:MPImageStart) fora "
        "do escopo hoje reconhecido como andaime estrutural"
    ),
    ".jpeg": (
        "JPEG — mesmo formato de .jpg, mesmo resultado por construção "
        "(não amostrado separadamente; 3/3 amostras .jpg reprovadas em "
        "2026-08-18)"
    ),
    ".cr2": (
        "CR2 — reprovado em 3/3 amostras medidas (2026-08-18): escrita "
        "desloca offsets de blocos binários já existentes (preview, "
        "miniatura, strips) fora do escopo hoje reconhecido como andaime "
        "estrutural"
    ),
    ".dng": (
        "DNG — reprovado em 2/2 amostras medidas (2026-08-18): escrita "
        "desloca offsets de blocos binários já existentes (dados RAW, "
        "tiles) fora do escopo hoje reconhecido como andaime estrutural"
    ),
    ".tif": (
        "TIF — reprovado em 1/1 amostra medida (2026-08-18): tag "
        "IPTC:EnvelopeRecordVersion nova fora do escopo reconhecido + 2 "
        "avisos novos do exiftool (IPTCDigest desatualizado, "
        "GPSProcessingMethod ausente)"
    ),
    ".tiff": (
        "TIFF — mesmo formato de .tif, mesmo resultado por construção "
        "(não amostrado separadamente; 1/1 amostra .tif reprovada em "
        "2026-08-18)"
    ),
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
