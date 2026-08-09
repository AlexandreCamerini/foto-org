# Immich — ingestão de arquivos e armazenamento

Fonte: `~/dev/fot`, versão 3.1.0, commit `5ad1e4e0f`. Caminhos relativos a
`server/src/` salvo indicação. Levantado em 2026-08-08.

---

## 1. Fluxo de ponta a ponta

### 1.A Caminho A: upload via HTTP (assets "internos")

**A1. Pré-checagem de duplicata, antes de subir bytes.** Dois mecanismos,
ambos por checksum SHA-1 **calculado no cliente**:

- Header `x-immich-checksum` no próprio POST:
  `middleware/asset-upload.interceptor.ts:18-25` chama
  `AssetMediaService.getUploadAssetIdByChecksum`
  (`services/asset-media.service.ts:46-57`) → se achar, devolve
  `200 {status: DUPLICATE, id}` e **curto-circuita** o multer (o corpo nem é
  lido).
- Endpoint em lote `POST /assets/bulk-upload-check`
  (`services/asset-media.service.ts:318-346`), usa
  `assetRepository.getByChecksums` (`repositories/asset.repository.ts:664-672`)
  e responde `ACCEPT` ou `REJECT/DUPLICATE` (com flag `isTrashed`) por item.

**A2. Recepção multipart com hash em streaming.**
`middleware/file-upload.interceptor.ts:54-68` — multer com *custom storage
engine*, não o disco do multer.

- `fileFilter` (`:89-95`) → `canUploadFile`
  (`services/asset-media.service.ts:59-89`): valida extensão contra
  `mimeTypes.isAsset/isSidecar/isProfile`.
- `_handleFile` (`middleware/file-upload.interceptor.ts:97-144`):
  gera `file.uuid = randomUUID()` (`:108`); destino =
  `getUploadFolder()` + `getUploadFilename()` (`:112-115`); abre
  `createWriteStream` (`:117`) **e** um `createHash('sha1')` (`:118`) — o hash
  é computado no mesmo passe do stream, sem reler o arquivo;
  `pipeline(file.stream, writeStream, cb)` (`:127`); rejeita arquivo de
  tamanho 0 (`:132`); callback devolve `{path, size, checksum}` (`:135-139`).
- Em `ECONNRESET`/erro de request (`:98-105`) chama `onUploadError` → enfileira
  `JobName.FileDelete` do caminho parcial
  (`services/asset-media.service.ts:117-123`).

**A3. Nome e pasta de staging** (ainda não é o storage template).

- Nome: `sanitize(`${uuid}${ext}`)` — `services/asset-media.service.ts:91-102`.
  O nome original **não** é usado no disco nesta fase; sidecar sempre vira
  `.xmp`.
- Pasta: `StorageCore.getNestedFolder(StorageFolder.Upload, userId, uuid)`
  (`services/asset-media.service.ts:104-115`, `cores/storage.core.ts:347-353`).
  Layout: `<mediaLocation>/upload/<ownerId>/<uuid[0:2]>/<uuid[2:4]>/<uuid>.<ext>`
  — fan-out de 2 níveis de 256 entradas para não estourar diretórios.

**A4. Criação da linha no banco e tratamento de duplicata exata.**
`services/asset-media.service.ts:125-227`:

1. permissão `AssetUpload` (`:133`), quota do usuário (`:140` → `:368-372`);
2. `assetRepository.create(...)` (`:149-167`) com `checksum: file.checksum`,
   `checksumAlgorithm: sha1File`, `originalPath` (staging), `libraryId: null`;
3. sidecar → `upsertFile({type: Sidecar})` (`:174-178`) + `utimes` (`:179`);
4. `utimes(originalPath, now, fileModifiedAt)` (`:181`) — preserva o mtime
   declarado pelo cliente;
5. `upsertExif({fileSizeInByte: file.size})` (`:182-185`);
6. enfileira `JobName.AssetExtractMetadata {id, source:'upload'}` (`:187`);
7. emite evento `AssetCreate` (`:193`).

**Duplicata exata é detectada pelo banco, não por consulta prévia.** O índice
único parcial `UQ_assets_owner_checksum` em
`(ownerId, checksum) WHERE libraryId IS NULL`
(`schema/tables/asset.table.ts:31-37`) faz o INSERT falhar. O `catch`
(`:196-226`):

