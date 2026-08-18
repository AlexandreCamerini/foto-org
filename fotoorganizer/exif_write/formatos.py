"""Allowlist de formatos com suporte de escrita — decisão medida, não suposição.

**Medido em 2026-08-18, remedido em 2026-08-18** (correção de meio-de-fase
sobre D-076, decisão explícita do dono) por `scripts/testar_escrita_exif.py`
contra o `catalog.db` de produção real (1.399 arquivos de acervo: 1.384
`.jpg`, 12 `.cr2`, 2 `.dng`, 1 `.tif`) — ver `docs/DECISOES.md` D-076 (medição
original) e D-077 (remedição com `verificacao.reclassificar_deslocamentos_
de_offset`, allowlist byte a byte) para a tabela completa e os critérios de
D-04.

**Resultado da remedição: `.jpg` e `.cr2` aprovam. `.dng` e `.tif`
continuam reprovados.** `verificacao.py` ganhou uma allowlist condicional
(D-077): tag de offset/ponteiro (`ThumbnailOffset`, `PreviewImageStart`,
`StripOffsets`, `TileOffsets`, `JpgFromRawStart`, `MPImageStart`) só deixa
de contar como "inesperada" quando o conteúdo binário que ela aponta é
sha256-idêntico antes/depois da escrita — prova de relocação pura, não
suposição. `.jpg` (20/20 amostras) e `.cr2` (12/12, todas as alcançáveis)
passam integralmente sob esse critério: todo deslocamento medido é
relocação comprovada. `.dng` (2/2) continua reprovado: duas das suas tags
de offset (`SubIFD:TileOffsets`, `SubIFD3:TileOffsets`) têm tiles demais
para o exiftool expor como lista de inteiros no dump (`-j -G1 -a -n`
devolve `"(Binary data N bytes, use -b option to extract)"`, não uma
lista parseável) — a prova byte a byte exige o valor numérico do offset, e
`reclassificar_deslocamentos_de_offset` fica corretamente fail-safe
(mantém "inesperada") quando não consegue parsear. `.tif` reprova por um
motivo sempre distinto de offset, inalterado por esta correção: tag
`IPTC:EnvelopeRecordVersion` nova + 2 avisos novos do exiftool.
`.cr3`/`.heic`/`.heif` continuam sem amostra no acervo (D-09), "não
testado" — categoria diferente de "reprovado".

`.dng` e `.tif` continuam caindo no fallback de sidecar XMP (D-06/EXIF-05).
`.jpg`/`.cr2` (e `.jpeg` por construção) passam a ter escrita EXIF direta
disponível a partir desta correção.
"""

from __future__ import annotations

from pathlib import Path

MEDIDO_EM: str | None = "2026-08-18"

# Medido (remedição D-077, 2026-08-18): .jpg (20/20) e .cr2 (12/12, todas
# as amostras alcançáveis) aprovam sob o critério estendido de
# verificacao.reclassificar_deslocamentos_de_offset — todo deslocamento de
# offset observado é relocação byte a byte comprovada, não perda de
# conteúdo. .dng/.tif continuam reprovados (ver docstring do módulo e
# docs/DECISOES.md D-077).
FORMATOS_APROVADOS: frozenset[str] = frozenset({".jpg", ".jpeg", ".cr2"})

# Motivo específico por extensão — D-05 exige motivo visível em toda linha
# não suportada, nunca desaparecimento silencioso. Distingue "reprovado no
# teste" (D-04) de "sem amostra para testar" (D-09) — são coisas
# diferentes e o texto é literal na UI.
MOTIVOS_NAO_SUPORTADO: dict[str, str] = {
    ".dng": (
        "DNG — reprovado em 2/2 amostras remedidas (2026-08-18, D-077): "
        "SubIFD:TileOffsets e SubIFD3:TileOffsets têm tiles demais para o "
        "exiftool expor como lista de inteiros no dump (vira \"(Binary "
        "data N bytes...)\"), então a prova byte a byte de relocação não "
        "consegue parsear o offset — fica fail-safe como inesperada, "
        "mesmo sendo provável que também seja relocação pura"
    ),
    ".tif": (
        "TIF — reprovado em 1/1 amostra medida (2026-08-18): tag "
        "IPTC:EnvelopeRecordVersion nova fora do escopo reconhecido + 2 "
        "avisos novos do exiftool (IPTCDigest desatualizado, "
        "GPSProcessingMethod ausente) — motivo não relacionado a offset, "
        "não afetado pela remedição D-077"
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
