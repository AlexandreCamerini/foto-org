# Immich — modelo de dados

Fonte: `~/dev/fot`, versão 3.1.0, commit `5ad1e4e0f`. Caminhos relativos a
`server/src/` salvo indicação. Levantado em 2026-08-08.

---

## 1. Esquema resumido das tabelas centrais

O schema é declarado em TypeScript com decorators do pacote
`@immich/sql-tools` (classes `*Table` = DDL declarativo), registrado em
`schema/index.ts:88` (`@Extensions([...])`, `@Database`), com o mapa de tipos
Kysely `DB` em `schema/index.ts:180-263`.

### Núcleo do ativo

**`asset`** — `schema/tables/asset.table.ts:64`

- Identidade/propriedade: `id` (uuid gerado, `:65`), `ownerId` FK→`user` CASCADE
  (`:68`), `libraryId` FK→`library` nullable (`:113`).
- Arquivo: `originalPath` (`:74`), `originalFileName` (`:104`), `checksum` bytea
  (`:89`) + `checksumAlgorithm` (`:92`), `type` (`IMAGE|VIDEO|AUDIO|OTHER`,
  `:71`).
- Tempo: `fileCreatedAt` (`:77`, indexado), `fileModifiedAt` (`:80`),
  `localDateTime` (`:122`), `createdAt` (`:101`, indexado), `updatedAt` (`:98`).
- Estado: `isFavorite` (`:83`), `isOffline` (`:110`), `isExternal` (`:116`),
  `deletedAt` (`:119`), `status` enum (`:131`), `visibility` enum (`:137`),
  `isEdited` (`:146`).
- Derivados/relações: `thumbhash` (`:107`), `width`/`height` (`:140`,`:143`),
  `livePhotoVideoId` self-FK (`:95`), `stackId` FK→`stack` SET NULL (`:125`),
  `duplicateId` uuid solto indexado (`:128`).
- Sync: `updateId` (`:134`).

**`asset_exif`** — `schema/tables/asset-exif.table.ts:22` — 1:1 com `asset` via
PK=`assetId` (`:23`).

- Datas: `dateTimeOriginal` (`:44`), `modifyDate` (`:47`), `timeZone` varchar
  (`:89`).
- GPS/lugar: `latitude`/`longitude` (`:62`,`:65`), `city` (indexado, `:68`),
  `state` (`:71`), `country` (`:74`).
- Câmera/óptica: `make`, `model`, `lensModel`, `fNumber`, `focalLength`, `iso`,
  `exposureTime`, `orientation`, `profileDescription`, `colorspace`,
  `bitsPerSample`, `projectionType`, `fps` (`:26-101`).
- Semântica do usuário: `description` (`:77`), `rating` (`:107`), `tags` text[]
  (`:110`).
- Agrupamento: `livePhotoCID` (indexado, `:86`), `autoStackId` (indexado,
  `:104`).
- **Proveniência: `lockedProperties` varchar[] (`:119`)** — ver §4.

**`asset_file`** — `schema/tables/asset-file.table.ts:19` — N derivados por asset
(`type`: fullsize/preview/thumbnail/sidecar/encoded_video, enum em `enum.ts:54`);
único por `(assetId, type, isEdited)` (`:17`); flags `isEdited`, `isProgressive`,
`isTransparent` (`:41-48`).

**`asset_metadata`** — `schema/tables/asset-metadata.table.ts:24` — key/value
jsonb por asset, PK `(assetId, key)`.

**`asset_edit`** — `schema/tables/asset-edit.table.ts:34` — edições **não
destrutivas** como lista ordenada: `action` (crop/rotate/mirror,
`dtos/editing.dto.ts:4`), `parameters` jsonb, `sequence` int único por asset
(`:33`).

**`asset_job_status`** — `schema/tables/asset-job-status.table.ts:5` — timestamps
de pipeline por asset (`metadataExtractedAt`, `facesRecognizedAt`,
`duplicatesDetectedAt`, `ocrAt`).

**`asset_audio` / `asset_video` / `asset_keyframe`** —
`schema/tables/asset-av.table.ts:5,23,77` — 1:1 com asset, detalhe de streams e
índice de keyframes (arrays `pts`, `accDuration`).

