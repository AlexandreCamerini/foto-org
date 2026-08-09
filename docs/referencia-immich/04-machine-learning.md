# Immich — machine learning

Fonte: `~/dev/fot`, versão 3.1.0, commit `5ad1e4e0f`. Levantado em 2026-08-08.

> **Licença:** o diretório `machine-learning/` também é AGPLv3. Reimplementar a
> partir deste mapa é livre; copiar código contamina o projeto. Os **pesos** dos
> modelos, baixados do Hugging Face (`immich-app/*`), têm as licenças dos
> modelos originais (OpenCLIP, InsightFace), não a do Immich.

---

## 0. Topologia geral

Dois processos independentes, sem estado compartilhado:

| | `machine-learning/` (Python) | `server/src` (NestJS) |
|---|---|---|
| Papel | Inferência pura, stateless | Filas, thresholds, clusterização, persistência, UI |
| Conhece | Bytes de imagem / string de texto | Assets, usuários, Postgres, Redis |
| Porta | 3003 (`machine-learning/immich_ml/config.py:87`) | 2283 |
| Estado | Só cache de modelos em RAM + arquivos de modelo em disco | Postgres (VectorChord) + Redis/BullMQ |

Único ponto de contato: `server/src/repositories/machine-learning.repository.ts`.
O serviço ML **não tem banco, e não tem noção de "pessoa", "duplicata" ou
"usuário"** — toda a semântica está no server.

---

## 1. Contrato ML ↔ server

### Protocolo

- `POST {url}/predict`, `multipart/form-data` —
  `machine-learning.repository.ts:173`; endpoint em
  `machine-learning/immich_ml/main.py:166-181`.
- `GET {url}/ping` → `"pong"` (healthcheck) — `main.py:161-163`, consumido em
  `machine-learning.repository.ts:135`.
- `GET /` → banner (`main.py:156-158`).

### Formato do request

Dois campos de formulário:

1. `entries`: string JSON com forma
   `{ task: { type: { modelName, options } } }`. Tipos no server:
   `machine-learning.repository.ts:41-67` (`ClipVisualRequest`,
   `ClipTextualRequest`, `FacialRecognitionRequest`, `OcrRequest`). Espelho no
   ML: `immich_ml/schemas.py:100-110` (`PipelineEntry`, `PipelineRequest`),
   parsing em `main.py:132-154`. Os enums `ModelTask`
   (`clip` | `facial-recognition` | `ocr`) e `ModelType`
   (`detection`|`recognition`|`textual`|`visual`) são duplicados manualmente nos
   dois lados: `machine-learning.repository.ts:15-28` vs `schemas.py:28-40`.
2. `image` (Blob lido do disco em `machine-learning.repository.ts:236-239`)
   **ou** `text` (`:240-241`). Um dos dois é obrigatório (`main.py:178-181`).

Multipart faz spool para disco acima de 64 MiB (`main.py:40`).

### Formato do response

JSON chaveado por task, mais dimensões da imagem: `main.py:196-199`. Exemplo
lógico: `{ "facial-recognition": [ {boundingBox, embedding, score} ],
"imageWidth": …, "imageHeight": … }` (`schemas.py:88-96`).

**Detalhe importante:** os embeddings viajam como *string JSON já serializada*
(`immich_ml/models/transforms.py:79-80`, `serialize_np_array`), justamente para o
server nunca desserializar/reserializar — ele repassa a string direto ao driver
do pgvector (`search.repository.ts:459-466`).

### Pipeline com dependências

`FaceRecognizer.depends = [(DETECTION, FACIAL_RECOGNITION)]`
(`immich_ml/models/facial_recognition/recognition.py:28`). O roteador separa
entradas sem/com dependência (`main.py:139-144`) e executa em duas ondas
`asyncio.gather` (`main.py:201-204`), injetando a saída da detecção como segundo
input da recognição (`main.py:189-193`). Ou seja: **uma única chamada HTTP faz
detecção + embedding de todas as faces**
(`machine-learning.repository.ts:194-207`).

### Ciclo de vida dos modelos no serviço ML

- Cache em memória com lock otimista e TTL: `immich_ml/models/cache.py:38-50`;
  TTL default 300 s (`config.py:58`).
- Preload opcional na subida (`main.py:78-115`).
- **Auto-shutdown por inatividade** quando `model_ttl > 0` (`main.py:251-262`) —
  o container morre e o orquestrador reinicia sob demanda.
