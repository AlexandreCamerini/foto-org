# Inventário funcional do APP_ORIGEM — o que trazer para o Foto Organizer

Levantado em 2026-08-10 sobre `~/dev/fot` (**Immich v3.1.0**, commit `5ad1e4e0f`).
Fontes: 57 serviços em `server/src/services/`, 55 rotas em `web/src/routes/`,
21 documentos em `docs/docs/features/`, e os cinco mapas já existentes em
`docs/referencia-immich/` (mesmo commit, levantados em 2026-08-08).

Cada linha marca `[mapeado]` quando o mecanismo já está descrito nos mapas de
referência do repositório, e `[novo]` quando é leitura desta sessão.

**Nada foi portado.** Esta é a lista de onde você escolhe.

## O critério de ordenação

Você pediu para **preservar, adaptar e melhorar** as funcionalidades do
destino, com prioridade para (a) **localização compartilhada** — a herança de
GPS entre fotos de origens diferentes — e (b) **organização por análise de toda
informação disponível**. A lista está ordenada por quanto cada item reforça
essas duas capacidades, não por quanto o Immich as valoriza.

Três coisas precisam ficar ditas antes da tabela:

**1. A capacidade (a) não existe no Immich.** Verifiquei: `metadata.service.ts`
e `map.service.ts` não têm nenhuma inferência de coordenada — nada de vizinho,
interpolação, empréstimo ou estimativa. O Immich só faz reverse geocoding de
GPS que **já está no arquivo**. `map.service.ts` tem 27 linhas e é um passa-
adiante de marcadores.

O motor de correlação do destino (`fotoorganizer/grouping/correlacao.py`, 377
linhas) — janelas por granularidade, estimativa de offset de relógio entre
câmeras, raio de incerteza calibrado contra 2.083 pares reais, frase de
justificativa gerada em Python — **não tem equivalente no origem e não é
substituível por nada desta lista**. Todo item abaixo que toca em geo é
*insumo* para ele: melhora a qualidade das doadoras, do Δt e do nome do lugar.
Nenhum o substitui.

**2. A capacidade (b) existe no Immich em forma mais pobre.** O `evidence` do
destino (origem, campo, valor, confiança, justificativa, versão da lógica) é
mais rico que o `lockedProperties` do Immich (um array de nomes de coluna, sem
quem/quando/valor anterior) — isso já estava registrado em
`docs/referencia-immich/README.md`. Mas o Immich **lê muito mais sinal do
arquivo** do que o destino: 11 tags de data em ordem de precedência, sidecar
XMP com merge, keywords hierárquicas de três namespaces, timezone declarado.
O `docs/INVENTARIO_DE_SINAIS.md` já mede esse buraco do lado de cá: XMP
sidecar ❌, XMP embutido ❌, IPTC ❌, e 8 chaves EXIF "capturadas e ociosas".

É exatamente aí que o origem tem o que o destino quer: **não o motor de
decisão, mas a matéria-prima que alimenta o motor.**

**3. Licença.** AGPLv3. Tudo aqui é reimplementação a partir de descrição de
mecanismo. Nenhuma linha de código do Immich entra no Foto Organizer.

---

## Faixa A — reforça diretamente as duas capacidades prioritárias

