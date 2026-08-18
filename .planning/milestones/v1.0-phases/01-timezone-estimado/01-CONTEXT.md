# Phase 1: Timezone estimado - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Fotos ganham `tz_estimado` — um fuso IANA estimado a partir do país já
atribuído à foto, por qualquer origem que o motor de classificação já
resolve (GPS próprio, herança temporal de D-025, ou nome de pasta). Fecha
o modelo de dois instantes de D-038: `tz_estimado IS NOT NULL` passa a ser
o sinal de "fuso conhecido" do catálogo, em vez da diferença entre
`data_capturada` e `data_capturada_utc` (que fica indistinguível de
"desconhecido" quando o fuso real é +00:00).

`tz_estimado` é dado técnico auxiliar gravado direto em `MediaFile`, no
mesmo padrão não revisado de `gps_lat_estimado`/`gps_lon_estimado` — não
passa por `Evidence`/`Suggestion`/revisão humana, não entra em
`docs/CONFIANCA.md`.

</domain>

<decisions>
## Implementation Decisions

### Fonte de verdade e precedência de spec
- **D-01 [informational]:** `docs/prompts/fase-11-timezone-estimado.md` é o spec
  autoritativo desta fase — mais detalhado e mais recente que o texto
  minerado em `docs/ROADMAP.md`/`AVALIACAO_UX.md` durante o ingest. Onde os
  dois divergem, `fase-11-timezone-estimado.md` vence. Decisão do dono,
  2026-08-16, após o ingest ter perdido esse doc por estar em
  `docs/prompts/` (fora do escopo de raiz do ingest).
- **D-02 [informational]:** `ROADMAP.md` e `REQUIREMENTS.md` (fase 1 / TZ-01) já foram
  corrigidos nesta sessão pra refletir esta decisão — Success Criteria e
  descrição do requisito reescritos, ver diff desses arquivos.

### Modelo de dado — sem Evidence, sem revisão
- **D-03:** `tz_estimado` é gravado direto em `MediaFile` dentro de
  `_persistir_sugestao` (`engine.py`), lendo `evidencias["pais"].valor`
  quando existir. **Não** cria `Evidence` nova, **não** aparece com
  confiança/justificativa no Inspetor, **não** entra em
  `docs/CONFIANCA.md`. Mesmo padrão de `gps_lat_estimado`/
  `gps_lon_estimado`/`media.location_id` — precedente já existe em
  `engine.py:282-305` e `:701,720`.
- **D-04:** Sem país conhecido (ou país fora da tabela — não deveria
  acontecer, mas por segurança), `tz_estimado` fica `None`. Nunca inventa,
  nunca lança erro — mesma filosofia de "erro de leitura não derruba o
  resto" do projeto.

### Tabela país → fuso
- **D-05:** Tabela estática nova, `fotoorganizer/geolocation/timezones.py`
  (mesmo espírito de `paises.py`), `TZ_POR_PAIS: dict[str, str]` — chave é
  o nome em português que `PAISES_PT` produz (não código ISO, pra não
  precisar recodificar o valor de `Evidence.valor`). Cobre os 98 países de
  `PAISES_PT` por completo (parcial deixaria país sem fuso por acidente de
  cobertura, não por decisão).
- **D-06:** Todo valor é identificador IANA válido, validado em teste
  contra `zoneinfo.available_timezones()` (stdlib, sem dependência nova,
  sem rede) — rede de segurança contra erro de digitação.
- **D-07:** Sem dependência nova (`timezonefinder`/`pytz`/`geo-tz`
  explicitamente descartados). Confirmado pela pesquisa em
  `docs/referencia-immich/02-metadados-e-midia.md` §3: o equivalente do
  Immich (`geo-tz`, resolve por coordenada geométrica) é exatamente a
  precisão que esta fase abre mão de propósito, em troca de zero
  dependência nova — coerente com invariante 4 (nada sai da máquina) e com
  o nível de granularidade grosseira que o resto do app já assume pra país
  estimado.
- **D-08:** País com mais de um fuso oficial (Brasil, EUA, Rússia, Canadá,
  Austrália...) resolve para o fuso da capital ou de maior população —
  aproximação deliberada. Documentar a regra usada uma vez, em comentário
  no topo de `timezones.py`; não precisa resolver caso a caso no código.
  Preenchimento da tabela (todos os 98 países) fica a critério do
  planner/executor — sem revisão linha a linha pelo dono antes de ir pra
  produção (decisão explícita: confiar no critério documentado em vez de
  aprovar cada entrada).