- Carregamento com fallback: se o formato acelerado (armnn/rknn) não existir para
  o modelo, cai para ONNX (`main.py:222-243`); em erro de arquivo corrompido,
  limpa o cache e tenta de novo (`main.py:238-243`, `models/base.py:85-105`).
- Execução em `ThreadPoolExecutor` porque o asyncio é gargalo (`main.py:59-61`,
  `main.py:214-219`).
- Servido por gunicorn + worker uvicorn custom (`immich_ml/__main__.py:29-55`).

### O que acontece se o ML estiver indisponível

1. **Poller de saúde** por URL, a cada 30 s, timeout 2 s —
   `machine-learning.repository.ts:109-146`; defaults em
   `server/src/config.ts:299-303`.
2. **Failover**: `predict` tenta primeiro as URLs saudáveis, depois as
   não-saudáveis; se todas falharem, lança erro
   (`machine-learning.repository.ts:164-192`).
3. O handler de job propaga a exceção. BullMQ está configurado com
   **`attempts: 1`, `removeOnFail: false`**
   (`server/src/repositories/config.repository.ts:287-291`) → **sem retry
   automático**. O asset simplesmente fica sem linha em `smart_search` / sem
   `asset_job_status.facesRecognizedAt`, e é repescado quando o usuário roda o
   job "Missing" (streams condicionais: `asset-job.repository.ts:211-218`,
   `440-446`, `195-208`).
4. Com `machineLearning.enabled = false`, todos os handlers retornam `Skipped`
   via guards em `server/src/utils/misc.ts:97-105`.
5. Busca semântica com ML off → `BadRequestException`
   (`search.service.ts:148-151`). Busca por metadados/OCR/pessoas continua
   funcionando.

---

## 2. Fluxo de ponta a ponta

### 2.0 Gatilho comum (upload)

`AssetGenerateThumbnails` → enfileira `SmartSearch`, `AssetDetectFaces`, `Ocr` —
`services/job.service.ts:170-186`. `SmartSearch` (origem upload) encadeia
`AssetDetectDuplicates` — `job.service.ts:254-258`. Reprocessamento manual por
asset: `asset.service.ts:472-478` (`REFRESH_FACES`).

### 2.1 CLIP / busca semântica

**Indexação**

| Etapa | Local |
|---|---|
| Enfileiramento em massa | `services/smart-info.service.ts:67-93` |
| Guard `clip.enabled && ml.enabled` | `utils/misc.ts:98-99` |
| Stream de assets faltantes | `repositories/asset-job.repository.ts:211-218` |
| Handler | `services/smart-info.service.ts:95-127` |
| Carrega caminho do **preview** (não o original) | `asset-job.repository.ts:221-228` |
| Chamada HTTP | `repositories/machine-learning.repository.ts:209-213` |
| Roteamento no ML | `immich_ml/main.py:166-183` |
| Pré-processamento (resize bicúbico → center-crop → normalize) | `immich_ml/models/clip/visual.py:60-77`, `models/transforms.py:15-39` |
| Inferência ONNX | `models/clip/visual.py:31-33` |
| Persistência | `repositories/search.repository.ts:459-466` (upsert em `smart_search`) |
| Proteção contra troca de modelo no meio do job | `smart-info.service.ts:113-122` |

**Consulta**

| Etapa | Local |
|---|---|
| Endpoint | `services/search.service.ts:143-189` |
| Cache LRU de 100 embeddings de query, em memória do processo | `search.service.ts:29`, `156-164` |
| Encode de texto | `machine-learning.repository.ts:215-219` → `models/clip/textual.py:84-111` |
| Tokenização (padding/truncation em `context_length`, default 77) | `clip/textual.py:85-99` |
| Prefixo de idioma FLORES-200 para modelos `nllb` | `clip/textual.py:101-111` + tabela `models/constants.py:103-160` |
| Variante MClip (usa `input_ids` + `attention_mask`) | `clip/textual.py:113-122` |
| kNN | `repositories/search.repository.ts:308-325` — `ORDER BY smart_search.embedding <=> $embedding` (distância cosseno), dentro de transação com `set local vchordrq.probes` |
| Busca "assets parecidos com este" (query por assetId) | `search.service.ts:165-172` + `search.repository.ts:330-333` |

