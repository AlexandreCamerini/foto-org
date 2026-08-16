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

- [ ] **Phase 1: Timezone estimado** - Fotos ganham fuso horário estimado
  (`tz_estimado`) a partir do país já atribuído, gravado direto sem revisão
- [ ] **Phase 2: Correção de dados medidos** - SINAL órfão, vídeo, filtro
  "Tudo" e assimetria Evento×Viagem do advisor param de esconder dado real
- [ ] **Phase 3: Revisão acessível e consistente** - Tela de Revisão operável
  só de teclado e alinhada ao design system
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
**Plans**: TBD

### Phase 2: Correção de dados medidos
**Goal**: Nenhuma foto real e única, nem vídeo válido, fica invisível por
efeito colateral de um filtro ou classificação — e a resposta do advisor
para "Viagens" pesa tanto quanto a resposta para "Evento".
**Depends on**: Nothing
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04
**Success Criteria** (what must be TRUE):
  1. Os registros `SINAL` sem cópia `ACERVO` equivalente dentro de
     `originals/`/`Masters/` deixam de ser tratados como derivado/miniatura
     — usuário consegue alcançá-los em Revisão/Viagens/Operações.
  2. Um arquivo `.mov`/`.mp4`/`.mpg` colocado numa pasta escaneada aparece
     no catálogo (ou gera erro registrado) — nunca desaparece em silêncio.
  3. O filtro "Tudo" da Biblioteca distingue `SINAL` de `ACERVO` em vez de
     devolver a tabela inteira sem `WHERE`.
  4. Quando o advisor LLM responde `categoria="Viagens"` para uma sessão
     neutra, uma Viagem é criada/associada com a mesma confiança e
     justificativa que o caminho `evento` já tem hoje.
**Plans**: TBD

### Phase 3: Revisão acessível e consistente
**Goal**: A tela onde as decisões em lote acontecem pode ser operada do
início ao fim sem mouse, e não contradiz visualmente o próprio design
system que o resto do app segue.
**Depends on**: Phase 2 (corrige o dado que a Revisão exibe antes de
polir a interação sobre ele)
**Requirements**: REV-01, REV-02, REV-03, REV-04, REV-05, REV-06, REV-07
**Success Criteria** (what must be TRUE):
  1. Usuário abre um grupo em Revisão e aprova/rejeita cada foto dele só
     com teclado (Enter/Espaço no cabeçalho, atalhos já existentes na
     linha).
  2. Trocar de grupo ou aba nunca mostra um "0 no filtro" falso por causa
     de busca antiga sobrevivendo à navegação.
  3. Modais, contraste de texto de conteúdo e peso visual de
     Aprovar/Rejeitar seguem `docs/DIRECAO_DE_ARTE.md` de forma uniforme
     em Review/Inspector/Operations.
  4. Data no Inspetor aparece no mesmo formato pt-BR usado em Loupe e
     Revisão.
**Plans**: TBD
**UI hint**: yes

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
| 1. Timezone estimado | 0/TBD | Not started | - |
| 2. Correção de dados medidos | 0/TBD | Not started | - |
| 3. Revisão acessível e consistente | 0/TBD | Not started | - |
| 4. Consistência visual secundária | 0/TBD | Not started | - |
| 5. Preparação para lançamento | 0/TBD | Not started | - |
