# Fase 14 — o que PhotoPrism e Immich têm que o mercado não tem

Síntese de julgamento, não de implementação. Cruza os três mapas do PhotoPrism
(`docs/referencia-photoprism/`, 2026-08-12) com os cinco do Immich
(`docs/referencia-immich/`, 2026-08-08) e responde a uma pergunta só: **o que
estas duas soluções fazem que Google Fotos, Apple Fotos, Lightroom e Mylio não
fazem, e que vale trazer para este acervo?**

Não é um plano de porte para o PhotoPrism. É o inverso: o PhotoPrism e o Immich
são a matéria-prima; o destino é o foto-organizer.

---

## 1. Requisitos — os dois filtros, nesta ordem

Um candidato só vira item se sobreviver aos dois. A ordem importa: o primeiro
filtro é barato de aplicar e corta a maior parte.

**Filtro 1 — diferenciador real vs. mercado.** Não basta "o Immich/PhotoPrism
faz X". Tem que ser "X não é o que um app de fotos decente já faz". Empilhar
RAW+JPEG, mostrar `<mixed>` num campo de edição em lote, navegar a grade pelo
teclado, carregar miniatura antes da imagem grande — tudo isso o Lightroom faz
há uma década. É table stakes do segmento profissional, não vantagem
competitiva. Descartado sem apelo.

**Filtro 2 — valor por unidade de custo para este acervo.** A mesma régua do
`ROADMAP.md` e da fase 12, calibrada pelos mesmos fatos medidos: pixel local
alcança ~5% dos ~99 mil registros conhecidos (D-028), GPS de qualquer fonte
existe em 4 dos 25 anos (D-029), single-user, sem servidor, sem segundo
dispositivo. Um mecanismo pode ser genuinamente diferenciador no mercado e
ainda assim não pagar aqui — quando for o caso, está dito na seção 7, não
escondido.

**Critério de aceite desta fase:** cada item tem âncora `arquivo:linha` no
mecanismo original (PhotoPrism ou Immich, nunca em código que não existe no
foto-organizer), esforço declarado, custo recorrente declarado, e a razão pela
qual sobreviveu aos dois filtros. Cada descarte tem o filtro que o matou.

**Restrição de licença.** PhotoPrism e Immich são AGPLv3. Tudo abaixo descreve
mecanismo para reimplementar; nada é código a copiar.

---

## 2. Estado atual — o que já foi fechado, com evidência

A fase 12 não é mais proposta: os três itens foram implementados e registrados.

| Item da fase 12 | Estado | Registro |
|---|---|---|
| A — reapontar fonte que mudou de lugar | implementado 2026-08-09 | D-036, `fotoorganizer/sources/reapontar.py` |
| B — terceiro estado de alcance + laço de reconciliação | implementado 2026-08-09 | D-037, `fotoorganizer/scanner/reconciliacao.py`, `scanner/elegibilidade.py` |
| C — modelo de tempo de dois instantes | implementado 2026-08-09 | D-038, migração `0014`, `data_capturada` + `data_capturada_utc` |

Isso muda o recorte desta fase de duas formas. Primeiro, o bloqueio que o
`ROADMAP.md` chamava de "o item que a lista ainda não tem" — reencontrar os
arquivos — deixou de ser hipótese: existe comando e tela. Segundo, itens que
antes seriam descartados por "só valem quando o disco montar" agora têm data
provável, e por isso entram (Item C abaixo), com a ressalva dita.

Quatro coisas do lado do foto-organizer que a leitura do PhotoPrism obrigou a
verificar no código antes de propor qualquer coisa:

**A regra de precedência do sidecar já está implementada, e é a boa.**
`fotoorganizer/metadata/exiftool.py:186-215` (`_fundir_sidecar`) faz exatamente
o que o Immich faz em `services/metadata.service.ts:591-608`: o `.xmp` vence o
arquivo, e se o sidecar declara **qualquer** data, todas as tags de data do
original saem junto — inclusive o fuso, para não casar a data do editor com o
offset da câmera. `_sidecar_de` (`:161-175`) reconhece as duas convenções
(`foto.jpg.xmp` do Adobe, `foto.xmp` do darktable), e as tags do sidecar entram
na base bruta com namespace próprio `xmp_sidecar` (`:62`, rótulo em
`server/app.py:207`). Nada a importar aqui — só falta o gatilho, que é o Item C.

**Os três tipos de integridade do Immich já existem, como script.**
`scripts/verificar_integridade.py:8-25` documenta e implementa exatamente
`checksum_mismatch`, `missing_file` e `untracked_file` do `integrity_report`
(`schema/tables/integrity-report.table.ts:9`, `enum.ts:404`), com amostragem por
padrão e `--tudo` para a varredura completa. Somente leitura.

**Não há mecanismo de backup no produto.** `sqlite3 .backup` aparece em quatro
lugares, todos ad-hoc e todos em scripts de manutenção:
`scripts/preparar_versao.sh:121-125`, `scripts/rebaixar_nao_acervo.py:88-90`,
`scripts/podar_metadados.py:55`, `scripts/medir_nome_de_album.py:105-110`. É
disciplina de quem escreveu o script, não garantia do app.

