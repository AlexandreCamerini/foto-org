# 09 — Melhorias possíveis, backlog e o que NÃO carregar

> Parte do mapa de reconstrução. Consolida `docs/ROADMAP.md` (v2+), `.planning/PROJECT.md` +
> `REQUIREMENTS.md` (milestone v2.0), `.planning/STATE.md`, `docs/AVALIACAO_ARQUITETURA.md`,
> `docs/AVALIACAO_UX.md`, `docs/NAVEGACAO.md` e a auditoria de 2026-09-19. Status em
> 2026-09-19, commit `524903d`.

## 0. A régua (não mudar sem medir)

Prioridade é **valor entregue por unidade de custo para este acervo**, medido — nunca valor
abstrato de funcionalidade (`docs/ROADMAP.md` § Próximas versões). Item cujo valor depende de
dado que o acervo não tem (pixel local, GPS em 2001-2018) desce. Qualquer custo recorrente
(por foto ou anual) exige aprovação explícita do dono antes de virar fase. Erro novo de
classificação vira cenário no benchmark (`scripts/avaliar_agrupamento.py`) **antes** de mexer
em limiar (`docs/AGRUPAMENTO.md`).

## 1. Milestone v2.0 em andamento — "Localização real e evidência expandida"

Ordem de prioridade do dono (`.planning/PROJECT.md` § Current Milestone):

| # | Feature | Requisitos | Status em `524903d` |
|---|---|---|---|
| 1 | Escrita EXIF de localização em campo vazio | EXIF-01..05 | **feito** (Fase 6, D-075..D-078) — com A2/A4 abertos (`08`) |
| 2 | GenAI de pasta → cidade/evento (opt-in, só metadado, custo visível por sessão) | GENAI-01..03 | **feito na essência** (Fase 7, 07-01..07-09; D-079..D-081). Tasks 2/3 do 07-10 adiadas por escolha do dono (Task 2 = sessão real de 10 pastas com a chave do dono, servidor com `ANTHROPIC_API_KEY`; Task 3 = marcar GENAI-01..03 só após checkpoint humano com evidência real); `REQUIREMENTS.md` ainda marca Pending (desatualizado). M2 aberto (`08`) |
| 3 | Sidebar navegável (busca incremental + teclado) | SIDEBAR-01/02 | pendente (Fase 9) |
| 4 | Picker de pasta nativo (Tauri) + progresso de importação com arquivos/total, taxa, ETA (linear, sem gauge) | PICKER-01/02 | pendente (Fase 8) |
| 5 | Confiança como eixo de navegação + saúde do acervo como **distribuição por dimensão** (nunca score único) | CONF-01/02 | pendente (Fase 10) |
| 6 | Motor de corroboração generalizado (padrão D-074 para data/hora e cidade/país; nenhum bônus sem medição) | CORR-01..03 | pendente (Fase 11) — **maior risco de regressão**: toca herança de GPS calibrada em 40.678 fotos (cobertura 91,1%); critério: GPS sai idêntico |
| 7 | Modo ativo de aprendizado (pedir confirmação onde a resposta mais reduz incerteza) | LEARN-01 | deferido (v3+) até 5 e 6 existirem |
| — | Reconectar volumes desmontados/só-iCloud (~90 mil registros) | ARCH-01 | candidato de **maior alavancagem** medido, sem forma nem aprovação. `sources/disponibilidade.py:99-107` já detecta volume remontado noutro ponto; falta o comando de reapontar (esforço S). Multiplica o valor de rosto, visão, UI de pessoas e sidecar XMP de uma vez |

Pendência de decisão registrada em `STATE.md:222`: JPEG com bloco IPTC gravado por outra
ferramenta (ex. Lightroom) gera o aviso `IPTCDigest is not current` do exiftool e reprova a
verificação D-04 mesmo após D-078. Não há allowlist de avisos. Mesma classe de decisão que
D-076/D-077 — aguarda o dono.

