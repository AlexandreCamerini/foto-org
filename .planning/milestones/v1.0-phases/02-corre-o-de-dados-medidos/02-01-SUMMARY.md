---
phase: 02-corre-o-de-dados-medidos
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, repository-pattern, media-filtering]

requires:
  - phase: 01-timezone-estimado
    provides: nenhuma dependência funcional — sequencial só por ordem de roadmap
provides:
  - "Filtro alcance=tudo (default da Biblioteca) distingue acervo de testemunha-com-arquivo, preservando referência externa sem arquivo (feature do commit 1b125f7)"
  - "_ACERVO_OU_REFERENCIA em fotoorganizer/repositories/media.py — novo predicado nomeado"
  - "Auditoria registrada dos 8 caminhos de contagem que não passam por _query, com um achado nomeado (arvore_de_pastas) para fase futura"
affects: [biblioteca, panorama, viagens-eventos]

tech-stack:
  added: []
  patterns:
    - "Predicado nomeado com docstring explicando o porquê e citando o teste que o trava, mesmo estilo de _acervo_ao_alcance"

key-files:
  created: []
  modified:
    - fotoorganizer/repositories/media.py
    - tests/test_repository.py
    - webapp/src/App.tsx

key-decisions:
  - "D-01 corrigido DUAS vezes nesta fatia: primeiro pelo pattern-mapper (papel puro, não _ACERVO), depois por mim durante execução (or_(papel==ACERVO, arquivo_ausente==True), não papel puro) — ver Deviations"
  - "faltantes não muda — testemunha (os dois tipos) continua lá, por desenho do próprio rótulo ALCANCES['faltantes']"
  - "Nenhum dos 4 contadores que não passam por _query foi alterado nesta fase (estatisticas, panorama, fontes_com_contagem, arvore_de_pastas, funil) — D-03 pediu auditoria, não mudança"

patterns-established:
  - "Antes de fixar um predicado que exclui um papel/estado, ler a função de gravação real (ex. _gravar_referencia) — o schema por si só (papel==ACERVO 'default') não garante o que o import real grava"

requirements-completed: [BUG-03]

duration: ~75min (incluindo o checkpoint e a correção)
completed: 2026-08-16
---

# Phase 2: Correção de dados medidos Summary

**Filtro "Tudo" da Biblioteca (`alcance=tudo`, o default) para de misturar miniatura/derivado interno com o acervo real, preservando a visibilidade de referência externa sem arquivo local (iCloud, volume desmontado) que o commit `1b125f7` havia introduzido de propósito.**

## Performance

- **Duration:** ~75 min (Task 1 incluiu um checkpoint de arquitetura resolvido pelo orquestrador)
- **Tasks:** 3/3 completas
- **Files modified:** 3 (`fotoorganizer/repositories/media.py`, `tests/test_repository.py`, `webapp/src/App.tsx`)

## Accomplishments
- `_ACERVO_OU_REFERENCIA` — novo predicado no branch `tudo` de `_query`, substituindo o `select(MediaFile)` sem filtro (o bug em si).
- Rótulo do backend (`ALCANCES["tudo"]`) e tooltip do webapp reescritos, sem a promessa "tudo que o app conhece".
- Auditoria completa dos 8 caminhos de contagem do produto, com 1 achado nomeado e não corrigido (fora de escopo do BUG-03).

## Task Commits

Executadas em duas sessões (a primeira parou num checkpoint, resolvido pelo orquestrador antes de continuar):

1. **Task 1, tentativa 1 (RED com predicado errado)** — `d4b0880` (test) — **checkpoint, ver Deviations**
2. **Task 1, correção do orquestrador (CONTEXT.md/PLAN.md)** — `87c11a6` (docs, no branch do orquestrador)
3. **Merge da correção no worktree** — `aed99da` (chore)
4. **Task 1, RED corrigido** — `22aebf6` (test)
5. **Task 1, GREEN** — `b12ad7c` (feat)
6. **Task 2** — `c7c0733` (fix: rótulo + tooltip)
7. **Task 3** — esta auditoria, sem código (só este SUMMARY)

**Plan metadata:** commit deste SUMMARY, feito pelo orquestrador após o merge do worktree.

## Files Created/Modified
- `fotoorganizer/repositories/media.py` — `_ACERVO_OU_REFERENCIA` (novo), branch `else` de `_query` filtrado, comentário reescrito, `ALCANCES["tudo"]` reescrito.
- `tests/test_repository.py` — fixture `repo_com_testemunha` (4 registros) e 3 testes novos.
- `webapp/src/App.tsx` — tooltip do botão "Tudo" reescrito (1 linha).

