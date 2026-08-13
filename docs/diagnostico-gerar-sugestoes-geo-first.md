# Diagnóstico — "Gerar sugestões" vs. objetivo geo-first

Investigação solicitada pelo dono em 2026-08-13, registrada como D-051 em
`docs/DECISOES.md`. Escopo: somente leitura (`git log`, `docs/**`,
`fotoorganizer/**`, `webapp/src/**`) — nenhuma linha de código de produção
foi alterada. A fronteira da fase 5 (`docs/prompts/00-protocolo.md:80-88`)
segue fechada; este documento é plano, não execução.

## Achado principal

A funcionalidade **existe e roda ponta a ponta** — não há lacuna de "botão
sem endpoint". O que diverge do objetivo relatado é a **ordem** em que o
motor decide: hoje a correlação temporal e o agrupamento em sessão rodam
**antes** de qualquer geocodificação, e a geocodificação é lazy, por
sessão. O objetivo descrito pelo dono (regras 1-2 abaixo) pede o oposto:
mapear geograficamente tudo primeiro, correlacionar por tempo depois. Essa
ordem atual não é acidente — está calibrada contra um benchmark de 17
cenários (`docs/AGRUPAMENTO.md`, `scripts/avaliar_agrupamento.py`) e
reordenar é inversão de arquitetura, não ajuste pontual.

Um gap separado e real, mas barato: XMP/IPTC são extraídos e persistidos,
mas não entram na cascata de evidências (regra 4, parcial).

**Revisão (D-052):** a geocodificação e a herança de GPS já são funções
puras, sem dependência de sessão/categoria — dá para movê-las para a
carga (import/scan) em vez de esperar a geração de sugestão, sem tocar na
cascata de categoria calibrada. Isso é mais barato e menos arriscado do
que reordenar `SuggestionEngine.gerar()` como a primeira versão deste
documento propunha — ver Fase B' abaixo.

## Cadeia atual (botão → execução)

1. UI: `webapp/src/components/StatusBar.tsx:131-138` → `job.gerarSugestoes()`
2. Hook: `webapp/src/hooks/useJob.ts:140` → `POST /api/sugestoes/gerar`
3. API: `fotoorganizer/server/app.py:1075-1079` → `jobs.iniciar_sugestoes()`
4. Job: `fotoorganizer/server/jobs.py:104-107` → `_rodar_sugestoes`
   (`jobs.py:182-216`), instancia `SuggestionEngine` com
   `LocationResolver(OfflineGeocoder())` e `ClaudeAdvisor` opcional
   (`jobs.py:201-207`, `jobs.py:280-289`)
5. Motor: `fotoorganizer/classification/engine.py`, `SuggestionEngine.gerar()`
   (linhas 243-291)
6. Resultado: linhas `Suggestion` (status `PENDENTE`) + `Evidence` —
   nenhum arquivo é tocado. Execução física é ação separada, atrás de
   aprovação e dry-run (`fotoorganizer/operations/planner.py`,
   `executor.py`).

Dentro de `gerar()`, a ordem real é:

```
253  self._correlacionar(midias)        # correlação temporal entre fontes
                                          # (herança de GPS por Δt, ANTES de geo)
365  agrupar_viagens(itens)              # sessão por gap de 3 dias — temporal puro
385  self._classificar(...)              # geocodificação acontece AQUI, lazy,
                                          # por sessão, dentro de _geo_da_sessao
                                          # (engine.py:518-558)
```

## Veredito por regra