**O filtro da biblioteca não compõe e não sobrevive a um reload.** A API expõe
15 parâmetros fixos (`fotoorganizer/server/app.py:565-583`) mais um `lacuna`
que é **enum de escolha única** entre 12 predicados (`repositories/media.py:54`
para os rótulos, `:69-110` para os predicados, `:240-241` para a aplicação). No
webapp, o estado é `useState` no topo (`webapp/src/App.tsx:68-93`), com
`recorte` explicitamente comentado como "Um só" (`:83`); não há `searchParams`,
`pushState` nem `localStorage` em `webapp/src/` (grep, zero ocorrências). Ou
seja: "local estimado **e** sem câmera **e** antes de 2010" é inexprimível, e
qualquer recorte morre no F5.

E o achado que mais mexeu no desenho do Item A: **`versao_logica` é escrito e
nunca lido.** A coluna existe em `Evidence` e em `Suggestion`
(`fotoorganizer/models/inference.py:57,75`), é preenchida com
`VERSAO_LOGICA = "4.1"` (`classification/engine.py:75,970,1045`) e não aparece
em nenhuma consulta, filtro ou operação. A auditoria mais cara do projeto está
gravada e é inalcançável.

---

## 3. Item A — o filtro composto sobre proveniência, como texto reversível

**Por que sobrevive ao filtro 1, e não pela razão óbvia.** "Busca salvável" não
é diferencial: o Lightroom tem coleções inteligentes desde sempre, e a busca do
Google Fotos é melhor que qualquer DSL. O diferencial não é o *mecanismo*, é **o
que ele consegue perguntar**. Nenhum app de mercado registra de onde cada campo
veio, com que confiança e por qual raciocínio — então nenhum consegue responder
"me mostre o que foi inferido por vizinhança temporal, com confiança baixa, pela
lógica 3.9". Este projeto registra: `Evidence.origem`, `.nivel`, `.score`,
`.justificativa`, `.versao_logica` (`models/inference.py:39-58`). É o ativo
estrutural que a fase 12 já identificou como "onde este projeto está à frente" —
e que hoje o usuário não alcança.

**O mecanismo a trazer, e de quem.** Os dois resolvem "como o recorte vira
estado". O PhotoPrism resolve melhor e é dele que se copia:

- `internal/form/serialize.go:80-191` (`Unserialize`) — parser de campo único
  que reconhece `chave:valor`, aspas para escapar espaço, e trata qualquer token
  sem `:` como texto livre. Erro de campo desconhecido ou de tipo é **reportado,
  não silenciado**.
- `internal/form/serialize.go:16-77` (`Serialize`) — o inverso. É o round-trip
  simétrico que faz o recorte inteiro caber numa string reversível, e é o que
  torna a busca linkável/salvável de graça.
- `internal/form/search_photos.go:11-99` — cada campo do struct tem tag
  `form:"..."` que é literalmente o nome do token. A gramática não é mantida
  separada do modelo; ela **é** o modelo.
- `internal/form/search_photos.go:80` — um único campo de texto carrega
  expressão booleana: `|` é OU dentro do grupo, `&` é E entre grupos, `!` nega.

O Immich resolve o mesmo problema por parâmetros de query na URL
(`timeline-manager/types.ts:8`, `navigation.ts:7` com `?at=<assetId>`): o estado
sobrevive ao reload, mas não há gramática, não há texto livre e não há negação.
É a versão mais fraca do mesmo contrato. **Fica com o PhotoPrism.**

```
   digitação livre                        formulário/chips da UI
        │                                          │
        └──────────────┐              ┌────────────┘
                       ▼              ▼
                  ┌──────────────────────┐
                  │  objeto de recorte   │   ← única fonte de verdade
                  └──────────────────────┘
                       │              ▲
             Serialize │              │ Unserialize
                       ▼              │
              "confianca:baixa origem:vizinhanca antes:2010"
                       │
                       └──► URL, link salvo, sessão retomada, teste
```

**O vocabulário que só este projeto pode oferecer.** Os tokens de câmera, país,
cidade, palavra-chave e pasta já existem como parâmetros (`repositories/media.py`
`MediaFilters`) — trazê-los para a gramática é reempacotamento. Os que
justificam o item são os que saem de `evidence` e de colunas que o projeto
inventou:

| Token | De onde sai | Por que nenhum app de mercado tem |
|---|---|---|
| `confianca:baixa\|media\|alta` | `Evidence.nivel` | nenhum registra confiança por campo |
| `origem:exif\|pasta\|vizinhanca\|usuario\|geocoding` | `Evidence.origem` | nenhum distingue medido de inferido |
| `versao:4.1` / `versao:<4.1` | `Evidence.versao_logica` | ninguém versiona o raciocínio |
| `papel:acervo\|sinal` | `MediaRole` (`models/catalog.py:45`) | ninguém tem o terceiro estado (D-024) |
| `lugar:estimado` | `gps_lat_estimado` | ninguém separa coordenada lida de herdada |
| `alcance:ausente\|offline` | fase 12 item B (D-037) | ninguém modela "sumiu" ≠ "está na gaveta" |

