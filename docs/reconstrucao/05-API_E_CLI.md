# 05 — API HTTP local, jobs e CLI

Escopo: `fotoorganizer/server/` (FastAPI em 127.0.0.1), `fotoorganizer/cli.py`
e `fotoorganizer/config/settings.py`. **62 rotas**, **12 subcomandos**.

---

## 1. Servidor: como sobe

### 1.1 `cmd_web` (`fotoorganizer/cli.py:615-682`)

Sequência exata:

1. `settings = _settings(args)` e `settings.ensure_dirs()` (`:637-638`) —
   cria `data_dir`, `cache_dir`, `log_dir`.
2. `setup_logging(settings.log_dir)` (`fotoorganizer/app/logsetup.py`,
   chamado em `:643-645`). Log **em arquivo**, não só stderr: o servidor
   morre junto com o terminal que o abriu, e dois scans do acervo real (93
   mil e 225 mil arquivos) morreram sem uma linha de log que dissesse por quê.
3. `upgrade_to_head(settings.db_path)` (`:646`) — migra antes de servir.
4. `factory = create_session_factory(create_db_engine(settings.db_path))`
   (`:647`).
5. `app = create_app(settings, factory)` (`:648`).
6. **Socket criado à mão** (`:650-653`): `AF_INET`/`SOCK_STREAM`,
   `SO_REUSEADDR`, `bind(("127.0.0.1", args.porta))`. Só loopback, nunca
   `0.0.0.0`. `--porta 0` faz o SO escolher; a porta efetiva é lida de
   `sock.getsockname()[1]`.
7. **Anúncio**: `print(f"FOTOORG_READY {url}", flush=True)` (`:658`). É a
   linha estável que o supervisor (shell Tauri) lê para descobrir a porta
   efêmera. Antes dela sai uma linha humana com a URL e o caminho do
   catálogo (`:656`).
8. `--encerrar-com-pai` (`:664-678`): thread daemon que a cada 2 s compara
   `os.getppid()` com o pai original; se mudou (o app pai morreu de
   qualquer forma), manda `SIGTERM` em si mesma — uvicorn drena e faz o
   checkpoint WAL. Sem backend órfão.
9. `uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[sock])`
   (`:680-681`). O `uvicorn.Server` instala handlers de SIGINT/SIGTERM.

Default de porta: `8765` (`:741`).

### 1.2 Middleware Host/Origin (`fotoorganizer/server/app.py:450-470`)

Escutar só no loopback impede acesso pela rede mas **não** impede que uma
página qualquer aberta no navegador do usuário chame o servidor: POST sem
corpo é "simple request" e vai sem preflight (`:97-101`).

```
_HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1"}   # app.py:102
```

Em **toda** requisição:
- `Host` cujo hostname não está em `_HOSTS_LOCAIS` → **403** `{"detail": "host não local"}` (`:459-461`). Denuncia DNS rebinding.
- `Origin` **presente** e não-local → **403** `{"detail": "origem não permitida"}` + `log.warning` (`:463-469`). Denuncia página de terceiros.
- `Origin` **ausente** (curl, CLI, navegação na própria página) → segue normal.

`_hostname()` (`:105-112`) usa `urlsplit`, com `//` prefixado quando o valor
não tem esquema (caso do `Host`), e devolve `None` em `ValueError`.
Testes: `tests/test_server_api.py::test_pagina_externa_nao_dispara_acoes`,
`::test_host_nao_local_e_recusado`,
`::test_origem_local_e_ausencia_de_origem_seguem_normais`.
Achado **B1**: `localhost` sem porta no guard.

### 1.3 Startup hooks

- `@app.on_event("startup") _reconciliar_scans` (`:1603-1614`): chama
  `scanner.reconciliar_orfas(session_factory)`. `RODANDO` no banco com o
  servidor nascendo agora é sempre órfã → vira `INTERROMPIDO`, e a UI
  oferece retomar. Envolvido em `try/except Exception` com `log.warning` —
  falha aqui não impede o servidor de subir.
- `@app.on_event("startup") _conferir_fontes` (`:1616-1632`): chama
  `sources.disponibilidade.verificar(session_factory)`, que atualiza
  `Source.disponivel`/`visto_em`/identidade de volume. Custa um `diskutil`
  por fonte, uma vez no boot. Sem isto, quem plugou o disco antes de abrir
  o app veria tudo fora de alcance. Também protegido por `try/except`.

### 1.4 Frontend estático e imagens

- `webapp/dist` é montado em `/` com `StaticFiles(..., html=True)`
  **apenas se o diretório existir** (`:1598-1601`). `_WEBAPP_DIST =
  Path(__file__).resolve().parents[2] / "webapp" / "dist"` (`:242`). No
  runtime empacotado isso resolve para `site-packages/webapp/dist`, e é por
  isso que `scripts/empacotar_runtime.sh` copia o build para lá.
- **Montado por último**, depois de todas as rotas `/api/*` — o catch-all
  não engole a API.
- Thumbnails: `GET /api/midia/{id}/thumb` serve do `ThumbnailCache`
  (`settings.cache_dir`), chaveado por `hash_rapido`, `Cache-Control:
  max-age=31536000` (`:842-851`).
- Preview grande (loupe): `GET /api/midia/{id}/preview`, `_PREVIEW_SIZE =
  2048` (`:240`), gerado sob demanda em `<cache_dir>/previews/<xx>/<hash>.jpg`
  (`:859-867`).

### 1.5 Composição do app (`create_app`, `:438-495`)

Recebe `settings` e `session_factory`; o terceiro parâmetro
`classificador_pasta_genai` é **só para teste** (injeta um classificador
falso sem rede). Instancia uma vez, em closure: `MediaRepository`,
`SuggestionRepository`, `DuplicateRepository`, `OperationRepository`,
`SettingsRepository`, `OperationPlanner`, `OperationExecutor`,
`ExifWriteRepository`, `ExifWritePlanner`, `ExifWriteExecutor`,
`ThumbnailCache`, `JobManager`, `SessaoDeClassificacaoDePasta` (`:480-495`).

Helper transversal `_fontes_fora_de_alcance()` (`:472-478`): **uma**
consulta por requisição devolvendo os ids de fontes com
`disponivel=False` — em vez de um `stat` por miniatura, que transformaria
rolagem em espera num NAS.

---

## 2. As 62 rotas

Convenções da tabela: "Efeito" diz se **lê** catálogo, **escreve**
catálogo, **dispara job** (background, um por vez) ou **toca filesystem**.
"Consumidor" cita `webapp/src/api.ts` (ou `webapp/src/hooks/useJob.ts`)
com a linha; "sem consumidor" é literal.

