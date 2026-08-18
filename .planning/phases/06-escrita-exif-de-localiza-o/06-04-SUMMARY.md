---
phase: 06-escrita-exif-de-localiza-o
plan: 04
subsystem: exif_write
tags: [exiftool, medicao-empirica, allowlist, d-03, d-04, d-09]

# Dependency graph
requires:
  - phase: 06-02
    provides: "ExifToolWriter.escrever, verificacao.diferenca/campo_gravado/avisos, formatos.py provisório (MEDIDO_EM=None)"
provides:
  - "scripts/testar_escrita_exif.py — CLI reproduzível (--db/--amostras/--extensoes/--json) que mede, contra cópias descartáveis do acervo real, se um formato passa no critério de D-04 (diff sem inesperadas + delta de avisos vazio + releitura estrutural idêntica); usa o writer/verificacao de produção, nunca reimplementa"
  - "fotoorganizer/exif_write/formatos.py MEDIDO_EM=2026-08-18, FORMATOS_APROVADOS=frozenset() (medido: nenhum formato aprovou), MOTIVOS_NAO_SUPORTADO com motivo distinto por extensão (reprovado vs. sem amostra D-09)"
  - "docs/DECISOES.md D-076 — tabela completa, os 3 critérios, achado do byte a byte idêntico da miniatura registrado como candidato a decisão futura (não decidido aqui)"
