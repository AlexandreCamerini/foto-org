---
phase: 06-escrita-exif-de-localiza-o
plan: 08
subsystem: ui
tags: [react, tanstack-query, typescript, tailwind, exif, webapp, vitest]

# Dependency graph
requires:
  - phase: 06-07
    provides: "EscritaExif.tsx esqueleto (plano→dry-run→gravar, linha tipo A com três chips de campo), tipos StatusCampoExif/ItemPlanoExif/PlanoExif em api.ts, executarEscritaExif(planId, itens) no useJob"
provides:
  - "Checkbox por linha (Set<number> marcados) semeado do servidor, nunca de 'todos marcados' — D-01/D-02"
  - "Linha tipo B (formato não suportado): badge de motivo sempre visível + badge redundante de sidecar .xmp, checkbox nasce desmarcado, chips com sufixo → .xmp (EXIF-05/D-05/D-06)"
  - "Linha tipo C (pasta sincronizada): badge aditivo com o serviço nomeado, linha continua marcada por padrão (D-07)"
  - "Linha B+C simultânea: os dois badges lado a lado, semântica do checkbox segue B"
  - "CORES_CAMPO: Record<StatusCampoExif, string> — mapa próprio, não estende Operations.tsx"
  - "Detalhamento de 3 segmentos pós-execução (✓/✗/—) com linha nomeando o campo em falha (EXIF-03), caminho de backup surfaceado quando item.erro existe"
  - "webapp/src/components/EscritaExif.test.tsx — 12 testes vitest presos ao Copywriting Contract da UI-SPEC"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Seleção de linha via Set<number> semeado por useEffect a partir da referência do react-query (não de toggles locais) — o servidor decide o default por tipo de linha, o cliente nunca duplica essa regra."
    - "Duas cores diferentes para o mesmo status em dois contextos visuais: CORES_CAMPO.pulado é text-texto-2 (chip pré-execução, convenção geral), mas o detalhamento pós-execução usa text-texto-3 para tudo que não é ✓/✗ — glifoDetalhamento() é literal, não reusa CORES_CAMPO, e o código comenta por quê."

key-files:
  created: []
  modified:
    - webapp/src/components/EscritaExif.tsx
    - webapp/src/components/EscritaExif.test.tsx (novo arquivo, listado em modified porque key-files não distingue — ver Files Created/Modified abaixo)

key-decisions:
  - "Requirements EXIF-01, EXIF-03 e EXIF-05 marcados completos em REQUIREMENTS.md — esta é a fatia que fecha o comportamento fim-a-fim visível ao dono para os três: aprovação em lote com opt-out (EXIF-01), falha parcial visível por campo (EXIF-03) e formato não suportado com motivo + oferta de sidecar (EXIF-05). EXIF-02 e EXIF-04 permanecem Pending — são garantias de backend já implementadas em 06-02/06-03/06-05, mas fora do escopo de frontmatter `requirements` deste plano; não reivindicadas aqui."
  - "Linha do backup_original: cópia de texto ('Cópia de recuperação preservada — é a forma de desfazer esta gravação', caminho no title) não estava travada verbatim na UI-SPEC — só a existência do sinal era exigida (EXIF-03 success criterion 4). Texto escolhido no mesmo tom do resto da tela."

patterns-established: []

requirements-completed: [EXIF-01, EXIF-03, EXIF-05]

# Metrics
duration: ~25min
completed: 2026-08-18
---

# Phase 6 Plan 08: Checkbox por linha, badges de formato/sync, detalhamento por campo Summary

**`EscritaExif.tsx` completo: checkbox nativo por linha com default vindo do servidor (D-01/D-02), badges de formato não suportado + oferta de sidecar (EXIF-05) e de pasta sincronizada (D-07), e detalhamento pós-execução de 3 segmentos nomeando o campo em falha (EXIF-03) — mais os 12 testes vitest que travam tudo isso.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-08-18
- **Tasks:** 3
- **Files modified:** 2 (1 modificado, 1 novo)

## Accomplishments

