---
phase: 05-prepara-o-para-lan-amento
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, sqlite, indexing, query-planner, pragma]

# Dependency graph
requires: []
provides:
  - "9 índices novos (migração 0018) em media_files.pasta, media_files.location_id, suggestions.media_id, operation_items.plan_id/media_id, audit_log.plan_id, duplicate_members.media_id, face_occurrences.media_id/person_id"
  - "4 índices de drift reconciliados só no modelo (gps_estimado_de_id, tipo_imagem, tipo_confirmado, sources.volume_id)"
  - "PRAGMA case_sensitive_like=ON habilitado em toda conexão SQLite"
  - "tests/test_indices.py cobrindo EXPLAIN QUERY PLAN, existência de índice e regressão de caixa"
affects: [database, repositories, operations, performance-baseline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Índice com comentário inline citando consumidor real (arquivo:linha), mesma convenção de MediaFile.__table_args__ existente"
    - "Migração Alembic com um op.batch_alter_table por tabela, downgrade simétrico em ordem inversa"
    - "Asserção de query plan (EXPLAIN QUERY PLAN sobre a consulta real compilada) em vez de checar só existência de índice em sqlite_master"

key-files:
  created:
    - tests/test_indices.py
    - fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py
  modified:
    - fotoorganizer/models/catalog.py
    - fotoorganizer/models/inference.py
    - fotoorganizer/models/operations.py
    - fotoorganizer/models/duplicates.py
    - fotoorganizer/models/people.py
    - fotoorganizer/database/engine.py

key-decisions:
  - "Um Index() sozinho em MediaFile.pasta não faz o SQLite usar o índice para LIKE 'prefixo/%' — precisou de PRAGMA case_sensitive_like=ON no hook de conexão (RESEARCH.md Pitfall 3, verificado empiricamente via EXPLAIN QUERY PLAN antes e depois)"
  - "4 índices já existiam no banco (migrações 0005/0006/0007/0011) sem espelho no modelo — reconciliados só no arquivo de modelo, sem migração nova, para não abortar upgrade_to_head() com índice duplicado"
  - "FaceEmbedding.person_id, MediaTag.tag_id e Trip.location_id ficam fora da migração 0018 por falta de consumidor real (grep não achou WHERE/join), seguindo o precedente já documentado em catalog.py (D-072)"

patterns-established:
  - "Todo Index() novo carrega comentário citando arquivo:linha do consumidor real, nunca 'pode ser útil'"
  - "Teste de índice em coluna LIKE-consultada afirma o plano de consulta compilado da função real, não SQL reescrito à mão nem existência de índice isolada"

requirements-completed: [LANC-02]

duration: ~35min
completed: 2026-08-17
---

# Phase 5 Plan 01: Índices de FK ausentes Summary

**9 índices de FK ausentes com consumidor real citado, 4 índices de drift reconciliados no modelo, e `PRAGMA case_sensitive_like=ON` — sem essa última linha, `ix_media_files_pasta` existia e o filtro de pasta continuava em `SCAN media_files`.**

## Performance

- **Duration:** ~35 min (inclui criação de `.venv` próprio do worktree)
- **Tasks:** 3/3
- **Files modified:** 8 (2 criados, 6 modificados)

## Accomplishments

- Fechado o critério 2 da Fase 5 ("consultas por prefixo de pasta usam índice, não table scan"), provado por `EXPLAIN QUERY PLAN` real sobre a função `_sob_a_pasta`, não por existência de índice em `sqlite_master`.
- Achado de maior risco do plano confirmado empiricamente: um `Index("ix_media_files_pasta", "pasta")` sozinho **não** basta — SQLite só reescreve `LIKE 'prefixo/%'` em range scan com `PRAGMA case_sensitive_like=ON` habilitado na conexão. Sem essa segunda linha, o teste teria passado na existência do índice e falhado silenciosamente no critério real.
- Drift de 4 índices (existentes no banco desde 2026, ausentes do modelo ORM) reconciliado sem quebrar `upgrade_to_head()`.
- Varredura de segurança de todo `.like`/`.not_like`/`.ilike` do codebase confirmada por leitura direta das fontes (não só resumo do RESEARCH.md) antes de tocar o PRAGMA — achou um terceiro par de usos (`repositories/inventario.py:190,207`) não citado no RESEARCH.md, mesmo padrão seguro (`%://%`, sem letras, curinga à esquerda).

## Task Commits

1. **Task 1: Teste de plano de consulta, existência de índice e regressão de caixa** - `8b132ca` (test) — RED esperado: 10 falhas de 16 testes parametrizados/diretos.
2. **Task 2: Declarações de Index nos modelos + migração 0018** - `383e247` (perf) — 13 índices no schema migrado do zero; `pasta` ainda em SCAN (esperado, falta a Task 3).
3. **Task 3: PRAGMA case_sensitive_like=ON e fechamento do critério de aceite** - `64f7f38` (perf) — `tests/test_indices.py` inteiro verde; `scripts/verificar.sh --rapido` verde (860 testes backend + 19/19 benchmark de agrupamento).

## Files Created/Modified

- `tests/test_indices.py` - EXPLAIN QUERY PLAN sobre `_sob_a_pasta`, existência dos 13 índices, guarda de busca insensível a caixa, não-vazamento de pasta irmã
- `fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py` - 9 `create_index`/`drop_index`, docstring justificando cada índice e a exclusão das 3 colunas sem consumidor
- `fotoorganizer/models/catalog.py` - 6 `Index()` novos em `MediaFile.__table_args__` (2 novos + 4 drift) e primeiro `__table_args__` de `Source`
- `fotoorganizer/models/inference.py` - `Index("ix_suggestions_media_id", "media_id")`
- `fotoorganizer/models/operations.py` - import `Index`; `__table_args__` novo em `OperationItem` e `AuditLog`
- `fotoorganizer/models/duplicates.py` - import `Index`; `Index("ix_duplicate_members_media_id", "media_id")`
- `fotoorganizer/models/people.py` - import `Index`; `__table_args__` novo em `FaceOccurrence` (não em `FaceEmbedding`, deliberado)
- `fotoorganizer/database/engine.py` - `cursor.execute("PRAGMA case_sensitive_like=ON")` em `_set_sqlite_pragmas`

## Decisions Made

- Enumeração de LANC-02 seguiu a lista já fechada em RESEARCH.md/PATTERNS.md (9 novos + 4 drift + 3 exclusões), sem desvio.
- `PRAGMA case_sensitive_like=ON` foi a opção adotada (não `GLOB`) — menor diff, mesmo resultado, `_sob_a_pasta` intocada (`grep -c "GLOB" fotoorganizer/repositories/media.py` = 0).

## Deviations from Plan

None — plano executado exatamente como escrito. O único ajuste foi cosmético: a primeira versão do docstring da migração 0018 continha a palavra `create_index` numa frase explicativa, inflando o grep de contagem de 9 para 10; reescrita para `criar índice` antes de commitar, sem mudar comportamento.

## Issues Encountered

- Worktree não tinha `.venv` próprio (esperado — cada worktree precisa do seu, per memória do projeto). Criado com Python 3.12 e `pip install -e ".[dev,xmp,apple]"` antes de rodar qualquer teste.
- `git merge-base` no início da execução mostrou HEAD já correto após o `worktree_branch_check` padrão; nenhuma surpresa além da criação do venv.

## User Setup Required

None - nenhuma configuração de serviço externo.

## Next Phase Readiness

- Critério 2 da Fase 5 fechado e verificável por `tests/test_indices.py`.
- `scripts/verificar.sh --rapido` verde (860 testes + benchmark 19/19); os passos de UI web (vitest/build) foram pulados por design do próprio script em modo `--rapido` — não bloqueiam este plano, mas ficam para o portão de fim de fase junto dos outros LANC.
- Nenhum bloqueio identificado para os demais planos da Fase 5 (LANC-01 empacotamento, LANC-03 onboarding, LANC-04 baseline de performance) — este plano não tocou nenhum arquivo compartilhado com eles.

## Self-Check: PASSED

- FOUND: tests/test_indices.py
- FOUND: fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py
- FOUND: .planning/phases/05-prepara-o-para-lan-amento/05-01-SUMMARY.md
- FOUND commit: 8b132ca (test)
- FOUND commit: 383e247 (perf)
- FOUND commit: 64f7f38 (perf)
- FOUND commit: 07149e2 (docs metadata)

---
*Phase: 05-prepara-o-para-lan-amento*
*Completed: 2026-08-17*