`versao:` merece nota. Ele resolve sozinho o achado da seção 2 — a coluna
escrita e nunca lida — sem virar item próprio. Considerei propor "recomputar em
massa por origem e versão de lógica, preservando o manual" como Item D, à la
`asset_face.sourceType` do Immich (`asset-face.table.ts:75`, com
`metadata.service.ts:968` apagando e recriando só as faces de origem `exif`).
Não vale: o projeto já resolve a preservação do manual de forma melhor — a
decisão do usuário mora em coluna própria (`tipo_confirmado`, `gps_lat` vs
`gps_lat_estimado`) e a evidência é cache derivado, apagada e refeita inteira a
cada passada (`classification/engine.py:961`). O que falta não é a operação de
recomputar; é **enxergar** o que cada versão decidiu. Isso é um token, não uma
fatia. Registrado em D-043.

- *Muda o quê:* o recorte deixa de ser um estado de componente e vira um
  endereço. "As 4.944 fotos cujo lugar veio de herança (D-025) com confiança
  baixa e sem câmera identificada" passa a ser uma pergunta que o app responde,
  um link que o dono guarda e um caso de teste que o `scripts/avaliar_*.py`
  consegue reproduzir. Alcança 100% dos 101.516 registros — não depende de
  pixel, de GPS nem de arquivo montado.
- *Esforço:* **M**. Os predicados existem (`_condicao_lacuna`,
  `repositories/media.py:69-110`); o repositório já compõe filtros com
  SQLAlchemy. O trabalho novo é a gramática (tokenizador + serializador), a
  composição de N predicados em vez de um, os predicados sobre `evidence`, e o
  espelho no webapp (URL como fonte de verdade em vez de `useState`).
- *Custo recorrente:* zero.
- *Desbloqueia:* a fase 13 inteira ganha superfície — o "Hub de trabalho
  pendente" (item B de lá) passa a poder linkar cada fila em vez de descrevê-la,
  e a "trilha de fato confirmado" (item C de lá) ganha como se auditar
  (`confianca:alta origem:exif` mostra exatamente o que a regra vai
  autoconfirmar, **antes** de ligar a regra).

**Duas armadilhas, ditas porque os próprios mapas as apontam.**

Não portar o parser char-a-char (`serialize.go:80-191` é um parser próprio, e o
mapa de UX já observa que o erro de tipo não aponta a posição na string). Em
Python/TS, tokenização com biblioteca ou regex testada entrega o mesmo contrato
com menos borda.

Não construir um segundo formulário espelhando os mesmos campos. O PhotoPrism
tem os dois (`frontend/src/component/photo/toolbar.vue:106-258`, 12 dropdowns
redundantes com a DSL) e o mapa 03 §4.3 já julga: é manutenção duplicada. O
contrato certo é o de `photos.vue:307-312` — texto livre e controles gravam no
**mesmo** objeto; a UI existente (chips de recorte, facetas do Panorama) vira
uma segunda entrada, não um segundo estado.

---

## 4. Item B — proteger a camada que não se refaz

**Por que sobrevive ao filtro 1.** Todo app de mercado faz backup de *fotos*.
Nenhum faz backup das *suas decisões sobre as fotos*, porque nenhum registra
decisão por campo. O Lightroom faz backup do catálogo — binário, opaco, sem
diff, restaurável só por inteiro. Apple e Google não te dão nada que dê para
segurar na mão. Aqui a camada de julgamento é o produto: D-024 a D-039 são meses
de calibração sobre 101 mil registros, e é a única camada que uma nova varredura
**não** reconstrói. Perder os arquivos é ruim; perder o julgamento sobre eles é
perder a fase 1 até a 13.

**O mecanismo a trazer.** Só o PhotoPrism tem o par completo:

- `internal/photoprism/backup/albums.go:19` (`Albums`) — exporta cada álbum como
  **YAML legível por humano**, com `RestoreAlbums` em `:85` para o caminho de
  volta. Roda sob mutex dedicado (`backupAlbumsMutex`), uma operação por vez.
- `internal/photoprism/backup/database.go:27` (`Database`) — dump SQL com rotação
  e retenção configurável.
- `internal/workers/backup.go:23` (`NewBackup`, `StartScheduled`) — os dois
  rodam agendados, não só quando alguém lembra. CLI:
  `photoprism backup --albums` / `--database --retain N`.

O Immich tem só a metade de baixo (job `DatabaseBackup`, com deduplicação em
`repositories/job.repository.ts:257` e notificação ao admin em caso de falha,
`services/notification.service.ts:81`) — dump de banco, nenhum artefato legível.
**Fica com o PhotoPrism**, e a diferença é exatamente o que importa: o YAML
legível é versionável em git, dá diff e serve para revisão, não só para desastre.

