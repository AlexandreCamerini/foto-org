# Foto Organizer

## What This Is

App desktop macOS, local-first, para catalogar, analisar e organizar (de
forma assistida e não destrutiva) uma grande coleção pessoal de fotos. O
núcleo (scan, catalogação, classificação, deduplicação) funciona
integralmente offline; recursos de nuvem (advisor LLM opt-in) são opcionais
e nunca pré-requisito. Único usuário: o dono do produto, na própria máquina.

MVP (M0–M7 de `docs/ROADMAP.md`) está **completo**. Este documento e o
roadmap associado cobrem o próximo incremento: v2+, priorizado por
valor-por-custo medido contra o acervo real (D-024..D-030), não por valor
abstrato de funcionalidade.

## Core Value

Toda sugestão de onde uma foto pertence é auditável até a evidência que a
gerou — origem, confiança, justificativa — e nenhuma operação física
acontece sem revisão humana e dry-run. Se isso quebrar, o produto perdeu a
única coisa que o diferencia de um DAM comercial comum.

## Requirements

### Validated

<!-- Shipped and confirmed valuable (MVP + v2 slices already implemented). -->

- ✓ Catalogação incremental somente-leitura, com checkpoint/pause-resume,
  fontes com detecção de volume indisponível — M1
- ✓ Grade de miniaturas virtualizada, inspetor, filtros e busca — M2
- ✓ Motor de evidências estruturadas + modelo de confiança (elo mais fraco,
  sem soma arbitrária) + agrupamento temporal/geográfico + sugestões — M3
- ✓ Detecção de duplicatas em 3 níveis (hash exato, conteúdo, phash), sem
  ação automática — M4
- ✓ Plano de operações com dry-run obrigatório, executor de cópia
  verificada (hash antes/depois, sem sobrescrita, retomada segura) — M5
- ✓ `VisionProvider`/`FaceRecognitionProvider` como `Protocol` com stub,
  desligados por padrão — M6
- ✓ Remoção completa do legado (`backend/`+`streamlit_app/` v1) e da UI
  PySide6 — webapp React/Vite/TS/Tailwind é a única interface (M7, commit
  `2e0ef1a`)
- ✓ exiftool como extrator padrão quando instalado, com fallback
  puro-Python automático — D-026/D-027
- ✓ Mapa do lugar estimado com raio de incerteza (`raio(Δt) = min(50km,
  max(15m, 6m/s×Δt))`), sem tile externo, com badge de descoberta no card
  de Viagens/Eventos — D-031/D-032/D-033/D-050/D-065
- ✓ Eventos nomeados a partir de álbum/pasta já existente, com regra de
  desempate em 3 camadas — D-030/D-034, `docs/AGRUPAMENTO.md` §2c
- ✓ Templates de destino editáveis na UI (aba Operações, preview ao vivo) —
  implementado 2026-08-02
- ✓ Inventário por pasta (`inventario.json` + `INVENTARIO.md`, escrita
  aditiva, pós-cópia-verificada) — D-061/D-063/D-064
- ✓ Advisor LLM opt-in (metadado apenas, nunca imagem), consultado só para
  sessões "neutra", modelo final Sonnet 5 medido nos 104 clusters reais —
  D-059/D-060
- ✓ Fase A/B' do diagnóstico geo-first: palavra-chave XMP/IPTC como
  evidência de categoria + geo-resolução antecipada — D-057/D-058
- ✓ Correções de acento NFD em nome de pasta e mês por extenso —
  D-066/D-067/D-073
- ✓ "Organizável" passa a exigir a fonte respondendo (funil afunila por
  construção) — D-068
- ✓ Correções pré-commit de correlação entre fontes e detecção de "não
  visto no walk" — D-036/D-037
- ✓ 3 fatias da auditoria pós-gate-fase5: aviso antes de excluir RAW/JPEG
  em duplicata VARIANTE, badge "Sem categoria" (era "Alta" em Não
  classificadas), performance da aba Viagens de 50-120s+ para ~0,1s —
  D-070/D-071/D-072
