---
phase: 05-prepara-o-para-lan-amento
plan: 04
subsystem: performance
tags: [baseline, scanner, suggestion-engine, duplicate-detector, sqlite]

# Dependency graph
requires:
  - phase: 05-prepara-o-para-lan-amento
    provides: "migração 0018 (9 índices de FK) do plano 05-01 — esta medição roda sobre o schema pós-índices"
provides:
  - "scripts/medir_baseline_producao.py — script reproduzível que mede varredura, geração de sugestões e detecção de duplicatas contra o acervo real, com --listar-fontes somente-leitura e cópia descartável (P-2) para as duas medições com escrita"
  - "docs/PERFORMANCE.md — baseline datado 2026-08-17: 59 arq/s de varredura, 1.33s de geração de sugestões (1382 sugestões), 4.54s de detecção de duplicatas, contra 1382 registros de ~/Pictures/2026"
affects: [performance-baseline, requirements-LANC-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Script solto (scripts/*.py) que reusa fotoorganizer.* diretamente, fora de cli.py, seguindo scripts/avaliar_agrupamento.py"
    - "Medição com escrita colateral (SuggestionEngine.gerar/DuplicateDetector.detectar) sempre sobre cópia shutil.copy2 do catálogo, nunca in place, quando a produção não pode ficar com efeito não revisado"
    - "docs/PERFORMANCE.md acumulativo por seção '# Baseline de <data>', espelhando docs/AVALIACAO_UX.md — rodadas futuras acrescentam seção, não reescrevem"

key-files:
  created:
    - scripts/medir_baseline_producao.py
    - docs/PERFORMANCE.md
  modified: []

key-decisions:
  - "Task 2 (checkpoint): dono escolheu varrer só ~/Pictures/2026 (1382 arquivos, 8.1GB) como raiz representativa desta rodada, excluindo dois caminhos ausentes, três volumes não montados, dois importadores (Apple Fotos/Lightroom) e o home inteiro em duas grafias — mapeia à opção 'lista-propria' do plano"
  - "Reset do catalog.db de produção (2026-08-16→17) sem backup adicional, escolha explícita e informada do dono; backup pré-reset catalog-antes-do-reset-20260816-013503.db preservado e usado só em modo leitura"
  - "P-1/P-2/P-3 (varredura in place; sugestões/duplicatas em cópia descartável; advisor=None literal) — decisões de execução do plano, aplicadas sem desvio"

patterns-established:
  - "Pattern: medição contra produção real sempre acompanhada de cópia descartável quando a operação medida tem escrita colateral, para nunca deixar produção com estado não revisado"

requirements-completed: [LANC-04]

# Metrics
duration: ~35min (task 1 em sessão anterior; tasks 2-3 nesta continuação)
completed: 2026-08-17
---

# Phase 5 Plan 04: Baseline de performance pós-reset (LANC-04) Summary

**Script reproduzível de medição contra o acervo real (59 arq/s de varredura, 1.33s de sugestões, 4.54s de duplicatas sobre 1382 fotos) e docs/PERFORMANCE.md com metodologia P-1/P-2/P-3 registrada para comparação futura.**

## Performance

- **Duration:** ~35 min (Task 1 concluída em sessão anterior sob commit `52bac4b`; Tasks 2-3 executadas nesta sessão de continuação)
- **Started (esta continuação):** 2026-08-17T~19:39:00Z (retomada do checkpoint)
- **Completed:** 2026-08-17T20:14:12Z
- **Tasks:** 3/3 (1 já concluída antes do checkpoint, 2 nesta continuação)
- **Files modified:** 2 (`scripts/medir_baseline_producao.py` na sessão anterior; `docs/PERFORMANCE.md` nesta)

## Accomplishments
- LANC-04 fechado: as três métricas (taxa de indexação, tempo de sugestões, tempo de detecção de duplicatas) medidas contra o acervo real de produção, não fixture sintética
- `docs/PERFORMANCE.md` criado no padrão acumulativo de `docs/AVALIACAO_UX.md`, com metodologia reproduzível (comando exato, raízes incluídas/excluídas com motivo)
- Produção verificada sem efeito colateral não revisado: `select count(*) from suggestions` no `catalog.db` real retorna 0; cópia descartável (`baseline-20260817-171223.db`) preservada por invariante 8

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Script de medição reproduzível** - `52bac4b` (feat) — sessão anterior
2. **Task 2: Quais raízes entram na rescan medida** - checkpoint de decisão, sem arquivo alterado (decisão do dono via AskUserQuestion, registrada abaixo)
3. **Task 3: Rodar a medição e escrever docs/PERFORMANCE.md** - `8dcf894` (docs)

## Files Created/Modified
- `scripts/medir_baseline_producao.py` - script de medição reproduzível (`--listar-fontes`, `--pasta`, `--data-dir`, `--pular-varredura`, `--saida`), sessão anterior
- `docs/PERFORMANCE.md` - baseline de 2026-08-17: contexto, metodologia P-1/P-2/P-3, tabela de taxa de indexação, tempos de sugestões/duplicatas, máquina, o que observar na próxima rodada

## Decisions Made

**Task 2 (checkpoint:decision), resolvida pelo dono via AskUserQuestion (não por este agente):**
- Reset do `catalog.db` de produção realizado **sem** cópia de backup adicional — escolha explícita, com "com backup" oferecido como alternativa e recusado.
- Raiz de varredura desta rodada: **só `~/Pictures/2026`** (1.382 arquivos, 8,1 GB) — mapeia à opção "lista-propria" das três oferecidas no plano (representativo / completo / lista-propria).

Raízes das 10 fontes do backup pré-reset excluídas desta rodada, com motivo (transcrito de `docs/PERFORMANCE.md` § Metodologia):

| Fonte | Motivo |
|---|---|
| `Pictures/2025_05_24` | caminho ausente agora |
| `Pictures/Dubai, Thai & Viet` | caminho ausente agora |
| `/Volumes/Externo` | volume não montado |
| `/Volumes/photo/Portfolio/Fotos Organizadas` | volume não montado |
| `/Volumes/photo` | volume não montado |
| `Photos Library.photoslibrary` (APPLE_PHOTOS) | importador, fora da medida de varredura |
| `Lightroom Catalog.lrcat` (LIGHTROOM) | importador, fora da medida de varredura |
| `/Users/acamerini` (home) | escolha do dono — não representativo |
| `/users/acamerini` (duplicata em minúsculas) | escolha do dono — mesmo motivo |

Nenhum volume externo entrou na lista aprovada, então a checagem de aceite "volumes externos confirmados montados com `test -d`" não se aplica a esta rodada (nenhum foi incluído).

## Deviations from Plan

None - plan executado exatamente como escrito. As decisões P-1/P-2/P-3 do plano foram aplicadas literalmente pelo script já commitado na Task 1; nenhum ajuste foi necessário nas Tasks 2-3.

## Issues Encountered
None. A medição rodou em ~29s de ponta a ponta (23,58s varredura + 1,33s sugestões + 4,54s duplicatas) — bem abaixo da estimativa de "dezenas de minutos a horas" do plano, porque a raiz aprovada pelo dono (`~/Pictures/2026`) é pequena (1.382 arquivos) frente ao acervo histórico completo (~422.738 registros). Documentado em `docs/PERFORMANCE.md` § O que observar na próxima rodada: a extrapolação de tempo absoluto para o acervo total não é linear e exige nova medição em escala maior.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Critério 4 da Fase 5 (baseline de performance documentado) satisfeito com número real.
- `scripts/medir_baseline_producao.py` fica disponível para repetir a medição em qualquer rodada futura, inclusive numa escala maior (candidato de reconexão dos volumes Apple Fotos/Lightroom citado em `PROJECT.md`).
- Nenhum bloqueio para as próximas plans da fase 5.

## Self-Check: PASSED

- `scripts/medir_baseline_producao.py` existe (commit `52bac4b`, sessão anterior — confirmado via `git log`).
- `docs/PERFORMANCE.md` existe e contém `# Baseline de`, `Metodologia`, `arq/s`, `advisor`.
- Commit `52bac4b` presente em `git log --oneline`.
- Commit `8dcf894` presente em `git log --oneline`.
- `select count(*) from suggestions` no `catalog.db` de produção = 0.
- `catalog-antes-do-reset-20260816-013503.db` presente e intacto.
- Cópia descartável `baseline-20260817-171223.db` presente em `~/Library/Application Support/FotoOrganizer/`.

---
*Phase: 05-prepara-o-para-lan-amento*
*Completed: 2026-08-17*
