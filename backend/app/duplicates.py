"""Detecção de duplicatas — exatas (mesmo md5) e visuais (hash perceptual
parecido, ex. a mesma foto reexportada em qualidade diferente)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Photo

# Distância de Hamming máxima entre dois `phash` de 64 bits pra considerar
# "visualmente parecidas" — abaixo de ~10 costuma ser a mesma cena/foto;
# acima disso já são fotos diferentes. Limiar conservador pra não juntar
# fotos distintas por engano.
_PERCEPTUAL_THRESHOLD = 8


@dataclass
class DuplicateGroup:
    tipo: str  # "exata" | "visual"
    fotos: list[Photo] = field(default_factory=list)
    espaco_desperdicado_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "fotos": [
                {
                    "id": foto.id,
                    "caminho_original": foto.caminho_original,
                    "nome_arquivo": foto.nome_arquivo,
                    "tamanho_bytes": foto.tamanho_bytes,
                }
                for foto in self.fotos
            ],
            "espaco_desperdicado_bytes": self.espaco_desperdicado_bytes,
        }


def _hamming_distance(hash_a: str, hash_b: str) -> int:
    # Hashes perceptuais em hexadecimal (saída de `str(imagehash.phash(...))`)
    # — XOR bit a bit sem depender da lib `imagehash` estar instalada aqui.
    int_a = int(hash_a, 16)
    int_b = int(hash_b, 16)
    return bin(int_a ^ int_b).count("1")


def find_exact_duplicates(photos: list[Photo]) -> list[DuplicateGroup]:
    by_hash: dict[str, list[Photo]] = {}
    for photo in photos:
        by_hash.setdefault(photo.hash_md5, []).append(photo)

    groups = []
    for fotos in by_hash.values():
        if len(fotos) < 2:
            continue
        fotos_ordenadas = sorted(fotos, key=lambda p: p.tamanho_bytes, reverse=True)
        desperdicado = sum(p.tamanho_bytes for p in fotos_ordenadas[1:])
        groups.append(DuplicateGroup(tipo="exata", fotos=fotos_ordenadas, espaco_desperdicado_bytes=desperdicado))
    return groups


def find_visual_duplicates(photos: list[Photo]) -> list[DuplicateGroup]:
    """Agrupa por similaridade visual — roda sobre TODAS as fotos (não só as
    que ainda não caíram num grupo de duplicata exata). Uma foto reexportada
    em qualidade menor a partir de um arquivo que já tem uma cópia exata em
    outro lugar ainda é visualmente igual às duas — excluir os membros do
    grupo exato do cálculo faria esse terceiro arquivo ficar sozinho (cluster
    de 1) e sumir do resultado. A deduplicação entre os dois tipos de grupo
    acontece depois, em `find_all_duplicates`."""
    candidatos = [p for p in photos if p.hash_perceptual]

    visitados: set[int] = set()
    groups: list[DuplicateGroup] = []

    for i, foto in enumerate(candidatos):
        if foto.id in visitados:
            continue
        cluster = [foto]
        visitados.add(foto.id)
        for outra in candidatos[i + 1 :]:
            if outra.id in visitados:
                continue
            if _hamming_distance(foto.hash_perceptual, outra.hash_perceptual) <= _PERCEPTUAL_THRESHOLD:
                cluster.append(outra)
                visitados.add(outra.id)

        if len(cluster) < 2:
            continue
        cluster_ordenado = sorted(cluster, key=lambda p: p.tamanho_bytes, reverse=True)
        desperdicado = sum(p.tamanho_bytes for p in cluster_ordenado[1:])
        groups.append(
            DuplicateGroup(tipo="visual", fotos=cluster_ordenado, espaco_desperdicado_bytes=desperdicado)
        )

    return groups


def find_all_duplicates(photos: list[Photo]) -> dict:
    exatas = find_exact_duplicates(photos)
    visuais = find_visual_duplicates(photos)

    # Um grupo visual com EXATAMENTE o mesmo conjunto de fotos que um grupo
    # exato não traz informação nova — descarta só esse caso redundante.
    conjuntos_exatos = {frozenset(foto.id for foto in grupo.fotos) for grupo in exatas}
    visuais = [g for g in visuais if frozenset(foto.id for foto in g.fotos) not in conjuntos_exatos]

    todas = exatas + visuais
    espaco_total = sum(g.espaco_desperdicado_bytes for g in todas)

    return {
        "grupos": [g.to_dict() for g in todas],
        "total_grupos": len(todas),
        "espaco_total_economizavel_bytes": espaco_total,
        "espaco_total_economizavel_mb": round(espaco_total / (1024 * 1024), 2),
    }