**`asset_ocr`** (`schema/tables/asset-ocr.table.ts:20`) — N caixas de texto por
asset com quadrilátero normalizado 0..1, `boxScore`, `textScore`, `isVisible`.
**`ocr_search`** (`schema/tables/ocr-search.table.ts:10`) — 1:1, texto
concatenado com índice GIN trigram.

**`smart_search`** — `schema/tables/smart-search.table.ts:12` — PK `assetId`,
`embedding vector(512)`, índice HNSW `clip_index`.

### Pessoas e faces

**`person`** — `schema/tables/person.table.ts:33`: `ownerId`, `name`,
`thumbnailPath`, `isHidden`, `birthDate` (com `@Check`
`birthDate <= CURRENT_DATE`, `:32`), `faceAssetId` FK→`asset_face` (foto de
capa, `:58`), `isFavorite`, `color`.

**`asset_face`** — `schema/tables/asset-face.table.ts:36`: `assetId`, `personId`
nullable (SET NULL), bounding box em pixels `boundingBoxX1..Y2` +
`imageWidth/imageHeight` de referência, **`sourceType`**
(`machine-learning|exif|manual`, `enum.ts:396`), `deletedAt` (soft delete),
`isVisible` (`:87`).

**`face_search`** — `schema/tables/face-search.table.ts:11`: PK `faceId`,
`embedding vector(512)`, HNSW `face_index`.

### Agrupamentos

**`album`** (`schema/tables/album.table.ts:18`), **`album_asset`**
(`schema/tables/album-asset.table.ts:23`, PK composta), **`album_user`**
(`schema/tables/album-user.table.ts:41`, PK `(albumId,userId)` + `role`
owner/editor/viewer, índice parcial único garantindo 1 owner, `:21`).

**`stack`** — `schema/tables/stack.table.ts:24`: `id`, `ownerId`,
`primaryAssetId` FK único (`:38`). A pertinência é invertida: fica em
`asset.stackId`.

**`memory`** — `schema/tables/memory.table.ts:26`: `type` (`on_this_day`), `data`
jsonb (`{year}`), `memoryAt`, `showAt`/`hideAt` (janela de exibição), `seenAt`,
`isSaved`, `deletedAt`. **`memory_asset`** —
`schema/tables/memory-asset.table.ts:23`.

**`tag`** — `schema/tables/tag.table.ts:18`: `userId`, `value` (único por
usuário, `:17`), `parentId` self-FK, `color`. **`tag_asset`**
(`schema/tables/tag-asset.table.ts:7`) e **`tag_closure`**
(`schema/tables/tag-closure.table.ts:5`, tabela de fecho transitivo
ancestral/descendente).

**`library`** — `schema/tables/library.table.ts:17`: `ownerId`, `importPaths`
text[], `exclusionPatterns` text[], `refreshedAt`, `deletedAt`.

### Geo de referência

**`geodata_places`** — `schema/tables/geodata-places.table.ts:28` (GeoNames:
nome, lat/lon, countryCode, admin1/admin2, `alternateNames`).
**`naturalearth_countries`** — `schema/tables/natural-earth-countries.table.ts:4`
(`coordinates polygon`).

### Infra de dados

- **`*_audit`** (tombstones): `asset_audit` (`schema/tables/asset-audit.table.ts:5`),
  `album_audit`, `album_asset_audit`, `album_user_audit`, `memory_audit`,
  `memory_asset_audit`, `stack_audit`, `person_audit`, `asset_face_audit`,
  `asset_edit_audit`, `asset_metadata_audit`, `asset_ocr_audit`, `user_audit`,
  `user_metadata_audit`, `partner_audit`.
- **`session_sync_checkpoint`** — `schema/tables/sync-checkpoint.table.ts:17`:
  `(sessionId, type)` → `ack`.
- **`version_history`** — `schema/tables/version-history.table.ts:4`;
  **`move_history`** — `schema/tables/move.table.ts:9`; **`integrity_report`** —
  `schema/tables/integrity-report.table.ts:9`
  (`untracked_file|missing_file|checksum_mismatch`).
