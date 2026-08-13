# PhotoPrism — metadados de imagem, thumbnails e visão computacional

Fonte: `~/dev/photoprism-develop` (Go, self-hosted, AGPLv3), sem repositório
Git local (clone sem `.git`) — caminhos relativos à raiz do módulo. Levantado
em 2026-08-12, cruzando leitura direta do código com o dossiê já ancorado em
`.local/audit/photoprism/{01-ingestao-e-midia,02-modelo-de-dados,
06-ia-e-enriquecimento}.md`.

Par deste mapa: [`docs/referencia-immich/02-metadados-e-midia.md`](../referencia-immich/02-metadados-e-midia.md)
e [`04-machine-learning.md`](../referencia-immich/04-machine-learning.md).

## Licença — leia antes de copiar qualquer coisa

O PhotoPrism é **AGPLv3**, sem exceção por diretório (ao contrário do Immich,
que isola o ML num serviço separado — aqui `internal/ai` está no mesmo
binário/licença do resto).

- Ler para entender arquitetura e **reimplementar**: livre.
- **Copiar código** para o Foto Organizer contamina o projeto inteiro. Não
  fazer — os mapas abaixo descrevem mecanismo, com `arquivo:linha`, nunca
  transcrevem trechos.
- Os modelos embutidos (`assets/models/{nasnet,nsfw,facenet,scrfd}`) têm
  proveniência própria (TensorFlow SavedModel / ONNX de terceiros), não a
  licença do PhotoPrism — mas não há motivo para baixá-los: o corte de pixel
  abaixo já descarta a maior parte desse território.

## Por que o corte de pixel muda a leitura deste material (relembrando)

Como no par do Immich: ~5% do acervo real tem pixel legível (D-028) e GPS é
raro no arquivo (D-029) — ver `docs/ROADMAP.md`. Tudo que depende de abrir o
arquivo e decodificar bytes (conversão RAW/HEIC, geração de thumbnail,
labels/NSFW/captions/faces por visão computacional) só se aplica a essa
fatia pequena. O que **não** depende de pixel — precedência de tags de data
já lidas de outro catálogo, resolução de timezone, o esqueleto de proveniência
— vale para 100% dos registros e é onde este mapa concentra a recomendação.

---

## 1. Precedência de metadados (EXIF / XMP / JSON / GPhotos)

### 1.1 Ordem de leitura por arquivo

`MediaFile.MetaData()` (`internal/photoprism/mediafile_meta.go:93-146`) é o
ponto único de entrada, com cache por `sync.Once` (`m.metaOnce`):

1. **EXIF bruto** do arquivo original via `data.Exif(...)`
   (`internal/meta/exif.go:47` `Data.Exif`) — parser Go interno
   (`dsoprea/go-exif`), com `bruteForce` como modo de segunda tentativa
   quando o parser padrão falha em arquivos malformados.
2. **JSON sidecar "Google Photos style"** (`img_1234.json`), se existir —
   `fs.SidecarJson.FindAll` + `data.metaData.JSON(jsonFile, ...)`
   (`mediafile_meta.go:110-122`). O despacho por conteúdo do JSON
   (`internal/meta/json.go:42-49`, `Data.JSON`) decide entre três formatos
   pelo texto bruto: contém `ExifToolVersion` → `data.Exiftool(...)`; contém
   `albumData` → `data.GMeta(...)`; contém `photoTakenTime` → `data.GPhoto(...)`
   (Google Photos Takeout, `internal/meta/json_gphotos.go:83,104`).
3. **JSON do ExifTool** (cache gerado sob demanda, `internal/meta/
   json_exiftool.go:315` `Data.Exiftool`) — lido por último em
   `mediafile_meta.go:126-130` (`ReadExifToolJson`).

Cada etapa que "ganha" atualiza `err = nil`, então o merge é cumulativo (cada
fonte escreve por cima da anterior nos campos que ela preenche) — não há uma
regra explícita de "a última fonte sempre vence campo a campo": o formato
efetivo de vitória é decidido dentro de cada parser (`Exif`, `Exiftool`,
`GMeta`, `GPhoto`), não centralizado num único merge.

### 1.2 XMP é tratado como arquivo relacionado, não como sidecar de merge

