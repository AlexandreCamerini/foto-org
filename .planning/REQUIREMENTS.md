# Requirements: Foto Organizer

**Defined:** 2026-08-16
**Core Value:** Toda sugestão de onde uma foto pertence é auditável até a
evidência que a gerou; nenhuma operação física acontece sem revisão humana
e dry-run.

**Provenance note:** nenhum documento deste ingest foi classificado `PRD`
(ver `.planning/intel/requirements.md`). Os requisitos abaixo foram
minerados diretamente de conteúdo com formato de requisito em três fontes
`DOC` (precedência mais baixa que ADR/SPEC, mas são as únicas fontes com
esse formato neste corpus):

- `docs/ROADMAP.md` — seção "Próximas versões (v2+)", itens ordenados por
  valor medido por unidade de custo para este acervo (recalibrado
  2026-08-01, D-024..D-030).
- `docs/PLANO_IA_E_PRODUTO.md` §6 — tabela de pré-requisitos de lançamento.
- `docs/AVALIACAO_UX.md` — rodada de 2026-08-06 (seções A/B/C/D), achados
  medidos e propostas priorizadas por valor/esforço.

Cada requisito carrega a fonte entre colchetes. Itens do backlog do
ROADMAP.md já confirmados como implementados por `docs/DECISOES.md` (mapa
com raio de incerteza, `docs/EVENTOS.md`, eventos nomeados, templates
configuráveis) **não** aparecem aqui — estão em PROJECT.md § Validated.

## v1 Requirements

Requisitos para este roadmap (próximo incremento pós-MVP). Cada um mapeia
para exatamente uma fase.

### Geolocalização (TZ)

- [x] **TZ-01**: Sistema infere `tz_estimado` a partir do país já atribuído
  à foto (GPS próprio, herança temporal — janela de 12h de D-025 — ou nome
  de pasta), em vez de depender de GPS+hora local (que só alcançaria 4 dos
  25 anos do acervo). Gravado direto em `MediaFile`, sem `Evidence`/revisão
  — mesmo padrão de `gps_lat_estimado` [docs/ROADMAP.md, item v2 #5;
  spec detalhado e autoritativo em
  `docs/prompts/fase-11-timezone-estimado.md`, decisão do dono 2026-08-16]

### Correção de dados medidos (BUG)

<!-- BUG-01, BUG-02 e BUG-04 foram minerados de docs/AVALIACAO_UX.md
(medido em 2026-08-06) durante o ingest, mas já tinham sido corrigidos no
código antes desta sessão — confirmado por leitura direta + testes
existentes em 2026-08-16. Ver PROJECT.md § Validated. Só BUG-03 segue
aberto. -->

- [x] **BUG-01**: ~~Registros `papel='SINAL'` dentro de `originals/`
  (Apple Fotos) ou `Masters/` (Aperture) sem cópia `ACERVO` equivalente
  ficam invisíveis~~ — já corrigido, commit `5c7b36d` (2026-08-06):
  `dentro_de_pacote()` diferencia `originals/`/`Masters/` do derivado.
  Teste: `tests/test_discovery.py:211-212`
  [docs/AVALIACAO_UX.md, §C.2 — achado já resolvido]
- [x] **BUG-02**: ~~Scanner de arquivo não descobre vídeo~~ — já
  corrigido: `VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi"}` existe
  em `fotoorganizer/metadata/purepython.py:51`, incluído na descoberta
  [docs/AVALIACAO_UX.md, §C.3 — achado já resolvido]
- [x] **BUG-03**: ~~Filtro "Tudo" (`alcance=tudo`) da Biblioteca não
  filtrava de fato~~ — corrigido na Fase 2 (2026-08-16):
  `_ACERVO_OU_REFERENCIA` em `fotoorganizer/repositories/media.py`
  exclui testemunha com arquivo local, preservando referência externa
  sem arquivo (feature do commit `1b125f7`). Testes:
  `tests/test_repository.py` (3 novos), tripwire
  `tests/test_sources_importer.py:428-430` intocado. Verificação humana
  visual pendente (catálogo zerado) — ver `02-HUMAN-UAT.md`
  [docs/AVALIACAO_UX.md, §C.2, medido]
- [x] **BUG-04**: ~~Quando o advisor LLM responde `categoria="Viagens"`,
  a sessão não cria/junta a uma Viagem~~ — já corrigido:
  `engine.py:713-725` já cria/junta `Trip` com a mesma justificativa do
  caminho `evento`, comentário no código cita a própria seção C.4.
  Testes: `test_advisor_llm_promove_sessao_neutra_a_viagem`,
  `test_advisor_llm_viagem_sem_nome_usa_pais_dominante`
  [docs/AVALIACAO_UX.md, §C.4 — achado já resolvido]

### Revisão acessível e consistente (REV)

- [ ] **REV-01**: Cabeçalho de grupo em Revisão navegável por teclado
  (`role="button"`, `tabIndex={0}`, `onKeyDown` para Enter/Espaço) — hoje
  só abre com mouse [docs/AVALIACAO_UX.md, A.1]
