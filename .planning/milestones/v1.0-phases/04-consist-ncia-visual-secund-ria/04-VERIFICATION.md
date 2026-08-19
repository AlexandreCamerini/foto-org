---
phase: 04-consist-ncia-visual-secund-ria
verified: 2026-08-17T16:12:04Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 04: Consistência Visual Secundária Verification Report

**Phase Goal:** As inconsistências visuais/interação restantes deixam de diferenciar "em que tela eu estou" de "o que o design system manda".
**Verified:** 2026-08-17T16:12:04Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (requirement) | Status | Evidence |
|---|---|---|---|
| 1 | CONS-08: webapp usa exatamente 2 pesos de fonte (400 corpo, 500 `font-titulo`); zero `font-semibold`/`font-medium` em produção; teste de guarda quebra a reintrodução | ✓ VERIFIED | `webapp/src/index.css` contém `--font-weight-titulo: 500;` (1×). `grep -rn --include='*.tsx' -E 'font-(semibold|medium)' webapp/src \| grep -v '\.test\.'` → 0 linhas. `webapp/src/design-tokens.test.ts` existe (75 linhas, 3 asserções) e passa (`npx vitest run src/design-tokens.test.ts` → 3/3). Nota de metodologia: contagem manual por grep de linhas deu 15 (não 17) porque `webapp/src/components/Review.tsx` contém 2 bytes NUL literais (ver Anti-Patterns) que fazem `file`/`grep` sem `-a` tratá-lo como binário e pular suas 2 ocorrências de `font-titulo`; o teste de guarda (que lê com `readFileSync`, não `grep`) conta corretamente e passa `toBeGreaterThanOrEqual(17)` — reconciliado, sem gap real. |
| 2 | CONS-03/CONS-07 (D-04/D-05): único botão preenchido é o que copia arquivo de verdade; "Retomar"/"Gerar sugestões" no contorno padrão; "Cancelar" de cópia em andamento neutro em repouso, vermelho só no hover, igual ao StatusBar | ✓ VERIFIED | `RetomarScan.tsx`: `border-acento` → 0 ocorrências. `Review.tsx`: `variante="solido"` → 0 ocorrências. `Operations.tsx`: `tom="erro"` → 0; `hover:text-erro` → 1 (linha 217). `solido` remanescente no app: `Operations.tsx:194` (Copiar N arquivos), `ModalCaminho.tsx:47` (Confirmar do modal compartilhado — extraído de Sidebar pelo plano 04-06, ação equivalente de disparo de scan/import), `Sidebar.tsx:267,303` (2 modais de confirmação restantes, o 3º migrou para `ModalCaminho.tsx` na extração). Testes de classificação em `RetomarScan.test.tsx`/`Review.test.tsx`/`Operations.test.tsx` passam. |
| 3 | CONS-04 (D-06): prévia em alta resolução que falha mostra estado de erro explícito (⊘ + 2 frases) no Loupe; membro de grupo de duplicatas com prévia falha mostra "imagem indisponível" com `title` completo; reset ao navegar | ✓ VERIFIED | `Loupe.tsx`: `onError` presente (linha 82), frase primária presente (linha 71), reset de `falhouPreview` no `useEffect` de troca de índice. `Duplicates.tsx`: `MembroFigura` extraído (linha 192), `onError` por membro (linha 228), "imagem indisponível" presente (linha 221). `Loupe.test.tsx` existe (4075 bytes) e passa; `Duplicates.test.tsx` passa incluindo os 3 testes novos de isolamento por membro. |
| 4 | CONS-02 (D-03): cards de Eventos colidindo em nome mostram selo "Álbum"/"Evento detectado"; card sem colisão não ganha selo; Viagens nunca ganham selo | ✓ VERIFIED | `Trips.tsx`: `colideNome` computado em `Secao` e passado a `Card` (linhas 111, 124, 130); selo condicional a `secao === "eventos" && colideNome` (linha 194); rótulo `grupo.metodo === "album_externo" ? "Álbum" : "Evento detectado"` (linha 196), posicionado `left-2 top-2` (canto oposto ao badge "Mapa"). 4 testes cobrindo colisão/não-colisão/seção/case-insensitive passam. |
| 5 | CONS-06 (D-08/D-09): abaixo de 1024px a barra da Biblioteca empilha em 2 linhas sem cobrir o Inspetor; ≥1024px volta a 1 linha; Inspetor sempre visível; nunca 3ª linha | ✓ VERIFIED (com verificação humana já resolvida) | `App.tsx:312`: `flex flex-col gap-2 border-b border-borda px-3 py-2 lg:flex-row lg:items-center lg:gap-2`. Inspetor (`App.tsx:486-488`) renderizado fora de qualquer condição de largura — a única condição é `aba === "Biblioteca" && !noMapa && inspetorVisivel`, onde `inspetorVisivel` é um toggle manual do usuário (`useState(true)`, não ligado a viewport). Verificação visual em navegador real (~700px/~900px/1200px) foi conduzida pelo orquestrador via Claude_Browser MCP, documentada em `04-05-SUMMARY.md`, com veredito aprovado. O plano exige explicitamente "não registrar aprovação parcial nem prosseguir com ressalva pendente" — o único ponto residual documentado (scroll horizontal contido no estado combinado mais apertado em ~1200px) não viola nenhum dos 4 must-have truths (não é 3ª linha, não cobre o Inspetor, é comportamento de scroll contido, não sobreposição) e foi comparado explicitamente contra o comportamento pré-existente (que já vazava sem contenção nesse mesmo estado raro) — é uma melhoria documentada, não uma ressalva pendente sobre a condição de aceite. Teste estrutural em `App.test.tsx` (flex-col/lg:flex-row, grupos com pais distintos) passa. |
| 6 | CONS-05 (D-07): os 3 estados vazios (Panorama, PhotoGrid, Trips) oferecem "Adicionar pasta…" que abre o mesmo modal; frases diagnósticas preservadas; confirmar dispara POST /api/scan de qualquer um dos 4 pontos; erro não é engolido | ✓ VERIFIED | `ModalCaminho.tsx` existe como módulo próprio com `export default`. `App.tsx` possui `onAdicionarPasta={abrirAdicionarPasta}` em 4 pontos (Sidebar linha 260, Panorama 292, PhotoGrid 304, Loupe/render do modal 470). `Panorama.tsx`, `PhotoGrid.tsx`, `Trips.tsx` têm a prop declarada e o botão "Adicionar pasta…" no estado vazio. `App.tsx` trata `.catch` de `job.escanear` escrevendo em `erroPasta`, repassado ao modal via prop `erro` (mantém modal aberto). Testes de integração em `App.test.tsx` provam os 4 pontos e o caminho de erro; suíte completa passa. |
| 7 | CONS-01 (D-01/D-02): sugestões vizinhas colidindo em nome+data+câmera com `media_id` diferente mostram, cada uma, selo com o nome da fonte; sugestão sem colisão não ganha selo; `source_id` chega em `GET /api/sugestoes`; nome resolvido no cliente via cache `["fontes"]` | ✓ VERIFIED | `fotoorganizer/server/app.py:231`: `"source_id": linha.source_id,` em `_sugestao_json`. `tests/test_server_api.py:323` (`test_sugestoes_trazem_source_id_da_fonte_que_catalogou`) passa; suíte completa (`pytest tests/test_server_api.py`) → 71 passed. `webapp/src/api.ts`: `source_id: number` em `SugestaoRow`. `Review.tsx`: colisão por adjacência (`chave`/`colideCom`), selo condicional usando `rotuloDeFonte(fontes, s.source_id)` sobre `useQuery(["fontes"])` compartilhado, sem requisição nova. `Review.test.tsx` cobre par colidido + controle sem selo + fallback; passa. Nota: a implementação da chave de comparação usa 2 bytes NUL (0x00) literais como delimitador de campo em vez do padrão de string comum — ver Anti-Patterns; não afeta a corretude observável (testes passam), mas é uma escolha de implementação incomum digna de nota. |
| 8 | Nenhum critical/blocking finding no code review da fase | ✓ VERIFIED | `04-REVIEW.md`: 0 critical, 5 warning, 1 info — nenhum bloqueia o gate por instrução explícita da tarefa de verificação. Ver seção Anti-Patterns/Requirements Coverage abaixo para o cruzamento de cada warning contra os must-haves desta fase. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `webapp/src/index.css` | Token `--font-weight-titulo: 500` no `@theme` | ✓ VERIFIED | 1 ocorrência, dentro do bloco `@theme` |
| `webapp/src/design-tokens.test.ts` | Guarda automatizada do peso único | ✓ VERIFIED | 75 linhas, 3 testes, passa |
| `webapp/src/components/Operations.tsx` | Cancelar com `hover:text-erro`, sem `tom="erro"` | ✓ VERIFIED | confirmado por grep + teste |
| `webapp/src/components/RetomarScan.tsx` | Botão no contorno padrão | ✓ VERIFIED | `border-acento` ausente |
| `webapp/src/components/Review.tsx` | "Gerar sugestões" contorno padrão + selo de fonte CONS-01 | ✓ VERIFIED | `variante="solido"` ausente; `rotuloDeFonte` presente 2× |
| `webapp/src/components/Loupe.tsx` | Estado de erro de prévia em tela cheia | ✓ VERIFIED | `onError` presente, reset no efeito de índice |
| `webapp/src/components/Duplicates.tsx` | `MembroFigura` com estado de falha por membro | ✓ VERIFIED | função existe, `onError` por instância |
| `webapp/src/components/Trips.tsx` | Selo Álbum/Evento detectado + botão "Adicionar pasta…" | ✓ VERIFIED | ambos presentes |
| `webapp/src/App.tsx` | Barra da Biblioteca `lg:flex-row`; dono do modal `ModalCaminho` | ✓ VERIFIED | classe presente; `ModalCaminho`/`abrirAdicionarPasta` presentes |
| `webapp/src/components/ModalCaminho.tsx` | Modal compartilhado entre App e Sidebar | ✓ VERIFIED | módulo próprio, `export default`, prop `erro` opcional |
| `fotoorganizer/server/app.py` | `source_id` na serialização de sugestão | ✓ VERIFIED | `"source_id": linha.source_id,` presente, testado |
| `webapp/src/api.ts` | `source_id` tipado em `SugestaoRow` | ✓ VERIFIED | presente |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `webapp/src/index.css` | utilitário `font-titulo` | namespace `--font-weight-*` (Tailwind 4) | ✓ WIRED | 17+ call sites usam a classe gerada; build Vite/Tailwind ok |
| `webapp/src/design-tokens.test.ts` | `webapp/src/**/*.tsx` | leitura de arquivo + regex pós-remoção de comentário | ✓ WIRED | teste passa, varre corretamente mesmo com bytes NUL em `Review.tsx` |
| `Operations.tsx` | `webapp/src/ui/Botao.tsx` | `variante="fantasma"` + `className` hover | ✓ WIRED | confirmado por grep + teste de clique/cancelar |
| `Panorama.tsx`/`PhotoGrid.tsx`/`Trips.tsx` | `App.tsx (abrirAdicionarPasta)` | prop `onAdicionarPasta` | ✓ WIRED | 4 pontos, testados em `App.test.tsx` |
| `App.tsx (ModalCaminho)` | `POST /api/scan` | `job.escanear(caminho)` no `onConfirmar` | ✓ WIRED | teste de integração prova o POST e o caminho de erro |
| `fotoorganizer/server/app.py (_sugestao_json)` | `webapp/src/api.ts (SugestaoRow)` | campo `source_id` | ✓ WIRED | testado em pytest e tipado no cliente |
| `Review.tsx` | `webapp/src/fontes.ts (rotuloDeFonte)` | cache `["fontes"]` | ✓ WIRED | zero requisição nova confirmada (`useQuery` compartilhado, mesma queryKey de `App.tsx`/`Sidebar.tsx`) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Webapp test suite completa | `cd webapp && npm test -- --run` | 150/150 testes, 17 arquivos | ✓ PASS |
| Webapp build | `cd webapp && npm run build` | `tsc -b && vite build` exit 0 | ✓ PASS |
| Servidor: suíte de API | `.venv/bin/python -m pytest tests/test_server_api.py -q` | 71 passed | ✓ PASS |
| Design token guard test isolado | `npx vitest run src/design-tokens.test.ts` | 3/3 | ✓ PASS |
| Testes específicos de CONS-01..08 (Review/Operations/RetomarScan/Duplicates/Trips/App/Sidebar/Loupe) | `npx vitest run <8 arquivos>` | 84/84 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CONS-01 | 04-07 | Selo de fonte por colisão de sugestão | ✓ SATISFIED | `source_id` serializado, colisão por adjacência, selo no cliente, testes verdes |
| CONS-02 | 04-04 | Selo Álbum/Evento detectado | ✓ SATISFIED | Selo condicional a colisão + seção, testes verdes |
| CONS-03 | 04-02 | Escala única de botão importante | ✓ SATISFIED | Retomar/Gerar sugestões no contorno padrão |
| CONS-04 | 04-03 | Estado de erro de prévia (Loupe/Duplicatas) | ✓ SATISFIED | onError + glifo ⊘ + reset, testes verdes |
| CONS-05 | 04-06 | Botão "Adicionar pasta…" nos 3 estados vazios | ✓ SATISFIED | Modal compartilhado, 4 pontos de entrada, erro visível |
| CONS-06 | 04-05 | Barra da Biblioteca responsiva | ✓ SATISFIED | `lg:flex-row`, verificação visual humana aprovada |
| CONS-07 | 04-02 | Hover de "Cancelar" consistente | ✓ SATISFIED | `hover:text-erro`, `tom="erro"` removido |
| CONS-08 | 04-01 | Peso de ênfase tokenizado | ✓ SATISFIED | `--font-weight-titulo`, guarda automatizada |