**A terceira perna, e ela vem do Immich.** Depois de migrar, o Immich compara o
esquema real com o declarado e loga as divergências
(`services/database.service.ts:118-127`), e recusa downgrade explicitamente com
mensagem clara em vez de falhar de forma obscura
(`repositories/database.repository.ts:387-394`). Isso não é teoria aqui: D-038
registra, por escrito, que a migração `0014` **não é atômica** — "uma interrupção
antes do backfill deixaria a coluna criada com `alembic_version` em 0013, e a
tentativa seguinte morreria em `duplicate column name` — o app deixaria de
abrir". A migração foi escrita para ser segura para retomar, o que é a resposta
certa para aquela migração; a checagem no boot é a resposta genérica para a
próxima, que ninguém vai lembrar de escrever assim.

- *Muda o quê:* três garantias que hoje dependem de disciplina. (1) O julgamento
  vira artefato legível e diffável — `papel` ACERVO/SINAL, evidências com origem
  e justificativa, decisões de duplicata, plano de operações. (2) O catálogo
  ganha cópia automática com retenção, em vez de `sqlite3 .backup` lembrado à
  mão em quatro scripts. (3) Um esquema divergente é diagnosticado no boot com
  nome, em vez de virar "o app não abre".
- *Esforço:* **S**. `sqlite3 .backup` já é usado e o padrão está entendido nos
  scripts existentes (WAL exige `.backup`, não `cp` — comentado em
  `scripts/rebaixar_nao_acervo.py:88-90`). O export legível é uma consulta e um
  serializador. A checagem de esquema é comparar `alembic_version` + `PRAGMA
  table_info` contra o esperado.
- *Custo recorrente:* zero em dinheiro; espaço em disco proporcional à retenção
  (o catálogo de 101 mil registros é da ordem de dezenas de MB, não de GB).
- *Desbloqueia:* nada funcionalmente — e é justamente por isso que fica em
  segundo, não em primeiro (ver seção 6). O que ele faz é tornar reversível
  qualquer coisa que os outros itens quebrem.

**Nota de escopo.** Export legível não é sidecar XMP (roadmap item 9). São
problemas diferentes: o XMP devolve metadado ao fluxo do Lightroom e depende de
haver onde escrever (bloqueado por acesso físico ao volume); o export daqui
descreve o **catálogo** num arquivo do próprio app, ao lado do `.db`, e não toca
em nada do usuário. Não conflita com o invariante 1 nem com o 7.

---

## 5. Item C — o `.xmp` que muda sem o arquivo mudar

**Por que sobrevive ao filtro 1.** Google Fotos e Apple Fotos ignoram sidecar
por completo. O Lightroom escreve XMP e lê o seu próprio, mas só quando você
manda ("Read Metadata from File", por seleção, manual). O Mylio sincroniza o
dele. **Duas ferramentas cooperando sobre a mesma biblioteca, com o sidecar como
canal, sem uma mandar na outra** não é o que o mercado faz — e é exatamente a
situação do dono, que usa Lightroom e vai continuar usando.

**A lacuna, medida no código.** A leitura do sidecar já existe e é boa (seção 2).
O que não existe é a **detecção**: `.xmp` não está em `supported_extensions()`
(`fotoorganizer/metadata/purepython.py:43-51` — Pillow, HEIF, RAW e vídeo, nada
de sidecar), então `scanner/discovery.py:185` nunca enumera o arquivo; e o
incremental pula por assinatura do arquivo de mídia, `(tamanho, mtime, inode)`
(`scanner/scanner.py:4`, `:529-534`). Consequência: **um `.xmp` escrito ou
alterado depois da indexação é invisível para sempre**, a menos de
`scan --reprocessar` (`scanner.py:168`), que relê o acervo inteiro. Cada estrela,
cada palavra-chave e cada título que o dono adicionar no Lightroom de hoje em
diante cai no chão.

**O mecanismo a trazer, e de quem.** Os dois tratam sidecar; resolvem problemas
diferentes:

- Immich: `handleSidecarCheck` (`services/metadata.service.ts:439-478`) +
  `getSidecarCandidates` (`:543-561`) — resolução **para frente** (dado o asset,
  ache o sidecar), rodando como job por asset dentro do pipeline. Para detectar
  um `.xmp` novo seria preciso reenfileirar todos os assets.
- PhotoPrism: `internal/photoprism/index_sidecar.go:16` (`mainForSidecar`), `:46`
  (`sidecarMainEnabled`) — resolução **ao contrário**. Num rescan não forçado,
  quando um XMP novo ou com `mod_time` alterado aparece, o resolvedor testa as
  duas convenções de nome contra as extensões principais conhecidas (ambos os
  casos de maiúscula/minúscula) sobre um cache `Files` já em memória — sem tocar
  o banco por candidato — e só então reenfileira o arquivo principal afetado.

**Fica com o PhotoPrism**, e sem hesitação: a estrutura dele é a de um scanner
de biblioteca em disco, que é a estrutura deste projeto; a do Immich é a de uma
fila por asset, que é o que este projeto não tem e não quer.