| # | Funcionalidade | O que faz | Arquivos/módulos (origem) | Dep. externas | Porte | Estratégia | Acoplamento | Recomendação |
|---|---|---|---|---|---|---|---|---|
| A1 | **Precedência de tags de data** `[mapeado]` | Percorre 11 tags de data em ordem fixa (`SubSecDateTimeOriginal`, `DateTimeOriginal`, `CreationDate`, `GPSDateTime`, `SonyDateTime2`, `SourceImageCreateTime`…), com fallback para o menor entre `fileCreatedAt`/`mtime`/`birthtime` | `services/metadata.service.ts:46-59, 988, 1033` | exiftool | **baixa** | adaptar | **nulo** — é uma lista ordenada | **Trazer primeiro.** Data melhor = Δt melhor = doadora melhor. Ataca (a) e (b) juntas |
| A2 | **Timezone declarado no arquivo** `[novo]` | Usa `tags.zone`/`OffsetTimeOriginal`; se ausente e o bruto termina em `Z`/`+00:00`, força UTC+0 | `services/metadata.service.ts:1006-1010` | exiftool | **baixa** | adaptar | nulo | **Trazer.** `INVENTARIO_DE_SINAIS` já aponta 1.527 fotos com `OffsetTimeOriginal` capturado e **não usado**. Substitui inferência por fato declarado |
| A3 | **Leitura de XMP sidecar com merge** `[mapeado]` | Lê `.xmp` ao lado do original e funde: **sidecar vence**; se o sidecar tem data, apaga todas as datas do original e o `zone` junto | `services/metadata.service.ts:580-631, 591-608`; `docs/features/xmp-sidecars.md` | exiftool | **média** | adaptar | baixo | **Trazer.** 605 sidecars no acervo, **599 com curadoria humana**, hoje 100% ignorados. É o maior sinal ocioso medido |
| A4 | **Keywords hierárquicas de 3 namespaces** `[novo]` | Lê tags em precedência `digiKam:TagsList` → `lr:HierarchicalSubject` → `IPTC:Keywords`, com hierarquia `pai/filho` | `docs/features/xmp-sidecars.md`; `services/tag.service.ts` (164 ln) | exiftool | **média** | adaptar | baixo | **Trazer a leitura**, não a entidade `Tag` do Immich. Vira evidência de origem `curadoria`, alta confiança — é humano dizendo o que a foto é |
| A5 | **Reverse geocoding GeoNames** `[mapeado]` | Cidade + estado (admin1) + estado menor (admin2) + país, de base local carregada no banco | `services/metadata.service.ts:259-265`; `repositories/map.repository.ts`; `docs/features/reverse-geocoding.md` | GeoNames (dump local) | **média** | adaptar | médio (Postgres) | **Avaliar contra o que já existe.** `geolocation/offline.py` usa `reverse_geocoder`; GeoNames dá **hierarquia administrativa e nome oficial**, que é o que `classification/engine.py` precisa para nomear pasta. Ganho é de qualidade de nome, não de cobertura |
| A6 | **Modelo de tempo de dois instantes** `[mapeado]` | Guarda instante absoluto e instante local em colunas separadas, com a fonte do fuso registrada | `03-modelo-de-dados.md §3`; `services/metadata.service.ts:988` | — | **média** | adaptar | baixo | **Trazer** — já julgado "vale importar" no README de referência. Pré-requisito coerente de A2, e o que faz o agrupamento temporal parar de errar na virada de fuso |
| A7 | **Pareamento de Live Photo / motion photo** `[mapeado]` | Casa foto + vídeo pelo `livePhotoCID` e esconde o vídeo da grade; extrai o vídeo embutido de motion photo | `services/metadata.service.ts:177, 405, 681` | exiftool | **média** | adaptar | baixo | **Trazer.** Acervo de iPhone com Apple Fotos: o par duplica contagem e polui rajada. O vídeo carrega GPS quando a foto não carrega — **doadora nova para (a)** |
| A8 | **Merge de metadados ao resolver duplicata** `[novo]` | Quando exatamente 1 é mantido, funde do descartado: álbuns, favorito, maior nota, descrições concatenadas | `docs/features/duplicates-utility.md`; `services/duplicate.service.ts` (412 ln) | — | **baixa** | adaptar | baixo | **Trazer o princípio.** Casa exatamente com o invariante 8 ("nada que possa ser referência real é apagado"): o rebaixado a SINAL doa metadado antes de sair da grade |
| A9 | **Pré-seleção da principal em duplicata** `[novo]` | Sugere qual manter por (1) tamanho em bytes, (2) **contagem de campos EXIF** | `docs/features/duplicates-utility.md` | — | **baixa** | adaptar | nulo | **Trazer o critério 2.** "Mais metadado vence" é a regra certa num acervo onde o metadado é o ativo — e é barata |

## Faixa B — reforça o resto do destino

