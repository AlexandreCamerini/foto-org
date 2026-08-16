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
- **D-01:** "Tudo" passa a significar `papel == MediaRole.ACERVO`
  (alcançável ou não) — mesmo critério de `_ACERVO`/`organizavel` já
  usado em `organizaveis`/`faltantes`, só sem o filtro de fonte
  disponível. Testemunha (`papel == SINAL`) nunca aparece na grade, em
  nenhum dos três filtros (`tudo`/`organizaveis`/`faltantes`) — decisão
  do dono, 2026-08-16, resolvendo a contradição entre o comentário de
  `_query()` ("Testemunhas ficam fora... de qualquer filtro") e o rótulo
  de `ALCANCES["tudo"]` ("tudo que o app conhece", que sugeria incluir
  testemunha).
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

### Claude's Discretion
- Redação exata do novo rótulo de `ALCANCES["tudo"]` (ver D-02).
- Se a mudança de `_query()` deve reutilizar `_ACERVO` diretamente ou uma
  pequena função nomeada — desde que o resultado seja idêntico e o teste
  cubra o caso testemunha-excluída-de-tudo.

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
  `_acervo_ao_alcance`) — os predicados já existem, só faltam ser
  aplicados ao branch `tudo`.
- `fotoorganizer/repositories/media.py:196-204` (`_query`, ponto exato da
  mudança — `if/elif/else` de `filters.alcance`).
- `fotoorganizer/repositories/media.py:68-72` (`ALCANCES`, dict de
  rótulos — D-02).
- `fotoorganizer/repositories/media.py:569-585` (`estatisticas`) —
  referência de como `_ACERVO`/`_TESTEMUNHA` já são usados separadamente,
  não precisa mudar (D-03).
- `fotoorganizer/models/catalog.py:250-275` (`organizavel` hybrid
  property) — define `papel == MediaRole.ACERVO` + arquivo presente/
  online; `_ACERVO` em `media.py` é este mesmo critério antes do filtro
  de fonte disponível.

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