```
scan incremental hoje:      foto.jpg  (tamanho,mtime,inode) igual → pula
                            foto.xmp  não é extensão conhecida → nem enumera
                                      └── estrela nova do Lightroom: perdida

com mainForSidecar:         foto.xmp  mod_time mudou
                                │
                                ├─ tenta "foto.xmp" → tira .xmp → foto.{jpg,cr3,…}
                                └─ tenta "foto.jpg.xmp" → tira .xmp → foto.jpg
                                        │
                                        ▼  (cache em memória, sem SELECT por candidato)
                                   reenfileira SÓ o principal casado
```

- *Muda o quê:* a curadoria que o dono faz no Lightroom passa a chegar ao
  catálogo sozinha. É a mesma tese de D-030 e D-034 — "intenção declarada é
  abundante e não custa nada para ler" — aplicada ao futuro em vez de ao
  passado: em vez de garimpar 27.226 nomeações de álbum já existentes, capturar
  a nomeação nova no dia em que ela acontece.
- *Esforço:* **S/M**. Um segundo conjunto de extensões na descoberta (o `.xmp`
  precisa ser *enumerado* sem virar linha em `media_files` — sidecar não é
  acervo), o resolvedor reverso com cache, e o reenfileiramento. A leitura e a
  fusão já estão prontas (`exiftool.py:161-215`).
- *Custo recorrente:* zero em dinheiro; um `stat` a mais por `.xmp` por
  varredura.
- *Depende de:* volume montado. **E é aqui que este item tem que ser honesto:**
  o `.xmp` mora ao lado do original, no mesmo volume desmontado das 45.397 fotos
  do Lightroom (D-028). Hoje alcança os ~5,6 mil arquivos locais, não o acervo.
  A razão de entrar mesmo assim é que a fase 12 item A já foi entregue (D-036) —
  o dia em que o HD montar deixou de ser hipotético, e este é o item que
  transforma aquele evento em fluxo contínuo em vez de uma colheita única.

**A limitação a decidir antes de codar**, porque o PhotoPrism a documenta como
débito próprio (`internal/photoprism/README.md:62`): um `.xmp` **apagado** não é
detectado no caminho incremental — só um rescan forçado reflete a remoção, e
mesmo assim alguns campos podem não reconciliar. Para este projeto a resposta
provavelmente é o invariante 8 aplicado a metadado: sidecar que some não desfaz
o que já foi lido — a entrada em `metadata_entries` continua, com a origem
`xmp_sidecar` dizendo de onde veio. Fica como pergunta em aberto do item, não
como surpresa na implementação.

---

## 6. Escala, confiabilidade e trade-offs

**Escala.** Nenhum dos três itens é sensível a tamanho de acervo da forma que a
grade é. O Item A compõe predicados que já rodam sobre 101.516 linhas com os
índices existentes — o risco não é volume, é uma composição de N predicados
gerar um plano ruim (`OR` sobre subconsultas de `evidence` sem índice em
`(campo, origem)`). O Item B copia um arquivo de dezenas de MB. O Item C
acrescenta um `stat` por sidecar; num volume com 45 mil fotos do Lightroom, isso
é da mesma ordem do `stat` por foto que o scan incremental já paga
(`scanner.py:7`).

**O que falha primeiro.** No Item A, a expressão booleana. `!` e `|` sobre
predicados que são subconsultas é onde um recorte inocente vira varredura
completa; a mitigação é começar sem negação e sem OU (conjunção pura de tokens,
que é 90% do uso real) e só então medir se vale o resto. No Item B, o dump
concorrente com uma escrita em WAL — daí a insistência em `.backup` em vez de
`cp`, e o mutex dedicado que o PhotoPrism usa (`backupAlbumsMutex`). No Item C,
o falso pareamento: `foto.xmp` casando com o `foto.jpg` errado numa pasta com
`foto.jpg` e `foto.cr3` — que é por que o resolvedor testa contra as extensões
principais **conhecidas do catálogo** e não adivinha.

**Trade-offs declarados.**

*A ordem A → B → C não é a ordem de valor/custo bruta, e isso é uma escolha.*
O Item B é mais barato (S contra M) e protege tudo. Se a régua fosse
custo puro, ele seria o primeiro. Ele fica em segundo porque o valor dele é
**zero no caso esperado** — é seguro, e seguro só entrega valor na cauda. O
Item A entrega valor todo dia em que alguém abrir o app, e é o único dos três
que converte em capacidade visível um diferencial pelo qual o projeto já pagou
(a tabela `evidence`, construída no M3). Quem pesar risco de cauda acima de
valor contínuo deve inverter os dois — e como o B é S e não toca em nada que o
A toca, os dois podem correr em paralelo sem conflito. Registrado em D-044.

*O Item A cria uma segunda linguagem para o usuário aprender.* Custo real. A
mitigação não é documentação: é o round-trip. Como `Serialize` reconstrói a
string a partir do objeto, clicar nos controles que já existem **escreve a
sintaxe na caixa** — o usuário aprende a gramática usando a UI que já sabe usar.
Sem o round-trip simétrico, essa mitigação não existe e o item vira uma caixa de
texto que ninguém preenche.

*O Item C aumenta a superfície do scan por um ganho que hoje é pequeno.*
Enumerar mais uma extensão significa mais um caminho onde `iter_media_files`
pode engolir um `OSError` — e D-037 registra que esse caminho já mentiu uma vez.
A mitigação é reusar as guardas que aquela fatia instalou, não escrever guardas
novas.

