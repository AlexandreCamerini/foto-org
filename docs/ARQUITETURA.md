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

## Módulo `classification/` — classificação de pasta por GenAI

Recurso opcional (Fase 7): quando as regras locais não conseguem preencher
cidade/país/categoria/evento de uma pasta, o dono pode pedir uma classificação
por Claude Sonnet 5 — nome de pasta e metadado já catalogado entram, nenhuma
imagem sai. Caminho completo, em ordem:

1. **Pré-filtro de candidatas** (`classification/candidatas_de_pasta.py::candidatas()`,
   D-01) — duas consultas agregadas sobre o catálogo (contagem/período por
   pasta + presença de `Evidence` por campo) combinadas em memória, nunca uma
   consulta por pasta. `MediaFile.organizavel` filtra as duas consultas: uma
   miniatura de cache ou referência de catálogo externo (invariante 8) nunca
   entra em `n_fotos` nem "completa" um campo via `Evidence` presa a mídia
   não-acervo. Só pastas com campo realmente vazio e sem classificação
   anterior aparecem como candidatas.
2. **Confirmação do dono** — gate de dois consentimentos (ver D-080 abaixo):
   a chave mestra `[privacidade] servicos_externos` no TOML E o opt-in
   próprio do recurso (`classificacao_pasta_genai`, gravável pela UI). A
   conjunção dos dois é `SessaoDeClassificacaoDePasta.liberado()`
   (`fotoorganizer/server/genai_pasta.py`) — copiar o gate de um flag só (o
   padrão que `jobs.py::_advisor` usa para o Advisor de cluster) seria a
   regressão que este código deliberadamente evita, porque este recurso tem
   opt-in próprio, separado do consentimento já dado ao Advisor.
3. **Estimativa de custo** (`classification/custo_genai.py::estimar()`) —
   contagem LOCAL de tokens de entrada, com fator conservador (nunca abaixo
   do real), sempre `entrada_exata=False`; não toca rede. Decisão híbrida
   D-079 (ver Decisões registradas) resolve a colisão entre `count_tokens`
   (que transmitiria o payload só para contar) e o critério "nada sai antes
   de confirmar": a contagem exata (`contar_exato()`) só roda depois da
   confirmação, imediatamente antes da chamada real — mostrada no resumo
   pós-execução, não na prévia.
4. **Chamada única** (`classification/location_advisor.py::ClassificacaoDePastaClaude`,
   D-03) — UMA chamada `messages.create` por sessão para todas as pastas
   confirmadas, saída estruturada por JSON schema (`categoria` restrita ao
   vocabulário canônico de `engine.py::_CATEGORIAS_PASTA`), Sonnet 5 com
   thinking desabilitado. Payload por allowlist literal (nunca
   `asdict()`/`__dict__`): só `pasta`, `n_fotos`, `periodo`,
   `campos_a_preencher`, `ja_conhecido` saem — ver docs/PRIVACIDADE.md para a
   declaração completa. Três filtros aplicados sobre a RESPOSTA do modelo,
   nessa ordem: pasta não pedida é descartada (anti-alucinação); item cujos 4
   campos de valor vêm todos `null` não vira proposta (D-06); campo que já
   está em `ja_conhecido` é zerado mesmo que o modelo o tenha devolvido (D-02
   reaplicada no código, não só no prompt — obediência do modelo nunca é
   pré-requisito de segurança). Never-crash em todo caminho de falha (rede,
   `refusal`, JSON inválido, 429).
5. **Persistência** (tabela `pasta_classificacoes_genai`, modelo
   `PastaClassificada` em `models/pasta_classificacao.py`,
   `repositories/pasta_classificacao.py::ClassificacaoPastaRepository`) —
   guarda de escrita por CAMPO (mais estrita que `LexicoRepository`, que é
   por linha): cidade/país/categoria/evento já preenchidos nunca são
   sobrescritos, mesmo por proposta discordante, e uma linha `origem="manual"`
   é inteiramente intocável. `status` (proposta/aprovada/descartada) é eixo
   separado de `origem` (llm/manual); só `status="aprovada"` é lido pela
   cascata. `descartar()` nunca apaga linha (invariante 8) — rebaixa status.
   **Por que a tabela existe:** `Evidence` é regenerada do zero a cada
   `SuggestionEngine.gerar()` (varredura determinística completa); sem uma
   tabela própria, a regeneração apagaria o resultado já pago à Anthropic. A
   tabela sobrevive à regeneração e é a fonte que `gerar()` relê a cada
   chamada, nunca a API.
