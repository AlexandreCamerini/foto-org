---
phase: 06-escrita-exif-de-localiza-o
plan: 02
subsystem: metadata
tags: [exiftool, subprocess, exif, iptc, xmp, gps, sync-detection]

# Dependency graph
requires:
  - phase: 06-01
    provides: ExifWritePlan/ExifWriteItem models (fundação de esquema; este plano não os usa diretamente, mas planner/executor de planos futuros vão)
provides:
  - "ExifToolWriter.escrever(origem, campos, destino=None) — um subprocess.run curto por escrita, grava GPS+cidade+país em ambos os grupos (IPTC/XMP), omite IPTC quando destino é .xmp (sidecar autônomo, D-06)"
  - "verificacao.diferenca()/campo_gravado() — único sinal confiável de sucesso/falha parcial (diff completo de tags, não exit code), com allowlist de andaime estrutural documentada tag a tag"
  - "validar_campos()/ValorInvalido — única fronteira de validação de GPS/texto antes de qualquer subprocesso"
  - "pasta_sincronizada() — detecção pura de caminho para iCloud Drive/CloudStorage/Dropbox legado (D-07), nunca levanta"
  - "formatos.suportado()/motivo()/caminho_sidecar() — allowlist provisória de D-09 ({jpg,cr2,dng,tif}), MEDIDO_EM=None até o plano 06-04 medir"