- **`kysely_migrations`** / **`migration_overrides`** — ver §8.

---

## 2. Relacionamentos e cardinalidades

```
user 1─N asset            (asset.ownerId, CASCADE)
user 1─N library 1─N asset (asset.libraryId nullable → assets "uploaded" vs "external")
user 1─N person, tag, memory, stack, album_user

asset 1─1 asset_exif        (PK = assetId)
asset 1─1 asset_job_status | asset_audio | asset_video | asset_keyframe | smart_search | ocr_search
asset 1─N asset_file        (único por type+isEdited)
asset 1─N asset_metadata    (PK assetId,key)
asset 1─N asset_edit        (único por assetId,sequence)  → ordem = pilha de edições
asset 1─N asset_ocr
asset 1─N asset_face N─1 person   (personId nullable = face detectada não atribuída)
asset_face 1─1 face_search

asset N─1 stack        (asset.stackId; stack.primaryAssetId → asset, UNIQUE)
asset 0..1─1 asset     (livePhotoVideoId: foto still → vídeo companheiro)
asset N─N album via album_asset
asset N─N memory via memory_asset
asset N─N tag  via tag_asset;  tag N─1 tag (parentId) + tag_closure (ancestor,descendant)
album N─N user via album_user (role)
user N─N user via partner (sharedById, sharedWithId)
album+asset 1─N activity (FK composta para album_asset, activity.table.ts:32)
```

Notas de cardinalidade:

- **Duplicatas não têm tabela.** É um `asset.duplicateId uuid` compartilhado
  pelos membros do grupo (`asset.table.ts:128`); um grupo com 1 membro é limpo
  para NULL (`repositories/duplicate.repository.ts:93-110`). Grupo = "assets com
  o mesmo duplicateId".
- **Stack** é 1:N invertido (o filho aponta para a pilha); o "primário" é
  referência do pai para o filho — sem constraint garantindo coerência (TODO em
  `stack.table.ts:37`).
- **`asset_exif` é obrigatória na prática**: o time-bucket usa
  `inner join asset_exif` (`queries/asset.repository.sql:420`).

---

## 3. Data/hora, fuso, GPS e lugar

### Estratégia de tempo — três colunas com papéis distintos

| Coluna | Onde | Semântica |
|---|---|---|
| `asset.fileCreatedAt` | `asset.table.ts:77` | instante absoluto (UTC real) da captura |
| `asset.localDateTime` | `asset.table.ts:122` | **hora de parede** da captura, armazenada como se fosse UTC ("keepLocalTime") |
| `asset_exif.dateTimeOriginal` | `asset-exif.table.ts:44` | timestamptz vindo do EXIF |
| `asset_exif.timeZone` | `asset-exif.table.ts:89` | nome/offset da zona resolvida |
| `asset_exif.modifyDate` | `asset-exif.table.ts:47` | mtime do arquivo |

Derivação em `services/metadata.service.ts:988-1055`:

1. `firstDateTime(exifTags)` escolhe a melhor tag de data;
2. zona vem de `exifTags.zone` (com `zoneSource` logado); heurística para
   `Z`/`+00:00` → `UTC+0` (`:1005-1010`);
3. sem zona → assume UTC sem converter (`keepLocalTime`, `:1023`);
4. `localDateTime = dateTimeOriginal.setZone('UTC', {keepLocalTime:true})`
   (`:1031`);
5. fallback: menor entre `fileCreatedAt`, `mtime` e `birthtime` (`:1036-1045`).

**O offset é reconstruído na leitura, não armazenado:**
`localOffsetHours = (localDateTime@UTC − fileCreatedAt@UTC)/3600` no time-bucket
(`queries/asset.repository.sql:391-397`). É a decisão de modelagem mais
interessante do arquivo: guardar dois instantes e derivar o offset em vez de uma
coluna de offset.

### GPS e lugar

