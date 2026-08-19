---
phase: 06-escrita-exif-de-localiza-o
plan: 07
subsystem: ui
tags: [react, tanstack-query, typescript, tailwind, exif, webapp]

# Dependency graph
requires:
  - phase: 06-06
    provides: "Seis endpoints /api/exif/*, JobManager.iniciar_escrita_exif (tipo de job 'escrita_exif'), contrato PlanoExif/ItemPlanoExif/RelatorioDryRunExif já fixado no bloco <interfaces> do plano"
provides:
  - "Tipos StatusCampoExif/CampoExif/ItemPlanoExif/PlanoExif/PlanoExifDetalhe/RelatorioDryRunExif em webapp/src/api.ts"
  - "Cliente HTTP api.planosExif/planoExif/criarPlanoExif/dryRunExif/auditoriaExif, reusando json/post"
  - "useJob().executarEscritaExif(planId, itens) — job type 'escrita_exif'"
  - "webapp/src/components/EscritaExif.tsx — esqueleto plano→dry-run→gravar, sidebar de planos, linha de veredito, estado vazio 'Nada para gravar', linha tipo A com os três chips de campo (GPS/Cidade/País)"
  - "Aba 'Localização' registrada em App.tsx (global, fora de ABAS_COM_FONTE)"
affects: [06-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EscritaExif.tsx segue Operations.tsx quase linha a linha (sidebar w-72, veredito(), barra de ações, <details> de auditoria) mas sem input de destino — escrita in-place não tem raiz de destino para escolher."
    - "Chip de campo (ChipCampo) com switch exaustivo sobre StatusCampoExif: gravado/falha caem no mesmo branch neutro de pendente nesta fase, só para o TypeScript acusar quando 06-08 esquecer de tratar um caso — não é comportamento final."

key-files:
  created:
    - webapp/src/components/EscritaExif.tsx
  modified:
    - webapp/src/api.ts
    - webapp/src/hooks/useJob.ts
    - webapp/src/App.tsx

key-decisions:
  - "CTA 'Gravar N arquivos' já chama job.executarEscritaExif(plano.id, null) — grava o plano inteiro, sem seleção por checkbox. A seleção pontual (D-02, opt-out por linha) e as linhas B/C (sidecar .xmp, pasta sincronizada) ficam para 06-08, conforme o próprio plano delimita no objective."
  - "Nenhum requisito EXIF-01/EXIF-02 marcado como completo em REQUIREMENTS.md — mesma disciplina de 06-01..06-06: esta fatia entrega a inspeção do plano e o disparo da gravação, mas o comportamento pós-execução (detalhamento por campo, falha parcial visível) só chega em 06-08, e é parte do texto de EXIF-03. `requirements.mark-complete` não foi executado."

patterns-established:
  - "Regra de gênero por campo no texto do chip 'pulado' (JA_PREENCHIDO): GPS/País masculino, Cidade feminino — evita frase gramaticalmente errada quando 06-08 estender a mesma tabela para os outros status."

requirements-completed: []

# Metrics
duration: ~20min
completed: 2026-08-18
---

# Phase 6 Plan 07: Base da tela Localização (tipos, cliente, esqueleto) Summary

**`EscritaExif.tsx` no molde de `Operations.tsx`, sem campo de destino, com sidebar de planos, veredito "gravar", CTA bloqueada até dry-run aprovado e linha tipo A mostrando os três chips de campo (GPS/Cidade/País) com estado pronto/pulado/sem_valor.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-18
- **Tasks:** 2
- **Files modified:** 4 (1 criado, 3 modificados)

## Accomplishments

- `webapp/src/api.ts` ganhou `StatusCampoExif`/`CampoExif`/`ItemPlanoExif`/`PlanoExif`/`PlanoExifDetalhe`/`RelatorioDryRunExif`, espelhando 1:1 o contrato do bloco `<interfaces>` do plano 06-07 (produzido em 06-06), e as cinco chamadas `planosExif`/`planoExif`/`criarPlanoExif`/`dryRunExif`/`auditoriaExif` no objeto `api`, reusando `json`/`post` sem wrapper novo.
- `useJob.ts` ganhou `executarEscritaExif(planId, itens)` — o único disparo de job que carrega seleção do dono no corpo (`itens: number[] | null`), comentado como tal.
- `EscritaExif.tsx` (novo, 311 linhas): duas colunas no molde de `Operations.tsx` — sidebar de planos com contagem `gravados/total_itens`, barra de ações (`Criar plano de escrita` sem campo de texto, `Rodar dry-run`, CTA `Gravar N arquivos` desabilitada enquanto `!plano.executavel`), linha de veredito com o verbo "gravar", estado vazio `Nada para gravar` com o corpo exato da UI-SPEC, e uma linha por `ItemPlanoExif` com os três chips (`ChipCampo`) cobrindo `pronto` (valor formatado, GPS com 4 casas), `pulado` (`text-texto-2`, nunca `text-erro`, `title` com o motivo do servidor) e `sem_valor` (`text-texto-3`, travessão).
- Aba `Localização` registrada em `App.tsx` depois de `Operações`, com a dica exata da UI-SPEC, fora de `ABAS_COM_FONTE` (escopo global, decisão explícita).
- Nenhum token de cor/tamanho novo, nenhuma dependência nova (`git diff webapp/package.json` vazio), nenhuma ocorrência da palavra "destino" no novo componente (grep = 0).

## Task Commits

Each task was committed atomically:

1. **Task 1: Tipos, cliente /api/exif e executarEscritaExif no useJob** - `d67a270` (feat)
2. **Task 2: EscritaExif.tsx (esqueleto + linhas tipo A) e a aba Localização** - `566ecd2` (feat)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified

- `webapp/src/api.ts` - `StatusCampoExif`/`CampoExif`/`ItemPlanoExif`/`PlanoExif`/`PlanoExifDetalhe`/`RelatorioDryRunExif` + `planosExif`/`planoExif`/`criarPlanoExif`/`dryRunExif`/`auditoriaExif`
- `webapp/src/hooks/useJob.ts` - `executarEscritaExif(planId, itens)`
- `webapp/src/components/EscritaExif.tsx` - componente novo: esqueleto da tela Localização
- `webapp/src/App.tsx` - aba `Localização` (ABAS, DICAS, render), import de `EscritaExif`

## Decisions Made

Ver `key-decisions` no frontmatter. Resumo: CTA já dispara a gravação do plano inteiro (`itens: null`); seleção por checkbox e linhas B/C ficam para 06-08 por delimitação explícita do próprio plano; nenhum requisito EXIF marcado como completo ainda.

## Deviations from Plan

None - plan executado exatamente como escrito.

## Issues Encountered

None.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- `EscritaExif.tsx` está pronto para 06-08 estender: checkboxes por linha (D-02, opt-out, Type A/C marcados por padrão, Type B desmarcado), linhas B (sidecar `.xmp`, D-05/D-06) e C (pasta sincronizada, D-07), e o detalhamento pós-execução (per-tag, EXIF-03) — o `switch` de `ChipCampo` já é exaustivo sobre `StatusCampoExif`, então o TypeScript acusa qualquer status esquecido quando 06-08 tratar `gravado`/`falha` de verdade.
- `scripts/verificar.sh` (suíte completa) verde: 937 testes Python + 19/19 benchmark de agrupamento + 151 testes do webapp + build.
- **Nenhum requisito EXIF-01/EXIF-02 foi marcado como completo em REQUIREMENTS.md** — a inspeção do plano e o disparo da gravação já existem na UI, mas o comportamento pós-execução (parte do texto de EXIF-03, e pré-requisito para o dono confirmar que EXIF-02 nunca sobrescreveu nada na prática) só fecha com 06-08.
- Nenhum arquivo fora de `webapp/src/api.ts`, `webapp/src/hooks/useJob.ts`, `webapp/src/components/EscritaExif.tsx` e `webapp/src/App.tsx` foi modificado (mais `webapp/tsconfig.app.tsbuildinfo`, artefato de build já rastreado pelo repositório), confirmado por `git status --short`.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 4 key files found on disk (api.ts, useJob.ts, EscritaExif.tsx, App.tsx) plus this SUMMARY; both task commits (d67a270, 566ecd2) found in git log.
