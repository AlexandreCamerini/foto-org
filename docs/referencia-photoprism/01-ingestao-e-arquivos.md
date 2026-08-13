# PhotoPrism — ingestão de arquivos e mídia

Fonte: `~/dev/photoprism-develop` (Go). Levantado em 2026-08-12 a partir de três
auditorias já ancoradas em `arquivo:linha` real (não reconstruídas de memória):
`.local/audit/photoprism/01-ingestao-e-midia.md`,
`07-integracoes-externas.md`, `08-config-cli-operacao.md` — mais verificação
direta de código para os mecanismos citados com maior confiança neste arquivo.

Este mapa é o par de [`referencia-immich/01-ingestao-e-storage.md`](../referencia-immich/01-ingestao-e-storage.md)
e assume que ele já foi lido: **não repete o que os dois softwares fazem
igual** (fan-out de diretório por hash, hash no mesmo passe de I/O, não
sobrescrever destino, `O_EXCL`/`'wx'` para evitar TOCTOU, journal de move em
duas fases…). Onde o mecanismo é idêntico em espírito, uma linha basta.

PhotoPrism é **AGPLv3**. Este arquivo descreve mecanismo, nunca reproduz
código.

## Por que este material existe

O Immich assume acervo com pixel presente e GPS recente; o PhotoPrism
compartilha essa assunção (self-hosted, servidor, biblioteca "viva" no
disco), mas resolve um problema que o Immich não tem: indexar **in-place**
sem servidor, com RAW+JPEG do mesmo clique, conversores externos variáveis,
sidecars XMP escritos por Lightroom/outros apps, e operação via CLI para
quem administra a própria instância. É a metade do espaço de problema mais
parecida com o que o foto-organizer precisa — biblioteca gerenciada pelo
usuário via app desktop, não upload para servidor de terceiros.

A régua de julgamento é a mesma do `referencia-immich`: **valor entregue por
unidade de custo para este acervo**, calibrado pelos números medidos —
~5,2 mil de ~99 mil registros conhecidos têm pixel legível hoje (D-028), só 4
dos 25 anos do acervo têm GPS de qualquer fonte (D-029), e 25.304+ nomeações
de álbum já estão no banco sem custar nada para ler (D-030). Ver
`docs/ROADMAP.md`, seção "Próximas versões", e `docs/DECISOES.md`.

---

## 1. Descoberta, indexação incremental e concorrência

**Scan padrão + validação de caminho.** Mesmo padrão do Immich/foto-organizer:
percorre `OriginalsPath()`, pula o que não mudou, rejeita traversal antes de
tocar disco (`internal/photoprism/index.go:98`, `index_options.go:73`
`ResolveIndexPath`). Nada novo aqui.

**Detecção incremental de sidecar XMP por `mod_time`, com resolução do
arquivo principal via cache — não por reindexar tudo.**
`internal/photoprism/index_sidecar.go:16` (`mainForSidecar`), `:46`
(`sidecarMainEnabled`). Em um rescan não forçado, quando um XMP novo/alterado
aparece, o resolvedor tenta duas convenções de nome (`foto.jpg.xmp` e
`foto.xmp` contra as extensões principais conhecidas, testando ambos os
casos de maiúscula/minúscula) contra um cache `Files` já carregado em
memória — sem tocar o banco por candidato — e só então reenfileira o arquivo
principal afetado. **Limitação documentada:** um XMP *apagado* não é
detectado nesse caminho incremental; só um rescan forçado reflete a remoção,
e mesmo assim campos como `CameraSerial`/`InstanceID` podem não reconciliar
por completo (débito confirmado em `internal/photoprism/README.md:62`).

**Lock por hash de conteúdo durante indexação paralela.**
`internal/photoprism/index_filehash.go:19` (`lockFileHash`). Mecanismo
pequeno e específico: quando dois workers processam concorrentemente duas
cópias do mesmo arquivo (mesmo hash, caminhos diferentes — comum quando o
mesmo evento foi copiado para duas pastas), um mutex por hash (mapa
`map[string]*fileHashLock` com contagem de referência, protegido por um
mutex próprio) serializa a indexação dessas duas cópias específicas sem
travar o resto do lote. O mapa só guarda hashes *em voo*: a entrada é
removida quando a contagem de referência chega a zero, então não cresce sem
limite ao longo de uma varredura grande.