- Coordenadas brutas: `asset_exif.latitude/longitude` (double precision).
- Lugar **denormalizado por reverse geocoding**: `city`/`state`/`country` são
  strings copiadas de `geodata_places`, **sem FK**
  (`services/metadata.service.ts:256-264, 275-283`). Não há vínculo de
  identidade com o gazetteer — o resultado é congelado no momento da extração.
- Gate: `hasGeo()` rejeita `(0,0)` e NaN (`metadata.service.ts:1057`).
- Índice geoespacial via `cube`+`earthdistance` (não PostGIS):
  `ll_to_earth_public(lat,lon)` GiST em `asset_exif` (`asset-exif.table.ts:16`) e
  em `geodata_places` (`geodata-places.table.ts:24`). Função em
  `schema/functions.ts:73`.
- Busca por bounding box converte a caixa em círculo `earth_distance`
  (`repositories/asset.repository.ts` — helper `getBoundingCircle`, ~linha 148).

---

## 4. Proveniência: extraído do arquivo vs. editado pelo usuário

**Existe um registro de proveniência — mas é minimalista: um array de nomes de
colunas "travadas".**

- Vocabulário fechado: `database.ts:557-566` — `lockableProperties =
  ['description','dateTimeOriginal','latitude','longitude','rating','timeZone','tags']`.
- Coluna: `asset_exif.lockedProperties varchar[]` (`asset-exif.table.ts:119`).

Semântica: **se o nome da coluna está em `lockedProperties`, aquele valor foi
definido pelo usuário e a re-extração de metadados não pode sobrescrevê-lo.** Não
há registro de quem, quando, nem de qual era o valor original.

Mecânica:

- `upsertExif` recebe `lockedPropertiesBehavior: 'override' | 'append' | 'skip'`
  (`repositories/asset.repository.ts:141`, implementação em `:188-300`). Com
  `'skip'`, cada coluna vira um
  `CASE WHEN 'col' = ANY(lockedProperties) THEN <valor atual> ELSE excluded.<col> END`
  (`:259-263`) — o *skip* é feito coluna a coluna **dentro do UPSERT**.
- Extração de metadados sempre usa `'skip'` (`services/metadata.service.ts:389`).
- Edições do usuário usam `'append'` + `updateLockedColumns()`
  (`utils/database.ts:999-1003`), que marca como travada toda propriedade
  presente no payload; tags idem (`services/tag.service.ts:160-161`).
- União sem duplicatas em SQL: helper `distinctLocked`
  (`repositories/asset.repository.ts:145`); `updateDateTimeOriginal` trava
  `['dateTimeOriginal','timeZone']` juntos (`:328-337`).
- **Destravamento acontece quando o valor é persistido de volta no arquivo**:
  `handleSidecarWrite` lê `lockedProperties`, escreve só esses campos no XMP
  sidecar, e chama `unlockProperties` (`services/metadata.service.ts:491-541`;
  `unlockProperties` em `repositories/asset.repository.ts:343`). O lock é,
  portanto, um **"dirty bit" de write-back para o sidecar**, não um log de
  auditoria.

Outros sinais de proveniência espalhados pelo schema:

- `asset_face.sourceType` = `machine-learning | exif | manual`
  (`asset-face.table.ts:75`; `manual` criado em
  `services/person.service.ts:690`). Faces `exif` são apagadas e recriadas a cada
  re-extração (`metadata.service.ts:968`).
- `asset.isEdited` + `asset_edit` = edições não destrutivas; a flag é mantida por
  **trigger**, não pela aplicação (`schema/functions.ts:247-276`).
- `asset_file.isEdited` distingue derivados gerados a partir do original vs. da
  versão editada.
- `asset_exif.autoStackId` guarda o BurstID/MediaUniqueID **extraído**
  (`metadata.service.ts:1063-1068`) — matéria-prima para agrupamento, separada de
  `asset.stackId`, que é a pilha **efetiva** (criada por ação de
  usuário/workflow).
- Dimensões: `asset.width/height` (efetivas, respeitam edição) vs.
  `asset_exif.exifImageWidth/Height` (do arquivo). A extração só sobrescreve as
  efetivas se `!asset.isEdited` (`metadata.service.ts:425-427`).

---

## 5. Removido vs. ausente — trash e soft delete