6. **Aprovação** — o dono revisa antes/depois por pasta (agrupado por pasta,
   não por campo, mesmo achatamento de `PastaClassificada` por campo do
   backend reagrupado no cliente) e aprova seletivamente; `aprovar()` nunca
   apaga linha rejeitada, só a mantém fora de `status="aprovada"`.
7. **Degrau `llm_pasta` na cascata do `SuggestionEngine`**
   (`classification/engine.py`) — entra como FALLBACK explícito, só decide
   quando todo passo determinístico e o Advisor de cluster já falharam:
   passo 2c em `_evidencias_geo` (país/cidade, entre a hierarquia de pasta e
   a vizinhança de sessão) e passo 3b em `_categoria` (depois do Advisor de
   cluster). `evento` da proposta só preenche quando nenhum draft de campo
   "evento" já existe (sessão de viagem/evento sempre tem precedência).
   `SCORES_REFERENCIA["llm_pasta"]` = 0.55 — medido contra o acervo real
   (D-081), chave separada de `llm` mesmo com o mesmo número, porque afirma
   sobre uma coisa diferente (nome de pasta, uma vez por sessão, não
   metadado de mídia individual via Advisor de cluster) — `docs/CONFIANCA.md`
   proíbe fundir origens de natureza distinta mesmo com score idêntico.
8. **`Evidence` re-derivada a cada `gerar()`** — `SuggestionEngine` recebe
   `pastas_classificadas` (dict de `PropostaDePasta` aprovadas, lido em lote
   uma vez no `__init__`, mesmo padrão de `lexico`), resolvido uma vez por
   mídia dentro do laço, zero consultas novas. Cada rodada de "Gerar/
   atualizar sugestões" relê a tabela e reconstrói a `Evidence` de origem
   `llm_pasta` do zero — nenhuma chamada nova à Anthropic acontece numa
   segunda geração; é exatamente por isso que o passo 5 existe.

**API e UI:** sete endpoints `/api/genai-pasta/*` em `fotoorganizer/server/app.py`
(`GET`/`PUT config`, `GET candidatas`, `POST estimar-custo`, `POST rodar`,
`GET propostas`, `POST aprovar`) — gate fechado responde 409, falha do
classificador que escapa do próprio contrato never-crash responde 502 com a
razão técnica. `webapp/src/components/ClassificacaoPasta.tsx` é o assistente
modal (passos 0 gate → 1 candidatas/seleção opt-out → 2 custo → 3 chamada em
voo não-cancelável → 4 revisão antes/depois → 5 concluído com custo real); o
ponto de disparo é o botão "Classificar pastas por IA…" dentro de
`Review.tsx` (Revisão), que também ganha a pastilha "IA · pasta" no `PorQue`
para qualquer evidência de origem `llm_pasta` já aprovada.

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
| 9 | Classificação de pasta por GenAI: prévia de custo híbrida — estimativa local antes de confirmar, contagem exata só depois (D-079); opt-in próprio em `application_settings`, não em `PrivacySettings`/TOML (D-080); score `llm_pasta` medido contra o acervo real, não herdado por analogia (D-081) | `count_tokens` transmite o payload inteiro só para contar — rodá-lo antes de confirmar violaria o critério "nada sai antes de confirmar"; a UI precisa GRAVAR o opt-in do recurso, e `PrivacySettings` é `frozen`/só-leitura do TOML; um score por analogia viraria verdade de base não checada para o índice de saúde da Fase 10 (mesma classe de bug de D-071). |

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
