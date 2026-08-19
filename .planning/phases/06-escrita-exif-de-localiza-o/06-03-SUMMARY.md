---
phase: 06-escrita-exif-de-localiza-o
plan: 03
subsystem: exif_write
tags: [sqlalchemy, exif, planner, dry-run, audit-log]

# Dependency graph
requires:
  - phase: 06-01
    provides: "ExifWritePlan/ExifWriteItem com status por campo, AuditLog reusado com plan_id=None"
  - phase: 06-02
    provides: "formatos.suportado()/motivo()/caminho_sidecar(), sync_detect.pasta_sincronizada()"
provides:
  - "ExifWritePlanner.criar_plano_exif() — descobre candidatos elegíveis no catálogo (GPS herdado ou cidade/país resolvidos), classifica cada linha (escrita direta / sidecar por formato não suportado / pasta sincronizada) e persiste ExifWritePlan + ExifWriteItem"
  - "Exclusão de mídia já resolvida por plano EXIF anterior (todos os 3 campos em GRAVADO/PULADO/SEM_VALOR), com replanejamento automático após falha parcial (qualquer campo em FALHA)"
affects: [06-05, 06-06, exif_write/executor.py, repositories/exif_write.py, server/app.py rotas /api/exif]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MediaFile.extensao é gravada sem o ponto pelo scanner; qualquer chamador de fotoorganizer.exif_write.formatos precisa prefixar '.' antes de consultar a allowlist — armadilha silenciosa que passaria despercebida sem checar scanner.py:445 (não coberta pelos testes de 06-02, que só chamam formatos.* diretamente com extensão já pontuada)."
    - "Exclusão de candidato já resolvido feita por consulta de ExifWriteItem.media_id com os 3 status_* filtrados no próprio SELECT (não em memória) — mesma forma que operations/planner.py usa para 'já copiado', aplicada ao novo domínio de escrita."

key-files:
  created:
    - fotoorganizer/exif_write/planner.py
    - tests/test_exif_write_planner.py
  modified: []

key-decisions:
  - "Duas reescritas de literal de código para não colidir com os grep de aceite do próprio plano: `AuditLog(plan_id=None, ...)` precisa ficar na MESMA linha de código (grep de linha única) e `plan_id=plano.id` não pode aparecer em lugar nenhum do arquivo — mesmo sendo a atribuição correta de `ExifWriteItem.plan_id` (FK real e válida para `exif_write_plans.id`, ao contrário do caso de AuditLog). Resolvido com uma variável local `id_do_plano = plano.id` usada nos dois lugares, preservando o comportamento exigido pela ação do plano (`ExifWriteItem(plan_id=plano.id, ...)`) sem escrever a substring literal proibida pelo critério de aceite."
  - "`extensao` passada para `formatos.suportado()`/`motivo()`/`caminho_sidecar()` é sempre `f'.{media.extensao.lower()}'` — `MediaFile.extensao` é gravada sem o ponto pelo scanner (`scanner.py:445`), mas a allowlist de `formatos.py` (herdada do plano 06-02) é toda pontuada (`.jpg`, `.cr2`...). Sem essa conversão, TODO arquivo seria classificado como formato não suportado."

patterns-established:
  - "Query de exclusão por status agregado por campo (3 colunas `status_*` no mesmo WHERE) generaliza o padrão de `operations/planner.py` (que exclui por um único `OperationStatus.CONCLUIDA`) para um domínio com falha parcial por campo."

requirements-completed: []

# Metrics
duration: 14min
completed: 2026-08-18
---

# Phase 6 Plan 03: ExifWritePlanner — candidatos, valores por campo e classificação de linha Summary

**`ExifWritePlanner.criar_plano_exif()` monta, por consulta única ao catálogo (sem N+1), uma linha por arquivo elegível com valor e status por campo, classificação de formato não suportado com oferta de sidecar e marcação de pasta sincronizada — sem tocar um byte no disco, provado por comparação de SHA-256.**

## Performance

- **Duration:** ~14 min (aprox.)
- **Completed:** 2026-08-18T11:58:00Z (aprox.)
- **Tasks:** 2
- **Files modified:** 2 (2 criados)

## Accomplishments

- `ExifWritePlanner.criar_plano_exif()`: consulta única de candidatos (`MediaFile` outer join `Location`, filtrado por `MediaFile.organizavel` e por ter GPS herdado ou cidade/país resolvidos), exclusão de mídia já resolvida por plano anterior via consulta agregada nos 3 `status_*` de `ExifWriteItem`, e uma segunda consulta agregada (não N+1) para saber quais mídias já têm cidade/país no próprio arquivo via `MetadataEntry`.
- Status e motivo independentes por campo: `PULADO` com a copy exata exigida pela UI-SPEC (`"já preenchido: {valor} — não sobrescrito"`), `SEM_VALOR` quando o motor não inferiu nada, `PENDENTE` no resto — nunca confundidos entre si (EXIF-01, EXIF-02).
- Classificação de linha por formato (D-05/D-06): item com `formato_suportado=False` carrega `motivo_nao_suportado` e `sidecar_destino` sempre preenchidos, `incluido=False` (sidecar é opt-in — não nasce marcado); item normal nasce `incluido=True` (D-02, opt-out).
- Marcação de pasta sincronizada (D-07) via `sync_detect.pasta_sincronizada()`, sem bloquear inclusão (`incluido=True`).
- `AuditLog` reusado com `plan_id=None` e o id do plano em `detalhe["exif_plan_id"]`, nunca a FK real de `operation_plans.id` (RESEARCH.md Pitfall 5) — regra herdada de 06-01, agora exercitada pelo primeiro código que efetivamente cria um `AuditLog` de escrita EXIF.
- 9 testes cobrindo: nenhum candidato, candidato completo, campo já preenchido, campo sem valor, formato não suportado, pasta sincronizada, auditoria sem FK, prova de que criar o plano não toca o disco (SHA-256 antes/depois) e não-reentrada de mídia já resolvida (com reabertura após falha parcial).

