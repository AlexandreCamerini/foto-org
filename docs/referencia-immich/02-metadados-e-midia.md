# Immich — metadados, geolocalização e geração de mídia

Fonte: `~/dev/fot`, versão 3.1.0, commit `5ad1e4e0f`. Caminhos relativos a
`server/src/` salvo indicação. Levantado em 2026-08-08.

---

## 1. Fluxo de ponta a ponta

### 1.0 Entrada — o que dispara tudo

| Origem | Arquivo:linha | Primeiro job |
|---|---|---|
| Upload HTTP | `services/asset-media.service.ts:124` (`uploadAsset`), enfileira em `:187` | `AssetExtractMetadata` com `source:'upload'` |
| Biblioteca externa (scan de disco) | `services/library.service.ts:435` (`queuePostSyncJobs`) | `SidecarCheck` → (via `job.service.ts:106`) `AssetExtractMetadata` |
| Reprocessamento manual por asset | `services/asset.service.ts:467` (`run`), casos `REFRESH_METADATA` / `REGENERATE_THUMBNAIL` / `TRANSCODE_VIDEO` | job direto |
| Botão "start" de fila no admin | `services/queue.service.ts:187` (`start`) | `*QueueAll` |
| Cron noturno | `services/queue.service.ts:263` (`handleNightlyJobs`), `:287` | `AssetGenerateThumbnailsQueueAll {force:false}` |

Na criação do asset o único EXIF gravado é `fileSizeInByte`
(`asset-media.service.ts:181-184`); o `type` (Image/Video) vem só da extensão
(`utils/mime-types.ts`, `mimeTypes.assetType`).

### 1.1 Etapa A — sidecar discovery (fila `sidecar`)

- `services/metadata.service.ts:439` `handleSidecarCheck` — testa candidatos na
  ordem: sidecar já registrado, `<original>.xmp`, `<basename>.xmp` (`:544`
  `getSidecarCandidates`), usando `storageRepository.checkFileExists(candidate,
  R_OK)`. Grava/apaga a linha `asset_file` tipo `sidecar`. Retorna `Skipped` se
  nada mudou — mas `Skipped` também encadeia o próximo job.
- `services/metadata.service.ts:490` `handleSidecarWrite` — caminho inverso:
  pega campos do banco (`description`, `dateTimeOriginal`, `latitude/longitude`,
  `rating`, `tags`, `timeZone`), filtra pelas `lockedProperties` (`:498`), e
  escreve XMP via exiftool (`:533`). Depois `job.service.ts:111` re-enfileira
  extração com `source:'sidecar-write'`.

### 1.2 Etapa B — extração de metadados (fila `metadataExtraction`)

`services/metadata.service.ts:235` `handleMetadataExtraction`:

1. `:237-240` carrega config + asset (`repositories/asset-job.repository.ts:148`
   `getForMetadataExtraction` — traz `columns.asset`, faces existentes e o
   arquivo sidecar).
2. `:246-249` em paralelo: `getExifTags(asset)` e
   `storageRepository.stat(originalPath)`.
3. `services/metadata.service.ts:580` `getExifTags` — o coração da leitura:
   - lê tags do arquivo original (`metadataRepository.readTags`), do sidecar (se
     houver) e, se for vídeo ou `.gif`, faz `ffprobe` (`:587` → `:1095`
     `getVideoTags`);
   - **se o sidecar tem data, apaga todas as tags de data do arquivo original e
     também `zone`/`tz`/`tzSource`** (`:591-608`);
   - descarta `Duration` de imagens que não podem ser animadas (`:612`) e nunca
     usa `Duration` do sidecar (`:617`);
   - para HEIF/HEIC/AVIF **ignora `Orientation` EXIF e usa `QuickTime:Rotation`**
     (`irot`) mapeado em `:1138` `getHeifOrientation`;
   - retorna merge `{...mediaTags, ...videoResult.tags, ...sidecarTags}` — **o
     sidecar vence** (`:631`).
4. `:253` → `:988` `getDates`: percorre `EXIF_DATE_TAGS` (`:46-59`, 11 tags em
   ordem de prioridade, incluindo `SubSecDateTimeOriginal`, `CreationDate`,
   `GPSDateTime`, `SonyDateTime2` e a não-padrão `SourceImageCreateTime` do
   Insta360) via `:61` `firstDateTime`. Timezone vem de `tags.zone`; se ausente
   e o valor bruto termina em `Z`/`+00:00`, força `UTC+0` (`:1006-1010`).
   Fallback total: menor entre `fileCreatedAt`, `mtime` e `birthtime`
   (`:1033-1046`).