## Decisions Made

**D-01 foi corrigida duas vezes nesta fatia** (ver `02-CONTEXT.md`, seção "Definição de Tudo", histórico completo):

1. Na discussão original (`/gsd:discuss-phase 2`), decidi "papel == ACERVO puro" — errado, viraria `_ACERVO`/`organizavel` se mal-lido.
2. O pattern-mapper (antes de planejar) corrigiu para "papel == ACERVO puro, não `_ACERVO`" — melhor, mas ainda incompleto.
3. **Durante a execução**, o checkpoint revelou que nem "papel puro" está certo: `_gravar_referencia` (`sources/importer.py`) sempre grava `papel=SINAL` pra referência externa (comentário no próprio código: "testemunha por definição"), então "papel==ACERVO puro" excluiria a referência do iCloud — revertendo a feature do commit `1b125f7` sem necessidade. A correção final: `or_(papel==ACERVO, arquivo_ausente==True)`.

Isso não é um problema de execução — é a razão de existir da regra de checkpoint: uma decisão de planejamento pode estar factualmente errada mesmo depois de duas revisões, quando ninguém leu o código de gravação real antes de travar o predicado.

## Deviations from Plan

### Checkpoint resolvido pelo orquestrador (não um auto-fix — decisão de arquitetura)

**1. [Rule 4 — conflito arquitetural] Predicado da Task 1 estava errado, contradizia o próprio tripwire que a Task exigia proteger**

- **Encontrado durante:** Task 1, implementação do GREEN.
- **Sintoma:** implementar `_PAPEL_ACERVO = papel == ACERVO` exatamente como o plano original mandava fazia `tests/test_sources_importer.py:428` falhar (`contar(alcance="tudo")` virava 0, não 1) — mas a Task também exigia, como critério de aceite, que esse arquivo **não fosse editado**.
- **Investigação:** o registro que aquele teste constrói (`ExternalAsset(caminho=None, ...)`) passa por `_gravar_referencia`, que grava `papel=MediaRole.SINAL` incondicionalmente (comentário: "Uma referência é testemunha por definição") — nunca `papel=ACERVO`. Uma migração dedicada (`0010_referencia_e_sempre_sinal.py`, 31/07/2026) já havia tornado a combinação `papel=ACERVO + arquivo_ausente=True` um estado inalcançável na prática. O teste em si vem do commit `1b125f7` (31/07/2026), que tornou essa referência visível em "Tudo" de propósito — o dono via 44.661 fotos do Apple Fotos virarem "(0)" na importação e chamou isso de "o sistema esquece".
- **Decisão:** não editar o teste (opção que o executor propôs mas não executou sozinho) nem reverter a feature do `1b125f7`. Em vez disso, o predicado foi ajustado para `or_(papel==ACERVO, arquivo_ausente==True)` — inclui acervo (qualquer) e referência externa sem arquivo, exclui só testemunha COM arquivo local (o caso real medido em `docs/AVALIACAO_UX.md` §C.2, 353.480 registros). Isso satisfaz as duas exigências ao mesmo tempo.
- **Arquivos modificados:** `.planning/phases/02-corre-o-de-dados-medidos/02-CONTEXT.md` e `02-01-PLAN.md` (correção documentada, commit `87c11a6` no branch do orquestrador), depois `fotoorganizer/repositories/media.py` e `tests/test_repository.py` (implementação, commits `22aebf6`/`b12ad7c`).
- **Verificação:** `tests/test_sources_importer.py:428-430` passam sem edição (`git diff --exit-code` limpo); 4 novos casos em `tests/test_repository.py` cobrem os dois tipos de testemunha separadamente; suíte completa 843/843.
- **Quem decidiu:** o orquestrador, após investigação própria (leitura direta de `_gravar_referencia`, da migração 0010 e do commit `1b125f7`) — não uma decisão unilateral do executor. O dono aprovou a resolução ("pode resolver") antes da investigação ser conduzida.

---

**Total deviations:** 1 (arquitetural, resolvida via checkpoint — não um auto-fix de execução)
**Impact on plan:** Sem isso, ou o BUG-03 ficaria mal resolvido (excluindo referência externa sem necessidade) ou o teste tripwire seria editado pra acomodar um predicado incompleto. A correção manteve os dois objetivos do produto (D-01 e a feature do `1b125f7`) intactos ao mesmo tempo.