*Os três são aditivos e reversíveis.* Nenhum apaga registro, nenhum move
arquivo, nenhum manda dado para fora. O Item A é leitura; o B escreve só em
arquivo próprio do app; o C lê `.xmp` e escreve em `metadata_entries`, com
origem registrada. Nenhum toca invariante.

---

## 7. Descartado, e por qual filtro

Esta seção é tão entregável quanto a lista de itens. Sem ela, alguém revisita as
mesmas ideias daqui a dois meses e refaz o mesmo julgamento.

### 7.1 Morreu no filtro 1 — é table stakes, não diferencial

| Mecanismo | Âncora | Quem já faz |
|---|---|---|
| Empilhamento de RAW+JPEG / capturas irmãs | PhotoPrism `index_mediafile.go:150-200`, `mediafile_related.go:16` | Lightroom, Apple Fotos e Mylio empilham RAW+JPEG. Ver nota abaixo — o gap é real, o rótulo "diferencial" é que não é |
| Grade teclado-first, foco do DOM como fonte da verdade | Immich `focus-actions.ts:36`, `Thumbnail.svelte:227-232`; PhotoPrism `photos.vue:296-319` | Lightroom e Photo Mechanic são teclado-first há décadas. E o `CLAUDE.md` já declara "teclado-first" como decisão de stack — é requisito do projeto, não achado desta leitura |
| Tri-state `mixed` em edição em lote | PhotoPrism `chip-selector.vue:199-234` | O Lightroom mostra `<mixed>` no painel de metadados desde sempre |
| Edição não destrutiva como lista ordenada de operações | Immich `asset-edit.table.ts:34` | O Lightroom **é** isso. Além disso, o MVP não edita imagem (invariante 7) |
| Live/Motion Photo como asset de primeira classe | Immich `metadata.service.ts:177-206,681-825` | Nativo no iOS/Android e nos dois apps de mercado |
| Escada thumbnail→preview→original + prefetch direcional | Immich `adaptive-image-loader.svelte.ts:34`, `PreloadManager.svelte.ts:12` | Carregamento progressivo é padrão de qualquer galeria |
| Seleção persistente entre navegação e reload | PhotoPrism `clipboard.js:70-80` | Quick Collection / target collection do Lightroom. E o Item A resolve por outro caminho: se o recorte é um link, "onde eu parei" é um link |
| Fila de revisão como filtro sobre a grade geral | PhotoPrism `routes.js:427` | O próprio mapa 03 §4.3 já julgou: aqui a revisão é tela própria (lista origem→destino), e virar "mais um filtro" perderia a especialização |
| **Estado do pipeline gravado no catálogo em vez da fila** | Immich `asset-job-status.table.ts:5`, `asset-job.repository.ts:356-369` | **Este é o descarte menos óbvio da rodada.** O README do `referencia-immich` o lista entre os três "vale importar" — mas é arquitetura interna que o usuário nunca vê, e o que ninguém vê não diferencia produto nenhum. Higiene de engenharia legítima se a fila crescer; não item de backlog de valor. Ver D-041 |
| Lock por hash na indexação paralela; verificação de miniatura antes de servir; sharding do cache de thumb; `awaitWriteFinish`; cancelamento de lote por disco cheio | PhotoPrism `index_filehash.go:19`, `thumb/verify.go:16`, `thumb/create.go:41`, `convert.go:69,82`; Immich `library.service.ts:136-139` | Higiene invisível. Cada um custa XS e nenhum é motivo para uma fatia. Se algum dia alguém mexer no arquivo vizinho, aplique de passagem |

**Nota sobre o empilhamento — os dois mapas do PhotoPrism discordam, e resolvo
aqui.** O mapa `01-ingestao-e-arquivos.md` §11 chama de "vale considerar" (M),
argumentando que `duplicates/` agrupa hash idêntico e phash mas não RAW+JPEG do
mesmo clique (bytes diferentes, phash diferente — são codificações distintas da
mesma cena). O mapa `03-ux-e-organizacao.md` §4.3 chama de "não vale", dizendo
que `papel` ACERVO/SINAL já resolve. Julgamento: **o gap técnico do mapa 01 é
real e o mapa 03 subestima** — `papel` responde "isto é acervo ou testemunha",
não "estes dois arquivos são o mesmo disparo". Mas o item morre no filtro 1
desta fase, não no argumento do mapa 03. Ele volta como candidato de roadmap **depois
de medir**, porque o tamanho do problema é desconhecido: o Lightroom, por padrão,
não trata o JPEG ao lado do RAW como foto separada, então o `.lrcat` importado
(54.086 `captureTime`, D-038) pode já ter escondido metade das capturas irmãs. A
medição é barata e não precisa de pixel: contar, por fonte, linhas com a mesma
`data_capturada` e a mesma câmera cuja extensão difere. Sem esse número, "M de
esforço" é chute. Ver D-042.

### 7.2 Morreu no filtro 2 — diferencia, mas não paga aqui

