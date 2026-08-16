# Decisions (ADR intel)

Synthesized from the 2 documents classified `ADR` in this ingest. Source of
truth for every entry below remains the original file — this is a
navigable index, not a replacement.

- `docs/DECISOES.md` — classified ADR, file-level `locked: false` because
  status varies per entry (per classifier note and per the synthesis
  instruction for this run). Each `D-XXX` entry's own `Status:` line is
  the real lock signal, applied individually below.
- `docs/NAVEGACAO.md` — classified ADR (medium confidence), file-level
  `locked: false`. Content reads as final ("Escolhida") for all three
  decisions, but there is no `Status: Accepted` marker. See WARNING in
  `INGEST-CONFLICTS.md` — user must confirm lock status before roadmapping
  treats these as unoverridable.

---

## docs/DECISOES.md — 73 entries, chronological

Legend: **[LOCKED]** = entry's own Status line contains some form of
"decidido" (decided — including "por timeout", "pelo dono", "por medição",
"implementado", "e implementado"). **[PENDING]** = Status is "aguardando"
(awaiting) or the entry is explicitly a recorded finding rather than a
closed decision. Precedence rule for this ingest: LOCKED entries cannot be
auto-overridden by any other source in this batch (none were found to
conflict — see `INGEST-CONFLICTS.md` INFO bucket for the one real
cross-doc contradiction found, which is ADR-vs-SPEC, not ADR-vs-ADR).