### 2.1 Status e fontes

| # | Rota | Params | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|---|
| 1 | `GET /api/status` (`:498-501`) | — | — | `{versao, total, erros, fontes, referencias, referencias_com_gps}` — `media_repo.estatisticas()` (`repositories/media.py:593-183`) | lê | `api.ts:578` | — |
| 2 | `GET /api/funil` (`:503-519`) | — | — | `{conhecidas, alcancaveis, organizaveis, registros}` | lê (caro: ~1,4 s em 197 mil linhas — o cliente cacheia e só refaz quando um job termina) | `api.ts:670` | — |
| 3 | `GET /api/fontes` (`:521-533`) | — | — | `[{id, caminho, apelido, tipo, disponivel, fotos}]` | lê | `api.ts:580` | — |
| 4 | `GET /api/fontes/reapontamentos` (`:535-554`) | — | — | `[{source_id, apelido, prefixo_antigo, prefixo_novo}]` — só fontes cujo volume voltou noutro ponto | lê + **toca filesystem** (`verificar()` roda `diskutil`/`mount` por fonte; também **escreve** `Source.disponivel`/`visto_em`) | `api.ts:584` | — |
| 5 | `POST /api/fontes/{source_id}/reapontar/preview` (`:568-587`) | path `source_id` | — | `{source_id, apelido, prefixo_antigo, prefixo_novo, total_media_files, total_ignoradas_sem_prefixo, amostra:[{antigo,novo}]}` | lê + filesystem (nada é escrito) | `api.ts:586` | 404 fonte não encontrada; **409** `ReapontamentoInaplicavel` |
| 6 | `POST /api/fontes/{source_id}/reapontar` (`:589-607`) | path `source_id` | `{confirmar: bool}` | `{source_id, prefixo_antigo, prefixo_novo, linhas_media_files, audit_log_id}` | **escreve catálogo** (`Source.caminho` + N `MediaFile.caminho`, uma transação) + audit log; valida amostra no disco antes | `api.ts:594` | **422** sem `confirmar:true`; 404; **409** `ValidacaoFalhou` / `ReapontamentoInaplicavel` / `ColisaoDeCaminho` |

Confirmação explícita **no corpo**, não só o método POST — mesma disciplina
do `--confirmar` no CLI (`app.py:124-128`).

### 2.2 Mídia (leitura)

| # | Rota | Params | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 7 | `GET /api/midia` (`:610-648`) | query: `busca, extensao, source_id, ano, trip_id, event_id, lacuna, ordenacao="data_desc", alcance="tudo", mes, pasta, camera, pais, cidade, palavra_chave, offset=0, limit=200` | `{total, offset, itens:[_media_json]}` | lê | `api.ts:602` | **422** `lacuna` fora de `LACUNAS`; 422 `alcance` fora de `ALCANCES` |
| 8 | `GET /api/pastas` (`:650-658`) | query `prefixo` | `{caminho, aqui, filhos:[{nome, caminho, total, alcancaveis}]}` — **um nível por chamada** | lê | `api.ts:621` | — |
| 9 | `GET /api/midia/alcances` (`:660-662`) | — | `[{chave, rotulo}]` dos 3 alcances | lê (constante) | **sem consumidor** (achado **B8**) | — |
| 10 | `GET /api/midia/filtros` (`:664-674`) | — | `{extensoes, anos, cameras, paises, palavras_chave}` | lê | `api.ts:618` | — |
| 11 | `GET /api/midia/linha-do-tempo` (`:676-693`) | query `busca, extensao, source_id, ano, trip_id, event_id, lacuna, alcance` | `[{mes, quantidade,…}]` para a grade saltar | lê | `api.ts:630` | 422 alcance |
| 12 | `GET /api/panorama` (`:695-697`) | — | `{total, lacunas:[{chave,rotulo,quantidade}], por_ano, por_camera, por_extensao, cruzamento_ano_fonte}` | lê (agregações pesadas) | `api.ts:623` | — |
| 13 | `GET /api/inventario` (`:699-724`) | — | `{fotos, alcancaveis, registros, sem_caminho, lugares:[{raiz, fotos, alcancaveis, so_no_catalogo, fontes}]}` | lê | `api.ts:624` | — |
| 14 | `GET /api/midia/{media_id}` (`:726-785`) | path | `_media_json` + opcionais `local`, `estimativa`, `sugestao{…evidencias}` | lê | `api.ts:604` | 404 |
| 15 | `GET /api/midia/{media_id}/metadados` (`:787-813`) | path | `{total, namespaces:[{nome, rotulo, itens:[{chave,valor}]}]}` | lê | `api.ts:605` | — (devolve vazio) |

`_media_json` (`:304-340`) — campos: `id, nome, caminho, pasta, extensao,
tamanho, data_capturada, make, model, lente, largura, altura, gps_lat,
gps_lon, tipo_imagem (= tipo_efetivo), tipo_provisorio, gps_estimado,
gps_lat_efetivo, gps_lon_efetivo, tz_estimado, source_id, trip_id,
event_id, erro_leitura, motivo_indisponivel`.

`motivo_indisponivel` (`_motivo_indisponivel`, `:291-301`) tem três valores
possíveis e nenhum é genérico: `"sem arquivo neste Mac"`
(`arquivo_ausente`), `"volume ou pasta fora de alcance"` (fonte com
`disponivel=False`), `"arquivo sumiu do disco"` (`arquivo_offline`). `None`
quando dá para abrir. A interface precisa separar "miniatura ainda não
pronta" de "não tenho como abrir isto".

No detalhe (`:736-750`), o **lugar herdado é entregue só até onde o Δt
sustenta** (D-025): `_campos_do_lugar` (`:270-282`) devolve
`("pais","regiao","cidade")` para GPS lido, `("pais",)` quando não há
`gps_estimado_delta_s`, e o que `campos_confiaveis(Δt)` permitir nos demais
casos. `granularidade` é o último campo permitido.

### 2.3 Mídia (escrita) e imagens

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 16 | `POST /api/midia/{media_id}/tipo` (`:815-839`) | `{tipo: str \| null}` | `{tipo_imagem, tipo_provisorio}` | **escreve catálogo** (`tipo_confirmado`, `tipo_confirmado_em`) | `api.ts:608` | **422** tipo fora de `TIPOS_VALIDOS` (`classification/tipo_imagem.TIPOS`); 404 |
| 17 | `GET /api/midia/{media_id}/thumb` (`:842-851`) | — | `image/jpeg`, `Cache-Control: max-age=31536000` | lê + **toca filesystem** (gera no cache se faltar) | `api.ts:668` (`thumbUrl`) | 404 "sem miniatura" (sem `hash_rapido`), 404 "imagem indecodificável" |
| 18 | `GET /api/midia/{media_id}/preview` (`:853-867`) | — | `image/jpeg` 2048 px | lê + filesystem | `api.ts:669` (`previewUrl`) | 404 (idem) |