- **sempre** enfileira `FileDelete` do arquivo recém-escrito (`:198-201`);
- se `isAssetChecksumConstraint(error)` (`utils/database.ts:98-102`, compara
  `constraint_name`), busca o id existente e responde `200 DUPLICATE`
  (`:204-217`);
- caso contrário, remove a linha órfã e propaga o erro (`:220-225`).

Há um segundo índice único
`(ownerId, libraryId, checksum) WHERE libraryId IS NOT NULL`
(`schema/tables/asset.table.ts:38-42`) — duplicata é escopada **por usuário e
por biblioteca**.

**A5. Contabilidade de quota.** `services/user.service.ts:240-245` escuta
`AssetCreate` e faz `updateUsage(ownerId, +file.size)`. Só para uploads.

### 1.B Caminho B: bibliotecas externas (assets in-place)

**B1. Descoberta por crawl agendado.**

- Cron por biblioteca em `services/library.service.ts:45-68`
  (`CronJob.LibraryScan`, default `EVERY_DAY_AT_MIDNIGHT`, `config.ts:410-418`).
- `handleQueueSyncFiles` (`services/library.service.ts:632-700`):
  - valida cada `importPath` (`validateImportPath`, `:295-334`): rejeita paths
    dentro do media location (`StorageCore.isImmichPath`,
    `cores/storage.core.ts:149-157`), exige absoluto, exige diretório, exige
    `R_OK`;
  - `storageRepository.walk({...take: 10_000})` (`:659-664`) — gerador
    assíncrono em lotes (`repositories/storage.repository.ts:238-267`), usando
    `fast-glob.globStream` com glob montado a partir de
    `mimeTypes.getSupportedFileExtensions()` (`:283-287`);
  - **filtro de já-conhecidos**:
    `assetRepository.filterNewExternalAssetPaths(libraryId, batch)`
    (`repositories/asset.repository.ts:1091-1112`) — `unnest(paths)` +
    `NOT EXISTS` contra `originalPath`. É a chave da dedup de bibliotecas:
    **caminho, não conteúdo**;
  - enfileira `LibrarySyncFiles` por lote com `progressCounter` (`:678-685`);
  - grava `library.refreshedAt = now()` no fim (`:697`).

**B2. Importação de um lote.** `handleSyncFiles`
(`services/library.service.ts:250-293`) → `processEntity` por path (`:414-433`):

- `stat()` do arquivo;
- `checksum = sha1("path:" + assetPath)`, `checksumAlgorithm: sha1Path`
  (`:421-422`) — **não é hash de conteúdo**; é um hash do caminho, só para
  satisfazer a coluna NOT NULL e o índice único. O enum documenta isso e o
  marca como *deprecated* (`enum.ts:47-52`);
- `fileCreatedAt = fileModifiedAt = localDateTime = stat.mtime`;
- `isExternal: true`, `originalPath` = caminho real no disco do usuário;
- `assetRepository.createAll(...)` em chunks de 4000
  (`repositories/asset.repository.ts:449-453`);
- emite `AssetCreate` por asset (`:284-288`) e chama `queuePostSyncJobs` →
  `SidecarCheck` (`:435-445`).

**B3. Watcher de filesystem (opt-in, default off).**

- `library.watch.enabled` default `false` (`config.ts:415-417`).
- `LibraryService.watch` (`services/library.service.ts:89-162`):
  - `picomatch` com as extensões suportadas + `exclusionPatterns` da library
    (`:103-106`);
  - `storageRepository.watch` = **chokidar**
    (`repositories/storage.repository.ts:269-279`), com `ignoreInitial: true` e
    `awaitWriteFinish: {stabilityThreshold: 5000, pollInterval: 1000}`
    (`services/library.service.ts:133-140`) — espera 5 s de estabilidade antes
    de considerar o arquivo pronto, evitando ingerir arquivo meio-copiado;
  - `add`/`change` → job `LibrarySyncFiles`; `unlink` → `LibraryRemoveAsset`
    (`:111-129`);
  - concorrência multi-processo: só **um** microservice roda o watcher,
    garantido por `databaseRepository.tryLock(DatabaseLock.Library)` = advisory
    lock 1337 do Postgres (`:52`).
- Remoção: `handleAssetRemoval` (`:702-714`) resolve
  `getByLibraryIdAndOriginalPath` e faz `assetRepository.remove` (delete da
  linha; o arquivo é do usuário, não é apagado).