## 2. Backlog v2+ do `docs/ROADMAP.md` (itens 1-11), com status real

| # | Item | Esforço | Custo recorrente | Status |
|---|---|---|---|---|
| 1 | Mapa do lugar estimado com raio de incerteza | M | 0 | **feito** (D-031/D-032/D-033/D-050/D-065) |
| 2 | `docs/EVENTOS.md` | XS | 0 | **feito** (165 linhas; ROADMAP:126 desatualizado) |
| 3 | Eventos nomeados por álbum/pasta existente | S/M | 0 | **feito** (D-034); zero nomes novos hoje porque nenhuma das 27.226 marcações está em foto alcançável |
| 4 | Templates configuráveis na UI | S | 0 | **feito** (2026-08-02; `GET/PUT /api/configuracoes/template`, preview) |
| 5 | `tz_estimado` por país herdado | S/M | 0 | **feito** (Fase 11 anterior, 2026-08-16) — mas o mtime ainda não é normalizado por ele (M1) |
| 6 | Detecção facial local (ONNX) | L | 0 dinheiro, CPU alta | pendente; bloqueado por pixel (~90% fora de alcance) |
| 7 | Análise visual local (`VisionProvider`) | M/L | 0 dinheiro, CPU | rebaixado (D-035): só 18 fotos de acervo 2001-2018 com pixel; útil só para cena grosseira 2019+ |
| 8 | UI de pessoas | S/M | 0 | bloqueado por 6 |
| 9 | Sidecar XMP de **todos** os metadados aprovados (para o Lightroom ler) | M | 0 | **parcial**: só localização, como fallback de `exif_write` para formatos sem escrita direta (e com A2 aberto); ROADMAP:252 desatualizado |
| 10 | Empacotamento assinado/notarizado (Marco 2) | M | **US$ 99/ano** | não aprovado; Marco 1 (ad-hoc) entregue |
| 11 | Provider externo opt-in (geocoding/visão por API) | L | **por foto** (~US$ 100 por passada em 99 mil) | último; conflita com invariante 4 sem ganho medido |

## 3. Melhorias derivadas da auditoria de 2026-09-19 (não são bugs; são ausências)

1. **CI.** Não existe `.github/workflows`. Sem CI, `skipif(not exiftool)` esconde a suíte de
   mutação de original (M6). Mínimo: workflow que instala exiftool e roda
   `scripts/verificar.sh`; em sandbox sem rede, marcar os 26 testes de socket/CA como job
   separado.
2. **Linter e type-checker.** Zero configuração (sem ruff/mypy/black em `pyproject.toml`, sem
   eslint/prettier em `webapp/`). Numa reconstrução, nascer com `ruff` + `mypy --strict` nos
   módulos de invariante (`operations/`, `exif_write/`, `security/`) e `eslint` + `tsc --noEmit`.
3. **Um `quando(media)` só** para "quando a foto foi tirada" (EXIF → nome do arquivo → mtime
   normalizado para parede local), usado por evidência, sessão, viagem, acontecimento e herança
   (M1 + M5).
4. **Idempotência e lock de jobs** como propriedade testada (A1, M8): `Barrier` nos testes,
   transição atômica de estado do plano, `isPending` em todo botão que dispara job.
5. **Verificação por valor** em `exif_write/verificacao.py` — presença de tag nunca é prova (A2).
6. **Retomada de plano tolerante a destino íntegro** (M3) e **reconciliação de plano
   `EXECUTANDO` no boot** (CONCERNS/D-069 Tier 3) no mesmo hook que já reconcilia scans.
7. **CSP** via middleware do FastAPI e **Origin com porta** no guard (B1, B2).
8. **Remover ou consumir** endpoints órfãos (`/api/midia/alcances`, `POST /api/reconciliacao`)
   e migrar os 12 `select()` de `server/app.py` para `repositories/` (B8, B9).