`tipo: null` **devolve a decisão ao detector** — grava `NULL` em
`tipo_confirmado` e `tipo_confirmado_em`.

### 2.4 Agrupamentos e mapa

| # | Rota | Params | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 19 | `GET /api/viagens` (`:917-920`) | query `source_id` | `[{id, nome, inicio, fim, metodo, fotos, capa_id}]` | lê | `api.ts:633` | — |
| 20 | `GET /api/eventos` (`:922-925`) | query `source_id` | idem | lê | `api.ts:635` | — |
| 21 | `GET /api/mapa` (`:928-1038`) | query `trip_id` **XOR** `event_id` | `{grupo, contagens:{total,no_mapa,sem_coordenada,fora_de_alcance}, pontos:[…], doadoras:[…], limites, escala, nota_do_raio}` | lê (nada recalcula, nada escreve, nada toca arquivo) | `api.ts:642` | **422** se informar os dois ou nenhum; 404 grupo |

`_agrupamentos` (`:884-915`) faz **uma** consulta agregada para o recorte
inteiro em vez de um `COUNT` por grupo (~190 grupos = N+1; sem os índices de
0017, cada um era um SCAN de 477 mil linhas — D-069 achado 3, D-072).
`_capa_disponivel` (`:870-882`) prefere foto com miniatura já em cache.

No mapa, **estar fora de alcance não tira a foto**: a coordenada está no
catálogo, o ponto é desenhado com `motivo_indisponivel` anexado (D-033,
invariante 8). Ponto herdado vira círculo, com `raio_m` e a frase `porque`
vindas de `grouping/correlacao.py` — a UI não remonta nenhum dos dois. Sem
`gps_estimado_delta_s`, o raio vai ao teto `RAIO_TETO_M` (`:389-395`), que é
a resposta honesta para "não sei há quanto tempo".

### 2.5 Configuração de template

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 22 | `GET /api/configuracoes/template` (`:1041-1043`) | — | `{template}` (default `TEMPLATE_PADRAO`) | lê | `api.ts:687` | — |
| 23 | `PUT /api/configuracoes/template` (`:1045-1062`) | `{template}` | `{template}` | **escreve catálogo** (`application_settings.template_destino`) | `api.ts:689` | **422** vazio; **422** placeholder inválido |
| 24 | `POST /api/configuracoes/template/preview` (`:1064-1071`) | `{template}` | `{exemplos:[{rotulo, campos, destino}]}` | puro (chama `render_destino` real) | `api.ts:691` | — |

Placeholders válidos (`PLACEHOLDERS_TEMPLATE_VALIDOS`, `:187-189`):
`categoria, ano, viagem, evento, pais, regiao, cidade`. Mudar essa lista sem
mudar `render_destino` quebra o contrato entre editor e motor.
Salvar **não** regenera sugestões de propósito (`:1058-1060`) — regenerar é
ação explícita separada.

### 2.6 Sugestões

| # | Rota | Params/Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 25 | `GET /api/sugestoes` (`:1074-1099`) | query `status="pendente", source_id, destino, offset=0, limit=200` (teto 500) | `{contagens:{status:n}, total, itens:[_sugestao_json]}` | lê | `api.ts:651` | **422** status inválido |
| 27 | `POST /api/sugestoes/gerar` (`:1128-1132`) | — | snapshot do job | **dispara job** `sugestoes` | `useJob.ts:140` | **409** "já existe um trabalho em andamento" |
| 28 | `POST /api/sugestoes/acao` (`:1134-1157`) | `{acao, ids?, destino?, source_id?, status="pendente"}` | `{afetadas: n}` | **escreve catálogo** | `api.ts:656` (por ids) e `api.ts:681` (por grupo) | **422** ação desconhecida / status inválido / nem `ids` nem `destino` |
| 29 | `GET /api/sugestoes/grupos` (`:1159-1184`) | query `status`, `source_id` | `[{destino, total, nivel, estimadas, fora_de_alcance, origens:[{pasta,fotos}]}]` | lê | `api.ts:675` | **422** status |
| 30 | `PATCH /api/sugestoes/{id}/destino` (`:1186-1198`) | `{destino}` | `_sugestao_json` | **escreve catálogo** | `api.ts:658` | **422** `CaminhoInvalido`; 404 |

Ações possíveis: `aprovar`, `rejeitar`, `desfazer`
(`acoes`, `:1136-1140`).
Com `destino` presente, a ação vale para o **grupo inteiro resolvido no
banco** (D-018): a tela não tem como mandar 2.406 ids — ela só carregou uma
página —, e era exatamente por isso que "Aprovar 85" aprovava 85 de um grupo
de 597 (`:134-137`). `status` importa aí: um `desfazer` age sobre aprovadas,
não sobre pendentes.
O `PATCH` de destino aplica a **mesma** sanitização do planejador
(`caminho_relativo_seguro`, invariante 5) — sem isso, `../../../etc` só
seria pego na hora do plano, e ainda assim como "conflito", não recusa.
Teste: `tests/test_server_api.py::test_editar_destino_recusa_path_traversal`.

### 2.7 Duplicatas

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 26 | `GET /api/duplicatas` (`:1101-1126`) | — | `[{id, nivel, rotulo, decidido, resolvido_automaticamente, bytes_recuperaveis, n_fontes, membros:[{member_id, media_id, nome, caminho, tamanho, papel, source_id}]}]` | lê | `api.ts:659` | — |
| 31 | `POST /api/duplicatas/detectar` (`:1200-1204`) | — | snapshot do job | **dispara job** `duplicatas` | `useJob.ts:141` | **409** ocupado |
| 33 | `POST /api/duplicatas/{group_id}/principal` (`:1216-1219`) | `{media_id}` | `{ok:true}` | **escreve catálogo** (papéis; marca decisão humana) | `Duplicates.tsx:175` | — |
| 34 | `POST /api/duplicatas/{group_id}/ignorar` (`:1221-1224`) | — | `{ok:true}` | **escreve catálogo** | `Duplicates.tsx:154` | — |
| 35 | `POST /api/duplicatas/{group_id}/desfazer` (`:1226-1229`) | — | `{ok:true}` | **escreve catálogo** (volta a `indefinido`, limpa `resolvido_automaticamente`) | `Duplicates.tsx:161` | — |