- [ ] **REV-02**: `texto-3` (contraste ≈3,46:1) deixa de ser usado como
  texto de conteúdo em Review/Inspector/Operations — troca para `texto-2`
  (≈6,1:1), reservando `texto-3` para o de fato desabilitado
  [docs/AVALIACAO_UX.md, B.1]
- [ ] **REV-03**: Busca de texto é limpa (ou os filtros ativos aparecem
  como chips removíveis) ao trocar de grupo/aba — hoje sobrevive à troca e
  mostra "0 no filtro" com a mensagem genérica de biblioteca vazia
  [docs/AVALIACAO_UX.md, A.2]
- [ ] **REV-04**: Modais usam `rounded-md` (6px) — hoje alguns usam
  `rounded-lg`, contra a regra explícita de `docs/DIRECAO_DE_ARTE.md`
  [docs/AVALIACAO_UX.md, B.2]
- [ ] **REV-05**: Data no Inspetor é formatada em pt-BR com
  `formatarData()` — hoje é ISO cru, divergindo de Loupe e Revisão
  [docs/AVALIACAO_UX.md, A.5]
- [ ] **REV-06**: Par Aprovar/Rejeitar tem peso visual único (neutro-até-
  hover) em cabeçalho e linha — hoje o cabeçalho é neutro e a linha
  individual é colorida em repouso [docs/AVALIACAO_UX.md, B.4]
- [ ] **REV-07**: `text-acento` deixa de ser cor permanente de coluna/lista
  inteira (Operations, TemplateEditor) — troca para `font-medium` neutro,
  já que acento é reservado a estado [docs/AVALIACAO_UX.md, B.5]

### Consistência visual secundária (CONS)

- [ ] **CONS-01**: Selo de fonte aparece quando duas sugestões adjacentes
  colidem em nome+data+câmera (`media_id` diferente), para distinguir
  "mesma foto em dois catálogos" de "arquivo diferente"
  [docs/AVALIACAO_UX.md, A.6]
- [ ] **CONS-02**: Selo "álbum" vs. "evento detectado" aparece quando dois
  cards de Eventos colidem no nome [docs/AVALIACAO_UX.md, A.7/B.6]
- [ ] **CONS-03**: Escala única de "botão importante" definida (preenchido
  = ação mais comprometedora); "Retomar"/"Gerar sugestões" migram para
  contorno neutro+hover [docs/AVALIACAO_UX.md, B.3]
- [ ] **CONS-04**: Imagem em alta resolução que retorna 404 (Loupe,
  comparação de Duplicatas) mostra estado de erro explícito, não texto cru
  ou retângulo preto [docs/AVALIACAO_UX.md, A.4]
- [ ] **CONS-05**: Estados vazios (Panorama, PhotoGrid, Trips) ganham botão
  de ação ("Adicionar pasta") em vez de repetir frase estática
  [docs/AVALIACAO_UX.md, B.6]
- [ ] **CONS-06**: Abaixo de ~1000px, com grupo aberto, o Inspetor colapsa
  automaticamente ou a barra empilha em duas linhas — hoje dropdown/busca/
  Inspetor se sobrepõem em ~900px [docs/AVALIACAO_UX.md, A.3]
- [ ] **CONS-07**: Hover de "cancelar" é consistente entre telas (decidir
  se cancelar job é irreversível o bastante para justificar `hover:text-erro`
  ou se deve ser `hover:bg-cartao` neutro em todo lugar)
  [docs/AVALIACAO_UX.md, B.7]
- [ ] **CONS-08**: Peso de texto de ênfase é tokenizado
  (`--font-weight-titulo` no `@theme`) em vez de `font-semibold`/
  `font-medium` convivendo sem regra [docs/AVALIACAO_UX.md, B.8]

### Preparação para lançamento (LANC)

- [ ] **LANC-01**: App empacotado como `.app` assinado e notarizado via
  Tauri v2 com Python embarcado via python-build-standalone (não
  PyInstaller — fragilidade de codesign/notarização de libs nativas em
  layout sidecar) [docs/PLANO_IA_E_PRODUTO.md §6 pré-requisito 1;
  docs/EMPACOTAMENTO.md, DOC-precedence — ver INGEST-CONFLICTS.md]
- [ ] **LANC-02**: Índices de FK ausentes adicionados, incluindo índice em
  `MediaFile.pasta` (hoje `LIKE 'prefixo%'` sem índice força table scan a
  cada clique na árvore de pastas) [docs/PLANO_IA_E_PRODUTO.md §6
  pré-requisito 3; corroborado por .planning/codebase/CONCERNS.md]
- [ ] **LANC-03**: Fluxo de onboarding do primeiro acervo existe (hoje não
  existe) [docs/PLANO_IA_E_PRODUTO.md §6 pré-requisito 4]