- Padrões de exclusão default na criação (`:238-245`): `@eaDir`, `._*`,
  `#recycle`, `#snapshot`, `.stversions`, `.stfolder`.

**B4. Reconciliação de assets existentes (online/offline).**
`handleQueueSyncAssets` (`:716-794`) + `handleSyncAssets` (`:494-591`) +
`checkExistingAsset` (`:593-630`):

- SQL em massa marca offline quem saiu do import path ou caiu em exclusão
  (`detectOfflineExternalAssets`, `repositories/asset.repository.ts:1064-1089`);
- por lote de 10k ids: `stat()` de cada; ausente → `OFFLINE`;
  `stat.mtime !== asset.fileModifiedAt` → `UPDATE` (re-enfileira sidecar +
  metadata); offline que voltou → `CHECK_OFFLINE` → online.
- **Detecção de mudança em biblioteca externa é por mtime, não por hash.**

### 1.C Pipeline pós-ingestão (comum aos dois caminhos)

Encadeamento explícito em `JobService.onDone` (`services/job.service.ts:104-263`),
disparado quando o handler retorna `Success` **ou** `Skipped` (`:91-93`):

```
SidecarCheck            -> AssetExtractMetadata                (job.service.ts:106-109)
AssetExtractMetadata    -> evento AssetMetadataExtracted       (metadata.service.ts:411-415)
  evento                -> StorageTemplateMigrationSingle      (storage-template.service.ts:136-139)
StorageTemplateMigrationSingle (se source 'upload'|'copy')
                        -> AssetGenerateThumbnails             (job.service.ts:119-124)
AssetGenerateThumbnails -> SmartSearch + AssetDetectFaces + Ocr
                           (+ AssetEncodeVideo se vídeo)       (job.service.ts:170-191)
SmartSearch (source upload) -> AssetDetectDuplicates           (job.service.ts:254-259)
SidecarWrite            -> AssetExtractMetadata (source 'sidecar-write')
                                                               (job.service.ts:111-117, 302-308)
```

**C1. Descoberta de sidecar.** `handleSidecarCheck`
(`services/metadata.service.ts:439-478`); candidatos em `getSidecarCandidates`
(`:543-561`): sidecar já registrado, `<original>.xmp`, `<original sem ext>.xmp`.
Grava/apaga a linha `asset_file` tipo `sidecar`.

**C2. Extração de metadados.** `handleMetadataExtraction`
(`services/metadata.service.ts:236-416`) — detalhado no mapa 02. Checkpoint ao
fim: `upsertJobStatus({metadataExtractedAt: now})` (`:406`) na tabela
`asset_job_status`.

**C3. Live photo / motion photo — derivado que vira asset de primeira classe.**

- Pareamento de Live Photo iOS por `livePhotoCID` (ContentIdentifier):
  `linkLivePhotos` (`:177-206`) → `findLivePhotoMatch`
  (`repositories/asset.repository.ts:~1030`); o vídeo vira `visibility: Hidden`
  e sai dos álbuns.
- Motion photo Android/Samsung: `applyMotionPhotos`
  (`services/metadata.service.ts:681-825`):
  - extrai o vídeo embutido (tag binária `MotionPhotoVideo`/`EmbeddedVideoFile`,
    ou fatia byte-range a partir de `ContainerDirectory`/`MicroVideoOffset`)
    (`:706-724`);
  - `sha1` **do buffer** (`:725`), procura asset com esse checksum (`:728`),
    cria se não existir com
    `originalPath = StorageCore.getAndroidMotionPath(asset, uuid)`
    (`cores/storage.core.ts:141-143`);
  - tolera a corrida de INSERT via `isAssetChecksumConstraint` (`:750-760`);
  - **só escreve no disco se o arquivo não existir** (`:807-816`) —
    `checkFileExists` antes de `createFile`, que usa flag `'wx'`
    (`repositories/storage.repository.ts:74-76`), ou seja, falha se já existir.

**C4. Storage template — mover o original para o destino final.**
`services/storage-template.service.ts`.

- **Compilação**: Handlebars, compilado uma vez em `ConfigInit`/`ConfigUpdate`
  (`:92-104`), com `strict: true` (`:394`) e flags
  `needsAlbum`/`needsAlbumMetadata` derivadas por `includes('album')` para
  evitar queries desnecessárias (`:395-396`).