- Checkbox nativo (`accent-acento`, `border-borda-forte`) por item, estado `marcados: Set<number>` semeado do servidor a cada troca de referência de `plano` (nunca "todos marcados") — o dono desmarca linhas pontuais e a CTA `Gravar N arquivos` envia `Array.from(marcados)`, nunca `null`.
- Linha tipo B (`formato_suportado === false`): fundo `bg-atencao/5`, badge `⚠ Formato não suportado — {motivo}` com o motivo sempre visível como texto (D-05), badge redundante `⇢ sidecar .xmp` (D-06), rótulo de checkbox exato `"Gravar sidecar .xmp para este arquivo"`, checkbox nasce desmarcado (opt-in), e os três chips de campo ganham o sufixo `→ .xmp`.
- Linha tipo C (`pasta_sincronizada !== null`): badge `☁ Pasta sincronizada — {serviço}` com a frase de risco exata da UI-SPEC no `title`, linha continua marcada por padrão — aviso aditivo, nunca bloqueio (D-07). Uma linha B+C mostra os dois badges lado a lado, semântica do checkbox segue B.
- `CORES_CAMPO: Record<StatusCampoExif, string>` declarado no próprio arquivo (não estende `Operations.tsx`, que não tem categoria para "pulado deliberado"). Quando o item já executou (algum campo em `gravado`/`falha`), os chips de valor viram o detalhamento de 3 segmentos ✓/✗/—, com uma linha `falha — {Campo}: {motivo}` por campo falho — nunca um "erro" nu. `item.erro` (falha de verificação do item inteiro) e `item.backup_original` (caminho de recuperação) são surfaceados quando existem.
- `EscritaExif.test.tsx` (novo, 12 testes): bloqueio sem dry-run, estado vazio, valor de linha tipo A, "pulado" nunca com `text-erro`, contagem da CTA acompanhando o `Set`, desmarcar tudo desabilita, execução envia só os ids marcados, linha B nasce desmarcada com motivo visível, linha C continua marcada, linha B+C com os dois badges, detalhamento pós-execução com falha nomeada, backup preservado visível. Checkbox sempre achado por `role`/`label`.
- Nenhuma dependência nova (`git diff webapp/package.json` vazio); `scripts/verificar.sh` completo verde: 937 testes Python, 19/19 benchmark de agrupamento, 163 testes webapp, build limpo.

## Task Commits

Each task was committed atomically:

1. **Task 1: Checkbox por linha e badges de linha tipo B e C** - `f386ed2` (feat)
2. **Task 2: Vocabulário de status pós-execução e detalhamento por campo** - `ab29d2d` (feat)
3. **Task 3: EscritaExif.test.tsx** - `280927d` (test)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified

- `webapp/src/components/EscritaExif.tsx` - checkbox por linha, badges B/C, `CORES_CAMPO`, `Detalhamento` pós-execução
- `webapp/src/components/EscritaExif.test.tsx` - novo, 12 testes vitest

## Decisions Made

Ver `key-decisions` no frontmatter. Resumo: EXIF-01/03/05 marcados completos (fecham o comportamento visível ao dono nesta fatia); EXIF-02/04 continuam Pending (garantias de backend, fora do escopo de `requirements` deste plano). Texto do sinal de backup preservado não estava travado na UI-SPEC — escolhido no mesmo tom do resto da tela, caminho sempre no `title`.

## Deviations from Plan

None - plan executado exatamente como escrito. Os três commits de task ficaram atômicos por reconstrução deliberada do estado intermediário (Task 1 sem `CORES_CAMPO`/`Detalhamento`, Task 2 adicionando ambos por cima), já que as duas tarefas tocam o mesmo arquivo e foram implementadas em conjunto por eficiência — sem perda de rastreabilidade por task.

## Issues Encountered

- Primeira versão do teste de detalhamento por falha duplicava o rótulo do campo no `motivo` de teste (`"GPS: valor rejeitado..."` mais o prefixo `"GPS: "` que o componente já adiciona), produzindo `"falha — GPS: GPS: valor rejeitado..."`. Corrigido ajustando o `motivo` do builder de teste para não repetir o rótulo — o componente já nomeia o campo, o `motivo` armazenado é só a razão.
- Dois comentários de código continham a substring literal do identificador que o comentário explicava não estar sendo usado (`CORES_STATUS`, `text-erro` perto de `"pulado"`), quebrando os `grep` de aceite dos Tasks 1/2 que checam ausência dessas strings. Reescritos para descrever sem citar o identificador/token literal.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- `EscritaExif.tsx` está funcionalmente completo para o objetivo da Fase 6: plano → dry-run → aprovação em lote com opt-out → execução → auditoria, com os três tipos de linha (A/B/C) e o detalhamento de falha parcial.
- `scripts/verificar.sh` (suíte completa) verde: 937 testes Python + 19/19 benchmark de agrupamento + 163 testes do webapp + build.
- EXIF-02 e EXIF-04 permanecem `Pending` em REQUIREMENTS.md — são garantias de backend já implementadas (06-02 allowlist byte a byte, 06-03 planner nunca sobrescreve campo preenchido, 06-05 executor com diff de verificação), mas nenhum plano até agora as reivindicou explicitamente no frontmatter `requirements`. Se a Fase 6 for dada como encerrada, vale uma checagem final se esses dois IDs devem ser marcados com base no comportamento já provado ponta a ponta pelos testes existentes (pytest de `06-02`/`06-03`/`06-05` + este plano de UI), ou se ficam deliberadamente abertos até um plano futuro os reivindicar.
- Nenhum arquivo fora de `webapp/src/components/EscritaExif.tsx` e `webapp/src/components/EscritaExif.test.tsx` foi modificado (mais `webapp/tsconfig.app.tsbuildinfo`, artefato de build já rastreado pelo repositório).

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 3 key files found on disk (EscritaExif.tsx, EscritaExif.test.tsx, this SUMMARY); all 3 task commits (f386ed2, ab29d2d, 280927d) found in git log.