Três mecanismos distintos coexistem:

**(a) Lixeira em dois estágios** — `asset.status` (`active|trashed|deleted`,
`enum.ts:390`) **combinado** com `asset.deletedAt`:

- Ir para lixeira: `deletedAt = now()` + `status='trashed'`.
- Restaurar: `status='active'`, `deletedAt=null`
  (`repositories/trash.repository.ts:15-24`, `:38-52`).
- Esvaziar: `status='deleted'` — a linha **continua existindo** enquanto um job
  apaga os arquivos em disco (`trash.repository.ts:27-36`; `getDeletedIds()` faz
  stream de `status='deleted'`, `:10-12`; consumo em
  `services/trash.service.ts:48-84`).
- As consultas filtram por `deletedAt is null` (padrão) e adicionam
  `status != 'deleted'` no modo lixeira
  (`repositories/asset.repository.ts:712-713, 750-751, 899`).

**(b) Tombstones para sync incremental** — DELETE físico dispara trigger
`AFTER DELETE ... FOR EACH STATEMENT` que copia `(id, ownerId)` para `*_audit`
(`schema/functions.ts:110-121` e seguintes; declaração em `asset.table.ts:25-30`).
Guarda `pg_trigger_depth() = 0` (ou `<= 1` em tabelas de junção) para não
registrar deleções em cascata. Clientes leem deleções por `asset_audit.id`
(uuid v7, ordenável por tempo) entre dois acks:
`queries/sync.repository.sql:400-411`.

**(c) Soft delete simples** (`deletedAt` sem `status`): `album`, `library`,
`memory`, `user`, `asset_face`.

**(d) "Ausente" ≠ "removido"**: `asset.isOffline` marca arquivo de biblioteca
externa que sumiu do disco sem apagar o registro; `integrity_report` classifica
explicitamente `untracked_file` / `missing_file` / `checksum_mismatch`
(`enum.ts:404`).

**(e) Ocultar sem remover**: `asset.visibility`
(`timeline|archive|hidden|locked`, `enum.ts:1150`) — `hidden` é o vídeo de uma
Live/Motion Photo, `locked` é pasta protegida por PIN; `asset_face.isVisible`,
`asset_ocr.isVisible`, `person.isHidden`.

---

## 6. Agrupamento: como cada tipo é modelado

| Conceito | Modelo | Origem |
|---|---|---|
| Álbum | N:N explícito `album_asset` + `album_user` com papéis | 100% usuário |
| Stack/rajada | FK no filho (`asset.stackId`) + ponteiro para o primário | usuário/workflow; pista extraída em `asset_exif.autoStackId` (BurstID/BurstUUID/CameraBurstID/MediaUniqueID) |
| Live/Motion Photo | `asset.livePhotoVideoId` + `asset_exif.livePhotoCID` (indexado, para parear os dois arquivos) + vídeo com `visibility='hidden'` | extraído |
| Duplicata | atributo `asset.duplicateId` compartilhado, sem tabela | kNN sobre `smart_search.embedding`, `maxDistance: 0.6` (`repositories/duplicate.repository.ts:187`) |
| Pessoa | `person` ← `asset_face` ← kNN sobre `face_search` | ML + correções manuais |
| Memória / "on this day" | `memory` (`type`, `data={year}`, `memoryAt`, `showAt`/`hideAt`) + `memory_asset` — **materializada**, não computada na hora | job diário |

"On this day": o job `createOnThisDayMemories`
(`services/memory.service.ts:47-66`) roda por dia-alvo, chama `getByDayOfYear` e
materializa uma `memory` por ano. A query gera a série de anos a partir do menor
`localDateTime` da instância e faz `LATERAL` por dia
(`queries/asset.repository.sql:104-164`) — comparando
`("localDateTime" at time zone 'UTC')::date`, exatamente a expressão do índice
`asset_localDateTime_idx`. Exige que exista thumbnail (`asset_file`), e a leitura
filtra assets de pessoas ocultas (`queries/memory.repository.sql:44-53`).

---

## 7. Índices e o que revelam sobre as consultas quentes