- Verificado no código: a struct embute `sync.Mutex` + `refs int`; `lockFileHash`
  incrementa `refs` sob o mutex global do mapa, adquire o lock da entrada,
  devolve uma closure que libera o lock e decrementa `refs`, removendo a
  entrada quando chega a zero.

## 2. Empilhamento (stacking) — agrupar capturas relacionadas como um item

Três heurísticas independentes, combináveis via config, todas rodando dentro
de `internal/photoprism/index_mediafile.go` na resolução de qual "photo" um
arquivo pertence (bloco em torno de `:150-200`, `photo.Merge` em `:1148`):

1. **Por identificador único (Document ID/Instance ID do XMP/EXIF).** Regra
   `Config().Settings().StackUUID()` (default `true`). Casa RAW+JPEG da mesma
   captura mesmo com nomes de arquivo completamente diferentes.
2. **Por metadado de tempo+local (`lat`, `lng`, `taken_at`, `camera_serial`
   idênticos).** `StackMeta()` (default `true`). Cobre o caso em que não há
   Document ID em comum (câmeras/apps que não gravam esse campo).
3. **Por sequência de nome de arquivo (`IMG_0001`, `IMG_0001-2`, …).**
   `StackSequences()` (default **`false`**, opt-in).

Junto: `internal/photoprism/mediafile_related.go:16` (`MediaFile.RelatedFiles`)
descobre *antes* de indexar todos os arquivos relacionados de um principal
(RAW+JPEG, sidecar XMP/JSON, vídeo de Live Photo, variações Insta360), para
tratá-los como grupo em vez de indexar cada um isoladamente e reconciliar
depois.

**Por que isto é relevante aqui e não no Immich:** o Immich não tem stacking
— cada asset é uma linha, ponto. O foto-organizer já sabe que o acervo tem
RAW+JPEG do mesmo clique (D-029 cita 58 câmeras Canon 2001–2026, a maioria
gravando os dois formatos por padrão) e hoje resolve duplicata por
`duplicates/` (hash exato → SHA-256 → phash), que agrupa **arquivos
idênticos ou visualmente idênticos**, não **capturas irmãs com bytes
diferentes** (RAW e JPEG do mesmo disparo nunca têm o mesmo hash nem o mesmo
phash — são codificações diferentes da mesma cena). É uma lacuna real: hoje
RAW e JPEG do mesmo clique entram como dois registros de acervo
independentes, competindo por espaço de revisão e space na grade.

## 3. Metadados: precedência de fontes e resolução de timezone

**Cadeia de fontes com despacho automático por conteúdo, sem flag do
usuário decidir qual vale:** EXIF nativo (`internal/meta/exif.go:40`), JSON
do ExifTool (`internal/meta/json_exiftool.go:315`, inclui regiões de rosto
MWG), XMP padrão + MWG/ACDSee (`internal/meta/xmp.go:15`,
`xmp_document.go:405`), e JSON do Google Photos Takeout
(`internal/meta/json_gphotos.go:83`, despachado por conteúdo em
`internal/meta/json.go:15`, sem exigir extensão/nome específico). A leitura
de XMP aqui é **de entrada**, não só de saída futura — título, descrição,
copyright, câmera, GPS, projeção 360°, favorito, regiões de rosto.

**Normalização GPS:** DMS→decimal, clamp de latitude, wrap de longitude
antes de persistir (`internal/meta/gps.go:27,133`). Mecanismo trivial, mas
correto — vale conferir se o parser atual do foto-organizer (Pillow/exifread/
exiftool) já faz o clamp/wrap ou assume que o valor de origem é sempre
válido.

**Resolução de timezone: coordenada GPS → offset EXIF → fuso configurado.**
`internal/meta/resolver.go:25` (`Data.ResolveTimeZone`),
`internal/photoprism/timezone.go:4`. A cadeia de prioridade é: se há GPS na
própria foto, resolve o fuso pela coordenada (via `internal/entity`
cells/geocoding); senão, usa o offset gravado no EXIF; senão, cai no fuso
default da instância.

