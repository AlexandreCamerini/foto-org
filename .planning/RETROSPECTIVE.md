# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP + Preparação para lançamento

**Shipped:** 2026-08-18
**Phases:** 5 | **Plans:** 16 | **Sessions:** ~2 (ingest + execução multi-fase)

### What Was Built
- Modelo de dois instantes fechado (`tz_estimado` gravado direto a partir do país já atribuído)
- Distinção acervo × testemunha corrigida no filtro "Tudo" da Biblioteca
- Revisão e navegação por teclado fechadas ponta a ponta (busca não vaza entre grupos/abas)
- Consistência visual secundária: selos de fonte/álbum×evento, estados de erro explícitos, modal de pasta unificado nos 4 pontos de entrada
- Índices de FK ausentes fecham o table scan de `pasta` (`SEARCH`, não `SCAN`)
- App empacotado (Marco 1, Tauri v2 + Python embarcado), onboarding validado com dois usuários reais sem instrução, baseline de performance documentado
- (fora do roadmap formal, mesma sessão) Interpolação de duas âncoras no `herdar_gps()` — corroboração entre doadores antes/depois em vez de extrapolação de âncora única

### What Worked
- Worktrees paralelas por wave (isolation="worktree") cortaram tempo de execução real — Wave 1 da Fase 5 rodou 05-01 e 05-02 simultaneamente sem conflito de arquivo, detectado corretamente porque `files_modified` não se sobrepunha entre planos.
- O ciclo pesquisa → plan-checker → revisão (2 iterações) pegou 1 blocker e 4 warnings reais antes da execução — todos mecânicos e baratos de corrigir (marcadores de `<automated>` que nunca podiam falhar, `Open Questions` não marcadas como resolvidas). Vale manter o ciclo mesmo quando parece burocrático.
- Delegar a calibração empírica (`scripts/calibrar_raio_incerteza.py` estendido) para o agente em vez de aceitar um bônus de confiança "por elegância" evitou introduzir uma constante inventada — a medição real (91,1% de cobertura no caso discordante, contra 97,5% no concordante) é o que sustenta a decisão, não intuição.
- Verificação goal-backward pegou um gap real e não-óbvio: `REQUIREMENTS.md` nunca foi atualizado por 2 dos 5 planos da Fase 5, apesar dos SUMMARYs declararem `requirements-completed` e o ROADMAP já marcar a fase como 5/5. Sem essa checagem, o milestone teria fechado com rastreabilidade quebrada.

### What Was Inefficient
- Um `kill -TERM` direto no processo backend (em vez de fechar o app pelo caminho gracioso) durante um reset de catálogo no meio da sessão deixou um processo zumbi que um agente de execução paralelo depois reportou como "achado urgente" — era efeito colateral do orquestrador, não bug do produto. Custou uma rodada de investigação e uma correção de registro no relatório de aceite. Lição: preferir sempre o caminho de encerramento gracioso da própria aplicação, mesmo em ambiente descartável.
- Um agente de fatia-vertical rodou com `isolation="worktree"` sem checagem explícita de base — o harness bifurcou de `main` (parado 133 commits atrás), não da branch de trabalho atual. O commit final ficou correto (só tocava os arquivos pretendidos), mas o merge exigiu diagnóstico extra (`git merge-base`, `git rev-list --count`) pra confirmar que era seguro. Lição: quando não se está usando o prompt padrão do executor de fase (que já inclui a checagem de base), validar a base do worktree manualmente antes do merge, não confiar que `isolation="worktree"` sempre bifurca do HEAD esperado.
- Um agente de checkpoint recusou corretamente uma instrução relayed via `SendMessage` do orquestrador (decisão real do dono, mas entregue pelo canal errado) — comportamento correto de segurança, mas custou um ciclo extra de spawn de agente fresco com `<completed_tasks>` explícito. Lição confirmada, não nova: checkpoints de plano GSD exigem spawn fresco pra retomar, nunca `SendMessage` — mesmo quando o orquestrador tem certeza da autorização.

### Patterns Established
- Reteste comportamental de UAT depois de um fix de bug de UI não é opcional quando o critério original era comportamental por desenho (D-06) — inspeção de código/CSS e teste de regressão automatizado provam que o bug não volta, não que o fluxo funciona pra um humano de verdade. `05-HUMAN-UAT.md` como artefato formal pra rastrear esse reteste até ele acontecer, em vez de fechar a fase com uma ressalva solta em texto.
- Quando o catálogo de produção precisa ser resetado no meio de uma sessão de execução (não só de planejamento), a decisão de "com ou sem backup" e o escopo exato da nova importação devem ser confirmados via pergunta direta ao dono, nunca assumidos — mesmo quando o pedido original parecia dar carta branca.

### Key Lessons
1. Delegar sempre que a tarefa pedir validação empírica contra dado real (não teórica) — o agente que tinha acesso ao catálogo de produção e ao script de calibração já existente produziu um número medido, não uma estimativa.
2. Checkpoints humanos em planos GSD são o ponto certo pra parar de verdade — nenhuma tentativa de simular/pular um teste de usuário sem instrução ou uma decisão de escopo de dado real deve acontecer sem confirmação explícita do dono.
3. Trabalho descoberto durante um checkpoint (ex.: pedido de feature nova numa resposta de checkpoint) não vira escopo automático — vale registrar como item de backlog explícito (`spawn_task`) e seguir com a pergunta original.

### Cost Observations
- Model mix: majoritariamente Sonnet (planner em Opus por config do projeto; pesquisa/execução/verificação em Sonnet)
- Sessions: 1 sessão de execução longa cobrindo ingest → planejamento → 3 waves de execução → fatia-vertical paralela → fechamento de milestone
- Notável: paralelismo de wave (2 executores simultâneos em worktrees) foi o maior ganho de tempo de parede desta fase; o ciclo de revisão de plano (checker + 1 rodada de revisão) teve retorno alto pra custo baixo — todos os achados eram mecânicos e rápidos de corrigir

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~2 | 5 | Primeiro milestone do projeto — GSD adotado via ingest de 25 documentos pré-existentes, não greenfield |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 867 backend + 151 frontend | não medido formalmente | 0 (nenhuma dependência nova adicionada nesta fase) |

### Top Lessons (Verified Across Milestones)

1. Checkpoints humanos GSD exigem spawn fresco com `<completed_tasks>` pra retomar — nunca confiar em mensagem relayed de outro agente como autorização, mesmo quando a autorização é real.
2. Validação empírica contra dado real vence estimativa/elegância toda vez que há dataset disponível para medir — mesmo que o dataset precise ser um backup, não o catálogo vivo.
