# Requirements: Foto Organizer v2.0

Ver `.planning/PROJECT.md` § Current Milestone para o objetivo e
`.planning/research/SUMMARY.md` para o levantamento que fundamenta a ordem
e o escopo abaixo. Decisões de escopo travadas nesta sessão de discussão:
D-075 (`docs/DECISOES.md`) para EXIF; demais decisões (ordem de fases,
forma do GenAI, formato do índice de saúde) confirmadas via
`AskUserQuestion` durante `/gsd:new-milestone`, não assumidas.

## v2.0 Requirements

### EXIF — Escrita de localização no arquivo original

- [ ] **EXIF-01**: Dono pode aprovar um plano dry-run que lista, por
  arquivo, quais campos de localização (GPS lat/long, cidade, país) estão
  vazios e seriam preenchidos, antes de qualquer escrita acontecer.
- [ ] **EXIF-02**: Sistema escreve GPS lat/long, cidade e país no EXIF do
  arquivo original somente quando o campo está vazio — nunca sobrescreve
  valor já preenchido, mesmo que a sugestão discorde dele.
- [ ] **EXIF-03**: Cada escrita é verificada por diff completo de tags
  antes/depois (não hash de arquivo inteiro — a escrita é mutação
  intencional) e registrada em audit log, incluindo falha parcial.
- [ ] **EXIF-04**: Sistema nunca escreve campos EXIF fora de localização
  (data, câmera, autor etc.) — fora de escopo, mesmo com evidência
  disponível.

### GENAI — Classificação de pasta por IA

- [ ] **GENAI-01**: Dono habilita a classificação de pasta→cidade/evento
  por sessão, com custo estimado visível antes de confirmar — desligado
  por padrão, mesmo modelo de opt-in do Advisor existente.
- [ ] **GENAI-02**: Sistema envia somente o nome da pasta e metadados já
  catalogados (nunca imagem) ao classificar, usando Claude Sonnet 5.
- [ ] **GENAI-03**: Resultado da classificação de pasta entra como
  `Evidence` própria (origem, campo, valor, confiança, justificativa),
  nunca reaproveitando o tipo de resultado do Advisor de cluster.

### PICKER — Seletor de pasta e progresso de importação

- [ ] **PICKER-01**: Dono seleciona a pasta de origem por diálogo nativo
  do SO (Tauri), substituindo o campo de texto livre atual do
  `ModalCaminho`.
- [ ] **PICKER-02**: Barra de progresso de importação mostra granularidade
  adicional (arquivos processados/total, taxa, ETA) mantendo o formato
  linear já usado no `StatusBar` — sem gauge radial.

### SIDEBAR — Navegação

- [ ] **SIDEBAR-01**: Dono busca uma pasta por texto (busca incremental)
  dentro da árvore da sidebar, sem precisar expandir manualmente até
  achar.
- [ ] **SIDEBAR-02**: Árvore da sidebar é navegável por teclado (setas,
  Enter, Home/End), consistente com o padrão já estabelecido em
  `Review.tsx` (REV-01).

### CONF — Confiança como eixo de navegação e saúde do acervo

- [ ] **CONF-01**: Dono filtra/navega a grade por faixa de confiança
  (alta/média/baixa) como um eixo de navegação de primeira classe, não só
  um badge por item.
- [ ] **CONF-02**: Dono vê a saúde do acervo como distribuição por
  dimensão (% com localização de alta confiança, % com data de alta
  confiança, % com categoria de alta confiança) — nunca como um score
  único combinado.

### CORR — Motor de corroboração generalizado

- [ ] **CORR-01**: Herança de data/hora confronta doadora antes E depois
  (mesmo padrão de D-074 para GPS) antes de aceitar, em vez de extrapolar
  de uma âncora única.
- [ ] **CORR-02**: Herança de cidade/país por contexto de pasta/álbum é
  confrontada entre fontes independentes antes de aceitar; concordância
  categórica (não geométrica) usa correspondência exata como critério —
  nunca um limiar de distância/similaridade inventado sem medição.
