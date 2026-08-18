#!/usr/bin/env python3
"""Mede, contra cópias descartáveis de arquivos reais do acervo, quais
formatos aceitam escrita de localização EXIF sem sujar nada fora de escopo
e sem passar a emitir aviso novo do exiftool (D-03/D-04).

ATENÇÃO — ao contrário do padrão do resto de `scripts/`, este script NÃO é
somente-leitura: ele ESCREVE. Mas escreve só e sempre em cópias feitas com
`shutil.copy2` dentro de um diretório temporário (`tempfile.mkdtemp()`) —
nunca no `catalog.db`, nunca em nenhum arquivo original do acervo. Nenhum
caminho vindo do catálogo é passado como `origem` do writer; só a cópia é.
Cada diretório temporário (incluindo o backup `_original` que o exiftool
deixa) é apagado no `finally` de cada amostra.

Usa o MESMO caminho de código de produção — `ExifToolWriter.escrever` e
`fotoorganizer.exif_write.verificacao` — nunca reimplementa a montagem de
argumentos aqui: se este script e o produto divergirem, a medição não vale
nada.

O resultado desta execução é registrado em `docs/DECISOES.md` e usado para
atualizar `fotoorganizer/exif_write/formatos.py` (plano 06-04 da fase
06-escrita-exif-de-localiza-o).

Uso:
    .venv/bin/python scripts/testar_escrita_exif.py
    .venv/bin/python scripts/testar_escrita_exif.py --amostras 5
    .venv/bin/python scripts/testar_escrita_exif.py --extensoes .cr2,.dng
    .venv/bin/python scripts/testar_escrita_exif.py --db <catalog.db> --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402
from fotoorganizer.exif_write import verificacao  # noqa: E402
from fotoorganizer.exif_write.writer import ExifToolWriter  # noqa: E402
from fotoorganizer.metadata.purepython import PurePythonExtractor  # noqa: E402

# O valor gravado na coluna `papel` é o NOME do membro do enum
# (`Enum(MediaRole, native_enum=False)` do SQLAlchemy grava o nome, não
# `.value`) — confirmado contra o catálogo real: a coluna guarda "ACERVO",
# não "acervo" (que é `MediaRole.ACERVO.value`). Usar o valor errado aqui
# não quebraria a query, silenciaria: toda extensão viraria `sem_amostra`
# sem nenhum erro visível — exatamente o tipo de falha que T-06-20 cobre.
_PAPEL_ACERVO = "ACERVO"

# Mesmos valores sintéticos usados na pesquisa (06-RESEARCH.md), para que a
# medição seja comparável entre execuções.
_CAMPOS_TESTE: dict[str, object] = {
    "gps": (-23.55052, -46.633308),
    "cidade": "São Paulo",
    "pais": "Brasil",
}

# Campos de `MediaMetadata` que precisam sair idênticos entre a releitura
# estrutural de antes e depois — condição (c) de D-04: o arquivo ainda abre
# e continua se lendo igual, não só "as tags esperadas mudaram".
_CAMPOS_ESTRUTURAIS_LEITURA = ("largura", "altura", "data_capturada", "model")


@dataclass(slots=True)
class ResultadoAmostra:
    """Veredito de uma cópia testada."""

    caminho: str
    aprovado: bool
    motivo: str
    campos_gravados: tuple[str, ...] = ()


@dataclass(slots=True)
class ResultadoExtensao:
    """Veredito agregado de uma extensão — conservador por desenho: uma
    amostra reprovada reprova a extensão inteira (D-04)."""

    extensao: str
    amostras: list[ResultadoAmostra] = field(default_factory=list)

    @property
    def veredito(self) -> str:
        if not self.amostras:
            return "sem_amostra"
        return "aprovado" if all(a.aprovado for a in self.amostras) else "reprovado"

    @property
    def motivo(self) -> str:
        if not self.amostras:
            return "nenhum arquivo de acervo alcançável em disco para esta extensão"
        if self.veredito == "aprovado":
            n = len(self.amostras)
            return f"diff limpo + sem aviso novo + releitura idêntica em {n}/{n} amostras"
        for amostra in self.amostras:
            if not amostra.aprovado:
                return amostra.motivo
        return ""


def amostrar(
    db: Path, amostras: int, extensoes: list[str] | None
) -> dict[str, list[Path]]:
    """Agrupa `media_files` de acervo por extensão (com ponto, minúscula) e
    escolhe até `amostras` caminhos ALCANÇÁVEIS em disco por extensão.

    Extensão presente no catálogo mas sem nenhum arquivo alcançável entra
    com lista vazia — o chamador reporta isso como `sem_amostra`, nunca
    como `aprovado`: ausência de dado é motivo para não afirmar (D-03).
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        linhas = con.execute(
            "select extensao, caminho from media_files"
            " where papel = ?"
            " order by extensao, id",
            (_PAPEL_ACERVO,),
        ).fetchall()
    finally:
        con.close()

    candidatos: dict[str, list[str]] = {}
    for extensao_crua, caminho in linhas:
        # `media_files.extensao` é gravada sem o ponto pelo scanner
        # (achado do plano 06-03) — normalizada aqui, uma vez, para o
        # mesmo formato pontuado que `formatos.py` e a allowlist esperam.
        ext = f".{extensao_crua.lower()}"
        candidatos.setdefault(ext, []).append(caminho)

    alvo = extensoes if extensoes is not None else sorted(candidatos)

    resultado: dict[str, list[Path]] = {}
    for ext in alvo:
        alcancaveis: list[Path] = []
        for caminho in candidatos.get(ext, []):
            p = Path(caminho)
            if p.exists():
                alcancaveis.append(p)
                if len(alcancaveis) >= amostras:
                    break
        resultado[ext] = alcancaveis
    return resultado