| ID | Title | Status |
|----|-------|--------|
| D-001 | Autonomia cobre documentos e protótipos, não código de produção | [LOCKED] decidido por timeout |
| D-002 | O timeout de 10 minutos não vale para ação irreversível ou externa (classe C sempre espera) | [LOCKED] decidido |
| D-003 | Um arquivo de prompt por fase, com protocolo compartilhado | [LOCKED] decidido |
| D-004 | IA embarcada é superfície de produto, com três restrições (regra determinística primeiro; nenhuma infra de agente caseira; saída de modelo é evidência, nunca decisão automática) | [LOCKED] decidido por timeout |
| D-005 | Fase 6 pode rodar em paralelo às fases 3–5 | [LOCKED] decidido |
| D-006 | Fase 1 executada sem subagente | [LOCKED] decidido |
| D-007 | `docs/ARQUITETURA.md` não foi corrigido nesta fase (divergências registradas, correção adiada) | [LOCKED] decidido |
| D-008 | Quatro lacunas de esquema (derivados/linhagem, tags hierárquicas, direitos, coleções) classificadas como não-bloqueio de MVP | [LOCKED] decidido por timeout |
| D-009 | `AGENTS.md` deveria ser symlink de `CLAUDE.md` (recomendado, não executado) | [PENDING] aguardando (fora da fronteira) |
| D-010 | Catálogo isolado por redirecionamento de `HOME` durante auditoria | [LOCKED] decidido |
| D-011 | Execução de plano (fora de dry-run) não foi exercitada nesta fase | [PENDING] aguardando (classe C) |
| D-012 | `npm install` no worktree tratado como classe A (não classe C) | [LOCKED] decidido |
| D-013 | Capturas de tela não versionadas; evidência de SQL/API usada no lugar | [LOCKED] decidido por timeout |
| D-014 | `design-mirror` (Bright Data) substituído por extração via navegador (`getComputedStyle`) | [LOCKED] decidido |
| D-015 | Peakto rejeitada como referência visual (mantida só como referência de IA) | [LOCKED] decidido por timeout |
| D-016 | Fronteira aberta para as quatro correções curtas pós-auditoria (itens 1,3,4,7 aprovados pelo dono) | [LOCKED] decidido |
| D-017 | Confiança como quantidade (segmentos preenchidos), não como semáforo de 3 cores | [LOCKED] decidido por timeout |
| D-018 | A unidade de decisão da tela de Revisão passa a ser o grupo (aprovação em lote), não a linha | [LOCKED] decidido por timeout |
| D-019 | `defusedxml` declarado como extra opcional, não instalado no venv compartilhado | [PENDING] aguardando (classe C) |
| D-020 | exiftool não entra nesta rodada (Python puro + script de medição preparado) | [PENDING] aguardando (classe C) — **superseded in effect by D-026**, ver abaixo |
| D-021 | Precedência de metadado XMP → IPTC → EXIF (valor canônico; os três continuam gravados como evidência) | [LOCKED] decidido por timeout (não implementado — depende de D-023) |
| D-022 | Advisor sobe para Opus 5 com `thinking` desligado | [LOCKED] decidido — **superseded in effect by D-060** (modelo final é Sonnet 5) |
| D-023 | Colunas tipadas de direitos/autoria ficam para depois da medição de volume | [LOCKED] decidido por timeout |
| D-024 | Registro que não é acervo é rebaixado a fonte de sinal, nunca apagado — elevado a invariante 8 do CLAUDE.md | [LOCKED] decidido pelo dono |
| D-025 | A janela de herança de GPS depende do campo herdado (cidade 10min / região 2h / país 12h) | [LOCKED] decidido pelo dono |
| D-026 | exiftool passa a ser o extrator padrão quando o binário está instalado, com fallback puro-Python automático | [LOCKED] decidido pelo dono (instalou o binário a pedido) |
| D-027 | MakerNotes fica fora da base bruta de metadados (83% do volume, sem valor para o app) | [LOCKED] decidido pelo dono |
| D-028 | Lightroom entra como fonte externa e é a principal do discovery (referência, nunca acervo; leitura `immutable=1`) | [LOCKED] decidido pelo dono |
| D-029 | Câmera com receptor de GPS próprio é sinal diferente (mais confiável) de coordenada herdada de celular pareado | [PENDING] registrado, aguardando o modelo de evento |
| D-030 | Álbum de catálogo externo nomeia, nunca divide acontecimento | [LOCKED] decidido por medição |
| D-031 | O mapa do lugar estimado nasce sem tiles (malha esquemática; tile externo violaria invariante 4) | [LOCKED] decidido pelo orquestrador, sem objeção do dono |
| D-032 | O raio de incerteza do mapa é medido (`raio(Δt) = min(50km, max(15m, 6m/s×Δt))`), não suposto pela janela de D-025 | [LOCKED] decidido por medição |
| D-033 | Foto fora de alcance continua desenhada no mapa, com `motivo_indisponivel` anexado, contada em `fora_de_alcance` (subconjunto de `no_mapa`) | [LOCKED] decidido pelo orquestrador |
| D-034 | Álbum nomeia onde a pasta não nomeia, e não passa por cima dela (regra de desempate em 3 camadas; ganho medido hoje: zero, ganho bloqueado: 20.515 fotos aguardando alcance) | [LOCKED] decidido por medição |
| D-035 | As 45.822 miniaturas do Apple Fotos já saíram do catálogo (remoção retroativa registrada); item 5 do ROADMAP desce por falta de dado | [PENDING] registrado por medição — ver nota de inferência abaixo |
| D-036 | Bug pego em revisão pré-commit: reapontar fonte quase reescreveu referência de nuvem como caminho de arquivo; corrigido com filtro `startswith(prefixo_antigo)` | [LOCKED] sem linha `Status:` explícita — ver nota de inferência abaixo |
| D-037 | Bug pego em revisão pré-commit: "não visto no walk" quase virou sinônimo de "arquivo apagado" (2 causas corrigidas: fonte externa fundida, `OSError` engolido) | [LOCKED] sem linha `Status:` explícita — ver nota de inferência abaixo |
| D-038 | Uma foto tem dois instantes (`data_capturada` hora de parede + `data_capturada_utc` absoluta); offset é a diferença, nunca uma terceira coluna; igualdade = fuso desconhecido | [LOCKED] decidido |
| D-039 | Referência PhotoPrism + síntese de backlog cruzando as duas leituras (fase 14) | [LOCKED] decidido |
| D-040 | O diferencial não é a linguagem de busca, é o que ela consegue perguntar | [LOCKED] decidido |
| D-041 | Estado do pipeline no catálogo sai da lista de "vale importar" | [LOCKED] decidido |
| D-042 | Empilhamento de capturas irmãs: os dois mapas discordavam | [LOCKED] decidido |
| D-043 | `versao_logica` é escrito e nunca lido; conserto é um token, não um redesenho | [LOCKED] decidido |
| D-044 | A ordem dos itens da fase 14 não é a ordem de valor/custo bruta | [LOCKED] decidido |
| D-045 | Lib preparatória dos 4 itens da fase 14 (+ item 5 do roadmap), em staging fora da fronteira | [LOCKED] decidido |
| D-046 | Medição do empilhamento de capturas irmãs: D-042 resolvida, 11,72% do acervo | [LOCKED] decidido |
| D-047 | "Resíduo" do advisor é 39% das sessões e 43% do acervo, não zero — PLANO_IA_E_PRODUTO.md §2/§3 revisado | [PENDING] aguardando (classe B — decisão 1 do gate da fase 5 depende) |
| D-048 | Comparação Opus 5 × Haiku 4.5 em 5 clusters reais: Haiku inventa onde Opus recusa | [PENDING] aguardando (decisão final da fase 5 é do dono) |
| D-049 | Comparação Opus 5 × Haiku 4.5 nos 104 clusters reais: bug no relatório, sinal de D-048 confirmado | [LOCKED] decidido (recomendação); aprovação final é a decisão 1 do gate (fechada em D-060) |
| D-050 | O mapa do lugar estimado existe e funciona, mas ninguém acha (achado de descoberta de UI) | [LOCKED] decidido (achado registrado; correção fica para UX — fechado por D-065) |
| D-051 | "Gerar sugestões" não é geo-first por desenho: cascata prioriza pasta/tempo, geocodificação é lazy por sessão | [PENDING] aguardando (classe B — plano pronto) |
| D-052 | Regra 1-2 (geo primeiro) não exige reordenar a cascata de categoria — geocoding e herança de GPS já são funções puras, migráveis | [PENDING] aguardando (plano revisado) |
| D-053 | Categoria travada em 3 valores em dois lugares; expansão é um eixo novo (tipo de mídia), não mais opções no mesmo campo | [PENDING] aguardando (classe B — medição é o próximo passo) |
| D-054 | Hipótese de D-053 refutada por medição: sessões "neutra" não são screenshots/WhatsApp disfarçados | [LOCKED] decidido (hipótese refutada) |
| D-055 | Fase D fechada: dono confirma que a trava do Item B não tinha base real | [LOCKED] decidido |
| D-056 | Dono aprova o plano da fase 5 para as Fases A e B' do diagnóstico "Gerar sugestões" | [LOCKED] decidido pelo dono |
| D-057 | Fase A implementada: palavra-chave XMP/IPTC vira evidência de categoria (commit `7492853`) | [LOCKED] decidido (implementado) |
| D-058 | Fase B' implementada: geo-resolução cedo, escopo menor do que D-052 previa (commit `b5f94b2`) | [LOCKED] decidido (implementado) |
| D-059 | Decisão 1 do gate: dono propõe Sonnet 5, ainda não medido — script generalizado para comparar qualquer par de modelos | [PENDING] aguardando (medição real fica com o dono, classe C) |
| D-060 | Decisão 1 do gate fechada: **Sonnet 5 no advisor**, medido nos 104 clusters reais | [LOCKED] decidido pelo dono — decisão 1 do gate fechada |
| D-061 | Decisão 3 do gate fechada: inventário por pasta entra antes do lançamento | [LOCKED] decidido pelo dono — gate da fase 5 fechado nas três decisões |
| D-062 | Desenho do inventário por pasta pronto para implementar (ver `docs/desenho-inventario-por-pasta.md`) | [PENDING] aguardando aprovação do dono para virar fatia |
| D-063 | Dono aprova a implementação do inventário por pasta | [LOCKED] decidido pelo dono |
| D-064 | Inventário por pasta implementado (commit `6efde4e`) | [LOCKED] decidido (implementado) — decisão 3 do gate fechada |
| D-065 | Badge "Mapa" no card de Viagens/Eventos corrige D-050 (commit `d0f215d`) | [LOCKED] decidido (implementado) — D-050 fechado |
| D-066 | Pasta acentuada em NFD não batia como "downloads"/"capturas" no detector de tipo | [LOCKED] decidido e implementado |
| D-067 | Mês acentuado em NFD não batia em `grouping/datas.py` | [LOCKED] decidido e implementado — D-066 fechado |
| D-068 | "Organizáveis" passa a exigir a fonte respondendo, e o funil afunila por construção | [LOCKED] decidido |
| D-069 | Auditoria pós-gate da fase 5: 18 achados medidos, nenhum é regressão desta sessão | [PENDING] aguardando (classe B — 18 candidatos a decisão, dono escolhe) |
| D-070 | Fatia #1 de D-069: UI de duplicata VARIANTE não avisa mais ao excluir RAW ou JPEG (implementado e commitado) | [LOCKED] decidido (implementado) — D-069 achado 1 fechado |
| D-071 | Fatia #2 de D-069: badge "Alta" em "Não classificadas" vira "Sem categoria" (implementado e commitado) | [LOCKED] decidido (implementado) — D-069 achado 2 fechado |
| D-072 | Fatia #3 de D-069: aba Viagens de 50-120s+ para ~0,1s (implementado e commitado) | [LOCKED] decidido (implementado) — D-069 achado 3 fechado |
| D-073 | Mês por extenso sem reconhecimento em `grouping/datas.py` — achado 5 de D-069 | [LOCKED] decidido e implementado (parcial) |