Diferente do Immich (onde o sidecar XMP é lido *dentro* da mesma passada de
extração e explicitamente sobrepõe a mídia), o PhotoPrism trata o `.xmp`
como um `MediaFile` próprio dentro do grupo de `RelatedFiles` — o `switch`
de tipo em `internal/photoprism/index_mediafile.go:498` (`case m.IsXMP()`)
roda `meta.XMP(m.FileName())` (`internal/meta/xmp.go:42` `Data.XMP`) e
aplica cada campo via `photo.Set*(..., entity.SrcXmp)`
(`index_mediafile.go:501-539`): `SetTitle`, `SetCaption`, `SetTakenAt`,
`SetCoordinates`, `SetCameraSerial`, mais `details.Set*` para
keywords/notes/subject/artist/copyright/license. Cada `Set*` decide se
sobrescreve ou não com base na prioridade de fonte (§2), não por regra
hardcoded de "sidecar vence" — na prática o resultado costuma coincidir
(XMP tem prioridade 32, acima de EXIF/JSON que entram como `SrcMeta`,
prioridade 16), mas o mecanismo é genérico, não um caso especial de XMP.

### 1.3 Regiões de rosto em XMP (MWG/ACDSee)

`internal/meta/xmp_document.go:793` (`FaceRegions`) — mesma fonte de dado
que o Immich lê (`RegionInfo`, padrão MWG), aplicada via
`index_faces_xmp.go:93` (`collectXmpFaces`) e reconciliada com marcadores já
existentes em `index_faces_xmp.go:306` (`reconcileXmpFaces`), gated por
`--xmp-faces` / `PHOTOPRISM_XMP_FACES` (`internal/config/options.go:261`,
desligado por padrão). Preserva nomes atribuídos manualmente ao reconciliar.

---

## 2. Proveniência: prioridade de fonte global, não evidência por campo

`internal/entity/src.go:61-89` (`SrcPriority`) é uma tabela **única e
global** que mapeia string de fonte → inteiro de prioridade (`SrcAuto=1`,
`SrcFile=2`, `SrcName=4`, `SrcYaml/SrcMarker/SrcImage=8`, `SrcMeta/
SrcTitle/SrcCaption=16`, `SrcXmp=32`, `SrcManual/SrcVision=64`,
`SrcAdmin=128`). Todo setter de campo em `entity.Photo` segue o mesmo
contrato — exemplo concreto em `internal/entity/photo_datetime.go:23-30`
(`SetTakenAt`): compara `SrcPriority[source] < SrcPriority[m.TakenSrc]` e
recusa sobrescrever se a fonte nova tem prioridade menor **e já existe
valor não-zero**. A mesma regra se repete campo a campo (`SetCoordinates`,
`SetTitle`, `SetCaption`, ...) — não há uma função central de merge, é um
padrão replicado por convenção em cada `Set*`.

**Isso é estruturalmente mais pobre que a tabela `evidence` do
foto-organizer** (`docs/CONFIANCA.md`): o `Src` do PhotoPrism guarda só a
*string da fonte vencedora* no próprio registro (`Photo.TakenSrc`,
`Photo.PlaceSrc`, etc.) — a evidência perdedora é descartada, não há score
numérico por instância, não há justificativa legível, não há timestamp de
quando/quem, e a prioridade é fixa por *nome* de fonte (todo `SrcXmp` vale
32 sempre), não por *confiança da leitura específica* (um GPS EXIF válido e
um GPS EXIF com valor implausível têm a mesma prioridade `SrcFile`). O README
do par Immich já registrou essa mesma conclusão para o `lockedProperties`
(um array de nomes de coluna); o `Src` do PhotoPrism é mais geral que o
`lockedProperties` (cobre qualquer campo, não só os editados manualmente),
mas ainda assim é uma classificação, não um histórico. Nada aqui muda a
avaliação de "onde este projeto já está à frente".

---

## 3. Resolução de timezone

`internal/meta/resolver.go:25` (`Data.ResolveTimeZone`), chamada tanto pelo
caminho ExifTool JSON quanto pelo XMP (comentário de topo do arquivo,
`resolver.go:2-7`, confirma o compartilhamento). Cascata, na ordem do
código:

1. Se há `CreatedAt` (Media Create Date), vira `TakenAt` (`:29-31`).
2. Se não há `TakenAt`/`TakenAtLocal` mas há `TakenGps` (timestamp UTC do
   bloco GPS), assume `TimeZone = UTC` e usa o GPS time como `TakenAt`
   (`:34-38`).
3. **Checagem de plausibilidade**: se `TakenAt` e `TakenAtLocal` já
   existem e a diferença absoluta excede 27 horas, descarta o offset como
   inválido — loga e trata `TakenAtLocal` como o valor confiável, definindo
   `TakenAt = TakenAtLocal.UTC()` (`:41-48`). Não há UTC offset real maior
   que ~14h; 27h é uma margem de segurança contra EXIF corrompido.