- **Validação de config**: renderiza com um asset fake antes de aceitar
  (`:106-130`).
- **Desligado por padrão**: `storageTemplate.enabled = false`, template default
  `{{y}}/{{y}}-{{MM}}-{{dd}}/{{filename}}` (`config.ts:364-368`). Se desligado,
  o original **fica no `upload/<uuid>` para sempre** — o path de staging *é* o
  path definitivo.
- **Tokens** (`render`, `:400-430`): `filename`, `ext`, `filetype` (IMG/VID),
  `filetypefull`, `assetId`, `assetIdShort`, `album`, `make`, `model`,
  `lensModel`, mais tokens de data Luxon
  (`y,yy,M,MM,MMM,MMMM,d,dd,W,WW,h,hh,H,HH,m,mm,s,ss,SSS`) e
  `album-startDate-<token>`/`album-endDate-<token>`. 21 presets em `:35-57`.
- **Raiz**: `StorageCore.getLibraryFolder({id, storageLabel})` =
  `<mediaLocation>/library/<storageLabel || userId>` (`cores/storage.core.ts:109-111`).
- **Sanitização e normalização** (`getTemplatePath`, `:262-389`):
  - `sanitize-filename` no basename (`:274`) e no nome de álbum, com remoção de
    `.` repetidos (`:410`);
  - extensão em minúsculas e canonicalizada: `jpeg|jpe→jpg`, `tif→tiff`,
    `3gpp→3gp`, `mpeg|mpe→mpg`, `m2ts|m2t→mts` (`:278-302`);
  - `//` colapsado (`:429`);
  - **guarda de path traversal**: se `fullPath` não começa com `rootPath`,
    aborta e devolve o path original (`:341-344`).
- **Como evitam sobrescrever** (`:372-382`): loop `while(true)` com
  `checkFileExists`; a cada colisão incrementa e tenta `<fullPath>+N.<ext>`
  (`FullSizeRender+1.heic`, `+2`, …). Não é atômico (TOCTOU), mas roda sob
  advisory lock global.
- **Idempotência do sufixo** (`:350-370`): se o `source` já é
  `<fullPath>+<digits>.<ext>`, considera já migrado e não faz nada — evita
  `+1+1+1`.
- **Assets externos e motion videos são isentos** (`:222-226`).
- **Lock**: toda a movimentação roda dentro de
  `databaseRepository.withLock(DatabaseLock.StorageTemplateMigration)` =
  advisory lock 420 (`:228`), serializando globalmente.
- **Dedup de job**: `StorageTemplateMigrationSingle` usa `jobId = assetId` no
  BullMQ (`repositories/job.repository.ts:264-266`).
- **Migração em massa**: `handleMigration` (`:173-213`) limpa histórico de moves
  órfãos, faz stream de todos os assets, e no fim `removeEmptyDirs` na pasta
  `library`.

**C5. O move em si — o mecanismo de retomada.** `StorageCore.moveFile`
(`cores/storage.core.ts:194-270`), com jornal na tabela `move_history`:

1. No-op se `oldPath == newPath` (`:196-198`); `mkdir -p` do destino (`:200`).
2. **Procura move pendente** para `(entityId, pathType)` (`:202`). Se existe, é
   retomada de um crash:
   - checa existência em **ambos** os paths (`:205-208`); se em nenhum, aborta
     com warn;
   - se o arquivo já está no destino, valida conteúdo
     (`verifyNewPathContentsMatchesExpected`) antes de aceitar (`:217-225`) —
     evita "adotar" um arquivo alheio que por acaso está no destino;
   - atualiza a linha com o `actualPath` observado (`:227`).
3. Senão, cria a linha `move_history` **antes** de tocar no disco (`:229`).
4. Exige `assetInfo` (size + checksum) para `pathType = Original` (`:232-235`).
5. Tenta `fs.rename` (`:240`). Se `EXDEV` (cross-device) →
   **copy → verify → utimes → unlink** (`:248-265`); se a verificação falha, o
   destino é removido e o original preservado.
6. `savePath` grava o novo caminho no banco (`asset.originalPath`,
   `asset_file.path` ou `person.thumbnailPath`) (`:268`, `:321-345`).
7. **Só então** deleta a linha de `move_history` (`:269`).