Todos declarados nos decorators das tabelas (`schema/tables/*.table.ts`).

**Timeline é a query mais otimizada.** Dois índices de expressão sobre
`localDateTime` (`asset.table.ts:43-50`):

- `("localDateTime" at time zone 'UTC')::date` → grade de dias / on-this-day;
- `date_trunc('MONTH', ...)` → *time buckets* mensais
  (`queries/asset.repository.sql:358-378`).

Mais o índice parcial `asset_id_timeline_notDeleted_idx` com
`WHERE visibility='timeline' AND deletedAt IS NULL` (`:58-62`) — o predicado
exato do "feed principal".

**Deduplicação/ingestão**: dois índices únicos parciais complementares sobre
`(ownerId, checksum)` quando `libraryId IS NULL` e `(ownerId, libraryId,
checksum)` quando não (`asset.table.ts:32-42`). O nome da constraint é capturado
em código para transformar violação em "já existe" (`utils/database.ts:98-102`).
`(originalPath, libraryId)` (`:51`) serve o scan de biblioteca externa.

**Busca textual sem FTS**: `pg_trgm` GIN sobre `f_unaccent(...)` em
`asset.originalFileName` (`:53`), `person.name` (`person.table.ts:20`),
`ocr_search.text`, e quatro campos de `geodata_places`. `f_unaccent` é uma função
IMMUTABLE wrapper (`schema/functions.ts:62`) — necessária porque `unaccent`
nativo não é imutável e não poderia indexar.

**Vetorial**: HNSW `ef_construction=300, m=16` em `smart_search` e `face_search`,
ambos com `synchronize:false` (gerenciados fora do diff de schema).

**Geo**: GiST sobre `ll_to_earth_public(lat,lon)`.

**Sync**: praticamente toda tabela tem `updateId` **indexado** (uuid v7 =
ordenável por tempo). O padrão de consulta é
`WHERE updateId < :ack_atual AND updateId > :ack_anterior AND ownerId = :user
ORDER BY updateId` (`queries/sync.repository.sql:413-443`) — cursor por chave,
sem OFFSET.

**Faces**: `asset_face_personId_assetId_notDeleted_isVisible_idx` parcial em
`deletedAt IS NULL AND isVisible IS TRUE` (`asset-face.table.ts:30-34`) — "fotos
desta pessoa" é quente. Alguns FKs têm `index:false` explicitamente porque um
índice composto já os cobre (`:44`, `:53`; também em `tag.table.ts:26`,
`partner.table.ts:28`).

**Índices únicos parciais como regra de negócio**: um único `owner` por álbum
(`album-user.table.ts:21-26`), um único "like" por (asset,user,album)
(`activity.table.ts:22-27`).

Uma migração inteira foi dedicada a *remover* índices redundantes:
`schema/migrations/1746636476623-DropExtraIndexes.ts`.

---

## 8. Versionamento de schema

Três camadas:

1. **Schema declarativo** — classes `*Table` são a fonte da verdade. O CLI
   `sql-tools migrations generate` **difa** as classes contra o banco e gera a
   migração (`server/package.json:29-33`).
2. **Migrações Kysely** — 90 arquivos em `schema/migrations/`, nomeados
   `<timestamp>-<Nome>.ts`, cada um com `up`/`down` em SQL cru. Executadas no
   boot por `Migrator` com `migrationTableName: 'kysely_migrations'` e lock table
   dedicada (`repositories/database.repository.ts:515-527`), sob advisory lock
   `DatabaseLock.Migrations` (`services/database.service.ts:67`).
   `allowUnorderedMigrations` só em dev. Downgrade é detectado explicitamente e
   recusado com mensagem clara (`database.repository.ts:387-394`).
3. **Detecção de drift** — após migrar, compara schema real vs. declarado e loga
   divergências (`services/database.service.ts:118-127`; comando
   `immich-admin schema-check`). A tabela `migration_overrides` armazena o DDL
   *legado* de funções/triggers/índices como jsonb, para que o diff não tente
   "consertar" objetos criados antes da adoção do sql-tools.