9. **Prévia do payload do advisor de cluster.** Hoje o advisor dispara dentro do job
   `sugestoes` com um gate só (`jobs.py:335`) e sem prévia; o GenAI de pasta tem prévia e
   consentimento por sessão. Igualar: mostrar o payload (pastas, amostra de nomes, período,
   contagem, lugares) antes da primeira chamada da rodada — é o que o invariante 4 pede.
10. **Timeout no writer EXIF** (`writer.py:126`) e reconciliação de `ExifWritePlan` órfão no
   boot (análogo ao de scan) — B13 e `04` § Lacunas.
11. **`Fonte.tipo` com `lightroom` no TS** e ícone na sidebar (B11).
12. **Docs vivos**: ROADMAP (itens 2, 9, linha 300), D-075 status, `REQUIREMENTS.md` (GENAI),
   `.planning/codebase/*` (200 commits atrás), `AGENTS.md` (invariante 7 ainda com o texto
   pré-D-075 — não é symlink de `CLAUDE.md` como D-009 pedia), e o prompt do agente de arte
   (`.claude/agents/agente-arte.md`) com tokens hex antigos (`06-UI.arte.md` § divergências) —
   atualizar ou apontar para a fonte de verdade.

## 4. Dívida técnica estrutural (`.planning/codebase/CONCERNS.md`, ainda válida)

- **Caminho incremental** para `SuggestionEngine.gerar()` (`engine.py:266-326`) e
  `DuplicateDetector.detectar()` (`detector.py:120-156`): hoje full-scan em memória; 1,33 s e
  4,54 s em 1.382 registros, não linear em 100 mil+. Reprocessar só mídia nova/alterada desde a
  última `versao_logica`.
- `_completar_sha256` paralelo com o mesmo `ThreadPoolExecutor` + janela do scanner
  (`detector.py:168-183`).
- `security/http_seguro.py`: **antes** do primeiro consumidor, SSRF + DNS rebinding no mesmo PR
  (docstring `:30-39` adia conscientemente).
- Teste dedicado para `PhotoGrid.tsx` (a grade mais usada) e `ClaudeAdvisor` (verificar se ainda
  falta).
- Esquema `metadata_entries` chave-valor (3,6 milhões de linhas hoje): revisitar ao passar de
  250 mil fotos — é a tabela que cresce mais rápido e a mais cara de remodelar depois
  (`AVALIACAO_ARQUITETURA.md` §6).

## 5. Arquitetura (`docs/AVALIACAO_ARQUITETURA.md` §6-7 — riscos ainda pertinentes)

| Risco | Sintoma | Esforço | Status |
|---|---|---|---|
| Um trabalho por vez, sem fila | scan de acervo grande bloqueia o app por horas | médio | aberto — e a corrida A1 mostra que o "um por vez" nem é garantido |
| Ausência de série de métricas de desempenho | regressão não detectável | baixo | aberto (`PERFORMANCE.md` é snapshot manual) |
| `SyncProvider` prometido e inexistente | 1º adaptador de nuvem vaza para o domínio | baixo hoje | aceito — não implementar sync sem criar o Protocol antes |
| Validação de caminho fora de `security/` em endpoints | irrelevante em 127.0.0.1; grave se a UI for exposta | baixo | aceito (endpoints hoje recebem `media_id`, não caminho) |
| Esquema sem derivados/linhagem, tags hierárquicas, direitos, coleções | "mostre só as editadas" sem resposta | médio | fora de escopo por D-008 até caso real |
| Segundo usuário / distribuição | esquema sem dono; segurança depende do loopback | alto | fora de escopo (usuário único) |
| FK sem índice + N+1 em agrupamentos | Viagens lenta | baixo | **corrigido** (D-072, LANC-02) |
| Duas UIs | custo duplo | — | **corrigido** (`2e0ef1a`) |

## 6. UX (`docs/AVALIACAO_UX.md` fase 6 §4, `docs/NAVEGACAO.md`)