5. `:255` → `:564` `getImageDimensions`: **prefere `ImageSize`** (correto em
   CR2/RAF) e só cai para `ImageWidth/ImageHeight` se falhar.
6. `:259-265` geolocalização: `hasGeo` (`:1057`) rejeita NaN e `(0,0)`; se
   `reverseGeocoding.enabled`, chama `mapRepository.reverseGeocode`.
7. `:269-315` monta o registro `Insertable<AssetExifTable>`.
8. `:317-362` monta três registros auxiliares só para vídeo: `audioData`,
   `videoData`, `keyframeData`.
9. `:364-366` corrige width/height do asset se a orientação for "de lado"
   (`:208` `isOrientationSidewards`).
10. `:368-403` executa em paralelo: update do asset + `upsertExif`
    (`repositories/asset.repository.ts:188`) + `applyTagList`; opcionalmente
    extração de motion photo (`:681`) e faces do XMP (`:910`).
11. `:405` `linkLivePhotos` (`:177`) — casa foto+vídeo pelo `livePhotoCID`,
    esconde o vídeo.
12. `:409` marca `asset_job_status.metadataExtractedAt = now()`.
13. `:411` emite evento `AssetMetadataExtracted`.

Escutas do evento: `services/storage-template.service.ts:136` (enfileira
`StorageTemplateMigrationSingle`), `services/notification.service.ts:166`,
`services/workflow-execution.service.ts:301`.

### 1.3 Etapa C — encadeamento para thumbnails

`services/job.service.ts:104` `onDone` é o orquestrador de "próximo passo" (roda
para `Success` **e** `Skipped`, ver `:91`):

- `StorageTemplateMigrationSingle` com `source` `upload`/`copy` →
  `AssetGenerateThumbnails` (`:119-123`). Como o handler retorna `Skipped`
  quando o storage template está desabilitado
  (`storage-template.service.ts:144`), o encadeamento acontece sempre.
- `AssetGenerateThumbnails` concluído → `SmartSearch`, `AssetDetectFaces`, `Ocr`
  e, para vídeo, `AssetEncodeVideo` (`:170-191`), além dos eventos websocket
  `on_upload_success` / `AssetUploadReadyV2`.

### 1.4 Etapa D — geração de thumbnails (fila `thumbnailGeneration`)

`services/media.service.ts:212` `handleGenerateThumbnails`:

- carrega asset via `repositories/asset-job.repository.ts:117`
  `getForGenerateThumbnailJob` (traz exif inner-join, edits, `videoStream`,
  `format`);
- pula assets `Hidden` (`:222`);
- **Imagem** → `:312` `generateImageThumbnails`; **Vídeo ou `.gif`** → `:508`
  `generateVideoThumbnails`;
- `:239` gera também as versões "edited" quando o asset tem edições (`:841`);
- `:244` `syncFiles` (`:792`) faz o diff entre arquivos antigos e novos, faz
  upsert em `asset_file` e enfileira `FileDelete` para os órfãos;
- `:247` grava `thumbhash` no asset só se mudou.

**Caminho de imagem** (`:312`):

1. `:277` `extractOriginalImage` — se `image.extractEmbedded` e o arquivo é RAW,
   tenta extrair o JPEG/JXL embutido (`:254` →
   `repositories/media.repository.ts:75` `extract`, tenta as tags
   `JpgFromRaw2`, `JpgFromRaw`, `PreviewJXL`, `PreviewImage` **nessa ordem**) e
   **só aceita se o menor lado do preview ≥ `image.preview.size`** (`:786`
   `shouldUseExtractedImage`).
2. `:263` `decodeImage` — colorspace sRGB se `isSRGB(exif)` (`:749`: olha
   `colorspace`/`profileDescription`, senão assume sRGB para 8 bits), senão
   `image.colorspace` (default P3). **Decodifica uma vez para buffer RAW e
   reaproveita para todos os tamanhos.**
3. `:343-347` gera em paralelo: thumbhash, thumbnail e preview; `:349-387`
   fullsize quando aplicável.
4. `:391-399` copia o grupo de tags `XMP-GPano` para preview/fullsize em fotos
   360 (`ProjectionType === 'EQUIRECTANGULAR'`).