Além disso: `version_history` registra a versão do app por upgrade
(`version-history.table.ts:4`, uso em `services/version.service.ts:48`); o boot
valida faixa de Postgres (`>=14.0.0`) e da extensão vetorial
(`vchord >=0.3 <2` ou `pgvector >=0.5 <1`) em `constants.ts:23-37`, dropando a
extensão vetorial não usada.

E o SQL é versionado como artefato: `queries/*.sql` são **gerados** a partir dos
repositórios (`server/src/bin/sync-sql.ts`) e commitados — todo PR mostra o SQL
efetivo que mudou.

---

## 9. Específico do Immich vs. portável para SQLite single-user

### Fortemente acoplado a Postgres (não portável)

| Recurso | Onde | Substituto em SQLite |
|---|---|---|
| `vector(512)` + HNSW (pgvector/VectorChord) | `smart-search.table.ts:5`, `face-search.table.ts:5` | `sqlite-vec` / FAISS / índice externo |
| `cube` + `earthdistance` + GiST | `asset-exif.table.ts:16`, `functions.ts:73` | R-Tree do SQLite ou geohash |
| `pg_trgm` GIN + `unaccent` | 7 índices | FTS5 (+ `unicode61 remove_diacritics=2`) |
| Triggers PL/pgSQL statement-level com `REFERENCING OLD TABLE` e `pg_trigger_depth()` | `schema/functions.ts` inteiro | triggers row-level do SQLite (sem transition tables, sem depth) — a lógica de "não auditar cascatas" precisa ir para a aplicação |
| `uuid v7` gerado no banco (`immich_uuid_v7`) para `updateId`/`createId` | `functions.ts:3`, `decorators.ts:13-19` | gerar na aplicação |
| Arrays nativos (`text[]`, `varchar[]`, `integer[]`) | `lockedProperties`, `tags`, `importPaths`, `asset_keyframe.pts` | JSON |
| ENUM types | `schema/enums.ts` | TEXT + CHECK |
| `jsonb` com operadores | `memory.data`, `asset_edit.parameters`, `asset_metadata.value` | JSON1 |
| Índices parciais e de expressão | vários | **suportados no SQLite** ✔ |
| `polygon` | `naturalearth_countries` | — |
| Advisory locks, `clock_timestamp()`, streaming de cursor | `database.repository.ts` | — |

### Específico do modelo multiusuário (descartável em single-user)

`ownerId` em ~toda tabela; `album_user` + papéis; `partner`;
`shared_link`/`shared_link_asset`; `activity` (comentários/likes); quotas em
`user`; `api_key`; `session` + `session_sync_checkpoint`; toda a família
`*_audit` (existe para o **sync delta multi-dispositivo**); `notification`;
`user_metadata`. Os índices únicos `(ownerId, checksum)` viram `(checksum)`.

### Diretamente portável — o "núcleo de catálogo"

`asset` (menos `ownerId`), `asset_exif`, `asset_file`, `asset_job_status`,
`asset_metadata`, `asset_edit`, `asset_audio/video/keyframe`, `asset_ocr`,
`person`, `asset_face`, `album`+`album_asset`, `stack`, `tag`+`tag_asset`+
`tag_closure`, `memory`+`memory_asset`, `library`, `geodata_places`,
`move_history`, `integrity_report`, `version_history`, `kysely_migrations`. Os
índices de expressão sobre `localDateTime` funcionam igual no SQLite (com a
função de data adaptada).

---

## 10. Decisões de modelagem que valem para um catálogo pessoal local-first

1. **Separar `asset` (identidade + estado da app) de `asset_exif` (o que o
   arquivo diz)** com 1:1 por PK compartilhada. Torna óbvio o que é fato do
   arquivo e o que é fato do catálogo, e mantém a tabela quente estreita.

2. **Três representações de tempo, offset derivado.** `fileCreatedAt`
   (instante), `localDateTime` (hora de parede como pseudo-UTC), `timeZone`
   (string). O offset nunca é coluna: sai da diferença entre as duas
   (`asset.repository.sql:391-397`). É o que permite indexar
   `("localDateTime" at time zone 'UTC')::date` e ordenar a timeline pela hora
   que a pessoa viveu, não pela hora absoluta.