affects: [06-05, 06-06, exif_write/executor.py, exif_write/verificacao.py (achado, não modificado em política)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "avisos() lê texto plano do exiftool, não -j — JSON colapsa tags Warning/Error repetidas em uma só, e o resumo agregado 'Validate' não é warning/error (fica fora do conjunto: seu valor muda tanto quando piora quanto quando melhora)"
    - "Script de medição empírica escreve só em cópias (shutil.copy2 em tempfile.mkdtemp), nunca no original nem no catalog.db (mode=ro) — mesmo padrão de scripts/calibrar_raio_incerteza.py para leitura, invertido para escrita com o mesmo rigor de isolamento"

key-files:
  created:
    - scripts/testar_escrita_exif.py
  modified:
    - fotoorganizer/exif_write/formatos.py
    - fotoorganizer/exif_write/verificacao.py
    - docs/DECISOES.md
    - tests/test_exif_write_writer.py
    - tests/test_exif_write_planner.py

key-decisions:
  - "D-076: FORMATOS_APROVADOS medido é frozenset() vazio — os 4 formatos com amostra real (.jpg, .cr2, .dng, .tif) reprovaram, todos por deslocarem offset de bloco binário pré-existente (miniatura, MPF, RAW/tiles) ao inserir o bloco IPTC/XMP novo, fora do escopo hoje reconhecido por TAGS_ESTRUTURAIS_ESPERADAS (06-02). Verificado à parte (fora do script, evidência anexada à decisão): o byte a byte da miniatura embutida de um .jpg real é idêntico antes/depois do deslocamento de IFD1:ThumbnailOffset — é relocação, não perda de conteúdo. Mesmo assim, NÃO estendi TAGS_ESTRUTURAIS_ESPERADAS: é política de segurança anti-mascaramento (EXIF-04) de um arquivo fora do files_modified deste plano, decisão explicitamente deixada para o dono em D-076."
  - "Corrigido bug Rule 1 em verificacao.avisos() (06-02): usava -j do exiftool, que colapsa tags Warning/Error repetidas (um .tif real com 6 warnings devolvia 1) e incluía o resumo 'Validate' no conjunto, contando melhora (3 Warnings -> OK após a escrita) como aviso novo. Sem o fix, o .jpg reprovaria por um falso positivo de aviso, mascarando a causa real (deslocamento de offset). Corrigido para parsing de texto plano, Validate fora do conjunto."
  - "TAGS_ESTRUTURAIS_ESPERADAS não foi tocada apesar da evidência favorável — mudar a allowlist anti-mascaramento é decisão de política de segurança, não bug fix, e fica fora do escopo de arquivo deste plano (fotoorganizer/exif_write/verificacao.py não está em files_modified de 06-04)."

requirements-completed: []

# Metrics
duration: ~55min
completed: 2026-08-18
---

# Phase 6 Plan 04: Teste empírico de escrita EXIF por formato (D-03/D-04) Summary

**Medição real contra o acervo de produção (1.399 arquivos de acervo) mostra que nenhum dos 4 formatos testados (.jpg, .cr2, .dng, .tif) passa no critério de D-04 — todo formato cai hoje no fallback de sidecar XMP; a causa raiz (deslocamento de offset de bloco binário pré-existente) é registrada como candidato a decisão futura, não resolvida por este plano.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-18 (aprox., sessão contínua após 06-03)
- **Completed:** 2026-08-18
- **Tasks:** 2
- **Files modified:** 6 (1 criado, 5 modificados — incl. 2 deviations em arquivos fora do `files_modified` declarado no plano)

## Accomplishments

- `scripts/testar_escrita_exif.py`: CLI reproduzível que amostra `media_files` de acervo (`papel = 'ACERVO'` — confirmado contra o schema real que o valor gravado é o NOME do membro do enum `MediaRole`, não `.value`) do catálogo em `mode=ro`, escreve GPS/cidade/país só em cópias (`shutil.copy2` em `tempfile.mkdtemp()`, apagadas no `finally`), e aplica o critério de D-04 na íntegra usando `ExifToolWriter.escrever` e `verificacao.diferenca`/`campo_gravado`/`avisos` de produção. Sai com código 1 quando não há amostra alcançável (D-03).
- Medição real executada contra o `catalog.db` de produção: 1.384 `.jpg`, 12 `.cr2`, 2 `.dng`, 1 `.tif` — **os quatro reprovaram**, todos por deslocamento de offset de bloco binário pré-existente ao inserir metadado novo; `.tif` reprova também por tag de andaime não catalogada + 2 avisos novos.
- `fotoorganizer/exif_write/formatos.py`: `MEDIDO_EM="2026-08-18"`, `FORMATOS_APROVADOS=frozenset()` (medido, não suposto), `MOTIVOS_NAO_SUPORTADO` com motivo medido por extensão, distinguindo "reprovado no teste" de "sem amostra" (D-09) — texto literal exigido por D-05.
- `docs/DECISOES.md` D-076: entrada completa no molde de D-026/D-074, com a tabela de resultado, os 3 critérios de D-04 e o achado do byte a byte idêntico da miniatura registrado explicitamente como candidato a decisão futura do dono, não decidido aqui.
- Achado e corrigido durante a medição (Rule 1): `verificacao.avisos()` usava `-j` do exiftool, que colapsa avisos repetidos e conta melhora de contagem (`Validate: 3 Warnings` → `Validate: OK`) como aviso novo — corrigido para parsing de texto plano, com 2 testes de regressão.

## Task Commits

Each task was committed atomically:

1. **Task 1: scripts/testar_escrita_exif.py** - `441b71c` (feat) — inclui o fix de `verificacao.avisos()` (Rule 1), necessário para a medição do próprio Task 1 ser correta.
2. **Task 2: allowlist medida + D-076** - `de9468e` (feat)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified
- `scripts/testar_escrita_exif.py` - CLI de medição empírica (D-03/D-04), único script desta fase autorizado a escrever em arquivo de teste — sempre cópia, nunca original
- `fotoorganizer/exif_write/formatos.py` - `MEDIDO_EM`/`FORMATOS_APROVADOS`/`MOTIVOS_NAO_SUPORTADO` atualizados com o resultado medido
- `fotoorganizer/exif_write/verificacao.py` - `avisos()` corrigido (Rule 1): texto plano em vez de `-j`, `Validate` fora do conjunto retornado
- `docs/DECISOES.md` - D-076
- `tests/test_exif_write_writer.py` - 2 testes novos de regressão do fix de `avisos()`; 1 teste existente atualizado (não assumia mais `.jpg` aprovado)
- `tests/test_exif_write_planner.py` - 1 teste (`test_pasta_sincronizada_marcada`) isolado de D-03/D-04 via monkeypatch de `formatos.suportado`, para continuar provando D-07 independente do resultado da allowlist

## Decisions Made

Ver `key-decisions` no frontmatter. Resumo: allowlist medida é vazia; a causa raiz mais provável (deslocamento de offset, não perda de dado — verificado byte a byte numa miniatura real) é deliberadamente **não** corrigida neste plano porque mexeria em política de segurança anti-mascaramento (`verificacao.TAGS_ESTRUTURAIS_ESPERADAS`) fora do escopo de arquivo declarado, e fica registrada em D-076 como pergunta em aberto para o dono decidir com a evidência em mãos.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `verificacao.avisos()` colapsava avisos duplicados e contava melhora como aviso novo**
- **Found during:** Task 1, primeira execução real do script contra o acervo de produção.
- **Issue:** `avisos()` usava `exiftool -j` para coletar warning/error; a saída `-j` do exiftool **colapsa** tags `Warning` repetidas em uma só (medido: um `.tif` real com 6 warnings devolvia 1 via `-j`) e incluía a chave de resumo agregado `Validate` no conjunto retornado — um `.jpg` cujos 3 warnings sumiram após a escrita (exiftool renormaliza o IFD ao reescrever) registrava `"Validate: OK"` como aviso NOVO no delta `avisos_depois - avisos_antes`, quando é melhora, não regressão. A própria docstring da função dizia "conjunto de strings de warning/error" — incluir `Validate` contradizia o próprio contrato declarado.
- **Fix:** `avisos()` reescrita para parsing de texto plano (sem `-j`), que lista cada ocorrência de `Warning`/`Error` numa linha própria; `Validate` explicitamente excluído do conjunto retornado.
- **Files modified:** `fotoorganizer/exif_write/verificacao.py`
- **Verification:** 2 testes de regressão (`test_avisos_nao_conta_melhora_do_resumo_validate_como_aviso_novo`, `test_avisos_preserva_todos_os_warnings_duplicados`), com `subprocess.run` monkeypatchado para reproduzir determinísticamente os dois casos reais encontrados. Sem o fix, a reprovação do `.jpg` teria uma causa adicional espúria (aviso novo fantasma) misturada com a causa real (offset).
- **Committed in:** `441b71c` (Task 1 commit)

**2. [Rule 1 - Bug] `test_suportado_case_insensitive_e_recusa_cr3` assumia `.jpg` aprovado**
- **Found during:** Task 2, `pytest tests/test_exif_write_writer.py` após atualizar `formatos.py`.
- **Issue:** Teste de 06-02 assumia `suportado(".JPG") is True` — verdade sob a allowlist provisória, falsa sob a medida (D-076: nenhum formato aprovou).
- **Fix:** Teste reescrito para verificar case-insensitividade sem assumir aprovação (`suportado(".JPG") is suportado(".jpg")`) e a recusa de `.cr3` (D-09), ambos ainda `False` hoje.
- **Files modified:** `tests/test_exif_write_writer.py`
- **Verification:** `pytest tests/test_exif_write_writer.py -q` verde (26 testes).
- **Committed in:** `de9468e` (Task 2 commit)

**3. [Rule 1 - Bug] `test_pasta_sincronizada_marcada` (06-03) ficou acoplado ao resultado da allowlist**
- **Found during:** Task 2, `pytest -q` completo após atualizar `formatos.py` — único teste do repositório que quebrou fora de `test_exif_write_writer.py`.
- **Issue:** O teste prova D-07 (pasta sincronizada vira aviso, não bloqueio) usando um arquivo `.jpg` — com `FORMATOS_APROVADOS` vazio, o item agora é excluído por formato não suportado antes mesmo de chegar à checagem de sincronização, quebrando a asserção `incluido is True` por um motivo que não é o que o teste pretende provar.
- **Fix:** `formatos.suportado` monkeypatchado para `True` dentro do teste, isolando o comportamento de D-07 (sync) do resultado empírico de D-03/D-04 (suporte de formato) — são duas decisões independentes.
- **Files modified:** `tests/test_exif_write_planner.py`
- **Verification:** `pytest tests/test_exif_write_planner.py -q` verde (9 testes); suíte completa `pytest -q` verde (906 testes).
- **Committed in:** `de9468e` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 Rule 1 - bug fixes: 1 na medição em si, 2 em testes que assumiam a allowlist provisória)
**Impact on plan:** A primeira deviation era pré-requisito para a medição do próprio Task 1 ser confiável (sem ela, o `.jpg` reprovaria com uma causa espúria misturada à real). As outras duas são consequência direta e esperada de zerar `FORMATOS_APROVADOS` — testes que dependiam implicitamente da lista provisória precisavam se atualizar ou se desacoplar. Nenhuma mudou o comportamento de produção fora do que a medição determinou.