**Caminho de vídeo** (`:508`): monta dois comandos ffmpeg com `ThumbnailConfig`
(`utils/media.ts:473`) e roda `transcode` duas vezes (preview e thumbnail),
depois calcula o thumbhash a partir do arquivo de preview (`:538`).

**Thumbnail de pessoa**: `services/media.service.ts:411`
`handleGeneratePersonThumbnail` — recorta a bounding box com folga de 10%
(`:470` `getCrop`), sempre JPEG, `FACE_THUMBNAIL_SIZE = 250` (`constants.ts:66`).

### 1.5 Etapa E — transcodificação de vídeo (fila `videoConversion`)

`services/media.service.ts:569` `handleVideoConversion`:

1. `repositories/asset-job.repository.ts:339` `getForVideoConversion` — exige
   `asset_video` e `asset_exif` (inner join): **sem metadados extraídos, o job
   falha** (`media.service.ts:583`).
2. `:592` `getTranscodeTarget` decide `None | Audio | Video | All` combinando
   `isAudioTranscodeRequired` (`:679`) e `isVideoTranscodeRequired` (`:702`).
3. `:593` se `None` e não precisa remux (`:734` `isRemuxRequired`), apaga um
   `encoded_video` que exista e retorna `Skipped`.
4. `:606` `BaseConfig.create(...).getCommand(...)` (`utils/media.ts:69` / `:137`)
   devolve `{inputOptions, outputOptions, twoPass, progress}`.
5. `:615-642` cascata de fallback em erro: HW encode+HW decode → HW encode+SW
   decode → tudo em software.
6. `:646` grava `asset_file` tipo `encoded_video` apontando para
   `StorageCore.getEncodedVideoPath` (`cores/storage.core.ts:129`).

### 1.6 Etapa F (paralela) — HLS sob demanda

- API: `services/hls.service.ts:47/69/83` (`getMainPlaylist`,
  `getMediaPlaylist`, `getSegment`), constrói playlists a partir de
  `asset_keyframe` (`utils/media.ts:42` `getCodecString`, `:30` `getOutputSize`).
- Worker: `services/transcoding.service.ts:65/132/171` — sessão com lease de
  30 min (`constants.ts:233`), backpressure em 30/15 segmentos (`:223-224`),
  segmentos de 2 s (`:235`), 15 variantes (`:237-253`).
- Comunicação API↔worker por websocket/Redis pub-sub, não por fila.

---

## 2. Modelo de dados nas fronteiras

**Fronteira 1 — exiftool → Immich.** `repositories/metadata.repository.ts:26`
define `ImmichTags`, que é `Tags` do `exiftool-vendored` com ~10 campos
re-tipados porque a lib mente sobre os tipos (`FocalLength`, `Duration`,
`Description`, `ISO`, `LensModel`, `TagsList`, `Keywords`,
`HierarchicalSubject`, `RegionInfo`) mais campos Android/Insta360
(`AndroidMake`, `Device.Manufacturer`, `MotionPhoto*`,
`EmbeddedVideoFile: BinaryField`). Datas chegam como `ExifDateTime` (objeto da
lib, não `Date`).

**Fronteira 2 — ffprobe → Immich.** `types.ts:90` `VideoStreamInfo`, `:111`
`AudioStreamInfo`, `:119` `VideoPacketInfo`, `:134` `VideoFormat`, `:150`
`VideoInfo`. A conversão está em `repositories/media.repository.ts:236` `probe`
(normaliza `h265`→`hevc`, aplica DAR para corrigir width, ordena streams por
`disposition.default` e bitrate) e `:291` `probePackets` (spawn direto de
`ffprobe`, CSV de `pts,duration,flags`, contabiliza keyframes e reimplementa o
cálculo CFR do ffmpeg em `:524` `cfrOutputFrames`).

**Fronteira 3 — Immich → Postgres.** Quatro tabelas alimentadas por um único
`upsertExif` (`repositories/asset.repository.ts:188`, um
`INSERT ... ON CONFLICT` com CTEs):

- `asset_exif` (`schema/tables/asset-exif.table.ts`) — chave = `assetId`;
  ~30 colunas; `tags` é `varchar[]`; `lockedProperties` é `varchar[]` que protege
  campos editados manualmente (`lockedPropertiesBehavior: 'skip'` em
  `metadata.service.ts:389`); índice GiST
  `ll_to_earth_public(latitude, longitude)`.