Nenhuma dessas rotas apaga arquivo. Qualquer uma das três marca **decisão
humana** e faz o grupo sobreviver à próxima redetecção
(`repositories/duplicates.py:187`).

### 2.8 Reconciliação de alcance

| # | Rota | Resposta | Efeito | Consumidor |
|---|---|---|---|---|
| 32 | `POST /api/reconciliacao` (`:1206-1214`) | snapshot do job | **dispara job** `reconciliacao`; lê filesystem (`Path.exists()` por linha), **escreve catálogo** (`arquivo_offline` + checkpoint) | **sem consumidor** (achado **B8**) |

Auto-limitada: termina sozinha dentro do orçamento e retoma na próxima
chamada de onde parou (checkpoint em `application_settings`). Erro: **409**
ocupado.

### 2.9 Operações físicas (plano → dry-run → execução)

| # | Rota | Params/Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 36 | `GET /api/operacoes` (`:1250-1252`) | — | `[_plano_json]` | lê | `api.ts:660` | — |
| 37 | `POST /api/operacoes` (`:1254-1270`) | `{raiz_destino, nome?}` | `_plano_json` | **escreve catálogo** (plano + itens + audit); **lê filesystem** (colisão de destino) | `api.ts:663` | **422** caminho não absoluto; **422** destino indisponível (nem a raiz nem o pai existem); **409** "nenhuma sugestão aprovada aguardando cópia" |
| 38 | `GET /api/operacoes/{id}` (`:1272-1290`) | — | `_plano_json` + `itens:[{id, origem, destino, status, conflito, erro}]` | lê | `api.ts:661` | 404 |
| 39 | `GET /api/operacoes/{id}/auditoria` (`:1292-1305`) | — | `[{id, quando, acao, resultado, detalhe}]` | lê | `api.ts:667` | 404 |
| 40 | `POST /api/operacoes/{id}/dry-run` (`:1307-1312`) | — | `{prontos, problemas:[str], bytes_necessarios, bytes_livres, espaco_suficiente}` | **lê filesystem**; **escreve catálogo** (`dry_run_em` + audit `dry_run`) | `api.ts:665` | 404 |
| 41 | `POST /api/operacoes/{id}/executar` (`:1314-1323`) | — | snapshot do job | **dispara job** `operacao` → **escreve filesystem** (cópia) | `useJob.ts:143` | 404; **409** "rode o dry-run antes de executar"; **409** ocupado |

`_plano_json` (`:1232-1248`): `id, nome, status, dry_run_em, criado_em,
total_itens, concluidos, com_conflito, com_erro, prontos, problemas,
executavel`. `prontos`/`problemas` vêm do **último dry-run lido do audit
log**, nunca copiados para a tabela do plano (duas verdades divergiriam —
`repositories/operations.py:86-101`). `executavel = dry_run_em is not None
and bool(prontos)`.

A raiz pode ainda não existir (a cópia cria as pastas), mas o **volume que a
contém** precisa existir — senão o plano nasce apontando para um disco
desconectado (`:1259-1263`).

### 2.10 Escrita EXIF de localização (D-075)

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 42 | `GET /api/exif` (`:1375-1377`) | — | `[_plano_exif_json]` | lê | `api.ts:692` | — |
| 43 | `POST /api/exif/plano` (`:1379-1391`) | **sem corpo** (escopo global, escrita in-place: não há raiz a escolher) | `_plano_exif_json` | **escreve catálogo**; **não toca o disco** | `api.ts:696` | **409** "nada a gravar — todo arquivo catalogado já tem localização preenchida ou não tem valor inferido" |
| 44 | `GET /api/exif/{id}` (`:1393-1401`) | — | plano + `itens:[_item_exif_json]` | lê | `api.ts:693` | 404 |
| 45 | `POST /api/exif/{id}/dry-run` (`:1403-1409`) | — | `{prontos, problemas:[str], campos_a_gravar, sidecars, nao_suportados, sincronizados}` | **lê filesystem** (dump exiftool em lote); **escreve catálogo** (status por campo + `dry_run_em` + audit) | `api.ts:698` | 404 |
| 46 | `POST /api/exif/{id}/executar` (`:1411-1425`) | `{itens: int[] \| null}` | snapshot do job | **escreve catálogo** (seleção) e depois **dispara job** `escrita_exif` → **escreve filesystem** (mutação in-place ou sidecar) | `useJob.ts:147` | 404; **409** "rode o dry-run antes de gravar"; **409** "nenhum item selecionado para gravar"; **409** ocupado |
| 47 | `GET /api/exif/{id}/auditoria` (`:1427-1440`) | — | `[{id, quando, acao, resultado, detalhe}]` | lê (filtra por `detalhe["exif_plan_id"]`, nunca pela coluna `plan_id`) | `api.ts:700` | 404 |

`itens: null` **preserva** a seleção persistida (D-02); lista vazia **zera**
a seleção — o endpoint distingue os dois casos (`app.py:161-166`,
`exif_write/executor.py:258-278`). A seleção é persistida **antes** de o job
começar, para sobreviver à troca de thread e ficar na auditoria.

`_plano_exif_json` (`:1327-1344`): `id, nome, status, dry_run_em, criado_em,
total_itens, prontos, problemas, campos_a_gravar, sidecars, nao_suportados,
sincronizados, gravados, com_erro, executavel`.
`_item_exif_json` (`:1346-1373`): `id, media_id, origem, nome, incluido,
formato_suportado, motivo_nao_suportado, sidecar_destino,
pasta_sincronizada, erro, backup_original, campos:{gps|cidade|pais:
{valor, status, motivo}}`. Os três campos vão num sub-objeto porque a UI os
renderiza como chips irmãos.

### 2.11 Trabalhos em background

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 48 | `POST /api/scan` (`:1443-1450`) | `{caminho}` | snapshot | **dispara job** `scan` | `useJob.ts:135` | **422** pasta não encontrada; **409** ocupado |
| 49 | `POST /api/importar` (`:1452-1467`) | `{tipo: "apple_photos"\|"google_takeout", caminho?}` | snapshot | **dispara job** `import` | `useJob.ts:137,139` | **422** tipo desconhecido / falta `caminho` do Takeout / pasta não encontrada; **409** ocupado |
| 50 | `GET /api/scan/interrompidos` (`:1469-1507`) | — | `[{source_id, caminho, apelido, disponivel, quando, vistos, indexados}]` | lê | `api.ts:672` | — |
| 51 | `GET /api/job` (`:1509-1511`) | — | snapshot | lê memória | `useJob.ts:35,80` | — |
| 52 | `POST /api/job/cancelar` (`:1513-1516`) | — | snapshot | sinaliza cancelamento | `useJob.ts:148` | — (nunca falha) |
| 53 | `POST /api/job/pausar` (`:1518-1522`) | — | snapshot | sinaliza pausa | `useJob.ts:117` | **409** "nenhum scan em andamento para pausar" |
| 54 | `POST /api/job/continuar` (`:1524-1528`) | — | snapshot | retoma | `useJob.ts:125` | **409** "nenhum scan pausado para continuar" |
| 55 | `GET /api/progresso` (`:1530-1545`) | — | **SSE** `text/event-stream`, `data: <json do snapshot>` | lê memória a cada 0,5 s | `useJob.ts:51` (`EventSource`) | — |

