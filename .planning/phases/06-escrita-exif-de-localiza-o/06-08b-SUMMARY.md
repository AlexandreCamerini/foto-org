---
phase: 06-escrita-exif-de-localiza-o
plan: 08b
subsystem: exif_write
tags: [exiftool, verificacao, allowlist, iptc, d-076, d-077, d-078]

# Dependency graph
requires:
  - phase: 06-04
    provides: "D-076 com o achado não-catalogado de IPTC:EnvelopeRecordVersion (tabela do .tif)"
  - phase: 06-04b
    provides: "D-077, remedição de .jpg/.cr2 (20/20, 12/12) que não exercitou esta tag"
provides:
  - "fotoorganizer/exif_write/verificacao.py: TAGS_ESTRUTURAIS_ESPERADAS ganha IPTC:EnvelopeRecordVersion"
  - "docs/DECISOES.md D-078 — achado do checkpoint 06-09 (JPEG real Canon R6m2), correção, remedição de .jpg (20/20 sem mudança de FORMATOS_APROVADOS), achado à parte (digest IPTC) registrado como blocker"
  - "2 testes de regressão em tests/test_exif_write_writer.py"
affects: [06-09, exif_write/verificacao.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TAGS_ESTRUTURAIS_ESPERADAS continua fechada e justificada tag-a-tag (nunca por prefixo inteiro) — IPTC:EnvelopeRecordVersion é a nona entrada, mesma classe das outras oito (versão de registro/bloco, nunca dado de localização)"

key-files:
  created:
    - .planning/phases/06-escrita-exif-de-localiza-o/06-08b-SUMMARY.md
  modified:
    - fotoorganizer/exif_write/verificacao.py
    - tests/test_exif_write_writer.py
    - docs/DECISOES.md
    - .planning/STATE.md

key-decisions:
  - "D-078: IPTC:EnvelopeRecordVersion (marcador de versão do registro de ENVELOPE IPTC, distinto de ApplicationRecordVersion) entra no andaime incondicional — mesma classe de decisão que as outras oito entradas de TAGS_ESTRUTURAIS_ESPERADAS, não uma extensão da allowlist byte a byte de D-077 (categoria distinta)."
  - "Achado à parte NÃO corrigido, registrado como blocker: JPEG real de produção com bloco IPTC pré-existente (gravado por outra ferramenta antes deste app, ex. Lightroom) produz o aviso NOVO do exiftool 'IPTCDigest is not current. XMP may be out of sync' ao escrever — sem allowlist de avisos hoje (só TAGS_ESTRUTURAIS_ESPERADAS cobre tags), corrigir isso seria mudança de política de segurança (Rule 4/arquitetural), fora do escopo desta correção narrow. Fica para decisão futura do dono, mesmo padrão que D-076 deixou em aberto para offsets antes de D-077 resolver."

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-08-18
---

# Phase 6 Correção 08b: IPTC:EnvelopeRecordVersion na allowlist estrutural (D-078) Summary

**Correção estreita de meio-de-fase sobre o checkpoint humano 06-09: `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` ganha `IPTC:EnvelopeRecordVersion` (nona entrada, mesma classe de andaime incondicional das outras oito), fechando o gap que reprovava a verificação de um JPEG real de produção (Canon EOS R6m2) mesmo com a escrita de localização tendo tido sucesso — achado que já existia, não catalogado, em D-076.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-18 (correção de meio-de-fase disparada pelo checkpoint 06-09)
- **Completed:** 2026-08-18
- **Tasks:** 4 (allowlist, testes de regressão, remedição de `.jpg`, D-078 em DECISOES.md) + atualização de STATE.md
- **Files modified:** 4

## Accomplishments

- `IPTC:EnvelopeRecordVersion` adicionada a `TAGS_ESTRUTURAIS_ESPERADAS` com comentário explicando a distinção de `IPTC:ApplicationRecordVersion` (registro de ENVELOPE vs. registro de APLICAÇÃO, dois marcadores de versão distintos dentro do mesmo container IPTC) e por que é andaime incondicional (tag de versão obrigatória, sempre escrita ao criar bloco IPTC novo, nunca dado de localização).
- 2 testes de regressão novos em `tests/test_exif_write_writer.py`: classificação isolada da tag em `estruturais`, e uma escrita completa simulando o cenário real (GPS + cidade + país + todo o andaime, incluindo a tag nova) confirmando `diff.inesperadas` vazio e os três campos (`gps`/`cidade`/`pais`) gravados.
- Remedição de `.jpg` contra o `catalog.db` de produção real (`scripts/testar_escrita_exif.py --extensoes .jpg --amostras 20`, mesmo método de D-076/D-077, cópias descartáveis via `shutil.copy2`/`tempfile.mkdtemp`, nunca o original): 20/20 aprovadas, `FORMATOS_APROVADOS` continua `{".jpg", ".jpeg", ".cr2"}` (D-077), sem mudança.
- Teste direcionado adicional (fora da suíte pytest, verificação ad-hoc via `testar_amostra()`) contra o arquivo original de produção citado no achado (`/Users/acamerini/Pictures/2026/Serena 15 Anos/ACM_7122.JPG`, cópia descartável — nunca o original nem a cópia de teste do dono no Desktop) confirma que a tag `EnvelopeRecordVersion` deixa de reprovar a verificação.
- `docs/DECISOES.md` ganhou D-078: achado do checkpoint 06-09, correção, remedição, e um achado à parte registrado — ver Issues Encountered abaixo.
- `.planning/STATE.md` ganhou blocker novo e decisão via `gsd-sdk query state.add-blocker`/`state.add-decision`/`state.record-session`/`state.record-metric`.

## Task Commits

Each task was committed atomically:

1. **Task 1: TAGS_ESTRUTURAIS_ESPERADAS ganha IPTC:EnvelopeRecordVersion** - `caa17c6` (fix)
2. **Task 2: testes de regressão** - `1bc84ee` (test)
3. **Task 3: remedição de .jpg (não gera commit — script de medição, não código)** - N/A, resultado documentado em D-078
4. **Task 4: D-078 em docs/DECISOES.md** - `71524d7` (docs)

## Files Created/Modified

- `fotoorganizer/exif_write/verificacao.py` - `IPTC:EnvelopeRecordVersion` adicionada a `TAGS_ESTRUTURAIS_ESPERADAS` com comentário justificando individualmente
- `tests/test_exif_write_writer.py` - 2 testes de regressão novos
- `docs/DECISOES.md` - D-078
- `.planning/STATE.md` - blocker, decisão, sessão e métrica registrados via SDK

## Decisions Made

Ver `key-decisions` no frontmatter. Resumo: tag nova entra na allowlist incondicional (mesma classe das outras oito); achado do aviso de digest IPTC fica registrado, não corrigido — mudança de política de avisos é arquitetural, fora do escopo desta correção narrow.

## Deviations from Plan

### Auto-fixed Issues

Nenhuma — a correção foi exatamente o que o `<required_tasks>` pediu, sem bug adicional descoberto no código em si durante a implementação.

### Discovered, documented, explicitly NOT auto-fixed (Rule 4 — architectural)

**1. Aviso novo do exiftool ("IPTCDigest is not current") em JPEG com bloco IPTC pré-existente**
- **Found during:** Task 3 (remedição), ao testar especificamente o arquivo original de produção citado no achado (`ACM_7122.JPG`), não coberto pelas 20 amostras genéricas usadas na remedição de D-077.
- **Issue:** este arquivo específico já chegava com um bloco IPTC gravado por outra ferramenta (Lightroom — `IPTC:ApplicationRecordVersion`/`Keywords`/`By-line`/`CodedCharacterSet` já presentes antes da escrita). Escrever localização nele produz o aviso NOVO `"Warning: IPTCDigest is not current. XMP may be out of sync"`, que reprova o critério (b) de D-04 (delta de avisos vazio) mesmo com a tag `EnvelopeRecordVersion` já corrigida e o diff de tags limpo (confirmado que `campo_gravado` bate para os três campos).
- **Por que não foi corrigido:** não existe hoje mecanismo equivalente a `TAGS_ESTRUTURAIS_ESPERADAS` para avisos (só cobre tags). Criar um seria mudança de política de segurança — mesma classe de decisão que D-076 deixou em aberto para offsets, só resolvida depois por D-077 com aprovação explícita do dono via `AskUserQuestion`. Corrigir aqui, sem medição contra o acervo real nem aprovação do dono, seria exatamente o tipo de mascaramento que EXIF-04 existe para impedir. Fora do escopo desta correção, que o objetivo explicitamente define como "narrow allowlist gap" (só tags).
- **Verification:** confirmado com `verificacao.dump()`/`avisos()` diretos, sem passar pela suíte pytest (não é regressão de código, é um caso não coberto por nenhum teste hoje).
- **Registered as:** blocker novo em `STATE.md` (`state.add-blocker`), não um checkpoint — a tarefa atual (fix do EnvelopeRecordVersion) não está bloqueada por isto, é um achado paralelo.

**Total deviations:** 0 auto-fixed; 1 achado documentado e explicitamente deixado fora de escopo (Rule 4).
**Impact on plan:** Nenhum — todos os `required_tasks` e `success_criteria` da correção foram cumpridos; o achado paralelo não impede o fechamento desta correção, só adia (novamente) a aprovação completa de `.jpg` para arquivos com histórico de edição em outra ferramenta.

## Issues Encountered

**A remedição genérica de `.jpg` (20/20) não teria pego este achado sozinha.** Inspecionei individualmente as 20 amostras usadas na remedição de D-077/desta correção: nenhuma tinha bloco IPTC pré-existente (`File:CurrentIPTCDigest` ausente em todas antes da escrita). O arquivo que efetivamente reproduz o achado do dono (`ACM_7122.JPG`) só apareceu porque testei especificamente o caminho citado no `<finding>` da correção, não pela amostragem aleatória padrão do script. Registrado em D-078 como achado à parte, precisamente para não deixar a leitura de "20/20 aprovado" esconder este caso.

**Drift conhecido de contagem de progresso em STATE.md (recorrência do achado já documentado em `06-08-SUMMARY.md`).** As chamadas `gsd-sdk query state.*` re-sincronizam o frontmatter de `STATE.md` a cada escrita, contando arquivos `*-PLAN.md` vs `*-SUMMARY.md` em `.planning/phases/06-escrita-exif-de-localiza-o/`. Como `06-04b-SUMMARY.md` já existia sem `PLAN.md` correspondente, e este arquivo (`06-08b-SUMMARY.md`) também não tem `PLAN.md` próprio, a contagem bateu 9 SUMMARY / 9 PLAN e o frontmatter foi automaticamente recalculado para `completed_phases: 1`/`percent: 17` — a Fase 6 marcada como concluída por engano, mesmo bug já relatado em `06-08-SUMMARY.md`. Corrigido manualmente de volta para `completed_phases: 0`/`completed_plans: 8`/`percent: 0` nesta sessão (a Fase 6 continua em execução — falta 06-09). `ROADMAP.md` não foi tocado por `roadmap.update-plan-progress` nesta correção, propositalmente, para não reproduzir o mesmo drift lá.

## User Setup Required

None — `exiftool` já confirmado instalado; nenhuma dependência nova. Nenhum arquivo do acervo real foi alterado: toda medição usou cópias descartáveis via `shutil.copy2`/`tempfile.mkdtemp`, incluindo contra o arquivo original específico citado no achado. `~/Desktop/teste-exif/` (pasta de teste manual do dono) não foi tocada — confirmado por timestamps inalterados antes/depois desta sessão.

## Next Phase Readiness

- `.jpg`/`.jpeg`/`.cr2` continuam aprovados (D-077), agora sem o gap de `EnvelopeRecordVersion` que travava a escrita real em arquivos "virgens" (nunca tiveram bloco IPTC/GPS/XMP).
- **Novo blocker para o dono avaliar antes ou durante 06-09:** arquivos com bloco IPTC pré-existente (histórico de edição em outra ferramenta, ex. Lightroom) ainda reprovam a verificação por um aviso novo do exiftool não catalogado. Isto pode afetar uma fração real do acervo do dono (fotos já editadas em Lightroom antes de entrarem no Foto Organizer) — vale medir a extensão antes de assumir que é caso raro.
- 06-09 (documentação de arquitetura, gate completo, verificação humana do fluxo) segue como próximo passo — esta correção não o substitui, só remove um bloqueio específico que apareceu durante a preparação dele.
- Suíte completa (`.venv/bin/python -m pytest -q`) verde: 939 passed.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 4 key files found on disk (`fotoorganizer/exif_write/verificacao.py`,
`tests/test_exif_write_writer.py`, `docs/DECISOES.md`, this file); all 3 task
commits (`caa17c6`, `1bc84ee`, `71524d7`) found in `git log`. Full suite
(`.venv/bin/python -m pytest -q`) 939 passed.
