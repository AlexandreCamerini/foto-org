# Roadmap: Foto Organizer

## Milestones

- ✅ **v1.0 MVP + Preparação para lançamento** — Phases 1-5 (shipped 2026-08-18) — [detalhe](milestones/v1.0-ROADMAP.md)
- 🚧 **v2.0 Localização real e evidência expandida** — Phases 6-11 (planejado 2026-08-18)

## Phases

**Phase Numbering:**

- Integer phases (6, 7, 8): Planned milestone work
- Decimal phases (6.1, 6.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>✅ v1.0 (Phases 1-5) — SHIPPED 2026-08-18</summary>

- [x] Phase 1: Timezone estimado (1/1 plano) — completed 2026-08-16
- [x] Phase 2: Correção de dados medidos (1/1 plano) — completed 2026-08-16
- [x] Phase 3: Revisão acessível e consistente (2/2 planos) — completed 2026-08-16
- [x] Phase 4: Consistência visual secundária (7/7 planos) — completed 2026-08-17
- [x] Phase 5: Preparação para lançamento (5/5 planos) — completed 2026-08-18

Detalhe completo de cada fase (goal, success criteria, planos, decisões):
[`milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md)

</details>

### 🚧 v2.0 Localização real e evidência expandida (em andamento)

**Milestone Goal:** Expandir a cobertura de evidência de localização (EXIF
real escrito no original, GenAI de nome de pasta) e a UI que expõe isso ao
dono (picker nativo, sidebar navegável, confiança como eixo, corroboração
generalizada além de GPS).

- [x] **Phase 6: Escrita EXIF de localização** - Localização inferida vira EXIF real no arquivo original, só em campo vazio, via plano dry-run aprovado (completed 2026-08-18)
- [ ] **Phase 7: Classificação de pasta por GenAI** - Nome de pasta vira evidência de cidade/evento por sessão opt-in com custo confirmado antes
- [ ] **Phase 8: Picker nativo + progresso de importação** - Diálogo nativo do macOS substitui o caminho digitado; barra linear ganha taxa/ETA/contagem
- [ ] **Phase 9: Sidebar navegável** - Busca incremental e navegação por teclado na árvore de pastas
- [ ] **Phase 10: Confiança como eixo + índice de saúde** - Filtrar por faixa de confiança e ver saúde do acervo como distribuição por dimensão
- [ ] **Phase 11: Motor de corroboração generalizado** - Confronto antes-E-depois de D-074 estendido a data/hora e cidade/país, cada tipo com medição própria

**Ordem das fases:** definida pelo dono na discussão de `/gsd:new-milestone`
(EXIF → GenAI → Picker → Sidebar → Confiança → Corroboração). A pesquisa
(`research/SUMMARY.md` § Phase Ordering Rationale) sugeria trocar Picker e
Sidebar por evitação de conflito de arquivo — a ordem do dono já coincide
com essa recomendação (Picker antes de Sidebar). Nenhuma dependência é
dura: as seis são independentes no nível de esquema; a ordem otimiza
risco-de-invariante primeiro, conflito de arquivo e composição de valor.

## Phase Details

### Phase 6: Escrita EXIF de localização

**Goal**: O dono grava no EXIF do arquivo original a localização que o motor
já inferiu (GPS lat/long, cidade, país), exclusivamente em campo vazio, com
a mesma disciplina de plano → dry-run → aprovação → verificação que
`operations/` impõe à cópia — mas num módulo próprio, porque mutação
in-place não é cópia.
**Depends on**: Nada (D-075 já decidida; independente das demais fases no
nível de esquema)
**Requirements**: EXIF-01, EXIF-02, EXIF-03, EXIF-04, EXIF-05

**Escopo expandido em `/gsd:discuss-phase 6` (2026-08-18):** formato
reprovado no teste empírico de escrita (D-03/D-04 em `06-CONTEXT.md`)
ganha oferta de sidecar XMP como alternativa no mesmo plano — não fica
só marcado "não suportado" sem caminho. Isso muda a linha "Explicitly
out of scope" abaixo (sidecar XMP deixou de estar fora do escopo) e
adiciona EXIF-05. Escrever um sidecar-writer mínimo (só os 3 campos de
localização, mesmo escopo estreito de EXIF-01..04) faz parte da Fase 6.

**Abordagem travada** (decidida em pesquisa + assinatura do dono — não
re-derivar no planejamento):

- Módulo **novo e próprio** (ex.: `fotoorganizer/exif_write/`). **Não**
  estender `operations/executor.py`: o truque de segurança da cópia
  (criação exclusiva num caminho novo que ainda não existe) não tem
  equivalente para mutação in-place. Modelo de plano/item estruturalmente
  paralelo a `operations/`, sem herdar dele; reusa `AuditLog` e os helpers
  de `security/` (validação de caminho, hash).

- Verificação é **diff completo de tags antes/depois**, não hash do arquivo
  inteiro. Refinamento consciente de D-075 (que dizia "hash antes/depois"):
  a escrita é mutação intencional, então o hash do arquivo *tem* que mudar —
  ele serve como fato de auditoria, nunca como critério de aprovação. O
  critério é: as tags de localização esperadas foram gravadas e **nenhuma
  outra tag mudou**.

- Escrita só acontece depois de **plano dry-run aprovado explicitamente**.
  Sem aprovação, zero bytes tocados.

- Audit log precisa registrar **falha parcial** (quais tags entraram antes
  do erro), não só sucesso/erro binário.

- Pré-condição "campo vazio" é também o mecanismo de recuperação de crash:
  reexecutar o plano é idempotente.

- **Decisões de `/gsd:discuss-phase 6` (2026-08-18, ver `06-CONTEXT.md`
  para o detalhe completo):** aprovação do plano é em lote com checkbox
  por linha para desmarcar item pontual (não arquivo por arquivo); teste
  empírico de escrita cobre todo formato RAW/proprietário do acervo real
  (não só CR3/HEIC), critério de "passou limpo" é diff de tags + arquivo
  abre normalmente depois; arquivo em pasta sincronizada (iCloud
  Drive/Dropbox) é detectado e marcado no plano com aviso de risco, dono
  decide incluir; os 3 campos (GPS, cidade, país) são sempre tentados
  juntos por arquivo, sem seleção por sessão.

**Success Criteria** (what must be TRUE):

  1. Antes de qualquer escrita, o dono vê um plano dry-run que lista, por
     arquivo, quais campos de localização estão vazios e qual valor
     entraria — e nada é escrito enquanto ele não aprovar.

  2. A execução aprovada preenche apenas campo vazio; arquivo com GPS,
     cidade ou país já preenchido sai como "pulado" com o motivo visível,
     mesmo quando a sugestão discorda do valor existente.

  3. Cada arquivo escrito é verificado por diff de tags antes/depois, que
     prova as tags de localização gravadas e que nenhuma tag fora de
     localização mudou.

  4. Escrita interrompida no meio (permissão negada, volume desmontado,
     formato recusado) aparece no audit log como falha parcial com as tags
     efetivamente gravadas, e rerodar o mesmo plano é idempotente.

  5. Nenhum campo EXIF fora de localização (data, câmera, autor) é escrito
     em nenhum caminho de código, provado por teste que compara o dump
     completo de tags antes/depois.

  6. Arquivo cujo formato reprova o teste empírico de escrita (CR3, HEIC
     ou qualquer RAW/proprietário do acervo real) aparece no plano como
     "formato não suportado" com motivo visível, e o dono pode optar por
     sidecar XMP para aquele arquivo específico no mesmo plano.

**Explicitly out of scope**: sobrescrita de campo já preenchido; qualquer
campo fora de localização; exclusão de arquivo; sidecar XMP para
qualquer campo fora de localização ou para arquivo cujo formato passou
no teste de escrita EXIF (o sidecar é oferta específica de fallback
para formato reprovado — EXIF-05 — não um caminho paralelo geral).
**Plans**: 9 plans em 7 waves

Plans:

- [x] 06-01-PLAN.md — Modelos ExifWritePlan/ExifWriteItem (status por campo) + migração 0019
- [x] 06-02-PLAN.md — Writer exiftool, verificação por diff de tags, sync-detect e allowlist de formatos
- [x] 06-03-PLAN.md — ExifWritePlanner: candidatos, valores por campo, linha não suportada e oferta de sidecar
- [x] 06-04-PLAN.md — Teste empírico de escrita por formato (D-03/D-04) e decisão medida em docs/DECISOES.md
- [x] 06-05-PLAN.md — ExifWriteExecutor: dry-run autoritativo, escrita verificada por campo, falha parcial e backup
- [x] 06-06-PLAN.md — Repositório, job em background e rotas /api/exif/*
- [x] 06-07-PLAN.md — Frontend base: tipos, cliente, aba Localização e linhas tipo A
- [x] 06-08-PLAN.md — Frontend: checkbox por linha, badges de formato/sync e detalhamento por campo
- [x] 06-09-PLAN.md — Documentação de arquitetura, gate completo e verificação humana do fluxo

**UI hint**: yes — a aprovação do plano dry-run precisa de superfície na UI
(padrão já existente em `Operations.tsx`: plano → dry-run → aprovar →
executar), não é feature só de backend.

### Phase 7: Classificação de pasta por GenAI

**Goal**: O nome da pasta vira evidência de cidade/evento via Claude Sonnet
5, em sessão interativa opt-in com custo estimado confirmado antes de
rodar, entrando no motor como `Evidence` própria com origem e justificativa
distinguíveis do Advisor de cluster.
**Depends on**: Nada funcionalmente. Ordem: antes da Fase 10, para o índice
de saúde já contar a origem de evidência nova desde o primeiro dia em vez
de retrofitar uma faceta depois.
**Requirements**: GENAI-01, GENAI-02, GENAI-03

**Abordagem travada** (decidida em pesquisa + assinatura do dono):

- **Interativa por sessão, não varredura em lote.** O dono confirma o custo
  antes de cada sessão rodar — mesmo modelo operacional do Advisor
  existente. Isso fecha a pergunta aberta da pesquisa (Batch API vs.
  síncrono): **síncrono**, porque a UX é interativa e o custo precisa ser
  visível por sessão, não numa fatura única depois.

- **Sonnet 5, nunca Haiku.** Precedente D-059/D-060: modelo barato já
  alucinou num input *mais rico* que nome-de-pasta-sozinho. Entrada esparsa
  aumenta o risco, não diminui — a conclusão de D-059/D-060 vale a fortiori
  aqui, e não se reabre sem medição nova.

- **Tipo de resultado irmão e novo** em `classification/` (ex.:
  `LocationAdvisorResult`), **nunca** sobrecarregar o `AdvisorResult` do
  Advisor de cluster. Degrau próprio na cascata do `SuggestionEngine`, com
  entrada própria em `SCORES_REFERENCIA` (ex.: `llm_pasta`, distinta de
  `llm`).

- Flag de opt-in **própria**, não carona no consentimento já dado ao
  Advisor de cluster.

- Falha de API nunca derruba o pipeline (mesmo contrato never-crash do
  Advisor atual).

**Success Criteria** (what must be TRUE):

  1. Com a classificação desligada — que é o padrão — nenhuma chamada
     externa acontece e o resultado do motor é idêntico ao de hoje.

  2. Ao ligar para uma sessão, o dono vê quantas pastas entram e o custo
     estimado, e nada é enviado antes de ele confirmar.

  3. A sugestão gerada responde "por quê?" com origem própria (nome de
     pasta via LLM) e confiança própria, distinguível na Revisão de uma
     sugestão vinda do Advisor de cluster.

  4. O que sai da máquina é só nome de pasta + metadado já catalogado —
     nenhuma imagem, nenhum pixel, provado por teste do payload.

  5. Erro, timeout ou 429 da API deixa a pasta sem a evidência de LLM e a
     geração de sugestões continua local até o fim, sem exceção vazando.

**Explicitly out of scope**: envio de imagem; varredura em lote do catálogo
inteiro; reabrir a escolha de modelo sem medição no método D-059/D-060.
**Plans:** 1/10 plans executed

Plans:
- [x] 07-01-PLAN.md — Persistência: modelo `PastaClassificada`, migração 0020 e repositório com D-02 por campo
- [ ] 07-02-PLAN.md — Cliente Claude Sonnet 5: chamada única em lote, payload sem imagem, never-crash
- [ ] 07-03-PLAN.md — Pré-filtro de candidatas (D-01) e estimativa de custo (decisão: `count_tokens` × critério 2)
- [ ] 07-04-PLAN.md — Gate de dois consentimentos e endpoints `/api/genai-pasta/*`
- [ ] 07-05-PLAN.md — Degrau `llm_pasta` na cascata do `SuggestionEngine` e durabilidade entre rodadas
- [ ] 07-06-PLAN.md — Cliente tipado em `api.ts` e assistente (passos 0-3: opt-in, candidatas, custo, rodando)
- [ ] 07-07-PLAN.md — Assistente (passos 4-5: revisão antes/depois, resumo de D-06, conclusão)
- [ ] 07-08-PLAN.md — Disparo na Revisão e pastilha de origem no `PorQue`
- [ ] 07-09-PLAN.md — Medição do score `llm_pasta` contra o acervo real e decisão registrada
- [ ] 07-10-PLAN.md — Documentação, verificação humana de sessão real e gate da fase

**UI hint**: yes — escopo estreito: um ponto de confirmação de custo antes
da sessão (modal/confirmação), não uma tela nova.

### Phase 8: Picker nativo + progresso de importação

**Goal**: Adicionar uma fonte deixa de exigir digitar um caminho, e a barra
de importação responde "quanto falta e em que ritmo" sem trocar de forma.
**Depends on**: Nada funcionalmente. Precede a Fase 9 de propósito: o picker
substitui o modal que o botão da sidebar dispara, então a sidebar herda
fiação já assentada em vez de duas sessões editando a mesma região de
arquivo.
**Requirements**: PICKER-01, PICKER-02

**Abordagem travada** (decidida em pesquisa + assinatura do dono):

- **`tauri-plugin-dialog`** (dependência nova, ainda não instalada) substitui
  o `<input>` de texto livre do `ModalCaminho.tsx`. Manter o campo de texto
  como fallback no caminho não-Tauri (dev server).

- Caminho escolhido continua passando pela validação de `security/`
  (travessia, symlink) — o diálogo nativo não é passe livre.

- Barra de progresso **permanece linear**, estendendo o padrão do
  `StatusBar.tsx` existente. O que muda é granularidade: processados/total,
  taxa, ETA. **Sem gauge radial** — decisão explícita do dono, fecha a
  lacuna que a pesquisa havia deixado aberta ("o que 'gauge' significa").

**Success Criteria** (what must be TRUE):

  1. O dono escolhe a pasta de origem pelo diálogo nativo do macOS, a partir
     do botão "Adicionar pasta…" e dos três estados vazios, sem digitar
     caminho nenhum.

  2. Rodando fora do Tauri (dev server), o campo de texto continua
     funcionando com a mesma validação, sem quebrar o fluxo.

  3. Caminho recusado pela validação de segurança ou por erro de scan mostra
     o erro no próprio modal, como hoje.

  4. Durante a importação, a barra do StatusBar mostra arquivos
     processados/total, taxa e ETA, atualizando sem travar a interface — na
     mesma forma linear de hoje.

**Explicitly out of scope**: gauge radial ou qualquer troca de forma do
indicador; reescrita do job de importação.
**Plans**: TBD
**UI hint**: yes

### Phase 9: Sidebar navegável

**Goal**: Encontrar uma pasta na árvore por digitação e por teclado, sem
expandir nível a nível com o mouse.
**Depends on**: Phase 8 (herda a fiação já assentada de
`ModalCaminho`/botão "Adicionar pasta…"; mesma superfície de arquivo)
**Requirements**: SIDEBAR-01, SIDEBAR-02

**Abordagem travada** (decidida em pesquisa + assinatura do dono):

- Busca incremental de texto + navegação por teclado **sobre a
  `ArvoreDePastas.tsx` existente**. A arquitetura de informação já está
  decidida em `docs/NAVEGACAO.md` (sidebar = lugar, topo = recorte com
  chips) — esta fase preenche uma forma documentada, **não** reabre decisão
  de IA.

- Padrão de teclado é o já estabelecido em `Review.tsx` (REV-01), não um
  novo.

- **Não** construir a árvore ciente de volume (fonte→volume→pasta): tem
  gatilho documentado ("lista de fontes passar de uma tela") que ainda não
  disparou.

**Success Criteria** (what must be TRUE):

  1. Digitando na sidebar, a árvore filtra incrementalmente e revela os
     ancestrais dos resultados, sem o dono expandir nada manualmente.

  2. Limpar a busca devolve a árvore ao estado de expansão anterior, sem
     perder a pasta selecionada.

  3. Setas, Enter e Home/End navegam e selecionam nós com foco visível, no
     mesmo padrão de teclado de `Review.tsx`.

  4. Selecionar pasta pela busca ou pelo teclado aplica exatamente o mesmo
     recorte que o clique de hoje, e a busca da sidebar não vaza para a
     busca da grade (guarda de REV-03 preservada).

**Explicitly out of scope**: árvore ciente de volume; painel de filtros
paralelo à barra do topo (já morto em `docs/NAVEGACAO.md`).
**Plans**: TBD
**UI hint**: yes

### Phase 10: Confiança como eixo + índice de saúde

**Goal**: Confiança deixa de ser só um badge por item e vira eixo de
navegação de primeira classe, e o dono passa a ver a saúde do acervo como
distribuição por dimensão — nunca como um número só.
**Depends on**: Phase 7 (soft — para o índice já contar a evidência de LLM
de pasta desde o primeiro dia). Sem dependência dura de esquema.
**Requirements**: CONF-01, CONF-02

**Abordagem travada** (decidida em pesquisa + assinatura do dono):

- **Agregação pura.** `GROUP BY`/`COUNT` sobre `Evidence`/`Suggestion`
  existentes, no precedente já entregue de `panorama()`/`LACUNAS`/
  `_condicao_lacuna`. Sem esquema novo — a única exceção prevista é um
  índice faltante em `Suggestion.nivel` (sinalizado pela pesquisa), porque
  filtro de navegação roda a cada clique, não uma vez por carga de painel.

- Índice de saúde é **obrigatoriamente distribuição por dimensão**: % de
  alta confiança em localização, % em data, % em categoria, mais um bucket
  explícito "sem evidência". **Nunca** um score único combinado — média,
  média ponderada ou elo-mais-fraco agregado violam D-017/`docs/CONFIANCA.md`
  (é a mesma soma arbitrária, um nível de abstração acima) e essa classe de
  bug já vazou uma vez (D-071, item sem evidência renderizado como "Alta").

- Formato do payload com facetas nomeadas (não aridade fixa), para a Fase 11
  poder acrescentar sinal de corroboração sem quebrar contrato de endpoint.

- Isto é rollup sobre sugestão já finalizada — **não** mexe na regra do elo
  mais fraco nem cria fórmula de pontuação nova.

**Success Criteria** (what must be TRUE):

  1. O dono filtra a grade por faixa de confiança (alta/média/baixa) como
     eixo próprio, combinável com os recortes já existentes (ano, câmera,
     pasta, extensão).

  2. O Panorama mostra três distribuições paralelas — localização, data,
     categoria — cada uma com % por faixa e um bucket explícito "sem
     evidência", e em nenhum lugar um número único combinado.

  3. Clicar numa faixa de uma dimensão leva direto à grade já filtrada por
     aquela faixa — o número é navegável, não decorativo.

  4. Filtrar por confiança no acervo real responde em tempo de clique, sem
     regressão medida contra o baseline de `docs/PERFORMANCE.md`.

**Explicitly out of scope**: score único de saúde; qualquer alteração na
regra de confiança de `docs/CONFIANCA.md`; visão de tendência ao longo do
tempo (depende da Fase 11 existir).
**Plans**: TBD
**UI hint**: yes

### Phase 11: Motor de corroboração generalizado

**Goal**: O padrão de confronto de D-074 (confrontar a doadora antes **e** a
depois) deixa de valer só para GPS: herança de data/hora e de cidade/país
também passa a exigir concordância entre fontes independentes, com cada tipo
de evidência medido por conta própria antes de valer bônus algum.
**Depends on**: Phase 10 (soft — o eixo de confiança dá como observar e
medir o efeito). É a fase de **maior risco de regressão** do milestone:
toca comportamento de GPS já calibrado e medido por D-074.
**Requirements**: CORR-01, CORR-02, CORR-03

**Abordagem travada** (decidida em pesquisa + assinatura do dono):

- **Aterrissar estreito primeiro.** Comparadores por tipo de evidência
  (data/hora, cidade/país) entram **direto em `grouping/correlacao.py`**, na
  mesma forma de três saídas (concorda / discorda / passa direto) do
  `_confrontar_com_outro_lado` existente. Extrair abstração compartilhada
  (ex.: para `classification/confidence.py`) **só se e quando** um segundo
  consumidor fora de `grouping/` precisar — não especulativamente.

- Campo categórico (cidade/país) usa **correspondência exata como portão de
  corroboração** (com normalização de acento/caixa, D-066/D-067), **nunca**
  limiar de distância/similaridade fuzzy — isso reintroduziria a constante
  não medida que D-074 explicitamente evitou ("nenhum fator novo foi
  adicionado").

- **Zero bônus de confiança para qualquer tipo de evidência generalizado sem
  medição dedicada contra o acervo real primeiro** — mesma barra empírica
  que o próprio D-074 cumpriu (40.678 fotos, cobertura 91,1%, chão de 50,9%
  numa banda). A calibração de GPS **não transfere por analogia**; concordância
  de "país" acontece por acaso a taxa de fundo alta num acervo enviesado.
  Cada tipo precisa do seu passo de medição no molde de
  `scripts/calibrar_raio_incerteza.py` e da sua decisão registrada.

- Comportamento de GPS de D-074 tem que sair idêntico do outro lado.

**Success Criteria** (what must be TRUE):

  1. Herança de data/hora só é aceita quando a doadora anterior e a
     posterior concordam; com âncora única ou âncoras discordantes o sistema
     não extrapola — a foto fica sem data herdada em vez de ganhar uma
     inventada.

  2. Herança de cidade/país por contexto de pasta/álbum exige concordância
     exata entre fontes independentes (após normalização de acento/caixa),
     sem nenhum limiar de distância ou similaridade.

  3. A justificativa da sugestão mostra quais fontes concordaram, de forma
     que o dono responda "por que essa data/cidade?" sem abrir o banco.

  4. Nenhum bônus de confiança novo está ativo sem um script de medição
     contra o acervo real e uma decisão registrada em `docs/DECISOES.md`, no
     mesmo molde de D-074.

  5. O comportamento de herança de GPS de D-074 sai idêntico — cobertura
     medida antes e depois inalterada, sem regressão.

**Explicitly out of scope**: abstração compartilhada de corroboração
(deferida até haver segundo consumidor real); LEARN-01 (modo ativo de
aprendizado — v3+, desbloqueado por esta fase e pela Fase 10).
**Plans**: TBD

## Progress

**Execution Order:**
Fases executam em ordem numérica: 6 → 7 → 8 → 9 → 10 → 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|-----------------|--------|-----------|
| 1. Timezone estimado | v1.0 | 1/1 | Complete | 2026-08-16 |
| 2. Correção de dados medidos | v1.0 | 1/1 | Complete | 2026-08-16 |
| 3. Revisão acessível e consistente | v1.0 | 2/2 | Complete | 2026-08-16 |
| 4. Consistência visual secundária | v1.0 | 7/7 | Complete | 2026-08-17 |
| 5. Preparação para lançamento | v1.0 | 5/5 | Complete | 2026-08-18 |
| 6. Escrita EXIF de localização | v2.0 | 11/9 | Complete   | 2026-08-18 |
| 7. Classificação de pasta por GenAI | v2.0 | 1/10 | In Progress|  |
| 8. Picker nativo + progresso de importação | v2.0 | 0/TBD | Not started | - |
| 9. Sidebar navegável | v2.0 | 0/TBD | Not started | - |
| 10. Confiança como eixo + índice de saúde | v2.0 | 0/TBD | Not started | - |
| 11. Motor de corroboração generalizado | v2.0 | 0/TBD | Not started | - |