## Issues Encountered

**Conflito entre o gate automatizado do plano e o resultado medido, documentado explicitamente (não contornado):** o bloco `<verify>` do Task 2 e o critério 1 do `<success_criteria>` do plano assumiam que pelo menos um formato aprovaria (`assert formatos.FORMATOS_APROVADOS, 'nenhum formato aprovado'`). Rodado literalmente, esse assert **falha** — `FORMATOS_APROVADOS` é `frozenset()`. Investiguei antes de aceitar isso como resultado final: (a) confirmei que não era o bug do `avisos()` (corrigido e re-medido, resultado se manteve); (b) confirmei com um dump byte a byte que o deslocamento de offset é relocação pura, não perda de conteúdo — evidência que torna plausível que a causa seja lacuna de scaffolding, não corrupção real. Mesmo assim, optei por **não** estender `TAGS_ESTRUTURAIS_ESPERADAS` para fazer o gate passar: seria mudar a política de segurança anti-mascaramento de EXIF-04 (arquivo fora do `files_modified` deste plano) só para satisfazer uma asserção que carregava uma suposição não confirmada. O restante do gate (MEDIDO_EM preenchido, motivo de cr3/heic/heif citando "teste", `pytest` verde, D-076 registrada) passa integralmente. O gate quebrado é, em si, o achado a reportar — registrado aqui e em D-076, não escondido.