| Mecanismo | Âncora | Por que não paga |
|---|---|---|
| Faces, NSFW, labels, caption, OCR, CLIP — o domínio inteiro | PhotoPrism `internal/ai/*`, `index_faces.go`, `mediafile_vision.go`; Immich `04-machine-learning.md` | ~5% de pixel legível (D-028). É o mesmo corte da fase 12; a leitura do PhotoPrism não muda nada, só confirma. E o PhotoPrism trata como fila cara e agendada à parte (`vision.yml`) justamente porque pressupõe acervo com pixel |
| Cascata de conversores RAW externos (Darktable→RawTherapee→sips→heif-convert) | PhotoPrism `convert_image_jpeg.go:16-90` | Quatro binários para 5% do acervo, e o próprio PhotoPrism documenta que a cadeia não é determinística entre ambientes. `rawpy` + `pillow-heif` já cobrem |
| Vocabulário de 25 tamanhos de miniatura | PhotoPrism `thumb/sizes.go:51-75`, `names.go:23-47` | Existe para compatibilidade com clientes móveis e apps de terceiros. Single-user com grade própria define os tamanhos por necessidade de UI |
| Célula geográfica (S2) para clustering do mapa | PhotoPrism `location.go:10` | Troca O(n²) por O(n) num mapa que hoje desenha 4.944 heranças (D-025) sem queixa medida. Otimização sem gargalo observado. Volta se o mapa engasgar |
| Tombstones `*_audit` + cursor `updateId` (uuid v7) | Immich `asset-audit.table.ts:5`, `sync.repository.sql:413-443` | Existem para sync delta multi-dispositivo. Single-user, uma máquina |
| Memórias materializadas / "on this day" | Immich `memory.table.ts:26`, `memory.service.ts:47-66` | Morre nos dois: Google e Apple fazem memórias agressivamente (filtro 1), **e** o Immich exige miniatura existente para incluir o asset (filtro 2) |
| WebDAV, links compartilhados, OAuth2/OIDC, cluster Portal↔Node, quotas, `ownerId` | PhotoPrism `internal/service/cluster/*`, `internal/api/links.go`, `routes_webdav.go` | Não há segundo usuário nem segundo node. Servidor escuta 127.0.0.1 e recusa origem não local |
| Reverse geocoding via serviço hospedado | PhotoPrism `internal/service/maps/location.go:46` | Inverte a prioridade do invariante 4. O projeto já decidiu offline-first, e nesse ponto está à frente do PhotoPrism |
| Ticker de auto-reconciliação quando o volume remonta | PhotoPrism `workers/auto/index.go` (`mustIndex`) | Morre nos dois: Lightroom e Mylio religam volume externo (filtro 1), e a fase 12 (D-036/D-037) já entregou o mecanismo — falta só disparar sozinho, o que é conveniência, não capacidade |

### 7.3 Descartado antes dos filtros — viola invariante

**Modo "mover" do import** (PhotoPrism `import_options.go:48`,
`ImportOptionsMove`, que remove arquivos da origem após a cópia). Contradiz
diretamente o invariante 2 do `CLAUDE.md` — "a execução é copiar por padrão,
nunca mover". Não entra nem como opção desligada: o valor que entrega
(arrumar a pasta de import depois de consumida) não paga um bug apagar um
original que não tinha cópia.

### 7.4 Descartado porque já existe aqui, e melhor

Não é descarte por filtro; é para ninguém propor de novo.

- **Prioridade de fonte global** (PhotoPrism `internal/entity/src.go:61-89`,
  `SrcPriority`, com o contrato replicado em cada setter, ex.
  `photo_datetime.go:23-30`). É mais geral que o `lockedProperties` do Immich,
  mas guarda só a string da fonte vencedora: a evidência perdedora é descartada,
  não há score por instância, nem justificativa, nem quem/quando, e a prioridade
  é fixa por *nome* de fonte — um GPS EXIF válido e um implausível valem o
  mesmo. Importar seria regressão frente a `evidence`.
- **Purge com soft/hard delete binário** (PhotoPrism `purge.go:36,218-245`).
  Uma foto sem arquivo vira invisível ou removida; nos dois casos para de doar
  GPS e correlação. `papel` ACERVO/SINAL (D-024) é estritamente melhor —
  medido: apagar as 45.822 miniaturas do Apple Fotos levaria as fotos com lugar
  estimado de 2.117 para 162.
- **Estado de sugestão em rosto — nenhum dos dois tem, e o PhotoPrism confirma
  o que a fase 12 já dizia do Immich.** `MarkerReview`
  (`internal/entity/marker.go:83`, setado como `score < 30`) é flag de
  *qualidade da detecção*, não "sugestão pendente de confirmação"; o `SubjUID`
  é escrito como fato assim que o matching roda. O único gesto na direção certa
  é um veto **em memória com TTL de 30 min** (`internal/photoprism/faces.go:24-46`,
  `rememberVeto`/`faceVetoTTL`) — que não sobrevive a restart nem a
  reclusterização, ou seja, não é o "cannot-link" persistente que o invariante 6
  exige. Quando o `FaceRecognitionProvider` sair de stub, o desenho começa na
  tabela de sugestão pendente que **nenhum dos dois** tem.
