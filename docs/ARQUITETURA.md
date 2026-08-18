# Arquitetura e decisões

Complementa o CLAUDE.md (invariantes, stack, módulos). Aqui: schema, fluxo
de dados, riscos e decisões registradas.

## Fluxo de dados

scan (read-only) → catálogo SQLite → extração de metadados → evidências →
sugestões (com confiança e versão da lógica) → revisão humana → plano de
operação → dry-run → execução (cópia verificada) → audit log.

UI ⇄ Repositories/Services ⇄ Workers — todo I/O e CPU pesada nos workers.

**UI web local (única interface):** `webapp/` (React/Vite/TS/Tailwind, grade
virtualizada, loupe teclado-first) fala com `fotoorganizer/server/`
(FastAPI, só 127.0.0.1) que reusa os MESMOS repositórios/serviços — os
handlers nunca tocam filesystem/DB direto. Trabalhos pesados (scan,
importação, sugestões, duplicatas) rodam um por vez no JobManager
(thread), com progresso por SSE. O build de `webapp/dist` é servido pelo
próprio FastAPI: um processo, zero rede externa. A UI PySide6 foi removida
por inteiro (commit `2e0ef1a`, 31/07/2026).

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

## Módulo `exif_write/`

Escreve GPS lat/long, cidade e país (só localização — D-075) no arquivo
original ou num sidecar `.xmp`, só em campo já vazio, nunca sobrescreve.
Autorizado pelo invariante 7 vigente (revogado em parte por D-075) e por
`docs/DECISOES.md` D-075.

**Por que é módulo próprio e não extensão de `operations/`:** a cópia se
protege criando um caminho novo que ainda não existe (`open('xb')`);
mutação in-place não tem equivalente disso. O modelo de segurança é outro
(backup `_original` do exiftool + diff completo de tags, não hash de
arquivo inteiro) e o modelo de status também é outro (por campo, não por
item).

**Fluxo:** planner (só banco, `ExifWritePlanner`) → dry-run (relê o disco
ao vivo, em lote, reconfere TOCTOU) → seleção do dono (checkbox por linha,
D-01/D-02) → executor (reconfere ao vivo, escreve via `exiftool`, verifica
por diff completo de tags — nunca `returncode` — só então apaga o backup
`_original`) → `AuditLog`.

**Armadilha do `AuditLog`:** a coluna `plan_id` tem FK real para
`operation_plans.id` (`PRAGMA foreign_keys=ON`). Linhas de auditoria da
escrita EXIF reusam `AuditLog`, mas deixam `plan_id=NULL` e carregam o id
do `ExifWritePlan`/`ExifWriteItem` dentro do JSON de `detalhe` — gravar o
id do plano de EXIF direto em `plan_id` violaria a FK.

**O que não é escrito:** qualquer campo fora de localização (data, câmera,
autor etc.) e nunca sobre valor já preenchido, mesmo que a sugestão
discorde do que já está gravado.

**Allowlist de formato, medida contra o acervo real (não suposta):**
`docs/DECISOES.md` D-075 (autorização), D-076 (medição inicial: nenhum
formato aprova, por deslocamento de offset de bloco binário pré-existente
ao inserir metadado novo), D-077 (verificação byte a byte estende D-076:
`.jpg`/`.cr2` passam a aprovar), D-078 (`IPTC:EnvelopeRecordVersion` entra
no andaime incondicional). Fonte de verdade de quais formatos entram é
`fotoorganizer/exif_write/formatos.py` (`FORMATOS_APROVADOS`), atualizado
por `scripts/testar_escrita_exif.py`.

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
| 8 | Escrita EXIF de localização em campo vazio, módulo próprio (D-075); allowlist de formato medida byte a byte contra o acervo real, não suposta (D-076/D-077/D-078) | Sidecar XMP não é lido por parte do fluxo real do dono; verificação byte a byte evita aprovar pelo NOME da tag e mascarar corrupção real (EXIF-04). |

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
6. **Escrita em pasta sincronizada (iCloud Drive/Dropbox/OneDrive)** —
   risco de dessincronização silenciosa se o app grava enquanto o cliente
   de sync ainda processa o arquivo. Mitigado por D-07: `pasta_sincronizada()`
   detecta por prefixo de caminho resolvido (O(1), sem I/O de rede) e marca
   aviso explícito no plano dry-run; o dono decide incluir ou desmarcar via
   o mesmo checkbox de D-02, nunca bloqueio automático nem escrita silenciosa.
7. **Formato sem amostra testável no acervo (CR3/HEIC)** — D-03 exige medir,
   não supor, e o catálogo real hoje não tem nenhum arquivo desses formatos.
   Mitigado por D-09: marcado "não testado" (nunca "reprovado" por omissão),
   roteado para o fallback de sidecar XMP (EXIF-05) até existir amostra real.