Verificação (`:272-306`): sempre compara tamanho; compara SHA-1 **apenas se**
`storageTemplate.hashVerificationEnabled` (default `true`, `config.ts:366`) e se
`assetInfo` foi fornecido.

Constraints de `move_history` (`schema/tables/move.table.ts:5-8`):
`UNIQUE(entityId, pathType)` (um move em voo por entidade) e `UNIQUE(newPath)`
(dois assets não podem mirar o mesmo destino). Limpeza: `cleanMoveHistory`
remove entradas de assets inexistentes
(`repositories/move.repository.ts:41-53`), e `cleanMoveHistorySingle` é chamada
no evento `AssetDelete` (`services/storage-template.service.ts:215-219`).

**C6. Derivados (thumbnails, preview, fullsize, vídeo transcodificado).**

- Caminho determinístico, **não** passa pelo storage template:
  `StorageCore.getImagePath` (`cores/storage.core.ts:121-127`) =
  `<media>/thumbs/<ownerId>/<id[0:2]>/<id[2:4]>/<assetId>_<fileType>[_edited].<format>`;
  vídeo em `<media>/encoded-video/<ownerId>/<..>/<assetId>.mp4` (`:129-131`).
- Geração: `handleGenerateThumbnails` (`services/media.service.ts:212-251`)
  escreve **direto no path final**, sem arquivo temporário. `ensureFolders`
  antes (`:337`, `:376`, `:578`).
- Reconciliação: `syncFiles` (`:791-839`) compara linhas `asset_file` antigas vs
  novas por `(type, isEdited)`; faz upsert das novas e enfileira `FileDelete` dos
  paths antigos que mudaram. Unique `(assetId, type, isEdited)` em
  `schema/tables/asset-file.table.ts:17`.
- Migração de derivados quando muda formato/layout: `AssetFileMigration`
  (`:157-171`) usa o mesmo `StorageCore.moveFile` (mesmo journal).
- `StorageCore.getTempPathInDir` existe (`cores/storage.core.ts:355-357`) mas
  **não tem chamador no `src`** — só testes.

**C7. Original vs. derivado.**

| | Original (upload) | Original (biblioteca externa) | Derivado |
|---|---|---|---|
| Local | `upload/…` → move p/ `library/<template>` | fica onde está, in-place | `thumbs/…`, `encoded-video/…` |
| Registro | `asset.originalPath` | `asset.originalPath` | linha em `asset_file` |
| Checksum | SHA-1 do conteúdo | SHA-1 de `"path:"+path` | nenhum |
| Renomeado/movido | sim (template) | **nunca** | sim (migração de formato) |
| Escrito | uma vez, streaming | nunca | regerável, sobrescrito |
| Deletado no `AssetDelete` | sim, se `deleteOnDisk && !isOffline` | idem (jobs de library usam `deleteOnDisk:false`) | sempre |

Deleção: `services/asset.service.ts:309-377` junta paths de
thumb/preview/fullsize/edited/encodedVideo e, **só se
`deleteOnDisk && !isOffline`**, acrescenta sidecar + original; tudo vai para
`JobName.FileDelete` (`services/storage.service.ts:135-153`, que só faz `unlink`
tolerante a ENOENT). Motion video só é apagado se nenhum outro asset o
referencia (`:349-357`). `LibraryDelete` enfileira `AssetDelete` com
`deleteOnDisk:false` (`services/library.service.ts:389`).

**C8. Bootstrap do storage e migração de media location.**
`services/storage.service.ts:46-133`:

- detecta media location (`IMMICH_MEDIA_LOCATION` → `/data` →
  `/usr/src/app/upload`) (`:23-44`);
- **mount checks**: em cada uma das 6 `StorageFolder`, escreve/lê/sobrescreve um
  arquivo sentinela `.immich` (`:155-196`) para provar que o volume está montado
  e gravável; estado persistido em `system_metadata`. Falha aqui aborta o boot
  (a menos de `ignoreMountCheckErrors`);
- **migração de prefixo de path**: compara media location atual com a salva; se
  mudou, roda `databaseRepository.migrateFilePaths(previous, current)`
  (`repositories/database.repository.ts:403`) — reescreve prefixos em massa no
  banco, **sem tocar em arquivo**. Se os samples não batem com o prefixo
  esperado, lança `InconsistentMediaLocation`.

---

## 2. Modelo de dados nas fronteiras