**Troca de modelo CLIP**: `smart-info.service.ts:34-65` — sob lock de banco,
compara a dimensão do modelo novo com a da coluna; se mudou, `setDimensionSize`
(recria a coluna vetorial); se só o nome mudou com a mesma dimensão, apaga
**todos** os embeddings. Validação do nome no boot: `smart-info.service.ts:23-32`
+ `utils/misc.ts:129-136` + tabela `server/src/constants.ts:69+`.

### 2.2 Reconhecimento facial — detecção e embedding

| Etapa | Local |
|---|---|
| Enfileiramento; `force` apaga faces ML e faz VACUUM/REINDEX | `services/person.service.ts:267-297` |
| Handler de detecção | `person.service.ts:300-382` |
| Carrega asset + faces existentes + preview | `asset-job.repository.ts:231-240` |
| Chamada HTTP (detecção+recognição num request) | `machine-learning.repository.ts:194-207` |
| Detector: RetinaFace via `insightface.model_zoo`, `det_thresh = minScore`, input 640×640 | `immich_ml/models/facial_recognition/detection.py:11-41` |
| Recognizer: ArcFaceONNX, crop alinhado pelos 5 landmarks (`norm_crop`) | `models/facial_recognition/recognition.py:27-77` |
| Batching de faces (eixo `batch` injetado no ONNX se necessário) | `recognition.py:37-45`, `55-64`, `79-86` |
| Saída: bbox + score + embedding serializado | `recognition.py:66-77` |
| **Reconciliação com faces já existentes por IoU > 0.5** (evita duplicar face ao re-rodar) | `person.service.ts:344`, `384-399` |
| Faces ML antigas não re-encontradas são deletadas | `person.service.ts:361-369` |
| Escrita atômica (insert faces + delete + insert embeddings numa query com CTEs) | `repositories/person.repository.ts:410-431` |
| Enfileira `FacialRecognition` por face + um `FacialRecognitionQueueAll` | `person.service.ts:371-377` |

Escala de bbox: o server reescala as caixas quando o preview mudou de tamanho
entre execuções (`person.service.ts:338-343`).

### 2.3 Reconhecimento facial — clusterização em pessoas

Handler: `services/person.service.ts:459-541`. Fila: `person.service.ts:401-457`.

Algoritmo (descrito em `docs/docs/features/facial-recognition.md:37-56`):
**DBSCAN incremental aproximado**, implementado como kNN em cima do índice
vetorial.

1. Espera as filas de thumbnail e detecção esvaziarem (`person.service.ts:408`) —
   quanto maior o lote, melhor o cluster.
2. `prewarm` do índice vetorial de faces (`person.service.ts:435`).
3. Para cada face não atribuída: kNN por cosseno em `face_search`, limitado a
   `numResults = minFaces` e filtrado por `distance <= maxDistance` —
   `person.service.ts:487-493` → `repositories/search.repository.ts:344-380`.
   Filtro extra: só casa com pessoas cuja `birthDate <= fileCreatedAt`
   (`search.repository.ts:363-367`).
4. **Core point** = `matches.length >= minFaces` **e** asset visível na timeline —
   `person.service.ts:503-505`.
5. Face não-core é **adiada** (`deferred: true`) e re-enfileirada para o fim
   (`person.service.ts:506-510`) — assim ela pode pegar carona numa pessoa criada
   depois, no mesmo lote.
6. Se algum vizinho já tem `personId` → herda (`person.service.ts:512`). Senão,
   faz uma segunda busca restrita a faces que **têm** pessoa
   (`person.service.ts:513-526`).
7. Se é core e ainda não há pessoa → **cria pessoa nova** sem nome, define feature
   photo e enfileira thumbnail (`person.service.ts:528-533`).
8. Atribui (`person.service.ts:535-538` → `person.repository.ts:82-91`).
9. Job noturno repesca faces órfãs, com short-circuit se nada mudou desde a
   última execução (`person.service.ts:410-420`, estado em
   `SystemMetadataKey.FacialRecognitionState`).

Thumbnail da pessoa (crop da bbox no original/preview):
`services/media.service.ts:411-468`.

### 2.4 Confirmação pelo usuário e o que acontece quando ele discorda

**Não existe estado "sugestão pendente".** A atribuição é escrita como fato em
`asset_face.personId` assim que o job roda; a "confirmação" implícita é o usuário
nomear a pessoa. Pessoas com menos de `minFaces` faces ficam ocultas da listagem.

Ações de discordância, todas corretivas e **sem qualquer feedback para o
modelo**:

