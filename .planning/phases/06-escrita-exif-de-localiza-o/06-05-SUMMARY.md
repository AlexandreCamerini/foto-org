---
phase: 06-escrita-exif-de-localiza-o
plan: 05
subsystem: exif_write
tags: [exiftool, dry-run, diff-de-tags, audit-log, falha-parcial, d-077]

# Dependency graph
requires:
  - phase: 06-01
    provides: "ExifWritePlan/ExifWriteItem com status por campo, AuditLog reusado com plan_id=None"
  - phase: 06-02
    provides: "ExifToolWriter.escrever, verificacao.dump/dump_lote/avisos/diferenca/campo_gravado, formatos.py"
  - phase: 06-03
    provides: "ExifWritePlanner.criar_plano_exif() — candidatos, valor e status por campo, classificação de linha"
  - phase: 06-04b
    provides: "verificacao.reclassificar_deslocamentos_de_offset() (D-077) — allowlist byte a byte condicional; formatos.py remedido (.jpg/.jpeg/.cr2 aprovados)"
provides:
  - "ExifWriteExecutor.dry_run() — passo autoritativo que relê o disco AO VIVO em lote (dump_lote) e promove cada campo a PRONTO/PULADO/SEM_VALOR/FALHA"
  - "ExifWriteExecutor.aplicar_selecao() — materializa D-02 (opt-out por item) antes da execução começar"
  - "ExifWriteExecutor.executar()/_executar_item() — dupla porta (dry-run feito + aprovou algo), reconferência ao vivo (TOCTOU) antes de escrever, veredito por diff completo de tags nunca por returncode, falha parcial registrada campo a campo, backup _original apagado só após diff+avisos aprovarem tudo"
  - "Integração correta com reclassificar_deslocamentos_de_offset() (D-077) — sem isso, toda escrita real em .jpg/.cr2 reprovaria de novo por deslocamento de offset de bloco binário pré-existente"
  - "verificacao.TAGS_ESTRUTURAIS_ESPERADAS estendida com File:FileType/FileTypeExtension/MIMEType — andaime de criação de sidecar .xmp novo, achado real ao integrar o executor com o caminho de sidecar"