`/api/scan/interrompidos` só conta a sessão **mais recente** de cada fonte:
se um scan posterior concluiu, a interrupção antiga é história, não
pendência (`:1471-1477`). A retomada é um novo `POST /api/scan` no mesmo
caminho — o incremental pula o que já foi indexado.

O SSE emite só quando o snapshot **muda** e fecha assim que
`status != "rodando"` (`:1536-1543`). O cliente tem fallback de polling com
backoff 1→15 s (`useJob.ts:29-35`).

`POST /api/importar` **não** cobre Lightroom — esse caminho só existe pela
CLI (`fotoorganizer importar lightroom <.lrcat>`), e por um motivo real: o
Acesso Total ao Disco do macOS é concedido **por app**, então rodar do
terminal usa a permissão do terminal (`cli.py:406-408`).

### 2.12 GenAI de pasta (Fase 7)

| # | Rota | Corpo | Resposta | Efeito | Consumidor | Erros |
|---|---|---|---|---|---|---|
| 56 | `GET /api/genai-pasta/config` (`:1548-1550`) | — | `{servicos_externos, classificacao_pasta_genai}` | lê TOML + catálogo | `api.ts:701` | — |
| 57 | `PUT /api/genai-pasta/config` (`:1552-1557`) | `{habilitado}` | mesma forma | **escreve catálogo** (só o opt-in do RECURSO, nunca a chave mestra) | `api.ts:705` | **409** com a mensagem literal `MENSAGEM_MESTRE_DESLIGADO` quando `habilitado=true` e o mestre está off |
| 58 | `GET /api/genai-pasta/candidatas` (`:1559-1564`) | — | `[{pasta, n_fotos, campos_ausentes, periodo}]` | lê | `api.ts:707` | **409** `RecursoDesligado` |
| 59 | `POST /api/genai-pasta/estimar-custo` (`:1566-1571`) | `{pastas: str[]}` | `{tokens_entrada, entrada_exata, custo_entrada_usd, teto_tokens_saida, teto_custo_saida_usd, teto_custo_total_usd, teto_custo_total_brl, cambio_usd_brl, cambio_fonte}` | lê; **estimativa local, sem rede** | `api.ts:709` | **409** gate fechado |
| 60 | `POST /api/genai-pasta/rodar` (`:1573-1587`) | `{pastas: str[]}` | `{propostas:[{pasta,campo,valor_antes,valor_proposto,justificativa}], pastas_sem_resposta, custo_real}` | **sai da máquina** (uma chamada à API da Anthropic para a lista inteira); **escreve catálogo** (`pasta_classificacoes_genai` com `status='proposta'`) | `api.ts:711` | **409** gate fechado; **502** `ClassificacaoIndisponivel` com cópia de erro pronta |
| 61 | `GET /api/genai-pasta/propostas` (`:1589-1591`) | — | mesma forma de `propostas` | lê | `api.ts:713` | — (**não exige o gate**: o dono pode ter desligado o recurso e ainda precisar rever o que já pagou) |
| 62 | `POST /api/genai-pasta/aprovar` (`:1593-1595`) | `{pastas: str[]}` | `{aprovadas: n, descartadas: n}` | **escreve catálogo** (status) | `api.ts:716` | — |

Ver §4 para o ciclo completo.

---

## 3. Jobs em background (`fotoorganizer/server/jobs.py`)

### 3.1 Um por vez

`JobManager` guarda `_thread`, `_control` (`ScanControl`),
`_exec_control` (`ExecutionControl | None`), `_estado` (dict) e um
`threading.Lock` (`:41-51`). `_iniciar(tipo, alvo, funcao, *args)`
(`:149-163`) recusa se `ocupado()` (`:58-59` — thread viva), reseta o
`ScanControl`, escreve o snapshot inicial **sob o lock** e sobe uma
`threading.Thread(daemon=True, name=f"job-{tipo}")`.

> **Achado A1 (ALTO)**: o check-then-act de `ocupado()` está **fora** do
> lock (`:58,127,140,150-162`) e as rotas de execução são `def` síncronas
> (`app.py:1315,1412`), servidas em threadpool. Dois POST simultâneos
> iniciam duas threads no mesmo plano (reproduzido 55/200). Com EXIF, o
> segundo exiftool renomeia a versão modificada por cima do
> `.jpg_original`. `_exec_control` é sobrescrito (`:143`). Fix indicado:
> lock em `_iniciar`.

### 3.2 Tipos de job

| `tipo` | Partida | Executor | Controle | Pausável |
|---|---|---|---|---|
| `scan` | `iniciar_scan(caminho)` `:90-91` | `CatalogScanner.scan_source` | `ScanControl` cooperativo | **sim** |
| `import` | `iniciar_import_apple()` `:93-97` / `iniciar_import_takeout(caminho)` `:99-103` | `ExternalCatalogImporter.importar` | — | não |
| `sugestoes` | `iniciar_sugestoes()` `:105-108` | `SuggestionEngine.gerar()` | — | não |
| `duplicatas` | `iniciar_duplicatas()` `:110-113` | `DuplicateDetector.detectar()` | — | não |
| `reconciliacao` | `iniciar_reconciliacao()` `:115-122` | `scanner.reconciliacao.reconciliar` | `ScanControl` (só cancelar) | não |
| `operacao` | `iniciar_execucao(plan_id)` `:124-134` | `OperationExecutor.executar` | `ExecutionControl` próprio | não |
| `escrita_exif` | `iniciar_escrita_exif(plan_id)` `:136-147` | `ExifWriteExecutor.executar` | `ExecutionControl` próprio | não |

`ExecutionControl` nasce **na thread do pedido** (`:129-130`, `:142-143`)
para que um cancelamento imediato não se perca.

### 3.3 Snapshot de estado