| Ação | Server | Efeito |
|---|---|---|
| Reatribuir face a outra pessoa | `person.service.ts:80-107` (lote) e `109-121` (uma face); controller `person.controller.ts:175-188` | Só troca `asset_face.personId` (`person.repository.ts:301-309`) |
| Criar pessoa nova a partir de uma face | UI: `web/src/lib/components/faces-page/PersonSidePanel.svelte:104-135` | Nova linha em `person` |
| Merge de duas pessoas | `person.service.ts:555-615`; UI `web/src/lib/modals/PersonMergeSuggestionModal.svelte` | Reatribui todas as faces e **apaga** a pessoa absorvida; herda nome/aniversário se o alvo não tiver |
| Remover face do asset | `person.service.ts:698-702` | `force=false` → soft delete (`deletedAt`), `force=true` → hard delete (`person.repository.ts:519-526`). Faces soft-deletadas são excluídas de `getAllFaces` (`person.repository.ts:123-124`), logo saem da clusterização |
| Marcar face manualmente (bbox desenhada) | `person.service.ts:626-696` | Grava `sourceType = Manual`, com transformação de coordenadas se o asset tem edições |
| Ocultar pessoa / favoritar / aniversário | `person.service.ts:186-220` | Flags em `person` |

**Proteção do trabalho manual**: o enum `SourceType` (`server/src/enum.ts:396-400`)
tem `machine-learning` / `exif` / `manual`. Re-rodar tudo com `force` só apaga
(`person.service.ts:274`) ou desassocia (`person.service.ts:425`) faces de origem
`machine-learning`. Faces importadas de XMP (`RegionInfo`) entram como `exif`
(`services/metadata.service.ts:910-968`).

### 2.5 Detecção de duplicatas por similaridade visual

**Técnica:** não é hash perceptual. Reusa o **mesmo embedding CLIP** de
`smart_search`.

| Etapa | Local |
|---|---|
| Enfileiramento | `services/duplicate.service.ts:303-327` |
| Guard (`clip.enabled && duplicateDetection.enabled`) | `utils/misc.ts:104-105` |
| Handler; pula assets em stack, hidden, locked, ou sem embedding | `duplicate.service.ts:329-385` |
| kNN | `repositories/duplicate.repository.ts:192-219` — top-64 candidatos (`DUPLICATE_SEARCH_LIMIT`, `duplicate.repository.ts:15`), mesmo `type` (foto/vídeo), mesmo dono, `distance <= maxDistance` |
| **Limiar default: `maxDistance = 0.01`** (distância cosseno → quase idêntico) | `server/src/config.ts:306-309` |
| Agrupamento: propaga/merge de `asset.duplicateId` | `duplicate.service.ts:387-411` → `duplicate.repository.ts:221-233` |
| Marca `asset_job_status.duplicatesDetectedAt` | `duplicate.service.ts:381-382` |

**Apresentação ao usuário:**

- `GET /duplicates` → `duplicate.service.ts:69-82`: limpa grupos-singleton
  (`duplicate.repository.ts:91-112`), devolve grupos com `suggestedKeepAssetIds`.
- Heurística da sugestão: **maior tamanho de arquivo**, desempate por **maior
  contagem de campos EXIF** — `server/src/utils/duplicate.ts:25-60`.
- UI:
  `web/src/routes/(user)/utilities/duplicates/[[photos=photos]]/[[assetId=id]]/+page.svelte`
  — resolver (`:98-125`), empilhar em vez de apagar (`:127-134`), "Deduplicate
  All" usando as sugestões do server (`:136-142`). Comparação lado a lado em
  `DuplicatesCompareControl.svelte`.
- Resolução: `duplicate.service.ts:94-238` — valida que todo asset do grupo está
  em `keep` **ou** `trash` (`:127-145`), e só faz merge de metadados (álbuns,
  tags, rating, descrição, coordenadas, favorito, visibilidade) quando
  **exatamente um** asset é mantido (`:159-218`). Vai para lixeira, não delete
  definitivo, se a lixeira estiver ligada (`:220-235`).
- **Nada é apagado automaticamente em nenhum ponto do pipeline.**

### 2.6 OCR

`services/ocr.service.ts`, request em `machine-learning.repository.ts:221-230`;
modelos PaddleOCR PP-OCRv5 via `rapidocr`
(`immich_ml/models/ocr/detection.py:21-60`, `ocr/recognition.py`), thresholds em
`config.ts:317-322`. Resultados em `ocr_search`
(`schema/tables/ocr-search.table.ts`).

