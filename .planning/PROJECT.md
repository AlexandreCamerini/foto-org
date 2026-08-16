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

### Active

<!-- Current scope for this roadmap. Mined from docs/ROADMAP.md v2+ backlog,
docs/PLANO_IA_E_PRODUTO.md launch prerequisites, and docs/AVALIACAO_UX.md
prioritized fixes — see REQUIREMENTS.md for the full checklist and
ROADMAP.md for phase mapping. -->

- [ ] Timezone estimado a partir do país herdado (fecha o último item
  bloqueado por D-025, agora desbloqueado pelo mapa concluído)
- [ ] Correção de 4 defeitos medidos (não hipótese) na rodada de UX de
  2026-08-06: SINAL órfão invisível, vídeo não lido pelo scanner, filtro
  "Tudo" sem WHERE, assimetria Evento×Viagem no advisor
- [ ] Revisão navegável 100% por teclado e consistente com
  `docs/DIRECAO_DE_ARTE.md` (7 achados de esforço P/M)
- [ ] Consistência visual secundária (selos de fonte/álbum×evento, estado
  de erro de imagem, estados vazios com ação, hover/peso de texto
  tokenizado) — 8 achados restantes
- [ ] Preparação para lançamento: empacotamento assinado/notarizado,
  índices de FK ausentes (incl. `pasta`), onboarding do primeiro acervo,
  série de métricas de desempenho

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Análise de visão/reconhecimento via provedor externo (nuvem) — recomendação
  explícita de "fechar a porta" em `docs/PLANO_IA_E_PRODUTO.md` §8 decisão 2;
  conflita com o invariante 4 (nada sai da máquina por padrão) sem ganho que
  justifique o risco. Visão e rostos, quando entrarem, entram locais.
- Exclusão de fotos e escrita direta de EXIF — invariante 7 do CLAUDE.md;
  MVP não implementa; futuro é sidecar XMP apenas, e mesmo esse depende de
  acesso físico ao volume (ver v2 backlog).
- Reescrita de UI em PySide6 ou qualquer stack que não seja o webapp — já
  decidido e revertido (webapp é a única UI, commit `2e0ef1a`); não reabrir
  sem evidência nova.
- 4 lacunas de esquema DAM (derivados/linhagem, tags hierárquicas, direitos,
  coleções autorais) — classificadas explicitamente como não-bloqueio de
  MVP (D-008); revisitar só quando houver caso de uso real, não abstrato.

## Context

**Estado do catálogo (2026-08-16):** `catalog.db` de produção foi zerado
hoje (backup em `catalog-antes-do-reset-20260816-013503.db`); uma nova
varredura completa ainda não rodou. Tratar como estado operacional atual,
não como decisão estrutural — os números medidos citados nas decisões
(D-024 a D-030, D-034, D-046 etc.) vêm do acervo antes do reset e continuam
válidos como evidência de prioridade, mesmo que o catálogo precise ser
reconstruído.

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
  UI; Tauri v2 é o alvo de empacotamento futuro. Não trocar sem
  justificativa de ganho concreto.
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

---
*Last updated: 2026-08-16 after initial project setup (new-project-from-ingest)*