`estado()` (`:54-56`) devolve uma **cópia** do dict sob o lock. Forma
inicial (`:154-158`):
`{status:"rodando", tipo, alvo, vistos:0, processados:0, pulados:0, erros:0, arquivos_por_segundo:0.0}`.
Quando não há job: `{"status": "nenhum"}` (`:51`).

Valores de `status`: `nenhum` · `rodando` · `pausado` · `concluido` ·
`cancelado` · `erro` (+ o `scan.status.value` que o scan devolve, que pode
ser `pausado` ou `concluido`). Em erro entra `mensagem`; ao terminar, cada
job acrescenta `resultado` com o dict do executor.

O que cada job escreve no fim:
- scan: `status=scan.status.value`, `vistos/processados/pulados/erros`.
- import: `status="concluido"` + contadores; em falha,
  `_mensagem_falha_import` (`:384-399`) — se for `ApplePhotosError`, a
  mensagem já traz a orientação de TCC; se for `PermissionError` em
  qualquer ponto da cadeia de causas (`_erro_de_permissao`, `:370-381`) num
  `ApplePhotosProvider`, acrescenta a instrução de Acesso Total ao Disco.
- sugestões: `processados = resultado["sugestoes"]`.
- duplicatas: `processados = soma dos níveis exceto "preservados"`.
- reconciliação: `status` = `cancelado`/`concluido`, `processados =
  verificados`, `resultado = {verificados, marcados_offline,
  marcados_online, ciclo_concluido}`.
- operação: `status` = `cancelado`/`concluido`, `processados = copiados`.
- escrita EXIF: `processados = gravados + sidecars` — a forma "copiados" do
  analog não existe aqui porque o resultado é por campo/rota de escrita.

### 3.4 Pausa, continuação, cancelamento

- `pausar()` (`:67-78`) só funciona para `tipo == "scan"` e
  `status == "rodando"`; devolve `False` **sem efeito colateral** para a
  rota responder 409 em vez de estourar. Só o scan tem pausa cooperativa.
- `continuar()` (`:80-87`): espelho, exige `status == "pausado"`.
- `cancelar()` (`:61-65`): **primeiro** `continuar()`, depois `cancelar()`
  no `ScanControl` — um job pausado precisa acordar para ver o
  cancelamento —, e propaga para o `ExecutionControl` se existir.
  Achado **B3**: `_exec_control` nunca é limpo depois do job.

### 3.5 Advisor (opt-in)

`_advisor()` (`:333-343`): devolve `None` se
`settings.privacidade.servicos_externos` for falso — **100% local**. Com
opt-in, tenta importar `ClaudeAdvisor` e, em qualquer falha, loga e segue
local.

---

## 4. GenAI de pasta (`fotoorganizer/server/genai_pasta.py`)

`SessaoDeClassificacaoDePasta` (`:113-381`) liga persistência, cliente
Claude e pré-filtro de custo atrás de um gate.

### 4.1 O gate de dois consentimentos

`liberado()` (`:129-135`) = **conjunção**:
`settings.privacidade.servicos_externos` (chave MESTRA, invariante 4,
**só TOML**) **E** `SettingsRepository.genai_pasta_habilitado()` (opt-in
PRÓPRIO do recurso, gravável pela UI — D-080).

Copiar o gate de um flag só, como `jobs.py::_advisor` faz para o Advisor de
cluster, é a regressão nomeada em `07-RESEARCH.md` Pitfall 4: este recurso
**não pega carona** no consentimento já dado ao Advisor.

Duas mensagens literais, reusadas pela UI sem paráfrase:
`MENSAGEM_MESTRE_DESLIGADO` (`:42-45`) e `MENSAGEM_GATE_FECHADO` (`:51-55`).

`habilitar(True)` com o mestre desligado levanta `ValueError` → 409.

### 4.2 Estados de uma sessão

`pasta_classificacoes_genai.status`: `proposta` → `aprovada` **ou**
`descartada`. Nada é apagado em nenhum caminho (invariante 8).

Ciclo (o assistente da UI tem passos numerados):
1. **config** (`GET`/`PUT /api/genai-pasta/config`) — o gate.
2. **candidatas** (`GET .../candidatas`) — pastas com campo ausente,
   calculadas por `classification.candidatas_de_pasta.candidatas(session,
   conhecidas)` (`:171-180`).
3. **estimar-custo** (`POST .../estimar-custo`) — monta o corpo da chamada e
   estima tokens **localmente**, sem rede (D-079). Sessão vazia devolve
   zero sem sequer resolver o classificador (`:238-243`).
4. **rodar** (`POST .../rodar`) — **uma** chamada para a lista inteira
   (D-03). Grava as propostas com o carimbo ISO-8601 da sessão. Devolve
   `pastas_sem_resposta` (pedidas menos respondidas) e `custo_real`
   (contagem exata de tokens, só **depois** da chamada — mesma transmissão
   já consentida; `None` quando o classificador é local/nulo ou a contagem
   falhou).
5. **propostas** (`GET .../propostas`) — permite reabrir uma sessão já paga
   depois de um refresh do navegador sem pagar de novo.
6. **aprovar** (`POST .../aprovar`) — aprova as listadas e **descarta** as
   demais que estavam em `proposta` (`:373-381`).

`_payloads` (`:182-231`) **reconcilia contra as candidatas reais**: pasta
pedida que já saiu da lista (o catálogo mudou, ou outra sessão a
classificou) é ignorada em silêncio, não vira erro. Nunca confia cegamente
no corpo da requisição.

Resolução do classificador (`:153-168`): injetado (teste) → se o gate está
fechado, `ClassificacaoDePastaNula` → senão `ClassificacaoDePastaClaude`,
e qualquer falha de import cai no nulo com `log.warning`. Never-crash em
três camadas; a de fora converte em 502 com cópia pronta.

> **Achado M2 (MÉDIO)**: o que segue no payload é o caminho **absoluto** da
> pasta (`scanner.py:443` → `candidatas_de_pasta.py:72` →
> `genai_pasta.py:224-230` → `location_advisor.py:203`), enquanto
> `docs/PRIVACIDADE.md`, a docstring do módulo e a UI prometem "nome da
> pasta". A UI mostra `pastaCurta()`, o que mascara a divergência.

---

## 5. Os 12 subcomandos da CLI

`fotoorganizer/cli.py`. Entrypoint `main(argv)` (`:842-852`) →
`_build_parser()` (`:685-839`) → `args.func(args)`. `ErroDeUso` (de env var
inválida) vira `parser.error()` — usage no stderr, código 2, nunca
traceback.

### 5.1 Flags globais (antes do subcomando)