---

## 3. Modelos, runtime e onde ficam os embeddings

### Runtime

- **ONNX Runtime** é o runtime primário (`immich_ml/sessions/ort.py:48-98`). Não
  há PyTorch em runtime — só no conversor offline (`machine-learning/ann/export/`).
- Provedores em ordem de preferência: CUDA → MIGraphX (ROCm) → OpenVINO →
  **CoreML** → CPU (`models/constants.py:91-97`, seleção em
  `sessions/ort.py:109-113`, opções por provedor em `ort.py:125-160`, session
  options/threads em `ort.py:182-203`).
- Runtimes alternativos: **ArmNN** (`sessions/ann/__init__.py`,
  `sessions/ann/loader.py`, biblioteca C++ em `ann/ann.cpp`) e **RKNN** para SoCs
  Rockchip (`sessions/rknn/__init__.py:42-`, pool de threads em
  `rknn/rknnpool.py`).
- Escolha do formato: RKNN > ARMNN > ONNX (`models/base.py:170-176`); seleção da
  classe de sessão pela extensão do arquivo (`models/base.py:107-120`).
- Extras de instalação por device: `machine-learning/pyproject.toml:49-56`
  (`cpu`, `cuda`, `openvino`, `armnn`, `rknn`, `rocm`).

### Modelos

| Área | Modelo default | Alternativas | Dimensão |
|---|---|---|---|
| CLIP | `ViT-B-32__openai` (`config.ts:302-305`) | ~59 OpenCLIP/SigLIP/SigLIP2/NLLB (`models/constants.py:4-59`) + 4 M-CLIP (`:62-67`) | 512 / 640 / 768 / 1024 conforme `server/src/constants.ts:69+` |
| Detecção facial | InsightFace `buffalo_l` (`config.ts:310-316`) | `buffalo_s`, `buffalo_m`, `antelopev2` (`models/constants.py:70-75`) | — |
| Embedding facial | ArcFace do mesmo pacote InsightFace | idem | **512, fixo** (`schema/tables/face-search.table.ts:15`) |
| OCR | `PP-OCRv5_mobile` (`config.ts:317-322`) | 10 variantes Paddle (`models/constants.py:78-89`) | — |

**Tamanhos:** o repositório não guarda os pesos. As tabelas de referência de
memória/latência/recall por modelo CLIP estão em
`docs/docs/features/searching.md:~93-140` (de ~975 MiB RSS para
`ViT-B-16__laion400m_e32` até ~6.5 GiB para `ViT-gopt-16-SigLIP2-384`; tempos de
2 ms a 147 ms por imagem em CPU 7800X3D).

**Onde ficam os pesos:** baixados do Hugging Face Hub, repositório
`immich-app/{nome-do-modelo}` via `snapshot_download` (`models/base.py:68-83`),
com `ignore_patterns` por formato. Layout no disco:
`{cache_folder}/{task}/{model_name}/{type}/model.{onnx|armnn|rknn}`
(`models/base.py:122-135`, `:153-155`). `cache_folder` default
`~/.cache/immich_ml` (`config.py:57`); no container é `/cache`
(`machine-learning/Dockerfile:137`), volume `model-cache`
(`docker/docker-compose.yml:42-43`).

### Onde ficam os embeddings

Todos no **Postgres**, em colunas `vector` com índice **HNSW cosseno** (na
prática substituído por índice VectorChord `vchordrq` em runtime):

| Tabela | Conteúdo | Arquivo |
|---|---|---|
| `smart_search(assetId, embedding vector(512))` | embedding CLIP da imagem; PK = assetId; `storage: external` | `server/src/schema/tables/smart-search.table.ts:4-17` |
| `face_search(faceId, embedding vector(512))` | embedding ArcFace por face detectada | `server/src/schema/tables/face-search.table.ts:4-17` |
| `asset_face` | bbox, dimensões da imagem de referência, `personId`, `sourceType`, `isVisible`, `deletedAt` | `server/src/schema/tables/asset-face.table.ts:20-89` |
| `person` | nome, thumbnail, `faceAssetId`, `isHidden`, `birthDate`, `color` | `server/src/schema/tables/person.table.ts:19-69` |
| `ocr_search` | texto + boxes | `server/src/schema/tables/ocr-search.table.ts` |

