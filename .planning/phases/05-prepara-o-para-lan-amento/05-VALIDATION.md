---
phase: 5
slug: prepara-o-para-lan-amento
status: approved
nyquist_compliant: true
wave_0_complete: false  # tests/test_indices.py (05-01 T1) e scripts/medir_baseline_producao.py (05-04 T1) são as tasks que fecham
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
| 05-01-01 | 05-01 | 1 | LANC-02 | T-05-01/02 | `EXPLAIN QUERY PLAN` da consulta real de `_sob_a_pasta` mostra SEARCH; busca `.ilike` segue insensível a caixa | integration (DB-level) | `.venv/bin/python -m pytest tests/test_indices.py -q` | ❌ Wave 0 — criado nesta task | ⬜ pending |
| 05-01-02 | 05-01 | 1 | LANC-02 | T-05-01 | 13 índices presentes no schema migrado; 4 de drift sem `create_index` duplicado | integration (DB-level) | `.venv/bin/python -m pytest tests/test_indices.py::test_indices_declarados_existem_no_schema tests/test_database.py -q` | ✅ | ⬜ pending |
| 05-01-03 | 05-01 | 1 | LANC-02 | T-05-01/02 | PRAGMA `case_sensitive_like=ON` sem regressão de busca/filtro/agrupamento | integration + suíte completa | `.venv/bin/python -m pytest tests/test_indices.py -q && scripts/verificar.sh --rapido` | ✅ | ⬜ pending |
| 05-02-01 | 05-02 | 1 | LANC-01 | T-05-12 | Runtime PBS importa rawpy/pillow_heif/fotoorganizer de dentro do bundle; extra `llm` fora | manual/scripted | `src-tauri/resources/runtime/python/bin/python3 -c "import rawpy, pillow_heif, fotoorganizer"` | N/A — verificação de artefato | ⬜ pending |
| 05-02-02 | 05-02 | 1 | LANC-01 | T-05-11 | Bundle existe com binário e runtime embarcado; identidade de assinatura conhecida | manual/scripted | `codesign -dv --verbose=4 "src-tauri/target/release/bundle/macos/Foto Organizer.app"` | N/A — build nativo, fora de `verificar.sh` | ⬜ pending |
| 05-03-01 | 05-03 | 2 | LANC-01 | T-05-20/22/23 | App empacotado sobe backend, varre fixtures, popula grade e encerra sem órfão nos dois caminhos | manual/scripted | `pgrep -f "fotoorganizer web"` sai 1 após `quit` e após `kill -9` no shell nativo | N/A — ciclo de vida nativo | ⬜ pending |
| 05-03-02 | 05-03 | 2 | LANC-01 | T-05-21 | Dono abre pelo Finder passando pelo Gatekeeper e vê grade populada | manual (checkpoint bloqueante) | — (human-check) | N/A por desenho | ⬜ pending |
| 05-03-03 | 05-03 | 2 | LANC-01 | — | Aceite do Marco 1 registrado em `docs/EMPACOTAMENTO.md` sem remover conteúdo | source assertion | `grep -c "## Aceite do Marco 1" docs/EMPACOTAMENTO.md` | ✅ | ⬜ pending |
| 05-04-01 | 05-04 | 2 | LANC-04 | T-05-30/31 | Script mede as três métricas ponta a ponta, sem caminho destrutivo e com `advisor=None` | manual/scripted | `.venv/bin/python scripts/medir_baseline_producao.py --data-dir <tmp> --pasta <fixtures>` | ❌ Wave 0 — criado nesta task | ⬜ pending |
| 05-04-02 | 05-04 | 2 | LANC-04 | T-05-33 | Raízes da medição aprovadas pelo dono antes da varredura longa | manual (checkpoint de decisão) | — (human-check) | N/A por desenho | ⬜ pending |
| 05-04-03 | 05-04 | 2 | LANC-04 | T-05-30/34 | Baseline com número, metodologia e máquina; produção sem sugestões auto-geradas | manual/scripted | `sqlite3 "$HOME/Library/Application Support/FotoOrganizer/catalog.db" "select count(*) from suggestions"` retorna 0 | ✅ | ⬜ pending |
| 05-05-01 | 05-05 | 3 | LANC-03 | T-05-40 | Wiring dos 4 pontos de entrada verde antes da sessão; catálogo do teste vazio | integration (frontend) | `cd webapp && npm test` | ✅ `webapp/src/App.test.tsx:373-510` | ⬜ pending |
| 05-05-02 | 05-05 | 3 | LANC-03 | T-05-40 | Usuário sem instrução chega (ou não) a uma grade populada | manual UAT (checkpoint bloqueante) | — (human-check, D-06) | N/A por desenho | ⬜ pending |
| 05-05-03 | 05-05 | 3 | LANC-03 | T-05-41 | Rodada registrada em `docs/AVALIACAO_UX.md`, achados classificados, sem mudança de UI não aprovada | source assertion | `git diff --stat webapp/` vazio e `grep -c "LANC-03" docs/AVALIACAO_UX.md` | ✅ | ⬜ pending |

*Task IDs preenchidos pelo planner em 2026-08-17.*

---

## Wave 0 Requirements

- [x] `tests/test_indices.py` — planejado como task 1 do plano 05-01. — asserts `EXPLAIN QUERY PLAN` uses `SEARCH ... USING INDEX` (not `SCAN`) for the `pasta` prefix query post-migration (LANC-02).
- [x] Timing script — planejado como task 1 do plano 05-04 (`scripts/medir_baseline_producao.py`). for `SuggestionEngine.gerar()` / `DuplicateDetector.detectar()` against real data (LANC-04) — direct-call CLI script recommended per RESEARCH.md Open Question 2, for reproducibility.

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`tests/test_indices.py`, timing script)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner, 2026-08-17 — 14 tasks mapeadas, 3 checkpoints humanos por desenho (LANC-01 visual, raízes da medição, UAT de LANC-03); nenhuma sequência de 3 tasks sem verificação automatizada.