- [ ] **CORR-03**: Nenhum bônus de confiança por corroboração é aplicado
  sem medição prévia contra dado real (mesmo padrão de D-074) — cada tipo
  de evidência generalizado precisa da própria medição, não herda a
  calibração do GPS por analogia.

## Future Requirements (v3+)

- **LEARN-01**: Modo ativo de aprendizado — sistema pede confirmação
  direcionada nos casos de menor confiança/maior incerteza, priorizando
  onde a resposta do dono mais reduz incerteza do acervo. Deferido até
  CONF (eixo de confiança) e CORR (corroboração generalizada) existirem —
  depende de ambos para saber o que perguntar e como usar a resposta.
- **ARCH-01**: Reconectar volumes desmontados/iCloud (Lightroom + Apple
  Fotos, ~90 mil registros) — candidato de maior alavancagem medido, mas
  ainda pendente de forma e aprovação do dono (carregado do milestone
  v1.0).

## Out of Scope

- Exclusão de fotos — invariante 7, nunca implementada.
- Escrita EXIF fora de localização (data, câmera, autor etc.) — D-075
  restringe o escopo explicitamente.
- Sobrescrita de campo EXIF já preenchido — D-075 proíbe, mesmo que a
  sugestão discorde do valor existente.
- Envio de imagem para classificação GenAI — GENAI-02 restringe a
  metadado apenas, consistente com invariante 4.
- Score único de saúde do acervo — CONF-02 usa distribuição por dimensão
  para não violar o modelo elo-mais-fraco de D-017.
- Gauge radial de progresso — PICKER-02 mantém o padrão linear do setor
  (Immich/PhotoPrism/digiKam), sem diferenciador puramente visual.
- Reconectar volumes desmontados — permanece como ARCH-01 em Future
  Requirements, fora das fases v2.0.

## Traceability

Mapeado pelo roadmapper em 2026-08-18. Cobertura: 16/16 requisitos v2.0 →
exatamente uma fase cada, sem órfão e sem duplicata. Detalhe de cada fase
em `.planning/ROADMAP.md` § Phase Details.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXIF-01 | Phase 6 — Escrita EXIF de localização | Pending |
| EXIF-02 | Phase 6 — Escrita EXIF de localização | Pending |
| EXIF-03 | Phase 6 — Escrita EXIF de localização | Pending |
| EXIF-04 | Phase 6 — Escrita EXIF de localização | Pending |
| GENAI-01 | Phase 7 — Classificação de pasta por GenAI | Pending |
| GENAI-02 | Phase 7 — Classificação de pasta por GenAI | Pending |
| GENAI-03 | Phase 7 — Classificação de pasta por GenAI | Pending |
| PICKER-01 | Phase 8 — Picker nativo + progresso de importação | Pending |
| PICKER-02 | Phase 8 — Picker nativo + progresso de importação | Pending |
| SIDEBAR-01 | Phase 9 — Sidebar navegável | Pending |
| SIDEBAR-02 | Phase 9 — Sidebar navegável | Pending |
| CONF-01 | Phase 10 — Confiança como eixo + índice de saúde | Pending |
| CONF-02 | Phase 10 — Confiança como eixo + índice de saúde | Pending |
| CORR-01 | Phase 11 — Motor de corroboração generalizado | Pending |
| CORR-02 | Phase 11 — Motor de corroboração generalizado | Pending |
| CORR-03 | Phase 11 — Motor de corroboração generalizado | Pending |
| LEARN-01 | — (v3+) | Deferred — depende de CONF e CORR existirem |
| ARCH-01 | — (v3+) | Deferred — pendente de forma e aprovação do dono |

### Nota de refinamento (EXIF-03 × D-075)

D-075 escreve "hash antes/depois de cada escrita". EXIF-03 refina para
**diff completo de tags** antes/depois: a escrita EXIF é mutação
intencional do arquivo, então o hash do arquivo inteiro *tem* que mudar e
não serve como critério de aprovação. O hash continua registrado como fato
de auditoria; a verificação que aprova a escrita é a de tags. Refinamento
de forma, não de escopo — o rigor de `operations/` que D-075 exige
permanece.