| # | Regra | Veredito | Onde |
|---|---|---|---|
| 1 | Mapear TODAS as fotos com GPS próprio antes de qualquer outra etapa | **Não implementado** | geocodificação é lazy por sessão (`engine.py:518-558`), nunca uma passada global prévia |
| 2 | Nunca correlacionar por tempo antes de concluir o mapeamento geo | **Não implementado** — violação direta | `_correlacionar` (`engine.py:253`) e `agrupar_viagens` (`engine.py:365`) rodam antes de qualquer geocodificação |
| 3 | Depois do geo, correlacionar por tempo as fotos sem localização própria | **Parcial** — mecanismo correto (`herdar_gps`, `grouping/correlacao.py:197-267`, com decaimento de confiança por Δt, D-025/D-032), ordem errada (roda antes, não depois) | |
| 4 | Usar todas as fontes de metadado: EXIF, XMP, IPTC, MakerNote, RAW | **Parcial** — extraídas: EXIF, XMP (`metadata/purepython.py:155-169`), IPTC (`:172-195`), RAW (via rawpy). Não usadas na classificação: XMP/IPTC (extraídas, persistidas, nunca lidas em `classification/`/`grouping/`). MakerNote fora por decisão deliberada (D-027) — confirmado por pesquisa externa que GPS raramente vive só ali | `metadata/purepython.py:63-67` (`_TAGS_OPACAS`) |
| 5 | Nome de arquivo/pasta como sinal auxiliar, nunca primário | **Satisfeito** para localização — cascata em `_evidencias_geo` (`engine.py:736-824`) só usa pasta depois de GPS próprio e GPS herdado falharem. Ressalva: para categoria (Viagens/Família/Eventos), pasta é consultada primeiro (`engine.py:829-835`) — decisão deliberada e calibrada (D-034, 17/17 cenários), não bug | |
| 6 | Nunca mover/renomear automaticamente | **Satisfeito** — `gerar()` só grava `Suggestion(status=PENDENTE)`; execução física é ação humana separada, sempre cópia, nunca mover (`operations/executor.py:8-12`) | |
| 7 | Sugestão expõe dados usados + confiança | **Satisfeito** — modelo de evidências exato de `docs/CONFIANCA.md`: `Evidence` (origem, campo, valor, score, justificativa, versão), agregação por elo mais fraco (`classification/confidence.py:67-72`), nunca soma | |

## Correção de uma premissa herdada

O handoff que abriu esta sessão registrava: *"Decisão 3 (inventário por
pasta): travada até resolver a sobreposição de desenho com o Item B
(protecao-julgamento)."*

Releitura completa do README do Item B e de todo `docs/DECISOES.md`,
`docs/PLANO_IA_E_PRODUTO.md`, `docs/ROADMAP.md` **não encontrou nenhuma
sobreposição**. O Item B cobre exclusivamente export legível de
Evidence/Suggestion, backup do catálogo e checagem de esquema no boot —
nunca toca correlação temporal, herança de GPS ou agrupamento de evento.
A única menção real a "inventário por pasta" no corpus é a decisão 3 do
gate em `docs/PLANO_IA_E_PRODUTO.md` §8, e ela trata de **timing de
lançamento** (antes ou depois de outras entregas), não de conflito
técnico com o Item B.

Tratando essa premissa como não confirmada pelos documentos. Se a trava
veio de uma conversa não capturada em `docs/DECISOES.md`, precisa virar
decisão própria antes de valer — do jeito que está, nada nos documentos
impede a decisão 3 de seguir independente do Item B.

## Boas práticas de DAM pesquisadas (aplicáveis)

- **Raio/janela para herdar GPS**: PhotoPrism usa janela fixa (~±12h) e já
  documentou contaminação entre eventos diferentes no mesmo dia. O projeto
  já faz melhor — janela por campo (D-025) e raio medido, não suposto
  (D-032) — mas o boundary de sessão deveria ser respeitado como limite
  duro da herança, não só a distância em horas.
- **Timezone entre câmeras**: nenhuma ferramenta madura resolve 100%
  automático (Lightroom pede confirmação manual do offset). Confirma que
  o item `timezone-por-pais` da lib preparatória é necessário mas não
  suficiente sozinho — o offset resolvido precisa virar evidência
  auditável com confiança reduzida quando duas câmeras do mesmo lote
  divergem, nunca assumido em silêncio.
- **Confiança na UI**: a literatura recomenda contra score numérico
  "preciso" (falso rigor) e contra badge em toda sugestão (vira papel de
  parede). Valida a decisão já tomada (D-017): enum alta/média/baixa, não
  percentual.
- **Nunca mover automaticamente**: nenhuma ferramenta pesquisada
  (PhotoPrism, Immich, Google Fotos, Apple Fotos) move/renomeia arquivo
  com base em inferência — a invariante do projeto está acima do padrão
  de mercado, vale manter como diferencial documentado.
- **MakerNote/nome de pasta**: GPS raramente vive só em MakerNote (confirma
  D-027). Nome de pasta como sinal terciário é prática validada
  (PhotoPrism), mas casado contra dicionário geográfico — não regex livre.

## Conflitos com decisões já travadas

- **D-049 (manter Opus 5 no advisor)**: sem conflito estrutural — o
  advisor só é chamado no resíduo "neutro" da cascata determinística
  (`engine.py:389-390`, `_consultar_advisor`), nunca decide geo/tempo
  diretamente. Efeito indireto a monitorar: se a Fase C abaixo (reordenar
  geo/tempo) mudar quantas sessões caem em "neutra", muda a proporção
  medida em D-047 (39,10%) que sustentou a decisão de manter Opus 5 —
  não invalida D-049, mas pede remedição se a arquitetura mudar.