- ✓ `--data-dir` para suporte remoto — commit `7249318`
- ✓ `tz_estimado` (fuso IANA estimado a partir do país já atribuído —
  GPS próprio, herança temporal D-025, ou pasta), gravado direto em
  `MediaFile` sem `Evidence`/revisão, recalculado incondicionalmente a
  cada `gerar()` mesmo para mídia com sugestão já decidida — Validado na
  Fase 1, 2026-08-16 (spec: `docs/prompts/fase-11-timezone-estimado.md`)
- ✓ Original dentro de pacote (`originals/`/`Masters/`) deixa de ser
  rebaixado a testemunha — `dentro_de_pacote()` diferencia do derivado —
  commit `5c7b36d`, 2026-08-06 (BUG-01, achado de `docs/AVALIACAO_UX.md`
  §C.2; confirmado ainda válido em 2026-08-16 antes de planejar a Fase 2)
- ✓ Scanner de arquivo descobre e cataloga vídeo (`.mov`/`.mp4`/`.m4v`/
  `.avi`) — `VIDEO_EXTENSIONS` em `metadata/purepython.py` (BUG-02,
  achado de `docs/AVALIACAO_UX.md` §C.3; confirmado ainda válido em
  2026-08-16)
- ✓ Advisor LLM respondendo "Viagens" cria/junta a sessão a uma Viagem
  real, mesma justificativa/confiança do caminho Evento —
  `engine.py:713-725` (BUG-04, achado de `docs/AVALIACAO_UX.md` §C.4;
  confirmado ainda válido em 2026-08-16)
- ✓ Filtro "Tudo" da Biblioteca distingue acervo de testemunha —
  `_ACERVO_OU_REFERENCIA` em `repositories/media.py` exclui testemunha
  com arquivo local, preserva referência externa sem arquivo (feature do
  commit `1b125f7`) — Validado na Fase 2, 2026-08-16 (BUG-03); decisão
  corrigida duas vezes durante planejamento/execução, ver
  `02-01-SUMMARY.md`. Verificação visual humana pendente (catálogo
  zerado) — `02-HUMAN-UAT.md`.
- ✓ Cabeçalho de grupo em Revisão navegável por teclado
  (`role`/`tabIndex`/`onKeyDown`) — `Review.tsx` (REV-01, achado de
  `docs/AVALIACAO_UX.md` A.1; confirmado ainda válido em 2026-08-16)
- ✓ Modais usam `rounded-md`, nunca `rounded-lg` — zero ocorrências no
  webapp (REV-04, achado de `docs/AVALIACAO_UX.md` B.2; confirmado ainda
  válido em 2026-08-16)
- ✓ Data no Inspetor formatada em pt-BR com `formatarData()`, igual
  Loupe/Revisão — `Inspector.tsx` (REV-05, achado de
  `docs/AVALIACAO_UX.md` A.5; confirmado ainda válido em 2026-08-16)
- ✓ Par Aprovar/Rejeitar com peso visual único (neutro-até-hover) em
  cabeçalho e linha — commit `ae60319`, 2026-08-06 (REV-06, achado de
  `docs/AVALIACAO_UX.md` B.4; confirmado ainda válido em 2026-08-16)
- ✓ `text-acento` deixou de ser cor permanente de coluna (Operations
  usa `CORES_STATUS` por estado, TemplateEditor usa `font-medium`) —
  commit `a7d6e5e` (REV-07, achado de `docs/AVALIACAO_UX.md` B.5;
  confirmado ainda válido em 2026-08-16)
- ✓ Busca de texto não vaza entre grupos/abas nos 3 pontos de navegação
  restantes (botão de troca de aba com guarda `nome !== aba`,
  `Sidebar.onSelecionarPasta`, `StatusBar.aoIrPara`) — REV-03,
  `App.tsx`, 4 testes de regressão — Validado na Fase 3, 2026-08-16
- ✓ `texto-3` de conteúdo real (não decorativo/desabilitado) vira
  `texto-2` em Review/Inspector/Operations — 9 promoções pela lista
  fechada de D-02, 10 usos legítimos preservados, aprovação visual do
  dono contra dado real — REV-02, Validado na Fase 3, 2026-08-16