- `asset_video` / `asset_audio` / `asset_keyframe`
  (`schema/tables/asset-av.table.ts`) — 1:1 com asset; `asset_keyframe` guarda
  três arrays de int (`pts`, `accDuration`, `ownDuration`).
- `asset_file` (`schema/tables/asset-file.table.ts`) — unique
  `(assetId, type, isEdited)`; `type ∈ {fullsize, preview, thumbnail, sidecar,
  encoded_video}` (`enum.ts:54`); flags `isProgressive`, `isTransparent`.
- `asset_job_status` (`schema/tables/asset-job-status.table.ts`) — apenas
  timestamps: `metadataExtractedAt`, `facesRecognizedAt`,
  `duplicatesDetectedAt`, `ocrAt`. É o "já processei isso" do sistema.
- No `asset`: `duration`, `localDateTime`, `fileCreatedAt`, `fileModifiedAt`,
  `width`, `height`, `thumbhash` (bytea).

**Fronteira 4 — pipeline de imagem.** Sharp trabalha com
`{data: Buffer, info: {width,height,channels}}` (RAW), definido em `types.ts:61`
`RawImageInfo` / `:74` `DecodeToBufferOptions` / `:79`
`GenerateThumbnailOptions`. O buffer decodificado é gerado **uma vez** e passado
com `raw: info` para thumbnail, preview, fullsize e thumbhash.

**Fronteira 5 — reverse geocode.** `repositories/map.repository.ts:30`
`ReverseGeocodeResult = {country, state, city}` (tudo `string|null`).

**Fronteira 6 — filas.** `types.ts:361` `JobItem` é uma união discriminada
`{name: JobName, data: ...}`; os payloads são mínimos
(`IEntityJob = {id, source?, notify?, force?}` em `:237`). Nada de objeto grande
trafega pelo Redis — só o UUID.

**Layout em disco.** `cores/storage.core.ts:347` `getNestedFolder`:
`<MEDIA>/<folder>/<ownerId>/<2 primeiros chars do filename>/<chars 3-4>/<filename>`.
Nome do arquivo de imagem: `<assetId>_<fileType>[_edited].<format>` (`:121`);
vídeo transcodificado `<assetId>.mp4` (`:129`); motion photo extraída
`<uuid>-MP.mp4` (`:141`).

---

## 3. Dependências externas

| Dependência | Onde entra | O que quebra sem ela |
|---|---|---|
| **exiftool** (via `exiftool-vendored ^35.20.0`, que embute o binário) | `repositories/metadata.repository.ts:85-99` — pool persistente de processos, `taskTimeoutMillis` 2 min, `-api largefilesupport=1` para arquivos >2 GB | Toda a extração. `readTags` já tem catch que devolve `{}` (`:116-119`), então o asset entra com data de arquivo e sem EXIF, mas nunca falha o job. Já `extractBinaryTag` (motion photo, preview RAW) e `writeTags` (sidecar) quebram de fato |
| **ffmpeg / ffprobe** (`fluent-ffmpeg` + `spawn('ffprobe')`) | `repositories/media.repository.ts:41`, `:291`, `:375` | Vídeos: sem probe o `handleMetadataExtraction` **lança** (não há catch em `getVideoTags`, `metadata.service.ts:1095`) → job falha. Sem ffmpeg não há thumbnail de vídeo, transcodificação nem HLS. Imagens não são afetadas, exceto `.gif` |
| **libvips / sharp `^0.34.5`** | `repositories/media.repository.ts:9`, config global em `:66-67` (`sharp.concurrency(0)`, `sharp.cache({files:0})`) | Nenhum thumbnail/preview/fullsize/thumbhash de imagem |
| **thumbhash `^0.1.1`** | `repositories/media.repository.ts:220` (import dinâmico) | Sem placeholder de carregamento |
| **geo-tz `^8.0.0`** | `repositories/metadata.repository.ts:93` — injetado como callback `geoTz` no ExifTool para inferir timezone a partir do GPS | Fotos sem tag de timezone explícita perdem o fuso |
| **i18n-iso-countries `^7.6.0`** | `repositories/map.repository.ts:2`, usado em `:169` e `:197` para converter ISO-3166 em nome em inglês | Campo `country` vira `null` |
| **Dataset GeoNames `cities500.txt`** | `constants.ts:58`; carregado em `repositories/map.repository.ts:268` | `loadCities500` **lança** se o arquivo não existir (`:271-273`), e isso propaga até `metadata.service.ts:173`, que lança `Metadata service init failed` → **o worker de microservices não sobe** |
| **`admin1CodesASCII.txt` / `admin2Codes.txt`** | `repositories/map.repository.ts:344` `loadAdmin` | Também lança se ausente (`:346-348`). Mapas `código → nome` para estado/município |
| **`ne_10m_admin_0_countries.geojson`** (Natural Earth) | `repositories/map.repository.ts:204` | Sem fallback de país para pontos no mar/deserto |
| **`geodata-date.txt`** | `repositories/map.repository.ts:55` | Usado como "versão" do dataset; se a data bate com `system_metadata.reverseGeocodingState.lastUpdate`, o import é pulado (`:58-61`) |
| **Postgres `cube` + `earthdistance`** | `repositories/map.repository.ts:155-161`, funções `ll_to_earth_public`, `earth_box`, `earth_distance`; índice GiST em `:258-263` | Reverse geocoding inteiro |
| **Postgres `unaccent` + `pg_trgm`** | `repositories/map.repository.ts:362` `createGeodataIndices` | Busca textual por lugar |
| **Redis** | `repositories/config.repository.ts:283-294` | Todas as filas |