- [ ] **LANC-04**: Série de métricas de desempenho medida e registrada
  como baseline formal (indexação, geração de sugestões, detecção de
  duplicatas) contra um catálogo representativo [docs/PLANO_IA_E_PRODUTO.md
  §6 pré-requisito 7]

## v2 Requirements

Reconhecidos, não descartados, mas fora deste roadmap — dependem de dado
que o acervo real ainda não tem alcançável, ou de uma decisão do dono
ainda não tomada.

### Alcance de arquivo (bloqueante de 4 itens abaixo)

- **ARCH-01**: Reconectar os volumes desmontados/só-iCloud (45.397
  registros do Lightroom, 44.661 do Apple Fotos) por identidade (hash,
  caminho original, tamanho+data) — candidato de maior alavancagem medida
  do backlog inteiro, **ainda sem decisão do dono**. Forma proposta em
  `docs/prompts/fase-12-alcance-e-tempo.md` (2026-08-08). Trazer ao dono
  antes de promover a v1. [docs/ROADMAP.md, "O item que a lista ainda não
  tem"]

### Reconhecimento e visão (bloqueados por ARCH-01)

- **FACE-01**: Detecção facial local real (`FaceRecognitionProvider` com
  modelo ONNX) — desceu de 1º para 6º no backlog porque ~90% dos ~99 mil
  registros conhecidos não têm pixel local alcançável hoje
  [docs/ROADMAP.md, v2 #6]
- **FACE-02**: UI de pessoas (cadastro/gestão de perfis, revisão de
  rostos) — bloqueada por FACE-01 [docs/ROADMAP.md, v2 #8]
- **VIS-01**: Análise visual local (`VisionProvider`: cena, qualidade,
  screenshot vs. foto) — demovida em 2026-08-02 (D-035); a premissa que a
  sustentava (miniaturas cobrindo 2001-2018) não existe mais no catálogo
  [docs/ROADMAP.md, v2 #7]

### Metadados e distribuição

- **META-01**: Sidecar XMP (gravar metadados aprovados em `.xmp` ao lado
  do original) — bloqueado por não haver onde escrever para ~90 mil
  registros hoje inacessíveis, e pelo invariante 7 do CLAUDE.md (MVP não
  implementa escrita de EXIF; futuro é sidecar apenas)
  [docs/ROADMAP.md, v2 #9]
- **SYNC-01**: `SyncProvider` / sincronização opcional (Railway/Postgres) —
  prometido como adaptador plugável pela arquitetura, não construído, sem
  urgência medida [docs/PLANO_IA_E_PRODUTO.md §6 "posterior"]
- **DAM-01**: Lacunas de esquema DAM (derivados/linhagem, tags
  hierárquicas, direitos autorais, coleções curadas) — classificadas como
  não-bloqueio de MVP (D-008); revisitar só com caso de uso real
  [.planning/intel/decisions.md D-008]

## Out of Scope

Explicitamente excluído. Documentado para não reabrir sem evidência nova.

| Feature | Reason |
|---------|--------|
| Análise de visão/reconhecimento via provedor externo (nuvem) | Recomendação explícita de "fechar a porta" em `docs/PLANO_IA_E_PRODUTO.md` §8 decisão 2; conflita com invariante 4 (nada sai da máquina por padrão) sem ganho que justifique o risco |
| Exclusão de fotos / escrita direta de EXIF | Invariante 7 do CLAUDE.md — MVP não implementa; futuro é sidecar XMP apenas (ver META-01 em v2) |
| UI em PySide6 (ou qualquer stack fora do webapp) | Já decidido e revertido — webapp é a única UI (commit `2e0ef1a`); não reabrir sem evidência nova |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TZ-01 | Phase 1 | Complete |
| BUG-01 | — | Already validated (commit `5c7b36d`, pre-session) |
| BUG-02 | — | Already validated (pre-session) |
| BUG-03 | Phase 2 | Complete (human verification pending) |
| BUG-04 | — | Already validated (pre-session) |
| REV-01 | Phase 3 | Pending |
| REV-02 | Phase 3 | Pending |
| REV-03 | Phase 3 | Pending |
| REV-04 | Phase 3 | Pending |
| REV-05 | Phase 3 | Pending |
| REV-06 | Phase 3 | Pending |
| REV-07 | Phase 3 | Pending |
| CONS-01 | Phase 4 | Pending |
| CONS-02 | Phase 4 | Pending |
| CONS-03 | Phase 4 | Pending |
| CONS-04 | Phase 4 | Pending |
| CONS-05 | Phase 4 | Pending |
| CONS-06 | Phase 4 | Pending |
| CONS-07 | Phase 4 | Pending |
| CONS-08 | Phase 4 | Pending |
| LANC-01 | Phase 5 | Pending |
| LANC-02 | Phase 5 | Pending |
| LANC-03 | Phase 5 | Pending |
| LANC-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-16*
*Last updated: 2026-08-16 after initial project setup (new-project-from-ingest)*