| # | Funcionalidade | O que faz | Arquivos/módulos (origem) | Dep. externas | Porte | Estratégia | Acoplamento | Recomendação |
|---|---|---|---|---|---|---|---|---|
| B1 | **Máquina de estados de alcance** `[mapeado]` | Estados explícitos online/offline por arquivo, com transição ao sumir e voltar o volume | `services/library.service.ts` (803 ln); `01-ingestao-e-storage.md §1.B` | — | **média** | adaptar | baixo | **Trazer** — já julgado "vale importar". `sources/disponibilidade.py` e `reapontar.py` cobrem parte; falta o estado explícito |
| B2 | **Estado do pipeline no catálogo** `[mapeado]` | `asset_job_status` grava o que já foi feito por asset, no banco — não na fila | `repositories/asset-job.repository.ts`; `03-modelo-de-dados.md` | — | **média** | adaptar | baixo | **Trazer** — já julgado "vale importar". Torna retomada de scan uma consulta, não um checkpoint |
| B3 | **Relatório de integridade** `[novo]` | Três varreduras: arquivo no disco sem registro, registro sem arquivo, checksum divergente — com relatório navegável | `services/integrity.service.ts` (723 ln); rota `admin/maintenance/integrity-report` | — | **média** | adaptar | médio | **Trazer.** É a rede de segurança do invariante 3, e o destino não tem equivalente |
| B4 | **Stacks (agrupar variantes)** `[novo]` | Agrupa RAW+JPEG, edições e derivados sob uma principal; a pilha ocupa um lugar na grade | `services/stack.service.ts` (88 ln); `repositories/stack.repository.ts` | — | **baixa** | adaptar | baixo | **Trazer.** Casa com rajada e com RAW+JPEG do acervo. Modelo simples, ganho de densidade alto |
| B5 | **Busca por metadados facetada** `[novo]` | Consulta por câmera, lente, cidade, país, data, tipo, tamanho — separada da busca semântica | `services/search.service.ts:65`; `repositories/search.repository.ts` | — | **média** | adaptar | médio | **Trazer.** É o modo de busca que funciona nos 95% sem pixel. Alimenta as facetas do Panorama |
| B6 | **Storage template por tokens** `[mapeado]` | Nomeia o destino por template com tokens de data, câmera, álbum, extensão, com migração incremental | `services/storage-template.service.ts` (431 ln) | handlebars | **média** | **adaptar com cuidado** | médio | **Comparar com `webapp/src/components/TemplateEditor.tsx` e `classification/templates.py`** antes de trazer. O vocabulário de tokens vale; o mecanismo **move arquivo** e isso viola o invariante 2 do destino, que copia |
| B7 | **Folder view** `[novo]` | Navegação por árvore de pastas real, além da linha do tempo | `services/view.service.ts` (16 ln); `repositories/view-repository.ts`; rota `(user)/folders` | — | **baixa** | adaptar | baixo | **Opcional.** A sidebar de fontes já cobre parte; a árvore de pastas é o que o dono reconhece do disco dele |
| B8 | **Timeline em duas chamadas (buckets)** `[mapeado]` | `/buckets` devolve contagem por período; `/bucket/:id` devolve o conteúdo — permite reservar altura antes de carregar | `services/timeline.service.ts` (89 ln); `05-ui-web.md §2.1` | — | **média** | adaptar | baixo | **Trazer se a grade crescer.** É o que elimina salto de layout. Hoje `useMidia.ts` carrega direto |
| B9 | **Virtualização em dois níveis** `[mapeado]` | Vira janela sobre grupos e janela sobre itens dentro do grupo | `05-ui-web.md §1.1-1.3` | — | **alta** | reescrever | médio (Svelte) | **Só se a grade sofrer.** `@tanstack/react-virtual` já resolve um nível |
| B10 | **Memórias ("neste dia")** `[novo]` | Job diário monta coleções por data de anos anteriores | `services/memory.service.ts` (172 ln) | — | **baixa** | adaptar | baixo | **Opcional.** Barato, e é o único item da lista que dá prazer em vez de dar ordem |

## Faixa C — descartar (com motivo)