affects: [06-03, 06-04, 06-05, 06-06, exif_write/planner.py, exif_write/executor.py, scripts/testar_escrita_exif.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "subprocess.run curto por escrita, não -stay_open — volume de escrita é plano revisado (dezenas a milhares), não scan completo"
    - "diff completo de tags antes/depois como único sinal de sucesso, exit code do exiftool nunca decide status (Pitfall 2)"
    - "allowlist de tags de andaime estrutural documentada individualmente por tag, nunca isenção de prefixo inteiro (protege EXIF-04)"

key-files:
  created:
    - fotoorganizer/exif_write/__init__.py
    - fotoorganizer/exif_write/verificacao.py
    - fotoorganizer/exif_write/writer.py
    - fotoorganizer/exif_write/sync_detect.py
    - fotoorganizer/exif_write/formatos.py
    - tests/test_exif_write_writer.py
  modified: []

key-decisions:
  - "File:CurrentIPTCDigest vive só em TAGS_ESTRUTURAIS_ESPERADAS, não também em TAGS_VOLATEIS — a prosa do plano listava a mesma tag nos dois conjuntos, o que faria diferenca() filtrá-la como volátil antes de nunca chegar a classificá-la como estrutural, quebrando o comportamento exigido pelo próprio plano (as 4 tags de andaime devem aparecer em diff.estruturais). Resolvido mantendo a tag só onde sua justificativa (checksum do bloco IPTC) se aplica; comportamento verificado pelos 7 testes de Task 1, incl. o caso das 4 tags juntas."
  - "Nenhum arquivo fora de fotoorganizer/exif_write/ e tests/test_exif_write_writer.py foi tocado — os dois grep de shell=True/subprocess nos módulos de prosa (docstrings) inicialmente davam falso positivo por conter a substring dentro de palavra em português ('subprocesso' contém 'subprocess'); reescrito para não conter a substring literal, sem mudar o sentido."

patterns-established:
  - "Escrita EXIF é sempre subprocess.run isolado, nunca processo -stay_open compartilhado com o leitor — desacopla o lock de escrita (bounded, revisado) do lock de leitura (full-scan)."
  - "Validação Python-side é sempre a primeira linha de código de escrever(): nenhuma escrita chega ao exiftool sem passar por validar_campos() primeiro."

requirements-completed: []

# Metrics
duration: 9min
completed: 2026-08-18
---

# Phase 6 Plan 02: Primitivas de escrita EXIF Summary

**`ExifToolWriter.escrever()` grava GPS/cidade/país num JPEG limpo com zero tags fora de escopo (prova automatizada de EXIF-04), verificado por diff completo de tags — nunca pelo exit code do exiftool, que aceita GPS fora de faixa e pula tag malformada em silêncio (Pitfall 1/2).**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-18T08:36:00-03:00 (aprox.)
- **Completed:** 2026-08-18T08:44:57-03:00
- **Tasks:** 3
- **Files modified:** 6 (5 criados, 1 criado/estendido incrementalmente — `tests/test_exif_write_writer.py`)

## Accomplishments
- `verificacao.py`: `dump`/`dump_lote`/`avisos` (leitura crua via `exiftool -j -G1 -a -n`, nunca levanta) e `diferenca`/`campo_gravado`, o único sinal confiável de sucesso/falha parcial exigido por EXIF-03 — allowlist de 4 tags de andaime estrutural justificadas individualmente, nunca por prefixo inteiro (protege EXIF-04 contra mascaramento).
- `writer.py`: `validar_campos`/`ValorInvalido` como única fronteira de validação (GPS fora de faixa, texto vazio/quebra de linha/oversized) antes de qualquer subprocesso — verificado empiricamente nesta fase que o exiftool aceita `-GPSLatitude=999` em silêncio. `ExifToolWriter.escrever` grava os dois grupos (IPTC+XMP) sempre explicitamente, sem `-overwrite_original` (backup `_original` como rede de recuperação até o diff aprovar), omite IPTC quando o destino é `.xmp` (sidecar D-06).
- `sync_detect.py`/`formatos.py`: `pasta_sincronizada` detecta iCloud Drive/CloudStorage/Dropbox legado por prefixo de caminho resolvido, nunca levanta (D-07); `formatos.py` fixa a allowlist provisória de D-09 (`{jpg,cr2,dng,tif}`) com `MEDIDO_EM=None` até o plano 06-04 medir, e `motivo()` nunca devolve string vazia (D-05).
- 24 testes automatizados em `tests/test_exif_write_writer.py`, incluindo prova de EXIF-04 (dump completo antes/depois num JPEG real sem localização, `inesperadas == {}`) e do comportamento de falha parcial da Pitfall 2 (GPS malformado falha sozinho, cidade entra do mesmo jeito).

## Task Commits

Each task was committed atomically:

1. **Task 1: verificacao.py — dump cru de tags, allowlist e diff** - `42ead4d` (feat)
2. **Task 2: writer.py — validação Python-side e escrita direta + sidecar** - `593f677` (feat)
3. **Task 3: sync_detect.py e formatos.py** - `298823b` (feat)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified
- `fotoorganizer/exif_write/__init__.py` - docstring do pacote, paralelo a `operations/`, não filho
- `fotoorganizer/exif_write/verificacao.py` - dump/dump_lote/avisos, `DiffTags`, `diferenca`, `campo_gravado`
- `fotoorganizer/exif_write/writer.py` - `ValorInvalido`, `validar_campos`, `ExifToolWriter`
- `fotoorganizer/exif_write/sync_detect.py` - `pasta_sincronizada`
- `fotoorganizer/exif_write/formatos.py` - `FORMATOS_APROVADOS`, `MOTIVOS_NAO_SUPORTADO`, `suportado`, `motivo`, `caminho_sidecar`, `MEDIDO_EM`
- `tests/test_exif_write_writer.py` - 24 testes (7 Task 1, 8 Task 2, 9 Task 3), binário-dependentes marcados com `tem_exiftool`

## Decisions Made
- `File:CurrentIPTCDigest` mora só em `TAGS_ESTRUTURAIS_ESPERADAS` — ver `key-decisions` no frontmatter para o raciocínio completo (a prosa do plano duplicava a tag em `TAGS_VOLATEIS` também, o que quebraria a classificação exigida pelo próprio behavior do plano).
- `diferenca()` classifica na ordem estrutural → volátil → localização → inesperada (não a ordem "filtra volátil primeiro" descrita literalmente na prosa do plano), para que uma tag de andaime tenha endereço fixo mesmo que também pareça "algo que muda sem significar nada".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Resolvida contradição de spec entre TAGS_ESTRUTURAIS_ESPERADAS e TAGS_VOLATEIS**
- **Found during:** Task 1 (verificacao.py)
- **Issue:** A prosa do plano lista `File:CurrentIPTCDigest` tanto em `TAGS_ESTRUTURAIS_ESPERADAS` quanto em `TAGS_VOLATEIS`, e descreve `diferenca()` como "ignora TAGS_VOLATEIS ... depois classifica em esperadas/estruturais/inesperadas" — nessa ordem literal, a tag seria filtrada como volátil antes de nunca chegar à classificação estrutural, quebrando o próprio behavior #3 do plano ("GPS:GPSVersionID, IPTC:ApplicationRecordVersion, File:CurrentIPTCDigest e XMP-x:XMPToolkit... classifica as quatro em estruturais").
- **Fix:** Removida a tag de `TAGS_VOLATEIS` (mantida só em `TAGS_ESTRUTURAIS_ESPERADAS`, onde sua justificativa - checksum do bloco IPTC - se aplica) e ajustada a ordem de checagem em `diferenca()` para estrutural → volátil → localização → inesperada, tornando a classificação robusta a qualquer duplicação futura entre os dois conjuntos.
- **Files modified:** `fotoorganizer/exif_write/verificacao.py`
- **Verification:** `test_diferenca_classifica_tags_de_andaime_em_estruturais_nao_inesperadas` passa; as 4 tags aparecem em `diff.estruturais`, nenhuma em `diff.inesperadas`.
- **Committed in:** `42ead4d` (Task 1 commit)

**2. [Rule 1 - Bug] Docstrings continham a substring literal `shell=True`/`subprocess` dentro de texto em português**
- **Found during:** Task 2 e Task 3 (acceptance criteria `grep -c 'shell=True'`/`grep -c subprocess`)
- **Issue:** `writer.py` descrevia o invariante 5 citando literalmente `shell=True` numa docstring (linha de prosa, não comentário `#`, então não é excluída pelo filtro `grep -v '^\s*#'` do critério de aceite); `sync_detect.py` continha a palavra portuguesa "subprocesso", que contém a substring `subprocess`. Os dois faziam o grep de aceite retornar 1 em vez de 0.
- **Fix:** Reescritas as duas frases sem a substring literal, preservando o sentido ("subprocess sem shell habilitado"; "sem chamar processo externo").
- **Files modified:** `fotoorganizer/exif_write/writer.py`, `fotoorganizer/exif_write/sync_detect.py`
- **Verification:** `grep -v '^\s*#' fotoorganizer/exif_write/writer.py | grep -c 'shell=True'` → 0; `grep -v '^\s*#' fotoorganizer/exif_write/sync_detect.py | grep -c subprocess` → 0.
- **Committed in:** `593f677`, `298823b`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - bug fixes, ambos de spec/critério de aceite, sem mudança de comportamento pretendido)
**Impact on plan:** Ambos são correções de consistência interna do próprio plano (contradição de conjunto de tags; substring literal em prosa cruzando um grep de aceite). Nenhum escopo novo, nenhuma funcionalidade fora do que o plano descreve.