**HTTP → interceptor.** `AssetMediaCreateDto` (`dtos/asset-media.dto.ts:47-57`),
multipart: `assetData` (binário), `sidecarData` (opcional), `fileCreatedAt`,
`fileModifiedAt`, `duration`, `filename`, `isFavorite`, `visibility`,
`livePhotoVideoId`, `metadata[]`. Header opcional `x-immich-checksum`.

**Interceptor → service.** `ImmichFile` (`types.ts:486-490`) =
`Express.Multer.File` + `uuid` + `checksum: Buffer`. `UploadFile` (`:492-497`) =
`{uuid, checksum, originalPath, originalName, size}`, normalizado por
`mapToUploadFile` (`utils/asset.util.ts:190-198`), incluindo o fix de encoding
`latin1 → utf8` no `originalname` do multer (`:195`).

**Service → banco.** `Insertable<AssetTable>` (`schema/tables/asset.table.ts`).
Campos-chave: `checksum: bytea`, `checksumAlgorithm: enum('sha1'|'sha1-path')`,
`originalPath: text`, `originalFileName`, `isExternal`, `isOffline`,
`libraryId`, `livePhotoVideoId`, `visibility`, `status`, `thumbhash: bytea`,
`width/height`, `duplicateId`.

**Service → fila.** União discriminada `JobItem` (`types.ts:~370-400`). Payloads
são **JSON serializável** — só ids e strings, nunca Buffers:

- `{id, source?: 'upload'|'copy'|'sidecar-write'}` para jobs por-asset;
- `{libraryId, paths: string[], progressCounter?, totalAssets?}` para
  `LibrarySyncFiles`;
- `{libraryId, importPaths, exclusionPatterns, assetIds, progressCounter,
  totalAssets}` para `LibrarySyncAssets`;
- `{files: string[]}` para `FileDelete`; `{force: boolean}` para `*QueueAll`.

**StorageCore.** `MoveRequest` (`cores/storage.core.ts:26-35`) =
`{entityId, pathType, oldPath, newPath, assetInfo?: {sizeInBytes, checksum}}`.
Persistido como linha `move_history {entityId, pathType, oldPath, newPath}`.

**Template.** `RenderMetadata`
(`services/storage-template.service.ts:64-74`) → `Record<string,string>` →
string de path relativa.

**Eventos internos** (`repositories/event.repository.ts`): `AssetCreate
{asset, file?}`, `AssetMetadataExtracted {assetId, userId, source}`,
`AssetHide`, `AssetDelete {assetId, userId}`, `ConfigInit/ConfigUpdate/
ConfigValidate`, `JobRun/JobStart/JobSuccess/JobError/JobComplete`.

---

## 3. Dependências externas

| Dependência | Onde | O que quebra sem ela |
|---|---|---|
| **PostgreSQL** (`pg`, `postgres`, `kysely`, `nestjs-kysely`) | tudo | Índices únicos parciais (dedup por checksum), advisory locks (`repositories/database.repository.ts:443-484`), `unnest()` para filtro de paths em lote, arrays nativos, `bytea`, streaming de cursores |
| **Redis + BullMQ** | `repositories/job.repository.ts` | Toda a pipeline assíncrona. O upload síncrono ainda gravaria arquivo e linha, mas o asset ficaria sem EXIF/thumb e no path de staging |
| **multer** | `middleware/file-upload.interceptor.ts` | Parsing multipart e o hook de storage onde o SHA-1 é calculado em streaming |
| **exiftool-vendored** | `repositories/metadata.repository.ts` | EXIF, datas, GPS, orientação, `livePhotoCID`, motion photos, tags, escrita de sidecar |
| **ffmpeg/ffprobe** | media/transcoding | Duração, codecs, keyframes, thumbnails de vídeo, transcode |
| **sharp** + **thumbhash** | `repositories/media.repository.ts` | Derivados de imagem e o placeholder |
| **chokidar** | `repositories/storage.repository.ts:269-279` | Watcher de bibliotecas externas (o crawl agendado continua) |
| **fast-glob** | `:238-267`, `:221-236` | Crawl de bibliotecas e scan de arquivos não-rastreados |
| **picomatch** | `services/library.service.ts:103,540` | Exclusion patterns |
| **handlebars** | `services/storage-template.service.ts:394` | Motor do storage template |
| **luxon** | `:416-427` | Tokens de data |
| **sanitize-filename** | `:274,410`, `asset-media.service.ts:101` | Sanitização de nome |
| **async-lock** | `database.repository.ts:445` | Lock in-process combinado com o advisory lock |
| Serviço de ML | `machine-learning/` | **Não** afeta ingestão nem storage |

