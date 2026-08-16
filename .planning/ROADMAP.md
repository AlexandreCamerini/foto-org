# Roadmap: Foto Organizer

## Overview

MVP (M0–M7) já entregou o núcleo completo: catalogação segura, evidências e
sugestões auditáveis, duplicatas em 3 níveis, plano de operações com
dry-run obrigatório e cópia verificada, stubs de visão/rosto, e um webapp
único (FastAPI local + React) substituindo por completo o legado. Este
roadmap cobre o próximo incremento — 5 fases derivadas do backlog v2+ já
priorizado por dado medido do acervo real (`docs/ROADMAP.md`), dos
pré-requisitos de lançamento (`docs/PLANO_IA_E_PRODUTO.md`) e dos achados
de UX medidos/priorizados (`docs/AVALIACAO_UX.md`). A jornada vai de
"fechar a última lacuna de geolocalização e corrigir defeitos medidos de
visibilidade de dado", passando por "revisão operável só de teclado e
consistente com o design system", até "produto pronto para um primeiro
usuário real fora da máquina do desenvolvedor".

Fora deste roadmap, por dependerem de uma decisão do dono ainda não tomada
ou de dado hoje inalcançável (reconhecimento facial, visão local, sidecar
XMP, reconexão de volumes desmontados) — ver REQUIREMENTS.md § v2.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Timezone estimado** - Fotos ganham fuso horário estimado (completed 2026-08-16)
  (`tz_estimado`) a partir do país já atribuído, gravado direto sem revisão
- [x] **Phase 2: Correção de dados medidos** - Filtro "Tudo" da Biblioteca (completed 2026-08-16)
  para de esconder SINAL misturado com acervo sem `WHERE`
- [x] **Phase 3: Revisão acessível e consistente** - `texto-3` restante em (completed 2026-08-16)
  conteúdo e busca não limpa em 3 pontos de navegação
- [ ] **Phase 4: Consistência visual secundária** - Selos, estados de erro/
  vazio e tokens de peso/hover consistentes entre telas
- [ ] **Phase 5: Preparação para lançamento** - Empacotamento assinado,
  índices ausentes, onboarding do primeiro acervo, baseline de performance

## Phase Details

### Phase 1: Timezone estimado
**Goal**: Fotos ganham `tz_estimado` — fuso IANA estimado a partir do país
já atribuído à foto por qualquer origem (GPS próprio, herança temporal de
D-025, ou nome de pasta) — fechando o modelo de dois instantes de D-038:
`tz_estimado IS NOT NULL` passa a ser o sinal de "fuso conhecido" do
catálogo.
**Depends on**: Nothing (mapa/raio de incerteza já validado; país já é
atribuído pelo motor de classificação — ver PROJECT.md)
**Requirements**: TZ-01
**Canonical spec**: `docs/prompts/fase-11-timezone-estimado.md` (spec
detalhado desta fase, mais autoritativo que a formulação abaixo — decisão
do dono em 2026-08-16: seguir este doc, não o texto minerado do
ROADMAP.md/AVALIACAO_UX.md original). Ver também D-038 em
`docs/DECISOES.md` (modelo de dois instantes).
**Success Criteria** (what must be TRUE):
  1. Tabela estática `TZ_POR_PAIS` (nova, `fotoorganizer/geolocation/
     timezones.py`) cobre os 98 países de `PAISES_PT`; todo valor é um
     identificador IANA válido, validado em teste contra
     `zoneinfo.available_timezones()`.
  2. Uma foto cujo país foi resolvido — por GPS próprio, herança temporal
     (D-025) ou nome de pasta — ganha `tz_estimado` gravado direto em
     `MediaFile` dentro de `_persistir_sugestao` após `gerar()`, **sem**
     passar por `Evidence`/`Suggestion`/revisão humana e **sem** entrada em
     `docs/CONFIANCA.md` — mesmo padrão não revisado de `gps_lat_estimado`.
  3. `GET /api/midia/{id}` devolve o campo `tz_estimado`.
  4. Sem país conhecido (ou país fora da tabela), `tz_estimado` fica
     `None` — nunca inventa, nunca lança erro.
  5. País com mais de um fuso oficial (Brasil, EUA, Rússia...) resolve para
     o fuso da capital ou de maior população — aproximação deliberada,
     documentada em comentário na própria tabela.
  6. Escrever `tz_estimado` não reescreve `data_capturada`/
     `data_capturada_utc` — conversão para hora local exibida em UI é
     decisão separada, fora desta fase.
**Explicitly out of scope**: geometria coordenada→fuso (`timezonefinder`);
leitura de `OffsetTimeOriginal`/`Z` do QuickTime nos extratores (item
adiado, não esta fase); correção de `sources/google_takeout.py` (fuso da
máquina do importador); qualquer mudança em `Evidence`/`docs/CONFIANCA.md`.
**Plans:** 1/1 plans complete

Plans:
- [x] 01-01-PLAN.md — tabela TZ_POR_PAIS, persistência direta em MediaFile, serialização em GET /api/midia/{id}