**Onde este mecanismo perde para este acervo:** as duas primeiras fontes da
cadeia (GPS próprio, offset EXIF) pressupõem uma proporção de fotos com GPS
que este acervo não tem — D-029 mediu **4 de 25 anos** com GPS de qualquer
origem, e mesmo dentro desses 4 anos só uma câmera (EOS 5D Mark IV) tem
receptor próprio confiável; o resto é herança/estimativa. Portar a cadeia
como está deixaria 21 dos 25 anos sem timezone. O roadmap (item 5) já
reformulou a fonte para "país herdado" em vez de GPS/offset — o padrão *de
cadeia com fallback ordenado* do PhotoPrism é o que vale copiar, não a
ordem das fontes.

## 4. Importação: copiar vs. mover, template de destino

**Import com dois modos, cópia e movimentação — movimentação remove
arquivos-ponto/inválidos/duplicados/dirs vazios da origem depois.**
`internal/photoprism/import_options.go:30` (`ImportOptionsCopy`), `:48`
(`ImportOptionsMove`). Default é copiar (`Settings.Import.Move=false`).

**Contraste direto com o invariante do foto-organizer:** o modo "mover" do
PhotoPrism é uma operação destrutiva na origem por desenho (remove arquivos
originais após a cópia bem-sucedida) — exatamente o que o invariante 2 do
`CLAUDE.md` proíbe ("execução é copiar, nunca mover"). Não portar o modo
mover, nem como opção — o valor que ele entrega (organizar a pasta de import
depois de consumida) não paga o risco de um bug apagar um original que não
tinha cópia em outro lugar.

**Template de nome/caminho de destino, evitando colisão com originais
existentes.** `internal/photoprism/import.go:325`
(`Import.DestinationFilename`), resolvido a partir de `Settings.Import.Dest`.
**Já temos o equivalente:** o roadmap (item 4, implementado em 2026-08-02)
entregou editor de template com preview ao vivo e persistência em
`application_settings`, mesmo conceito. Nada a importar aqui.

## 5. Conversão e miniaturas

Cadeia de conversores (RAW→preview via darktable-cli/rawtherapee-cli/sips,
libvips nativo para PNG/HEIC/AVIF/WebP, vetorial→PNG, vídeo→AVC via ffmpeg
com encoders de hardware, dewarp fisheye 360°) — `internal/photoprism/
convert_image.go`, `convert_video_avc.go`, `internal/ffmpeg/`. Conceitualmente
é o mesmo papel que o `thumbnails/` do foto-organizer já cobre (cache em
disco, geração em background, nunca resolução completa na grade), só que
com uma cadeia de binários externos maior. O próprio audit marca isso como
ponto fraco: **"a cadeia de conversão RAW depende de binários externos
variáveis por imagem Docker — não é 100% determinística entre ambientes"**
(débito documentado). Não vale reproduzir a cadeia inteira — libvips +
pillow-heif + rawpy já cobrem HEIC/RAW/AVIF sem depender de N binários
CLI instalados corretamente.

Dois detalhes pequenos e baratos, vale considerar:

- **Verificação de integridade da miniatura antes de servi-la**
  (`internal/thumb/verify.go:16`) — confirma que o arquivo gerado é uma
  imagem válida e não truncada antes de expor no cache. Custo de implementação
  trivial, evita servir miniatura corrompida por escrita interrompida.
- **Job de conversão/thumbnail cancela o lote quando o storage fica
  insuficiente** (`internal/photoprism/convert.go:69,82`
  `insufficientStorage`/`cancelInsufficientStorage`; mesmo padrão em
  `thumbs_worker.go:43`). Evita que uma fila de milhares de gerações de
  miniatura continue tentando escrever com disco cheio.

## 6. Faces, NSFW, labels de visão — não vale agora

`internal/photoprism/index_faces.go`, `mediafile_vision.go`,
`internal/ai/nsfw`. Pipeline completo: detecção facial, clustering, matching
por embedding, import de rosto anotado via XMP/MWG, detecção NSFW, geração
de labels/caption. Todos exigem pixel legível na resolução original.