### Escopo — o que NÃO faz nesta fase
- **D-09:** Não converte `data_capturada`/`data_capturada_utc` para hora
  local em nenhuma tela. Esta fase só produz o dado; consumo (mostrar hora
  local em vez de naive) é decisão de UI separada, não pedida aqui.
- **D-10 [deferred]:** Não lê `OffsetTimeOriginal`/o `Z` do QuickTime nos extratores
  (`exiftool.py`/`purepython.py` já detectam e descartam esse dado hoje —
  `MediaMetadata.data_capturada_utc` já existe esperando, em `None`).
  Explicitamente adiado para fase futura que já vai mexer em fuso de novo.
- **D-11 [deferred]:** Não corrige `sources/google_takeout.py:_data()` (monta hora
  local no fuso da máquina que importou, não da foto). Mesmo motivo do
  item acima — adiado.
- **D-12 [deferred]:** Nenhuma geometria coordenada→fuso (tipo `timezonefinder`).

### Medição do "Aceite" contra catálogo zerado
- **D-13 [deferred]:** `catalog.db` de produção foi zerado em 2026-08-16 (backup em
  `catalog-antes-do-reset-20260816-013503.db`); a nova varredura completa
  ainda não rodou. O critério de pronto (Aceite) do `fase-11` pede medir
  contra o catálogo real quantas fotos ganhariam `tz_estimado` (~2.235
  citado no ROADMAP). **Essa medição não bloqueia esta fase** — a fase
  entra código-completa (implementação + testes com fixtures sintéticas +
  `pytest` verde) agora; a medição contra o acervo real roda depois, fora
  do critério de pronto formal desta fase, assim que o catálogo for
  repovoado.

### Claude's Discretion
- Ordem exata de implementação das 4 partes do fase-11 (tabela, cálculo/
  persistência, serialização API, testes) — o planner decide o
  sequenciamento/waves.
- Nome exato de variáveis/funções auxiliares dentro de `timezones.py`,
  desde que a interface pública seja `TZ_POR_PAIS: dict[str, str]`.
- Preenchimento linha a linha dos 98 países da tabela — critério
  documentado (capital/maior população), sem revisão humana entrada por
  entrada (ver D-08).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec desta fase (autoritativo)
- `docs/prompts/fase-11-timezone-estimado.md` — spec detalhado e
  autoritativo desta fase (D-01). Cobre tabela país→fuso, cálculo,
  persistência, serialização de API, testes e critério de aceite.