3. **`lockedProperties` como proveniência barata.** Um array de nomes de coluna
   resolve "não sobrescreva o que eu editei" com uma coluna só, e serve de fila
   de write-back para o sidecar XMP. Limitações: não guarda valor anterior, não
   guarda origem nem timestamp, e o vocabulário é fechado (7 campos). Para
   desfazer ou explicar, é preciso uma tabela
   `field_provenance(assetId, field, value, source, confidence, at)` — mas o
   padrão "lock array + `CASE WHEN ANY(...)` no UPSERT" é o ponto de partida
   certo.

4. **`sourceType` no dado inferido, não flag booleana.**
   `asset_face.sourceType ∈ {machine-learning, exif, manual}` permite
   recomputar/apagar em massa só o que veio da ML, preservando o manual. Mesmo
   princípio vale para tags, lugares e datas inferidas.

5. **Edições não destrutivas como lista ordenada de operações** (`asset_edit`
   com `sequence`), com o original intocado e os derivados marcados por
   `asset_file.isEdited`. A flag `asset.isEdited` é mantida por trigger a partir
   da existência de linhas — a fonte da verdade é a lista, o booleano é cache.

6. **Delete em dois estágios: `deletedAt` (lixeira, reversível) e
   `status='deleted'` (marcado para expurgo físico, ainda reversível-em-banco).**
   O trabalho de I/O é assíncrono e idempotente; a linha só some depois. Em
   local-first isso evita o pior caso: apagar arquivo antes de o índice
   concordar.

7. **Distinguir "ausente" de "removido".** `isOffline` + `integrity_report` com
   três tipos nomeados. Um catálogo local-first sobre pastas que o usuário mexe
   *precisa* disso — arquivo sumido não é arquivo apagado.

8. **Tombstones em tabelas separadas com PK uuid v7.** Se algum dia houver sync
   (ou só "desfazer"), `*_audit` + cursor `updateId` dá sincronização incremental
   sem full-scan e sem coluna `dirty`. O uuid v7 faz "ordenado por tempo" e
   "chave única" serem a mesma coluna.

9. **Fatos extraídos e agrupamentos efetivos em campos diferentes.**
   `autoStackId` (BurstID lido do arquivo) ≠ `stackId` (pilha que existe).
   `livePhotoCID` (pista de pareamento) ≠ `livePhotoVideoId` (par confirmado).
   Sempre que houver sugestão automática, guarde a evidência num campo e a
   decisão em outro.

10. **Memórias materializadas, não views.** Gerar `memory` + `memory_asset` num
    job e guardar `showAt`/`hideAt`/`seenAt`/`isSaved` custa espaço trivial e
    torna a UI instantânea, estável entre sessões e editável pelo usuário.

11. **Grupo de duplicatas como atributo compartilhado, não tabela.**
    `duplicateId` uuid indexado + limpeza de singletons é bem mais simples que
    uma tabela de grupos, e o "resolver" é só um UPDATE.

12. **Índices parciais espelhando exatamente o predicado da tela**
    (`WHERE visibility='timeline' AND deletedAt IS NULL`) e índices de expressão
    espelhando exatamente a expressão da query. SQLite suporta os dois. É a maior
    alavanca de performance do modelo do Immich.

13. **Arquivo derivado como tabela, não colunas.**
    `asset_file(assetId, type, isEdited, path)` com unique composto escala para
    novos tipos de derivado sem migração de colunas.

14. **Lugar denormalizado sem FK ao gazetteer.** O Immich congela
    `city/state/country` como texto. Vantagem: sobrevive à atualização do
    GeoNames e ao gazetteer não estar presente. Custo: não dá para renormalizar
    nem agregar por identidade de lugar. Para um catálogo pessoal, considere
    guardar também o `geodata_places.id` resolvido.

15. **Schema declarativo + migrações geradas + drift check no boot + SQL
    commitado.** É a parte de processo mais replicável: a definição das tabelas é
    código legível, as migrações são derivadas por diff, e o app avisa quando o
    banco diverge do que o código espera.
