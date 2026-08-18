---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Localização real e evidência expandida
status: Fase 6 em execução — plano 06-08 concluído (8/9)
stopped_at: "06-08 (checkbox por linha, badges de formato/sync, detalhamento por campo) concluído — próximo: 06-09 (documentação de arquitetura, gate completo e verificação humana do fluxo)"
last_updated: "2026-08-18T14:25:13.180Z"
last_activity: 2026-08-18 — 06-08 executado (checkbox por linha semeado do servidor D-01/D-02, badges de linha tipo B/formato não suportado e tipo C/pasta sincronizada, CORES_CAMPO e detalhamento pós-execução de 3 segmentos nomeando o campo em falha EXIF-03, 12 testes vitest; EXIF-01/EXIF-03/EXIF-05 marcados completos)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 9
  completed_plans: 8
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-16)

**Core value:** Toda sugestão é auditável até a evidência que a gerou;
nenhuma operação física acontece sem revisão humana e dry-run.
**Current focus:** v2.0 — Fases 6-11 mapeadas; próximo passo é planejar a
Fase 6 (escrita EXIF de localização).

## Current Position

Phase: 6 — Escrita EXIF de localização (em execução)
Plan: 08 de 9 concluído (+ correção 06-04b) — próximo: 06-09 (documentação de arquitetura, gate completo e verificação humana do fluxo)
Status: Fase 6 em execução — plano 06-08 concluído (8/9)
Last activity: 2026-08-18 — 06-08 executado (checkbox por linha semeado do servidor D-01/D-02, badges de linha tipo B/formato não suportado e tipo C/pasta sincronizada, CORES_CAMPO e detalhamento pós-execução de 3 segmentos nomeando o campo em falha EXIF-03, 12 testes vitest; EXIF-01/EXIF-03/EXIF-05 marcados completos em REQUIREMENTS.md)

Progresso v2.0: [░░░░░░░░░░] 0/6 fases

## Performance Metrics

**Velocity:**

- Total plans completed: 18
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 1 | - | - |
| 02 | 1 | - | - |
| 03 | 2 | - | - |
| 04 | 7 | - | - |
| 05 | 5 | - | - |
| 06 P01 | 24min | 3 tasks | 4 files |
| 06 P02 | 9min | 3 tasks | 6 files |
| 06 P03 | 14min | 2 tasks | 2 files |
| 06 P04 | 55min | 2 tasks | 6 files |
| 06 P04b (correção D-077) | ~90min | 5 tasks | 6 files |
| 06 P05 | ~35min | 3 tasks | 3 files |
| 06 P06 | ~25min | 3 tasks | 5 files |
| 06 P07 | ~20min | 2 tasks | 4 files |
| 06 P08 | ~25min | 3 tasks | 2 files |

**Recent Trend:**

- Last 5 plans: 06-04b (~90min, correção), 06-05 (~35min), 06-06 (~25min), 06-07 (~20min), 06-08 (~25min)
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (sample of the
73-entry log in `docs/DECISOES.md`).

Recent decisions affecting current work:

- Ordem das fases v2.0 fixada pelo dono na discussão de
  `/gsd:new-milestone`: EXIF → GenAI → Picker → Sidebar → Confiança →
  Corroboração. Não reordenar sem sinalizar. Coincide com a única troca
  que a pesquisa recomendava (Picker antes de Sidebar, por conflito de
  arquivo).

- D-075 autoriza escrita EXIF de localização em campo vazio (revoga parte
  do invariante 7). EXIF-03 refina "hash antes/depois" de D-075 para
  **diff de tags** antes/depois — hash de arquivo inteiro muda por
  construção numa mutação intencional. Ver nota em REQUIREMENTS.md §
  Traceability.

- GenAI de pasta é **interativa por sessão** (custo confirmado antes de
  rodar), não varredura em lote — fecha a lacuna "batch vs. síncrono" da
  pesquisa. Modelo é **Sonnet 5, nunca Haiku** (precedente D-059/D-060;
  entrada esparsa aumenta risco de alucinação).

- Índice de saúde é **distribuição por dimensão** (% alta em localização,
  data, categoria + bucket "sem evidência"), nunca score único — score
  combinado violaria o modelo elo-mais-fraco de D-017 um nível acima
  (classe de bug que já vazou em D-071).

- Progresso de importação continua **linear** com granularidade extra
  (taxa, ETA, contagem) — gauge radial descartado explicitamente pelo
  dono.