Gestão do índice vetorial: `server/src/repositories/database.repository.ts:31-48`
(detecção da extensão), `:51` (`probes`), `:149-156` (`prewarm`), `:158-208`
(reindex adaptativo por número de linhas), `:283-320` (get/set da dimensão),
`:345+` (limpar embeddings).

---

## 4. Dependências externas

### Serviço ML (`machine-learning/pyproject.toml:8-25`)

| Dependência | Uso | Sem ela |
|---|---|---|
| `onnxruntime` (extra por device) | toda a inferência | nada roda |
| `insightface` | `RetinaFace` e `ArcFaceONNX` (wrappers de pré/pós-processamento e `norm_crop`) | reconhecimento facial inteiro cai; seria preciso reimplementar decode de anchors do RetinaFace e o alinhamento por landmarks |
| `opencv-python-headless` | `cv2.cvtColor`, resize interno do insightface | detecção facial e OCR caem |
| `Pillow` | decode de imagem, resize/crop do CLIP | tudo cai |
| `tokenizers` (HF) | tokenizer do CLIP textual | busca por texto cai (embedding de imagem sobrevive) |
| `huggingface-hub` | download dos pesos | modelos já em cache continuam funcionando; novos, não |
| `rapidocr` | PP-OCRv5 | só OCR cai |
| `fastapi`/`uvicorn`/`gunicorn`/`python-multipart` | transporte | o serviço não sobe |
| `orjson` | serialização de arrays numpy | o contrato de embedding-como-string quebra |
| `aiocache` | cache de modelos com TTL/lock | recarregaria o modelo a cada request |
| `rknn-toolkit-lite2` (opcional) | NPU Rockchip | fallback automático para ONNX (`main.py:228-236`) |

### Server

| Dependência | Uso | Sem ela |
|---|---|---|
| **Postgres + VectorChord/pgvector** | armazenar e buscar embeddings (`<=>`), índices `vchordrq` | busca semântica, clusterização facial e duplicatas ficam impossíveis |
| **Redis + BullMQ** | todas as filas ML | nada é processado em background |
| Serviço ML por HTTP | inferência | ver §1 |
| `sharp` (via `media.repository`) | preview que alimenta o ML e crop do thumbnail da pessoa | sem preview, os jobs falham (`smart-info.service.ts:103`, `person.service.ts:305-307`) |

---

## 5. Portabilidade para desktop local-first, single-user, Python + SQLite

### 5.1 Portável quase 1:1

- **Toda a estrutura de `machine-learning/`** é aproveitável como *biblioteca
  in-process*, sem FastAPI. As classes `InferenceModel` (`models/base.py:16-176`),
  `OpenClipVisualEncoder`, `OpenClipTextualEncoder`, `FaceDetector`,
  `FaceRecognizer` já são autocontidas: recebem bytes/PIL, devolvem numpy. Basta
  chamar `model.predict(...)` no lugar do HTTP. **(Reimplementar — não copiar:
  AGPL.)**
- **Pré-processamento**: `models/transforms.py:15-74` (resize bicúbico
  preservando aspecto, center-crop, normalize por mean/std do
  `preprocess_cfg.json`, `clean_text`).
- **Contrato de duas fases detecção→embedding** (`main.py:185-204`) vira duas
  chamadas sequenciais triviais.
- **Layout de modelos em disco** (`models/base.py:122-155`) e o download por
  `snapshot_download` funcionam offline-first: baixa uma vez, roda sempre local.
- **Runtime**: `onnxruntime` CPU + `CoreMLExecutionProvider` no macOS já está
  previsto (`models/constants.py:91-97`, `sessions/ort.py:157-160`) — cobre
  desktop sem GPU dedicada.
- **Heurística de sugestão de duplicata** (`utils/duplicate.ts:25-60`): ~20
  linhas.
- **IoU para reconciliar re-detecções** (`person.service.ts:384-399`).
- **`SourceType`** (`enum.ts:396-400`) — marcar a origem de cada face
  (`machine-learning` / `manual` / `exif`) e nunca deixar um reprocessamento
  tocar em faces manuais (`person.service.ts:274`, `:425`).
- **`asset_job_status` + streams condicionais**
  (`asset-job.repository.ts:195-218`, `440-446`): "o que ainda falta processar",
  trivial em SQLite.
