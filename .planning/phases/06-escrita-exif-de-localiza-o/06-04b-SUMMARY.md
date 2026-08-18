---
phase: 06-escrita-exif-de-localiza-o
plan: 04b
subsystem: exif_write
tags: [exiftool, verificacao-byte-a-byte, allowlist, sha256, d-076, d-077]

# Dependency graph
requires:
  - phase: 06-04
    provides: "scripts/testar_escrita_exif.py, formatos.py medido (FORMATOS_APROVADOS=frozenset()), D-076 com achado byte a byte anexo (não decidido)"
provides:
  - "fotoorganizer/exif_write/verificacao.py: DiffTags.esperadas_condicionais (categoria nova), reclassificar_deslocamentos_de_offset() — allowlist byte a byte condicional para tag de offset/ponteiro, fail-safe em toda borda"
  - "scripts/testar_escrita_exif.py chamando a reclassificação com o backup <copia>_original do writer como par 'antes' byte a byte"
  - "fotoorganizer/exif_write/formatos.py remedido: FORMATOS_APROVADOS={.jpg, .jpeg, .cr2} (jpg 20/20, cr2 12/12 amostras); .dng/.tif continuam reprovados"
  - "docs/DECISOES.md D-077 — decisão do dono (AskUserQuestion), tabela remedida, relação explícita com D-076 (superado em parte)"
  - "06-04-SUMMARY.md com cross-referência a D-077 (não deixa a afirmação 'nenhum formato aprovou' stale)"
