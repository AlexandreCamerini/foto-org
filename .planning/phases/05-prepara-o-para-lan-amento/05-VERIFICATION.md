---
phase: 05-prepara-o-para-lan-amento
verified: 2026-08-18T01:27:21Z
status: gaps_found
score: 3/4 must-haves verified (1 uncertain, routed to human verification)
overrides_applied: 0
gaps:
  - truth: "REQUIREMENTS.md reflete a conclusão de LANC-03 e LANC-04"
    status: failed
    reason: "05-04-SUMMARY.md e 05-05-SUMMARY.md declaram `requirements-completed: [LANC-04]` e `[LANC-03]` respectivamente, e ROADMAP.md marca a Fase 5 inteira como Complete (5/5), mas `.planning/REQUIREMENTS.md` ainda tem as duas linhas como `[ ]` (não marcadas) e a tabela de cobertura como `Pending` para ambas. `git log -- .planning/REQUIREMENTS.md` confirma que só os commits de 05-01 (LANC-02) e 05-03 (LANC-01) tocaram o arquivo — 05-04 e 05-05 nunca o atualizaram, apesar do SUMMARY de 05-03 já ter estabelecido o padrão (marcar o requisito fechado no mesmo plano)."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Linhas 160-166 (checkbox `[ ]`) e linhas 249-250 (tabela `Pending`) para LANC-03 e LANC-04, apesar do trabalho correspondente existir e ter sido verificado nesta rodada"
    missing:
      - "Marcar `[x]` em LANC-03 e LANC-04 em .planning/REQUIREMENTS.md (linhas ~160 e ~162)"
      - "Atualizar a tabela de cobertura (linhas ~249-250) de `Pending` para `Complete`"
human_verification:
  - test: "Repetir a Task 2 (checkpoint:human-verify) do plano 05-05: sentar um usuário de primeira vez, sem instrução, sem participação no desenvolvimento, na frente do `.app` empacotado (com o fix `bg-black/95` do ModalCaminho já aplicado) sobre um catálogo vazio e descartável (`FOTOORG_DATA_DIR`)."
    expected: "O usuário chega sozinho a uma grade populada, sem ler documentação e sem intervenção, repetindo o roteiro de observação já definido em 05-05-PLAN.md Task 1."
    why_human: "A própria SUMMARY 05-05 (§ Next Phase Readiness) registra explicitamente: 'não houve um reteste completo com um usuário real sem instrução após o fix'. O defeito original (backdrop translúcido demais) foi diagnosticado por screenshot real e corrigido, com regressão automatizada (`webapp/src/App.test.tsx`, teste 'regressão UAT 2026-08-17 (LANC-03)') travando a classe CSS — verificado nesta sessão, `npx vitest run -t LANC-03` passa. Mas isso prova que o CSS não regride, não que um usuário desinstruído de fato completa o fluxo agora. O critério 3 da Fase 5 é comportamental por desenho (D-06), não de inspeção de código, e a única rodada real registrada em docs/AVALIACAO_UX.md terminou em 'não chegou'."
---

# Phase 5: Preparação para lançamento — Verification Report