4. Detecta offset explícito pela zona de `TakenAtLocal.Zone()`; se ausente e
   o MIME é MP4/QuickTime, assume UTC por convenção do formato
   (`:50-60`, comentário cita a doc oficial do QuickTime).
5. **Se há coordenadas GPS válidas** (`Lat != 0 && Lng != 0`), resolve o
   fuso pela posição via `tz.Position(lat, lng)` (`:63-66`) e recalcula
   `TakenAt`/`TakenAtLocal` fazendo o parse na `time.Location` encontrada.
   Sem GPS, mas com offset detectado no passo 4, normaliza os dois campos
   para UTC truncado (`:83-89`).
6. Fallback final: se ainda não há `TimeZone` (ou é `Local`/vazio) e o
   `TakenAt` está preenchido, tenta `tz.UtcOffset(...)` calculado a partir
   da diferença UTC↔local já resolvida (`:92-105`).
7. Preenche `TakenAtLocal` a partir de `TakenAt` quando um dos dois ficou
   vazio (`:111-121`), e reaplica os nanossegundos de sub-segundo por
   último para não interferir no parse de string (`:123-129`).

`MediaFile.TimeZone()` (`internal/photoprism/timezone.go:4-8`) é só um
getter fino sobre esse resultado já cacheado em `m.MetaData()`.

**Ponto útil e independente de pixel:** o passo 3 (limite de 27h para
descartar offset implausível) é uma heurística concreta de defesa contra
EXIF malformado que o mapa do Immich não documentou explicitamente (lá o
tratamento é só fallback para mtime/birthtime, não uma checagem de
plausibilidade do próprio offset). Ver §7.

---

## 4. Normalização de GPS

`internal/meta/gps.go:27` (`GpsToLatLng`) aceita tanto strings já decimais
(`GpsFloatRegexp`) quanto o formato DMS clássico do EXIF (graus/minutos/
segundos + referência N/S/E/W, via `exif.GpsDegrees`), retornando `0, 0`
quando não reconhece nenhum dos dois formatos — nunca gera erro, o chamador
trata `(0,0)` como "sem GPS". `internal/meta/gps.go:133` (`NormalizeGPS`,
não lido linha a linha nesta rodada) faz o clamp de latitude e wrap de
longitude antes de persistir. Mecanismo equivalente ao `hasGeo` do Immich
(`server/src/services/metadata.service.ts:1057`, que rejeita `NaN` e
`(0,0)`), com a diferença de que o parsing DMS→decimal já está embutido na
própria função de conversão, não numa lib externa.

---

## 5. Conversão RAW / HEIC / vetorial (depende de pixel)

`Convert.ToImage` (`internal/photoprism/convert_image.go:29`) é o
orquestrador. Ordem de tentativa por tipo de arquivo
(`convert_image_jpeg.go:16-90`, `JpegConvertCmds`):