---

## 4. Immich-específico vs. portável (desktop local-first, Python + SQLite)

### 4.1 Específico do Immich — descartar ou simplificar

| Aspecto | Por quê |
|---|---|
| **`ownerId` em todo lugar** | Escopo do checksum, das pastas, da quota, do template. Single-user → a chave única vira `checksum` puro |
| **Quota por usuário** (`asset-media.service.ts:368-372`) | Sem sentido local |
| **Advisory locks do Postgres** (420/1337/300) | Existem porque há N processos disputando. Local: `threading.Lock`. `tryLock(Library)` para eleger "quem roda o watcher" é problema distribuído puro |
| **BullMQ/Redis + workers separados** | Multi-processo. Local: fila em SQLite ou `asyncio.Queue` + checkpoint |
| **Captura de violação de constraint como fluxo normal** (`asset-media.service.ts:204`) | A *técnica* é substituível por `INSERT … ON CONFLICT DO NOTHING RETURNING id`. A **ideia** — deixar o banco ser a autoridade sobre unicidade, em vez de check-then-insert com corrida — é portável e vale copiar |
| **`storageLabel`, shared links, álbuns compartilhados, partners, `sync_checkpoint`** | Multi-usuário / sincronização cliente-servidor |
| **Mount checks com arquivo `.immich`** (`storage.service.ts:155-196`) | Existe porque Docker pode subir com volume não-montado. Um app desktop tem análogo válido — verificar que o volume externo está montado antes de operar. Vale portar em versão leve |
| **HTTP multipart / interceptors / DTOs / OpenAPI** | O "upload" local é seleção de arquivos. Some a etapa de staging inteira |
| **`checksumAlgorithm: sha1Path`** | Hack para satisfazer NOT NULL em assets externos. Num app local você quer **hash de conteúdo para tudo**, inclusive in-place |

### 4.2 Portável — copiar o mecanismo

**a) Hash no mesmo passe da leitura/escrita.**
`middleware/file-upload.interceptor.ts:118-140`. Em Python: `hashlib` alimentado
dentro do loop de leitura em blocos. Evita segundo passe de I/O.

**b) Unicidade delegada ao banco.** Índice único em `checksum` +
`INSERT OR IGNORE` / `ON CONFLICT`. Fecha a corrida entre threads/watcher/scan
sem lock explícito.

**c) Pré-checagem barata antes de gastar I/O.** Equivalente ao
`bulkUploadCheck` (`asset-media.service.ts:318-346`) e ao
`filterNewExternalAssetPaths` (`asset.repository.ts:1091-1112`): um `SELECT` em
lote, não um por arquivo.

**d) Fan-out de diretórios por prefixo do id.** `getNestedFolder`
(`storage.core.ts:347-353`): `<id[0:2]>/<id[2:4]>/`. Mantém diretórios pequenos
com milhões de arquivos.

**e) Template de path como config compilada e validada.**
`storage-template.service.ts:391-398` (compilação cacheada, invalidada com a
config) e `:106-130` (renderiza com dado sintético para validar antes de
aceitar). Copiar também: **guarda de path traversal** (`:341-344`),
**sanitização de nome**, **canonicalização de extensão** (`:278-302`),
**colapso de `//`** (`:429`).

**f) Anti-sobrescrita por sufixo incremental + reconhecimento do sufixo.**
`:372-382` combinado com `:350-370`. A segunda parte é o detalhe que a maioria
erra: sem ela, cada re-execução acrescenta outro sufixo. Numa reimplementação,
prefira criar com `O_EXCL` (`open(path, 'xb')` — mesma semântica do flag `'wx'`
em `storage.repository.ts:74`) em vez de `exists()` + `write`, eliminando o
TOCTOU.

**g) Journal de move em duas fases.** `storage.core.ts:194-270` +
`move_history`. O invariante: **a linha do journal é criada antes de tocar no
disco e só é apagada depois de o banco apontar para o novo path.** Na retomada,
verifica os dois lados, e se o arquivo só existe no destino, **valida
tamanho+hash antes de adotá-lo**. Em SQLite: tabela
`pending_move(entity_id, kind, old_path, new_path)` com `UNIQUE(entity_id, kind)`
e `UNIQUE(new_path)`, varrida no startup.