### Modelo de dois instantes e evidências
- `docs/DECISOES.md` D-038 ("Uma foto tem dois instantes, e o offset não é
  coluna") — por que `data_capturada`/`data_capturada_utc` existem, por
  que offset nunca vira coluna, e por que `tz_estimado IS NOT NULL` é o
  sinal de "fuso conhecido".
- `docs/DECISOES.md` D-025 ("A janela da herança depende do que se
  herda") — janela de 12h para herança de país, base da cascata que
  `_evidencias_geo` já implementa.
- `docs/CONFIANCA.md` — modelo de confiança geral do projeto (elo mais
  fraco). `tz_estimado` **não** participa deste modelo (D-03) — citado
  aqui só para o executor entender por que este campo é a exceção, não a
  regra.
- `fotoorganizer/models/inference.py` — schema de `Evidence`/`Suggestion`
  (para entender o que `tz_estimado` explicitamente NÃO usa).

### Código existente a reaproveitar
- `fotoorganizer/classification/engine.py:693-781` (`_evidencias_geo`) —
  já monta `Evidence(campo="pais", ...)` com três origens (GPS próprio,
  herança temporal, pasta), convergindo pro vocabulário de
  `PAISES_PT`.
- `fotoorganizer/classification/engine.py:930-950` (dentro de
  `_persistir_sugestao`) — ponto de gravação: `evidencias["pais"]` já
  resolvido, mais barato que geocodificar de novo.
- `fotoorganizer/classification/engine.py:282-305` (`_persistir_herancas`)
  — precedente de escrita direta em `MediaFile` sem Evidence/Suggestion
  (mesmo padrão que `tz_estimado` segue).
- `fotoorganizer/geolocation/paises.py` — tabela `PAISES_PT` (ISO
  alfa-2 → nome PT-BR, 98 países), modelo pro novo `timezones.py`.
- `fotoorganizer/models/catalog.py:143` — coluna `tz_estimado` já existe
  (migrada desde `0001_schema_inicial.py:145`), terreno virgem (confirmado
  por `grep -rn "tz_estimado" fotoorganizer/ webapp/ tests/`).
- `fotoorganizer/metadata/base.py:56-63` — comentário explícito
  confirmando que `OffsetTimeOriginal`/QuickTime `Z` são descartados hoje
  e ficam esperando esta fase (mas fora de escopo aqui — ver D-10).

### Pesquisa de referência (Immich/PhotoPrism) — validação, sem mudança de plano
- `docs/referencia-immich/03-modelo-de-dados.md` §3, item 2 — o modelo de
  três representações de tempo (offset derivado, nunca coluna) do Immich é
  o mesmo padrão que D-038 já adotou; validação cruzada, não nova decisão.
- `docs/referencia-immich/02-metadados-e-midia.md` §3 (dependências
  externas, linha `geo-tz`) — por que este projeto conscientemente NÃO usa
  resolução geométrica de fuso (D-07/D-12).
- `docs/referencia-photoprism/02-metadados-imagem-e-visao.md` §3
  (`internal/meta/resolver.go:41-48`) — checagem de plausibilidade de
  offset (limite de 27h) do PhotoPrism. **Não aplicável a esta fase**
  (não computamos offset aqui) — relevante só quando a fase futura de
  `OffsetTimeOriginal` (D-10) for planejada. Registrado aqui pra não se
  perder.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fotoorganizer/geolocation/paises.py` (`PAISES_PT`): modelo direto para
  a nova tabela `TZ_POR_PAIS` — mesma forma (dict estático, docstring
  explicando o porquê, sem rede), mesma chave (nome PT-BR).
- `_persistir_herancas`/`_persistir_sugestao` em `engine.py`: ponto de
  gravação e precedente de escrita direta sem revisão já estabelecidos —
  não é preciso inventar um novo mecanismo de persistência.

### Established Patterns
- Escrita direta vs. Evidence→Suggestion: o motor já tem os dois caminhos
  coexistindo (`gps_*_estimado`/`location_id` direto; sugestões de destino
  via Evidence). `tz_estimado` segue o caminho direto — precedente, não
  exceção nova.
- "Nunca inventa, nunca lança erro": erro de leitura/país desconhecido
  sempre vira `None`/log, nunca derruba `gerar()` — consistente com o
  tratamento de erro do resto do scanner/motor.

### Integration Points
- `GET /api/midia/{id}` — mesmo serializador que já monta
  `gps_lat_efetivo`/`local` no JSON de `MediaFile`; `tz_estimado` entra ao
  lado.
- `gerar()` do motor de sugestões — `tz_estimado` recalculado a cada
  rodada, mesmo padrão de recálculo de `gps_*_estimado`.

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência visual/exemplo específico — esta fase não tem
superfície de UI nova (campo é dado técnico auxiliar, não exibido com
evidência/confiança).

</specifics>

<deferred>
## Deferred Ideas

- **Determinismo da classificação de viagem/evento/não-fotos/vídeo usar
  LLM quando regra determinística não alcança** — ponto levantado pelo
  dono durante esta discussão. Fora do escopo de Timezone estimado (mexe
  em `classification/engine.py`/`grouping/`, não em `tz_estimado`).
  Candidato a fase própria ou revisão de arquitetura da classificação;
  trazer ao dono como item de backlog separado antes de agendar.
- **Ler `OffsetTimeOriginal`/`Z` do QuickTime nos extratores** (D-10) —
  já adiado pelo próprio `fase-11-timezone-estimado.md`, não por esta
  discussão. Quando essa fase futura for planejada, revisitar a checagem
  de plausibilidade de 27h do PhotoPrism (`resolver.go:41-48`, ver
  canonical_refs).
- **Corrigir `sources/google_takeout.py:_data()`** (D-11) — mesmo caso do
  item acima, agrupado no mesmo adiamento do `fase-11-timezone-estimado.md`.
- **Converter `data_capturada` pra hora local exibida em alguma tela
  usando `tz_estimado`** (D-09) — decisão de UI separada, não pedida nesta
  fase.

</deferred>

---

*Phase: 01-timezone-estimado*
*Context gathered: 2026-08-16*
