"""Detecção de pasta sincronizada (D-07) — checagem pura de caminho.

Isto é **aviso**, nunca bloqueio: o dono decide incluir ou desmarcar pelo
mesmo checkbox de D-02. É checagem de caminho, não de estado de download —
o sinal "está materializado agora" (dataless/baixado) é transitório e
verificado nesta pesquisa que mudou durante a própria sessão de pesquisa;
"este caminho vive numa pasta gerida por sync" é fato estável e O(1), sem
chamar processo externo, sem nova dependência.
"""

from __future__ import annotations

from pathlib import Path

_RAIZES_SINCRONIZADAS: dict[str, Path] = {
    "iCloud Drive": Path("~/Library/Mobile Documents").expanduser(),
    # Cobre OneDrive, Google Drive, Box e a versão atual do Dropbox — raiz
    # unificada de File Provider desde o macOS 12.3.
    "Nuvem (File Provider)": Path("~/Library/CloudStorage").expanduser(),
}

# Fallback para instalação legada de Dropbox, anterior ao File Provider
# unificado (não coberta por _RAIZES_SINCRONIZADAS acima).
_DROPBOX_LEGADO = Path("~/Dropbox").expanduser()


def pasta_sincronizada(
    caminho: Path | str, raizes: dict[str, Path] | None = None,
) -> str | None:
    """Nome do serviço de sync que gerencia `caminho`, ou `None`.

    Resolve symlinks primeiro (`Path.resolve()`) — cobre o caso do
    redirecionamento de Desktop/Documents do iCloud, em que o caminho
    aparente parece uma pasta comum mas o alvo real do symlink cai dentro
    de `Mobile Documents`. Nunca levanta: falha de `resolve()` (`OSError`)
    devolve `None`, a resposta segura.

    `raizes`: injeção de teste — o default é `_RAIZES_SINCRONIZADAS`, mas
    testes podem passar raízes sob `tmp_path` sem depender do filesystem
    real desta máquina.
    """
    mapa = raizes if raizes is not None else _RAIZES_SINCRONIZADAS
    try:
        resolvido = Path(caminho).resolve()
    except OSError:
        return None
    for nome, raiz in mapa.items():
        if resolvido.is_relative_to(raiz):
            return nome
    if resolvido.is_relative_to(_DROPBOX_LEGADO):
        return "Dropbox (legado)"
    return None