Terceira camada de precedência sobre `Settings`. `default=UNSET` distingue
"flag não passado" de "passado com valor vazio/zero/false" (`:691-695`).

| Flag | Env | Tipo | O que faz |
|---|---|---|---|
| `--data-dir PASTA` | `FOTOORG_DATA_DIR` | str | outro catálogo em vez de `~/Library/Application Support/FotoOrganizer`. **Sozinho também deriva `cache_dir`** (`:126-132`), como camada *derivada* (perde para o TOML) |
| `--cache-dir PASTA` | `FOTOORG_CACHE_DIR` | str | outro cache de thumbnails |
| `--workers N` | `FOTOORG_WORKERS` | int | workers paralelos do scanner |
| `--incluir-ocultos` / `--no-incluir-ocultos` | `FOTOORG_INCLUIR_OCULTOS` | bool | varre arquivos/pastas ocultos |
| `--seguir-symlinks` / `--no-seguir-symlinks` | `FOTOORG_SEGUIR_SYMLINKS` | bool | atravessa symlinks — **desligado por padrão** |
| `--servicos-externos` / `--no-…` | `FOTOORG_SERVICOS_EXTERNOS` | bool | permite serviços externos opt-in |

`privacidade.reconhecimento_facial` fica **de fora desta camada de
propósito** (`:724-729`): ligar reconhecimento facial (invariante 6) tem de
ser decisão escrita na config do usuário, não algo que um script de CI, um
alias de shell ou uma env var herdada consigam ligar de passagem.

Booleanos de env aceitos (`:37-38`): verdadeiro
`1,true,verdadeiro,sim,yes,on`; falso `0,false,falso,nao,não,no,off`.
Valor irreconhecível é **erro de uso**, nunca palpite (`:75-81`).
Env var exportada **vazia** conta como ausente (`:50-63`) — tratar `""`
como valor explícito fazia `data_dir` virar `Path('.')` e o scan criar um
catálogo novo no diretório corrente do shell.

### 5.2 Os subcomandos

| # | Nome | Argumentos / flags | O que faz | Saída | Quando usar vs UI |
|---|---|---|---|---|---|
| 1 | `scan` (`:732-738`, `cmd_scan:219-236`) | `pastas...` (1+), `--reprocessar` | varre pastas para o catálogo, **somente leitura** sobre as fotos | linha de progresso viva (`vistos/indexados/pulados/erros/arq-s`) e resumo por pasta | headless, script, ou quando a UI não está aberta. `--reprocessar` relê arquivo inalterado para capturar metadado que a extração passou a ler — **não existe na UI** |
| 2 | `web` (`:740-747`, `cmd_web:615-682`) | `--porta N` (default 8765), `--encerrar-com-pai` | sobe a UI web em 127.0.0.1 | `FOTOORG_READY <url>` no stdout | é a forma normal de abrir o app; `--porta 0` + `--encerrar-com-pai` é o que o shell Tauri usa |
| 3 | `importar` (`:749,793-804`, `cmd_importar:405-460`) | `fonte` ∈ `{apple, takeout, lightroom}`; `caminho` opcional; `--ler-arquivos` | importa catálogo externo, somente leitura | progresso + `N importados, N pulados, N erros` | **necessário** para Lightroom (sem rota HTTP) e preferível para Apple Fotos: o TCC do macOS concede Acesso Total ao Disco **por app**, e rodar do terminal usa a permissão do terminal (`:406-408`) |
| 4 | `volumes` (`:753-755`, `cmd_volumes:265-291`) | — | onde cada fonte está e o que está fora de alcance | marca `✓` disponível, `→` mudou de lugar, `·` na gaveta; identidade de volume e aviso de identidade frágil | diagnóstico de disco; a UI só mostra a affordance de reapontar |
| 5 | `inventario` (`:757-759`, `cmd_inventario:239-262`) | — | o que existe e onde, inclusive fora de alcance | fotos conhecidas × alcançáveis, por raiz, + referências de nuvem | equivale a `GET /api/inventario` |
| 6 | `reapontar` (`:761-780`, `cmd_reapontar:294-377`) | `fonte` (id ou apelido, opcional com `--desfazer`), `--confirmar`, `--desfazer AUDIT_LOG_ID` | reescreve o catálogo para onde um volume remontado voltou — **nunca toca em arquivo** | dry-run com amostra `antigo → novo`; com `--confirmar`, `N linha(s) reapontada(s) (audit_log N)` | `--desfazer` é **só CLI** (recuperação, não fluxo normal — `sources/reapontar.py:320-322`) |
| 7 | `verificar-arquivos` (`:782-791`, `cmd_verificar_arquivos:380-402`) | `--segundos N` | uma passada da reconciliação de alcance, auto-limitada, read-only sobre metadado | `N verificado(s): N offline, N online`; diz se o ciclo fechou ou se retoma daqui | a rota `/api/reconciliacao` existe mas **não tem consumidor na UI** (B8) — hoje este é o caminho real |
| 8 | `planos` (`:806-807`, `cmd_planos:463-477`) | — | lista os planos de operação | por plano: status, itens, copiados, conflitos, erros, e o **veredito legível do dry-run** (`_veredito_legivel:480-497`) | equivale a `GET /api/operacoes` |
| 9 | `plano` (`:809-814`, `cmd_plano:500-514`) | `destino` (raiz), `--nome` | cria plano de cópia das sugestões aprovadas | `Plano N criado: X itens para <raiz> (Y com conflito)` + próximo passo | equivale a `POST /api/operacoes` |
| 10 | `dry-run` (`:816-818`, `cmd_dry_run:517-530`) | `plano_id` | simula sem tocar em nada | prontos, MB necessários, GB livres, lista de problemas | equivale a `POST /api/operacoes/{id}/dry-run` |
| 11 | `executar` (`:820-824`, `cmd_executar:533-555`) | `plano_id`, `--confirmar` | copia os arquivos do plano | progresso `n/total` + `N copiados · N pulados · N erros`; **exit 1 se houve erro** | `--confirmar` é a aprovação explícita que o invariante 2 pede sem a UI (`:13-15`). Sem ele: recusa e sai 1 |
| 12 | `bench` (`:826-837`, `cmd_bench:566-612`) | `-n/--quantidade` (default 500), `--cache-dir PASTA` | benchmark de indexação com JPEGs sintéticos num diretório temporário | indexação a frio × re-scan, em arq/s | **nunca** toca o catálogo nem o cache reais por padrão; `--cache-dir` aqui é `dest="bench_cache_dir"`, distinto do global |

