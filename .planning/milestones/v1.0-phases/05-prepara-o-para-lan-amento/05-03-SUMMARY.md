---
phase: 05-prepara-o-para-lan-amento
plan: 03
subsystem: infra
tags: [tauri, packaging, macos, lifecycle, codesign]

# Dependency graph
requires:
  - phase: 05-prepara-o-para-lan-amento (plano 05-02)
    provides: "Foto Organizer.app construído (bundle Tauri v2 + runtime Python PBS embarcado), assinatura ad-hoc verificada"
provides:
  - "Critério de aceite do Marco 1 (docs/EMPACOTAMENTO.md § Marcos) exercido pela primeira vez, por comando e visualmente pelo dono"
  - "Prova, nos dois caminhos de encerramento (SIGTERM via ExitRequested e kill -9 via _vigia_pai), de que o backend Python embarcado não fica órfão"
  - "Registro auditável do aceite em docs/EMPACOTAMENTO.md § Aceite do Marco 1"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verificação de lifecycle de app nativo empacotado: lançar o binário direto (não `open -a`) para herdar env de teste (FOTOORG_DATA_DIR descartável) sem cair no catálogo real"
    - "Prova do desenho anti-órfão de duas camadas exercendo os dois caminhos de saída: encerramento normal (ExitRequested/SIGTERM) e kill -9 no pai (rede de segurança _vigia_pai)"

key-files:
  created: []
  modified:
    - "docs/EMPACOTAMENTO.md — nova seção `## Aceite do Marco 1 — 2026-08-17`"
    - ".planning/REQUIREMENTS.md — LANC-01 marcado completo (escopo Marco 1, per D-01)"

key-decisions:
  - "Nenhuma correção de código necessária (D-03): o caminho crítico completo funcionou de primeira contra o bundle do plano 05-02 — subida do backend, FOTOORG_READY, API, varredura, grade e ambos os caminhos de encerramento sem processo órfão"
  - "LANC-01 marcado Complete no escopo do Marco 1 (não assinado/notarizado), conforme D-01 já registrado em 05-CONTEXT.md e 05-RESEARCH.md: Marco 2 (Developer ID + notarização) segue fora, bloqueado pelo custo do Apple Developer Program (decisão do dono, PROJECT.md § Constraints)"

patterns-established: []

requirements-completed: [LANC-01]

# Metrics
duration: ~35min (Task 1 verificação scriptada + Task 2 checkpoint humano + Task 3 registro)
completed: 2026-08-17
---

# Phase 5 Plan 3: Aceite do Marco 1 do empacotamento Tauri Summary

**Critério de aceite do Marco 1 (`docs/EMPACOTAMENTO.md`) exercido pela primeira vez contra o bundle `Foto Organizer.app` — catálogo descartável, fixtures sintéticas, grade populada, zero processo Python órfão nos dois caminhos de encerramento — e confirmado visualmente pelo dono via Finder.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-17
- **Tasks:** 3/3 completed (Task 1 auto, Task 2 checkpoint humano, Task 3 auto)
- **Files modified:** 2 (`docs/EMPACOTAMENTO.md`, `.planning/REQUIREMENTS.md`)

## Accomplishments

- Ciclo de vida completo do `.app` empacotado exercido por comando: `GET /api/job` (200), `POST /api/scan` com fixtures sintéticas, `GET /api/midia` com contagem exata, `GET /api/pastas` com a árvore de subpastas — tudo contra o runtime Python embarcado, não o `.venv` de dev.
- Catálogo de produção (`~/Library/Application Support/FotoOrganizer/catalog.db`) comprovadamente intocado (mtime inalterado) durante todo o teste, que rodou num `FOTOORG_DATA_DIR` descartável.
- Ambos os lados do desenho anti-órfão de duas camadas provados: encerramento normal via `osascript quit` (SIGTERM no `ExitRequested` do Rust) e `kill -9` direto no shell nativo, pulando o handler do Rust, exercendo especificamente o `_vigia_pai` do lado Python — nenhum processo remanescente em nenhum dos dois casos.
- Zero defeito bloqueante encontrado no caminho crítico (D-03): nenhuma mudança em `src-tauri/src/main.rs` nem em `fotoorganizer/cli.py` foi necessária.
- Confirmação visual do dono (checkpoint Task 2): abriu pelo Finder, passou pelo Gatekeeper, viu a UI carregada com a grade populada, testou "Adicionar pasta…" com uma pasta real pequena e confirmou o fluxo de varredura, fechou pelo menu (Sair/⌘Q).
- Aceite do Marco 1 registrado de forma auditável em `docs/EMPACOTAMENTO.md`, citando literalmente a saída de `codesign -dv --verbose=4` e nomeando os quatro elementos do critério.