## Issues Encountered
Nenhum outro além do checkpoint documentado acima.

## User Setup Required
Nenhum — mudança de backend/frontend, sem serviço externo.

## Auditoria D-03 — 8 caminhos de contagem

D-03 pediu verificação, não mudança. Nenhum destes 8 contadores foi alterado
nesta fase — só o comportamento de `contar`/`listar` (linhas 1-2) muda,
como consequência direta da Task 1.

| # | Caminho | Predicado usado | Classificação |
|---|---|---|---|
| 1 | `MediaRepository.contar(alcance="tudo")` — feed do `total` de `GET /api/midia` | `_ACERVO_OU_REFERENCIA` (via `_query`) | **muda** — exclui testemunha-com-arquivo, mantém referência sem arquivo |
| 2 | `MediaRepository.listar(alcance="tudo")` — feed dos itens da grade | `_ACERVO_OU_REFERENCIA` (via `_query`) | **muda** — mesmo predicado de #1 |
| 3 | `MediaRepository.linha_do_tempo(filters)` — feed do histograma por mês | `self._query(filters)` — herda o predicado de `alcance` recebido | **muda quando `alcance="tudo"`** — mesma consequência de #1, propagada por reuso de `_query` |
| 4 | `MediaRepository.estatisticas()` — feed de `GET /api/status` | `_ACERVO`/`_TESTEMUNHA` (`organizavel`/`~organizavel`) | **não muda** — não usa `_query` nem o novo predicado; intocado |
| 5 | `MediaRepository.panorama()` — feed de `GET /api/panorama` | `_ACERVO` (`organizavel`) | **não muda** — mesma razão de #4 |
| 6 | `MediaRepository.fontes_com_contagem()` — feed de `GET /api/fontes`, campo `fotos` | nenhum (conta TODAS as linhas por fonte via `outerjoin`) | **passa a divergir do total da grade, mas já era assim e já está justificado** — comentário explícito no código (linhas 495-498): "a contagem é do que a fonte CONHECE, não do que ela entrega para organizar" |
| 7 | `MediaRepository.arvore_de_pastas()` — campos `total`/`alcancaveis`, feed da árvore lateral | nenhum filtro de `papel` (conta todas as linhas sob a pasta) | **passa a divergir do total da grade, SEM justificativa registrada no código** — achado nomeado abaixo |
| 8 | `GET /api/funil` (`levantar_funil` → `inventario.py::funil`/`levantar`) | computação própria, independente de `_query`/`_ACERVO` | **não muda** — módulo `inventario.py` não referencia `_ACERVO`, `_TESTEMUNHA` nem `_query` |

### Achado nomeado (não corrigido nesta fase): `arvore_de_pastas`

`arvore_de_pastas()` (`fotoorganizer/repositories/media.py:389-461`) conta
`total` e `alcancaveis` por pasta somando TODAS as linhas sob o prefixo,
sem filtrar por `papel`. A partir desta fase, uma pasta com miniatura/
derivado interno (`papel=SINAL` com arquivo local) vai mostrar `total`
maior que o que aparece se o usuário clicar nela com `alcance=tudo` —
divergência do mesmo tipo do achado 8/D-065 em `CONCERNS.md`, mas **sem**
o comentário de justificativa que `fontes_com_contagem` já tem. Não é
regressão desta fase (o comportamento de `arvore_de_pastas` não mudou),
mas a lacuna fica mais visível agora que "tudo" ficou mais preciso.
Registrado para fase futura — fora do escopo de BUG-03, que fala só do
filtro "Tudo" da Biblioteca (não da árvore de pastas lateral).

## Next Phase Readiness
- BUG-03 fechado, sem dependência criada para a Fase 3 (Revisão acessível e consistente).
- Achado `arvore_de_pastas` acima é candidato a item futuro de "correção de
  dados medidos", não bloqueia nada do roadmap atual.
- Catálogo de produção segue zerado (reset em 2026-08-16) — verificação
  manual desta fase (checkpoint `<human-check>` do plano) fica pendente
  até a próxima varredura completa; não bloqueia o fechamento da fase
  porque a verificação decisiva é automatizada (testes + `scripts/verificar.sh`).

---
*Phase: 02-correção-de-dados-medidos*
*Completed: 2026-08-16*