def testar_amostra(origem: Path, writer: ExifToolWriter) -> ResultadoAmostra:
    """Copia `origem` para um diretório temporário, escreve nela (nunca no
    original) e aplica o critério de D-04 na íntegra: aprovado só quando as
    TRÊS condições valem — diff sem tags inesperadas, delta de avisos
    vazio, e releitura estrutural idêntica.

    Deviação (correção de meio-de-fase, D-0XX): antes de aplicar o
    critério, toda tag "inesperada" que seja um deslocamento de
    offset/ponteiro comprovadamente byte a byte idêntico (mesmo padrão do
    achado de D-076) é reclassificada para `esperadas_condicionais` via
    `verificacao.reclassificar_deslocamentos_de_offset`. O writer nunca
    usa `-overwrite_original` (ver `writer.py`), então o backup
    `<copia>_original` que o exiftool deixa é byte a byte o "antes" —
    exatamente o par de arquivos que a prova byte a byte precisa, sem
    nenhum snapshot extra deste script.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="testar_escrita_exif_"))
    try:
        copia = tmpdir / origem.name
        shutil.copy2(origem, copia)  # daqui em diante só a cópia é tocada

        antes = verificacao.dump(copia)
        avisos_antes = verificacao.avisos(copia)
        meta_antes = PurePythonExtractor().extract(copia)

        writer.escrever(copia, dict(_CAMPOS_TESTE))

        depois = verificacao.dump(copia)
        avisos_depois = verificacao.avisos(copia)
        meta_depois = PurePythonExtractor().extract(copia)

        diff = verificacao.diferenca(antes, depois)
        backup = ExifToolWriter.caminho_backup(copia)
        if diff.inesperadas and backup.exists():
            diff = verificacao.reclassificar_deslocamentos_de_offset(
                diff, antes, depois, backup, copia
            )
        avisos_novos = avisos_depois - avisos_antes

        campos_gravados = tuple(
            campo for campo in _CAMPOS_TESTE if verificacao.campo_gravado(campo, diff)
        )

        motivos_falha: list[str] = []
        if diff.inesperadas:
            motivos_falha.append(f"tags inesperadas: {sorted(diff.inesperadas)}")
        if avisos_novos:
            motivos_falha.append(f"avisos novos do exiftool: {sorted(avisos_novos)}")

        divergencias_estruturais = [
            f"{campo}: {getattr(meta_antes, campo)!r} -> {getattr(meta_depois, campo)!r}"
            for campo in _CAMPOS_ESTRUTURAIS_LEITURA
            if getattr(meta_antes, campo) != getattr(meta_depois, campo)
        ]
        if divergencias_estruturais:
            motivos_falha.append(
                f"releitura estrutural mudou: {divergencias_estruturais}"
            )

        aprovado = not motivos_falha
        motivo = (
            f"campos gravados: {campos_gravados}" if aprovado else "; ".join(motivos_falha)
        )
        return ResultadoAmostra(
            caminho=str(origem),
            aprovado=aprovado,
            motivo=motivo,
            campos_gravados=campos_gravados,
        )
    finally:
        # Apaga a cópia, o `_original` que o exiftool deixou e qualquer
        # outro resíduo — tudo mora dentro de `tmpdir` (T-06-19).
        shutil.rmtree(tmpdir, ignore_errors=True)


def imprimir_tabela(resultados: dict[str, ResultadoExtensao]) -> None:
    print(f"{'extensão':<10}{'amostras':>10}  {'veredito':<12}motivo")
    for ext in sorted(resultados):
        r = resultados[ext]
        print(f"{ext:<10}{len(r.amostras):>10}  {r.veredito:<12}{r.motivo}")


def imprimir_bloco_copiar(resultados: dict[str, ResultadoExtensao]) -> None:
    """Linha pronta para colar em `formatos.py` — para não haver
    transcrição manual errada do resultado medido."""
    aprovados = sorted(ext for ext, r in resultados.items() if r.veredito == "aprovado")
    reprovados = {
        ext: r.motivo for ext, r in resultados.items() if r.veredito == "reprovado"
    }
    sem_amostra = sorted(ext for ext, r in resultados.items() if r.veredito == "sem_amostra")

    print("\n--- copiar para fotoorganizer/exif_write/formatos.py ---")
    print("FORMATOS_APROVADOS (medido):")
    print("    frozenset({" + ", ".join(f'"{e}"' for e in aprovados) + "})")
    if reprovados:
        print("MOTIVOS_NAO_SUPORTADO — reprovados no teste:")
        for ext, motivo in sorted(reprovados.items()):
            print(f'    "{ext}": "{ext.lstrip(".").upper()} — reprovado: {motivo}",')
    if sem_amostra:
        print("MOTIVOS_NAO_SUPORTADO — sem amostra alcançável (não testado, não reprovado):")
        for ext in sem_amostra:
            print(
                f'    "{ext}": "{ext.lstrip(".").upper()} — sem amostra alcançável '
                'neste acervo, não testado",'
            )


def _para_json(resultados: dict[str, ResultadoExtensao]) -> dict:
    return {
        ext: {
            "veredito": r.veredito,
            "motivo": r.motivo,
            "amostras": [
                {
                    "caminho": a.caminho,
                    "aprovado": a.aprovado,
                    "motivo": a.motivo,
                    "campos_gravados": list(a.campos_gravados),
                }
                for a in r.amostras
            ],
        }
        for ext, r in resultados.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", type=Path, default=paths.default_db_path())
    ap.add_argument("--amostras", type=int, default=3)
    ap.add_argument(
        "--extensoes",
        type=str,
        default=None,
        help="lista separada por vírgula, ex: .cr2,.dng "
        "(default: todas as presentes no catálogo)",
    )
    ap.add_argument("--json", action="store_true", help="imprime também o resultado em JSON")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"catálogo não encontrado: {args.db}", file=sys.stderr)
        return 1

    if not ExifToolWriter.disponivel():
        print("exiftool não encontrado no PATH — necessário para a medição.", file=sys.stderr)
        return 1

    extensoes: list[str] | None = None
    if args.extensoes:
        extensoes = [
            e.strip().lower() if e.strip().startswith(".") else f".{e.strip().lower()}"
            for e in args.extensoes.split(",")
            if e.strip()
        ]

    amostragem = amostrar(args.db, args.amostras, extensoes)
    if not amostragem or not any(amostragem.values()):
        alvo = ", ".join(extensoes) if extensoes else "(todas as presentes no catálogo)"
        print(
            f"nenhum arquivo de acervo alcançável em {args.db} para {alvo} — "
            "catálogo vazio, sem registro papel=ACERVO ou nenhum arquivo em "
            "disco. A medição não pode prosseguir sem dado real (D-03): "
            "ausência de amostra não é motivo para aprovar.",
            file=sys.stderr,
        )
        return 1

    writer = ExifToolWriter()
    resultados: dict[str, ResultadoExtensao] = {}
    for ext, caminhos in amostragem.items():
        r = ResultadoExtensao(extensao=ext)
        for caminho in caminhos:
            r.amostras.append(testar_amostra(caminho, writer))
        resultados[ext] = r

    imprimir_tabela(resultados)
    imprimir_bloco_copiar(resultados)

    if args.json:
        print()
        print(json.dumps(_para_json(resultados), ensure_ascii=False, indent=2))

    print(
        "\nResultado registrado em docs/DECISOES.md "
        "(entrada nova, molde de D-026/D-074)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