Propostas com protótipo em `docs/prototipos/` (ordenadas por quanto aumentam a confiança nas
decisões, §5):
1. **Confiança que leva à evidência** (`01-confianca.html`) — clicar no badge abre a evidência
   que puxou a confiança para baixo. Relaciona-se a D-069 Tier 1 ("confiança agregada
   contradiz evidências") e a CONF-01. Status: verificar.
2. **Revisão em lote** (`02-revisao-em-lote.html`) — incluir "rejeitar em lote" (D-069 Tier 2:
   só existe aprovar). Status: verificar.
3. **Mapa lido × estimado** (`03-mapa-local-estimado.html`) — **feito**.
4. **Linha do tempo por fonte** (`04-linha-do-tempo.html`) — status: pendente.
5. **Plano antes-e-depois** (`05-plano-antes-depois.html`) — status: pendente.

Navegação (`NAVEGACAO.md` § Ordem de implementação): (1) âncora temporal na grade (cabeçalho de
período fixo + seletor ano/mês) — **verificar se implementada**; (2) chip único para fonte e
recorte; (3) alcance/busca/ordenação numa faixa só. Quando NAS e HDs externos entrarem: volume
acima de fonte, lateral vira árvore (SIDEBAR-01/02); balde "sem data" para as fotos sem
`data_capturada` (1.129 hoje).

Revisitar (`AVALIACAO_UX.md` §7): contraste da superfície translúcida sobre foto clara;
virtualização dentro de cada grupo da Revisão; acessibilidade (foco/tab/leitor de tela)
desenhada mas **não testada**; modo claro exigiria redesenhar a mecânica de superfície, não
inverter.

## 7. O que NÃO carregar na reconstrução

- PySide6, Streamlit, `backend/`, `streamlit_app/`, `database/fotos.db` — removidos por decisão;
  não reabrir.
- `security/http_seguro.py` sem consumidor — ou não carregar, ou carregar já com SSRF/rebinding.
- Endpoints órfãos (`/api/midia/alcances`, `POST /api/reconciliacao`) — só se ganharem consumidor.
- Duplicação de `pastaCurta()` (`ClassificacaoPasta.tsx:32` e `Review.tsx`) — um módulo só.
- `skipif` silencioso em teste de invariante.
- `select()` direto em `server/app.py` — passar por `repositories/`.
- `.planning/codebase/*` como fonte (stale); `docs/AUDITORIA_*`, `docs/AVALIACAO_*`,
  `docs/auditoria-pos-gate-fase5.md` como **história**, não spec — a spec é `docs/reconstrucao/`.
- Tokens hex antigos citados em `.claude/agents/agente-arte.md` e no histórico de
  `docs/AVALIACAO_UX.md` — a verdade é `webapp/src/index.css` `@theme` (`06-UI.arte.md`).
- Qualquer "score único" de confiança/saúde, qualquer soma de confianças, qualquer semáforo de
  3 cores — contrariam D-017 e `CONFIANCA.md`.
- Qualquer `DELETE` de mídia, qualquer `move` em operação física, qualquer escrita EXIF fora de
  localização ou em campo preenchido — invariantes.

## 8. Ideias ainda sem decisão (registrar, não implementar)

- **Reencontrar arquivos** (ARCH-01) — reconectar volume por identidade (hash, caminho original,
  tamanho+data); a régua aponta para ele sozinho.
- **Fila de jobs** em vez de "um por vez" — só depois de resolver A1 (lock) e medir se o
  bloqueio de horas acontece de fato no acervo completo.
- **Série temporal de métricas** — persistir o que `scripts/medir_baseline_producao.py` mede a
  cada rodada, para detectar regressão.
- **Balde "sem data"** na grade (NAVEGACAO §revisitar).
- **Allowlist de avisos do exiftool** (`IPTCDigest is not current`) — decisão do dono pendente
  (`STATE.md:222`).
