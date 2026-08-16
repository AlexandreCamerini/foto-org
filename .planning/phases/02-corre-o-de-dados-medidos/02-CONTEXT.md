# Phase 2: Correção de dados medidos - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

O filtro "Tudo" (`alcance=tudo`) da Biblioteca passa a distinguir `SINAL`
(testemunha) de `ACERVO` — hoje `repositories/media.py:203-204` devolve
`select(MediaFile)` sem `WHERE` nenhum, misturando os dois. Esta fase
corrige só isso (BUG-03).

Escopo reduzido nesta sessão: dos 4 defeitos medidos originalmente em
`docs/AVALIACAO_UX.md` §C (2026-08-06), BUG-01 (`5c7b36d`), BUG-02
(`VIDEO_EXTENSIONS`) e BUG-04 (`engine.py:713-725`) já estavam corrigidos
no código antes desta sessão — confirmado por leitura direta + testes
existentes (`tests/test_discovery.py`, `tests/test_suggestion_engine.py`)
em 2026-08-16, e movidos para `PROJECT.md` § Validated. Só BUG-03 segue
aberto.

</domain>

<decisions>
## Implementation Decisions

### Definição de "Tudo"
- **D-01 [corrigido pelo executor durante a execução, 2026-08-16 —
  segunda correção, ver histórico completo em `02-01-SUMMARY.md`]:**
  "Tudo" inclui `papel == MediaRole.ACERVO` (qualquer, alcançável ou não)
  **OU** `papel == MediaRole.SINAL com arquivo_ausente == True`
  (referência externa pura — ex. Apple Fotos iCloud-only, volume do
  Lightroom desmontado). Exclui só `SINAL` com arquivo local real
  (miniatura/derivado dentro de pacote — `.photoslibrary`/`.aplibrary`/
  `.lrdata`), que é o caso que o BUG-03 de fato reclama (353.480
  registros medidos em `docs/AVALIACAO_UX.md` §C.2).

  **Por que não é `papel == ACERVO` puro** (versão anterior desta
  decisão, corrigida): o teste `tests/test_sources_importer.py:398-433`
  (`test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel`)
  não testa um registro `ACERVO` — testa uma **referência externa**
  (`ExternalAsset(caminho=None, ...)` → `_gravar_referencia`, que grava
  `papel = MediaRole.SINAL` explicitamente, comentário "Uma referência é
  testemunha por definição"). Esse teste existe desde o commit
  `1b125f7` (31/07/2026, "a Biblioteca mostra o que o app conhece, não
  só o que ele organiza") — feature deliberada: o dono viu 44.661 fotos
  do Apple Fotos (todas iCloud-only, sem arquivo local) virarem "(0)" na
  importação e descreveu isso como "o sistema esquece". Excluir toda
  `SINAL` de "Tudo" (a versão anterior desta decisão) reverteria essa
  feature sem necessidade — o achado do BUG-03 é sobre miniatura/
  derivado com arquivo real (a maioria dos 353.480), não sobre
  referência sem arquivo (~99 mil, um subconjunto bem menor).

  **Tripwire de teste** (agora correto, sem contradição): `tests/
  test_sources_importer.py:428-430` continuam passando (`tudo`==1,
  `faltantes`==1, `organizaveis`==0) **sem editar o arquivo** — a
  referência externa (SINAL + sem arquivo) permanece contada em "tudo"
  E em "faltantes" (não mudou), só sai de "organizaveis" (não mudou).
- **D-02:** O rótulo `ALCANCES["tudo"]` (`repositories/media.py:70`,
  hoje `"tudo que o app conhece"`) precisa mudar para não prometer o que
  não entrega mais — ex. `"todo o acervo, alcançável ou não"`. Redação
  exata fica a critério do planner/executor, desde que não use "conhece"
  (ambíguo com testemunha) nem repita a palavra "acervo" duas vezes na
  mesma frase.
- **D-03:** `estatisticas()` (`repositories/media.py:569-585`) já separa
  `total` (`_ACERVO`) de `referencias` (`_TESTEMUNHA`) como contagens
  distintas — não mexer nisso, já está consistente com a decisão D-01.
  Verificar (não é preciso mudar) que nenhuma contagem de sidebar/painel
  em `server/app.py` ou no webapp usa o resultado de `alcance=tudo` sem
  filtro para compor um número que agora vai mudar — evitar reintroduzir
  o padrão "dois números discordando" que já mordeu o projeto duas vezes
  (D-065, achado 8 do CONCERNS.md).

- **D-04:** `webapp/src/App.tsx:341-347` tem um tooltip hardcoded pro
  botão "Tudo" com o mesmo problema de redação do D-02 ("tudo que o app
  conhece, inclusive sem arquivo local") — string independente do dict
  `ALCANCES` do backend (não é buscada via API). Corrigir também, mesmo
  texto/espírito do D-02, já que é a mesma causa raiz e o mesmo esforço
  de uma linha. Não é mudança de componente/visual, só texto — não conta
  como "UI nova" pro propósito do `<domain>` desta fase.

### Claude's Discretion
- Redação exata do novo rótulo de `ALCANCES["tudo"]` e do tooltip do
  `App.tsx` (ver D-02/D-04) — mesma restrição (sem "conhece", sem
  "acervo" repetido).
- Se a mudança de `_query()` introduz uma função nomeada nova
  (`_e_acervo()` ou similar) ou usa `MediaFile.papel ==
  MediaRole.ACERVO` inline — desde que seja o critério puro de papel
  (ver D-01), não `_ACERVO`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Achado original e estado atual
- `docs/AVALIACAO_UX.md` §C.2 — achado original do BUG-03 (medido
  2026-08-06, ainda válido pra este item específico).
- `docs/DECISOES.md` D-024/D-068 — invariante de rebaixamento de
  testemunha (nunca some, nunca vira acervo) e "organizável exige fonte
  respondendo" — base conceitual de `_ACERVO`/`_TESTEMUNHA`.
- `.planning/codebase/CONCERNS.md` — achado 8/D-065 (padrão "dois números
  discordando"), relevante pra D-03.

### Código existente a reaproveitar
- `fotoorganizer/repositories/media.py:40-64` (`_ACERVO`, `_TESTEMUNHA`,
  `_acervo_ao_alcance`) — **NÃO usar `_ACERVO` pro branch `tudo`** (ver
  D-01) — mais estrito que o critério decidido. Referenciado aqui só pra
  contraste, não como reaproveitamento direto.
- `fotoorganizer/repositories/media.py:196-204` (`_query`, ponto exato da
  mudança — `if/elif/else` de `filters.alcance`).
- `fotoorganizer/repositories/media.py:68-72` (`ALCANCES`, dict de
  rótulos — D-02).
- `fotoorganizer/repositories/media.py:569-585` (`estatisticas`) —
  referência de como `_ACERVO`/`_TESTEMUNHA` já são usados separadamente,
  não precisa mudar (D-03).
- `fotoorganizer/models/catalog.py:250-275` (`organizavel` hybrid
  property) — define o critério de `_ACERVO` (`papel == MediaRole.ACERVO`
  **+** `not arquivo_ausente` **+** `not arquivo_offline`) — mais estrito
  que o `papel` puro que D-01 exige. Ver tripwire de teste em D-01.
- `webapp/src/App.tsx:341-347` — tooltip do botão "Tudo" (D-04).
- `tests/test_sources_importer.py:398-433` — teste existente que trava o
  comportamento correto de `alcance="tudo"` com registro ACERVO sem
  arquivo (tripwire do D-01).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ACERVO`/`_TESTEMUNHA` (`repositories/media.py:40-42`): predicados
  SQLAlchemy já prontos, só precisam ser aplicados no branch que falta.

### Established Patterns
- `organizaveis`/`faltantes` já filtram por `_acervo_ao_alcance()`/sua
  negação — `tudo` deveria seguir o mesmo estilo de filtro explícito em
  vez de "sem filtro nenhum".
- Testemunha é sempre um conceito de exclusão da grade visível — nunca
  aparece em Revisão, Viagens ou Operações; a mudança estende essa regra
  pro terceiro filtro que ainda não a seguia.

### Integration Points
- `GET /api/midia` (grade principal) e qualquer endpoint que reuse
  `MediaRepository.listar`/`contar`/`_query` com `alcance=tudo` — mudança
  é no repositório, propaga automaticamente pros consumidores.

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência visual — mudança é de filtro de backend, sem UI nova
(só o texto do rótulo do seletor já existente, D-02).

</specifics>

<deferred>
## Deferred Ideas

- Nenhuma — discussão ficou dentro do escopo restrito desta fase
  (BUG-03 apenas).

</deferred>

---

*Phase: 02-correção-de-dados-medidos*
*Context gathered: 2026-08-16*
