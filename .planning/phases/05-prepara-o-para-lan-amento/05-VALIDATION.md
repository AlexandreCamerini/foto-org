---
phase: 5
slug: prepara-o-para-lan-amento
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-17
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, `pyproject.toml` / `testpaths = ["tests"]`); vitest (webapp, `webapp/package.json` `"test": "vitest run"`) |
| **Config file** | `pyproject.toml` (pytest); `webapp/vite.config.ts` (vitest, inline config) |
| **Quick run command** | `.venv/bin/python -m pytest -q --no-header` (backend); `cd webapp && npm test` (frontend) |
| **Full suite command** | `scripts/verificar.sh` (pytest + `scripts/avaliar_agrupamento.py` benchmark + vitest + `npm run build`) |
| **Estimated runtime** | ~90 seconds |

**Note:** `scripts/verificar.sh` does not run `cargo tauri build` or any Rust check — LANC-01 verification is manual, outside this script's coverage.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest -q` for any LANC-02 model/migration change; `cd webapp && npm test` for any webapp change.
- **After every plan wave:** `scripts/verificar.sh` (full backend+frontend suite) — does not cover LANC-01 (native build) or LANC-03/LANC-04 (manual/one-time) by design.
- **Before `/gsd:verify-work`:** Full suite must be green, plus the three non-automatable verifications (LANC-01 native launch test, LANC-03 uninstructed user test, LANC-04 documented measurement run) each explicitly checked off.
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-XX-XX | TBD | TBD | LANC-01 | — | `.app` builds, opens on fresh catalog, scans fixtures, shows grid, leaves no orphan Python process on close | manual | `cd src-tauri && cargo tauri build`, then manual launch + process check | N/A — manual, no existing test | ⬜ pending |
| 05-XX-XX | TBD | TBD | LANC-02 | — | `pasta` and other enumerated FK columns use an index (`SEARCH`, not `SCAN`) after migration | integration (DB-level) | `EXPLAIN QUERY PLAN` assertion against migrated test DB | ❌ Wave 0 — `tests/test_indices.py` needed | ⬜ pending |
| 05-XX-XX | TBD | TBD | LANC-03 | — | First-time user reaches populated grid without documentation | manual UAT (uninstructed user test, per D-06) | None automatable — requirement is about an unguided human | N/A by design | ⬜ pending |
| 05-XX-XX | TBD | TBD | LANC-04 | — | Baseline metrics measured and documented in `docs/PERFORMANCE.md` | manual/scripted one-time measurement | New timing script for suggestion/duplicate-detection, mirroring `cmd_bench` pattern | ❌ Wave 0 — new script needed | ⬜ pending |

*Task IDs filled in by the planner once PLAN.md files exist.*

---

## Wave 0 Requirements

- [ ] `tests/test_indices.py` — asserts `EXPLAIN QUERY PLAN` uses `SEARCH ... USING INDEX` (not `SCAN`) for the `pasta` prefix query post-migration (LANC-02).
- [ ] Timing script for `SuggestionEngine.gerar()` / `DuplicateDetector.detectar()` against real data (LANC-04) — direct-call CLI script recommended per RESEARCH.md Open Question 2, for reproducibility.

*No Wave 0 gap for LANC-01/LANC-03 — both are inherently manual verifications per the phase's own success criteria (D-02, D-06).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| `.app` signed/notarized, passes Gatekeeper, no orphan process on quit | LANC-01 | Native app lifecycle — not automatable in this stack; `scripts/verificar.sh` does not build/sign the Tauri bundle | `cd src-tauri && cargo tauri build`; launch the built `.app`; quit it; confirm via `ps aux \| grep fotoorganizer` (or `~/.claude/scripts/portas.py`) that no orphan Python process remains |
| First-time user reaches populated grid unassisted | LANC-03 | Requirement is explicitly about an unguided human (D-06), not a scripted click-path | Recruit an uninstructed user (or simulate cold-start), observe them add a source/folder and reach a populated grid with zero documentation |
| Documented performance baseline | LANC-04 | One-time measurement against a representative catalog, not a repeatable pytest assertion | Run the new timing script against a freshly-rescanned representative catalog; record indexing rate, suggestion generation time, duplicate detection time in `docs/PERFORMANCE.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_indices.py`, timing script)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