**h) Fallback `EXDEV`: copy → verify → utimes → unlink.** `:241-265`. Em Python
`os.rename` levanta `OSError(errno.EXDEV)` igual. `shutil.move` faz o fallback
mas **não verifica** — vale reimplementar com a verificação.

**i) Verificação de integridade com política.**
`verifyNewPathContentsMatchesExpected` (`:272-306`): tamanho sempre, hash só se
a config pedir. Separação entre checagem barata e cara.

**j) Preservação de mtime.** `utimes` após upload
(`asset-media.service.ts:181`) e após copy (`storage.core.ts:257-258`).

**k) Detecção de mudança por mtime, não por rehash.** `checkExistingAsset`
(`library.service.ts:593-630`). Barato e suficiente para varredura periódica.

**l) Estados online/offline em vez de deleção.** `isOffline` +
`AssetStatus.Trashed` (`library.service.ts:562-576`). Arquivo sumido (drive
desmontado, pasta renomeada) ≠ usuário deletou. E a lógica `CHECK_OFFLINE` que
reonlina quando o arquivo reaparece.

**m) Checkpoints em duas granularidades.**

- Por item: `asset_job_status.metadataExtractedAt` + a query
  `streamForMetadataExtraction` que só devolve `WHERE metadataExtractedAt IS
  NULL` a menos que `force` (`asset-job.repository.ts:356-369`). É retomada
  natural, sem estado extra.
- Por varredura longa: `IntegrityChecksumCheckpoint`
  (`integrity.service.ts:539,556,574`) guarda a data do último item processado;
  o stream reinicia a partir dela e o job **se auto-limita** por tempo
  (`timeLimit`) e por percentual do acervo (`percentageLimit`),
  reenfileirando-se.

**n) Streaming em lotes, nunca `SELECT *` inteiro na memória.** `walk()` gerador
com `take` (`storage.repository.ts:238-267`), `.stream()` do Kysely, chunks de
1000/10000 (`constants.ts:27-28`).

**o) `awaitWriteFinish` no watcher.** `stabilityThreshold: 5000`
(`library.service.ts:136-139`). Sem isso você ingere arquivos ainda sendo
copiados. `watchdog` em Python **não** tem isso embutido — precisa de debounce
por tamanho estável.

**p) Deleção de arquivo como job separado, idempotente, tolerante a ENOENT.**
`FileDelete` (`storage.service.ts:135-153`). Desacopla "remover do índice" de
"remover do disco" e sobrevive a re-execução.

**q) Derivados são descartáveis e o índice sabe disso.** Tabela `asset_file`
separada de `asset`, `UNIQUE(assetId, type, isEdited)`, `syncFiles` que
reconcilia e limpa órfãos.

**r) Sidecar por convenção de nome, com candidatos ordenados.**
`getSidecarCandidates` (`metadata.service.ts:543-561`), e a regra de que
**datas do sidecar têm precedência** (`:583-600`).

**s) Sentinela de raiz de mídia + migração de prefixo de path.**
`storage.service.ts:97-132`. Um app desktop vai ver o usuário mover a
biblioteca. Guardar a raiz e reescrever prefixos em massa
(`UPDATE … SET path = replace(...)`) é muito melhor do que quebrar.

**t) Isenção do template para arquivos in-place.**
`storage-template.service.ts:222-226`: assets externos nunca são movidos. Se o
app tem modo "gerenciar pastas" e modo "só indexar", esta separação precisa
existir desde o dia 1.

### 4.3 A diferença estrutural que muda o desenho

O Immich separa **staging** (`upload/<uuid>`) de **destino final**
(`library/<template>`) porque o upload chega por rede, sem nome confiável, e os
metadados que o template precisa (data EXIF, álbum, câmera) **só são conhecidos
depois** da extração — daí o template rodar como job disparado pelo evento
`AssetMetadataExtracted`, não no momento do upload.

Num app local existe o mesmo problema temporal (precisa do EXIF antes de decidir
o destino), então a arquitetura de duas fases se justifica igualmente:
**indexar primeiro no lugar de origem, mover depois**. O que se economiza é a
cópia para staging — dá para ler EXIF direto do arquivo de origem e mover uma
única vez.