| # | Funcionalidade | Por que não |
|---|---|---|
| C1 | **Duplicata por embedding CLIP** | Já julgado no README de referência: o phash resolve sem depender de pixel, e 95% do acervo não tem pixel. Trocar seria perder cobertura |
| C2 | **Busca semântica CLIP / OCR** | Alcança ~5% do acervo. Custo de modelo + embedding + índice vetorial não se paga nessa fração |
| C3 | **Reconhecimento facial (InsightFace + clusterização)** | Desativado por padrão no destino por invariante 6; alcança os mesmos 5%. O mecanismo de confirmação do Immich (§2.4 do mapa 04) vale reler **quando** M6 chegar |
| C4 | **Payload colunar da grade + thumbhash** | Já julgado: 95% dos registros não têm imagem para pré-visualizar |
| C5 | **Journal de move em duas fases** | Já julgado: o executor do destino copia, não move, e cria com `'xb'` |
| C6 | **Trash / soft delete / esvaziar lixeira** | **Viola o invariante 8.** O destino rebaixa a SINAL, não apaga. Não trazer nem como opção |
| C7 | **Edição destrutiva (crop/rotate/filtros)** | Fora do MVP e em rota de colisão com o invariante 1 |
| C8 | **Transcodificação de vídeo / HLS / casting** | Escopo de servidor de streaming. Nada a ver com catalogar |
| C9 | **Multiusuário, partner sharing, shared links, álbuns compartilhados, notificações, e-mail** | O destino é single-user local-first. Traz superfície de rede e privacidade sem contrapartida |
| C10 | **Workflows / plugin SDK (Extism/WASM)** | `services/workflow.service.ts` + `@immich/plugin-sdk`. Automação por gatilho é interessante, mas o destino tem 1 usuário e um invariante de "revisar antes de executar" que a automação existe para pular |
| C11 | **Postgres + Redis + BullMQ + OpenTelemetry** | SQLite é a fonte de verdade por decisão de stack. A fila do destino (`server/jobs.py`) atende |
| C12 | **App mobile Flutter** | Fora de escopo |

---

## Detalhamento dos quatro primeiros

### A1 + A2 — a data e o fuso

O destino hoje decide data por um caminho mais curto e depois **estima deriva de
relógio** entre câmeras em `correlacao.py:142` (`estimar_offsets`). Isso é
engenhoso e continua necessário — mas está compensando, por inferência
estatística, uma informação que **1.527 arquivos declaram explicitamente**
(`OffsetTimeOriginal`, medido em `docs/INVENTARIO_DE_SINAIS.md`).

Trazer A1+A2 tem efeito composto sobre a capacidade (a):

- Δt mais exato entre foto e doadora → raio de incerteza menor → círculo menor
  no mapa → afirmação mais forte com o mesmo rigor.
- `estimar_offsets` passa a ter âncoras de fuso conhecido para calibrar, em vez
  de inferir tudo.
- A multiplicação de confiança por `mtime` (o `0.6` comentado em
  `correlacao.py:44-47`) passa a valer para menos fotos, porque menos fotos
  caem no fallback de mtime.

Custo: baixo. É uma lista ordenada de chaves e um parser de offset. Nenhuma
dependência nova — `exiftool` já é a estratégia declarada do destino.

**Risco a declarar:** mudar a precedência de data **muda datas já gravadas no
catálogo**, e portanto muda agrupamento, viagens e sugestões já revisadas. Não
é uma migração silenciosa. Precisa de reprocessamento com evidência nova
(`origem: exif_precedencia_v2`) preservando a anterior, e de um número medido
de quantas fotos mudaram de data antes de virar padrão.

### A3 + A4 — os 599 sidecars

`docs/INVENTARIO_DE_SINAIS.md` mede: 605 arquivos `.xmp`, 599 com curadoria.
Hoje o catálogo não lê nenhum. É trabalho humano já feito, parado no disco.

O que o Immich faz e vale copiar como mecanismo:

1. Descobrir o sidecar por regra de nome (dois padrões: `foto.jpg.xmp` e
   `foto.xmp`).
2. Ler as tags do original e as do sidecar **separadamente**.
3. Fundir com o sidecar vencendo — e, crucialmente, **se o sidecar tem data,
   descartar todas as datas do original e o fuso junto**. Meia-mistura de
   data do arquivo com fuso do sidecar produz um instante que não existiu.
4. Ler keywords em precedência de três namespaces, preservando hierarquia.