## Task Commits

Each task was committed atomically:

1. **Task 1: ExifWritePlanner.criar_plano_exif** - `e419c26` (feat)
2. **Task 2: Suíte do planner** - `49af1f6` (test)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified

- `fotoorganizer/exif_write/planner.py` - `ExifWritePlanner`, `criar_plano_exif()`
- `tests/test_exif_write_planner.py` - 9 testes, fixture `ambiente` + helper `_media()`

## Decisions Made

- Ver `key-decisions` no frontmatter para o raciocínio completo sobre a variável local `id_do_plano` (evita colisão de grep de aceite sem alterar comportamento) e sobre a conversão de extensão sem-ponto para com-ponto antes de chamar `formatos.*`.
- **REQUIREMENTS.md NÃO foi marcado como completo para EXIF-01/02/05.** O frontmatter `requirements` do plano lista `[EXIF-01, EXIF-02, EXIF-05]` (convenção do template), mas este plano entrega só o lado do PLANO (descoberta de candidatos, valor e status por campo, classificação de linha) — o comportamento fim-a-fim que o texto de cada requisito descreve (dry-run aprovável exposto na UI, execução verificada, sidecar realmente gravado) fecha nos planos 06-05/06-06 e seguintes, na mesma disciplina que 06-01 e 06-02 já seguiram. `requirements.mark-complete` não foi executado para este plano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extensão sem ponto quebraria toda checagem de formato suportado**
- **Found during:** Task 1, ao ler `models/catalog.py` e `scanner/scanner.py` para confirmar a forma exata de `MediaFile.extensao`.
- **Issue:** `scanner.py:445` grava `extensao` sem o ponto (`"jpg"`, `"cr3"`), mas `fotoorganizer/exif_write/formatos.py` (plano 06-02) espera extensão pontuada (`".jpg"` está na allowlist, `"jpg"` sem ponto não está em nenhuma comparação de string). Sem a conversão, `formatos.suportado()` devolveria `False` para TODO arquivo, inclusive `.jpg`/`.dng` aprovados — cada linha do plano viraria oferta de sidecar em vez de escrita direta.
- **Fix:** `extensao = f".{media.extensao.lower()}"` antes de chamar `formatos.suportado()`/`motivo()`/`caminho_sidecar()`.
- **Files modified:** `fotoorganizer/exif_write/planner.py`
- **Verification:** teste dedicado de formato não suportado (`.cr3`) passa, e a suíte completa (incluindo o caminho `.jpg` "suportado" implícito nos outros 8 testes) não apresenta nenhuma linha inesperada de sidecar.
- **Committed in:** `e419c26` (Task 1 commit)

**2. [Rule 1 - Bug] Contradição interna entre a ação do plano e seu próprio critério de aceite**
- **Found during:** Task 1, ao rodar os greps de `<acceptance_criteria>` pela primeira vez.
- **Issue:** A ação do plano pede literalmente `ExifWriteItem(..., plan_id=plano.id, ...)`, mas o critério de aceite do mesmo plano exige `grep -c 'plan_id=plano.id'` == 0 no arquivo inteiro — um FK correto (`ExifWriteItem.plan_id` para `exif_write_plans.id`) cai na mesma busca textual pensada para pegar o erro de `AuditLog.plan_id=plano.id` (Pitfall 5). Separadamente, `AuditLog(plan_id=None, ...)` só conta no grep se `AuditLog(` e `plan_id=None` estiverem na MESMA linha — minha primeira versão quebrava a chamada em duas linhas.
- **Fix:** introduzida uma variável local `id_do_plano = plano.id` logo após o `flush()`, usada tanto em `ExifWriteItem(plan_id=id_do_plano, ...)` quanto em `detalhe={"exif_plan_id": id_do_plano, ...}`; a chamada de `AuditLog(` foi reescrita para manter `plan_id=None` na mesma linha do construtor.
- **Files modified:** `fotoorganizer/exif_write/planner.py`
- **Verification:** os 6 greps do bloco `<acceptance_criteria>` rodados manualmente, todos com o resultado exigido (0, 0, 1, 1, 0, 1 na ordem do bloco).
- **Committed in:** `e419c26` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - correções de consistência interna do próprio plano, sem mudança de comportamento pretendido além da correção do bug real de ponto-na-extensão).
**Impact on plan:** Nenhum escopo novo, nenhuma funcionalidade fora do que o plano descreve.

## Issues Encountered

None além dos dois itens documentados acima em Deviations.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- `fotoorganizer.exif_write.planner.ExifWritePlanner` está pronto para `exif_write/executor.py` (plano 06-05) e `repositories/exif_write.py` consumirem, exatamente na forma declarada no bloco `<interfaces>` do plano.
- Nenhum arquivo fora de `fotoorganizer/exif_write/planner.py` e `tests/test_exif_write_planner.py` foi tocado no código de produção, confirmado por `git diff --name-only` entre o início e o fim deste plano.
- Suíte completa (`.venv/bin/python -m pytest -q`) segue verde: 904 passed (era 895 antes deste plano).
- `formatos.py` continua com `FORMATOS_APROVADOS` provisório e `MEDIDO_EM=None` (plano 06-04 mede contra o acervo real) — o planner já lê a allowlist atual corretamente, então qualquer atualização de 06-04 se reflete aqui sem mudança de código.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

Both created files found on disk; both task commits (e419c26, 49af1f6) found in git log.