Os arquivos de geodata **não estão no repositório**: vêm da imagem base
(`server/Dockerfile`, `FROM ghcr.io/immich-app/base-server-prod:...`) e ficam em
`/build/geodata` (`repositories/config.repository.ts:196-199`, `:338-346`,
controlado por `IMMICH_BUILD_DATA`).

---

## 4. Reverse geocoding offline — detalhamento

**Dataset:** GeoNames `cities500` (todos os lugares povoados com ≥500
habitantes), TSV. O parser em `repositories/map.repository.ts:284-302` usa as
colunas por índice: `0=geonameid, 1=name, 3=alternatenames, 4=lat, 5=lon,
7=featureCode, 8=countryCode, 10=admin1, 11=admin2, 18=modificationDate`. Filtra
fora `PPLX` (bairro/seção de cidade — exceto na Austrália) e `PPLH` (lugar
histórico) em `:286`.

**Carga:** streaming linha a linha com `highWaterMark` de 512 MB, batches de 5000
linhas, no máximo 9 inserts concorrentes "para deixar uma conexão sobrando"
(`:304-325`). O import é protegido por lock de banco `DatabaseLock.GeodataImport`
e acontece com a fila `metadataExtraction` **pausada**
(`services/metadata.service.ts:166-168`). A estratégia de recriação é *swap de
tabela*: cria `geodata_places_tmp` com `LIKE ... INCLUDING ALL EXCLUDING
INDEXES`, dropa a original, renomeia (`:249-257`), e só depois cria os índices
(GiST antes da carga, GIN/PK depois).

**Consulta** (`repositories/map.repository.ts:148`), duas etapas:

1. `earth_box(ll_to_earth_public(lat,lon), 25000) @> ll_to_earth_public(latitude,
   longitude)` — caixa de 25 km (`constants.ts:59` `reverseGeocodeMaxDistance =
   25_000`), ordenado por `earth_distance` real, `LIMIT 1`. Retorna
   `{country: nome do countryCode, state: admin1Name, city: name}`.
2. Se vazio, cai para `naturalearth_countries` com teste de contenção poligonal
   `coordinates @> point(lon, lat)` (`:179-184`) — devolve só o país, `state` e
   `city` ficam `null`.

**Precisão:** granularidade de cidade, "cidade mais próxima dentro de 25 km com
≥500 habitantes". Não há geocodificação de endereço/rua. O nome vem sempre em
inglês (`getName(code, 'en')`). O `state` é o nome do admin1 do *lugar
encontrado*, não necessariamente o do ponto consultado.

---

## 5. Thumbnails, preview e transcodificação — parâmetros concretos

**Tamanhos e formatos** (defaults em `config.ts:369-390`, editáveis pelo admin):

| Variante | Formato | Tamanho | Qualidade | Progressive |
|---|---|---|---|---|
| `thumbnail` | WebP | 250 | 80 | false |
| `preview` | JPEG | 1440 | 80 | false |
| `fullsize` | JPEG | (sem resize) | 80 | false, `enabled: false` |
| face/pessoa | JPEG fixo | 250 | igual thumbnail | false |

`colorspace` default P3; `extractEmbedded` default false.

