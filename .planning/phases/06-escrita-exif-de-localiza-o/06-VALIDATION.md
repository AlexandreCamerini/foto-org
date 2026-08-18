---
phase: 6
slug: escrita-exif-de-localiza-o
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-18
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Extracted from `06-RESEARCH.md` § Validation Architecture per plan-checker
> finding (Dimension 8 blocker, 2026-08-18) — content unchanged, moved to
> the dedicated gate artifact.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest, `pyproject.toml [tool.pytest.ini_options]`, `testpaths = ["tests"]` |
| **Framework (frontend)** | vitest, `npm test` → `vitest run`, per `webapp/package.json` |
| **Config file** | `pyproject.toml` (backend), `webapp/vitest.config.*` (frontend) |
| **Quick run command (backend)** | `.venv/bin/pytest tests/test_exif_write.py -x` |
| **Quick run command (frontend)** | `cd webapp && npm test -- EscritaExif` |
| **Full suite command** | `.venv/bin/pytest` and `cd webapp && npm test` |
| **Estimated runtime** | ~5s quick (backend), ~5s quick (frontend); full suite per existing baseline |

---

## Sampling Rate

- **After every task commit:** backend quick-run command; frontend `npm test -- EscritaExif`.
- **After every plan wave:** full `pytest` + full `npm test`.
- **Before `/gsd:verify-work`:** full suite must be green, plus D-03's standalone
  `scripts/testar_escrita_exif.py` run once against real (disposable-copy) samples,
  result logged to `docs/DECISOES.md` before the format allowlist is considered final.
- **Max feedback latency:** <10s (quick commands are scoped to the new test file/component only).

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| EXIF-01 | Dry-run lists empty fields per file, nothing written before approval | unit | `pytest tests/test_exif_write.py::test_dry_run_nao_escreve -x` | ❌ Wave 0 |
| EXIF-02 | Only empty fields get written; pre-filled fields skip with visible reason | unit | `pytest tests/test_exif_write.py::test_pula_campo_preenchido -x` | ❌ Wave 0 |
| EXIF-03 | Full-tag diff verification incl. scaffolding-tag allowlist; partial failure logged with which tags landed | unit | `pytest tests/test_exif_write.py::test_diff_detecta_falha_parcial -x` | ❌ Wave 0 |
| EXIF-04 | Never writes non-location tags, proven by full tag dump comparison | unit | `pytest tests/test_exif_write.py::test_nunca_escreve_fora_de_localizacao -x` | ❌ Wave 0 |
| EXIF-05 | Unsupported format appears as explicit dry-run line + sidecar XMP offer | unit + integration | `pytest tests/test_exif_write.py::test_formato_nao_suportado_oferece_sidecar -x` | ❌ Wave 0 |
| D-02 (checkbox per row) | Per-item deselect before confirming, batch approval otherwise | frontend unit | `cd webapp && npm test -- EscritaExif` | ❌ Wave 0 (no existing checkbox component to extend — Pitfall 6) |
| D-07 (sync detection) | Path inside iCloud Drive/CloudStorage flagged with warning | unit | `pytest tests/test_exif_write.py::test_detecta_pasta_sincronizada -x` | ❌ Wave 0 |
| Pitfall 5 fix (AuditLog FK) | Exif-write audit rows never populate `plan_id` with a non-`operation_plans` id | regression | `pytest tests/test_exif_write.py::test_audit_log_nao_viola_fk -x` | ❌ Wave 0 |

*Status: all ⬜ pending until Wave 1 lands — this is the pre-execution contract, not a live run log.*

---

## Wave 0 Requirements

- [ ] `tests/test_exif_write.py` — covers EXIF-01..05 (new file, no existing equivalent)
- [ ] `tests/fixtures.py` extension — reuse `make_jpeg(gps=...)` (already supports the
      "already has GPS, must skip" case; no new fixture needed beyond confirming coverage)
- [ ] `webapp/src/components/EscritaExif.test.tsx` — new component, new test file, no
      existing checkbox-per-row component to extend (Pitfall 6)
- [ ] `scripts/testar_escrita_exif.py` — D-03's empirical script itself; not a pytest
      target, but its existence and one real run against real (copied) samples is a
      phase-gate precondition per D-03/D-04, same as `calibrar_raio_incerteza.py` was
      for D-074
- [ ] Migration for `ExifWritePlan`/`ExifWriteItem` tables (Alembic, new revision) —
      needs a regression test asserting `PRAGMA foreign_keys=ON` doesn't reject
      legitimate inserts with `plan_id=NULL` (Pitfall 5)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-tool read-back of written tags | Underlying premise of D-075 (EXIF over sidecar for interoperability) | No Lightroom/Photos.app available to script against; needs the dono's actual tools | See `06-09-PLAN.md` Task 3 — blocking human checkpoint, dono opens one written test file in Lightroom/Photos.app/Finder and confirms location shows up |
| `_original` backup cleanup policy in practice | A3 in `06-RESEARCH.md` Assumptions Log | Policy synthesis (delete only after verified success) needs the dono to see it happen once, not just read the design | `06-09-PLAN.md` Task 2, step 8 — dono confirms `_original` is absent after a successful write and present after a rejected/failed one |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (confirmed by plan-checker, 2026-08-18)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (confirmed by plan-checker)
- [x] Wave 0 covers all MISSING references (5 items above, all traced to a specific plan)
- [x] No watch-mode flags (`-x` and `vitest run`, not `--watch`)
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-18 (plan-checker verified; content sourced verbatim from `06-RESEARCH.md` § Validation Architecture, no new claims introduced)