- **Item B (protecao-julgamento)**: sem sobreposição encontrada (ver seção
  acima) — premissa herdada corrigida, não confirmada.
- **D-034 (álbum nomeia onde pasta não nomeia, calibrado em 17/17
  cenários)**: qualquer reordenação geo-first precisa preservar essa
  regra de desempate ou refazer o benchmark que a valida.

## Categorias — limite estrutural em 3 valores (D-053)

O produto hoje só reconhece 3 categorias organizacionais — Viagens,
Família, Eventos — travadas em dois lugares independentes:
`_CATEGORIAS_PASTA` na cascata (`engine.py:91-93`) e o `enum` do schema
JSON do advisor (`advisor.py:72`). O segundo é o mais rígido: mesmo que o
LLM "quisesse" propor outra categoria, o `output_config` estruturado
bloqueia — não é limitação de prompt, é limitação de schema.

Pesquisa em Google Fotos, Apple Fotos, PhotoPrism, Immich e Lightroom
mostra que a expansão relevante não é "mais uma opção no mesmo campo" —
é um eixo diferente: **tipo/proveniência de mídia** (Capturas de Tela,
WhatsApp/Mensageria, Fotos ao Vivo, Panorama), todos detectáveis só por
metadado (resolução, EXIF, XMP `GPano`/`ContentIdentifier`, padrão de
nome `IMG-YYYYMMDD-WAxxxx`), sem visão computacional. "Por que essa sessão
existe" (Viagem/Evento/Família) e "que tipo de arquivo é este"
(Screenshot/Panorama/RAW) não competem pelo mesmo valor — uma foto pode
ser as duas coisas ao mesmo tempo. Documentos/Recibos e Selfies por
metadado ficam de fora: sinal ruidoso (a comunidade do Immich já reportou
falso positivo tentando isso) e a versão confiável depende de visão
(OCR/rosto), fora de escopo pelo mesmo motivo de D-035.

**Atualização (D-054): hipótese medida e refutada.** `scripts/medir_categorias_ausentes.py`
rodou a passada completa sobre as 104 sessões neutra reais — **0 sessões,
0% das 41.901 fotos**, têm qualquer traço de padrão de nome WhatsApp ou
de captura de tela, mesmo no limiar mais frouxo. Checagem direta no
catálogo confirma que o conteúdo genuinamente não existe em volume neste
acervo (187 PNG em 96.692 registros, 1 nome tipo WhatsApp, 2 nomes de
screenshot) — não é sinal de metadado perdido na importação. Os 39,10%
de "neutra" continuam sem explicação alternativa medida; a leitura
original de D-047 (residual genuíno da cascata, não resíduo pequeno)
segue de pé. **Não implementar o facet `tipo_midia` com essa
justificativa** — ver Fase E abaixo, mantida no documento como registro
do que foi medido e por quê a resposta é não.

## Plano faseado — nenhuma fase escreve em `fotoorganizer/**`/`webapp/src/**` sem aprovação explícita do dono

**Fase A — alimentar XMP/IPTC na cascata de evidências (regra 4)**
Baixo risco: não muda a ordem geo/tempo, só adiciona um sinal que já é
extraído e persistido, mas ignorado. Verificação: teste novo em
`tests/test_classification*.py` cobrindo um caso onde XMP/IPTC decide um
campo que EXIF sozinho não decidiria; captura de tela do Inspector
(`webapp/src/components/Inspector.tsx:107`) mostrando a evidência nova.