- ✓ Consistência visual secundária: selo de fonte em sugestões colididas
  (CONS-01), selo álbum×evento (CONS-02), escala única de botão
  importante + hover de cancelar consistente (CONS-03/07), estado de
  erro explícito para imagem 404 no Loupe/Duplicatas (CONS-04), 3
  estados vazios com botão de ação via modal compartilhado (CONS-05),
  barra da Biblioteca responsiva sem sobrepor o Inspetor abaixo de
  1024px (CONS-06), token `--font-weight-titulo` único para peso de
  ênfase (CONS-08) — Validado na Fase 4, 2026-08-17
- ✓ Preparação para lançamento: índices de FK ausentes incl. `pasta`
  (LANC-02, `_sob_a_pasta` usa `SEARCH` via índice + `PRAGMA
  case_sensitive_like=ON`, não mais table scan); empacotamento Marco 1
  via Tauri v2 + python-build-standalone, assinatura ad-hoc automática
  confirmada por `codesign -dv` (LANC-01 — só Marco 1, Marco 2
  assinado/notarizado segue fora de escopo por D-01, custo recorrente do
  Apple Developer Program não aprovado); baseline de performance
  documentado em `docs/PERFORMANCE.md` (59 arq/s varredura, 1,33s
  geração de sugestões, 4,54s detecção de duplicatas — LANC-04); fluxo
  de onboarding do primeiro acervo (LANC-03) — defeito real de UAT
  (backdrop translúcido do `ModalCaminho` deixava texto sobrepor)
  diagnosticado por screenshot e corrigido (`bg-black/95`); reteste
  comportamental com segunda pessoa sem instrução pós-fix confirmou
  sucesso (chegou à grade populada) — Validado na Fase 5, 2026-08-18

### Active

<!-- Current scope for this roadmap. Ver REQUIREMENTS.md para o checklist
completo e ROADMAP.md para o mapeamento de fases. -->

## Current Milestone: v2.0 Localização real e evidência expandida

**Goal:** Expandir a cobertura de evidência de localização (EXIF real,
GenAI de pasta) e a UI que expõe isso ao dono (navegação, confiança como
eixo, corroboração generalizada).

**Target features (ordem de prioridade do dono):**
1. Escrita EXIF de localização (lat/long, cidade, país) em campo vazio —
   D-075
2. GenAI de pasta → cidade/evento, no modelo do Advisor (opt-in, só
   metadado, custo visível por sessão)
3. Sidebar navegável
4. Picker de pasta + gauge de importação
5. Confiança como eixo de navegação + índice de saúde do acervo
6. Motor de corroboração generalizado (extensão do padrão D-074 para além
   de GPS)
7. Modo ativo de aprendizado — deferido até 5 e 6 existirem, por desenho
   (depende do eixo de confiança e do motor de corroboração)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Análise de visão/reconhecimento via provedor externo (nuvem) — recomendação
  explícita de "fechar a porta" em `docs/PLANO_IA_E_PRODUTO.md` §8 decisão 2;
  conflita com o invariante 4 (nada sai da máquina por padrão) sem ganho que
  justifique o risco. Visão e rostos, quando entrarem, entram locais.
- Exclusão de fotos — invariante 7 do CLAUDE.md, nunca implementada.
- Escrita EXIF fora de localização (data, câmera, autor etc.) e
  sobrescrita de campo EXIF já preenchido — invariante 7 revisado por
  D-075; escrita de lat/long, cidade e país em campo vazio passou a ser
  escopo v2.0 (ver Active).
- Reescrita de UI em PySide6 ou qualquer stack que não seja o webapp — já
  decidido e revertido (webapp é a única UI, commit `2e0ef1a`); não reabrir
  sem evidência nova.
- 4 lacunas de esquema DAM (derivados/linhagem, tags hierárquicas, direitos,
  coleções autorais) — classificadas explicitamente como não-bloqueio de
  MVP (D-008); revisitar só quando houver caso de uso real, não abstrato.

## Context