**Não vale portar agora — mesma calibração do roadmap itens 6/7/8.** D-028
mede ~5% do acervo com pixel local hoje; qualquer coisa que precise abrir a
imagem alcança essa fatia. O próprio PhotoPrism trata isso como pipeline caro
(fila assíncrona, agendamento separado via `vision.yml`) porque pressupõe
acervo majoritariamente com pixel — premissa que não vale aqui. Revisitar
quando os volumes do Lightroom (45.397 fotos) remontarem.

## 7. Backup, restore e purge

**Export YAML de álbuns + dump de banco com retenção, ambos via CLI e via
worker agendado.** `internal/photoprism/backup/albums.go:19` (`Albums`,
exporta todos os álbuns como YAML legível por humano, restaurável por
`RestoreAlbums` em `:85`), `internal/photoprism/backup/database.go:27`
(`Database`, dump SQL com rotação/retenção configurável), agendamento
automático em `internal/workers/backup.go:23` (`NewBackup`, `StartScheduled`).
CLI: `photoprism backup --albums`/`--database --retain N`.

Verificado no código: `Albums` adquire um mutex dedicado
(`backupAlbumsMutex`) antes de rodar — só uma operação de backup/restore de
álbum por vez — e escreve um arquivo YAML por álbum via `query.Albums(0,
1000000)`.

**Vale considerar — candidato forte.** O catálogo do foto-organizer não é só
uma cópia de arquivos: carrega decisão cara de recomputar — `papel`
ACERVO/SINAL, evidências com confiança e justificativa, `gps_estimado_de_id`
com raio calibrado, correlação de eventos (D-024 a D-035 são meses de
julgamento humano em cima de dado medido). Um SQLite corrompido ou uma
migração malfeita hoje não tem rede de segurança formal além de backup
manual do arquivo `.db`. O padrão do PhotoPrism — dump automático com
retenção (roda sozinho, agendado) + export legível/versionável em git
(útil para diff e review, não só disaster recovery) — é exatamente o tipo de
"vale a pena para este acervo": custo de implementação baixo (SQLite dump é
`sqlite3 catalog.db .backup`), valor alto (protege trabalho que não se
refaz de graça).

**Purge: soft-delete por padrão, hard-delete opt-in — e aqui o PhotoPrism
perde para o próprio foto-organizer.** `internal/photoprism/purge.go:36`
(`Purge.Start`). Fluxo verificado: para fotos cujo arquivo físico sumiu,
`query.FlagHiddenPhotos()` zera `PhotoQuality` (`:283`), e
`query.MissingPhotos` + `photo.Delete(opt.Hard)` (`:218-245`) **sem `--hard`
apenas marca a foto como deletada** (sai da busca padrão, mas a linha
permanece); **com `--hard` remove permanentemente**. É melhor que um simples
`DELETE`, mas ainda é binário: uma foto sem arquivo físico vira "invisível"
(soft) ou "removida" (hard) — em nenhum dos dois casos ela continua
contribuindo GPS/data para correlação de outras fotos, porque sai
completamente da busca.

Compare com o invariante 8 do `CLAUDE.md` deste projeto: um registro que não
serve como acervo é **rebaixado a fonte de sinal** — sai da grade/revisão/
plano, mas continua doando GPS e correlação (D-024, medido: apagar 45.822
miniaturas do Apple Fotos levaria fotos reais com lugar estimado de 2.117
para 162). O PhotoPrism não tem esse terceiro estado. Isto já foi observado
de forma equivalente no `referencia-immich` (comparação com `isOffline`) —
o padrão `papel` ACERVO/SINAL deste projeto é estritamente melhor que a
dicotomia visível/invisível dos dois softwares de referência. Não há nada a
importar aqui; é confirmação de que o desenho atual está à frente.

## 8. Geocoding reverso e célula geográfica

**Reverse geocoding via serviço hospedado por padrão.**
`internal/service/maps/location.go:46` (`QueryApi`), consumindo
`places.photoprism.app` através de `internal/service/hub`. Só há
`--disable-places`; não há um dataset offline embutido usado por padrão.

**Onde o PhotoPrism perde para a própria decisão já tomada aqui.** O
foto-organizer já decidiu (invariante 4 + `geolocation/` no CLAUDE.md do
projeto) que reverse geocoding roda **offline por padrão** (dataset local
tipo `reverse_geocoder`), com serviço externo só opt-in e com indicação
prévia. O PhotoPrism inverte essa prioridade — API paga por padrão,
offline não é opção de primeira classe. Não copiar a prioridade; a
arquitetura de "provider substituível" (`GeocodingProvider` no
foto-organizer) já é o desenho correto.