**Semântica do resize:** `repositories/media.repository.ts:214` usa
`fit: 'outside'` + `withoutEnlargement: true` — **o menor lado** vira `size` e a
imagem nunca é ampliada. Chroma subsampling é 4:4:4 se quality ≥ 80, senão 4:2:0
(`:180`).

**Quando o `fullsize` é gerado** (`services/media.service.ts:281-285`): se
(`fullsize.enabled` **ou** a foto é 360º equirretangular) **e** o original não é
web-supported (RAW, HEIC, TIFF, JXL...), **ou** o asset tem edições. Se o preview
embutido do RAW já é JPEG e grande o suficiente, ele é gravado como fullsize
direto e recebe só EXIF essencial via exiftool (`:368-386`).

**Transparência:** detectada por `sharp.metadata().hasAlpha`
(`repositories/media.repository.ts:413`), persistida em
`asset_file.isTransparent`, e gera warning se o formato configurado for JPEG
(`services/media.service.ts:871`).

**Thumbnail de vídeo** (`utils/media.ts:473` `ThumbnailConfig`): filtros
`fps=12` → `thumbnail=12` → `select=gt(scene,0.1)...` → `trim=end_frame=2` →
`reverse`, com `-skip_frame nointra` (exceto MPEG-TS) e escala Lanczos (`:534`).
Saída `-frames:v 1 -update 1`.

**Política de transcodificação** (`enum.ts` `TranscodePolicy`, aplicada em
`services/media.service.ts:702`):

- `Disabled` — nunca; `All` — sempre; `Required` (default) — codec fora de
  `acceptedVideoCodecs` **ou** pixel format não-4:2:0; `Optimal` — o anterior +
  resolução maior que o alvo; `Bitrate` — o `Required` + bitrate acima de
  `maxBitrate`.
- Defaults ffmpeg (`config.ts:229-256`): CRF 23, preset `ultrafast`, alvo H.264,
  `acceptedVideoCodecs: [h264]`, alvo de áudio AAC, `targetResolution: '720'`,
  `maxBitrate: '0'` (desligado), `twoPass: false`, `accel: disabled`.
- Aceleração de hardware: NVENC, QSV, VAAPI, RKMPP, cada uma com classes
  SW-decode e HW-decode em `utils/media.ts:639-1010`; matriz de codecs em
  `constants.ts:215`.

**"Cache" e regeneração.** Não existe cache separado — os derivados são arquivos
permanentes em `<MEDIA>/thumbs/` e `<MEDIA>/encoded-video/` com linha em
`asset_file`. O que dispara regeneração:

- `AssetGenerateThumbnailsQueueAll {force:false}`
  (`repositories/asset-job.repository.ts:64` `streamForThumbnailJob`):
  reprocessa se falta thumbnail, falta preview, falta fullsize-edited de asset
  editado, `thumbhash IS NULL`, ou (com fullsize ligado) falta fullsize e o
  original é de extensão web-unsupported. Exige `asset_job_status` existir
  (metadata já rodou).
- `force: true` reprocessa tudo.
- Nightly job roda a versão `force:false` toda noite
  (`services/queue.service.ts:287`).
- Mudança de formato/tamanho na config **não** invalida nada automaticamente;
  existe a fila `migration` (`services/media.service.ts:122/157`) que
  *move/renomeia* os arquivos para o novo path/extensão sem re-encodar.
- Vídeo: `streamForVideoConversion` (`repositories/asset-job.repository.ts:314`)
  só pega assets sem `asset_file` do tipo `encoded_video`.
- `syncFiles` (`services/media.service.ts:792`) apaga fisicamente o arquivo
  antigo (via job `FileDelete`) quando o path novo difere.

---

## 6. A fila de jobs

**Stack:** BullMQ 5 sobre Redis, integrado via `@nestjs/bullmq`.

**Workers (processos):** dois tipos — `api` e `microservices`
(`server/src/workers/api.ts`, `microservices.ts`), selecionados por
`IMMICH_WORKERS_INCLUDE/EXCLUDE`. Só o `microservices` cria `Worker`s BullMQ
(`services/queue.service.ts:78-86` → `repositories/job.repository.ts:90`
`startWorkers`); o `api` só enfileira e monitora a presença do outro a cada 30 s
(`job.repository.ts:22`, `:115`).