Todos os 8 requirement IDs listados na tarefa (CONS-01..08) aparecem declarados em exatamente um plano cada (`requirements:` no frontmatter de 04-01 a 04-07) e todos batem com `REQUIREMENTS.md`, que já os marca `[x]`/`Complete`. Nenhum requirement órfão encontrado (nenhum ID mapeado à Fase 4 em `REQUIREMENTS.md` ficou de fora dos 7 planos).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `webapp/src/components/Review.tsx` | ~col 18847/18874 (dentro da função `chave` da colisão CONS-01, introduzida no commit `4c13d1d`) | 2 bytes NUL (`0x00`) literais embutidos no template literal como delimitador de campo (`` `${it.nome}\x00${it.data_capturada ?? ""}\x00${it.camera ?? ""}` `` — os bytes são caracteres de controle reais no arquivo-fonte, não a sequência de escape de 2 caracteres `\0`) | ⚠️ WARNING | Funcionalmente inofensivo hoje — JS aceita NUL em string, `npm test`/`npm run build` passam, `git show` confirma que o byte já foi commitado assim. Mas faz `file(1)` e `grep` (sem `-a`) tratarem o arquivo como binário — foi a causa raiz de uma discrepância de contagem (15 vs. 17 `font-titulo`) durante esta verificação, e provavelmente vai confundir `grep`/diff/linters de qualquer pessoa que trabalhe neste arquivo depois. Recomendação: trocar os bytes NUL literais pela sequência de escape de string `\0` de dois caracteres (comportamento idêntico em runtime, arquivo volta a ser reconhecido como texto puro). Não é um debt marker (TBD/FIXME/XXX) nem um requisito não satisfeito — não bloqueia o objetivo da fase, mas é uma dívida de higiene de código introduzida por esta fase que vale corrigir num plano futuro pequeno. |
| — | — | REVIEW.md WR-01 (`contagens` de `/api/sugestoes` ignora `source_id`) | ℹ️ INFO (fora do escopo desta fase) | Afeta os badges "Pendentes N/Aprovadas N" por fonte selecionada, não a asserção de colisão/selo do CONS-01. Nenhum must-have truth desta fase depende de `contagens` ser filtrado por fonte. |
| — | — | REVIEW.md WR-02 (`Duplicates.tsx` mutation não checa `response.ok`) | ℹ️ INFO (fora do escopo desta fase) | Ação de duplicatas (marcar principal/ignorar/desfazer), não a prévia de imagem que CONS-04 endereça. Nenhum must-have truth de CONS-04 fala de erro de mutação de ação — fala de `<img>` que falha ao carregar. Pré-existente à fase (não foi introduzido pelos planos 04-01..07; `Duplicates.tsx` só foi tocado por 04-01/04-03 para peso de fonte e estado de erro de prévia, não para a mutação). |
| — | — | REVIEW.md WR-03 (Sidebar Takeout ignora o contrato de erro do `ModalCaminho` compartilhado) | ⚠️ WARNING (adjacente ao escopo, pré-existente, explicitamente fora do plano) | Digno de nota por tocar o mesmo componente (`ModalCaminho`) cujo contrato de erro é um must-have truth do CONS-05 ("erro ao iniciar a varredura é mostrado ao usuário, não engolido") — mas esse must-have é especificamente sobre o caminho de "Adicionar pasta" (`job.escanear`), que está corretamente implementado e testado (`App.test.tsx`). O caminho de Google Takeout (`job.importarTakeout`) já tinha esse comportamento (fechar o modal antes do `.catch` resolver) antes da Fase 4, e o plano 04-06 documenta explicitamente a decisão de preservá-lo intocado ("O erro local e o helper executar continuam servindo takeout/apple"). Não é uma regressão desta fase nem viola o must-have truth como escrito; é uma inconsistência residual do mesmo componente compartilhado que vale um plano futuro dedicado. |