**Phase Goal:** O app pode ser entregue a um primeiro usuário real fora da máquina do desenvolvedor — assinado, com fluxo de entrada e com desempenho medido, não só funcionando para quem já sabe onde tudo está.
**Verified:** 2026-08-18T01:27:21Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | App instala como `.app` assinado e notarizado via Tauri v2 com Python embarcado, passando pelo Gatekeeper sem aviso | ✓ VERIFIED (Marco 1 scope) | Escopo desta fase é deliberadamente só o Marco 1 (D-01 em 05-CONTEXT.md, explicitamente flagueado em ROADMAP.md — Marco 2/notarização depende de custo recorrente não aprovado pelo dono). Dentro desse escopo: `docs/EMPACOTAMENTO.md` linha 97 tem `## Aceite do Marco 1 — 2026-08-17` com saída literal de `codesign -dv --verbose=4` (`Signature=adhoc`, não "not signed at all"); `.planning/REQUIREMENTS.md` linha 151 marca `[x] LANC-01`; checkpoint humano bloqueante (05-03 Task 2) foi respondido "aprovado" pelo dono após ver a UI carregada e a grade populada pelo Finder |
| 2 | Consultas por prefixo de pasta (e demais FKs sem índice) usam índice, não table scan | ✓ VERIFIED | `tests/test_indices.py` executado nesta sessão: `16 passed in 5.16s` (`.venv/bin/python -m pytest tests/test_indices.py -q`). `fotoorganizer/database/engine.py:31` contém `PRAGMA case_sensitive_like=ON`. Migração `0018_indices_de_fk_ausentes.py` tem `create_index` × 9 e `drop_index` × 9 (grep confirmado); os 4 índices de drift (`gps_estimado_de_id`, `tipo_imagem`, `tipo_confirmado`, `sources.volume_id`) aparecem só como comentário/justificativa, sem `create_index` duplicado, como o plano exige |
| 3 | Um usuário de primeira vez consegue adicionar sua primeira fonte/pasta e chegar a uma grade populada sem ler documentação | ? UNCERTAIN — human_needed | A única rodada real de UAT (docs/AVALIACAO_UX.md, 2026-08-17) terminou em **não chegou** — o usuário travou no `ModalCaminho` por um backdrop translúcido demais deixando texto sobreposto. A causa raiz foi diagnosticada por screenshot real (não suposição) e corrigida: `webapp/src/components/ModalCaminho.tsx:27` tem `bg-black/95` (era `/60`), confirmado por grep nesta sessão. Regressão automatizada existe e passa: `npx vitest run src/App.test.tsx -t "LANC-03"` → `1 passed`. **Mas** a própria 05-05-SUMMARY.md (§ Next Phase Readiness) declara explicitamente que não houve reteste com usuário real após o fix — o critério 3 é comportamental por desenho (D-06), inspeção de código/CSS não o satisfaz sozinha |
| 4 | Existe um baseline de performance documentado (indexação, sugestões, duplicatas) contra um catálogo de tamanho representativo | ✓ VERIFIED | `docs/PERFORMANCE.md` existe com seção `# Baseline de 2026-08-17`, subseção `## Metodologia` citando P-1/P-2/P-3, as três métricas com número e unidade (59 arq/s; 1.33s de sugestões/1382 sugestões; 4.54s de detecção de duplicatas). Nota honesta no próprio documento: a amostra medida (1.382 arquivos de `~/Pictures/2026`) é uma "fração deliberada" do total (~99 mil/~422 mil), escolhida explicitamente pelo dono no checkpoint da Task 2 — não escondida, documentada com a ressalva de que a extrapolação de tempo absoluto não é linear. `select count(*) from suggestions` na produção = 0 (confirma que a medição não deixou lote não revisado) |

