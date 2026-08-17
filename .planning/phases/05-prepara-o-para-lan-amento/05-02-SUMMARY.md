---
phase: 05-prepara-o-para-lan-amento
plan: 02
subsystem: infra
tags: [tauri, python-build-standalone, codesign, packaging, macos]

# Dependency graph
requires:
  - phase: 04-consist-ncia-visual-secund-ria
    provides: webapp React/Vite/TS/Tailwind estável, único front a empacotar
provides:
  - "Foto Organizer.app construído a partir do scaffold Tauri v2 existente (commits 5a797e1/30ba735)"
  - "Runtime Python (python-build-standalone 3.12.14 arm64) embarcado no bundle, com rawpy/pillow_heif/osxphotos/fotoorganizer importáveis de dentro dele"
  - "Suposição A1 da pesquisa resolvida empiricamente: cargo tauri build sem signingIdentity configurado já aplica assinatura ad-hoc (Signature=adhoc) automaticamente"
affects: [05-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verificação de assinatura efetiva via codesign -dv --verbose=4 antes de decidir se tauri.conf.json precisa de signingIdentity explícito"
    - "Worktree novo sempre precisa de webapp/node_modules próprio (npm ci) e não deve depender do symlink do checkout principal — MEMORY.md já documentava isso para .venv"

key-files:
  created: []
  modified: []

key-decisions:
  - "tauri.conf.json NÃO foi alterado: codesign -dv confirmou Signature=adhoc já aplicada pelo default do cargo tauri build, satisfazendo o Marco 1 sem precisar de \"signingIdentity\": \"-\" explícito"
  - "webapp/dist e src-tauri/resources/runtime são artefatos de build (já cobertos por .gitignore/src-tauri/.gitignore) — nenhum commit de artefato, só o commit deste SUMMARY.md, conforme <output> do plano"

patterns-established: []

requirements-completed: [LANC-01]

# Metrics
duration: ~18min
completed: 2026-08-17
---

# Phase 5 Plan 2: Bundle Marco 1 e assinatura ad-hoc automática Summary

**`Foto Organizer.app` construído a partir do scaffold Tauri v2 existente, com runtime Python (PBS 3.12.14 arm64) e webapp de produção embarcados, assinatura ad-hoc `Signature=adhoc` aplicada automaticamente sem configuração — resolve a suposição A1 da pesquisa da Fase 5.**

## Performance

- **Duration:** ~18 min (build do runtime PBS + `cargo tauri build` release dominam o tempo)
- **Completed:** 2026-08-17T18:28:57Z
- **Tasks:** 2/2 completed
- **Files modified:** 0 (nenhuma mudança rastreada — build-only, ver Deviations)

## Accomplishments

- `webapp/dist/index.html` construído (`npm run build`, 2 chunks de assets) e embarcado em `src-tauri/resources/runtime/python/lib/python3.12/site-packages/webapp/dist/` pelo `scripts/empacotar_runtime.sh`.
- Runtime Python autocontido (`python-build-standalone` CPython 3.12.14 aarch64-apple-darwin) gerado com o projeto instalado (extras `xmp,apple`); `rawpy`, `pillow_heif`, `reverse_geocode`, `osxphotos`, `PIL` e `fotoorganizer` importam de dentro dele. Extra `llm` (`anthropic`) confirmadamente ausente — `ModuleNotFoundError`, como exigido pelo invariante 4 do CLAUDE.md.
- `cargo tauri build` completo (release, ~2 min de compilação Rust): gerou `Foto Organizer.app` (472M) e `Foto Organizer_0.1.0_aarch64.dmg` (144M) em `src-tauri/target/release/bundle/`.
- **Suposição A1 resolvida com evidência de comando** (`codesign -dv --verbose=4`), não leitura de documentação — ver saída completa abaixo.

## Task Commits

Nenhum commit de tarefa — ambas as tasks produziram apenas artefatos de build (já cobertos por `.gitignore`/`src-tauri/.gitignore`), e `tauri.conf.json` não precisou de alteração porque a assinatura ad-hoc já veio por default (ver Task 2). Conforme `<output>` do plano: "Commit só se houver mudança rastreada... artefatos de build não vão para o git."

1. **Task 1: Front de produção e runtime Python embarcado** — sem commit (artefatos de build gitignored)
2. **Task 2: Bundle Tauri e identidade de assinatura efetiva** — sem commit (`git diff --stat src-tauri/tauri.conf.json` vazio, confirmando que o arquivo não foi tocado)

**Plan metadata:** commit deste SUMMARY.md (ver abaixo)

## Saída de `codesign -dv --verbose=4` (evidência da suposição A1)

```
Executable=/Users/.../src-tauri/target/release/bundle/macos/Foto Organizer.app/Contents/MacOS/foto-organizer
Identifier=foto_organizer-317d535e0bb0f816
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=84184 flags=0x20002(adhoc,linker-signed) hashes=2627+0 location=embedded
VersionPlatform=1
VersionMin=786432
VersionSDK=1705216
Hash type=sha256 size=32
CandidateCDHash sha256=322294f2746eab7439ebcd1682e04c8c2fc91330
CandidateCDHashFull sha256=322294f2746eab7439ebcd1682e04c8c2fc91330ef70a7127bc722237d9dbb38
Hash choices=sha256
CMSDigest=322294f2746eab7439ebcd1682e04c8c2fc91330ef70a7127bc722237d9dbb38
CMSDigestType=2
Executable Segment base=0
Executable Segment limit=7159808
Executable Segment flags=0x1
Page size=4096
CDHash=322294f2746eab7439ebcd1682e04c8c2fc91330
Signature=adhoc
Info.plist=not bound
TeamIdentifier=not set
Sealed Resources=none
Internal requirements=none
```

**Interpretação (Pitfall 1 / Assumption A1 da pesquisa):** `Signature=adhoc` com `flags=0x20002(adhoc,linker-signed)` confirma que o `cargo tauri build`, sem nenhum `signingIdentity` configurado em `tauri.conf.json`, já aplica assinatura ad-hoc automaticamente no macOS arm64. Não é "código não assinado" (`code object is not signed at all` — 0 ocorrências verificadas). Isso satisfaz o critério do Marco 1: o `.app` roda localmente, o usuário só precisa do clique-direito → Abrir uma vez (Gatekeeper "unidentified developer"), sem precisar de certificado pago. `tauri.conf.json` foi mantido intacto — nenhuma mudança necessária.

## Files Created/Modified

Nenhum arquivo rastreado criado ou modificado. Artefatos de build gerados (todos gitignored):
- `webapp/dist/` — front de produção (`index.html` + 2 assets)
- `src-tauri/resources/runtime/python/` — runtime PBS 3.12.14 arm64 com o projeto instalado
- `src-tauri/target/release/bundle/macos/Foto Organizer.app` — bundle Marco 1 (472M)
- `src-tauri/target/release/bundle/dmg/Foto Organizer_0.1.0_aarch64.dmg` — DMG (144M)

## Decisions Made

- **`tauri.conf.json` não alterado.** A pesquisa (Pitfall 1) levantava duas hipóteses: ad-hoc automático ou objeto não assinado. A evidência de comando confirmou a primeira — nenhuma mudança de configuração era necessária para o Marco 1.
- **Runtime `webapp/node_modules` reconstruído com `npm ci`.** O plano assumia (`<interfaces>`, "ambiente já verificado") que `webapp/node_modules` já estava presente neste worktree; na prática o worktree isolado não tinha `node_modules` (nem `.venv`), então `npm run build` falhou com `tsc: command not found`. Segui a contingência já prevista no próprio plano ("Se `npm run build` falhar por dependência ausente, aí sim rodar `npm ci`"): rodei `npm ci` (172 pacotes, 3s) e o build passou. Não é uma mudança arquitetural — é exatamente o caminho de contingência documentado na Task 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `webapp/node_modules` ausente neste worktree isolado**
- **Found during:** Task 1 (front de produção)
- **Issue:** `npm run build` falhou com `sh: tsc: command not found` — o worktree `agent-aec01761d8079c1fa` não herdou `webapp/node_modules` do checkout principal (nem `.venv`, notado em paralelo mas não necessário para este plano).
- **Fix:** `(cd webapp && npm ci)` — exatamente a contingência já documentada na `<action>` da Task 1 do próprio plano, não uma decisão nova.
- **Files modified:** nenhum arquivo rastreado (só `webapp/node_modules/`, gitignored)
- **Verification:** `npm run build` subsequente completou com sucesso (`105 modules transformed`, `dist/index.html` + 2 assets)
- **Committed in:** N/A — nenhum arquivo rastreado alterado

---

**Total deviations:** 1 auto-fixed (1 blocking, já era a contingência documentada no próprio plano)
**Impact on plan:** Nenhum — comportamento previsto no texto da Task 1, sem improviso.

## Issues Encountered

- Worktree base drift: HEAD do worktree apontava para `75d46c1f` (commit `fix: mês por extenso...`), ancestral do commit-base esperado `ea0a9de` ("docs(05): create phase plan"). Corrigido com `git reset --hard ea0a9de...` conforme o protocolo `<worktree_branch_check>` — avançou o worktree, não descartou trabalho (HEAD era ancestral do alvo, não divergente).
- `.venv` esperado pelo `<interfaces>` do plano não estava presente no worktree; não foi necessário para este plano (nenhum `pytest` rodado — as verificações de Task 1/2 usam apenas o Python embarcado no runtime PBS recém-construído, não o `.venv` de dev).

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- `Foto Organizer.app` existe e está pronto para o plano `05-03` exercer o critério de aceite completo do Marco 1 (abrir num catálogo novo, escanear fixtures, ver a grade, fechar sem processo Python órfão).
- Suposição A1 fechada — `05-03` não precisa reavaliar assinatura, só executar o teste de lifecycle.
- Nenhum bloqueio conhecido. `src-tauri/target/` e `src-tauri/resources/runtime/` permanecem no worktree local (gitignored) — se `05-03` rodar em worktree diferente, precisará reconstruir o bundle (`cargo tauri build` já é rápido, ~2min, pois as deps Rust já compilaram uma vez neste `target/`, mas um worktree novo não herda esse cache).

---
*Phase: 05-prepara-o-para-lan-amento*
*Completed: 2026-08-17*