1. **PNG/GIF/BMP/TIFF/HEIC/HEIF/AVIF** (e JPEG XL quando `djxl` não está
   disponível) são decodificados **nativamente por libvips**
   (`convert_image.go:99-124`, `internal/thumb/vips_convert.go:27`
   `vipsConvert`) — sem processo externo. Fallback para os conversores
   externos abaixo só em caso de erro, e só para os formatos que ainda não
   têm suporte nativo confiável (comentário em `convert_image.go:88-93`:
   TIFF/WebP/HEIC/AVIF/JPEG XL mantêm o fallback "até depender de libvips
   em todo runtime suportado").
2. **RAW e HEIF** via `sips` no macOS, se habilitado
   (`convert_image_jpeg.go:49-54`).
3. **RAW**: se `RawEnabled()`, cascata Darktable → RawTherapee (comandos
   `raw.DarktableCmd`/`raw.RawTherapeeCmd`, não lidos linha a linha nesta
   rodada) → **extração de preview via ExifTool mesmo com a renderização
   desligada**, para reaproveitar previews já embutidos
   (`convert_image_jpeg.go:73-90`, comentário explícito sobre essa
   independência).
4. **HEIC/AVIF**: `heif-dec`/`heif-convert` como alternativa aos passos 1-2
   (`convert_image_jpeg.go:64-70`).
5. **Insta360 dual-fisheye**: dewarp via `ffmpeg`/filtro `v360` antes de
   qualquer conversão de formato genérica (`convert_image_jpeg.go:29-46`).

**Detalhe de correção que sobrevive ao corte de pixel exatamente onde
importa:** `vipsConvert` (`internal/thumb/vips_convert.go:27-42`) **pula a
reaplicação do EXIF `Orientation`** quando a imagem foi carregada via
libheif (`vipsLoadedViaHeif(img)`), porque o decoder HEIF já aplicou
`irot`/`imir` durante o decode — reaplicar giraria a imagem duas vezes. O
comentário no próprio arquivo (`:26-29`) documenta o caso não-conformante
(HEIC que carrega `Orientation` EXIF sem `irot` correspondente) como
conhecido e não coberto. Ver §7 — isso é diretamente relevante para
`pillow-heif` no foto-organizer, já que HEIC é o formato nativo de captura
do iPhone e concentra boa parte do que sobra no lado "tem pixel" do corte.

---

## 6. Thumbnails: tamanhos, cache e pipeline

### 6.1 Vocabulário de tamanhos

`internal/thumb/sizes.go:51-75` — 25 variantes nomeadas
(`internal/thumb/names.go:23-47`), cada uma com resample method e formato
próprios (`Colors` 3×3 nearest-neighbor PNG sem ICC até `Fit15360` 15360×8640
JPEG). `Find(pixels)` (`names.go:71-80`) escolhe a maior variante que caiba
no tamanho pedido, sempre reaproveitando um tamanho maior já gerado como
fonte para os menores (documentado em `.local/audit/photoprism/
01-ingestao-e-midia.md`, capability `thumbnails-geracao-por-arquivo`).

### 6.2 Cache em disco keyed por hash de conteúdo, com sharding de diretório

`internal/thumb/create.go:24-49` (`FileName`): o caminho do arquivo de
thumbnail é `<thumbPath>/<hash[0]>/<hash[1]>/<hash[2]>/<hash>_<w>x<h>_<
método>.<formato>` — os três primeiros caracteres do hash viram três níveis
de diretório (`path.Join(thumbPath, hash[0:1], hash[1:2], hash[2:3])`,
`create.go:41`), criados sob demanda (`fs.MkdirAll`). Isso evita um único
diretório flat com centenas de milhares de arquivos — o mesmo problema que
o Immich resolve com nesting de 2+2 caracteres em
`cores/storage.core.ts:347`. O PhotoPrism já usa o hash de conteúdo (não
UUID) como chave, que é exatamente o que o foto-organizer decidiu em
`CLAUDE.md` ("cache em disco... chaveado por conteúdo").

### 6.3 ICC, rotação e verificação

- **Perfil de cor ICC**: lido do original e aplicado na miniatura via
  libvips (`internal/thumb/icc.go:175` `GetIccProfile`,
  `internal/thumb/vips_icc.go`) — sem flag de usuário, sempre ativo quando
  o original carrega um perfil não-sRGB.
- **Rotação por Orientation EXIF**: `internal/thumb/rotate.go:22`
  (`Rotate`), mais correção manual via API
  (`internal/photoprism/mediafile_thumbs.go:214`
  `MediaFile.ChangeOrientation`).
- **Verificação de integridade** pós-geração: `internal/thumb/verify.go:16`
  (`Verify`) confirma que o arquivo gerado é uma imagem válida e não
  truncada antes de servi-la — evita propagar corrupção do pipeline de
  conversão para o cache.

### 6.4 Cores dominantes

`internal/photoprism/colors.go:16` (`MediaFile.Colors`) roda sobre a
miniatura já gerada (nunca a imagem em resolução completa) para alimentar o
filtro de busca por cor — mesma disciplina de "nunca decodificar full-res
para uma operação leve" que o foto-organizer já segue para a grade.

---

## 7. O que sobrevive ao corte de "~5% tem pixel"

A régua é a mesma do par Immich: um mecanismo só é candidato a "vale
considerar" se (a) não depende de decodificar pixel, ou (b) é barato o
suficiente para valer nos poucos milhares de arquivos que **têm** pixel —
e nenhum dos dois se sobrepõe ao que o README do Immich já cobriu (dedup
por embedding CLIP, thumbhash de grade, journal de move).

### Vale considerar

1. **Checagem de plausibilidade de offset de timezone (limite de 27h)** —
   `internal/meta/resolver.go:41-48`. Não depende de pixel: aplica-se a
   qualquer registro com data EXIF/XMP/catálogo, inclusive os 95% sem
   arquivo local. É uma linha de defesa barata contra timestamp corrompido
   que o `docs/AGRUPAMENTO.md`/futuro timezone estimado do foto-organizer
   ainda não tem — vale como caso de teste em
   `scripts/avaliar_agrupamento.py` quando a estimativa de timezone virar
   fatia real do roadmap (ver D-029, "modelo de tempo" já sinalizado como
   pré-requisito no README do Immich).
2. **Skip de reaplicação de `Orientation` EXIF para imagens decodificadas
   via libheif** — `internal/thumb/vips_convert.go:26-29`. Aplica-se
   exatamente ao formato que domina a fatia "tem pixel" do acervo real
   (HEIC de iPhone). `pillow-heif` no foto-organizer decodifica via
   libheif do mesmo jeito; reaplicar a orientação EXIF por cima de um
   decode que já girou a imagem é uma classe de bug de dupla-rotação real
   e barata de evitar — um teste sintético com um HEIC girado (`irot`
   presente, sem `Orientation` inconsistente) cobre o caso.
3. **Sharding de diretório do cache de thumbnail por hash de conteúdo
   (3 níveis)** — `internal/thumb/create.go:41`. O foto-organizer já
   decidiu "cache em disco chaveado por conteúdo"; falta só o detalhe de
   não despejar tudo num diretório flat quando a fatia com pixel crescer
   (dezenas de milhares de miniaturas, mesmo sendo 5% do total). Custo de
   adoção é uma função de path, não uma dependência nova.

### Não vale (calibrado pelo acervo real)

- **Cascata de conversão RAW via binários externos (Darktable →
  RawTherapee → sips → heif-convert)** — `convert_image_jpeg.go` inteiro.
  O foto-organizer já resolveu isso de forma mais leve com `rawpy` puro-
  Python (ver `agente-imagem.md`), que é a escolha certa quando só ~5% do
  acervo tem pixel: não vale puxar quatro dependências binárias externas
  (com toda a fragilidade de "conversor varia por imagem Docker" já
  documentada no dossiê PhotoPrism) para um recorte que já funciona.
- **Vocabulário de 25 tamanhos de thumbnail nomeados** — excesso para um
  app single-user com grade própria; o foto-organizer já define seus
  próprios tamanhos por necessidade de UI, não por compatibilidade com
  clientes móveis/apps de terceiros como o PhotoPrism precisa suportar.
- **Labels TensorFlow/ONNX, NSFW, captions via LLM, face embedding
  (FaceNet/SCRFD)** — todo o domínio de `internal/ai/vision` e
  `internal/ai/face` (labels-tensorflow-classification,
  nsfw-detection-tensorflow, caption-generation, face-detection-onnx,
  face-embedding-facenet). Mesma conclusão do README do Immich para
  CLIP/InsightFace: alcança só a fatia com pixel, e mesmo nessa fatia
  compete com o phash já decidido para duplicata. Nenhum desses modelos
  resolve um problema que o foto-organizer tenha e o phash/metadados não
  cubram.
- **Modelo de dados de faces (`Marker`/`Face`/`Subject`,
  `internal/entity/marker.go:28-56`, `face.go:22-38`)** — repete o mesmo
  defeito conceitual que o README do Immich já apontou como o
  desalinhamento central com a invariante 6 (`CLAUDE.md`): `MarkerReview`
  (`marker.go:83`, setado como `score < 30` na criação) é uma flag de
  *qualidade da detecção*, não um estado de "sugestão pendente de
  confirmação" — o `SubjUID` é escrito como fato assim que o matching roda
  (`internal/photoprism/faces_match.go`), igual ao Immich. O único
  mecanismo parcialmente na direção certa é o veto **em memória, com TTL de
  30 min** (`internal/photoprism/faces.go:24-46`, `rememberVeto`/
  `faceVetoTTL`) — um "não sugira de novo por um tempo" que não sobrevive a
  um restart nem a uma reclusterização, ou seja, não é o "cannot-link
  persistente" que a invariante 6 vai exigir quando o `Protocol` de faces
  sair de stub. Vale só como lembrete de forma (uma tabela de veto existe
  como conceito), não como implementação a copiar — quando a feature real
  for construída, o design correto começa da tabela de sugestão pendente
  que nem o Immich nem o PhotoPrism têm, não desses dois.
- **Geocodificação reversa via serviço externo configurável
  (`internal/service/cluster` / provedor externo por API)** — fora do
  escopo deste mapa (é território de reverse geocoding *online*, o
  foto-organizer já decidiu offline-first); mencionado aqui só para
  registrar que o PhotoPrism não tem um dataset offline embutido
  equivalente ao GeoNames `cities500` do Immich — não há nada a herdar
  daqui, o par Immich já é a referência.