Observações que o reconstrutor não pode perder:
- `_abrir_catalogo` (`:173-184`) é o único caminho que abre o catálogo: faz
  `ensure_dirs()` + `upgrade_to_head()` + session factory.
- `_build_scanner` (`:187-207`) exige `settings` **de propósito**: enquanto
  era opcional e caía num `load_settings()` interno, quem esquecesse de
  passá-lo rodava só com defaults+TOML, pulando a camada de CLI/env sem
  nenhum sinal — foi assim que `bench` passou a ignorar `--workers`.
- `executar` devolve `1` quando `stats["erros"]` (`:555`), o que torna o
  comando utilizável em script.

---

## 6. Config (`fotoorganizer/config/settings.py`)

### 6.1 Campos

`Settings` (`:66-94`), frozen dataclass:

| Campo | Tipo | Default | Quem lê |
|---|---|---|---|
| `data_dir` | Path | `~/Library/Application Support/FotoOrganizer` (`paths.py:10-11`) | `db_path`, `log_dir`, `ensure_dirs` |
| `cache_dir` | Path | `~/Library/Caches/FotoOrganizer` (`paths.py:14-15`) | `ThumbnailCache` em `server/app.py:490`, `jobs.py:173,298,348`, `cli.py:206,451` |
| `scanner` | `ScannerSettings` | ver abaixo | `CatalogScanner`, `ExternalCatalogImporter` |
| `privacidade` | `PrivacySettings` | ver abaixo | `jobs._advisor:335`, `genai_pasta.liberado:133` |
| `campos_explicitos` | frozenset[str] | `frozenset()` | interno: proveniência, `compare=False` |

Propriedades: `db_path` = `<data_dir>/catalog.db`; `log_dir` =
`<data_dir>/logs`. `ensure_dirs()` cria os três diretórios.

`ScannerSettings` (`:51-55`):

| Campo | Default | Quem lê |
|---|---|---|
| `workers` | `4` | `scanner/scanner.py:231,258` (janela = `max(workers*2, 4)`), `sources/importer.py:88,115` |
| `incluir_ocultos` | `False` | `scanner/scanner.py:210` → `DiscoveryConfig` |
| `seguir_symlinks` | `False` | `scanner/scanner.py:211` → `DiscoveryConfig` (invariante 5) |

`PrivacySettings` (`:58-63`):

| Campo | Default | Quem lê |
|---|---|---|
| `servicos_externos` | `False` | invariante 4: nada sai da máquina enquanto for falso. `jobs.py:335`, `genai_pasta.py:133,139,148` |
| `reconhecimento_facial` | `False` | invariante 6. **Sem leitor de produção hoje** (faces é stub) |

### 6.2 TOML

Arquivo opcional em `~/Library/Application Support/FotoOrganizer/config.toml`,
lido com `tomllib`. Template comentado em `CONFIG_TEMPLATE` (`:34-48`);
`write_config_template()` (`:238-243`) grava **sem** sobrescrever config
existente.

```toml
[geral]
# data_dir = "~/Library/Application Support/FotoOrganizer"
# cache_dir = "~/Library/Caches/FotoOrganizer"

[scanner]
# workers = 4
# incluir_ocultos = false
# seguir_symlinks = false

[privacidade]
# servicos_externos = false
```

Degradação: erro de leitura ou TOML inválido → `log.error` + **defaults**
(`:171-173`), nunca derruba o app. Seção desconhecida (`[scaner]`) e chave
desconhecida são ignoradas **com aviso**, nunca em silêncio (`:105-143`).

### 6.3 Precedência

```
defaults (dataclass)  <  derivados de outro flag  <  TOML  <  CLI/env explícito
```

- `load_settings()` (`:146-185`) resolve as duas primeiras camadas
  (defaults + TOML) e registra em `campos_explicitos` o que o TOML tocou.
- `aplicar_overrides(settings, overrides, derivados)` (`:188-235`) aplica a
  camada derivada primeiro (só preenche o que ninguém definiu de propósito)
  e depois a explícita.
- `cli._overrides_de_cli_e_env` (`:97-157`) monta os dois dicts no formato
  de seções do TOML. Dentro dele, **flag de CLI vence env var** quando os
  dois aparecem na mesma invocação (`:111-115`) — decisão local ao módulo,
  porque o flag é ainda mais explícito.
- Hoje o único **derivado** é `cache_dir` deduzido de `--data-dir`.

Testes que fixam esta matriz: `tests/test_cli.py::test_flag_cli_sobrescreve_toml`,
`::test_env_var_usada_quando_flag_nao_veio_mas_flag_explicito_vence_env`,
`::test_cache_dir_explicito_vence_o_derivado_de_data_dir`,
`::test_data_dir_sozinho_nao_descarta_cache_dir_escrito_no_toml`,
`::test_env_var_de_caminho_vazia_nao_reaponta_o_catalogo_para_o_cwd`,
`::test_workers_zero_explicito_nao_e_confundido_com_nao_passado`.

---

## Lacunas e incertezas

1. **Schemas de resposta**: descrevi a forma que o handler monta, com as
   chaves exatas. Não transcrevi as **interfaces TypeScript** de
   `webapp/src/api.ts` (linhas 1-530) que as tipam do outro lado; se elas
   divergirem do que o servidor devolve hoje, não detectei.
2. **`GET /api/midia/linha-do-tempo`** — a forma exata de cada item vem de
   `MediaRepository.linha_do_tempo` (`repositories/media.py:470`), que eu
   não li linha a linha; sei que é "mês + contagem" pelo docstring do
   endpoint.
3. **`POST /api/duplicatas/{id}/*`** não têm tratamento de grupo
   inexistente visível no handler (`app.py:1216-1229`) — não determinei se
   o repositório levanta ou é no-op silencioso.
4. **`POST /api/importar`** não aceita `lightroom`, embora o provider
   exista. Não achei decisão registrada dizendo se é omissão deliberada ou
   dívida; o motivo plausível (permissão TCC do terminal) está documentado
   só para o comando de CLI.
5. **Rate limit / autenticação**: não há nenhum. O único controle é o
   middleware Host/Origin. Confirmei a ausência por leitura de
   `create_app`, não por varredura de middlewares de terceiros.
6. **`/api/progresso`**: não determinei o comportamento com **dois**
   clientes SSE simultâneos (duas janelas). Cada um abre seu próprio
   gerador lendo o mesmo snapshot; não há teste disso.
7. Os **códigos de erro** que listei são os levantados explicitamente nos
   handlers. Erros de validação de corpo do próprio Pydantic (422 com o
   formato do FastAPI) não foram enumerados caso a caso.