- **Leitura de sidecar `.xmp` com precedência declarada** — já implementada e
  idêntica à regra do Immich (seção 2). Só falta o gatilho: Item C.
- **Três tipos nomeados de integridade** — `scripts/verificar_integridade.py`
  já cobre os três (seção 2).
- **Template de destino com preview e validação** — roadmap item 4, entregue em
  2026-08-02.

---

## 8. Reforços a itens já planejados

Achados que não viram item novo porque fortalecem um que já está na fila.

**Sub-seleção dentro do diálogo de lote, com guarda de fechamento** —
PhotoPrism `batch-edit.vue:1327-1357` (tira de miniaturas com checkbox por item;
o save usa `selection.filter(p => p.selected)`, `:1463-1469`) e `:1363-1370`
(`hasUnsavedChanges()` bloqueia o fechamento, com shake em vez de descarte
silencioso). Reforça a **fase 13, item A**: a tela proposta lá — "42 grupos
resolvidos automaticamente — revisar ou confirmar todos" — é exatamente onde
"excluir 2 dos 42 sem refazer a seleção" acontece, e onde um Escape acidental
não pode jogar fora uma decisão em lote quase pronta.

**Descarte inline sem abrir detalhe** — PhotoPrism `people/new.vue:607-614`
(`toggleHidden`, rejeita direto no grid de triagem). A feature (clustering
facial) não entra; o padrão "rejeitar sugestão sem sair da lista" reforça a
**fase 13, itens A e D**.

**Barra de ação que só existe quando há seleção** — PhotoPrism
`clipboard.vue:3-17` (`v-if` em vez de barra desabilitada permanente) e
`:29-139` (um único flag `busy` trava a barra inteira durante qualquer chamada
em voo, matando duplo-submit em lote). Reforça a **fase 13, item B**.

**Checagem de plausibilidade de offset (limite de 27 h)** — PhotoPrism
`internal/meta/resolver.go:41-48`: se `TakenAt` e `TakenAtLocal` divergem mais
que 27 h, o offset é tratado como corrompido e a hora local vira a confiável.
Não há UTC offset real maior que ~14 h. Reforça **D-038**: agora que existem
`data_capturada` e `data_capturada_utc` e o offset é a **diferença** entre elas,
um EXIF corrompido produz um offset absurdo que nenhuma coluna denuncia. Custa
uma linha no ponto de escrita e vale para 100% dos registros.

**Clamp de latitude e wrap de longitude antes de persistir** — PhotoPrism
`internal/meta/gps.go:133` (`NormalizeGPS`). `metadata/purepython.py:240-245`
(`_dms_to_decimal`) converte DMS→decimal sem verificar faixa. XS.

**Skip da reaplicação de `Orientation` em imagem decodificada por libheif** —
PhotoPrism `internal/thumb/vips_convert.go:26-42`: o decoder HEIF já aplicou
`irot`/`imir`, então reaplicar o `Orientation` EXIF gira a imagem duas vezes.
`pillow-heif` decodifica pelo mesmo libheif. É uma classe de bug real, e o HEIC
domina justamente a fatia que **tem** pixel. Um teste sintético com HEIC girado
cobre.

---

## 9. O que eu revisitaria

**Se os volumes do Lightroom montarem e ficarem montados.** O Item C sobe para
primeiro — ele deixa de alcançar 5,6 mil arquivos e passa a alcançar ~50 mil, e
vira o caminho pelo qual toda curadoria futura entra sozinha. E o empilhamento
de capturas irmãs (§7.1) merece a medição antes da próxima rodada de
priorização, porque com os arquivos presentes o `phash` volta a ser uma
alternativa e o cálculo muda.

**Se o acervo com pixel passar de ~5% para ~30%.** Todo o §7.2 primeiro bloco
(visão, rosto, OCR, CLIP) precisa ser reavaliado do zero, não ajustado. O corte
atual é sobre o dado, não sobre o mérito dos mecanismos.

**Se aparecer um segundo dispositivo ou um segundo usuário.** Os tombstones
`*_audit` com cursor `updateId` deixam de ser overkill e passam a ser a resposta
certa — e o momento de adotá-los é *antes* de haver dois dispositivos, não
depois. É o único item de §7.2 cuja janela de adoção fecha.

**Se o Item A entrar e o `versao:` for usado de verdade.** A pergunta seguinte
aparece sozinha: "recomputar só o que a versão X decidiu". Hoje ela não se
justifica (seção 3), porque a evidência é cache derivado e o recompute é
integral. Se o motor de sugestões ficar caro o bastante para que reprocessar
101 mil registros incomode, aí sim vale a operação escopada — e o token `versao:`
já terá provado que a informação existe e é confiável.

**Se a expressão booleana do Item A for cortada do escopo inicial** (o que
recomendo), vale medir depois de três meses quantos recortes salvos o dono
realmente criou e se algum deles pediu OU ou negação. Se nenhum pediu, o corte
vira permanente e economiza a parte mais frágil do parser.