**19 filas** (`enum.ts:792`). Concorrência default (`config.ts:273-289`):
`backgroundTask` 5, `metadataExtraction` 5, `sidecar` 5, `migration` 5, `search`
5, `notifications` 5, `library` 5, `workflow` 5, `thumbnailGeneration` 3,
`smartSearch` 2, `faceDetection` 2, `editor` 2, `videoConversion` 1, `ocr` 1,
`integrityCheck` 1. Quatro filas são forçadas a concorrência 1 e não
configuráveis (`types.ts:216`, `services/queue.service.ts:254`):
`facialRecognition`, `storageTemplateMigration`, `duplicateDetection`,
`backupDatabase`.

Os workers nascem com `concurrency: 1` (`repositories/job.repository.ts:97`) e
são reajustados em `ConfigInit`/`ConfigUpdate` (`services/queue.service.ts:93`
`updateConcurrency` → `job.repository.ts:147`).

Detalhe específico da extração: a concorrência da fila `metadataExtraction`
também controla o número de processos exiftool no pool
(`services/metadata.service.ts:154/159` →
`repositories/metadata.repository.ts:105` `setMaxProcs`).

**Descoberta de handlers:** reflexão sobre o decorator `@OnJob({name, queue})`
(`decorators.ts:157`) em `repositories/job.repository.ts:40` `setup`. Garante 1
handler por `JobName` e falha o boot se algum `JobName` estiver órfão (`:78-87`).

**Prioridade:** praticamente inexistente. `repositories/job.repository.ts:257`
`getJobOptions` é a única fonte: `PersonGenerateThumbnail` recebe `priority: 1`;
`NotifyAlbumUpdate` e `StorageTemplateMigrationSingle` recebem `jobId` (dedupe
por chave); `FacialRecognitionQueueAll`, `VersionCheck` e `DatabaseBackup` usam
`deduplication`. Todo o resto entra sem opções, em FIFO.

**Retry: não existe.** `repositories/config.repository.ts:288-290`:
`attempts: 1, removeOnComplete: true, removeOnFail: false`. Além disso,
`services/job.service.ts:85` `onJobRun` envolve o handler em try/catch e **não
relança** — emite `JobError` e segue. Do ponto de vista do BullMQ o job sempre
"completa", então nem o `attempts` chega a ser exercido. Falhas viram: log de
erro (`services/notification.service.ts:81`), contador OpenTelemetry
(`services/telemetry.service.ts:45`) e, só para `DatabaseBackup`, notificação ao
admin.

**A recuperação real é reenfileirar via `*QueueAll {force:false}`, que usa o
estado no Postgres (`asset_job_status`, existência de `asset_file`) como fonte de
verdade.**

**Enfileiramento em lote:** `queueAll` agrupa por fila e usa `addBulk`, exceto
quando há `jobId`/`deduplication` (`repositories/job.repository.ts:198-228`). Os
produtores fazem streaming do Postgres em blocos de
`JOBS_ASSET_PAGINATION_SIZE = 1000` (`constants.ts:27`), ex.
`services/metadata.service.ts:222-231`.

---

## 7. Immich-específico vs. portável (desktop local-first, Python + SQLite)

### 7.1 Portável quase 1:1 — a lógica de domínio

- **Ordem de precedência das tags de data** (`metadata.service.ts:46-59`) e a
  cascata de fallback para mtime/birthtime (`:1033-1046`). É conhecimento
  acumulado por bug report, não infraestrutura.
- **Regra sidecar-vence-mídia**, incluindo o apagamento das tags de timezone
  junto com as de data (`:591-608`).
- **HEIF: ignorar `Orientation` EXIF e usar `QuickTime:Rotation`** (`:621`,
  `:1138`).
- **Dimensões: preferir `ImageSize` a `ImageWidth/Height` em RAW** (`:564`).
- **Swap width/height quando a orientação é 90/270** (`:208`, `:364`).
- **`getBitsPerSample`** com a divisão por 3 quando o valor é per-pixel
  (`:1070`).
- **Extração de preview embutido de RAW** com a ordem
  `JpgFromRaw2 → JpgFromRaw → PreviewJXL → PreviewImage` e o critério "só use se
  o menor lado ≥ tamanho do preview" (`media.repository.ts:75`,
  `media.service.ts:786`).
- **Decodificar uma vez para RAW e derivar todos os tamanhos** desse buffer
  (`media.service.ts:340-347`) — em Python, `pyvips`/`Pillow` com um único
  decode.