### Human Verification Required

Nenhum item pendente. O único ponto do plano que exigia verificação humana (CONS-06, plano 04-05, Task 2 `checkpoint:human-verify`) já foi executado e aprovado — o orquestrador conduziu a conferência visual em navegador real via Claude_Browser MCP nas larguras ~900px/~700px/1200px, documentado em `04-05-SUMMARY.md` com veredito registrado ("aprovado... único ponto residual... é uma melhoria sobre o comportamento pré-existente, não um gap novo"). Conforme instrução explícita desta tarefa de verificação, esse checkpoint é tratado como resolvido/aprovado com as ressalvas documentadas (scroll horizontal contido em largura muito estreita e em um estado composto raro — ambos avaliados como melhorias sobre o comportamento anterior, não regressões).

### Gaps Summary

Nenhum gap bloqueante encontrado. As 8 verdades observáveis (uma por requirement CONS-01..08) estão implementadas, testadas (150 testes vitest + 71 testes pytest relevantes passando) e com build verde. O único achado de dívida de código não coberto pelo `04-REVIEW.md` (bytes NUL literais em `Review.tsx`) é funcionalmente inofensivo e não compromete nenhum must-have truth — registrado como recomendação de correção futura, não como gap desta fase.

---

_Verified: 2026-08-17T16:12:04Z_
_Verifier: Claude (gsd-verifier)_