## Task Commits

1. **Task 1: Ciclo de vida do `.app` num catálogo descartável** — sem commit de código (nenhuma correção necessária; verificação puramente scriptada contra o bundle já construído no plano `05-02`, sem arquivo rastreado alterado)
2. **Task 2: Aceite visual do Marco 1 pelo dono** — checkpoint humano, sem arquivo alterado; aprovação textual ("aprovado") recebida na sessão de execução
3. **Task 3: Registrar o aceite do Marco 1** — ver commit abaixo

**Plan metadata:** commit deste SUMMARY.md (ver abaixo)

## Files Created/Modified

- `docs/EMPACOTAMENTO.md` — nova seção `## Aceite do Marco 1 — 2026-08-17` inserida logo após `## Marcos`, sem remover conteúdo existente: ferramentas usadas (tauri-cli 2.11.4, PBS 3.12.14 aarch64-apple-darwin), saída literal de `codesign -dv --verbose=4`, os quatro elementos do aceite com o comando que provou cada um, ausência de defeitos, confirmação do dono, e Marco 2 explicitamente fora de escopo.
- `.planning/REQUIREMENTS.md` — `LANC-01` marcado `[x]`/`Complete`, no escopo do Marco 1 (D-01).

## Decisions Made

- **Nenhuma correção de código (D-03).** O plano previa corrigir qualquer defeito bloqueante encontrado na Task 1 dentro do desenho de duas camadas já existente (SIGTERM no `ExitRequested`, `_vigia_pai` no Python). A verificação não encontrou nenhum: todos os quatro elementos do aceite passaram de primeira contra o bundle construído no plano `05-02`.
- **LANC-01 marcado Complete no escopo do Marco 1**, não "assinado e notarizado" ao pé da letra do texto original do requisito. Essa é a leitura já fixada pela decisão D-01 da fase (`05-CONTEXT.md`, `05-RESEARCH.md`): Marco 2 (Developer ID + notarização) fica fora por decisão de custo do dono, e o critério que a Fase 5 exige de LANC-01 é o Marco 1. Registrado explicitamente em `docs/EMPACOTAMENTO.md` § Aceite do Marco 1 para não deixar essa leitura implícita.

## Deviations from Plan

None - plano executado exatamente como escrito. Task 1 não encontrou defeito para corrigir (o "corrigir se necessário" da `<action>` não foi acionado); Task 2 recebeu aprovação do dono sem ressalvas; Task 3 seguiu a estrutura pedida sem necessidade de decisão adicional.

## Issues Encountered

Nenhum no escopo deste plano. Nota de contexto (não bloqueante, já resolvida antes do checkpoint da Task 2 ser apresentado ao dono): durante a sessão, o orquestrador identificou e encerrou um processo zumbi de uma instância **diferente e já instalada** de `/Applications/Foto Organizer.app` (não o bundle deste worktree), remanescente de um `kill -TERM` anterior do próprio orquestrador feito para um reset de catálogo de outro plano/baseline. Resolvido antes da verificação humana; não fez parte do que o dono testou/aprovou aqui.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- Marco 1 do empacotamento aceito e documentado: `LANC-01` fechado no escopo desta fase.
- Marco 2 (assinatura Developer ID + notarização) permanece explicitamente fora, sem pedido de custo ao dono — só será reaberto se/quando o dono decidir assumir o Apple Developer Program.
- Sem bloqueios conhecidos para o restante da Fase 5.

---
*Phase: 05-prepara-o-para-lan-amento*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: docs/EMPACOTAMENTO.md contains "## Aceite do Marco 1"
- FOUND: .planning/REQUIREMENTS.md LANC-01 marked [x] / Complete
- FOUND: docs/EMPACOTAMENTO.md § Aceite do Marco 1 cites codesign output and names the four acceptance elements