**Score:** 3/4 truths verified, 1 routed to human verification (not counted as failed — see `important_context` on LANC-03 nuance)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tests/test_indices.py` | EXPLAIN QUERY PLAN + existência de índice + regressão de caixa | ✓ VERIFIED | 134 linhas, 4 funções de teste, 16 casos parametrizados, todos passando nesta sessão |
| `fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py` | DDL dos 9 índices novos | ✓ VERIFIED | 9 `create_index`/9 `drop_index`, `ix_media_files_pasta` presente |
| `fotoorganizer/database/engine.py` | `PRAGMA case_sensitive_like=ON` | ✓ VERIFIED | Linha 31 |
| `docs/EMPACOTAMENTO.md` § Aceite do Marco 1 | Registro datado do aceite | ✓ VERIFIED | `grep -c "## Aceite do Marco 1"` = 1 |
| `Foto Organizer.app` (bundle) | Bundle Marco 1 construído | ⚠️ EPHEMERAL (não verificável nesta sessão) | Artefato de build gitignored; não presente neste worktree no momento da verificação (`src-tauri/target/` e `src-tauri/resources/runtime/` ausentes). Isso é esperado — build artifacts não persistem entre worktrees/sessões. A evidência do build (saída de `codesign`, contagem de itens na grade via API) está documentada literalmente em 05-02-SUMMARY.md/05-03-SUMMARY.md e o checkpoint humano da Task 2 do plano 05-03 confirmou visualmente. Não é um stub: é um artefato reproduzível, não commitado por design |
| `scripts/medir_baseline_producao.py` | Medição cronometrada das 3 métricas | ✓ VERIFIED | Existe, `advisor=None` (1 ocorrência fora de comentário), 0 ocorrências de `os.remove/shutil.rmtree/unlink/DROP TABLE/DELETE FROM`, 1+ `shutil.copy2` |
| `docs/PERFORMANCE.md` | Baseline datado com metodologia | ✓ VERIFIED | Contém `# Baseline de`, `Metodologia`, `arq/s`, `advisor` |
| `webapp/src/components/ModalCaminho.tsx` | Modal compartilhado de onboarding | ✓ VERIFIED + WIRED | `bg-black/95` presente; usado pelos 4 pontos de entrada per 04-06; teste de regressão específico do UAT de 05-05 passa |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `fotoorganizer/models/catalog.py` (Index) | `migrations/versions/0018...py` | `create_index` correspondente | ✓ WIRED | `ix_media_files_pasta` aparece em ambos; teste de schema migrado do zero passa |
| `fotoorganizer/database/engine.py` (PRAGMA) | `repositories/media.py:_sob_a_pasta` | Planner usa `ix_media_files_pasta` no LIKE de prefixo | ✓ WIRED | Confirmado empiricamente por `EXPLAIN QUERY PLAN` no teste `test_prefixo_de_pasta_usa_indice_nao_scan`, que passa |
| `src-tauri/src/main.rs` | `fotoorganizer/cli.py cmd_web` | `FOTOORG_READY` no stdout | ✓ WIRED (per 05-03-SUMMARY, checkpoint humano aprovado) | Não re-executável nesta sessão (bundle ausente), mas exercido por comando e visualmente pelo dono em 05-03 |
| `webapp/src/components/Panorama.tsx` | `ModalCaminho.tsx` | botão "Adicionar pasta…" | ✓ WIRED | Herdado da Fase 4 (04-06); cobertura em `App.test.tsx:373-510`, verde nesta sessão (`npx vitest run -t LANC-03` passou sem quebrar o describe maior) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `tests/test_indices.py` inteiro passa | `.venv/bin/python -m pytest tests/test_indices.py -q` | `16 passed in 5.16s` | ✓ PASS |
| Migração 0018 tem 9 create/9 drop | `grep -c create_index / drop_index` | 9 / 9 | ✓ PASS |
| PRAGMA case_sensitive_like presente | `grep -n case_sensitive_like fotoorganizer/database/engine.py` | linha 31 | ✓ PASS |
| Fix do backdrop presente e travado por teste | `grep -n bg-black webapp/src/components/ModalCaminho.tsx` + `npx vitest run -t LANC-03` | `bg-black/95` presente; `1 passed` | ✓ PASS |
| Nenhum debt marker nos arquivos tocados pela fase | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` em 11 arquivos-chave | nenhuma ocorrência | ✓ PASS |
| Bundle `.app` do Marco 1 | `test -d "src-tauri/target/release/bundle/macos/Foto Organizer.app"` | não existe neste worktree agora | ? SKIP — artefato de build ephemeral, evidência já coletada e transcrita nos SUMMARYs no momento do build |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| LANC-01 | 05-02, 05-03 | Empacotamento Marco 1 | ✓ SATISFIED | `.planning/REQUIREMENTS.md:151` marcado `[x]`, tabela linha 247 `Complete`. Consistente com o código/docs |
| LANC-02 | 05-01 | Índices de FK ausentes | ✓ SATISFIED | `.planning/REQUIREMENTS.md:156` marcado `[x]`, tabela linha 248 `Complete`. Consistente com o código/docs |
| LANC-03 | 05-05 | Onboarding validado | ? NEEDS HUMAN + traceability gap | Trabalho real existe (fix + regressão), mas `.planning/REQUIREMENTS.md:160` continua `[ ]` e tabela linha 249 continua `Pending`, apesar de `05-05-SUMMARY.md` frontmatter declarar `requirements-completed: [LANC-03]`. Além disso, o próprio resultado comportamental exigido pelo requisito (usuário chega à grade) não foi reconfirmado após o fix — ver human_verification |
| LANC-04 | 05-04 | Baseline de performance | ✓ SATISFIED (functionally) but traceability gap | Trabalho real existe e verificado (`docs/PERFORMANCE.md`, script), mas `.planning/REQUIREMENTS.md:162` continua `[ ]` e tabela linha 250 continua `Pending`, apesar de `05-04-SUMMARY.md` frontmatter declarar `requirements-completed: [LANC-04]` |

**Orphaned requirements:** None — all 4 declared LANC IDs are claimed by a plan in this phase.

**Traceability gap found:** `git log --oneline -- .planning/REQUIREMENTS.md` shows only two commits touching this file during the phase (`07149e2` for LANC-02, `e41621a` for LANC-01). Neither `05-04` nor `05-05` updated it, despite both SUMMARYs declaring `requirements-completed`. `ROADMAP.md` already marks the whole phase `Complete (2026-08-18)` with 5/5 plans, which is inconsistent with `REQUIREMENTS.md` still showing 2 of 4 phase requirements as `Pending`. This is a mechanical, low-risk fix (flip 2 checkboxes + 2 table cells) but it is a real, verifiable inconsistency in the project's own tracking document — not something to wave through silently.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `scripts/medir_baseline_producao.py` | 261-269 | Non-atomic 3-file `shutil.copy2` snapshot of a live WAL-mode SQLite DB (no locking, no Online Backup API) | ⚠️ Warning (carried from 05-REVIEW.md WR-01) | Could produce a torn/inconsistent baseline copy if the production catalog is written to mid-copy (e.g. server running concurrently) — would silently produce wrong baseline numbers, not an error. Does not block LANC-04 (the one run that produced `docs/PERFORMANCE.md` was not concurrent), but is a latent correctness bug in a script meant to be re-run for future baselines |
| `webapp/src/components/ModalCaminho.tsx` | 34-37 | `Escape`-to-cancel wired only to the `<input>`'s `onKeyDown`, not the modal container — Tab to a button then Escape does nothing | ⚠️ Warning (carried from 05-REVIEW.md WR-02) | Keyboard-incomplete interaction in a codebase that explicitly commits to "navegação por teclado" (CLAUDE.md). Does not block the phase goal (the fix that mattered for LANC-03 was the backdrop opacity, not this), but is a real, demonstrable gap the code review already found and this verification confirms is still present (`grep -n onKeyDown webapp/src/components/ModalCaminho.tsx` shows only the input handler) |
| — | — | Debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) | None found | Scanned all 11 files touched by the phase's plans — zero matches |

Both warnings above were already surfaced by `05-REVIEW.md` (code review, 2026-08-18T01:21:57Z) and are reproduced here for completeness since goal-backward verification must not silently drop known code-review findings. Neither rises to BLOCKER: WR-01 affects only future re-measurements, not the LANC-04 truth already verified; WR-02 is a real but narrower keyboard gap than the one that actually blocked the UAT user (which was the backdrop opacity, now fixed).

### Human Verification Required

See frontmatter `human_verification`. One item:

1. **Reteste de UAT do onboarding pós-fix (LANC-03)**
   **Test:** Repetir a sessão de usuário-de-primeira-vez do plano 05-05 Task 2, agora com o fix do backdrop (`bg-black/95`) presente no `.app` empacotado.
   **Expected:** O usuário chega sozinho a uma grade populada, sem documentação, repetindo os seis pontos do roteiro de observação de 05-05-PLAN.md.
   **Why human:** Critério comportamental por desenho (D-06); a única rodada real registrada terminou em "não chegou", e o fix — embora corretamente diagnosticado e travado por regressão automatizada — nunca foi reconfirmado ponta a ponta com um humano desinstruído, conforme a própria 05-05-SUMMARY.md admite explicitamente.

### Gaps Summary

Um gap mecânico e de baixo risco: `.planning/REQUIREMENTS.md` não foi atualizado para LANC-03 e LANC-04 apesar do trabalho correspondente existir e ter sido verificado independentemente nesta sessão (índices/PRAGMA testados e passando; script e documento de baseline existentes e consistentes com o catálogo de produção). Correção é trivial: marcar os dois checkboxes e as duas linhas da tabela de cobertura.

Separadamente, um item de verificação humana (não um "gap" no sentido de trabalho faltando, mas de confirmação comportamental pendente): o critério 3 da fase (onboarding) teve seu único incidente de UAT real terminar em falha, cuja causa raiz foi corrigida e travada por teste de regressão, mas sem reteste humano pós-fix. Isso é tratado como `human_needed`, não como falha da fase, seguindo a orientação explícita do `important_context` desta verificação.

Nenhum dos dois itens indica trabalho faltando na substância técnica da fase — LANC-01, LANC-02 e a metodologia/documentação de LANC-04 estão solidamente verificados por evidência direta (testes rodados nesta sessão, greps de código, documentos lidos). O escopo Marco 1 vs Marco 2 de LANC-01 é uma decisão travada e sancionada (D-01), não uma redução silenciosa.

---

_Verified: 2026-08-18T01:27:21Z_
_Verifier: Claude (gsd-verifier)_