- **Detecção sRGB heurística** (`media.service.ts:749`).
- **Extração de motion photo / live photo**: os três caminhos
  (`MotionPhotoVideo` binário, `EmbeddedVideoFile` binário, offset
  `MicroVideoOffset`/`ContainerDirectory` lendo do fim do arquivo) em
  `metadata.service.ts:681-733`.
- **Faces do XMP MWG (`RegionInfo`)** com a normalização de coordenadas por
  orientação (`:834` `orientRegionInfo`) — matemática pura.
- **Normalização de tags hierárquicas** (`TagsList` / `HierarchicalSubject` com
  `|`↔`/` / `Keywords`) em `:639`.
- **Thumbhash** — existe port Python.
- **Filtros ffmpeg do thumbnail de vídeo** (`utils/media.ts:510`).
- **Layout de arquivos com nesting de 2+2 chars** (`storage.core.ts:347`).
- **A ideia do `asset_job_status`**: marcar timestamps por etapa e derivar "o que
  falta processar" com uma query, em vez de manter estado de fila.
- **Reverse geocoding com GeoNames `cities500`**: o dataset é livre (CC BY), o
  parser é trivial e a consulta "vizinho mais próximo dentro de 25 km" é
  reimplementável em SQLite com R-Tree ou com um k-d tree em memória (o arquivo
  tem ~200 mil linhas — cabe em RAM). O fallback por polígono de país (Natural
  Earth) também é portável com `shapely`.
- **Timezone a partir de GPS** — `timezonefinder` é o equivalente Python de
  `geo-tz`.

### 7.2 Específico do Immich — não portar

- **BullMQ + Redis inteiro.** Para single-user local-first, a fila deve ser uma
  tabela SQLite + um pool de threads/processos. O próprio Immich não usa retry,
  prioridade nem delayed jobs de forma significativa, então a superfície
  realmente usada do BullMQ é pequena: enfileirar, concorrência por tipo de
  tarefa, pausar/retomar, contar.
- **Separação api/microservices em processos distintos** e o `watchWorkers`.
- **Toda a camada de websocket/pub-sub**
  (`repositories/websocket.repository.ts`), incluindo o protocolo HLS
  API↔worker — só existe por causa do multiprocesso/multiusuário.
- **`ownerId` em todos os caminhos, `libraryId`, `visibility`, quotas, shared
  links, partners, permissões** (`requireAccess` em toda service).
- **Postgres-específico:** `cube`/`earthdistance`, tipo `polygon` nativo,
  índices GiST/GIN com `pg_trgm`+`unaccent`, `INSERT ... ON CONFLICT` com CTEs
  encadeadas, `varchar[]`, advisory locks, streaming de cursor. Em SQLite: R-Tree
  ou tabela ordenada por geohash para o geocoding, FTS5 no lugar do trigram, JSON
  ou tabela de junção no lugar dos arrays.
- **Import de geodata por swap de tabela com `LIKE ... INCLUDING ALL`** — em
  SQLite basta reconstruir o arquivo de índice.
- **`lockedProperties`** — o *conceito* (resolver conflito entre edição do
  usuário e re-extração automática) é bom e portável; a implementação (array
  Postgres + `= ANY()` no `ON CONFLICT`) não é.
- **Configuração de sistema dinâmica com propagação por evento**
  (`ConfigInit`/`ConfigUpdate` reajustando concorrência em runtime) — overkill
  local.
- **Aceleração de hardware por NVENC/QSV/VAAPI/RKMPP com detecção de `/dev/dri`**
  — num desktop macOS o equivalente seria VideoToolbox, que o Immich nem cobre.
  A *cascata de fallback* HW→SW (`media.service.ts:615-642`) é um padrão
  portável; a matriz de encoders não.
- **Storage template / migration queue** — reorganização de disco por template
  configurável.

### 7.3 Ponto de atenção para a porta

O acoplamento mais forte do desenho do Immich é: **thumbnail depende de metadata
ter rodado** (`streamForThumbnailJob` faz inner join com `asset_job_status`) e
**transcodificação depende de `asset_video` existir** (`getForVideoConversion`
usa inner join, e o handler falha explicitamente em `media.service.ts:583`).

Ou seja: "ffprobe roda na etapa de metadados e persiste streams no banco" é
decisão arquitetural, não detalhe — evita re-probar o vídeo em cada etapa
posterior (thumbnail, transcode, HLS). Vale replicar.