- Corroboração generalizada aterrissa **estreita**, direto em
  `grouping/correlacao.py`; abstração compartilhada só com segundo
  consumidor real. Campo categórico usa correspondência exata, nunca
  limiar fuzzy. Nenhum bônus de confiança sem medição própria contra
  acervo real (a calibração de GPS de D-074 não transfere por analogia).

- Roadmap scope: mapa do lugar estimado e demais itens 1-4 do backlog v2+
  do `docs/ROADMAP.md` já estavam implementados (confirmado via
  D-031/032/033/034/065 + implementação de templates 2026-08-02) — não
  entraram como requisitos v1, foram para PROJECT.md § Validated.

- Reconectar volumes desmontados (Lightroom + Apple Fotos, ~90 mil
  registros) é o candidato de maior alavancagem do backlog, mas **não é
  decisão ainda** — ficou em REQUIREMENTS.md v2 (ARCH-01), fora das 5
  fases deste roadmap. Trazer ao dono antes de qualquer trabalho nele.

- `docs/NAVEGACAO.md` e `docs/EMPACOTAMENTO.md` tratados como DOC-precedence
  (não ADR-locked) nesta sessão, por aprovação explícita do dono — ver
  `.planning/INGEST-CONFLICTS.md`.

- Plano 06-02 entregou as primitivas de escrita (`ExifToolWriter.escrever`,
  `verificacao.diferenca`/`campo_gravado`, `pasta_sincronizada`,
  `formatos.suportado`/`motivo`) — verificação por diff completo de tags é
  o único sinal de sucesso aceito (exit code do exiftool provadamente
  insuficiente, Pitfall 2). Nenhum requisito EXIF-02/03/04/05 foi marcado
  como completo — são fundação, não o comportamento fim-a-fim (mesma
  disciplina que 06-01 já seguiu). `formatos.py` continua provisório
  (`MEDIDO_EM=None`) até 06-04 medir contra o acervo real.

- Plano 06-03 entregou `ExifWritePlanner.criar_plano_exif()`: consulta
  única de candidatos (GPS herdado ou cidade/país resolvidos), exclusão
  de mídia já resolvida por plano anterior (com reabertura automática
  após falha parcial), status/motivo por campo e classificação de linha
  (sidecar opt-in D-06, sync opt-out-com-aviso D-07). Achado que valia a
  pena registrar: `MediaFile.extensao` é gravada sem o ponto pelo
  scanner, mas `formatos.suportado()/motivo()` (06-02) espera extensão
  pontuada — todo chamador futuro dessas funções via `MediaFile.extensao`
  precisa da mesma conversão `f".{extensao.lower()}"`. Nenhum requisito
  EXIF-01/02/05 foi marcado como completo — este plano entrega o lado do
  plano, não o comportamento fim-a-fim (mesma disciplina de 06-01/06-02).