No destino isso não vira campo sobrescrito: vira **linha de `evidence` com
origem `xmp_sidecar` e confiança alta**, porque é humano afirmando. É a forma
mais direta de aumentar a capacidade (b) sem inventar heurística nova — e o
motor de confiança já sabe o que fazer com uma evidência de origem forte.

**Risco a declarar:** os sidecars do acervo vieram de Lightroom (o destino tem
`sources/lightroom.py`). Se o Lightroom já foi importado como fonte, parte
dessa curadoria pode entrar **em duplicidade** por dois caminhos, com
confiança somada indevidamente. Medir a interseção antes, não depois.

### A5 — o nome do lugar

Aqui a recomendação é a mais fraca da Faixa A, e é honesto dizer por quê.

`geolocation/offline.py` (57 linhas) já resolve coordenada → lugar com
`reverse_geocoder`. O ganho do GeoNames não é cobertura, é **hierarquia
administrativa** (país → admin1 → admin2 → cidade) e nome oficial — que é o
que `classification/engine.py` consome para nomear pasta e o que `D-025`
precisa para dizer "cidade" e "país" com granularidades diferentes.

Se a nomeação atual já satisfaz, isto é otimização de qualidade de string, não
capacidade nova. **Medir antes**: quantas sugestões hoje param em "país" por
falta de admin1/cidade no dataset atual. Se for pouco, cai para Faixa B.

O Immich carrega o dump no Postgres a cada upgrade — esse mecanismo é
descartável. No destino seria uma tabela SQLite carregada uma vez.

---

## O que NÃO trazer porque substituiria capacidade do destino

Esta seção existe porque a instrução foi preservar e melhorar, não trocar.
Quatro tentações reais, todas plausíveis, todas erradas aqui:

1. **Trocar `evidence` por `lockedProperties`.** O modelo do Immich é mais
   simples e por isso mais tentador. Ele registra *que* um campo foi travado,
   não *por quê*, nem *com que confiança*, nem *qual era o valor antes*. O
   destino inteiro — badge de confiança, tela de Revisão, a pergunta "por quê?"
   — está construído sobre o que o Immich não guarda.

2. **Trocar o raio de incerteza por um ponto no mapa.** O Immich desenha ponto
   porque todo GPS dele é lido, nunca herdado. O destino herda em 4.944 fotos.
   Adotar a UI de mapa do Immich junto com o resto significaria desenhar como
   fato o que é estimativa — exatamente o que `docs/LOCAL_ESTIMADO.md` foi
   escrito para impedir.

3. **Trocar `papel: ACERVO/SINAL` por `visibility` + `isOffline`.** Já
   registrado no README de referência: `papel` resolve com mais precisão o que
   o Immich espalha entre dois campos. E `isOffline` do Immich convive com um
   caminho de deleção que o invariante 8 proíbe.

4. **Adotar o storage template como está (B6).** O vocabulário de tokens é bom
   e o `TemplateEditor.tsx` do destino pode crescer com ele. O *mecanismo* move
   arquivo e migra a biblioteca inteira quando o template muda. O destino copia,
   verifica hash e nunca sobrescreve. Trazer o token sem trazer o executor.

---

## Ordem sugerida, se você quiser uma

Se a escolha for pela leitura de valor/esforço acima e não por outra prioridade
sua:

1. **A1 + A2** juntos — data e fuso são um assunto só, e destravam o resto.
2. **A3 + A4** juntos — sidecar e keywords vêm pelo mesmo parser.
3. **A8 + A9** — baratos, e fecham o ciclo de duplicatas sem violar o
   invariante 8.
4. **A7** — Live Photo, que traz doadoras novas para a correlação.
5. **A6 + B2** — modelo de tempo e estado do pipeline, os dois de infraestrutura.
6. **B3** — integridade, quando o acervo já estiver mexido o bastante para
   precisar de rede.
7. **A5** — só depois de medir se o nome do lugar hoje é insuficiente.

Nada aqui está começado. Diga quais números você quer da lista e a Fase 3
monta o `plano-refactor.md` em cima da sua seleção mais a decisão de design
que ficou aberta na Fase 1.