## User Setup Required

None — `exiftool` já confirmado instalado (13.55); nenhuma dependência nova.

## Next Phase Readiness

- **Achado de escopo relevante para o dono (não é um blocker técnico, é uma decisão pendente):** com a allowlist medida vazia, a Fase 6 hoje entrega escrita EXIF direta para **zero formatos** — todo arquivo cai no fallback de sidecar XMP (D-06/EXIF-05), que já está implementado desde 06-02/06-03 e continua funcionando. O alcance de "GPS/cidade/país no arquivo original" (feature #1 do roadmap v2.0) fica bloqueado até uma decisão do dono sobre estender `TAGS_ESTRUTURAIS_ESPERADAS` para reconhecer deslocamento de offset de bloco binário pré-existente como andaime — candidato plausível pela evidência (byte a byte idêntico), mas não decidido aqui. Registrado em D-076 e nos Blockers/Concerns de STATE.md.
- **Nenhum requisito EXIF-03/04/05 foi marcado como completo em REQUIREMENTS.md**, seguindo a mesma disciplina de 06-01/06-02/06-03: este plano mede e fecha a allowlist (D-03/D-04), mas EXIF-03/04 exigem o executor real com audit log (06-05, ainda não construído) e EXIF-05 exige o comportamento fim-a-fim de UI (06-06+). `requirements.mark-complete` não foi executado.
- `scripts/testar_escrita_exif.py` está pronto para reexecução: se/quando `TAGS_ESTRUTURAIS_ESPERADAS` for revisada (decisão do dono), rodar `.venv/bin/python scripts/testar_escrita_exif.py --json` de novo refaz a medição contra o catálogo atual sem nenhuma mudança de código.
- Suíte completa (`.venv/bin/python -m pytest -q`) verde: 906 passed.
- Nenhum arquivo do acervo real (`~/Pictures/2026`, `/Volumes/Externo/Fotos/Do Peru ao Chile`) foi alterado — confirmado por busca de `_original`/`.xmp` órfão nos diretórios amostrados (vazio) e por nenhum diretório temporário residual em `/tmp`.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 3 created/modified key files found on disk (scripts/testar_escrita_exif.py, fotoorganizer/exif_write/formatos.py, docs/DECISOES.md); both task commits (441b71c, de9468e) found in git log.