**Locked count: 59. Pending count: 14** (D-009, D-011, D-019, D-020, D-029,
D-035, D-047, D-048, D-051, D-052, D-053, D-059, D-062, D-069).

**Superseded-in-place pairs (not a conflict — same document resolves its
own chronology):** D-020→D-026 (exiftool absent → exiftool now default),
D-022→D-060 (Opus 5 → Sonnet 5 as advisor model), D-050→D-065 (mapa
undiscoverable → badge fix), D-053↔D-054↔D-055 (hypothesis raised, then
refuted, then trava closed), D-069→D-070/071/072/073 (audit findings →
individual fix slices). Downstream consumers should treat the
higher-numbered (later) entry as current state.

**Inference note (transparency, not silent):** D-035, D-036, D-037 lack a
clean `Status: decidido` / `Status: aguardando` string.
- D-035's Status line reads "registrado por medição; reordenação do
  ROADMAP aplicada nesta mesma sessão" — a recorded finding paired with an
  action already taken (ROADMAP reordered), but not phrased as "decidido".
  Classified PENDING/informational here; the ROADMAP reordering itself is
  already reflected in `docs/ROADMAP.md` v2+ ordering.
- D-036 and D-037 have no `Status:` line at all; both are tagged "Classe: A
  ... registro do achado e da correção, não uma escolha em aberto" (record
  of a finding and its fix, not an open choice) — i.e. bugs found and
  fixed pre-commit. Classified LOCKED here on that basis (closed, not
  pending a decision).