**Célula geográfica para agrupar por local.** `internal/photoprism/
location.go:10` (`MediaFile.Location`) resolve uma `entity.Cell` (grade S2)
a partir de lat/lng — usada para clusterizar fotos por local na busca/mapa
sem comparar coordenada-a-coordenada. **Vale considerar** para o roadmap
item 1 (mapa com raio de incerteza, em execução na fase 9): quando o número
de círculos de incerteza no mapa crescer, uma grade de célula é a forma
padrão de bucketizar pontos para clustering visual sem custo O(n²) —
mecanismo simples (hash de lat/lng arredondado a uma resolução de grade),
não precisa da lib S2 inteira.

## 9. WebDAV, sharing, cluster, OAuth — não vale, domínio inteiro

`internal/server/routes_webdav.go`, `internal/api/links.go`,
`internal/api/oauth_*.go`, `internal/service/cluster/*`. Servidor WebDAV
para sync de terceiros, links de compartilhamento público com token,
servidor OAuth2/OIDC completo, topologia de cluster Portal↔Node.

**Não vale — descartar o domínio inteiro.** O foto-organizer é single-user,
desktop, com servidor que escuta só em `127.0.0.1` e recusa origem não
local (invariante 5). Não há segundo usuário para compartilhar com, não há
"outro node" para federar, e abrir um WebDAV de escrita sobre `Originals`
contradiria o invariante 1 (catalogação é somente leitura) a menos que fosse
estritamente read-only — e mesmo assim é superfície nova sem consumidor
identificado hoje. Isto espelha a mesma disposição que o `referencia-immich`
já deu a `storageLabel`/shared links/partners: multi-usuário puro.

## 10. Configuração, CLI e workers em background

**Precedência de configuração em camadas** (`options.yml` > CLI/env >
defaults) — mesmo padrão conceitual do config TOML do foto-organizer
(camadas de override), formato de arquivo diferente, ideia igual. Nada a
importar.

**Comandos destrutivos exigem `--yes`/`--force` explícito.**
`internal/commands/reset.go`, `purge.go --hard`, `users_reset.go`. Mesmo
padrão já adotado pelo foto-organizer (`scripts/verificar.sh`,
invariante de confirmação explícita para operação física). Confirma
convergência de desenho — nada a copiar, é validação de que a régua já
adotada aqui é a certa.

**Scheduler com "modo seguro" quando o intervalo é ≤ 0.**
`internal/workers/workers.go:75` (loop de ticker), `:88` (guarda de modo
seguro) — se `WakeupInterval <= 0`, os workers de background (metadados,
compartilhamento, sync, purge) desligam inteiramente, e isso só está
documentado no código, não no `--help`. Padrão pequeno mas útil de copiar
como convenção: um valor sentinela explícito ("0 desliga o worker") é mais
claro que uma flag booleana separada por job.