**Estado do catálogo (2026-08-17):** `catalog.db` de produção foi zerado de
novo hoje (sem backup desta vez, decisão explícita do dono), para a medição
de baseline da Fase 5 (LANC-04) — hoje só tem a fonte `~/Pictures/2026`
(1.382 arquivos), não o acervo completo. Backup do reset anterior
(2026-08-16) segue em `catalog-antes-do-reset-20260816-013503.db` e foi
usado, somente leitura, para calibrar a interpolação de duas âncoras de GPS
(D-074). Uma nova varredura completa do acervo real ainda não rodou. Tratar
como estado operacional atual, não como decisão estrutural — os números
medidos citados nas decisões (D-024 a D-030, D-034, D-046, D-074 etc.) vêm
de acervos anteriores ao(s) reset(s) e continuam válidos como evidência de
prioridade, mesmo que o catálogo precise ser reconstruído.

**Composição do acervo real (medida, motiva a ordem do roadmap):**
Pixel local é raro (~5% de ~99 mil registros conhecidos são arquivo real
legível — 44.661 registros do Apple Fotos só no iCloud, 45.397 do
Lightroom num volume desmontado). GPS é raro e recente (só 4 dos 25 anos do
acervo têm GPS de câmera). Intenção declarada (nome de álbum, nota,
sinalização) é abundante e já está no banco, sem custo de leitura.

**Candidato de maior alavancagem, ainda sem decisão do dono:**
reconectar os dois volumes desmontados/só-iCloud (Lightroom + Apple Fotos,
~90 mil registros) multiplicaria de uma vez o valor de 4 itens do backlog
(detecção facial, análise visual, UI de pessoas, sidecar XMP — todos hoje
bloqueados por falta de pixel alcançável). Proposta de forma em
`docs/prompts/fase-12-alcance-e-tempo.md` (2026-08-08), citando que
`sources/disponibilidade.py:99-107` já detecta o volume remontado noutro
ponto de montagem e recusa, por desenho, reescrever o caminho sozinho — só
falta o comando que oferece o reapontamento. **Não incluído neste roadmap
como fase v1** porque ainda é candidato, não decisão; ver REQUIREMENTS.md
v2 e trazer ao dono antes de iniciar.

**Duas decisões DOC-precedence, não ADR, tratadas como aprovadas para uso
nesta sessão (ver `.planning/INGEST-CONFLICTS.md`):**
- `docs/NAVEGACAO.md` — 3 decisões de navegação (abas com esqueleto comum;
  sidebar=lugar/topo=recorte com chips; rolagem contínua com âncora
  temporal) já refletidas na implementação atual do webapp.
- `docs/EMPACOTAMENTO.md` — decisão de empacotamento via
  python-build-standalone (não PyInstaller), por causa da fragilidade de
  codesign/notarização de libs nativas (libraw, libheif, Pillow/numpy) num
  layout sidecar do PyInstaller. Alimenta o item de lançamento no roadmap.

**Dívida técnica relevante para o roadmap (ver `.planning/codebase/CONCERNS.md`
para o detalhe completo):** motor de sugestões e detector de duplicatas
fazem full-scan em memória sem caminho incremental; navegação por árvore de
pastas é O(n) sem índice em `pasta`; nenhuma rotina de boot reconcilia
`OperationPlan.EXECUTANDO` travado após um crash (só o scanner tem
`reconciliar_orfas` equivalente); `PhotoGrid.tsx` (a grade mais usada do
app) e `ClaudeAdvisor` não têm teste dedicado.

## Constraints

- **Segurança/privacidade**: os 8 invariantes do CLAUDE.md do projeto
  (catalogação somente-leitura; operação física só após aprovação
  explícita e nunca sobrescreve; hash antes/depois de cada cópia; nada sai
  da máquina sem opt-in explícito; subprocesso sem `shell=True`; rosto
  desligado por padrão e sempre local; sem exclusão nem escrita de EXIF no
  MVP; sinal nunca é apagado, só rebaixado) — nunca violar, checados em
  toda fase.