affects: [06-06, 06-07, 06-08, 06-09, server/app.py rotas /api/exif, repositories/exif_write.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dry-run autoritativo relendo o disco ao vivo em lote (dump_lote), não item a item — mesmo raciocínio de custo do scanner de leitura aplicado à escrita"
    - "reconferência ao vivo (TOCTOU) imediatamente antes de montar os argumentos de escrita, não só no dry-run — é isto que torna o rerun idempotente sem depender do dry-run estar fresco"
    - "backup _original do exiftool como recuperação durante a janela entre escrita e verificação, apagado só depois do diff+avisos aprovarem tudo — nunca 'restaurado' automaticamente, o app não desfaz nada sozinho"
    - "diff completo de tags (com reclassificação condicional de offset) como único veredito de escrita, nunca o exit code do subprocesso — generaliza o padrão de 06-02/06-04b para o caminho de execução real"

key-files:
  created:
    - tests/test_exif_write_executor.py
  modified:
    - fotoorganizer/exif_write/executor.py
    - fotoorganizer/exif_write/verificacao.py

key-decisions:
  - "_executar_item() chama verificacao.reclassificar_deslocamentos_de_offset() entre diferenca() e o veredito por campo, usando o backup <alvo>_original do writer como par 'antes' byte a byte — exatamente o padrão de scripts/testar_escrita_exif.py::testar_amostra(), nomeado como risco central deste plano em 06-04b-SUMMARY.md. Sem essa chamada, toda escrita real em .jpg/.cr2 reprovaria de novo por IFD1:ThumbnailOffset/similares, uma regressão silenciosa da allowlist que D-077 acabou de aprovar."
  - "TAGS_ESTRUTURAIS_ESPERADAS (verificacao.py, fora do files_modified original do plano) ganhou File:FileType/FileTypeExtension/MIMEType — achado real, não hipotético: ao integrar o executor com o caminho de sidecar (item com formato_suportado=False), diferenca({}, dump_do_xmp_recem_criado) classificava essas três tags como inesperadas, reprovando TODA escrita de sidecar. A causa é estrutural (o .xmp não existia antes, então seu 'antes' é {} — o próprio dump não tem tipo de arquivo para comparar), não localização fora de escopo. A suíte de 06-02 nunca chamou diferenca() no caminho de sidecar, por isso o gap não apareceu antes."
  - "Rerodar o mesmo plano sem novo dry-run é idempotente por DOIS mecanismos, não um só: (1) o filtro de 'pendentes' em executar() já exclui item cujo status não é mais PRONTO (terminal: GRAVADO/PULADO/SEM_VALOR/FALHA), então _executar_item nem é chamado de novo; (2) mesmo se fosse chamado, a reconferência ao vivo do passo 5 (TOCTOU) pularia sem subprocesso. O teste de idempotência exercita o mecanismo (1), que é o caminho real que o rerun toma."
  - "Rodar dry_run() DE NOVO depois de um plano já totalmente resolvido faz o PRÓPRIO dry-run reportar prontos=0 — a dupla porta de executar() (mesma lógica do analog de cópia física) corretamente recusa 'executar' um lote vazio nesse caso, em vez de silenciosamente devolver stats zerados. Não é bug: é o mesmo gate que já existe para 'origens todas num volume desmontado' no domínio de cópia física, generalizado para 'nada mais a gravar'."
  - "**REQUIREMENTS.md NÃO foi marcado como completo para EXIF-01/02/03/04/05**, seguindo a mesma disciplina de 06-01/06-02/06-03/06-04b: este plano entrega o executor (dry-run autoritativo + execução verificada + backup + audit), mas o comportamento fim-a-fim que o texto de cada requisito descreve inclui a aprovação do dono via UI (06-06+, ainda não construída). `requirements.mark-complete` não foi executado."

patterns-established:
  - "Guarda de dupla porta (dry_run_em is None + prontos==0) reusada literalmente do domínio de cópia física, mas com a leitura do veredito via JSON path (AuditLog.detalhe['exif_plan_id'].as_integer()) em vez da coluna plan_id — necessário porque AuditLog.plan_id tem FK real para operation_plans.id, não para exif_write_plans.id (Pitfall 5, 06-01)."

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-08-18
---

# Phase 6 Plan 05: ExifWriteExecutor — dry-run autoritativo e escrita verificada Summary

**`ExifWriteExecutor.dry_run()`/`executar()` fecham o loop plano→dry-run→execução→auditoria da Fase 6: disco relido ao vivo em lote, reconferência TOCTOU antes de cada escrita, veredito sempre pelo diff completo de tags (com a reclassificação condicional de offset de D-077 corretamente encadeada), falha parcial registrada campo a campo e backup `_original` preservado até o diff aprovar tudo.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-18
- **Tasks:** 3
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments

- `ExifWriteExecutor.dry_run()`: relê o disco AO VIVO em uma única invocação em lote (`verificacao.dump_lote`) e promove cada um dos 3 campos a `PRONTO`/`PULADO`/`SEM_VALOR`/`FALHA` com motivo — inclui a checagem de "sidecar já existe" (invariante 3 aplicado ao sidecar) e a recomputação de `pasta_sincronizada` (o arquivo pode ter mudado de lugar desde o scan).
- `ExifWriteExecutor.aplicar_selecao()`: materializa D-02 no banco antes da execução começar, com audit log próprio.
- `ExifWriteExecutor.executar()`/`_executar_item()`: dupla porta (dry-run feito + aprovou algo), reconferência ao vivo (TOCTOU) imediatamente antes de montar os argumentos de escrita, escrita via `ExifToolWriter`, veredito por `verificacao.campo_gravado()` sobre o diff — **nunca** `returncode` (0 ocorrências no arquivo). Falha parcial e falha de verificação (tags fora de escopo, avisos novos) preservam o backup `_original`; sucesso total apaga o backup só depois de tudo aprovado.
- **Integração crítica com D-077 (06-04b)**: `_executar_item` chama `verificacao.reclassificar_deslocamentos_de_offset()` entre `diferenca()` e o veredito por campo — a ausência dessa chamada era o risco nomeado explicitamente em `06-04b-SUMMARY.md § Next Phase Readiness` como a forma mais provável deste plano regredir silenciosamente a allowlist de `.jpg`/`.cr2`. Provado de ponta a ponta por `test_executar_nao_regride_por_deslocamento_de_offset` (miniatura injetada via exiftool, mesmo achado real de D-076/D-077).
- 13 testes automatizados cobrindo EXIF-01 a EXIF-05, os critérios 1-6 do roadmap, idempotência do rerun e a política do backup — ver `Deviations` para o teste além dos 12 do `<behavior>` do plano.
- Achado e corrigido durante a integração (Rule 1): `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` não cobria `File:FileType`/`File:FileTypeExtension`/`File:MIMEType`, que aparecem como "inesperadas" toda vez que um sidecar `.xmp` é criado pela primeira vez (o "antes" do diff é `{}` porque o arquivo não existia) — sem o fix, `test_formato_nao_suportado_grava_sidecar` reprovava com os 3 campos em `FALHA` mesmo com o conteúdo correto gravado.

## Task Commits

Each task was committed atomically:

1. **Task 1: dry_run autoritativo, guarda e aplicar_selecao** - `d98ce64` (feat)
2. **Task 2: executar + _executar_item com verificação por diff e falha parcial** - `af38eb1` (feat)
3. **Task 3: suíte do executor — EXIF-01..05 e idempotência** - `a30ceb6` (test, inclui fix de verificacao.py)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified

- `fotoorganizer/exif_write/executor.py` - `DryRunObrigatorioExif`, `ExifWriteExecutor` (`dry_run`, `aplicar_selecao`, `executar`, `_executar_item`, `_audit_item`)
- `fotoorganizer/exif_write/verificacao.py` - `TAGS_ESTRUTURAIS_ESPERADAS` estendida com 3 tags de andaime de criação de sidecar (deviation)
- `tests/test_exif_write_executor.py` - 13 testes, fixture `ambiente` com planner real + helpers `_item_manual`/`_media_avulsa`/`hashes`

## Decisions Made

Ver `key-decisions` no frontmatter para o raciocínio completo. Resumo: a chamada a `reclassificar_deslocamentos_de_offset()` foi implementada exatamente no ponto e com os argumentos que `06-04b-SUMMARY.md` já havia especificado; a extensão de `TAGS_ESTRUTURAIS_ESPERADAS` foi necessária para o caminho de sidecar funcionar e é andaime estrutural genuíno (não localização), justificado tag a tag como as quatro entradas anteriores; REQUIREMENTS.md permanece com EXIF-01..05 em aberto, seguindo a disciplina já estabelecida pelos planos anteriores da fase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` não cobria a criação de sidecar novo**
- **Found during:** Task 3, primeira execução real de `test_formato_nao_suportado_grava_sidecar` contra o binário exiftool.
- **Issue:** `_executar_item` escreve num `.xmp` que ainda não existe (`destino != origem`, alvo inexistente); o "antes" do diff é `{}` (o arquivo não existia). O exiftool cria o arquivo e o dump "depois" inclui `File:FileType`, `File:FileTypeExtension` e `File:MIMEType` (descrição do CONTAINER: "isto é um XMP"), que `diferenca()` classificava como `inesperadas` — reprovando os 3 campos mesmo com o conteúdo de localização correto gravado. A suíte de 06-02 nunca exercitou esta combinação (seus testes de sidecar checam conteúdo, não chamam `diferenca()` no caminho de sidecar).
- **Fix:** as 3 tags adicionadas a `TAGS_ESTRUTURAIS_ESPERADAS` (não a `TAGS_VOLATEIS` nem a um prefixo `File:` inteiro — cada uma individualmente justificada, mesma disciplina das 4 entradas anteriores), com comentário explicando a causa (arquivo que não existia antes).
- **Files modified:** `fotoorganizer/exif_write/verificacao.py`
- **Verification:** `test_formato_nao_suportado_grava_sidecar` passa (status `GRAVADO` nos 3 campos); suíte completa de `verificacao`/`writer` (35 testes) e a suíte nova do executor (13 testes) verdes; suíte completa do repositório (928 testes) verde.
- **Committed in:** `a30ceb6` (Task 3 commit)

**2. [Rule 2 - Cobertura crítica ausente] Teste adicional de regressão da integração com D-077**
- **Found during:** Orientação antes de escrever Task 3 — `06-04b-SUMMARY.md § Next Phase Readiness` nomeia explicitamente o risco de esta integração faltar silenciosamente, e nenhum dos 12 testes do `<behavior>` original do plano usa um arquivo com bloco binário pré-existente (miniatura) capaz de reproduzir o deslocamento de offset — `make_jpeg()` não embute miniatura.
- **Ação:** adicionado `test_executar_nao_regride_por_deslocamento_de_offset`, que injeta uma miniatura real via exiftool (mesma técnica de `test_exif_write_writer.py::test_reclassificar_offset_real_byte_identico_vira_esperada_condicional`, 06-04b) e prova de ponta a ponta, via `dry_run()`+`executar()`, que os 3 campos terminam `GRAVADO` — só possível se `reclassificar_deslocamentos_de_offset()` estiver corretamente encadeada em `_executar_item`.
- **Impacto no critério de aceite do plano:** a suíte reporta **13 passed**, não os 12 literais do `<acceptance_criteria>` do Task 3 (`"12 passed, 0 failed"`). Julgamento: a cobertura substantiva do plano (EXIF-01..05, idempotência, política de backup) permanece intacta nos 12 testes originais; o 13º prova exatamente a propriedade que a plan-file de 06-04b identificou como o risco central deste plano nomeadamente — omiti-lo para bater a contagem literal teria deixado sem prova automatizada a garantia mais crítica desta entrega.
- **Files modified:** `tests/test_exif_write_executor.py`
- **Verification:** teste passa; sem a chamada a `reclassificar_deslocamentos_de_offset()` em `_executar_item` (testado manualmente comentando a chamada), o mesmo teste reprova com os 3 campos em `FALHA` — confirma que o teste de fato pega a regressão que existe para prevenir.

---

**Total deviations:** 2 (1 Rule 1 - bug fix necessário para o caminho de sidecar funcionar; 1 Rule 2 - teste adicional para uma garantia de correção nomeada explicitamente pelo plano anterior)
**Impact on plan:** Nenhuma mudança de escopo além do necessário para o executor funcionar corretamente nos dois caminhos que o próprio plano exige (escrita direta e sidecar) e para provar automaticamente a integração com D-077 que 06-04b sinalizou como risco central.

## Issues Encountered

Nenhum além dos dois itens documentados acima em Deviations.

## User Setup Required

None — `exiftool` já confirmado instalado; nenhuma dependência nova.

## Next Phase Readiness

- `fotoorganizer.exif_write.executor.ExifWriteExecutor` está pronto para os planos de UI (06-06+) consumirem `dry_run()`/`aplicar_selecao()`/`executar()` exatamente na forma declarada no bloco `<interfaces>` do plano.
- **Nenhum requisito EXIF-01/02/03/04/05 foi marcado como completo em REQUIREMENTS.md** — este plano entrega o executor completo (backend), mas o texto de cada requisito inclui a aprovação do dono via UI, que só chega em 06-06+. `requirements.mark-complete` não foi executado.
- `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` agora cobre o caminho de sidecar novo além do caminho de escrita direta — planos futuros que escrevam sidecar `.xmp` por este writer não precisam repetir esta descoberta.
- Suíte completa (`.venv/bin/python -m pytest -q`) verde: 928 passed (era 915 antes deste plano + 13 testes novos).
- Nenhum arquivo fora de `fotoorganizer/exif_write/executor.py`, `fotoorganizer/exif_write/verificacao.py` (deviation) e `tests/test_exif_write_executor.py` foi modificado, confirmado por `git status --short`.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 3 key files found on disk (executor.py, test_exif_write_executor.py, this SUMMARY); all 3 task commits (d98ce64, af38eb1, a30ceb6) found in git log.