**Fase B' — mover a geo-resolução para a carga, não para a geração de
sugestão (revisado em D-052, substitui a Fase B/C originais)**
`LocationResolver.resolve` (`geolocation/resolver.py:36-66`) e
`estimar_offsets`/`herdar_gps` (`grouping/correlacao.py:63-194`) já são
funções puras — cache-keyed por coordenada, operam sobre a lista inteira
de fotos do catálogo, sem depender de sessão/grupo/classificação. Hoje só
rodam de dentro de `SuggestionEngine.gerar()` (`engine.py:253,741,763`)
porque ninguém as moveu, não por necessidade arquitetural. A cascata de
CATEGORIA (Viagens/Família/Eventos, `_categoria()`, D-034, calibrada em
17/17 cenários) consome local já resolvido (país/região/cidade), nunca
coordenada bruta — mover a geo-resolução para a carga não toca nela e
**não exige refazer o benchmark de categoria**. Isso substitui o plano
original de "medir antes de reordenar": a mudança é estrutural, não uma
inversão de cascata.
O que falta desenhar antes de codar (não é motivo para não migrar, é
o item de projeto que falta): invalidação. Hoje a herança é recalculada do
zero a cada `gerar()`; persistida na carga, precisa de uma forma de
re-rodar quando (a) uma foto nova chega depois e é doadora melhor (Δt
menor) para uma foto já processada, e (b) uma constante calibrada muda
(D-025/D-032) — versionar por `versao_logica`, como já feito em `Evidence`.
Verificação: novo teste cobrindo scan incremental que traz doador melhor
depois; teste de invalidação por `versao_logica`; medição no catálogo real
mostrando que `SuggestionEngine.gerar()` lê `location_id`/heranças
pré-persistidos sem recalcular.

### Fase B' — desenho técnico (sem código)

**Onde entra no pipeline**: não dentro do `scanner/` (que precisa continuar
rápido e somente leitura, invariante 1) — como um job novo, próprio,
disparado depois do scan completar (mesmo padrão de job em background já
existente em `fotoorganizer/server/jobs.py`), não por arquivo individual.
Rodar por arquivo a cada evento de scan incremental sairia mais caro do
que rodar a geração de sugestão sob demanda como hoje — `estimar_offsets`/
`herdar_gps` operam sobre o catálogo inteiro a cada chamada (é assim que
uma foto nova vira doadora melhor para uma foto antiga, ver abaixo), então
acoplar isso a CADA scan incremental multiplicaria o custo sem
necessidade. Proposta: job "resolver geo" que o usuário dispara (ou que
roda uma vez ao fim de um scan grande), não por arquivo.

**O que persiste**: nada de tabela nova — o job grava exatamente as mesmas
linhas de `Evidence` (origem `geocoding_offline`/`vizinhanca_temporal`,
mesmos campos `pais`/`regiao`/`cidade`, mesma justificativa) que
`_evidencias_geo` já produz hoje, só que mais cedo no pipeline. `gerar()`
passa a LER essa evidência existente em vez de chamar `_evidencias_geo`
do zero a cada geração — o método encolhe para cascata de categoria +
fallback para o que ainda não foi resolvido (foto processada entre o job
de geo e a geração de sugestão).

**Invalidação**: como o job recalcula sobre o catálogo inteiro a cada
execução (mesmo custo do `gerar()` de hoje, só que dissociado do clique
do usuário), o problema de "foto nova é doadora melhor para foto antiga"
se resolve sozinho a cada rodada do job — não precisa de lógica de
invalidação incremental nova. O único gatilho de invalidação real é
mudança de constante calibrada (D-025/D-032) ou de `versao_logica` —
mesmo mecanismo que já existe para `Evidence`, reaproveitado sem
desenhar nada novo.

**Fase E — medir se um facet de tipo de mídia reduz a fração "neutra"
(D-053) — CONCLUÍDA, resultado negativo (D-054)**
`scripts/medir_categorias_ausentes.py` mediu, entre as 104 sessões neutra
reais, a fração com maioria de arquivos em padrão de nome WhatsApp ou de
captura de tela. Resultado: **0%** — nem uma sessão, nem parcialmente.
Checagem direta no catálogo (fora da amostra) confirma que o conteúdo
não existe em volume neste acervo. **Não implementar** o facet
`tipo_midia` com a justificativa de reduzir "neutra" — a medição não
sustenta. Se o facet tiver valor por outro motivo (navegação/filtro por
tipo de mídia), é decisão de produto separada, sem essa medição a favor.

**Fase D — esclarecer a decisão 3 do gate — CONCLUÍDA (D-055)**
O dono confirmou diretamente: a trava do Item B não tinha origem real
fora dos documentos. A decisão 3 do gate (timing do "inventário por
pasta", `PLANO_IA_E_PRODUTO.md` §8) segue independente do Item B — a
trava artificial foi removida; a decisão em si (antes ou depois do
lançamento) ainda é do dono, sem prazo.

## Parar aqui

Nenhuma linha de `fotoorganizer/**`, `webapp/src/**`, migração Alembic ou
`pyproject.toml` foi ou deve ser alterada a partir deste documento sem
aprovação explícita do dono. A Fase A é a de menor risco e mais barata de
aprovar isoladamente, se o dono quiser destravar algo antes do gate da
fase 5 completo — mas continua sendo decisão dele, não default.