- **Stack fixa**: Python 3.12+/SQLite WAL/SQLAlchemy 2/Alembic no core;
  FastAPI 127.0.0.1-only + React/Vite/TS/Tailwind (`webapp/`) como única
  UI; empacotamento via Tauri v2 + python-build-standalone, Marco 1
  (assinatura ad-hoc) entregue na Fase 5 — Marco 2 (assinado/notarizado)
  segue como próximo passo, pendente de aprovação de custo recorrente.
  Não trocar sem justificativa de ganho concreto.
- **Escala**: acervo real já mediu ~422.738 registros de catálogo em uma
  rodada de auditoria; toda fase que toca consulta/filtro deve continuar
  virtualizada e sem N+1, sem regressão de performance medida.
- **Custo recorrente**: qualquer item que implique custo por foto (provider
  externo de visão/geocodificação) ou custo anual fixo (Apple Developer
  Program, US$99/ano para empacotamento assinado) precisa de aprovação
  explícita do dono antes de entrar em fase — nunca ligado por padrão.
- **Fonte de verdade de tokens de design**: `webapp/src/index.css` bloco
  `@theme`; `docs/DIRECAO_DE_ARTE.md` espelha, não define.

## Key Decisions

<!-- Amostra representativa dos decisões ADR-locked mais relevantes ao
roadmap v2+. Log completo (73 entradas) em docs/DECISOES.md. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Confiança é quantidade (segmentos preenchidos), não semáforo de 3 cores — D-017 | Cor sozinha compete com a foto e falha para daltônicos | ✓ Good |
| Unidade de decisão da Revisão é o grupo, não a linha — D-018 | 63 linhas idênticas empurravam para "aprovar tudo" sem informação | ✓ Good |
| Registro sem valor de acervo é rebaixado a fonte de sinal, nunca apagado — D-024, invariante 8 | Miniatura/derivado pode ser a única testemunha de lugar/hora de uma foto sem GPS | ✓ Good |
| exiftool é extrator padrão quando instalado, fallback puro-Python — D-026 | 0/40 → 40/40 câmeras identificadas em CR3, mais rápido | ✓ Good |
| Mapa do lugar estimado nasce sem tile externo, malha esquemática — D-031 | Tile externo revela coordenada sem nenhum arquivo sair (invariante 4) | ✓ Good |
| Álbum de catálogo externo nomeia, nunca divide acontecimento — D-030/D-034 | Álbuns se aninham; medição mostrou zero ganho de divisão, risco de contagem tripla | ✓ Good |
| Advisor final é Sonnet 5, não Opus 5 nem Haiku 4.5 — D-059/D-060 | Medido nos 104 clusters reais pelo dono, decisão 1 do gate fechada | ✓ Good |
| Inventário por pasta entra antes do lançamento — D-061 | Barato agora (mesma passada de cópia), caro depois (reprocessar catálogo inteiro) | ✓ Good |
| Detecção facial local desce de 1º para 6º no v2 — ROADMAP.md, D-028 | 90% dos registros conhecidos não têm pixel local alcançável hoje | ✓ Good |
| Visão local em vez de remota, sem opção de API externa — PLANO_IA_E_PRODUTO §8 decisão 2 | Mantém invariante 4 sem asterisco; qualidade menor é aceita pelo dono | ✓ Good |
| Reconectar volumes desmontados/iCloud ainda não é decisão | Maior alavancagem medida do backlog, mas exige forma própria e aprovação do dono | — Pending |
| Herança de GPS confronta doadora antes E depois, não só a mais próxima — D-074 | Duas âncoras concordantes corroboram sem inventar bônus de confiança; medido contra 40.678 fotos reais, subconjunto discordante tinha cobertura de só 91,1% (chão de 50,9% numa banda) | ✓ Good |
| EXIF direto de localização (lat/long, cidade, país) autorizado em campo vazio, revoga parte do invariante 7 — D-075 | Sidecar XMP não é lido pelo fluxo real do dono; escopo estreito (só localização, só campo vazio) + rigor de operations/ evita abrir precedente maior | — Pending implementação |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-18 — Milestone v2.0 started*