**Ticker de auto-reindex/auto-import por intervalo.**
`internal/workers/auto/index.go` — `mustIndex(delay)` compara o timestamp do
último gatilho contra o delay configurado e evita rodar se o worker de index
já estiver ativo (checagem via `mutex.IndexWorker.Running()`). É polling por
intervalo, não fs-watch (o watch por evento de filesystem já foi coberto no
`referencia-immich`, item "o" — `awaitWriteFinish`/chokidar). **Vale
considerar**, ligado diretamente ao item que falta no roadmap ("reencontrar
os arquivos"): o scanner do foto-organizer já detecta quando um volume
volta em outro ponto de montagem e se recusa a reescrever o caminho
sozinho (`sources/disponibilidade.py:99-107`, citado no roadmap); um ticker
periódico que testa "o volume que estava indisponível voltou?" e dispara
reconciliação automaticamente (em vez de esperar o usuário rodar a CLI
manualmente, `cli.py:156-158`) é exatamente esse padrão de polling barato,
sem precisar de fs-watch nem do overhead do chokidar.

---

## 11. Vale considerar vs. não vale, para o foto-organizer

### Vale considerar

| Mecanismo | Por quê | Esforço aproximado |
|---|---|---|
| **Empilhamento (stacking) de RAW+JPEG/capturas irmãs** (`index_mediafile.go`, `mediafile_related.go`) | Lacuna real hoje: `duplicates/` só agrupa hash idêntico/phash, não RAW+JPEG do mesmo clique (bytes diferentes, mesma cena). D-029 confirma câmeras Canon com esse padrão no acervo. | M — descoberta de arquivos relacionados antes de indexar + heurística por Document ID/metadado; reaproveita `related_files` já parcialmente coberto pelo scanner |
| **Backup automático com retenção + export YAML legível** (`backup/albums.go`, `backup/database.go`, `workers/backup.go`) | O catálogo carrega julgamento caro de recomputar (evidências, `papel`, `gps_estimado`). Hoje não há mecanismo formal de disaster recovery além de cópia manual do `.db`. | S — `sqlite3 .backup` agendado + dump legível (JSON/YAML) do que o usuário decidiu (papel, tags, plano de operação) |
| **Lock por hash durante indexação paralela** (`index_filehash.go`) | Fecha uma corrida real do scanner com `ThreadPoolExecutor`: duas cópias do mesmo arquivo processadas ao mesmo tempo por workers diferentes. Escritor único de DB já evita corrupção, mas não evita trabalho duplicado. | XS — um mutex por hash com contagem de referência, ~30 linhas |
| **Ticker de auto-reconciliação quando volume remonta** (`workers/auto/index.go`) | Ataca a causa raiz que o roadmap já identificou (D-028: 45.397 fotos em volume desmontado) — hoje a reconexão é manual via CLI. | S — polling periódico sobre `sources/disponibilidade.py`, sem fs-watch |
| **Verificação de integridade de miniatura antes de servir** (`thumb/verify.go`) | Barato, evita cache corrompido por escrita interrompida. | XS |
| **Célula geográfica para clustering do mapa** (`location.go`, S2 cell) | Insumo direto para o roadmap item 1 (mapa com raio de incerteza) quando o volume de círculos crescer. | S, e só quando o mapa precisar de clustering visual |
| **Cadeia de fallback ordenado para timezone** (padrão, não a ordem de fontes) | A *forma* — cadeia com fallback claro — é reaproveitável; a *ordem de fontes* (GPS→offset→default) não serve para este acervo e já foi corretamente reformulada no roadmap item 5 (país herdado). | já em andamento no roadmap |

### Não vale (calibrado pelo acervo real)

| Mecanismo | Por quê não |
|---|---|
| **Modo "mover" do import** (`import_options.go` `ImportOptionsMove`) | Contradiz diretamente o invariante 2 (copiar, nunca mover). Risco não compensa o benefício de organização de pasta. |
| **Faces/NSFW/labels de visão** (`index_faces.go`, `mediafile_vision.go`) | Mesma calibração dos itens 6/7/8 do roadmap: ~5% do acervo tem pixel legível hoje (D-028). Pipeline caro para alcance mínimo. |
| **Cadeia de conversores RAW externos (darktable/rawtherapee/sips)** | Não determinístico entre ambientes por design (débito documentado pelo próprio PhotoPrism); pillow-heif + rawpy já cobrem o essencial sem N binários CLI. |
| **Reverse geocoding via serviço hospedado por padrão** | Inverte a prioridade já decidida aqui (offline primeiro, invariante 4). O foto-organizer já está à frente nesse ponto. |
| **WebDAV/sharing/OAuth2/cluster** (domínio 07 inteiro) | Single-user, servidor local-only, sem segundo usuário nem node para federar. Superfície nova sem consumidor. |
| **Purge com soft/hard delete binário** (`purge.go`) | O `papel` ACERVO/SINAL deste projeto (D-024) já é estritamente melhor: preserva contribuição de correlação em vez de só marcar invisível/removido. |
| **Insta360 merge, dewarp fisheye, encoders de hardware de vídeo** | Fora do domínio do acervo real deste projeto (fotos de câmera/celular, não vídeo 360°/produção). |
| **`download` via yt-dlp** | Fora de escopo — o foto-organizer cataloga um acervo existente, não baixa mídia de URL externa. |
