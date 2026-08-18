---
phase: 06-escrita-exif-de-localiza-o
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, sqlite, exif, foreign-key]

# Dependency graph
requires:
  - phase: 05-lancamento-v1
    provides: models/operations.py como template estrutural (OperationPlan/OperationItem/AuditLog), engine com PRAGMA foreign_keys=ON, convenção de migração Alembic (docstring-como-justificativa)
provides:
  - "ExifWritePlan/ExifWriteItem persistidos em exif_write_plans/exif_write_items, paralelos a operation_plans/items mas sem herdar deles"
  - "Status e motivo independentes por campo (GPS/cidade/país) em ExifWriteItem — suporta falha parcial (EXIF-03)"
  - "Padrão validado e testado de reuso de AuditLog com plan_id=None + id do plano em detalhe JSON, evitando a FK real de operation_plans.id"
  - "Migração 0019 (upgrade/downgrade testados) e export completo em models/__init__.py"
affects: [06-02, 06-03, 06-04, 06-05, 06-06, exif_write/planner.py, exif_write/executor.py, repositories/exif_write.py, server/app.py rotas /api/exif]

# Tech tracking
tech-stack:
  added: []
  patterns: ["modelo com status por campo em vez de status único por item, quando o subprocesso subjacente (exiftool) não é atômico por tag", "AuditLog compartilhado entre domínios via campo JSON detalhe, sem alterar esquema, quando a coluna FK dedicada não serve o novo domínio"]

key-files:
  created:
    - fotoorganizer/models/exif_write.py
    - fotoorganizer/database/migrations/versions/0019_tabelas_de_escrita_exif.py
    - tests/test_exif_write_models.py
  modified:
    - fotoorganizer/models/__init__.py

key-decisions:
  - "AuditLog é reusado como está (nenhuma coluna nova); plan_id fica sempre None nas linhas de escrita EXIF e o id do ExifWritePlan viaja em detalhe JSON, porque AuditLog.plan_id tem FK ativa para operation_plans.id (RESEARCH.md Pitfall 5, confirmado por teste com IntegrityError)."
  - "Status por campo (status_gps/status_cidade/status_pais) em vez de um status único no item, porque exiftool não é atômico por tag dentro de uma invocação — falha parcial é resultado real (EXIF-03)."
  - "hash_pre/hash_pos documentados no código como fato de auditoria, nunca critério de aprovação — quem aprova é o diff de tags, tratado em plano futuro da fase."

patterns-established:
  - "Modelo paralelo sem herança: ExifWritePlan/ExifWriteItem espelham a forma de OperationPlan/OperationItem mas não compartilham tabela, FK nem lógica — domínios de escrita e de cópia física ficam desacoplados mesmo sendo estruturalmente semelhantes."

requirements-completed: [EXIF-01, EXIF-03, EXIF-05]

# Metrics
duration: 24min
completed: 2026-08-18
---

# Phase 6 Plan 01: Modelo de dados da escrita EXIF Summary

**`ExifWritePlan`/`ExifWriteItem` com status independente por campo (GPS/cidade/país) e `AuditLog` reusado com `plan_id=None` para não colidir com a FK real de `operation_plans.id`.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-08-18T08:23:00-03:00 (aprox.)
- **Completed:** 2026-08-18T08:27:47-03:00
- **Tasks:** 3
- **Files modified:** 4 (3 criados, 1 modificado)

## Accomplishments
- Modelo `ExifWritePlan`/`ExifWriteItem` criado, estruturalmente paralelo a `OperationPlan`/`OperationItem` mas sem herança nem relacionamento com eles.
- Status e motivo independentes por campo (GPS, cidade, país) em `ExifWriteItem`, atendendo EXIF-03 (falha parcial).
- Migração Alembic `0019` criando `exif_write_plans`/`exif_write_items` e os dois índices declarados no modelo; `upgrade`/`downgrade` testados numa base descartável.
- Regressão que trava a armadilha da FK de `AuditLog.plan_id` (Pitfall 5): um teste prova que `plan_id=None` + id no `detalhe` funciona, outro prova que usar o id do `ExifWritePlan` direto em `plan_id` levanta `IntegrityError`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Modelo ExifWritePlan/ExifWriteItem com status por campo** - `b6b05e1` (feat)
2. **Task 2: Migração Alembic 0019 e export em models/__init__.py** - `469e6d2` (feat)
3. **Task 3: Teste de esquema e regressão da FK de AuditLog** - `8b18cb8` (test)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified
- `fotoorganizer/models/exif_write.py` - `ExifWritePlan`, `ExifWriteItem`, `ExifWriteStatus`, `CampoStatus`
- `fotoorganizer/database/migrations/versions/0019_tabelas_de_escrita_exif.py` - migração Alembic que cria as duas tabelas e os dois índices
- `fotoorganizer/models/__init__.py` - exporta os 4 novos nomes
- `tests/test_exif_write_models.py` - 4 testes: roundtrip, FK de AuditLog (caso certo e caso que deve falhar), padrões do item

## Decisions Made
- `AuditLog` não ganhou coluna nova; a integração com o domínio de escrita EXIF é só via `detalhe` JSON. Justificativa completa no docstring de `exif_write.py` e no docstring da migração 0019.
- Enum `CampoStatus` distingue `PULADO` (campo já preenchido, não sobrescrito) de `SEM_VALOR` (motor não inferiu nada) — os dois viram cópias diferentes na UI (plano futuro).
- `incluido` nasce `True` para itens normais; a decisão de nascer `False` para linha de sidecar (D-06, opt-in) fica para o planner (plano futuro), não para o modelo em si — o modelo só documenta a intenção no comentário.
- **REQUIREMENTS.md NÃO foi marcado como completo para EXIF-01/03/05.** O frontmatter `requirements-completed` acima copia o campo `requirements` do plano (convenção do template), mas EXIF-01, EXIF-03 e EXIF-05 também aparecem nos planos 06-03, 06-04, 06-05, 06-06, 06-08 e 06-09 — este plano só entrega a fundação de esquema, não o comportamento fim-a-fim que o texto de cada requisito descreve (dry-run aprovável, escrita verificada por diff de tags, oferta de sidecar visível). Rodei `requirements.mark-complete` por engano e revertido antes do commit final; os checkboxes ficam `[ ]` até o plano que efetivamente fecha cada requisito.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `fotoorganizer.models.exif_write` está pronto para `exif_write/planner.py`, `exif_write/executor.py` e `repositories/exif_write.py` (planos seguintes da Fase 6) consumirem.
- Nenhum arquivo de `fotoorganizer/operations/` ou `fotoorganizer/models/operations.py` foi tocado — confirmado por `git diff --name-only`.
- Suíte completa (`.venv/bin/python -m pytest -q`) segue verde: 871 passed.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created files found on disk; all 3 task commits (b6b05e1, 469e6d2, 8b18cb8) found in git log.