- **`model_ttl` + auto-unload** (`main.py:251-262`, `models/cache.py`) — é o que
  torna viável rodar CLIP + face num desktop, já que juntos são ~1 GB de RSS.

### 5.2 Precisa ser substituído

| Peça do Immich | Substituto |
|---|---|
| HTTP multipart + health poller + failover (`machine-learning.repository.ts`) | chamada de função direta; failover e `/ping` deixam de existir |
| BullMQ/Redis, `QueueName`, `@OnJob` | fila local (worker + tabela `jobs` no SQLite, ou `concurrent.futures`) |
| Postgres `vector` + `<=>` + índices `vchordrq`/HNSW (`search.repository.ts:308-380`, `duplicate.repository.ts:192-219`) | **maior gap.** SQLite não tem kNN nativo. Opções: `sqlite-vec` / `sqlite-vss` como extensão; ou embeddings em `BLOB` + índice em memória (`faiss`, `hnswlib`, ou força bruta numpy — para <100k fotos, 512-d f32 é ~200 MB e ~ms por query) |
| `set local vchordrq.probes`, `prewarm`, reindex adaptativo (`database.repository.ts:149-208`) | desnecessário fora do Postgres |
| Migração de dimensão ao trocar modelo CLIP (`smart-info.service.ts:34-65`) | vale replicar a *ideia*: guardar `model_name` + `dim` junto do índice e invalidar tudo ao trocar |
| Multi-usuário: `ownerId`, `partnerIds`, `Permission`, `requireAccess` | remover — simplifica muito |
| `person.birthDate <= fileCreatedAt` como filtro de match (`search.repository.ts:363-367`) | opcional |

### 5.3 O que **não** é portável, dado o requisito de "sempre sugestão a confirmar"

Este é o desalinhamento conceitual central com o Foto Organizer (invariante 6):

1. **O Immich não tem estado de sugestão.** `handleRecognizeFaces` grava
   `asset_face.personId` direto (`person.service.ts:535-538`). Para um modelo
   sugestão-a-confirmar é preciso uma tabela intermediária tipo
   `face_suggestion(face_id, person_id, distance, status: pending|accepted|rejected)`
   e só materializar o vínculo no `accept`.
2. **Não há feedback negativo.** Quando o usuário discorda, ele reatribui, faz
   merge ou apaga a face (`person.service.ts:80-121`, `555-615`, `698-702`) —
   nenhum registro de "esta face NÃO é esta pessoa" é guardado, e nada disso
   influencia clusterizações futuras. Para que "discordar" tenha efeito
   duradouro, é preciso inventar essa camada (ex.: cannot-link constraints
   consultadas antes de sugerir).
3. **Duplicatas com `maxDistance = 0.01`** (`config.ts:308`) é um limiar de
   *quase-idêntico*, calibrado para reencodes/recompressões, não para "fotos
   parecidas da mesma cena". Se o produto promete "visualmente similar", o limiar
   precisa ser outro e o número de falsos positivos muda de ordem de grandeza — e
   aí a UI de confirmação em par (`DuplicatesCompareControl.svelte`) passa a ser
   obrigatória, não opcional.
4. **O opt-in de reconhecimento facial não é opt-in de verdade**: no Immich o
   toggle é global de admin (`config.ts:310-312`, guard em `utils/misc.ts:102-103`)
   e desligar apenas **para de enfileirar** — não apaga nada. Para um opt-in
   honesto é preciso: (a) não baixar os modelos de face até o opt-in, (b) apagar
   `face_search` + `asset_face` + `person` no opt-out. O Immich tem as primitivas
   de limpeza (`person.repository.ts:111-113`, `person.service.ts:239-249`) mas
   não as amarra ao toggle.
5. **Custo do "roda 100% local"**: o pipeline default (ViT-B-32 + buffalo_l) é o
   mais barato do catálogo; ainda assim são ~1 GB de RSS para CLIP + os modelos
   de face carregados simultaneamente.

### 5.4 Recorte mínimo recomendado

**Aproveitar (reimplementando):** a estrutura de `immich_ml/models/*`, o
pré-processamento, o layout de cache de modelos, o padrão `sourceType`, o IoU de
reconciliação, a heurística de sugestão de duplicata, o auto-unload por TTL.

**Reescrever:** camada de persistência (SQLite + `sqlite-vec` ou hnswlib), fila,
e — obrigatoriamente — a tabela de sugestões e o registro de rejeições, que não
existem no original.
