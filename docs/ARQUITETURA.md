# Arquitetura e decisões

Complementa o CLAUDE.md (invariantes, stack, módulos). Aqui: schema, fluxo
de dados, riscos e decisões registradas.

## Fluxo de dados

scan (read-only) → catálogo SQLite → extração de metadados → evidências →
sugestões (com confiança e versão da lógica) → revisão humana → plano de
operação → dry-run → execução (cópia verificada) → audit log.

UI (PySide6, main thread) ⇄ ViewModels ⇄ Repositories/Services ⇄ Workers
(QThreadPool) — todo I/O e CPU pesada nos workers.

**UI web local (M9, principal):** `webapp/` (React/Vite/TS/Tailwind, grade
virtualizada, loupe teclado-first) fala com `fotoorganizer/server/`
(FastAPI, só 127.0.0.1) que reusa os MESMOS repositórios/serviços — os
handlers nunca tocam filesystem/DB direto. Trabalhos pesados (scan,
importação, sugestões, duplicatas) rodam um por vez no JobManager
(thread), com progresso por SSE. O build de `webapp/dist` é servido pelo
próprio FastAPI: um processo, zero rede externa. A UI PySide6 segue como
fallback até paridade.

## Schema inicial (Alembic, migração 0001)

- `sources` — pasta/volume raiz, tipo (pasta | apple_photos |
  google_takeout — migração 0003), apelido, ativo, disponível,
  ignorar_padrões. Catálogos externos (Apple Fotos via osxphotos,
  Google Takeout via sidecars JSON) entram como fontes do MESMO catálogo
  pelo `ExternalCatalogImporter` (`fotoorganizer/sources/`): o arquivo
  manda (EXIF), o catálogo externo preenche lacunas (data/GPS de export)
  e contribui contexto em `metadata_entries` (namespaces `apple`,
  `google`). O cruzamento entre fontes (deriva de relógio por
  pares-âncora + herança de GPS por proximidade temporal) vive em
  `grouping/correlacao.py` — ver docs/AGRUPAMENTO.md.
- `scan_sessions` — fonte, início/fim, status (rodando/pausado/concluído),
  checkpoint, contadores (arquivos, erros, bytes), versão do scanner.
- `media_files` — id, source_id, caminho, volume, pasta, nome, extensão,
  tamanho, inode, ctime, mtime, data_capturada (hora de parede) +
  data_capturada_utc (o mesmo instante, absoluto — o offset é a diferença
  entre as duas, nunca uma coluna; iguais quer dizer "fuso desconhecido",
  ver D-038), tz_estimado, make, model,
  lente, orientação, largura, altura, gps_lat, gps_lon, hash_rapido,
  hash_sha256 (nullable), status_revisão, erro_leitura, indexado_em.
- `metadata_entries` — media_id, namespace, chave, valor (dados brutos
  relevantes). Namespaces reais: `exif`, `gps`, `iptc`, `xmp` (este só
  com `defusedxml` — ver docs/PLANO_METADADOS.md), `libraw` em RAW, e
  `apple`/`google` vindos de catálogo externo. Campo repetível vira uma
  linha com valores separados por ponto e vírgula, não chave indexada:
  índice em chave não sobrevive a reprocessamento.
- `locations` — geocoding resolvido (país, região, cidade, local, fonte do
  dado, cache key) referenciado por `media_files.location_id`.
- `trips` / `events` — agrupamentos com período, local dominante, método.
- `people`, `face_embeddings` (blob criptografado), `face_occurrences`
  (media_id, person_id?, bbox, estado: detectado/possível/confirmado).
- `tags`, `media_tags`.
- `evidence` — media_id, campo alvo (data/país/cidade/evento/categoria/…),
  origem (exif/gps/pasta/nome/vizinhança/visão/usuário), valor, confiança
  (enum + score), justificativa, versão_lógica, criado_em.
- `suggestions` — media_id, destino_sugerido (por template), confiança
  final, status (pendente/aprovada/rejeitada/editada), evidências vinculadas.
- `duplicate_groups` / `duplicate_members` — nível (exato/conteúdo/visual),
  papel (principal/versão/ignorado).
- `operation_plans` / `operation_items` — operação, origem, destino,
  conflito, status, hash pré/pós.
- `audit_log` — quem/quando/o quê/resultado, id de operação.
- `application_settings` — chave/valor tipado.

Índices: media_files(hash_rapido), (source_id, caminho) unique,
(data_capturada), (mtime, tamanho); evidence(media_id); suggestions(status).

## Decisões registradas

| # | Decisão | Racional |
|---|---------|----------|
| 1 | Reiniciar em PySide6, abandonando FastAPI+Streamlit | Streamlit não sustenta grade virtualizada de dezenas de milhares de thumbs nem workers pausáveis; app é local, cliente/servidor era complexidade sem ganho. |
| 2 | Portar (não reescrever) scanner RAW/HEIC, phash e gap de viagem do legado | Lógica já validada em uso real (commits ffa956d, df98cdc, bc459af). |
| 3 | exiftool em batch com fallback puro-Python | exiftool é o padrão-ouro (IPTC/XMP/RAW), mas não pode ser dependência dura num app desktop. |
| 4 | xxhash como hash rápido, SHA-256 completo sob demanda | MD5 do legado nem é rápido nem é o hash criptográfico exigido para verificação de cópia. |
| 5 | Geocoding offline por padrão | Privacidade primeiro; serviço externo vira provider opt-in com cache. |
| 6 | Confiança como enum+score por evidência, agregada por regra documentada | Prompt proíbe soma arbitrária (o score aditivo do legado morre aqui). |
| 7 | Criptografia de embeddings via chave no Keychain (macOS) | Melhor prática viável num app local; limitação (quem tem a sessão do usuário acessa) documentada em PRIVACIDADE.md. |

## Riscos principais

1. **Integridade das fotos** — mitigado por read-only estrutural: módulo
   `operations/` é o único com permissão de escrita fora do catálogo, e só
   copia com verificação de hash.
2. **Escala (100k+ fotos)** — indexação incremental, transações em lote,
   WAL, thumbs em cache de disco, virtualização na UI, benchmark desde M1.
3. **Volumes externos desconectados** — fonte marcada indisponível; scan e
   operações pausam com checkpoint, nunca falham parcialmente sem registro.
4. **Metadados ruins/ausentes** — cada campo tem origem e confiança; nunca
   inventar localização; corrompidos registrados e pulados.
5. **Scope creep (visão, rostos, serviços externos)** — congelados atrás de
   Protocols com stub até o núcleo (M0–M5) estar estável.