### Phase 2: Correção de dados medidos
**Goal**: O filtro "Tudo" da Biblioteca distingue `SINAL` de `ACERVO` em
vez de misturar os dois numa tabela sem `WHERE`.
**Depends on**: Nothing
**Requirements**: BUG-03
**Scope note (2026-08-16):** dos 4 defeitos medidos originalmente em
`docs/AVALIACAO_UX.md` §C (2026-08-06), BUG-01 (`5c7b36d`), BUG-02
(`VIDEO_EXTENSIONS`) e BUG-04 (`engine.py:713-725`) já estavam corrigidos
no código antes desta sessão — confirmado por leitura direta + testes
existentes, movidos para PROJECT.md § Validated. Só BUG-03 segue aberto;
o escopo desta fase foi reduzido de acordo.
**Success Criteria** (what must be TRUE):
  1. O filtro "Tudo" da Biblioteca distingue `SINAL` de `ACERVO` em vez de
     devolver a tabela inteira sem `WHERE`.
**Plans:** 1/1 plans complete

Plans:
- [x] 02-01-PLAN.md — branch `tudo` de `_query` filtra por `papel == ACERVO`,
  rótulo/tooltip corrigidos, auditoria das contagens vizinhas (D-03)

### Phase 3: Revisão acessível e consistente
**Goal**: A busca de texto não vaza entre grupos/abas, e `texto-3`
restante em conteúdo real (não decorativo/desabilitado) vira `texto-2`.
**Depends on**: Phase 2 (corrige o dado que a Revisão exibe antes de
polir a interação sobre ele)
**Requirements**: REV-02, REV-03
**Scope note (2026-08-16):** dos 7 achados desta rodada
(`docs/AVALIACAO_UX.md` A.1-A.2/B.1-B.5, medido 2026-08-06), REV-01
(commit pré-sessão), REV-04, REV-05, REV-06 (commit `ae60319`) e REV-07
(commit `a7d6e5e`) já estavam corrigidos no código antes desta sessão —
confirmado por leitura direta + `git log`, movidos para PROJECT.md §
Validated. Só REV-02 (parcial) e REV-03 (parcial) seguem abertos; o
escopo desta fase foi reduzido de acordo. **UI-SPEC.md desta fase já
reflete o escopo restrito** (aprovado antes desta correção de escopo,
mas já tratava REV-01/04/05 como feitos).
**Success Criteria** (what must be TRUE):
  1. Trocar de grupo ou aba nunca mostra um "0 no filtro" falso por causa
     de busca antiga sobrevivendo à navegação — nos 3 pontos de entrada
     ainda não cobertos (botão de troca de aba, `Sidebar.onSelecionarPasta`,
     `StatusBar.aoIrPara`).
  2. `texto-3` usado como texto de conteúdo real (não decorativo, não
     desabilitado, não estado de carregamento) em Review/Inspector/
     Operations vira `texto-2`.
**Plans:** 2/2 plans complete
**UI hint**: yes

Plans:
- [x] 03-01-PLAN.md — REV-03: `setBusca("")` no botão de aba, em
  `Sidebar.onSelecionarPasta` e em `StatusBar.aoIrPara`, + 4 testes de
  regressão (inclui a guarda de que reclicar a aba ativa não apaga a busca)
- [x] 03-02-PLAN.md — REV-02: 9 promoções `texto-3` → `texto-2` em
  Review/Inspector/Operations pela lista fechada de D-02, com checkpoint
  visual de contraste

### Phase 4: Consistência visual secundária
**Goal**: As inconsistências visuais/interação restantes deixam de
diferenciar "em que tela eu estou" de "o que o design system manda".
**Depends on**: Phase 3
**Requirements**: CONS-01, CONS-02, CONS-03, CONS-04, CONS-05, CONS-06, CONS-07, CONS-08
**Success Criteria** (what must be TRUE):
  1. Sugestões adjacentes que colidem em nome+data+câmera mostram selo de
     fonte, distinguindo "mesma foto em dois catálogos" de "arquivo
     diferente".
  2. Grupos de Eventos com nome igual mostram selo "álbum" vs. "evento
     detectado".
  3. Imagem quebrada (404) no Loupe ou na comparação de Duplicatas mostra
     estado de erro explícito, nunca texto cru ou retângulo preto.
  4. Estados vazios (Panorama, PhotoGrid, Trips) oferecem um botão de ação
     direta em vez de repetir frase estática.
**Plans**: TBD
**UI hint**: yes

### Phase 5: Preparação para lançamento
**Goal**: O app pode ser entregue a um primeiro usuário real fora da
máquina do desenvolvedor — assinado, com fluxo de entrada e com
desempenho medido, não só funcionando para quem já sabe onde tudo está.
**Depends on**: Nothing (pode rodar em paralelo às fases 1-4)
**Requirements**: LANC-01, LANC-02, LANC-03, LANC-04
**Success Criteria** (what must be TRUE):
  1. App instala como `.app` assinado e notarizado via Tauri v2 com Python
     embarcado (python-build-standalone), passando pelo Gatekeeper sem
     aviso.
  2. Consultas por prefixo de pasta (e demais FKs hoje sem índice) usam
     índice, não table scan.
  3. Um usuário de primeira vez consegue adicionar sua primeira fonte/pasta
     e chegar a uma grade populada sem ler documentação.
  4. Existe um baseline de performance documentado (taxa de indexação,
     tempo de geração de sugestões, tempo de detecção de duplicatas) contra
     um catálogo de tamanho representativo.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 (Phase 5 pode rodar em
paralelo, sem dependência estrutural das demais)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Timezone estimado | 1/1 | Complete   | 2026-08-16 |
| 2. Correção de dados medidos | 1/1 | Complete   | 2026-08-16 |
| 3. Revisão acessível e consistente | 2/2 | Complete   | 2026-08-16 |
| 4. Consistência visual secundária | 0/TBD | Not started | - |
| 5. Preparação para lançamento | 0/TBD | Not started | - |