---

## docs/NAVEGACAO.md — 3 decisions (ADR, locked: false per classifier)

1. **Abas com esqueleto comum, não módulos** — six tabs keep one shared
   skeleton instead of Lightroom-style per-module layouts.
2. **Navegação à esquerda = lugar, topo = recorte, um estado só** — sidebar
   answers "where am I looking from" (fonte/volume/pasta); top bar answers
   "what am I looking at" (alcance/busca/ordenação/chip). Every active
   filter renders as a removable chip in one place, including source.
3. **Rolagem contínua com âncora temporal** — grid stays infinite-scroll
   (already virtualized, already fast: 200 items/98ms measured), adds a
   fixed period header + year/month jump selector instead of switching to
   pagination.

All three are written as final ("Escolhida") but the document has no
`Status: Accepted` marker and the classifier set `locked: false`. **See
WARNING in `INGEST-CONFLICTS.md`** — treat these as high-confidence
proposed decisions, not unoverridable LOCKED ADRs, until the user
confirms.

---

## Candidate decision not yet formalized as ADR

`docs/EMPACOTAMENTO.md` (classified DOC, source:
`docs/EMPACOTAMENTO.md`) contains a `## Decisão` section stated as final:
**python-build-standalone + frozen venv, not PyInstaller**, for macOS
packaging via Tauri v2 (rationale: PyInstaller's sidecar layout makes
codesign/notarization of native libs — libraw, libheif, Pillow/numpy —
fragile; PBS produces a normal Python tree signable in one `codesign`
pass). Two alternatives explicitly rejected: PyInstaller sidecar, and
venv-on-first-boot (rejected for breaking the local-first invariant under
hardened runtime). This reads as a committed decision but lives in a
DOC-classified file, so it carries DOC (lowest) precedence in this
ingest rather than ADR precedence — flagged so the roadmapper doesn't
silently under-weight it.