affects: [06-05, 06-06, exif_write/executor.py, exif_write/planner.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verificação byte a byte (sha256 de intervalo de arquivo, não do arquivo inteiro) como prova de relocação pura — categoria distinta de allowlist incondicional por nome de tag (TAGS_ESTRUTURAIS_ESPERADAS): aprova pelo CONTEÚDO medido a cada escrita, não pelo NOME da tag confiando que todo deslocamento futuro é inofensivo"
    - "Fail-safe por parsing estrito: exiftool devolve '(Binary data N bytes, use -b option to extract)' em vez de lista de inteiros quando um array de offsets é grande (achado real no SubIFD:TileOffsets de um .dng) — int() estrito sobre cada token detecta isso sem tentar extrair um número de dentro do texto (que seria o tamanho da descrição, não o offset)"
    - "Backup _original do exiftool (writer nunca usa -overwrite_original) reaproveitado como o par 'antes' byte a byte, sem precisar de snapshot extra no script de medição"

key-files:
  created:
    - .planning/phases/06-escrita-exif-de-localiza-o/06-04b-SUMMARY.md
  modified:
    - fotoorganizer/exif_write/verificacao.py
    - scripts/testar_escrita_exif.py
    - fotoorganizer/exif_write/formatos.py
    - tests/test_exif_write_writer.py
    - docs/DECISOES.md
    - .planning/phases/06-escrita-exif-de-localiza-o/06-04-SUMMARY.md

key-decisions:
  - "D-077: dono escolheu explicitamente 'estender allowlist com verificação byte a byte' (AskUserQuestion) — não estender TAGS_ESTRUTURAIS_ESPERADAS incondicionalmente. Categoria nova esperadas_condicionais, populada só por reclassificar_deslocamentos_de_offset(), nunca por diferenca() diretamente."
  - "Mapa fechado de 6 sufixos de tag (ThumbnailOffset, PreviewImageStart, StripOffsets, TileOffsets, JpgFromRawStart, MPImageStart) — os mesmos que apareceram como inesperada em D-076. Tag fora do mapa nunca reclassifica, mesmo que pareça um offset por convenção de nome."
  - "DNG fica parcialmente resolvido, não totalmente: duas tags de offset (SubIFD:TileOffsets, SubIFD3:TileOffsets) têm tiles demais para o dump -j -G1 -a -n expor como inteiros — vem como blob binário textual. Decisão deliberada de NÃO tentar extrair um número de dentro desse texto (armadilha: seria o tamanho da descrição, não o offset real). DNG continua reprovado, fail-safe, até uma extensão futura que use -b para ler o array real (fora do escopo desta correção)."
  - "Verificação empírica pré-implementação (não assumida): rodei exiftool -j -G1 -a -n contra amostras reais de .jpg e .dng do acervo ANTES de escrever o código, para confirmar que MPImage2:MPImageStart/MPImageLength compartilham grupo (confirmado) e que TileOffsets multi-valor vira blob binário no dump (confirmado) — evita as duas armadilhas que o advisor sinalizou antes de qualquer teste ser escrito."

requirements-completed: []

# Metrics
duration: ~90min
completed: 2026-08-18
---

# Phase 6 Plan 04b: Allowlist byte a byte para deslocamento de offset (D-077) Summary

**Correção de meio-de-fase sobre D-076: `verificacao.py` ganha uma segunda categoria de andaime — não incondicional por nome de tag, mas condicional a prova sha256 do conteúdo apontado antes/depois — e a remedição contra o acervo real aprova `.jpg` (20/20) e `.cr2` (12/12); `.dng` continua reprovado por uma limitação de parsing do próprio exiftool (tiles demais viram blob binário no dump), não por conteúdo divergente.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-08-18 (sessão de correção sobre 06-04, antes de 06-05)
- **Completed:** 2026-08-18
- **Tasks:** 5 (extensão de verificacao.py, testes de regressão, remedição + formatos.py, D-077, cross-referência em 06-04-SUMMARY.md)
- **Files modified:** 6

## Accomplishments

- `verificacao.reclassificar_deslocamentos_de_offset(diff, antes, depois, arquivo_antes, arquivo_depois)`: rebaixa de `inesperadas` para a categoria nova `esperadas_condicionais` uma tag de offset/ponteiro (6 sufixos conhecidos) só quando o par offset+tamanho, lido como bytes reais dos dois arquivos, é sha256-idêntico. Toda borda que impede a prova (tag fora do mapa, tag de tamanho ausente, tamanho que mudou, contagem que não bate, valor não-numérico, leitura que falha) mantém a tag em `inesperadas` — nunca promove por omissão.
- Validação empírica pré-implementação (antes de escrever qualquer teste, seguindo orientação do advisor): confirmado contra `.jpg`/`.dng` reais do acervo que `MPImage2:MPImageStart`/`MPImage2:MPImageLength` compartilham grupo, e que `SubIFD:TileOffsets`/`SubIFD3:TileOffsets` do DNG (muitos tiles) vêm do exiftool como `"(Binary data N bytes, use -b option to extract)"`, não lista de inteiros — a segunda descoberta explica por que o DNG fica parcialmente resolvido.
- 9 testes de regressão novos, incluindo o teste de segurança central (conteúdo pós-escrita deliberadamente corrompido continua `inesperada` e reprova) e um teste end-to-end real via exiftool (miniatura injetada num JPEG sintético, mesmo padrão do achado de D-076, sem precisar de foto real do acervo no repo).
- `scripts/testar_escrita_exif.py` passa a chamar a reclassificação usando o backup `<copia>_original` que o `writer` já deixa (nunca usa `-overwrite_original`) como o par "antes" byte a byte — nenhum snapshot extra necessário.
- Remedição contra o `catalog.db` de produção real (cópias descartáveis, nunca o original): `.jpg` 20/20, `.cr2` 12/12 (todas as amostras alcançáveis) aprovam; `.dng` 2/2 e `.tif` 1/1 continuam reprovados.
- `fotoorganizer/exif_write/formatos.py`: `FORMATOS_APROVADOS` passa de `frozenset()` para `{".jpg", ".jpeg", ".cr2"}`, docstring e `MOTIVOS_NAO_SUPORTADO` atualizados com os motivos remedidos.
- `docs/DECISOES.md` D-077: decisão do dono, tabela completa, relação explícita "supera D-076 em parte" (jpg/cr2 mudam de veredito; achado sobre `.tif` permanece válido, inalterado).
- `06-04-SUMMARY.md` ganhou um banner cross-referenciando D-077, para não deixar a afirmação original ("nenhum formato aprovou") contradizer `formatos.py` sem explicação.

## Task Commits

Each task was committed atomically:

1. **Task 1: verificacao.py extension** - `e1aa14c` (feat)
2. **Task 2: regression tests** - `8143fb3` (test)
3. **Task 3: remedição + formatos.py + fix de teste desatualizado** - `a663804` (feat)
4. **Task 4: D-077 em DECISOES.md + limpeza de placeholder D-0XX** - `3a2bee5` (docs)
5. **Task 5: cross-referência em 06-04-SUMMARY.md** - `7129166` (docs)

## Files Created/Modified

- `fotoorganizer/exif_write/verificacao.py` - `DiffTags.esperadas_condicionais`, `reclassificar_deslocamentos_de_offset()`, `_e_relocacao_comprovada()`, `_ler_intervalo()`, `_valores_numericos()`, mapa `_SUFIXOS_OFFSET_PARA_TAMANHO`
- `scripts/testar_escrita_exif.py` - chama a reclassificação antes de aplicar o critério de D-04
- `fotoorganizer/exif_write/formatos.py` - `FORMATOS_APROVADOS`/`MOTIVOS_NAO_SUPORTADO`/docstring remedidos
- `tests/test_exif_write_writer.py` - 9 testes novos + `test_suportado_case_insensitive_e_recusa_cr3` atualizado
- `docs/DECISOES.md` - D-077
- `.planning/phases/06-escrita-exif-de-localiza-o/06-04-SUMMARY.md` - banner + nota cross-referenciando D-077

## Decisions Made

Ver `key-decisions` no frontmatter. Resumo: allowlist byte a byte (não incondicional), mapa fechado de 6 sufixos, DNG deliberadamente deixado parcial (fail-safe sobre parsing, não sobre conteúdo).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_suportado_case_insensitive_e_recusa_cr3` assumia `.jpg` reprovado**
- **Found during:** Task 3, `pytest` completo após remedir `formatos.py`.
- **Issue:** Teste de 06-04 fixava `suportado(".jpg") is False`, correto sob a allowlist vazia de D-076, falso sob a remedição de D-077.
- **Fix:** Teste reescrito para o resultado remedido (`.jpg`/`.cr2` `True`, `.dng`/`.cr3` `False`), com docstring explicando a mudança.
- **Files modified:** `tests/test_exif_write_writer.py`
- **Verification:** `pytest tests/test_exif_write_writer.py tests/test_exif_write_planner.py -q` verde (44 testes); suíte completa `pytest -q` verde (915 testes).
- **Committed in:** `a663804` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — consequência direta e esperada de remedir a allowlist, mesmo padrão do que 06-04 já havia encontrado ao zerá-la).
**Impact on plan:** Nenhuma mudança de comportamento de produção fora do que a remedição determinou.

## Issues Encountered

**DNG fica parcialmente resolvido — achado real, não hipotético.** Antes de implementar, uma inspeção manual de `.dng` reais do acervo (`exiftool -j -G1 -a -n`) mostrou que `SubIFD:TileOffsets`/`SubIFD3:TileOffsets` (arquivos com muitos tiles) vêm como `"(Binary data N bytes, use -b option to extract)"`, não como lista de inteiros — o parsing estrito (`int()` por token) corretamente falha e mantém essas duas tags em `inesperadas`, então o DNG continua reprovado mesmo com a allowlist estendida. Isto não é um bug: é o comportamento fail-safe funcionando como desenhado. Estender para usar `-b` e ler o array real de offsets seria a próxima extensão, fora do escopo desta correção (D-077 documenta isso como motivo específico, não como lacuna escondida).

**Advisor sinalizou dois riscos de suposição antes de qualquer código ser escrito** (casamento de grupo `MPImage2:MPImageStart`/`MPImageLength`, e estabilidade posicional de arrays multi-valor de `StripOffsets`/`TileOffsets`) — ambos verificados empiricamente contra arquivos reais do acervo antes da implementação (não por lembrança/suposição): o casamento de grupo MPF se confirmou; a preocupação de ordenação posicional acabou moot para os casos reais medidos, porque os arrays problemáticos (DNG multi-tile) vêm como blob binário textual, então nunca chegam ao passo de zip posicional — falham no parsing antes, pelo mesmo motivo de fail-safe.

## User Setup Required

None — `exiftool` já confirmado instalado; nenhuma dependência nova. Nenhum arquivo do acervo real foi alterado (medição sempre em cópias descartáveis via `shutil.copy2`/`tempfile.mkdtemp`, confirmado por ausência de `_original`/`.xmp` órfão nos diretórios amostrados e nenhum diretório residual em `/tmp`).

## Next Phase Readiness

- Fase 6 hoje entrega escrita EXIF direta real para `.jpg`/`.jpeg`/`.cr2` — não mais zero formatos. `.dng`/`.tif` continuam no fallback de sidecar XMP (D-06/EXIF-05).
- `06-05-PLAN.md` (ExifWriteExecutor: dry-run autoritativo, escrita verificada, falha parcial e backup) segue como próximo passo — nenhuma mudança de escopo necessária, `formatos.suportado()` já reflete o resultado atualizado e o executor deve consumi-lo sem alteração.
- Se/quando o dono quiser fechar o `.dng` parcial, o candidato natural é estender `_valores_numericos`/`_ler_intervalo` (ou uma função irmã) para reler a tag via `exiftool -b` quando o dump vier como blob binário — não decidido aqui, fica registrado como lacuna conhecida em D-077.
- Suíte completa (`.venv/bin/python -m pytest -q`) verde: 915 passed.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 6 created/modified key files found on disk (verificacao.py, testar_escrita_exif.py, formatos.py, test_exif_write_writer.py, DECISOES.md, 06-04-SUMMARY.md) plus this file (06-04b-SUMMARY.md); all 5 task commits (e1aa14c, 8143fb3, a663804, 3a2bee5, 7129166) found in git log.