- [Phase 06-04]: D-076: allowlist medida contra o acervo real — nenhum formato aprovou (jpg/cr2/dng/tif reprovam por deslocar offset de bloco binário pré-existente ao inserir metadado; tif também por avisos novos). FORMATOS_APROVADOS vira frozenset() vazio, sidecar XMP é o único caminho de escrita hoje. Estender TAGS_ESTRUTURAIS_ESPERADAS fica como decisão futura do dono, não decidida aqui. — Byte a byte da miniatura embutida idêntico antes/depois confirma que o deslocamento é relocação, não corrupção — mas mudar a allowlist anti-mascaramento (EXIF-04) é política de segurança fora do escopo de arquivo deste plano.
- [Phase 06-04b]: D-077: dono escolheu allowlist byte a byte (AskUserQuestion) sobre o achado em aberto de D-076 — jpg/cr2 remedidos e aprovados (20/20, 12/12), dng/tif continuam reprovados por motivos distintos (dng: parsing de offset multi-tile; tif: causa não relacionada a offset, inalterada). verificacao.py ganha esperadas_condicionais/reclassificar_deslocamentos_de_offset, categoria distinta de TAGS_ESTRUTURAIS_ESPERADAS, fail-safe em toda borda.
- [Phase 06-05]: `ExifWriteExecutor.dry_run()`/`executar()` fecham o loop plano→dry-run→execução→auditoria: disco relido ao vivo em lote, reconferência TOCTOU antes de cada escrita, veredito sempre pelo diff completo de tags (nunca returncode), falha parcial registrada campo a campo, backup `_original` preservado até diff+avisos aprovarem tudo. `_executar_item` chama `reclassificar_deslocamentos_de_offset()` (D-077) depois de `diferenca()` — sem isso toda escrita real em `.jpg`/`.cr2` reprovaria de novo, regressão nomeada por 06-04b. Achado durante a integração: `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` precisou ganhar `File:FileType`/`FileTypeExtension`/`MIMEType` (andaime de criação de sidecar `.xmp` novo, nunca exercitado pela suíte de 06-02). Nenhum requisito EXIF-01..05 foi marcado como completo — falta a UI de aprovação (06-06+).
- [Phase 06]: 06-06: seis endpoints /api/exif/* espelhando /api/operacoes*, ExifWriteRepository lendo veredito e auditoria via detalhe['exif_plan_id'], JobManager.iniciar_escrita_exif rodando ExifWriteExecutor em background. Nenhum requisito EXIF-01/02/03/05 marcado completo — aprovação do dono via UI (06-07+) ainda falta.
- [Phase 06]: 06-07: EscritaExif.tsx (esqueleto) no molde de Operations.tsx, sem campo de destino (escrita in-place, D-075) — sidebar de planos, veredito com verbo "gravar", CTA "Gravar N arquivos" desabilitada sem dry-run aprovado (já dispara job.executarEscritaExif(id, null) — plano inteiro, sem seleção), estado vazio "Nada para gravar" e linha por item com os três chips de campo (GPS/Cidade/País: pronto/pulado/sem_valor). Checkbox por linha, linhas B/C (sidecar/pasta sincronizada) e detalhamento pós-execução ficam para 06-08 por delimitação explícita do próprio plano. Aba "Localização" global (fora de ABAS_COM_FONTE). Nenhum requisito EXIF-01/02 marcado completo — comportamento pós-execução (parte de EXIF-03) só fecha com 06-08.
- [Phase 06]: 06-08: EscritaExif.tsx completo — checkbox por linha (`Set<number> marcados`) semeado do servidor a cada troca de plano, nunca de "todos marcados" (D-01/D-02); CTA envia `Array.from(marcados)`, nunca `null`. Linha tipo B (formato não suportado): fundo `bg-atencao/5`, motivo sempre visível como texto (D-05), badge redundante de sidecar `.xmp` (D-06), checkbox nasce desmarcado, chips com sufixo `→ .xmp`. Linha tipo C (pasta sincronizada): badge aditivo, linha continua marcada (D-07). Linha B+C mostra os dois badges. `CORES_CAMPO` declarado no próprio arquivo (não estende `Operations.tsx::CORES_STATUS` — sem categoria para "pulado deliberado"). Detalhamento pós-execução de 3 segmentos (✓/✗/—) com linha `falha — {Campo}: {motivo}` por campo em falha (EXIF-03), `item.erro`/`backup_original` surfaceados quando existem. 12 testes vitest presos ao Copywriting Contract da UI-SPEC. **EXIF-01, EXIF-03 e EXIF-05 marcados completos em REQUIREMENTS.md** — fecham o comportamento visível ao dono para os três; EXIF-02/EXIF-04 continuam Pending (garantias de backend, fora do `requirements` frontmatter deste plano). Achado de execução: `roadmap.update-plan-progress` conta arquivos `*-PLAN.md` vs `*-SUMMARY.md` na pasta da fase e os dois batem em 9 mesmo com 06-09 (gate/verificação) ainda não executado, porque `06-04b-SUMMARY.md` (correção sem PLAN.md numerado próprio) infla a contagem de summaries — a ferramenta marcou a Fase 6 como Complete por engano; corrigido manualmente para 8/9 In Progress. Falta 06-09 (documentação de arquitetura, gate completo, verificação humana) antes de fechar a fase de verdade.

### Pending Todos

None yet.

### Blockers/Concerns

- **Fase 11 é a de maior risco de regressão do milestone**: toca o
  comportamento de herança de GPS já calibrado e medido por D-074
  (40.678 fotos, cobertura 91,1%). Critério 5 da fase exige provar
  que o GPS sai idêntico.

- **Fases 7, 10 e 11 medem contra uma base pequena, por decisão explícita
  do dono (2026-08-18).** `catalog.db` de produção só tem 2 fontes
  cadastradas hoje — `~/Users/acamerini/Pictures/2026` e
  `/Volumes/Externo/Fotos/Do Peru ao Chile` (~1.400 arquivos). As duas
  fontes que formam o grosso do acervo real (Apple Fotos só-iCloud,
  ~44.661 registros; Lightroom em volume desmontado, ~45.397 registros)
  não estão cadastradas — reconectá-las é ARCH-01, deferido pra v3+
  (ver REQUIREMENTS.md), fora de escopo desta milestone. Medição de
  custo do GenAI, baseline de confiança e calibração dos comparadores de
  corroboração são preliminares contra ~1.400 arquivos; podem precisar
  de reajuste se/quando ARCH-01 entrar. Dono optou por seguir assim em
  vez de abrir ARCH-01 agora.

- **Lacunas de pesquisa a fechar antes/durante a Fase 6** (flagadas em
  `research/SUMMARY.md`, confiança MÉDIA e de fonte externa): confiabilidade
  de escrita em CR3/HEIC e comportamento de iCloud Drive/Dropbox sob
  rename atômico do exiftool. Verificar contra a distribuição real de
  formatos do acervo antes de fechar escopo da fase.

- `catalog.db` de produção foi zerado em 2026-08-16 (backup em
  `catalog-antes-do-reset-20260816-013503.db`); nova varredura completa
  ainda não rodou. Não bloqueia planejamento, mas fases que dependem de
  medição contra o acervo real (ex. Phase 5 baseline de performance)
  precisarão de um catálogo populado primeiro.

- Dívida técnica relevante às fases 1-2: motor de sugestões e detector de
  duplicatas fazem full-scan em memória sem caminho incremental; nenhuma
  reconciliação de boot para `OperationPlan.EXECUTANDO` travado. Ver
  `.planning/codebase/CONCERNS.md`.

- ~~Escrita EXIF direta (feature #1 do roadmap v2.0) hoje não tem NENHUM formato com suporte medido~~ — **resolvido em parte por D-077 (06-04b, 2026-08-18):** o dono escolheu allowlist byte a byte (`verificacao.reclassificar_deslocamentos_de_offset`), não a extensão incondicional de `TAGS_ESTRUTURAIS_ESPERADAS` cogitada em D-076. `.jpg`/`.cr2` remedidos e aprovados (20/20, 12/12 amostras). `.dng` continua reprovado — duas de suas tags de offset (tiles demais) não dão para verificar byte a byte com o dump padrão do exiftool, fica fail-safe. `.tif` continua reprovado por motivo sempre não relacionado a offset. `.dng`/`.tif`/`.cr3`/`.heic`/`.heif` seguem no fallback de sidecar XMP.

- ~~**Atenção para 06-05 (ExifWriteExecutor):** o gate de verificação da escrita real não pode chamar só `verificacao.diferenca()` — precisa chamar `reclassificar_deslocamentos_de_offset()` depois.~~ — **resolvido em 06-05 (2026-08-18):** `_executar_item` chama a reclassificação no ponto exato especificado, com o backup `<alvo>_original` do writer como par "antes" byte a byte; provado de ponta a ponta por `test_executar_nao_regride_por_deslocamento_de_offset` (miniatura injetada via exiftool). Ver `06-05-SUMMARY.md`.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Reconhecimento/visão | FACE-01, FACE-02, VIS-01 (v2) | Deferred — bloqueado por alcance de pixel (~90% inalcançável) | Roadmap init, 2026-08-16 |
| Metadados | META-01 sidecar XMP (v2) | Deferred — sem destino de escrita para ~90 mil registros | Roadmap init, 2026-08-16 |
| Infraestrutura | SYNC-01 SyncProvider, DAM-01 lacunas de esquema (v2) | Deferred — sem urgência medida / não-bloqueio de MVP (D-008) | Roadmap init, 2026-08-16 |
| Decisão pendente | ARCH-01 reconectar volumes (v2) | Pending dono — maior alavancagem medida, forma ainda não aprovada | Roadmap init, 2026-08-16 |
| UAT | Fase 2 — verificação visual humana do filtro "Tudo" (acervo × testemunha) | Deferred — pendente desde 2026-08-16 (catálogo estava zerado na época), `02-HUMAN-UAT.md` (1 cenário aberto), `02-VERIFICATION.md` status `human_needed` | Milestone v1.0 close, 2026-08-18 |

## Session Continuity

Last session: 2026-08-18T14:25:13.172Z
Stopped at: 06-08 (checkbox por linha, badges de formato/sync, detalhamento por campo) concluído — próximo: 06-09 (documentação de arquitetura, gate completo e verificação humana do fluxo)
Resume file: .planning/phases/06-escrita-exif-de-localiza-o/06-09-PLAN.md

## Operator Next Steps

- Planejar a primeira fase com `/gsd:plan-phase 6`
- Fases 6, 7, 8, 9 e 10 estão marcadas com `UI hint` no ROADMAP —
  considerar `/gsd:ui-phase` antes de planejar cada uma (a da Fase 7 é
  estreita: só a confirmação de custo)