## Issues Encountered

None além dos dois itens documentados acima em Deviations.

## User Setup Required

None - `exiftool` já é dependência existente do projeto (D-026/D-027), confirmado instalado (13.55) nesta sessão.

## Next Phase Readiness

- `fotoorganizer.exif_write.writer.ExifToolWriter`, `verificacao.diferenca`/`campo_gravado`, `sync_detect.pasta_sincronizada` e `formatos.suportado`/`motivo`/`caminho_sidecar` estão prontos para `exif_write/planner.py` e `exif_write/executor.py` (planos 06-03/06-05) consumirem, exatamente na forma declarada no bloco `<interfaces>` do plano.
- **Nenhum requisito EXIF-02/03/04/05 foi marcado como completo em REQUIREMENTS.md.** Este plano entrega as primitivas (writer, verificação por diff, detecção de sync, allowlist de formato) que os requisitos exigem, mas não o comportamento fim-a-fim (dry-run aprovável, execução orquestrada, UI) — esse fecha em planos futuros da fase (06-03 planner, 06-05 executor, 06-06+ UI). `requirements.mark-complete` não foi executado para este plano.
- `formatos.py` continua com `FORMATOS_APROVADOS` provisório e `MEDIDO_EM=None` — o plano 06-04 (`scripts/testar_escrita_exif.py`) precisa rodar contra o acervo real antes do allowlist ser considerado final (D-03/D-04).
- Nenhum arquivo fora de `fotoorganizer/exif_write/` e `tests/test_exif_write_writer.py` foi modificado, confirmado por `git status --short`.
- Suíte completa (`.venv/bin/python -m pytest -q`) segue verde: 895 passed.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 6 created files found on disk; all 3 task commits (42ead4d, 593f677, 298823b) found in git log.
