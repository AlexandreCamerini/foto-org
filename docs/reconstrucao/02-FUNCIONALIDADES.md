# 02 — Funcionalidades: inventário com contrato

> Parte do mapa de reconstrução. Um bloco por funcionalidade, sempre com os 10 campos:
> Propósito · Gatilho · Entradas · Regras de negócio · Saídas · Degradação/falha · Estado ·
> Testes que provam · Decisões · Arquivos. Três partes por domínio, numeradas de forma
> independente: **F-A** (arquivos: scan, fontes, alcance, duplicatas por hash, operações
> físicas, escrita EXIF, segurança, config, empacotamento), **F-I** (imagem e inferência:
> metadados, thumbnails, evidências, cascata, agrupamento, herança de GPS, geolocalização,
> duplicatas visuais, GenAI, stubs) e **F-U** (experiência do usuário: o contrato de cada tela e
> fluxo). O backend de um F-U está no F-A/F-I correspondente; a UI de um F-A/F-I está no F-U.
> Cada parte termina com as lacunas declaradas pelo autor.

---

# Parte A — Arquivos (F-A)

# 02 — Inventário funcional do domínio ARQUIVOS

Uma funcionalidade por bloco, template fixo de 10 campos. "n/a" é literal.
Escopo: `scanner/`, `sources/`, `duplicates/` (hash exato), `operations/`,
`exif_write/`, `security/`, `server/jobs.py`, `config/`, empacotamento.

Detalhe de contrato em `04-PIPELINES.arquivos.md`; rotas e CLI em
`05-API_E_CLI.md`; tabelas em `03-DADOS.md`; integrações em
`07-INTEGRACOES.arquivos.md`.

Achados da auditoria de 2026-09-19 (`A1`-`B10`) são referenciados por id,
não re-auditados.

---

### F-A01 — Scan de pasta (descoberta + indexação incremental)
- Propósito: varrer uma raiz do filesystem e catalogar todo arquivo de mídia
  elegível, somente leitura sobre as fotos. É a porta de entrada do acervo.
- Gatilho: tela `ModalCaminho` / `Sidebar` → rota `POST /api/scan` / CLI
  `fotoorganizer scan <pasta>... [--reprocessar]`
- Entradas: caminho absoluto da pasta; `ScannerSettings` (`workers`,
  `incluir_ocultos`, `seguir_symlinks`); `Source.padroes_ignorados` (globs).
- Regras de negócio:
  1. Extensões aceitas vêm SEMPRE de `PurePythonExtractor.supported_extensions()`
     (`metadata/exiftool.py:311-315`), mesmo com exiftool instalado: Pillow
     (`.jpg .jpeg .png .tif .tiff .webp .bmp .gif`) + vídeo
     (`.mov .mp4 .m4v .avi`) + HEIF se `pillow-heif` + RAW se `rawpy` **e** `exifread` (import conjunto em `metadata/purepython.py:32-41` — faltar qualquer um dos dois desliga RAW inteiro).
  2. Symlinks NÃO são atravessados por padrão (invariante 5); ciclos de
     diretório são cortados por `(st_dev, st_ino)` já visitados.
  3. Ocultos ignorados por padrão; lixo de sistema (`thumbs.db`,
     `desktop.ini`, `.ds_store`) e diretórios `@eadir`/`.thumbnails` sempre.
  4. Pastas de trabalho de programação NÃO são varridas
     (`discovery.py:29-46`): `node_modules`, `cache`, `caches`, `venv`,
     `site-packages`, … e sufixos `.xcassets .imageset .app .framework …`.
  5. Pacotes de biblioteca de foto (`.photoslibrary`, `.photolibrary`,
     `.migratedphotolibrary`, `.aplibrary`, `.lrdata`) SÃO descidos, mas o
     conteúdo entra como `papel=SINAL` — exceto o que estiver diretamente
     sob `originals/` ou `masters/` dos quatro primeiros, que é original e
     volta a `ACERVO`.
  6. Incremental: arquivo com `(tamanho, inode, mtime±1e-6 s)` inalterados é
     pulado. `--reprocessar` ignora a assinatura.
  7. Extração paralela em `ThreadPoolExecutor(max(workers,1))`, janela de
     `max(workers*2, 4)` em voo, teto de `_EXTRACAO_TIMEOUT_S = 120 s` por
     arquivo; **o banco é escrito por uma única thread**, na ordem de
     descoberta.
  8. Commit + checkpoint a cada `_BATCH_SIZE = 200` itens.
  9. `mtime`/`ctime` gravados UTC naive via `_ts()`; `ctime` usa
     `st_birthtime` no macOS. `data_capturada_utc = data_capturada` quando o
     extrator não traz fuso (= "fuso desconhecido").
  10. Arquivo dentro de pacote (`dentro_de_pacote(path)`, `scanner.py:408`) não ganha miniatura — é o mesmo predicado que o rebaixa a `papel=SINAL` (`:440-441`), então no scan os dois conjuntos coincidem; testemunhas criadas por outra via (migração 0009, referência externa) tampouco têm miniatura porque nunca passam por `get_or_generate`. Testemunha (`papel=SINAL`) não ganha miniatura nem base bruta de
      metadado — só `curadoria` e `derivado` (`scanner.py:484-505`).
  11. Identidade de fonte por `samefile` (dispositivo+inode), não por
      string: o APFS não distingue maiúscula. Fonte cujo caminho não existe
      agora é pulada na comparação.
- Saídas: linhas em `media_files` e `metadata_entries`; `Source` criada ou
  reaproveitada com `disponivel` atualizado; `ScanSession` com contadores,
  checkpoint e status. Miniaturas no cache. **Nenhuma escrita em arquivo.**
- Degradação/falha: fonte indisponível → `ScanSession.status=ERRO` +
  `checkpoint={"motivo": "volume ou pasta indisponível"}`, nada é tocado.
  `OSError` por diretório → log + continua (e o diretório entra em
  `diretorios_com_erro`). Erro/timeout por arquivo → `metrics.erros++`,
  `erro_leitura` preenchido, a foto entra sem metadado, varredura segue.
  Sem exiftool → fallback puro-Python, menos tags (sem `Make`/`Model` em
  CR3). Sem `rawpy`/`pillow-heif` → essas extensões somem da descoberta.
- Estado: pronto
- Testes que provam: `tests/test_scanner.py::test_corrompido_nao_interrompe_scan`,
  `::test_extracao_que_excede_o_teto_vira_erro_e_o_scan_segue`,
  `::test_segunda_passada_nao_rele_inalterados`,
  `::test_reprocessar_relê_arquivo_inalterado`,
  `::test_fonte_indisponivel`, `::test_fonte_reutilizada_entre_scans`,
  `::test_testemunha_nao_ganha_thumbnail`;
  `tests/test_discovery.py::test_nao_atravessa_symlink_e_evita_ciclo`,
  `::test_original_dentro_do_pacote_nao_e_rebaixado`
- Decisões: D-024 (rebaixar, nunca apagar), D-026 (exiftool padrão quando
  instalado), D-027 (MakerNotes fora), D-038 (dois instantes)
- Arquivos: `fotoorganizer/scanner/scanner.py:160-575` (entrada
  `scan_source:160`), `fotoorganizer/scanner/discovery.py:134-217`,
  `fotoorganizer/scanner/elegibilidade.py:25-42`,
  `fotoorganizer/security/hashing.py:20-29`,
  `fotoorganizer/server/jobs.py:170-194`, `fotoorganizer/cli.py:219-236`

---

### F-A02 — Pausa, continuação e cancelamento de trabalho
- Propósito: dar ao dono controle sobre um trabalho longo sem perder o que
  já foi feito.
- Gatilho: tela `StatusBar`/`useJob` → rotas `POST /api/job/pausar`,
  `POST /api/job/continuar`, `POST /api/job/cancelar` / CLI n/a (o CLI roda
  em foreground; Ctrl-C mata o processo)
- Entradas: nenhuma (agem sobre o job corrente, um por vez).
- Regras de negócio:
  1. **Só o scan tem pausa cooperativa** (`ScanControl`). Importação,
     execução de plano e escrita EXIF não a oferecem.
  2. `pausar()` exige `tipo=="scan"` e `status=="rodando"`; `continuar()`
     exige `status=="pausado"`. Fora disso devolve `False` **sem efeito
     colateral**, e a rota responde 409 em vez de estourar.
  3. `cancelar()` faz `continuar()` ANTES de `cancelar()` — um job pausado
     precisa acordar para ver o cancelamento — e propaga para o
     `ExecutionControl` quando existe.
  4. Scan cancelado drena o que já estava em voo (`consumir(0)`) para não
     jogar fora extração já paga, e fecha como `ScanStatus.PAUSADO`.
  5. Scan cancelado **não marca sumiço** (viu poucos caminhos; a diferença
     entre conhecidos e vistos explodiria).
  6. Execução de cópia e de escrita EXIF terminam o item corrente e param;
     o plano vira `CANCELADA`. Commit por item torna a retomada segura.
- Saídas: `ScanSession.status`; `OperationPlan.status`/`ExifWritePlan.status`
  = `CANCELADA`; snapshot do job com `status` correspondente.
- Degradação/falha: cancelar sem job em curso é no-op (200). Pausar/continuar
  fora do estado → 409 com mensagem específica. Morte do processo no meio:
  ver F-A03.
- Estado: parcial — falta pausa para importação e para execução de plano;
  `_exec_control` nunca é limpo após o job (**B3**); cancelamento de execução
  e de escrita EXIF **sem teste ponta a ponta** (**M8**).
- Testes que provam: `tests/test_scanner.py::test_cancelamento_e_retomada`,
  `::test_scan_cancelado_nao_marca_sumico_em_massa`;
  `tests/test_server_api.py::test_pausar_e_continuar_scan_em_background`,
  `::test_pausar_continuar_sem_job_e_recusado_limpo`;
  `tests/test_operations.py::test_cancelamento_e_retomada`;
  `tests/test_reconciliacao.py::test_cancelamento_no_meio_da_passada_salva_checkpoint_parcial`
- Decisões: n/a
- Arquivos: `fotoorganizer/server/jobs.py:61-87,124-147`,
  `fotoorganizer/scanner/scanner.py:89-111,292-303`,
  `fotoorganizer/operations/executor.py:42-51,174-177`,
  `fotoorganizer/server/app.py:1513-1528`

---

### F-A03 — Retomada de varredura interrompida
- Propósito: um scan que morreu com o processo (app fechado, Mac desligado)
  deixaria a sessão em `RODANDO` para sempre, e o catálogo mentiria sobre
  trabalho em curso. Esta funcionalidade fecha a mentira e oferece a
  retomada.
- Gatilho: tela `RetomarScan.tsx` / rota `GET /api/scan/interrompidos` (e
  o hook de startup do servidor) / CLI n/a
- Entradas: nenhuma.
- Regras de negócio:
  1. No boot do servidor, `reconciliar_orfas` carimba toda `ScanSession`
     `RODANDO` como `INTERROMPIDO` + `finalizado_em`. É seguro por
     construção: nenhum job pode estar rodando antes de o servidor existir.
  2. A listagem só conta a sessão **mais recente** de cada fonte: se um scan
     posterior concluiu, a interrupção antiga é história, não pendência.
  3. A retomada **não** é um comando novo: é um `POST /api/scan` no mesmo
     caminho. O incremental pula o que já foi indexado, ao custo de um
     `stat()` por arquivo.
  4. A reconciliação de alcance (F-A05) **não** grava `ScanSession` de
     propósito — uma passada parcial dela apareceria nesta tela e o botão
     "Retomar" dispararia o comando errado.
- Saídas: `ScanSession.status = INTERROMPIDO`; a lista com `source_id`,
  `caminho`, `apelido`, `disponivel`, `quando`, `vistos`, `indexados`.
- Degradação/falha: falha no hook de startup é capturada e logada
  (`log.warning`), o servidor sobe mesmo assim. Fonte indisponível aparece
  na lista com `disponivel=false` — a tela diz que não dá para retomar agora.
- Estado: pronto
- Testes que provam: `tests/test_scanner.py::test_sessao_rodando_orfa_vira_interrompida_no_boot`;
  `tests/test_server_api.py::test_scan_orfao_e_reconciliado_no_boot_e_oferecido_para_retomada`
- Decisões: n/a
- Arquivos: `fotoorganizer/scanner/scanner.py:122-144`,
  `fotoorganizer/server/app.py:1469-1507,1603-1614`

---

### F-A04 — Marcação de sumiço no scan (`arquivo_offline`)
- Propósito: distinguir "o arquivo sumiu do disco" de "sempre esteve lá" sem
  nunca apagar o registro.
- Gatilho: efeito colateral do fim de uma passada de `POST /api/scan` / CLI
  `fotoorganizer scan`
- Entradas: o conjunto `conhecidos` (índice da fonte carregado no início) e
  o conjunto `vistos` (todo caminho cujo `stat()` teve sucesso nesta passada).
- Regras de negócio:
  1. Candidato = `conhecidos - vistos`, filtrado por
     `eh_caminho_de_filesystem` (nada com `://`).
  2. **Três guardas antes de escrever**, em ordem:
     (a) passada cancelada → não marca nada;
     (b) `diretorios_com_erro` não vazio → não marca nada, só `log.warning`
         (o walk não viu a árvore inteira; a reconciliação cobre depois);
     (c) segunda confirmação `Path(c).exists()` — um caminho pode ter saído
         do walk porque `padroes_ignorados` ou a lista de extensões mudou.
     A guarda (c) **não substitui** a (b): sob pasta sem permissão de
     leitura, `exists()` também devolve `False`.
  3. `UPDATE` em lotes de `_LOTE_SUMICO = 500` (o limite de variáveis do
     SQLite estoura com tudo de uma vez), com
     `arquivo_ausente IS FALSE` e `caminho NOT LIKE '%://%'` **redundantes de
     propósito**: última linha de defesa contra marcar referência de
     catálogo externo como sumida.
  4. O registro e seus metadados **nunca** são apagados (invariante 8).
  5. Caminho de volta: `_gravar` põe `arquivo_offline=False` — chegar ali
     prova que o arquivo existe agora.
- Saídas: `MediaFile.arquivo_offline`; a UI mostra "arquivo sumiu do disco"
  como `motivo_indisponivel`.
- Degradação/falha: NAS que cai no meio ou subpasta sem permissão → nenhuma
  marcação nesta passada (guardas b/c), e a reconciliação confirma depois com
  calma.
- Estado: pronto
- Testes que provam: `tests/test_scanner.py::test_arquivo_que_some_e_marcado_offline`,
  `::test_arquivo_que_volta_e_marcado_online_de_novo`,
  `::test_diretorio_ilegivel_no_meio_do_walk_nao_marca_sumico`,
  `::test_subpasta_sem_permissao_real_nao_marca_sumico`,
  `::test_padrao_ignorado_novo_nao_marca_arquivo_existente_como_sumido`,
  `::test_referencia_externa_no_mesmo_source_nunca_vira_offline`
- Decisões: D-037 ("não visto no walk" quase virou sinônimo de "arquivo
  apagado"), D-024/invariante 8
- Arquivos: `fotoorganizer/scanner/scanner.py:296-334,357-382`,
  `fotoorganizer/scanner/elegibilidade.py:18-42`

---

### F-A05 — Reconciliação de alcance (varredura de existência)
- Propósito: manter `arquivo_offline` honesto sem depender de um re-scan
  manual. Um acervo em NAS pode passar semanas sem re-scan, e ninguém
  percebe que um arquivo sumiu até tentar abri-lo.
- Gatilho: rota `POST /api/reconciliacao` (**sem consumidor na UI**, achado
  **B8**) / CLI `fotoorganizer verificar-arquivos [--segundos N]`
- Entradas: `orcamento_segundos` (default 30,0), `orcamento_percentual`
  (default 0,20), `control` opcional.
- Regras de negócio:
  1. Só `Path.exists()` por linha — **sem reler metadado, sem recalcular
     hash** ("rehash só sob demanda" é regra do M1).
  2. Elegível = fonte `disponivel` **e** `arquivo_ausente IS FALSE` **e**
     `caminho NOT LIKE '%://%'`. Referência de catálogo externo nunca é
     tocada, nem lida nem escrita.
  3. Auto-limitada pelo que vier primeiro: tempo, percentual do elegível, ou
     `_TETO_DURO_POR_CHAMADA = 20_000` linhas.
  4. Cursor por `MediaFile.id` crescente; checkpoint em
     `application_settings["reconciliacao_checkpoint"]`, **nunca** em
     `ScanSession` (senão a tela de "retomar varredura" chamaria o comando
     errado).
  5. Antes de gastar `exists()` por arquivo, confere a raiz de cada fonte do
     lote **uma vez** — cobre o HD que caiu depois do último scan e ainda
     consta `disponivel=True`. Linha pulada por fonte fora de alcance
     **trava o checkpoint** para continuar elegível na próxima passada.
  6. Ao alcançar o fim do elegível, o checkpoint volta a zero
     (`ciclo_concluido`): a próxima chamada recomeça em vez de ficar presa.
  7. Reversível nos dois sentidos: marca offline e desmarca online.
- Saídas: `MediaFile.arquivo_offline`; checkpoint em `application_settings`;
  `ResultadoReconciliacao(verificados, marcados_offline, marcados_online,
  ciclo_concluido, cancelado)`.
- Degradação/falha: fonte fora de alcance → linhas puladas sem tocar o
  disco. Cancelamento → salva o checkpoint parcial e reporta `cancelado`.
  Um único commit no fim do lote.
- Estado: parcial — a rota existe e não tem consumidor na UI (**B8**); não há
  scheduler, então cada chamada é UMA passada disparada por CLI/API.
- Testes que provam: `tests/test_reconciliacao.py::test_referencia_de_catalogo_externo_nunca_e_tocada`,
  `::test_checkpoint_processa_parte_e_retoma_na_proxima_chamada`,
  `::test_orcamento_de_tempo_para_a_passada_no_meio`,
  `::test_fonte_sumida_no_meio_do_lote_nao_gasta_exists_por_linha`,
  `::test_fonte_indisponivel_nao_e_verificada`;
  `tests/test_cli.py::test_verificar_arquivos_reporta_offline_e_online`
- Decisões: D-037; invariante 8
- Arquivos: `fotoorganizer/scanner/reconciliacao.py:100-238`,
  `fotoorganizer/repositories/settings.py:27-42`,
  `fotoorganizer/server/jobs.py:115-122,314-331`,
  `fotoorganizer/cli.py:380-402`

---

### F-A06 — Disponibilidade de fontes e identidade de volume
- Propósito: dizer TRÊS coisas que hoje se confundem em "arquivo não
  encontrado": está aqui, está na gaveta, mudou de lugar. Sem isso, uma
  remontagem vira "disco novo" e 45.397 fotos seriam recatalogadas do zero.
- Gatilho: hook de startup do servidor; rota `GET /api/fontes` e
  `GET /api/fontes/reapontamentos` / CLI `fotoorganizer volumes`
- Entradas: as `Source` do catálogo.
- Regras de negócio:
  1. Identidade do volume, do mais forte ao mais fraco:
     `uuid:<VolumeUUID>` (diskutil) → `rede:<origem>` (SMB/AFP/NFS/WebDAV/FTP)
     → `caminho:<ponto>` com `estavel=False`.
  2. Gravada na fonte **na primeira vez que ela é vista**; depois é só
     comparada.
  3. `volume_desmontado()`: se o caminho pede `/Volumes/<nome>` e esse ponto
     não está montado, para ali — sem isso, subir a árvore a partir de um
     disco desligado chega em `/` e atribui as fotos dele ao disco de boot,
     trocando "está na gaveta" por "está aqui".
  4. Volume que voltou noutro ponto é **detectado e não reescrito**: mover 45
     mil linhas é operação do usuário, não efeito colateral de uma
     verificação (ver F-A07).
  5. Subprocessos `/sbin/mount` e `diskutil info -plist` em lista, sem
     shell, timeout 10 s. Falha **nunca levanta** — devolve a identidade mais
     fraca e segue; volume de rede não aparece no diskutil e isso é esperado.
  6. `resumo()` produz as quatro frases da UI, inclusive "a pasta não existe
     mais neste volume" — que não é indisponibilidade, é ausência, e a ação
     do usuário é procurar backup, não plugar cabo.
  7. O servidor usa `Source.disponivel` (uma consulta por requisição), não um
     `stat` por miniatura — a grade pede centenas de uma vez.
- Saídas: `Source.disponivel`, `visto_em`, `volume_id`, `volume_nome`;
  `EstadoDaFonte` em memória; `motivo_indisponivel` em cada `_media_json`.
- Degradação/falha: `diskutil`/`mount` ausente ou lento → identidade
  `caminho:`, `estavel=False`, e a UI avisa "identidade frágil". `OSError` ao
  identificar → `volume=None` + log.
- Estado: pronto
- Testes que provam: `tests/test_volumes.py::test_disco_desligado_nao_vira_o_disco_de_boot`,
  `::test_uuid_manda_sobre_o_ponto_de_montagem`,
  `::test_nas_sem_uuid_usa_servidor_e_compartilhamento`,
  `::test_diskutil_quebrado_nao_derruba_a_identificacao`,
  `::test_disco_na_gaveta_e_indisponivel_sem_perder_identidade`,
  `::test_volume_que_voltou_noutro_ponto_e_apontado`,
  `::test_pasta_apagada_no_disco_montado_nao_e_gaveta`
- Decisões: migração 0011 (identidade de volume)
- Arquivos: `fotoorganizer/security/volumes.py:62-170`,
  `fotoorganizer/sources/disponibilidade.py:31-121`,
  `fotoorganizer/server/app.py:291-301,472-478,1616-1632`,
  `fotoorganizer/cli.py:265-291`

---

### F-A07 — Reapontar fonte para o novo ponto de montagem
- Propósito: quando um volume volta em `/Volumes/photo 1` em vez de
  `/Volumes/photo`, reescrever o catálogo para onde ele está — **sem tocar em
  nenhum arquivo**.
- Gatilho: tela `Sidebar` (affordance só para fontes marcadas) → rotas
  `POST /api/fontes/{id}/reapontar/preview` e `POST /api/fontes/{id}/reapontar`
  / CLI `fotoorganizer reapontar <fonte> [--confirmar] [--desfazer ID]`
- Entradas: id ou apelido da fonte; confirmação explícita (`{"confirmar":
  true}` no corpo, ou `--confirmar`); ou um `audit_log_id` para desfazer.
- Regras de negócio:
  1. Duas camadas: `previa`/`aplicar` operam sobre **dois prefixos
     explícitos** e não sabem nada de volumes montados (é isso que dá
     reversibilidade de graça); `prefixos_do_estado` deriva os prefixos do
     estado ao vivo.
  2. Guarda: só age quando o caminho é uma raiz `/Volumes/<nome>...`. Disco
     interno ou identidade `caminho:` frágil não são caso deste mecanismo —
     um replace genérico ali reescreveria o caminho errado.
  3. **Só linhas cujo `caminho` começa com `prefixo_antigo`** são contadas,
     amostradas e reescritas. `apple://uuid` e `lightroom://uuid` não têm
     esse prefixo nunca e ficam bit-a-bit intocadas (invariante 8); o total
     ignorado é reportado para o dono não confundir "não mudou" com "não tem".
  4. `aplicar` recusa se `source.caminho != prefixo_antigo` — abortar para não
     reescrever linhas da fonte errada.
  5. Valida `_TAMANHO_VALIDACAO = 20` caminhos NOVOS no disco (amostragem
     espaçada, só `Path.exists()`); qualquer ausente → `ValidacaoFalhou` e
     **nenhuma linha alterada**.
  6. Colisão proativa: duas linhas caindo no mesmo caminho, ou uma
     reapontada caindo sobre uma intocada → `ColisaoDeCaminho` com mensagem
     que diz qual caminho colidiu, em vez de `IntegrityError` cru.
  7. Uma transação, tudo ou nada: `Source.caminho` + N `MediaFile.caminho` +
     `AuditLog`.
  8. Desfazer = chamar `aplicar` com os prefixos TROCADOS, lendo-os da
     entrada de auditoria; cria uma entrada nova, para desfazer-o-desfazer
     funcionar pelo mesmo caminho.
- Saídas: `Source.caminho`, N `MediaFile.caminho`, uma linha
  `audit_log(acao="reapontar_fonte", plan_id=None)` com `{source_id,
  prefixo_antigo, prefixo_novo, linhas_media_files}`.
- Degradação/falha: sem `confirmar` → 422 e nada acontece. Validação falha,
  colisão ou fonte inaplicável → 409, nada escrito, `rollback` no
  `IntegrityError`. `--desfazer` com id que não é de reapontamento → recusa.
- Estado: parcial — `--desfazer` existe **só na CLI**; não há superfície de
  API/UI (decisão explícita: reapontar errado devia ser raro o bastante para
  não precisar de botão).
- Testes que provam: `tests/test_reapontar.py::test_fonte_mista_execucao_so_reescreve_o_que_tem_o_prefixo`,
  `::test_validacao_aborta_a_operacao_inteira_se_um_caminho_novo_nao_existe`,
  `::test_colisao_de_caminho_aborta_sem_escrever_nada`,
  `::test_desfazer_por_auditoria_reverte_bit_a_bit`,
  `::test_aplicar_recusa_prefixo_antigo_que_nao_bate_com_a_fonte`,
  `::test_prefixo_recusa_fonte_que_nao_e_volume`;
  `tests/test_server_reapontar.py::test_reapontar_ignora_referencias_de_catalogo_externo`,
  `::test_reapontar_sem_confirmar_e_recusado`
- Decisões: D-036 (reapontar quase reescreveu referência de nuvem)
- Arquivos: `fotoorganizer/sources/reapontar.py:100-343`,
  `fotoorganizer/server/app.py:535-607`, `fotoorganizer/cli.py:294-377`

---

### F-A08 — Importação do Apple Fotos
- Propósito: trazer para o catálogo próprio o que a biblioteca do Apple
  Fotos sabe e o arquivo às vezes não — em especial o **fuso por foto**, que
  é o único fuso medido deste acervo, e o GPS das referências de iCloud, que
  é o que localiza as fotos de câmera.
- Gatilho: tela `Sidebar`/`ModalCaminho` → rota `POST /api/importar`
  `{"tipo":"apple_photos"}` / CLI `fotoorganizer importar apple [caminho]`
- Entradas: caminho da biblioteca (default `~/Pictures/Photos
  Library.photoslibrary`).
- Regras de negócio:
  1. **Somente leitura** sobre a biblioteca; nada de rede.
  2. `db.photos(movies=True)`: o vídeo não é ruído — é metade de cada Live
     Photo e carrega GPS e horário quando a foto ao lado não carrega.
  3. Item sem `path` mas com `uuid` vira **referência**
     (`caminho="apple://<uuid>"`, `arquivo_ausente=True`, `papel=SINAL`).
     Numa biblioteca em "Otimizar armazenamento" isso é a maioria.
  4. Item sem `path` **e** sem `uuid` é descartado (sem identidade não há o
     que referenciar).
  5. `photo.date` vem com fuso: o absoluto vai para `data_capturada_utc` e a
     hora de parede naive para `data_capturada`. Fuso descartado não volta
     por inferência.
  6. Fusão: o **arquivo manda**; o catálogo externo preenche lacunas e doa
     contexto (título, descrição, favorito, álbuns, pessoas, palavras-chave)
     em `metadata_entries` com namespace `apple`.
  7. O fuso do catálogo só é emprestado quando as duas horas de parede
     batem dentro de `_TOLERANCIA_DE_PAREDE = 1 s`, e o que se empresta é o
     **offset**, não o absoluto — 65% das linhas do Apple Fotos têm
     microssegundo e nenhuma de EXIF tem.
  8. Reimportar é idempotente (upsert por `(source_id, caminho)`; o namespace
     `apple` é apagado e regravado).
- Saídas: `Source` tipo `apple_photos`; `media_files` (arquivos e
  referências); `metadata_entries` namespace `apple` + `curadoria`.
- Degradação/falha: sem `osxphotos` → `ApplePhotosError` com
  `pip install fotoorganizer[apple]`. Sem Acesso Total ao Disco →
  `ApplePhotosError` que **nomeia o app responsável pelo TCC** (descoberto
  subindo a árvore de processos com `ps`). `PermissionError` em qualquer
  ponto da cadeia de causas durante a iteração ganha a mesma orientação no
  job. Erro por asset → conta e segue.
- Estado: pronto
- Testes que provam: `tests/test_sources_importer.py::test_fuso_do_catalogo_vale_quando_a_hora_de_parede_bate_com_o_exif`,
  `::test_hora_de_parede_divergente_nao_empresta_o_fuso_do_catalogo`,
  `::test_fronteira_da_tolerancia_de_um_segundo`,
  `::test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel`,
  `::test_referencia_doa_gps_para_foto_de_camera`;
  `tests/test_jobs.py::test_permissao_crua_do_apple_photos_ganha_orientacao`;
  `tests/test_cli.py::test_erro_do_apple_nomeia_o_app_que_precisa_da_permissao`
- Decisões: D-024 (miniaturas do pacote são testemunha), D-030/D-034
  (álbum nomeia, não divide), D-035, D-038 (dois instantes)
- Arquivos: `fotoorganizer/sources/apple_photos.py:37-172`,
  `fotoorganizer/sources/importer.py:76-427`,
  `fotoorganizer/server/jobs.py:93-97,345-399`, `fotoorganizer/cli.py:405-460`

---

### F-A09 — Importação do Google Takeout
- Propósito: via local-first para o Google Photos (desde março/2025 a Library
  API só acessa mídia criada pelo próprio app). O valor está no `geoData` do
  sidecar, que traz coordenada mesmo quando o export removeu o EXIF.
- Gatilho: tela `Sidebar`/`ModalCaminho` → rota `POST /api/importar`
  `{"tipo":"google_takeout","caminho":…}` / CLI
  `fotoorganizer importar takeout <pasta> [--ler-arquivos]`
- Entradas: pasta do Takeout descompactado; flag `ler_arquivos`.
- Regras de negócio:
  1. **Por padrão não abre as imagens**: o Takeout é exportação de fotos que o
     dono já tem, com dezenas de GB. Os itens entram como **referência**
     (`caminho="google://<relativo>"`), com nome e tamanho lidos da entrada
     de diretório — informação *sobre* o arquivo, não conteúdo dele.
  2. `ler_arquivos=True` restaura a catalogação de verdade, para quando o
     Takeout *for* o acervo.
  3. Sidecar procurado em 4 variantes, cobrindo `IMG(1).jpg` e
     `.supplemental-metadata.json`.
  4. `photoTakenTime.timestamp` é o instante **absoluto**; os dois instantes
     saem iguais (= "não sei o fuso"), nunca "foi tirada em Greenwich".
     Converter com `fromtimestamp(n)` sem fuso fazia a hora depender do fuso
     da MÁQUINA que rodou a importação.
  5. `geoData`/`geoDataExif` com `0.0/0.0` é o "sem GPS" do Takeout, **não**
     uma coordenada real.
  6. Nome da pasta pai vira álbum, **exceto** pasta de ano
     (`^(photos from|fotos de)\s+\d{4}$`).
  7. Vídeo entra: tem sidecar como qualquer foto, e o `geoData` dele é
     coordenada real de um celular que costuma ser o mesmo que não gravou
     EXIF na foto ao lado.
- Saídas: `Source` tipo `google_takeout`; `media_files` (referências por
  padrão); `metadata_entries` namespace `google`.
- Degradação/falha: sidecar ausente → entra com o que a entrada de diretório
  diz. Sidecar ilegível (`OSError`/`JSONDecodeError`) → `log.warning` e segue
  com `{}`. `stat()` falhando → `tamanho=None`. Pasta inexistente → 422 na
  rota, mensagem no CLI.
- Estado: pronto
- Testes que provam: `tests/test_google_takeout.py` (suíte);
  `tests/test_server_api.py::test_import_takeout_em_background`;
  `tests/test_cli.py::test_importar_takeout_traz_gps_do_sidecar`,
  `::test_importar_takeout_sem_pasta_avisa_em_vez_de_estourar`
- Decisões: D-038
- Arquivos: `fotoorganizer/sources/google_takeout.py:49-186`,
  `fotoorganizer/sources/importer.py:265-323`,
  `fotoorganizer/server/jobs.py:99-103`, `fotoorganizer/cli.py:405-460`

---

### F-A10 — Importação do Lightroom Classic (`.lrcat`)
- Propósito: é o inventário mais valioso de um acervo espalhado por um motivo
  que nenhuma outra fonte tem — **responde com os discos desligados**. Num
  acervo real o `.lrcat` conhecia 54.086 fotos, 44.474 num volume desmontado;
  varrer o disco teria encontrado zero.
- Gatilho: rota n/a (**não existe** `POST /api/importar` para Lightroom) /
  CLI `fotoorganizer importar lightroom <catalogo.lrcat>`
- Entradas: caminho do arquivo `.lrcat` (é o arquivo, não a pasta).
- Regras de negócio:
  1. Abre com `sqlite3.connect("file:<cat>?immutable=1", uri=True)`: sem lock,
     sem journal, sem escrita — o Lightroom pode estar aberto ao lado
     (invariante 1).
  2. **Todo item entra como referência** (`caminho="lightroom://<uuid>"`,
     `arquivo_ausente=True`, `papel=SINAL`): o arquivo pode estar
     inacessível, e mesmo acessível é o scanner quem cataloga arquivo.
  3. `caminho_original` guarda onde o Lightroom acredita que o arquivo está —
     é isso que responde "onde estava esta foto?" com o volume na gaveta, e
     vira `MediaFile.pasta`.
  4. Os pedaços do caminho vêm SEPARADOS do SQL: em SQL `a || b` é `NULL` se
     qualquer parte for `NULL`, e uma extensão ausente apagava o caminho
     inteiro — em silêncio, sem exceção e sem log.
  5. `favorito` = `rating >= 4` **ou** `pick > 0`.
  6. Coleções → `albuns`; keywords → `palavras_chave`, que são unificadas com
     a curadoria do arquivo **sem repetir** (o mesmo "Selected" chega pelo
     `.lrcat` e pelo `.xmp` ao lado — mesma afirmação, mesma origem).
  7. Data implausível (o `.lrcat` do dono trazia um registro de 2100) sai das
     **duas** colunas de instante junto.
- Saídas: `Source` tipo `lightroom`; `media_files` (só referências);
  `metadata_entries` namespace `lightroom` + `curadoria`.
- Degradação/falha: arquivo ausente/ilegível → `LightroomError` com instrução
  ("abra-o uma vez no Lightroom Classic para atualizar o formato"). Tabela
  auxiliar ausente numa versão diferente → `log.warning` e dicionário vazio:
  perde-se o contexto, não o mapa. Itens sem caminho reconstruível são
  contados e logados (antes acontecia calado).
- Estado: parcial — **sem superfície de UI/HTTP**; só CLI.
- Testes que provam: `tests/test_lightroom.py::test_le_caminho_data_gps_e_intencao`,
  `::test_nada_e_aberto_do_disco`;
  `tests/test_sources_importer.py::test_data_implausivel_de_referencia_sai_das_duas_colunas_junto`,
  `::test_curadoria_do_catalogo_externo_nao_duplica_a_do_arquivo`
- Decisões: D-028 (Lightroom entra como fonte externa e é a principal do
  discovery), migração 0010 (referência é sempre sinal)
- Arquivos: `fotoorganizer/sources/lightroom.py:34-219`,
  `fotoorganizer/sources/importer.py:265-323,363-398`,
  `fotoorganizer/cli.py:405-460`

---

### F-A11 — Rebaixamento a fonte de sinal (acervo × testemunha)
- Propósito: separar "foto do usuário" de "testemunha" sem apagar nada. 89%
  dos arquivos locais de um acervo real eram miniaturas 540×360 do pacote do
  Apple Fotos, e elas inundaram a revisão com 45.822 sugestões. Apagá-las
  seria pior: são a única testemunha do lugar de milhares de fotos sem GPS
  próprio.
- Gatilho: efeito de `POST /api/scan` e `POST /api/importar` / CLI `scan` e
  `importar`; migrações 0008, 0009 e 0010 fizeram o backfill
- Entradas: o caminho do arquivo (para `dentro_de_pacote`) e a natureza do
  item (arquivo × referência).
- Regras de negócio:
  1. `papel` é reavaliado **a cada passagem** do scan — uma pasta pode virar
     pacote entre scans.
  2. Dentro de pacote de biblioteca de foto → `SINAL`, **exceto** o que
     estiver diretamente sob `originals/`/`masters/` dos pacotes que separam
     original de derivado (`.lrdata` não separa: por dentro é sempre
     pré-visualização).
  3. Toda referência de catálogo externo → `SINAL` obrigatoriamente: quem não
     tem arquivo local não pode ser acervo, porque não há o que mostrar na
     grade nem o que copiar no plano (migração 0010).
  4. Pasta de trabalho de programação nem entra (é pulada na descoberta): um
     ícone de app não é testemunha de nada, não tem data nem GPS para doar.
  5. `SINAL` fica fora de grade, revisão, duplicata e plano de cópia —
     expresso pela hybrid property `MediaFile.organizavel`, que precisa valer
     em SQL porque filtrar por lista de ids em Python estourou o limite de
     variáveis do SQLite.
  6. `SINAL` **continua doando** data, GPS e correlação. Não guarda base
     bruta de metadado (685 mil linhas e 134 MB sem nada em troca), mas
     guarda `curadoria` e `derivado`.
  7. **Nada é apagado, nem do disco nem do catálogo** (invariante 8).
- Saídas: `MediaFile.papel`; `organizavel` muda; a foto some da grade e do
  plano sem sumir do catálogo.
- Degradação/falha: n/a — é uma classificação, não uma operação de IO.
- Estado: pronto
- Testes que provam: `tests/test_discovery.py::test_pacote_de_biblioteca_e_reconhecido_pelo_sufixo`,
  `::test_pacote_reconhecido_em_qualquer_nivel_do_caminho`,
  `::test_original_dentro_do_pacote_nao_e_rebaixado`,
  `::test_original_do_lrdata_continua_testemunha`,
  `::test_smart_previews_do_lightroom_entram_como_testemunha`,
  `::test_pasta_de_fotos_com_nome_parecido_continua_valendo`;
  `tests/test_sources_importer.py::test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel`
- Decisões: **D-024** (registro que não é acervo é rebaixado, nunca apagado),
  D-035; invariante 8 do CLAUDE.md
- Arquivos: `fotoorganizer/scanner/discovery.py:48-116`,
  `fotoorganizer/scanner/scanner.py:439-442`,
  `fotoorganizer/sources/importer.py:285-291`,
  `fotoorganizer/models/catalog.py:45-61,273-324`

---

### F-A12 — Duplicatas exatas (nível 1) e resolução automática
- Propósito: achar bytes idênticos sem hashear o acervo inteiro, e já
  responder a única pergunta que sobra num grupo exato — qual caminho é a
  referência de trabalho.
- Gatilho: tela `Duplicates.tsx` → rota `POST /api/duplicatas/detectar` /
  CLI n/a
- Entradas: todas as `media_files` com `tamanho > 0`.
- Regras de negócio:
  1. Hash rápido `xxh3:` é O(1) por arquivo: tamanho em 8 bytes + primeiros
     64 KiB + (se `size > 128 KiB`) últimos 64 KiB. É o que detecta mudança e
     aponta candidatos.
  2. SHA-256 completo só para candidatos — agrupados por
     `(tamanho, hash_rapido)` com 2+ membros. **Nunca** para o acervo inteiro.
  3. Igualdade de conteúdo só é afirmada com SHA-256.
  4. Grupo `EXATO` = 2+ com mesmo `hash_sha256`. O **primeiro** membro
     continua elegível para a passada de phash, para que uma recompressão da
     mesma foto agrupe com ele em vez de ficar órfã.
  5. Resolução automática **só** para `EXATO`: bytes idênticos não deixam
     ambiguidade sobre o conteúdo. Ordem de desempate: (a) fonte própria
     antes de catálogo externo; (b) caminho mais organizado (mais
     segmentos); (c) nome descritivo antes de `IMG_1234`/numérico puro;
     (d) mais metadado conhecido; (e) `id` menor, para ser estável entre
     execuções.
  6. Grava `resolvido_automaticamente=True` e `PRINCIPAL`/`VERSAO`.
  7. **Nada é excluído.** A detecção é somente leitura sobre os arquivos.
- Saídas: `duplicate_groups` (nível `exato`, `resolvido_automaticamente`),
  `duplicate_members` com papéis; `media_files.hash_sha256` preenchido sob
  demanda.
- Degradação/falha: `OSError` ao calcular SHA-256 → `log.warning` e segue
  (aquele membro fica sem hash e não agrupa). Arquivo fora de alcance idem.
  Job ocupado → 409.
- Estado: pronto
- Testes que provam: `tests/test_duplicates.py::test_deteccao_exato_e_conteudo`,
  `::test_deteccao_nao_modifica_arquivos`,
  `::test_sha256_calculado_so_para_candidatos`,
  `::test_grupo_exato_e_resolvido_automaticamente`,
  `::test_resolucao_prefere_fonte_propria_sobre_externa`,
  `::test_resolucao_prefere_nome_descritivo_sobre_generico`,
  `::test_resolucao_desempata_por_id_e_e_estavel_a_ordem_de_entrada`,
  `::test_resolucao_prefere_quem_sabe_mais_antes_de_cair_no_id`;
  `tests/test_hashing.py` (suíte)
- Decisões: migração 0016 (`resolvido_automaticamente`)
- Arquivos: `fotoorganizer/duplicates/detector.py:120-200,248-276`,
  `fotoorganizer/duplicates/resolucao.py:24-67`,
  `fotoorganizer/security/hashing.py:20-37`,
  `fotoorganizer/server/jobs.py:110-113,293-312`

---

### F-A13 — Classificação de grupos além do exato (variante, rajada, conteúdo, visual)
- Propósito: impedir que a interface peça para escolher UMA foto quando a
  resposta certa é "fique com as duas".
- Gatilho: mesma rota `POST /api/duplicatas/detectar`
- Entradas: grupos formados pela busca de phash (BKTree, `LIMIAR_VISUAL = 8`).
- Regras de negócio:
  1. Ordem de decisão **importa**: `VARIANTE` → `SEQUENCIA` → `CONTEUDO`
     (distância 0) → `VISUAL` (1..8).
  2. `VARIANTE` = RAW + JPEG do mesmo clique: **um só** nome base, **duas ou
     mais** extensões distintas, e ao menos uma em `RAW_EXTENSIONS`. Vem
     antes da rajada porque um par RAW+JPEG é sempre da mesma câmera no mesmo
     segundo e casaria como rajada também — e "rajada" convida a escolher o
     melhor frame, que aqui não é a pergunta. O RAW é o negativo, o JPEG é a
     cópia de trabalho, e o dono quase sempre quer os dois.
  3. `SEQUENCIA` (rajada) = **todos** com `data_capturada`, **uma só**
     `(make, model)` não-nula, e frames consecutivos a ≤ `GAP_RAJADA = 10 s`.
     Sem data ou sem câmera identificada, não se afirma rajada.
  4. Dois `.CR3` de nome igual em pastas diferentes são cópia, não variante —
     por isso exigir extensões distintas.
  5. Nenhum desses níveis recebe resolução automática: dependem de julgamento
     sobre o conteúdo e ficam `INDEFINIDO` até um clique humano.
- Saídas: `duplicate_groups.nivel` ∈ `{variante, sequencia, conteudo,
  visual}`; membros `INDEFINIDO`.
- Degradação/falha: sem `hash_perceptual` (erro de leitura, imagem
  indecodificável) a mídia não entra na passada de phash — fica fora dos
  níveis 2-5 sem erro visível.
- Estado: parcial (o cálculo do phash em si é do domínio imagem; achado
  **M4**: `duplicates/phash.py:97` não aplica `exif_transpose` enquanto
  `thumbnails/generator.py:51` aplica — cópias de foto retrato, uma com
  thumb e outra sem, não agrupam, e a docstring `:66-67` fica falsa)
- Testes que provam: `tests/test_duplicates.py::test_raw_e_jpeg_do_mesmo_clique_sao_variante_nao_duplicata`,
  `::test_variante_vence_rajada_na_classificacao`,
  `::test_duas_copias_do_mesmo_raw_nao_sao_variante`,
  `::test_jpeg_e_png_sem_raw_nao_e_variante`,
  `::test_rajada_mesma_camera_vira_sequencia`,
  `::test_phash_identico_em_rajada_tambem_e_sequencia`,
  `::test_sem_data_de_captura_nao_afirma_rajada`,
  `::test_parecidas_com_horas_de_distancia_nao_sao_rajada`
- Decisões: D-070 (UI de duplicata VARIANTE avisa ao excluir RAW ou JPEG)
- Arquivos: `fotoorganizer/duplicates/detector.py:50-91,202-246`,
  `fotoorganizer/metadata/purepython.py:45`

---

### F-A14 — Decisão do usuário sobre um grupo de duplicatas
- Propósito: a decisão humana vale mais que a do algoritmo e precisa
  sobreviver a toda redetecção futura.
- Gatilho: tela `Duplicates.tsx` → rotas
  `POST /api/duplicatas/{id}/principal` `{media_id}`,
  `POST /api/duplicatas/{id}/ignorar`, `POST /api/duplicatas/{id}/desfazer` /
  CLI n/a
- Entradas: id do grupo; para "principal", o `media_id` escolhido.
- Regras de negócio:
  1. Qualquer uma das três ações marca **decisão humana**: zera
     `resolvido_automaticamente`. A partir daí a decisão é do usuário.
  2. Na redetecção, grupo é preservado **só** quando
     `not resolvido_automaticamente and any(papel != INDEFINIDO)`. Um grupo
     EXATO resolvido sozinho é regenerado — se contasse como decisão,
     travaria no tamanho de quando foi criado e uma terceira cópia idêntica
     descoberta depois nunca se juntaria a ele.
  3. `VERSAO` = cópia redundante de grupo com PRINCIPAL definido → **não
     entra** no plano de cópia.
  4. `IGNORADO` = "olhei e não são duplicatas de fato" → **continua
     entrando** no plano normalmente. São coisas diferentes e o planner as
     trata diferente.
  5. O principal **herda** o metadado que só a versão tinha.
  6. Nenhuma dessas ações apaga arquivo. Nunca.
- Saídas: `duplicate_members.papel`;
  `duplicate_groups.resolvido_automaticamente=False`; `metadata_entries`
  herdadas pelo principal.
- Degradação/falha: grupo inexistente não tem tratamento explícito no
  handler (ver Lacunas).
- Estado: pronto
- Testes que provam: `tests/test_duplicates.py::test_acoes_do_repositorio`,
  `::test_redeteccao_preserva_decisao`,
  `::test_decisao_humana_substitui_resolucao_automatica`,
  `::test_desfazer_reverte_resolucao_automatica`,
  `::test_nova_copia_identica_se_junta_a_grupo_resolvido_automaticamente`,
  `::test_principal_herda_o_metadado_que_so_a_versao_tinha`;
  `tests/test_operations.py::test_plano_exclui_versao_de_duplicata_exata`,
  `::test_plano_inclui_grupo_ignorado_por_inteiro`;
  `tests/test_server_api.py::test_duplicatas_detectar_e_decidir`
- Decisões: D-070, D-071
- Arquivos: `fotoorganizer/repositories/duplicates.py:105-190`,
  `fotoorganizer/duplicates/detector.py:279-299`,
  `fotoorganizer/operations/planner.py:72-86`,
  `fotoorganizer/server/app.py:1216-1229`

---

### F-A15 — Plano de cópia física (dry-run como registro)
- Propósito: materializar como **registro** o que uma operação física faria,
  antes de qualquer byte se mover. Nenhum arquivo é tocado aqui.
- Gatilho: tela `Operations` → rota `POST /api/operacoes`
  `{raiz_destino, nome?}` / CLI `fotoorganizer plano <destino> [--nome N]`
- Entradas: raiz de destino absoluta; nome opcional.
- Regras de negócio:
  1. Só sugestões com `status in (APROVADA, EDITADA)` entram.
  2. Exclui mídia já copiada por plano anterior (`OperationItem.status ==
     CONCLUIDA`) — não refaz trabalho.
  3. Exclui mídia marcada `VERSAO` em grupo de duplicata. `IGNORADO` entra.
  4. Caminho de destino passa por `resolver_destino`: cada segmento
     normalizado, `..` e `~` recusados, e **depois de resolver** exige
     `is_relative_to(raiz)` — defesa em profundidade contra path traversal.
  5. Colisão resolvida sufixando **antes da extensão** (`IMG_1 (2).jpg`),
     contra o disco **e** contra o próprio plano. Nunca sobrescreve nome
     ocupado; renomear vira `conflito` visível.
  6. Raiz de destino dentro da árvore da fonte → `conflito` ("copiar para
     dentro da própria origem faria o próximo scan indexar as cópias"). Na
     dúvida (`OSError`), bloqueia.
  7. `CaminhoInvalido` → `conflito` e `destino=""` (string vazia é o sinal de
     "sem destino calculado" para o dry-run e o executor).
  8. A raiz pode não existir (a cópia cria as pastas), mas o **volume que a
     contém** precisa existir — senão o plano nasce apontando para um disco
     desconectado.
  9. A operação é **sempre CÓPIA**. `OperationType` tem um único valor.
- Saídas: `operation_plans` + N `operation_items` (`status=planejada`);
  `audit_log(acao="plano_criado", detalhe={raiz, itens})`.
- Degradação/falha: nenhuma sugestão aprovada pendente → `None` → 409
  "nenhuma sugestão aprovada aguardando cópia" (CLI imprime e sai 1). Raiz
  não absoluta ou volume ausente → 422.
- Estado: pronto
- Testes que provam: `tests/test_operations.py::test_plano_so_inclui_aprovadas_e_resolve_colisao`,
  `::test_plano_exclui_versao_de_duplicata_exata`,
  `::test_plano_inclui_grupo_ignorado_por_inteiro`,
  `::test_destino_dentro_da_origem_e_conflito`,
  `::test_plano_nao_refaz_midias_ja_copiadas`;
  `tests/test_server_api.py::test_plano_exige_aprovadas_e_destino_valido`
- Decisões: invariantes 2 e 3 do CLAUDE.md
- Arquivos: `fotoorganizer/operations/planner.py:37-148`,
  `fotoorganizer/security/paths.py:18-55`,
  `fotoorganizer/server/app.py:1254-1270`, `fotoorganizer/cli.py:500-514`

---

### F-A16 — Dry-run de plano de cópia (obrigatório)
- Propósito: dizer, sem tocar em nada, o que aconteceria — e produzir o
  **veredito** sem o qual a execução é recusada.
- Gatilho: tela `Operations` → rota `POST /api/operacoes/{id}/dry-run` / CLI
  `fotoorganizer dry-run <plano_id>`
- Entradas: id do plano.
- Regras de negócio:
  1. **Só lê.** Confere, por item não-concluído: destino calculado, origem é
     arquivo, destino ainda não existe; soma bytes.
  2. Espaço livre: sobe os `parents` do destino do primeiro item até achar um
     que exista e chama `shutil.disk_usage(...).free`.
  3. Grava `plano.dry_run_em` e `audit_log(acao="dry_run")` com
     `{prontos, problemas, bytes_necessarios, bytes_livres}`.
  4. O veredito **mora no audit log**, nunca copiado para a tabela do plano —
     duas verdades divergiriam. `PlanRow.prontos/problemas` são lidos de lá.
  5. `executavel = dry_run_em is not None and bool(prontos)`. Sem essa linha,
     o resumo mostrava "0 erros · dry-run ✓" para um plano com as 97 origens
     num volume desmontado, que lê como "pronto para copiar".
- Saídas: `{prontos, problemas[], bytes_necessarios, bytes_livres,
  espaco_suficiente}`; `dry_run_em`; uma linha de auditoria.
- Degradação/falha: plano inexistente → 404. Origem indisponível, destino
  ocupado ou caminho inválido viram entradas em `problemas`, nunca exceção.
  Nenhum destino existente ainda → `bytes_livres=None` e
  `espaco_suficiente=True`.
- Estado: pronto
- Testes que provam: `tests/test_operations.py::test_resumo_do_plano_carrega_o_veredito_do_dry_run`,
  `::test_execucao_exige_dry_run`;
  `tests/test_server_api.py::test_plano_dry_run_e_execucao_copiam_sem_tocar_origem`
- Decisões: invariante 2 (plano até aprovação explícita)
- Arquivos: `fotoorganizer/operations/executor.py:67-135`,
  `fotoorganizer/repositories/operations.py:67-101`,
  `fotoorganizer/server/app.py:1307-1312`, `fotoorganizer/cli.py:517-530`

---

### F-A17 — Execução de plano: cópia verificada por hash
- Propósito: a ÚNICA parte do app que escreve fora do catálogo. Copiar sem
  nunca sobrescrever, verificando antes e depois.
- Gatilho: tela `Operations` → rota `POST /api/operacoes/{id}/executar` / CLI
  `fotoorganizer executar <plano_id> --confirmar`
- Entradas: id do plano; aprovação explícita (a UI aprovou o plano; no CLI é
  `--confirmar`, "a aprovação explícita que o invariante 2 pede sem a UI").
- Regras de negócio:
  1. **Duas portas**: sem `dry_run_em` → `DryRunObrigatorio`; com o último
     dry-run reportando `prontos == 0` → `DryRunObrigatorio` com mensagem
     própria. Ter rodado não basta — ele precisa ter aprovado alguma coisa.
     `prontos is None` (plano de versão anterior) deixa a decisão com o
     usuário.
  2. O servidor recusa **e** o executor recusa de novo, por dentro.
  3. Por item: `hash_pre = sha256_full(origem)` → `mkdir(parents=True)` →
     cópia em streaming de 1 MiB com `open("xb")` → `hash_pos =
     sha256_full(destino)`.
  4. `open("xb")` é **criação exclusiva**: se o destino existir, o SO recusa.
     Sobrescrever é impossível no nível do SO, não por checagem do app.
  5. Hash divergente → remove a **CÓPIA** (nunca o original) e marca erro.
  6. Falha no meio da cópia remove o parcial (nunca o original).
  7. `shutil.copystat` preserva mtime/permissões **na cópia**.
  8. Commit **por item** → retomada segura: itens `CONCLUIDA` viram `pulados`
     e não são refeitos.
  9. Cancelamento: o item corrente termina, o plano vira `CANCELADA`.
  10. Mover e excluir **não existem** no MVP, por decisão de segurança.
- Saídas: arquivos copiados no destino; `operation_items` com `status`,
  `hash_pre`, `hash_pos`, `erro`; `operation_plans.status`; audit
  `execucao_iniciada`, `copia_verificada`/`copia`, `execucao_finalizada`.
- Degradação/falha: origem indisponível (volume desconectado) → erro **por
  item**, o resto segue. `FileExistsError` → "destino já existe — sobrescrita
  bloqueada". `ENOSPC` → `erro = "disco cheio"`. Nada disso derruba o plano.
  Job ocupado → 409.
- Estado: parcial — achado **A1** (dois POST simultâneos iniciam duas threads
  no mesmo plano: check-then-act fora do lock); **A3** (o ramo de hash
  divergente não tem teste); **M3** (`OSError` **depois** da verificação
  deixa destino órfão, e a retomada trava em "sobrescrita bloqueada"
  permanente); **B6** (ENOSPC sem teste).
- Testes que provam: `tests/test_operations.py::test_copia_verificada_preserva_originais`,
  `::test_sobrescrita_impossivel`, `::test_execucao_exige_dry_run`,
  `::test_execucao_recusa_plano_sem_nada_copiavel`,
  `::test_origem_indisponivel_nao_para_o_resto`,
  `::test_cancelamento_e_retomada`, `::test_audit_log_completo`;
  `tests/test_server_api.py::test_execucao_nunca_sobrescreve_destino_que_surgiu_depois`
- Decisões: invariantes 1-3 do CLAUDE.md; D-011 (execução de plano não fora
  exercitada)
- Arquivos: `fotoorganizer/operations/executor.py:138-283`,
  `fotoorganizer/server/jobs.py:124-134,243-263`,
  `fotoorganizer/server/app.py:1314-1323`, `fotoorganizer/cli.py:533-555`

---

### F-A18 — Inventário por pasta ao lado das fotos copiadas
- Propósito: deixar um manifesto legível por humano e por máquina junto das
  fotos, que responda "por quê?" mesmo sem o app.
- Gatilho: efeito automático de cada item copiado com sucesso em
  `POST /api/operacoes/{id}/executar` / CLI `executar`
- Entradas: o `OperationItem` já copiado e verificado.
- Regras de negócio:
  1. Roda **só depois** que a cópia já foi verificada por hash. Nunca decide
     se a cópia é válida — só registra o que já foi verificado.
  2. Um par `inventario.json` + `INVENTARIO.md` **por PASTA de destino**,
     **aditivo** entre execuções de planos diferentes. Nunca um par por foto
     nem por plano.
  3. Escrita atômica: `.tmp` no mesmo diretório + `os.replace`.
     `write_text` trunca antes de escrever, e um crash no meio corromperia o
     arquivo para a **próxima** leitura, travando a pasta inteira.
  4. JSON corrompido de execução anterior é **renomeado** para
     `inventario.json.corrompido-<epoch>` e preservado para inspeção; o MD é
     sempre regenerado do JSON inteiro.
  5. Idempotente: se `arquivo` já está no inventário, não duplica.
  6. `tamanho` vem do arquivo **realmente copiado**, não de `media.tamanho` —
     os dois divergem se o original mudou entre o catálogo e esta execução.
  7. Guarda as **evidências** da sugestão aprovada e a `versao_logica`.
- Saídas: `<destino>/inventario.json` e `<destino>/INVENTARIO.md`.
- Degradação/falha: **nunca bloqueante**. Envolto em `except Exception`
  genérico de propósito — não só `OSError`, porque um JSON corrompido levanta
  `JSONDecodeError` (`ValueError`), e qualquer falha inesperada não pode
  abortar o PLANO INTEIRO no meio deixando cópias verificadas com o commit
  pendente. Incrementa `stats["inventario_falhou"]` e grava audit
  `inventario`. A cópia real nunca depende do manifesto.
- Estado: pronto
- Testes que provam: `tests/test_operations.py::test_inventario_registra_evidencia_e_hash_verificado`,
  `::test_inventario_e_aditivo_entre_execucoes_e_idempotente`,
  `::test_falha_no_inventario_nao_desfaz_copia_verificada`,
  `::test_inventario_corrompido_recupera_em_vez_de_travar_o_plano`
- Decisões: **D-062** (desenho), D-061 (entra antes do lançamento), D-063,
  D-064
- Arquivos: `fotoorganizer/operations/inventario.py:38-173`,
  `fotoorganizer/operations/executor.py:221-241`

---

### F-A19 — Plano de escrita EXIF de localização
- Propósito: a única escrita autorizada em arquivo original — GPS lat/long,
  cidade e país, **somente em campo vazio** (D-075 revoga parte do
  invariante 7). O plano é só registro; nada toca o disco aqui.
- Gatilho: tela `EscritaExif.tsx` → rota `POST /api/exif/plano` (**sem
  corpo**: escopo global, escrita in-place, não há raiz a escolher) / CLI n/a
- Entradas: nenhuma.
- Regras de negócio:
  1. Candidato = `MediaFile.organizavel` **e** (GPS lido ausente com GPS
     estimado presente **ou** `Location.cidade`/`Location.pais` presente).
     Sem recorte por fonte — escopo é global.
  2. Exclui mídia cujos **três** campos já estão em `(GRAVADO, PULADO,
     SEM_VALOR)`. Sem isso, todo plano novo renasceria com centenas de linhas
     "nada a gravar" e a tela perderia o sinal. Item com qualquer campo em
     `FALHA` ou `PENDENTE` **continua elegível** — replanejar depois de falha
     parcial é o caminho de recuperação.
  3. "Já preenchido" é checado aqui pelo **catálogo** (`metadata_entries`
     namespace `iptc`/`xmp`, chaves `City`, `Country`,
     `Country-PrimaryLocationName`) numa **única** consulta agregada, não
     N+1. O valor concreto vira o motivo de `PULADO`. A checagem
     autoritativa, ao vivo no disco, é do dry-run.
  4. Status inicial por campo: `PULADO` (já preenchido), `SEM_VALOR` (motor
     não inferiu), `PENDENTE` (candidato real).
  5. Allowlist de formatos é **medida, não suposta**: `.jpg/.jpeg/.cr2`
     aprovam; `.dng/.tif/.tiff` reprovam; `.cr3/.heic/.heif` são **"não
     testado"** — categoria diferente de "reprovado". Toda linha não
     suportada carrega um motivo visível (D-05), e `motivo()` nunca devolve
     string vazia.
  6. Formato não aprovado → `sidecar_destino = foto.<ext>.xmp` e
     `incluido=False` (**D-06 é opt-in**). Formato aprovado →
     `incluido=True` (**D-02 é opt-out**).
  7. Pasta sincronizada (iCloud Drive, File Provider, Dropbox legado) é
     **aviso, nunca bloqueio** — checagem pura de caminho, O(1), com
     `resolve()` antes de comparar (cobre o redirecionamento de
     Desktop/Documents do iCloud).
  8. Auditoria com `plan_id=None` e o id do plano em
     `detalhe["exif_plan_id"]`: a coluna tem FK real e ativa para
     `operation_plans.id`, e gravar ali o id de um `ExifWritePlan` derruba o
     insert com `PRAGMA foreign_keys=ON`.
- Saídas: `exif_write_plans` + N `exif_write_items`;
  `audit_log(acao="plano_exif_criado", plan_id=None)`.
- Degradação/falha: nada a planejar → `None` → 409 com cópia específica.
  `resolve()` falhando na detecção de sync → `None`, a resposta segura.
- Estado: pronto
- Testes que provam: `tests/test_exif_write_planner.py::test_sem_candidato_devolve_none`,
  `::test_lista_campo_vazio_e_valor_que_entraria`,
  `::test_campo_ja_preenchido_no_arquivo_sai_como_pulado`,
  `::test_campo_sem_valor_inferido`,
  `::test_formato_nao_suportado_vira_linha_com_motivo_e_sidecar`,
  `::test_pasta_sincronizada_marcada`,
  `::test_audit_log_do_plano_nao_usa_plan_id`,
  `::test_criar_plano_nao_toca_o_disco`,
  `::test_midia_ja_resolvida_nao_reentra`;
  `tests/test_exif_write_api.py::test_criar_plano_sem_candidato_devolve_409`
- Decisões: **D-075** (autoriza a escrita), **D-076** (allowlist medida),
  **D-077** (remedição byte a byte: jpg/cr2 aprovam), D-078
- Arquivos: `fotoorganizer/exif_write/planner.py:56-229`,
  `fotoorganizer/exif_write/formatos.py:40-128`,
  `fotoorganizer/exif_write/sync_detect.py:15-52`,
  `fotoorganizer/server/app.py:1379-1391`

---

### F-A20 — Dry-run de escrita EXIF (passo autoritativo)
- Propósito: o plano foi montado a partir do catálogo, que pode estar
  desatualizado em relação ao disco. Aqui o disco é lido **ao vivo**, e o
  resultado é o que a execução exige ter acontecido.
- Gatilho: tela `EscritaExif.tsx` → rota `POST /api/exif/{id}/dry-run` /
  CLI n/a
- Entradas: id do plano.
- Regras de negócio:
  1. **Só lê.** `dump_lote` em uma única invocação por fatia de 200 caminhos:
     ~1.400 arquivos a ~200 ms cada seriam ~5 min; em lote são segundos.
  2. `pasta_sincronizada` é recomputada **sempre**, mesmo se a origem sumiu —
     é checagem pura de caminho.
  3. Origem que não é arquivo → entra em `problemas` e **nenhum campo muda de
     status** (o item continua elegível depois).
  4. Sidecar cujo destino **já existe** → os três campos viram `PULADO` com
     "sidecar já existe — nunca será sobrescrito".
  5. Por campo: sem valor → `SEM_VALOR`; já preenchido no dump → `PULADO`
     com o valor legível; `validar_campos` falhou → `FALHA`; senão `PRONTO`.
  6. `prontos` conta **itens** (com `incluido` e ≥1 campo pronto);
     `campos_a_gravar` conta campos. São números diferentes e a UI mostra os
     dois.
  7. Grava `dry_run_em` e `audit_log(acao="dry_run_exif", plan_id=None)`.
- Saídas: `{prontos, problemas[], campos_a_gravar, sidecars, nao_suportados,
  sincronizados}`; status por campo em cada item; uma linha de auditoria.
- Degradação/falha: sem exiftool, `dump`/`dump_lote` devolvem `{}` e **nunca
  levantam** — na prática todo campo aparece como não preenchido, e a
  execução falharia na verificação. Plano inexistente → 404. Timeout de 30 s
  por invocação.
- Estado: parcial — os testes deste caminho têm `skipif` sem exiftool e, sem
  CI, passam verde sem executar (**M6**).
- Testes que provam: `tests/test_exif_write_executor.py::test_dry_run_nao_escreve`,
  `::test_dry_run_promove_campo_vazio_e_pula_preenchido`;
  `tests/test_exif_write_api.py::test_dry_run_e_veredito`,
  `::test_detalhe_traz_campos_por_campo`
- Decisões: D-075 (EXIF-01, EXIF-02)
- Arquivos: `fotoorganizer/exif_write/executor.py:143-255`,
  `fotoorganizer/exif_write/verificacao.py:314-376`,
  `fotoorganizer/server/app.py:1403-1409`

---

### F-A21 — Seleção de itens antes de gravar (D-02 / D-06)
- Propósito: o dono desmarca item pontual antes de confirmar. Item
  desmarcado **não é escrito, e nenhum subprocesso roda para ele** — é isso
  que prova o opt-out.
- Gatilho: tela `EscritaExif.tsx` (checkboxes) → corpo de
  `POST /api/exif/{id}/executar` `{itens: int[] | null}` / CLI n/a
- Entradas: lista de ids de `ExifWriteItem`, ou `null`.
- Regras de negócio:
  1. `itens is None` **preserva** a seleção já persistida; lista **vazia**
     zera a seleção. O endpoint distingue os dois casos, não confunde "não
     mandou nada" com "mandou lista vazia".
  2. A seleção é **persistida antes** de o job começar: a execução relê do
     banco, então passá-la só como argumento perderia o registro de auditoria
     e a fonte de verdade da retomada.
  3. Grava `audit_log(acao="selecao_exif")` com `{exif_plan_id, incluidos,
     excluidos}`.
  4. Seleção resultante zero → 409 "nenhum item selecionado para gravar", e o
     job **não** é disparado.
  5. Assimetria deliberada no nascimento: `incluido=True` para formato
     aprovado (D-02 é opt-out) e `incluido=False` para linha de sidecar
     (D-06 é opt-in).
- Saídas: `exif_write_items.incluido`; uma linha de auditoria; a contagem de
  incluídos.
- Degradação/falha: plano sem dry-run → 409 antes de chegar aqui. Ids
  inexistentes simplesmente não casam (os itens do plano que não estiverem na
  lista viram `incluido=False`).
- Estado: pronto
- Testes que provam: `tests/test_exif_write_executor.py::test_item_desmarcado_nao_e_escrito`;
  `tests/test_exif_write_api.py::test_selecao_vazia_devolve_409`
- Decisões: D-075 (D-02 e D-06 do plano da Fase 6)
- Arquivos: `fotoorganizer/exif_write/executor.py:258-278`,
  `fotoorganizer/exif_write/planner.py:205-207`,
  `fotoorganizer/server/app.py:161-166,1411-1425`

---

### F-A22 — Execução da escrita EXIF, verificada por diff de tags
- Propósito: mutar o arquivo original em escopo estreito, com um critério de
  sucesso que não pode ser enganado pelo subprocesso.
- Gatilho: tela `EscritaExif.tsx` → rota `POST /api/exif/{id}/executar` /
  CLI n/a
- Entradas: id do plano; seleção já persistida (F-A21).
- Regras de negócio:
  1. **Duas portas**, como na cópia: sem `dry_run_em` → `DryRunObrigatorioExif`;
     último dry-run com `prontos == 0` → idem.
  2. **O exit code do exiftool não é sinal de sucesso.** Verificado em 13.55:
     `-GPSLatitude=notanumber -City=X -Country=Y` imprime warning, pula só a
     tag malformada, escreve City e Country, reporta "1 image files updated"
     e sai 0. O único sinal confiável é o diff completo de tags antes/depois.
  3. `hash_pre`/`hash_pos` são **fato de auditoria, nunca critério**: a
     escrita é mutação intencional, o hash do arquivo muda sempre por
     construção. Quem aprova é o diff de tags.
  4. **Reconferência TOCTOU ao vivo**: só entra na lista quem continua
     `PRONTO` **e** cujas tags continuam ausentes **agora**. Campo que passou
     a estar preenchido entre o dry-run e agora vira `PULADO` sem tocar em
     nada. É isto que torna rerodar idempotente sem depender de o dry-run
     estar fresco.
  5. Lista vazia após a reconferência → `pulados++`, **nenhum subprocesso**.
  6. Argumentos exatos (lista, sem shell): `-GPSLatitude=<abs(lat)>`,
     `-GPSLatitudeRef=<N|S>`, `-GPSLongitude=<abs(lon)>`,
     `-GPSLongitudeRef=<E|W>`, `-IPTC:City=`, `-XMP:City=`,
     `-IPTC:Country-PrimaryLocationName=`, `-XMP:Country=`, `-charset
     filename=utf8`, `<alvo>`. Os **dois grupos** de cidade/país são sempre
     gravados: `-City` sem prefixo cai em IPTC e `-Country` sem prefixo cai
     em XMP-photoshop, e gravar só um deixaria o dado invisível para metade
     dos consumidores.
  7. `validar_campos` é a única fronteira de validação do pacote e roda
     **antes de qualquer subprocesso**: lat em `[-90,90]`, lon em
     `[-180,180]`, ambas finitas; cidade/país `str` não vazio, sem quebra de
     linha, ≤ 200 caracteres.
  8. Veredito **por campo**: `campo_gravado` exige **todas** as tags do campo
     em `diff.esperadas`. Cidade que entrou no IPTC mas não no XMP é falha.
  9. Classificação do diff em 4 baldes, nesta ordem: `estruturais` (andaime
     inevitável, lista fechada e justificada item a item) → volátil
     (descartado) → `esperadas` (tag de localização que **entrou**) →
     `inesperadas`. Tag de localização que **sumiu** vai para `inesperadas`.
  10. Allowlist condicional D-077: tag de offset/ponteiro só deixa de contar
      como inesperada quando o conteúdo binário que ela aponta é
      sha256-idêntico antes e depois — prova byte a byte usando o próprio
      `_original` como "antes". **Fail-safe**: qualquer condição que falhe
      mantém a tag em `inesperadas`, nunca promove por omissão.
  11. Critério de aviso é **delta** (nenhum aviso NOVO), não "zero avisos
      depois" — e a coleta é em texto plano, porque a saída `-j` colapsa
      warnings repetidos (um TIFF com 6 devolve 1, silenciando 5).
  12. Corrupção (tag inesperada ou aviso novo) → reprova **tudo** que foi
      tentado e **preserva o backup**.
  13. **Falha parcial é resultado real e esperado** (EXIF-03): algum campo
      gravou, outro não, sem tag inesperada → registrado campo a campo,
      backup mantido, e **não** derruba o plano para `ERRO`.
  14. Commit por item → retomada segura.
- Saídas: tags gravadas no arquivo original; `exif_write_items` com status
  por campo, motivos, `hash_pre`/`hash_pos`, `backup_original`, `erro`;
  `exif_write_plans.status`; auditoria `execucao_exif_iniciada`,
  `escrita_exif`/`escrita_exif_verificada`, `limpeza_backup_exiftool`,
  `execucao_exif_finalizada` — todas com `plan_id=None`.
- Degradação/falha: origem indisponível → erro por item, **nenhum campo muda
  de status** (rerodar retoma). `ValorInvalido` → campos tentados viram
  `FALHA`. `OSError` inesperado → erro por item, nunca derruba o plano. Sem
  exiftool → a escrita é impossível; não há caminho alternativo.
- Estado: parcial — **A1** (dois POST simultâneos: o 2º exiftool renomeia a
  versão modificada por cima do `.jpg_original`); **A2** (no sidecar, grava
  `abs(lat)` + `-GPSLatitudeRef`, que não é gravável em XMP: `(-22.95,
  -43.18)` vira `22,57.0N`, e a verificação só checa presença, marcando
  `GRAVADO` — estado sticky); **A4** (TOCTOU no alvo direto sem teste);
  **M6** (`skipif` sem exiftool, sem CI).
- Testes que provam: `tests/test_exif_write_executor.py::test_executar_sem_dry_run_levanta`,
  `::test_escreve_e_verifica_por_diff`,
  `::test_nunca_escreve_fora_de_localizacao`,
  `::test_diff_detecta_falha_parcial`, `::test_rerodar_e_idempotente`,
  `::test_audit_de_execucao_nao_viola_fk`,
  `::test_executar_nao_regride_por_deslocamento_de_offset`;
  `tests/test_exif_write_writer.py::test_escrever_tag_gps_malformada_falha_sozinha`,
  `::test_validar_campos_nao_chama_subprocesso`,
  `::test_campo_gravado_exige_todas_as_tags_do_campo`,
  `::test_reclassificar_conteudo_corrompido_continua_inesperada_e_reprova`
- Decisões: **D-075** (EXIF-01..EXIF-05), **D-077**, **D-078**
- Arquivos: `fotoorganizer/exif_write/executor.py:287-552`,
  `fotoorganizer/exif_write/writer.py:32-138`,
  `fotoorganizer/exif_write/verificacao.py:33-146,241-490`,
  `fotoorganizer/server/jobs.py:136-147,265-291`

---

### F-A23 — Sidecar XMP para formato não aprovado
- Propósito: gravar a localização **sem tocar** em arquivo cujo formato não
  passou na medição de escrita — o dado fica num `.xmp` ao lado.
- Gatilho: mesma execução de F-A22, para itens com `formato_suportado=False`
  e `incluido=True`
- Entradas: o item do plano, com `sidecar_destino` já calculado pelo planner.
- Regras de negócio:
  1. Nome: `foto.<ext>.xmp` — a convenção Adobe, que
     `metadata/exiftool.py::_sidecar_de` já procura **primeiro** ao ler. Um
     sidecar novo é pego pela próxima varredura sem nenhuma mudança do lado
     da leitura.
  2. **Opt-in** (D-06): a linha nasce `incluido=False`.
  3. **Sidecar existente nunca é sobrescrito**: no dry-run vira `PULADO` nos
     três campos; na execução vira erro do item.
  4. Os argumentos `-IPTC:` são **omitidos** quando o alvo é `.xmp`: IPTC é
     formato de segmento binário de container de imagem, não existe num
     `.xmp` autônomo.
  5. As tags conferidas são outras (`TAGS_POR_CAMPO_SIDECAR`):
     `XMP-exif:GPSLatitude`/`GPSLongitude`, `XMP-photoshop:City`,
     `XMP-photoshop:Country`.
  6. Quando o alvo ainda não existe, o "antes" é `{}` — por isso
     `File:FileType`, `File:FileTypeExtension` e `File:MIMEType` entram no
     andaime estrutural: descrevem só "este arquivo é um .xmp".
  7. Sucesso conta em `stats["sidecars"]`, não em `stats["gravados"]`.
- Saídas: arquivo `.xmp` novo ao lado do original; `exif_write_items`
  atualizado; auditoria com `alvo = sidecar_destino`.
- Degradação/falha: sidecar já existe → erro do item, nada é escrito.
  Formato "não testado" (`.cr3/.heic/.heif`) segue o mesmo caminho de
  sidecar, com motivo que diz **"sem teste de escrita neste acervo"**, não
  "reprovado" — são coisas diferentes e o texto é literal na UI.
- Estado: parcial — o achado **A2** afeta exatamente este caminho
  (`.dng/.tif/.cr3/.heic`; 3 de 1.399 arquivos hoje).
- Testes que provam: `tests/test_exif_write_executor.py::test_formato_nao_suportado_grava_sidecar`,
  `::test_sidecar_existente_nunca_e_sobrescrito`;
  `tests/test_exif_write_writer.py::test_escrever_com_destino_xmp_cria_sidecar_autonomo_sem_iptc`,
  `::test_caminho_sidecar_convencao_foto_ext_xmp`,
  `::test_motivo_cr3_cita_sem_teste_de_escrita`,
  `::test_motivo_extensao_desconhecida_nunca_e_none`
- Decisões: **D-076**, **D-077** (allowlist), D-075 (D-05, D-06, EXIF-05)
- Arquivos: `fotoorganizer/exif_write/formatos.py:48-128`,
  `fotoorganizer/exif_write/writer.py:94-124`,
  `fotoorganizer/exif_write/verificacao.py:47-51,94-103`,
  `fotoorganizer/exif_write/executor.py:362-368`

---

### F-A24 — Backup `_original`: preservação e restauração
- Propósito: mutação in-place não tem o truque da criação exclusiva. O
  backup que o exiftool cria por padrão é a rede de recuperação durante a
  janela entre escrita e verificação.
- Gatilho: efeito automático de F-A22; leitura em `GET /api/exif/{id}`
  (`backup_original` por item) / CLI n/a
- Entradas: nenhuma — é comportamento, não comando.
- Regras de negócio:
  1. O writer **nunca** passa `-overwrite_original`. Passar a flag destruiria
     a recuperação exatamente na janela em que ela importa.
  2. Nome: `Path(str(alvo) + "_original")`.
  3. O backup só é **apagado** depois que o diff de tags **e** o delta de
     avisos aprovarem TUDO. É passo deliberado e auditado
     (`limpeza_backup_exiftool`).
  4. Falha ao apagar o backup **nunca** derruba uma escrita já verificada —
     só `log.warning`. A limpeza é auxiliar; a escrita real já está correta.
  5. Em falha de verificação ou falha parcial, o caminho do backup é gravado
     em `ExifWriteItem.backup_original` e **preservado**.
  6. **O app nunca desfaz nada sozinho** (invariante 8). Quem decide restaurar
     é o dono; o app só preserva e expõe o caminho.
  7. Manter o backup para sempre poluiria a árvore que o scanner trata como
     observada-somente-leitura e confundiria cliente de sync — por isso a
     limpeza no caminho feliz.
- Saídas: arquivo `<alvo>_original` no disco (temporária ou
  permanentemente); `exif_write_items.backup_original`; auditoria.
- Degradação/falha: o backup é o "antes" byte a byte usado pela
  reclassificação de offsets (D-077) — sem ele, toda escrita real em
  `.jpg/.cr2` reprovaria de novo por deslocamento de bloco binário
  pré-existente.
- Estado: parcial — **não há comando de restauração** no app (nem CLI, nem
  rota): a restauração é ato manual do dono, fora do produto.
- Testes que provam: `tests/test_exif_write_executor.py::test_backup_apagado_so_apos_sucesso_verificado`,
  `::test_executar_nao_regride_por_deslocamento_de_offset`;
  `tests/test_exif_write_writer.py::test_escrever_deixa_backup_original_ao_lado`
- Decisões: D-075, **D-077**
- Arquivos: `fotoorganizer/exif_write/writer.py:77-93`,
  `fotoorganizer/exif_write/executor.py:434-521`,
  `fotoorganizer/models/exif_write.py:123`

---

### F-A25 — Trilha de auditoria (audit log)
- Propósito: invariante 3 — "registrar tudo em audit log". Toda ação que
  escreve fora do catálogo, ou que reescreve o catálogo em massa, deixa
  rastro consultável.
- Gatilho: efeito de F-A07, F-A15..F-A19, F-A21..F-A24 → rotas
  `GET /api/operacoes/{id}/auditoria` e `GET /api/exif/{id}/auditoria` /
  CLI `fotoorganizer planos` (mostra o veredito derivado da trilha)
- Entradas: nenhuma para leitura; as ações geram as linhas.
- Regras de negócio:
  1. Colunas: `quando`, `plan_id`, `acao`, `detalhe` (JSON), `resultado`.
  2. **`plan_id` tem FK real e ativa** para `operation_plans.id`. Com
     `PRAGMA foreign_keys=ON`, gravar ali o id de um `ExifWritePlan`
     (sequência de PK independente) **derruba o insert**. Por isso o domínio
     de escrita EXIF e o reapontamento gravam `plan_id=None`, e o id viaja em
     `detalhe["exif_plan_id"]`.
  3. Consequência: a consulta de auditoria do domínio EXIF filtra por JSON
     (`AuditLog.detalhe["exif_plan_id"].as_integer() == plan_id`), nunca pela
     coluna.
  4. O **veredito do dry-run mora no audit log**, não na tabela do plano —
     copiá-lo criaria duas verdades livres para divergir. Vale para os dois
     domínios.
  5. Ações gravadas: `plano_criado`, `dry_run`, `execucao_iniciada`,
     `copia_verificada`, `copia`, `inventario`, `execucao_finalizada`,
     `reapontar_fonte`, `plano_exif_criado`, `dry_run_exif`, `selecao_exif`,
     `execucao_exif_iniciada`, `escrita_exif`, `escrita_exif_verificada`,
     `limpeza_backup_exiftool`, `execucao_exif_finalizada`.
  6. A entrada `reapontar_fonte` é **reversível por construção**: guarda os
     dois prefixos e o `source_id`, e é o insumo de `--desfazer`.
  7. Auditoria por item da escrita EXIF carrega `campos` + `tags_gravadas`
     juntos — exatamente o que EXIF-03 pede: quais tags entraram antes do
     erro, numa linha só.
  8. Nenhuma linha de auditoria é apagada.
- Saídas: `audit_log`; listas ordenadas nas duas rotas (limite 500).
- Degradação/falha: plano inexistente → 404. Scan, importação, reconciliação
  e duplicatas **não** escrevem aqui — não tocam o filesystem (a trilha do
  scan é a `ScanSession`).
- Estado: pronto
- Testes que provam: `tests/test_operations.py::test_audit_log_completo`;
  `tests/test_exif_write_planner.py::test_audit_log_do_plano_nao_usa_plan_id`;
  `tests/test_exif_write_executor.py::test_audit_de_execucao_nao_viola_fk`;
  `tests/test_exif_write_api.py::test_auditoria_do_plano_exif`;
  `tests/test_reapontar.py::test_audit_log_criado_com_os_prefixos`
- Decisões: invariante 3 do CLAUDE.md; D-075
- Arquivos: `fotoorganizer/models/operations.py:79-92`,
  `fotoorganizer/repositories/operations.py:86-133`,
  `fotoorganizer/repositories/exif_write.py:127-154`,
  `fotoorganizer/server/app.py:1292-1305,1427-1440`

---

### F-A26 — Config em camadas e gates de privacidade
- Propósito: dar ao dono controle explícito sobre onde o catálogo mora e o
  que pode sair da máquina, com precedência previsível e nenhum caminho
  acidental para ligar um recurso sensível.
- Gatilho: tela `TemplateEditor` (dentro de `Operations`) e `ClassificacaoPasta.tsx` (gate
  GenAI) → rotas `GET|PUT /api/configuracoes/template`,
  `GET|PUT /api/genai-pasta/config` / CLI: flags globais + env vars
  `FOTOORG_*` em **todos** os subcomandos
- Entradas: `config.toml`, flags de CLI, env vars, e as duas chaves de
  `application_settings`.
- Regras de negócio:
  1. Precedência: `defaults < derivados de outro flag < TOML < CLI/env
     explícito`.
  2. A sentinela `UNSET` distingue "flag não passado" de "passado com valor
     vazio/zero/false" — sem ela, `--workers 0` e `--no-seguir-symlinks`
     seriam indistinguíveis de omitir o flag.
  3. Flag de CLI **vence** env var na mesma invocação (é ainda mais
     explícito).
  4. Env var exportada **vazia** conta como ausente: tratar `""` como valor
     fazia `data_dir` virar `Path('.')`, e um `scan` criava catálogo, cache e
     logs no diretório corrente do shell enquanto o catálogo real ficava
     intacto e simplesmente não aparecia.
  5. Env booleana irreconhecível é **erro de uso** (usage + código 2), nunca
     palpite — um valor virando `False` em silêncio vencia um `true` do TOML.
  6. `--data-dir` sozinho **também deriva** `cache_dir`, como camada
     *derivada*: perde para um `cache_dir` escrito no TOML.
  7. TOML inválido ou ilegível → `log.error` + defaults, nunca derruba o app.
     Seção ou chave desconhecida é ignorada **com aviso**, nunca em silêncio.
  8. `privacidade.servicos_externos` é a chave **mestra** (invariante 4).
     Enquanto for `False`, nada sai da máquina: `jobs._advisor()` devolve
     `None` e o classificador de pasta resolve para `ClassificacaoDePastaNula`.
  9. `privacidade.reconhecimento_facial` fica **fora** da camada de CLI/env
     de propósito: ligar reconhecimento facial (invariante 6) tem de ser
     decisão escrita na config do usuário, não algo que um script de CI, um
     alias de shell ou uma env var herdada consigam ligar de passagem.
  10. **Gate de dois consentimentos** do GenAI de pasta (D-080): exige a
      CONJUNÇÃO de `servicos_externos` (mestra, **só TOML**, fora do alcance
      da UI) **e** `classificacao_pasta_genai` (opt-in do recurso, em
      `application_settings`, gravável pela UI). Copiar o gate de um flag só
      — como `_advisor` faz — seria a regressão nomeada no research: este
      recurso **não pega carona** no consentimento dado ao Advisor.
  11. `PUT /api/genai-pasta/config` grava **só** o opt-in do recurso; ligar
      com o mestre desligado → 409 com mensagem literal reusada pela UI.
- Saídas: `Settings` resolvido; `application_settings.template_destino` e
  `.classificacao_pasta_genai`.
- Degradação/falha: config ausente → defaults. `write_config_template` grava
  o template comentado **sem** sobrescrever config existente.
- Estado: pronto
- Testes que provam: `tests/test_cli.py::test_flag_cli_sobrescreve_toml`,
  `::test_env_var_usada_quando_flag_nao_veio_mas_flag_explicito_vence_env`,
  `::test_env_booleana_irreconhecivel_e_erro_de_uso_e_nao_palpite`,
  `::test_env_var_de_caminho_vazia_nao_reaponta_o_catalogo_para_o_cwd`,
  `::test_cache_dir_explicito_vence_o_derivado_de_data_dir`,
  `::test_data_dir_isola_o_catalogo_do_padrao`,
  `::test_workers_zero_explicito_nao_e_confundido_com_nao_passado`;
  `tests/test_config.py` (suíte);
  `tests/test_settings_repository.py` (suíte);
  `tests/test_api_genai_pasta.py` (suíte)
- Decisões: **D-080** (opt-in mora em `application_settings`), invariantes 4
  e 6 do CLAUDE.md
- Arquivos: `fotoorganizer/config/settings.py:20-243`,
  `fotoorganizer/config/paths.py:10-27`, `fotoorganizer/cli.py:50-170,690-729`,
  `fotoorganizer/repositories/settings.py:16-64`,
  `fotoorganizer/server/genai_pasta.py:42-151`

---

### F-A27 — Servidor local: bind, guard de origem e progresso
- Propósito: expor o motor Python para a UI web **sem** abrir uma superfície
  de rede, e sem deixar que uma página qualquer do navegador do usuário
  dispare ações no catálogo.
- Gatilho: CLI `fotoorganizer web [--porta N] [--encerrar-com-pai]`; rotas
  `GET /api/job`, `GET /api/progresso`
- Entradas: porta (default 8765; `0` = efêmera).
- Regras de negócio:
  1. Socket criado à mão com `bind(("127.0.0.1", porta))` — **só loopback**,
     nunca `0.0.0.0`.
  2. `FOTOORG_READY <url>` no stdout, com `flush=True`, assim que o socket
     está ligado: é a linha estável que o supervisor lê para descobrir a
     porta efêmera.
  3. Guard de origem em **toda** requisição: `Host` não-local → 403 (denuncia
     DNS rebinding); `Origin` **presente** e não-local → 403 + `log.warning`
     (denuncia página de terceiros). `Origin` ausente (curl, CLI, navegação
     na própria página) segue normal. Escutar no loopback não bastaria: POST
     sem corpo é "simple request" e o navegador o envia sem preflight.
  4. `webapp/dist` é montado em `/` **por último**, só se existir — o
     catch-all não engole `/api/*`.
  5. Um trabalho por vez; snapshot atômico do estado, consultável por polling
     (`GET /api/job`) ou SSE (`GET /api/progresso`, emite só quando o
     snapshot muda, intervalo de 0,5 s, fecha quando o status sai de
     "rodando"). O cliente tem fallback de polling com backoff 1→15 s.
  6. `--encerrar-com-pai`: thread daemon compara `os.getppid()` a cada 2 s e
     manda `SIGTERM` em si mesma se o pai mudou — rede de segurança além do
     SIGTERM do shell, para nunca deixar backend órfão.
  7. `uvicorn.Server` instala handlers de SIGINT/SIGTERM: o processo encerra
     limpo, com checkpoint WAL.
  8. Log estruturado **em arquivo**, não só stderr: o servidor morre junto
     com o terminal que o abriu, e dois scans do acervo real (93 mil e 225
     mil arquivos) morreram sem uma linha de log que dissesse por quê.
- Saídas: servidor HTTP em `http://127.0.0.1:<porta>`; logs em
  `<data_dir>/logs`.
- Degradação/falha: hooks de startup (`reconciliar_orfas`, `verificar`) são
  protegidos por `try/except` + `log.warning` — falha neles não impede o
  servidor de subir. `webapp/dist` ausente → só a API responde.
- Estado: parcial — **B1** (`localhost` sem porta no guard de Origin);
  **B2** (`csp: null` no Tauri e nenhum header CSP no FastAPI); **A1**
  (rotas de execução são `def` síncronas, servidas em threadpool, e o
  check-then-act do job está fora do lock); **B9** (12 `select()` diretos no
  `app.py`, fora dos repositórios).
- Testes que provam: `tests/test_server_api.py::test_pagina_externa_nao_dispara_acoes`,
  `::test_host_nao_local_e_recusado`,
  `::test_origem_local_e_ausencia_de_origem_seguem_normais`,
  `::test_scan_em_background_indexa_e_reporta`;
  `tests/test_web_launch.py` (falha no sandbox por restrição de rede);
  `tests/test_logsetup.py`
- Decisões: UI web local (2026-07-24); invariante 5 do CLAUDE.md global
- Arquivos: `fotoorganizer/server/app.py:97-112,450-470,1509-1545,1598-1632`,
  `fotoorganizer/server/jobs.py:41-163`, `fotoorganizer/cli.py:615-682`

---

### F-A28 — Empacotamento macOS: Tauri + runtime Python embarcado
- Propósito: distribuir um `.app` assinado e notarizado em que o backend
  Python e o webapp já vêm dentro, sem o usuário instalar nada.
- Gatilho: n/a (build) — `scripts/empacotar_runtime.sh`,
  `scripts/assinar_runtime.sh`, `cargo tauri build`
- Entradas: `webapp/dist` construído; certificado Developer ID no keychain;
  toolchain Rust + `tauri-cli ^2`.
- Regras de negócio:
  1. **python-build-standalone, não PyInstaller**: o gargalo não é embarcar
     Python, é assinar e notarizar as bibliotecas nativas (libraw via rawpy,
     libheif via pillow-heif, os `.so` de Pillow) sob hardened runtime. No
     PBS a árvore é um Python "normal" e um loop `codesign` sobre
     `*.dylib/*.so` cobre tudo.
  2. Descartados: **PyInstaller sidecar** (cada dep nativa nova pode exigir
     hook/`--collect`) e **venv no 1º boot** (baixa wheels em runtime → código
     nativo não assinado, e fura o invariante local-first).
  3. O webview carrega de `http://127.0.0.1:<porta>` servido pelo próprio
     FastAPI: o front usa só URLs relativas, herda a origem e o guard de
     origem local passa intacto. O Tauri fica reduzido a janela, ciclo de vida
     e assinatura — **nenhuma mudança na comunicação front↔back**.
  4. `windows: []` na config é intencional: a janela só nasce depois que a
     porta efêmera é conhecida (o shell lê `FOTOORG_READY` do stdout).
  5. O shell passa `--porta 0 --encerrar-com-pai` e **nenhum** `--data-dir`:
     o catálogo fica no padrão.
  6. Encerramento com **SIGTERM, não SIGKILL** → uvicorn drena e faz o
     checkpoint WAL. Sem netos: os workers são threads.
  7. O build **embarca o `webapp/dist` dentro do runtime**, em
     `site-packages/webapp/dist`, que é onde `_WEBAPP_DIST =
     parents[2]/webapp/dist` resolve lá dentro. Sem isso o backend empacotado
     não serve a UI e `/` dá 404.
  8. Extras padrão do runtime: `xmp,apple`. `dev` fica de fora; **`llm` (que
     envia dados) é opt-in de release**.
  9. O script **prova** que `rawpy`, `pillow_heif`, `reverse_geocode`,
     `osxphotos`, `PIL` e `fotoorganizer` importam a partir do runtime
     congelado.
  10. Assinatura é passo **separado**, antes do `cargo tauri build`: o Tauri
      assina o `.app` externo, mas não os binários aninhados; sem isso a
      notarização falha com "signature invalid".
- Saídas: `src-tauri/resources/runtime/python/`; `.app` e `.dmg` assinados.
- Degradação/falha: depende de **rede** no momento do build (API do GitHub +
  tarball do PBS), e o asset é resolvido por regex sobre a resposta da API —
  mudança de nomenclatura quebra com "não encontrei asset". `webapp/dist`
  ausente vira aviso, não erro. O **exiftool não é embarcado**: num `.app`
  distribuído, o app degrada para puro-Python e a escrita EXIF fica
  indisponível.
- Estado: parcial — milestone futuro, não exercitado num build real neste
  repositório. Achado **M7**: `allow-unsigned-executable-memory=true`
  contradiz o próprio comentário ("comece sem esta chave") e, junto com
  `disable-library-validation`, derruba boa parte do hardened runtime.
  Achado **B2**: `csp: null`.
- Testes que provam: n/a (nenhum teste cobre o empacotamento;
  `tests/test_web_launch.py` cobre só o anúncio `FOTOORG_READY` e falha no
  sandbox)
- Decisões: `docs/EMPACOTAMENTO.md` (decisão PBS × PyInstaller)
- Arquivos: `src-tauri/src/main.rs:18-88`, `src-tauri/tauri.conf.json`,
  `src-tauri/Entitlements.plist`, `scripts/empacotar_runtime.sh`,
  `scripts/assinar_runtime.sh`, `fotoorganizer/cli.py:615-682`,
  `fotoorganizer/server/app.py:242,1598-1601`

---

### F-A29 — Benchmark de indexação com fixtures sintéticas
- Propósito: medir antes de otimizar, sem nunca tocar o catálogo nem o cache
  de produção.
- Gatilho: rota n/a / CLI `fotoorganizer bench [-n N] [--cache-dir PASTA]`
- Entradas: quantidade de JPEGs sintéticos (default 500); cache opcional.
- Regras de negócio:
  1. Gera N JPEGs 64×48 de cor determinística (`seed`) em 10 subpastas, tudo
     num `TemporaryDirectory`.
  2. O banco é `bench.db` no temporário — **nunca** o catálogo real.
  3. As miniaturas vão para um cache no temporário por padrão;
     `--cache-dir` do bench é **opt-in explícito** para medir contra o cache
     real de propósito, e tem `dest="bench_cache_dir"` próprio para não
     colidir com o `--cache-dir` global (que é outra coisa: aquele troca o
     cache de produção da invocação inteira).
  4. Mede duas passadas: indexação a frio e re-scan (pulando inalterados),
     em arq/s.
  5. Passa pela **mesma** camada de config dos outros comandos — sem isso,
     `fotoorganizer --workers 16 bench` mediria o `workers` do TOML, não o
     que foi pedido; foi assim que `bench` passou a ignorar `--workers`.
  6. Regra do projeto: otimização de produção deve ser medida com **arquivos
     reais do usuário em catálogo temporário** (`--data-dir`), nunca no
     catálogo de produção. O `bench` é o caso sintético.
- Saídas: duas linhas no stdout; nada persistido.
- Degradação/falha: o `TemporaryDirectory` é removido ao final mesmo em erro.
- Estado: pronto
- Testes que provam: `tests/test_cli.py::test_bench_passa_pela_camada_de_cli_e_env`,
  `::test_bench_nao_grava_miniaturas_no_cache_real_do_usuario`,
  `::test_bench_com_cache_dir_explicito_usa_a_pasta_escolhida`
- Decisões: método de trabalho do CLAUDE.md (performance é requisito
  mensurável; baseline antes de otimizar)
- Arquivos: `fotoorganizer/cli.py:558-612,187-207,826-837`

---

### F-A30 — Inventário e funil do acervo (o que existe e onde)
- Propósito: o Panorama responde só sobre o que dá para abrir agora. Num
  acervo em NAS e discos externos isso é a minoria — 5.191 de 100.164 num
  caso real — e a pergunta de quem está descobrindo é outra: **o que existe,
  e onde**.
- Gatilho: tela `Panorama` (seção O acervo)/`Funil` → rotas `GET /api/inventario` e
  `GET /api/funil` / CLI `fotoorganizer inventario`
- Entradas: nenhuma.
- Regras de negócio:
  1. Conta **fotos**, não registros: `fotos` e `total_registros` são números
     diferentes e os dois aparecem.
  2. Agrupa por **raiz** de caminho, com `fotos`, `alcancaveis` e
     `so_no_catalogo` por lugar, e as fontes que contribuíram.
  3. Referências sem arquivo local aparecem numa linha própria
     (`sem_caminho`) — não somem e não se confundem com o que está no disco.
  4. "Alcançável" tem **três** condições, não duas: não offline, não ausente,
     **e a fonte montada**. Sem a terceira, uma pasta em volume desligado
     aparecia com 225 mil "alcançáveis" ao lado do Panorama dizendo "fora de
     alcance" — dois números contraditórios na mesma tela é pior que número
     nenhum.
  5. `GET /api/funil` é **caro por natureza** (~1,4 s em 197 mil linhas):
     percorre o catálogo inteiro para contar foto, não registro. O cliente
     guarda o resultado e só refaz quando um job termina — o número não muda
     sozinho, só scan, importação e geração de sugestões o alteram.
  6. Consultas em lote por limite de variáveis do SQLite (mesmo remédio do
     `_LOTE_SUMICO` do scanner).
- Saídas: `{fotos, alcancaveis, registros, sem_caminho, lugares[]}` e
  `{conhecidas, alcancaveis, organizaveis, registros}`; no CLI, uma tabela
  por raiz.
- Degradação/falha: catálogo vazio → o CLI imprime "Catálogo vazio. Use
  `scan` ou `importar` primeiro." e sai 0.
- Estado: pronto
- Testes que provam: `tests/test_inventario.py` (suíte);
  `tests/test_server_api.py::test_panorama_conta_lacunas_e_facetas`
- Decisões: **D-068** ("Organizáveis" passa a exigir a fonte respondendo, e o
  funil), D-050
- Arquivos: `fotoorganizer/repositories/inventario.py:45-280`,
  `fotoorganizer/server/app.py:503-519,699-724`,
  `fotoorganizer/cli.py:239-262`

---

## Lacunas e incertezas

1. **Nomes de componentes React** citados no campo "Gatilho"
   (`ModalCaminho`, `Sidebar`, `Duplicates.tsx`, `EscritaExif.tsx`,
   `RetomarScan.tsx`, `Operacoes`, `Configuracoes`, `ClassificacaoPasta.tsx`,
   `Inventario`/`Funil`) vêm de grep por rota em `webapp/src` e de
   comentários no código Python. **Não verifiquei a árvore de componentes**:
   alguns podem ser telas compostas, e nomes como `Operacoes`,
   `Configuracoes` e `Inventario` são inferência do domínio, não leitura do
   arquivo. O domínio UX tem a fonte correta.
2. **F-A14**: `POST /api/duplicatas/{id}/*` não tem tratamento visível de
   grupo inexistente no handler (`app.py:1216-1229`); não determinei se
   `repositories/duplicates.py` levanta ou é no-op silencioso.
3. **F-A24**: afirmo que não existe comando de restauração de backup por
   busca no CLI e nas rotas; não varri `scripts/` exaustivamente atrás de um
   utilitário solto.
4. **F-A22/F-A23**: o corpo completo de
   `verificacao._ler_intervalo`, `_valores_numericos`,
   `_e_relocacao_comprovada` e `avisos` (~90 linhas) não foi lido linha a
   linha — as condições de fail-safe vêm dos docstrings e dos nomes dos
   testes.
5. **Retomada de escrita EXIF após crash do processo** (não cancelamento):
   o plano fica `EXECUTANDO` e nada o reconcilia no boot, ao contrário de
   `ScanSession`. Não achei mecanismo equivalente — pode ser lacuna real ou
   intencional (o commit por item torna rerodar seguro), mas não determinei.
6. **F-A28**: nada sobre notarização foi verificado por execução; tudo vem de
   `docs/EMPACOTAMENTO.md` e dos comentários dos scripts. `src-tauri/build.rs`
   e `src-tauri/capabilities/` não foram abertos.
7. **Funcionalidades adjacentes deixadas fora de propósito** por serem de
   outro domínio, embora toquem arquivos: geração de sugestões
   (`classification/`), thumbnails e previews (`thumbnails/`), cálculo de
   phash (`duplicates/phash.py`), geocodificação (`geolocation/`) e o
   assistente GenAI de pasta em si (só o **gate** de privacidade entrou, em
   F-A26). `security/http_seguro.py` (445 linhas) não virou bloco por não ter
   nenhum consumidor em produção.
8. **Números "medidos no acervo real"** reproduzidos como o código os
   declara (45.822 miniaturas, 54.086 fotos no `.lrcat`, 1.399 arquivos
   testados, 5.191 de 100.164 alcançáveis etc.); não foram remedidos contra o
   catálogo atual.


---

# Parte B — Imagem e inferência (F-I)

# 02 — Funcionalidades do domínio IMAGEM / INFERÊNCIA

Um bloco por funcionalidade, template fixo de 10 campos (`n/a` quando não se
aplica). Base: commit `524903d` (main). Detalhes de limiar, precedência e
payload estão em `docs/reconstrucao/04-PIPELINES.imagem.md`; aqui está o
recorte por funcionalidade, com gatilho, estado e prova.

Índice:

| id | nome | estado |
|---|---|---|
| F-I01 | Extração de metadados (contrato e escolha do extrator) | pronto |
| F-I02 | Leitura de RAW e CR3 via libraw | pronto |
| F-I03 | Sidecar XMP e curadoria humana unificada | pronto |
| F-I04 | Instante absoluto a partir do offset declarado | parcial |
| F-I05 | Miniatura e cache por conteúdo | pronto |
| F-I06 | Preview grande para o loupe | pronto |
| F-I07 | Detecção de tipo de imagem | pronto |
| F-I08 | Confirmação de tipo pelo usuário | pronto |
| F-I09 | Evidência de data | pronto |
| F-I10 | Evidência de ano pelo nome da pasta | pronto |
| F-I11 | Evidência de lugar (país/região/cidade) | pronto |
| F-I12 | Herança de GPS entre fontes | pronto |
| F-I13 | Correção de deriva de relógio | pronto |
| F-I14 | Concordância de duas âncoras | pronto |
| F-I15 | Lugar estimado e raio de incerteza | pronto |
| F-I16 | Sessões temporais | pronto |
| F-I17 | Transição casa↔fora | pronto |
| F-I18 | Cascata de classificação de sessão | pronto |
| F-I19 | Nomeação por álbum de catálogo externo | pronto |
| F-I20 | Viagem multi-país (pernas) | pronto |
| F-I21 | Subdivisão em acontecimentos | pronto |
| F-I22 | Evidência de categoria | pronto |
| F-I23 | Montagem do destino e confiança final | pronto |
| F-I24 | Preservação de decisão na regeneração | parcial |
| F-I25 | Descarte de sugestões órfãs | pronto |
| F-I26 | Geocodificação reversa offline e cache | pronto |
| F-I27 | Fuso estimado por país | pronto |
| F-I28 | Duplicatas visuais (phash + BK-tree) | parcial |
| F-I29 | Rajadas (SEQUENCIA) | pronto |
| F-I30 | Variante de revelação (RAW + JPEG) | pronto |
| F-I31 | Advisor de cluster por GenAI | pronto |
| F-I32 | Classificação de pasta por GenAI | pronto |
| F-I33 | Léxico de nomes por GenAI | pronto |
| F-I34 | Cobertura de metadados (medição) | pronto |
| F-I35 | Inventário de sinais (medição) | pronto |
| F-I36 | Reconhecimento facial | stub |
| F-I37 | Análise visual (visão) | stub |

---

### F-I01 — Extração de metadados
- **Propósito:** ler de cada arquivo tudo que ele diz sobre si — data, câmera, lente, orientação, dimensões, GPS e a base bruta de tags — sem nunca derrubar a varredura por causa de um arquivo ruim.
- **Gatilho:** job `scan` (`POST /api/scan`, `server/jobs.py:170-176`) e CLI `fotoorganizer scan` (`cli.py:197-206`); chamado por arquivo em `CatalogScanner._extrair`.
- **Entradas:** `Path` do arquivo. Nenhum estado, nenhum banco.
- **Regras de negócio:**
  1. `Protocol MetadataExtractor` com `supported_extensions()` e `extract(path)`; **nunca levanta exceção** — devolve `MediaMetadata(erro=...)`.
  2. Precedência do extrator: exiftool quando `shutil.which("exiftool")` responde, senão puro-Python. A escolha mora em `criar_extrator`, num lugar só.
  3. `data_capturada` é **hora de parede local**, naive, sem fuso — é ela que ordena a grade e agrupa evento e viagem.
  4. Data impossível (`> agora + 1 dia`, `_FOLGA_DE_RELOGIO`) não entra na coluna; o valor bruto vai para `extras` como `("exif","data_invalida",…)`. **Não há piso** — filme digitalizado pode ser de 1950.
  5. Precedência de data no exiftool: `Composite:SubSecDateTimeOriginal → EXIF:DateTimeOriginal → Composite:SubSecCreateDate → EXIF:CreateDate → QuickTime:CreateDate → XMP:DateCreated → IPTC:DateCreated → EXIF:ModifyDate`. `Composite:GPSDateTime` fica **fora** (é UTC, e a coluna é parede).
  6. No puro-Python, `DateTimeOriginal` mora na **sub-IFD Exif** (`get_ifd`), com `DateTime` da IFD0 como fallback; sem EXIF, a data vem de IPTC/XMP (`datecreated`, `datetimeoriginal`, `createdate` — nunca `ModifyDate`).
  7. GPS: exiftool usa `Composite:GPSLatitude/Longitude` (já com hemisfério); puro-Python converte DMS→decimal com `_dms_to_decimal`.
  8. Orientação: exiftool traduz as 8 strings por extenso para 1..8; libraw traduz o vocabulário dcraw por `_FLIP_PARA_ORIENTACAO = {0:1, 3:3, 5:8, 6:6}`, com `flip == -1` → `None`.
  9. Base bruta filtrada: `_TAGS_OPACAS` fora, valor > 500 caracteres fora (puro-Python) ou truncado em 2000 (exiftool), `bytes` fora, `MakerNotes` fora (D-027).
  10. `supported_extensions()` do exiftool **delega ao fallback** — o exiftool entende mais formatos do que o app trata.
- **Saídas:** `MediaMetadata` (dataclass), gravada em `media_files` e `metadata_entries` por `CatalogScanner._gravar`.
- **Degradação/falha:** arquivo corrompido → `erro` preenchido, linha criada mesmo assim; exiftool travado → morto em 30 s, fallback puro-Python daquele arquivo; exiftool morto ou JSON inválido → fallback; caminho com `\n`/`\r` → fallback antes de tentar.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_metadata.py::test_jpeg_com_exif_completo`, `::test_arquivo_corrompido_registra_erro`, `::test_data_exif_invalida_nao_quebra`, `::test_extras_trazem_as_tags_do_arquivo`, `::test_valor_ilegivel_ou_gigante_fica_de_fora`, `::test_video_entra_no_catalogo_em_vez_de_ser_invisivel`; `tests/test_exiftool_extractor.py::test_data_aceita_subsegundo_e_fuso`, `::test_gps_datetime_nao_entra_como_hora_de_parede`, `::test_coordenada_vem_do_composite_com_sinal`, `::test_orientacao_por_extenso_vira_numero`, `::test_exiftool_travado_cai_no_fallback_dentro_do_teto`, `::test_quebra_de_linha_no_nome_vai_para_o_fallback`, `::test_binario_ausente_cai_no_fallback`, `::test_criar_extrator_prefere_exiftool_quando_existe`, `::test_makernotes_fica_fora_da_base_bruta`, `::test_data_impossivel_nao_entra_na_coluna`, `::test_extensoes_sao_as_que_o_app_trata`.
- **Decisões:** D-020 (exiftool não entrava), D-021 (precedência XMP→IPTC→EXIF), D-026 (exiftool vira padrão quando instalado), D-027 (MakerNotes fora), D-038 (dois instantes, sem coluna de offset).
- **Arquivos:** `fotoorganizer/metadata/base.py:17-106`, `fotoorganizer/metadata/__init__.py:20-35`, `fotoorganizer/metadata/purepython.py:43-398`, `fotoorganizer/metadata/exiftool.py:43-521`, `fotoorganizer/metadata/camera.py:23-38`, `fotoorganizer/scanner/scanner.py:404-521`.

---

### F-I02 — Leitura de RAW e CR3 via libraw
- **Propósito:** dar data, lente, orientação e parâmetros de disparo a arquivos RAW — inclusive CR3, onde nenhuma outra biblioteca do stack entra.
- **Gatilho:** job `scan`, ramo `_extract_raw` quando a extensão está em `RAW_EXTENSIONS`.
- **Entradas:** `Path` de `.dng .cr2 .cr3 .nef .arw .raf .orf .rw2`.
- **Regras de negócio:**
  1. A data vem de `raw.other.timestamp` (libraw), que entende todas as variantes, **inclusive CR3 (ISO-BMFF)**, onde o `exifread` falha em silêncio.
  2. `raw.lens.model` → `lente`; `raw.sizes.flip` → `orientacao` via `_FLIP_PARA_ORIENTACAO`; `raw.sizes.width/height` → dimensões.
  3. Base bruta `libraw`: iso, abertura, obturador, distância focal, artista, ordem de disparo, focal mín/máx, flip.
  4. **`.cr3` retorna cedo**, sem tentar `exifread`: economiza uma segunda leitura de ~25 MB por foto. O preço é `make`/`model` em branco no CR3 — o libraw não expõe o fabricante, e deduzir "Canon" do prefixo `EF` da lente seria adivinhação disfarçada de evidência.
  5. Demais RAW: `exifread.process_file(details=False)` best-effort para make/model/GPS, todo o bloco sob `except Exception: pass`.
  6. O logger `exifread` é rebaixado a `ERROR` no import — ele avisa "File format not recognized" para cada CR3, e num scan grande isso inunda o log.
- **Saídas:** `MediaMetadata` com `data_capturada`, `lente`, `orientacao`, `largura`, `altura`, `extras` namespace `libraw`, e `make`/`model`/GPS quando não for CR3.
- **Degradação/falha:** sem `rawpy`/`exifread` (`_HAS_RAW = False`), `RAW_EXTENSIONS` sai de `supported_extensions()` e os arquivos ficam invisíveis ao scanner; se `_extract_raw` for chamado assim mesmo, devolve `erro = "suporte RAW indisponível (rawpy/exifread não instalados)"`. Exceção de leitura → `erro` preenchido.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_metadata.py::test_raw_ganha_lente_e_orientacao_do_libraw`, `::test_flip_do_libraw_vira_orientacao_exif`, `::test_raw_sem_lente_ou_rotacao_conhecida_nao_inventa`, `::test_extensoes_suportadas_incluem_raw_e_heif`.
- **Decisões:** n/a (medição registrada em `docs/COBERTURA_METADADOS.md`: 195 de 300 arquivos sem lente e sem orientação eram todos RAW; make/model no CR3 deixado em branco de propósito).
- **Arquivos:** `fotoorganizer/metadata/purepython.py:34-41,45,58,342-398`.

---

### F-I03 — Sidecar XMP e curadoria humana unificada
- **Propósito:** ler a curadoria que uma pessoa escreveu sobre a foto — palavra-chave, nota, rótulo — venha de dentro do arquivo ou do `.xmp` ao lado, e entregá-la como **um** conjunto, sem contar a mesma afirmação duas vezes.
- **Gatilho:** job `scan`, dentro de `ExifToolExtractor.extract` (sidecar) e `PurePythonExtractor._extract_pillow` (XMP/IPTC embutidos).
- **Entradas:** `Path` do arquivo; o `.xmp` irmão é procurado no filesystem.
- **Regras de negócio:**
  1. Sidecar: procura `foto.jpg.xmp` (Adobe) e depois `foto.xmp` (darktable/Lightroom). **O primeiro que existir vence** — fundir os dois arriscaria juntar curadoria de dois editores.
  2. Fusão: o sidecar vence onde os dois falam (é mais novo por construção). **Exceção crítica:** se o sidecar declara qualquer data (`XMP:DateTimeOriginal`, `XMP:DateCreated`, `XMP:CreateDate`), **todas** as tags de data do original saem junto — inclusive o offset de fuso. Casar a data do editor com o fuso da câmera produziria um instante que nunca existiu.
  3. Tags do sidecar entram na base bruta com grupo `XMPSidecar` → namespace `xmp_sidecar`, separado de `xmp`, para a pergunta "de onde veio?" continuar tendo resposta.
  4. Palavras-chave dos quatro formatos, nesta precedência: `XMPSidecar:TagsList`, `XMP:TagsList`, `XMPSidecar:HierarchicalSubject`, `XMP:HierarchicalSubject`, `XMPSidecar:Subject`, `XMP:Subject`, `IPTC:Keywords`. Os dois primeiros pares carregam hierarquia; os últimos são lista plana.
  5. Cada nível da hierarquia entra **separado além** do caminho inteiro: `"Viagens|2019|Patagônia"` também vale como `"Patagônia"`.
  6. Deduplicação preservando ordem — contar duas vezes a mesma afirmação de uma pessoa só é soma indevida de confiança (`docs/CONFIANCA.md`).
  7. O resultado é gravado no namespace unificado `NAMESPACE_CURADORIA = "curadoria"`, chave `palavra_chave`, **inclusive para mídia rebaixada a testemunha** — é a única exceção à regra de não gravar base bruta de não-acervo.
  8. No puro-Python, XMP e IPTC são coletados **antes** do short-circuit do EXIF: arquivo editado no Lightroom pode ter palavras-chave sem trazer EXIF nenhum.
- **Saídas:** `MediaMetadata.palavras_chave` (tupla) e linhas em `metadata_entries` nos namespaces `xmp`, `xmp_sidecar`, `iptc`, `curadoria`.
- **Degradação/falha:** sem `defusedxml`, `_HAS_XMP = False` e `_coletar_xmp` retorna em silêncio (um log no import, nunca um por arquivo); sidecar ilegível → `warning` e o original segue; `getiptcinfo` que levanta → ignorado.
- **Estado:** pronto para a leitura. **Parcial no consumo:** `_carregar_curadoria` só alimenta `_categoria` (regra 2b); usar essas palavras para inferir LUGAR "fica para quando esse uso existir de fato" (`engine.py:120-125`). Nota, rótulo de cor e `crs:` de revelação são capturados e não consumidos.
- **Testes que provam:** `tests/test_exiftool_extractor.py::test_sidecar_e_encontrado_nos_dois_padroes`, `::test_sidecar_vence_o_arquivo_e_leva_a_data_junto`, `::test_sidecar_sem_data_nao_apaga_a_do_arquivo`, `::test_palavras_chave_dos_quatro_formatos_sem_repetir`, `::test_hierarquia_entra_inteira_e_por_nivel`, `::test_sem_palavra_chave_o_campo_fica_vazio`; `tests/test_metadata.py::test_xmp_traz_autor_e_palavras_chave`, `::test_iptc_traz_autor_direitos_e_palavras_chave`, `::test_arquivo_sem_iptc_nao_inventa_namespace`, `::test_sem_exif_a_data_vem_dos_extras_iptc_ou_xmp`, `::test_data_dos_extras_chega_a_data_capturada_num_jpeg_com_xmp`; `tests/test_suggestion_engine.py::test_palavra_chave_curadoria_decide_categoria_sem_pasta`.
- **Decisões:** D-019 (`defusedxml` declarado, não instalado), D-021 (precedência XMP→IPTC→EXIF), D-023 (colunas tipadas de direitos e autoria ficam para depois da medição), D-057 (palavra-chave vira evidência de categoria).
- **Arquivos:** `fotoorganizer/metadata/exiftool.py:148-269`, `fotoorganizer/metadata/purepython.py:101-198,213-234`, `fotoorganizer/metadata/base.py:38-52`, `fotoorganizer/scanner/scanner.py:485-509`, `fotoorganizer/classification/engine.py:116-134`.

---

### F-I04 — Instante absoluto a partir do offset declarado
- **Propósito:** quando o arquivo **declara** o fuso da captura, guardar também o instante absoluto — sem inventar fuso para quem não o declara.
- **Gatilho:** job `scan`, dentro de `ExifToolExtractor._converter`.
- **Entradas:** `EXIF:OffsetTimeOriginal` → `EXIF:OffsetTimeDigitized` → `EXIF:OffsetTime`.
- **Regras de negócio:**
  1. Regex `([+-])(\d{2}):?(\d{2})`; recusa `horas > 14` ou `minutos > 59`.
  2. `data_capturada_utc = data_capturada - offset` — o offset diz quanto o relógio local está **à frente** de UTC (14h em +02:00 são 12h UTC).
  3. `"+00:00"` é aceito como fato: a foto foi tirada em Greenwich (ou Lisboa no inverno).
  4. Sem offset, o extrator **não inventa** — `data_capturada_utc` fica `None`, e o scanner grava `data_capturada_utc = data_capturada_utc or data_capturada`. **A igualdade é como se diz "não sei o fuso"**, nunca "foi tirada em UTC".
  5. **Não existe coluna de offset**: ele é a diferença entre as duas datas. Uma terceira coluna criaria um terceiro lugar para a mesma verdade, livre para discordar em silêncio.
  6. Sem hora de parede não há instante absoluto, mesmo que o extrator mande um (`scanner.py:462-466`).
- **Saídas:** `MediaFile.data_capturada_utc`.
- **Degradação/falha:** offset inválido → ignorado, `data_capturada_utc` fica igual à parede. Nenhuma exceção.
- **Estado:** **parcial.** O `PurePythonExtractor` **não lê offset nenhum** — só o exiftool preenche (`metadata/base.py:58-67` diz que ler o fuso no puro-Python "exige `_data()` devolver o PAR em vez de só a hora local, o que muda todos os campos de data dos dois extratores de uma vez. Fica para a fase 11"). E fuso real `+00:00` fica indistinguível de desconhecido — limitação inerente ao padrão, declarada e aceita.
- **Testes que provam:** `tests/test_exiftool_extractor.py::test_offset_declarado_vira_instante_absoluto`, `::test_offset_negativo_e_sem_dois_pontos`, `::test_sem_offset_o_extrator_nao_inventa_instante`, `::test_offset_invalido_e_ignorado`.
- **Decisões:** D-038.
- **Arquivos:** `fotoorganizer/metadata/exiftool.py:117-146,458-468`, `fotoorganizer/metadata/base.py:56-67`, `fotoorganizer/models/catalog.py:196-231`, `fotoorganizer/scanner/scanner.py:455-466`.

---

### F-I05 — Miniatura e cache por conteúdo
- **Propósito:** ter uma imagem pequena pronta para a grade, o phash e a capa de card, sem nunca carregar resolução completa e sem reprocessar o que já foi feito.
- **Gatilho:** job `scan` (`CatalogScanner._extrair`, na mesma leitura do arquivo) e rota `GET /api/midia/{media_id}/thumb`.
- **Entradas:** `hash_rapido` (chave) + caminho do original.
- **Regras de negócio:**
  1. **Chave é o conteúdo, não o caminho**: duas cópias do mesmo arquivo compartilham a miniatura; arquivo alterado ganha chave nova e o cache se invalida sozinho.
  2. Caminho: `<cache_dir>/thumbs/<2 primeiros chars da chave>/<chave>.jpg`, com `:` trocado por `_` (o prefixo `xxh3:` não pode virar diretório).
  3. `THUMB_SIZE = 320` (lado maior, caixa 320×320), `_JPEG_QUALITY = 82`.
  4. **`ImageOps.exif_transpose` é aplicado** — a orientação EXIF entra na miniatura.
  5. RAW abre pela **miniatura JPEG embutida** via `rawpy.extract_thumb()`; nunca revela o RAW.
  6. Escrita atômica: `.tmp` com sufixo `"{pid}-{thread_id}"` e `replace()` — duas cópias idênticas geradas em paralelo têm a mesma chave e não podem disputar o mesmo `.tmp`.
  7. Gerada durante o scan "aproveitando que o arquivo já está sendo lido" — em RAW, ~0,4 s a menos por arquivo depois.
  8. **Não gera para arquivo dentro de pacote** (`.photoslibrary`, `.imageset`): ele nunca aparece na grade, e a miniatura era quase só custo — 2 GB de cache e RAW inteiro lido pelo SMB no acervo real. O phash ainda a alcança sob demanda, lendo o original.
  9. Resposta HTTP com `Cache-Control: max-age=31536000`.
  10. Modo de cor diferente de `RGB`/`L` é convertido para `RGB` antes de salvar.
- **Saídas:** arquivo JPEG no cache; `FileResponse` na rota; `True`/`False` da função.
- **Degradação/falha:** imagem indecodificável → `log.debug` + `False`/`None`, **nunca exceção**; a UI mostra placeholder e a rota devolve 404 "imagem indecodificável". Mídia sem `hash_rapido` → 404 "sem miniatura". Disco desligado tira a miniatura, **não** a coordenada — no mapa a foto continua desenhada com `motivo_indisponivel`.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_thumbnails.py::test_gera_miniatura_reduzida`, `::test_orientacao_exif_aplicada`, `::test_corrompida_retorna_false_sem_excecao`, `::test_cache_gera_uma_vez`, `::test_cache_chave_sanitizada_e_metricas`.
- **Decisões:** D-024 (testemunha é rebaixada, nunca apagada — e por isso não ganha miniatura), D-035 (as 45.822 miniaturas do Apple Fotos saíram do catálogo).
- **Arquivos:** `fotoorganizer/thumbnails/generator.py:25-69`, `fotoorganizer/thumbnails/cache.py:22-46`, `fotoorganizer/scanner/scanner.py:404-419`, `fotoorganizer/server/app.py:490,842-851`.

---

### F-I06 — Preview grande para o loupe
- **Propósito:** dar ao loupe um JPEG grande sem abrir o original em resolução completa a cada visualização.
- **Gatilho:** rota `GET /api/midia/{media_id}/preview`.
- **Entradas:** `media_id`; a chave é o mesmo `hash_rapido`.
- **Regras de negócio:**
  1. Diretório **separado** do de miniaturas: `<cache_dir>/previews/<2 chars>/<chave>.jpg`.
  2. `_PREVIEW_SIZE = 2048`; mesma função `generate_thumbnail`, só o `size` muda.
  3. RAW usa a prévia embutida do arquivo (mesmo `_open_source`).
  4. Geração **sob demanda**, nunca durante o scan.
  5. `Cache-Control: max-age=31536000`.
- **Saídas:** `FileResponse` image/jpeg.
- **Degradação/falha:** sem `hash_rapido` → 404 "sem preview"; indecodificável → 404 "imagem indecodificável".
- **Estado:** pronto.
- **Testes que provam:** n/a — nenhum teste cobre a rota `/preview` nem o diretório `previews` (`tests/test_thumbnails.py` cobre só `THUMB_SIZE`).
- **Decisões:** n/a.
- **Arquivos:** `fotoorganizer/server/app.py:240,491,853-867`, `fotoorganizer/thumbnails/generator.py:43-69`.

---

### F-I07 — Detecção de tipo de imagem
- **Propósito:** separar foto de câmera do que só passou pelo disco — captura de tela, imagem recebida em mensageiro, arquivo baixado — para que isso não entope a grade nem seja organizado por viagem.
- **Gatilho:** job `sugestoes` (`POST /api/sugestoes/gerar`), dentro de `_evidencias_para`, para toda mídia organizável ainda não decidida.
- **Entradas:** `nome`, `pasta`, `extensao`, `largura`, `altura`, `make`, `model`, `lente`, `exposicao`, `tem_gps`.
- **Regras de negócio (ordem importa — sinal forte antes de fraco):**
  1. **`tem_gps` usa `media.gps_lat` (LIDO do arquivo), nunca a coordenada efetiva** — a herdada é justamente o que uma captura de tela ganha das fotos vizinhas.
  2. GPS gravado → `foto`, 0.95. Vence qualquer heurística de nome: é o caso da foto que você tirou e mandou para si mesmo.
  3. Nome WhatsApp (`^(IMG|VID|AUD|PTT)-\d{8}-WA\d+` ou `^WhatsApp (Image|Video)\b`) → `recebida` 0.95; Telegram (`^photo_\d{4}-\d{2}-\d{2}_`) → `recebida` 0.90; captura (`^(captura de (tela|ecrã|ecra)|screenshot|screen shot|simulator screen shot)`) → `captura` 0.95.
  4. Pasta de mensageiro (`whatsapp|telegram|signal|messenger`) → `recebida` 0.85; pasta de capturas (`screenshots|capturas de tela|capturas`) → `captura` 0.85.
  5. Resolução **exatamente** igual a uma de `_TELAS` (24 pares + transpostos) **e** sem assinatura de câmera → `captura` 0.85.
  6. Sem câmera e pasta `downloads|transferências|transferencias` → `baixada` 0.80; nome genérico (`image|imagem|unnamed|download|untitled|sem título` + `(N)` opcional) → `baixada` 0.70.
  7. PNG sem câmera → `captura` 0.55 (sinal fraco sozinho, não passa de média).
  8. Sem câmera e `largura*altura < _MP_MINIMO = 480_000` (≈ 800×600) → `recebida` 0.55. Piso deliberadamente baixo: uma compacta de 1999 tirava 0,78 MP.
  9. Sem câmera, nada indica o contrário → `foto` 0.50. Com câmera → `foto` 0.90.
  10. Normalização de pasta por NFKD+ascii+lower, não `lower()` — o Finder/APFS grava pasta acentuada em NFD (D-066).
  11. `media.tipo_imagem` é **reescrito a cada geração** (um arquivo reprocessado pode ganhar EXIF); `tipo_confirmado` **nunca** é tocado pelo motor.
  12. Draft de evidência só nasce quando o veredito **não** é `foto`: origem `arquivo` com `score_override = veredito.score` e justificativa `"<motivo> — a confirmar"`.
  13. Regra de ouro: **na dúvida, é foto** — marcar foto legítima como lixo custa a confiança no catálogo inteiro.
- **Saídas:** `MediaFile.tipo_imagem`; `_Draft("tipo", ...)`; destino no ramo `"Não são fotos/<Rótulo>/<ano>"`.
- **Degradação/falha:** sem dimensões, sem câmera e sem nome reconhecível, cai na regra 9 (`foto`, 0.50) — nunca condena por ausência de sinal.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_tipo_imagem.py::TestReconhece::test_whatsapp_pelo_nome`, `::TestReconhece::test_whatsapp_do_desktop`, `::TestReconhece::test_telegram`, `::TestReconhece::test_captura_pelo_nome`, `::TestReconhece::test_pasta_de_mensageiro`, `::TestReconhece::test_resolucao_exata_de_tela_sem_camera`, `::TestReconhece::test_download_por_pasta`, `::TestReconhece::test_pasta_transferencias_bate_em_nfc_e_nfd`, `::TestReconhece::test_pasta_captura_de_tela_bate_em_nfc_e_nfd`, `::TestReconhece::test_png_sem_camera_e_captura_com_confianca_media`, `::TestReconhece::test_resolucao_muito_baixa_sem_camera_parece_recomprimida`, `::TestNaoCondena::test_gps_vence_nome_de_whatsapp`, `::TestNaoCondena::test_resolucao_de_tela_com_camera_nao_e_captura`, `::TestNaoCondena::test_foto_de_camera_antiga_sem_exif_continua_foto`, `::TestNaoCondena::test_sem_nada_nao_condena`, `::test_justificativa_sempre_existe_e_e_legivel`; `tests/test_suggestion_engine.py::test_captura_de_tela_sai_do_fluxo_de_viagem`.
- **Decisões:** D-053 (categoria travada em 3 valores; expansão é eixo novo — tipo de mídia), D-054 (hipótese refutada: sessões neutras não são screenshots disfarçados), D-066 (NFD no detector).
- **Arquivos:** `fotoorganizer/classification/tipo_imagem.py:32-199`, `fotoorganizer/grouping/origens.py:14-16`, `fotoorganizer/classification/engine.py:793-819,1084-1096,1231-1239`.

---

### F-I08 — Confirmação de tipo pelo usuário
- **Propósito:** deixar a palavra final sobre o que a imagem é com quem sabe — e garantir que nenhuma regeneração a sobrescreva.
- **Gatilho:** rota `POST /api/midia/{media_id}/tipo`.
- **Entradas:** `{"tipo": "foto" | "captura" | "recebida" | "baixada" | null}`.
- **Regras de negócio:**
  1. Tipo fora de `TIPOS_VALIDOS` → HTTP 422.
  2. Grava `tipo_confirmado` e `tipo_confirmado_em`; `tipo: null` devolve a decisão ao detector e zera o carimbo de tempo.
  3. `tipo_efetivo = tipo_confirmado or tipo_imagem` — é o que decide o destino.
  4. `tipo_provisorio = (tipo_confirmado is None and tipo_imagem is not None)` — é o que permite a interface **perguntar em vez de afirmar**.
  5. Na cascata, tipo confirmado vira evidência de origem `usuario` com `score_override = 1.0` e justificativa `"classificado por você"`.
- **Saídas:** `{"tipo_imagem": <efetivo>, "tipo_provisorio": <bool>}`.
- **Degradação/falha:** mídia inexistente → 404.
- **Estado:** pronto.
- **Testes que provam:** n/a no nível da rota; o efeito na cascata é coberto indiretamente por `tests/test_suggestion_engine.py::test_captura_de_tela_sai_do_fluxo_de_viagem`.
- **Decisões:** n/a.
- **Arquivos:** `fotoorganizer/server/app.py:815-839`, `fotoorganizer/models/catalog.py:257-313`, `fotoorganizer/classification/engine.py:806-819`.

---

### F-I09 — Evidência de data
- **Propósito:** responder "quando esta foto foi tirada?" com a melhor testemunha disponível, dizendo qual é e o quanto ela vale.
- **Gatilho:** job `sugestoes`, dentro de `_evidencias_para`.
- **Entradas:** `media.data_capturada`, `media.nome`, `media.mtime`.
- **Regras de negócio:**
  1. **Exatamente uma evidência de data por foto** — é ela que vira o `{ano}` do destino, e duas testemunhas do mesmo campo disputariam a vaga.
  2. Precedência: `data_capturada` (origem `exif`, 0.95) → data no nome do arquivo (`nome_arquivo`, 0.65) → `mtime` (`fs`, 0.40).
  3. O nome só é consultado quando `data_capturada is None`.
  4. Três convenções reconhecidas, nesta ordem: WhatsApp (`^(IMG|VID|AUD|PTT)-(\d{8})-WA`), ISO (`(?<!\d)(19|20)\d{2}-\d{2}-\d{2}(?!\d)`), compacto de câmera de celular (`(?<!\d)(19|20)\d{2}\d{2}\d{2}(?!\d)`). Os lookarounds isolam o número: um serial de 13 dígitos que contém "20240315" é serial, não data.
  5. Toda data do nome passa por `_data_valida` — mês/dia válidos e **não no futuro**, mesmo teto do EXIF.
  6. O nome vale mais que o mtime porque **nasce com o arquivo**; vale menos que o EXIF porque a data do WhatsApp é a do RECEBIMENTO, não a do clique.
  7. Justificativas literais: `"data de captura lida do EXIF (DateTimeOriginal)"`; `"sem EXIF; '<texto>' no nome do arquivo (<padrão>)"`; `"sem EXIF; data de modificação do arquivo (pouco confiável)"`.
- **Saídas:** uma linha em `evidence` com `campo = "data"`; `campos["ano"]` derivado dela.
- **Degradação/falha:** sem EXIF, sem nome reconhecível e sem mtime → **nenhuma** evidência de data; o destino vai para `"Não classificadas/sem data"`.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_datas_em_pastas.py::test_nome_whatsapp_carrega_a_data`, `::test_nome_de_video_whatsapp_tambem`, `::test_nome_compacto_de_camera_de_celular`, `::test_nome_iso_de_captura_e_mensageiro`, `::test_nome_sem_data_ou_com_data_impossivel_nao_inventa`, `::test_numero_de_serie_nao_vira_data`; `tests/test_suggestion_engine.py::test_data_no_nome_do_arquivo_vira_evidencia_media`, `::test_fotos_sem_data_de_captura_nao_viram_viagem`, `::test_nao_classificadas_quebram_por_ano_e_mes`.
- **Decisões:** D-043 (`versao_logica` é escrito e nunca lido — conserto pendente).
- **Arquivos:** `fotoorganizer/classification/engine.py:821-845`, `fotoorganizer/grouping/datas.py:209-270`, `fotoorganizer/classification/confidence.py:14,56-57`.
- **⚠️ Divergência M5:** a cascata de data prefere o nome ao mtime, mas a **linha do tempo** do agrupamento usa `data_capturada or mtime` e **ignora o nome** (`engine.py:469`). `IMG-20150420-WA0001.jpg` copiado em 2024 recebe ano 2015 e viagem de 2024.

---

### F-I10 — Evidência de ano pelo nome da pasta
- **Propósito:** ter uma segunda testemunha do ano, independente do EXIF — e tornar visível a divergência quando as duas discordam.
- **Gatilho:** job `sugestoes`, dentro de `_evidencias_para`, sempre que a pasta carrega data.
- **Entradas:** `media.pasta`, `media.data_capturada`.
- **Regras de negócio:**
  1. `data_no_caminho` procura da **folha para a raiz**: a pasta mais funda fala da foto, as de cima falam do arquivamento. Em empate de ano, vence a de maior precisão (mês + dia).
  2. Seis padrões, do mais específico ao mais genérico: `2025-05-24` · `24-05-2025` (**convenção brasileira** — dia primeiro) · `29 de outubro de 2016` · `Abril 2015`/`Jul.2023`/`Julho de 2023` · `2015-04` (não aceita espaço: "Rio 2016 04" é ano + número) · `2015`.
  3. `_ANO = (?:18|19|20)\d{2}` é a âncora que impede "15 Anos" de virar data e "Serena 15 Anos" de perder o nome.
  4. `_MESES` cobre PT e EN, com e sem acento, abreviado e por extenso; o alternador ordena por comprimento decrescente para "janeiro" casar antes de "jan".
  5. Normalização NFC **da string inteira, uma vez no início** — normalizar só na comparação dessincronizaria os índices de fatiamento (NFC e NFD têm comprimentos diferentes).
  6. `"novembro 30"` (mês + dia sem ano, segmento inteiro) **não vira data e também não é nome** — sem isso virava nome de álbum e podia ser promovido a evento falso pela regra 6.
  7. Justificativa: `"'<texto>' escrito no nome da pasta"` + `" — confere com o EXIF"` ou `" — DIVERGE do EXIF (<ano>)"`.
  8. **O EXIF continua mandando no destino**: o draft de `ano` é removido de `usados` antes do cálculo de confiança. Concordância **não** sobe score — `docs/CONFIANCA.md` proíbe soma.
- **Saídas:** linha em `evidence` com `campo = "ano"`, origem `pasta`, 0.60. No catálogo real: 32.484 linhas.
- **Degradação/falha:** pasta sem data reconhecível → nenhuma evidência de ano; nada muda.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_datas_em_pastas.py::test_separa_nome_e_data`, `::test_marco_em_nfd_bate_igual_a_nfc`, `::test_data_no_caminho_reconhece_marco_em_nfd`, `::test_mes_dia_sem_ano_esvazia_o_nome`, `::test_mes_dia_sem_ano_so_esvazia_o_segmento_inteiro`, `::test_mes_dia_sem_ano_valida_faixa_do_dia`, `::test_nomes_sem_data_ficam_intactos`, `::test_mes_invalido_nao_vira_data`, `::test_data_no_caminho_prefere_a_mais_especifica`; `tests/test_suggestion_engine.py::test_pasta_com_lugar_e_data_nomeia_o_evento_e_confirma_o_ano`, `::test_data_da_pasta_que_diverge_do_exif_e_denunciada`.
- **Decisões:** D-067 (mês acentuado em NFD), D-073 (mês por extenso sem reconhecimento — 303 fotos com destino `Eventos/2016/29 de`).
- **Arquivos:** `fotoorganizer/grouping/datas.py:35-206`, `fotoorganizer/classification/engine.py:826-844,1266-1274`.

---

### F-I11 — Evidência de lugar (país / região / cidade)
- **Propósito:** responder "onde esta foto foi tirada?" pela melhor fonte disponível, e **nunca inventar** quando não há fonte.
- **Gatilho:** job `sugestoes`, `_evidencias_geo`.
- **Entradas:** `media.gps_lat/lon`, a `Heranca` desta mídia, `media.pasta`, a proposta de GenAI aprovada para esta pasta, e o país dominante da sessão.
- **Regras de negócio (cada ramo que resolve faz `return` — não há acúmulo):**
  1. **GPS próprio + resolver** → até 3 drafts, origem `geocoding_offline` (0.85), justificativa `"geocodificação offline das coordenadas GPS do EXIF (<lat:.4f>, <lon:.4f>)"`. Grava `media.location_id`.
  2. **GPS herdado** → um draft por campo em que `heranca.fator_de(campo)` não é `None`; score `round(0.75 * fator, 3)`; justificativa monta-se em camadas (ver F-I12).
  3. **Nome da pasta** → `extrair_hierarquia_da_pasta`: no primeiro segmento que é país, o penúltimo resto é região e o último é cidade; sem resto, só país. Origem `pasta` (0.60), justificativa `"reconhecido no caminho da pasta ('<segmento>')"`.
  4. **Proposta de GenAI de pasta aprovada** (cidade/país) → origem `llm_pasta` (0.55). Fica **acima** da vizinhança porque a proposta é sobre ESTA pasta; vizinhança é inferência sobre o grupo inteiro.
  5. **Vizinhança de sessão** → um draft `("pais", "vizinhanca", 0.55)`, `"outras fotos da mesma sessão têm GPS em <país>"`.
  6. Nada acima → `return []`. **Não inventa localização** — o v1 chutava a pasta mais funda como cidade e isso foi removido.
  7. País é sempre canonizado para a grafia em português (`canonizar_pais`): uma pasta "France" e outra "França" dariam duas pastas para o mesmo país no destino.
  8. **Uma viagem é uma pasta**: quando o destino já tem `viagem` ou `evento`, país/região/cidade são zerados do caminho — mas continuam gravados como evidência e vinculados à sugestão por `_contexto_da_sugestao`.
- **Saídas:** linhas em `evidence` com `campo ∈ {pais, regiao, cidade}`; `media.location_id`. No catálogo real: 3.648 de cada campo por `geocoding_offline`, 10.507 `pais` por `vizinhanca_temporal`, 7.506 `pais` por `vizinhanca`.
- **Degradação/falha:** `resolver = None` (sem `reverse_geocode`) → ramos 1, 2 e a geocodificação de sessão desligam; a cascata cai para pasta e vizinhança. Provider mudo → `LocationResolver` devolve o que já sabia, não apaga.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_suggestion_engine.py::test_gps_gera_destino_com_alta_e_justificativas`, `::test_pasta_da_pais_com_media_confianca`, `::test_vizinhanca_infere_pais_de_fotos_proximas`, `::test_sem_evidencia_fica_baixa_e_nao_inventa`, `::test_uma_viagem_e_uma_pasta_so`, `::test_lugar_suprimido_do_caminho_continua_vinculado_a_sugestao`, `::test_location_id_resolvido_mesmo_para_sugestao_ja_decidida`; `tests/test_geolocation.py::test_hierarquia_da_pasta`, `::test_sem_pais_nao_inventa`, `::test_identificar_pais_normaliza_acentos_e_caixa`; `tests/test_paises.py::test_apelidos_convergem_para_uma_grafia`, `::test_nome_de_pasta_usa_a_mesma_grafia_do_geocoder`; `tests/test_cascata_llm_pasta.py::test_determinismo_vence_o_llm`.
- **Decisões:** D-025 (janela por campo), D-051/D-052/D-058 (geo-first), D-081 (score de `llm_pasta`).
- **Arquivos:** `fotoorganizer/classification/engine.py:902-1025,1126-1143,1218-1229`, `fotoorganizer/geolocation/folder_names.py:51-81`, `fotoorganizer/geolocation/paises.py:151-233`.

---

### F-I12 — Herança de GPS entre fontes
- **Propósito:** dar lugar a foto sem GPS, emprestando a coordenada da foto **de outra origem** mais próxima no tempo — como evidência com origem, confiança por Δt e justificativa legível, **nunca** como escrita no arquivo.
- **Gatilho:** job `sugestoes`, `SuggestionEngine._correlacionar`, antes de tudo.
- **Entradas:** `FotoRef` de **todas** as mídias com `data_capturada or mtime` — inclusive as referências sem arquivo local e as testemunhas rebaixadas, que são quem traz GPS de celular numa biblioteca em iCloud.
- **Regras de negócio:**
  1. Doadora precisa ser de **outra origem**: `source_id` diferente **ou** câmera `(make, model)` diferente. Duas fotos da mesma câmera na mesma fonte já vivem na mesma linha do tempo.
  2. **Uma janela por campo** (D-025): cidade ≤ 10 min, região ≤ 2 h, país ≤ 12 h. A busca usa a maior (`JANELA_HERANCA = 12 h`); cada campo é filtrado depois.
  3. Fator por campo: `1.0` até `_JANELA_CURTA = 2 min`, decaindo linearmente até `0.6` na borda da **própria** janela — "país a 6 h" e "cidade a 6 min" não competem na mesma escala.
  4. Hora vinda do mtime em qualquer dos dois lados (`hora_incerta`) multiplica o fator por `_PENALIDADE_HORA_DE_ARQUIVO = 0.6` — escolhido para derrubar a herança de "alta" para "média" mesmo com Δt curto.
  5. A busca **caminha** para cada lado até estourar a janela, não olha só os vizinhos imediatos: a versão anterior barrou **27.117 candidatos** que tinham doador válido logo atrás.
  6. O lado mais próximo vence; o outro vira testemunha (ver F-I14).
  7. Score final da evidência: `round(SCORES_REFERENCIA["vizinhanca_temporal"] * fator, 3)`, com `vizinhanca_temporal = 0.75`.
  8. A justificativa monta-se em camadas: base `"GPS herdado de '<nome>' (<câmera>) — tirada a <Δt> de distância"`; + `"; a essa distância dá para afirmar <o país|a região>, não a cidade"` quando a granularidade não alcança cidade; + `"; a hora de uma delas é a do arquivo, não a da captura — a proximidade pode ser coincidência"` quando incerta; + `"; confirmada por outra foto do lado oposto no tempo, na mesma área plausível"` só no campo concordante.
  9. `gps_lat_estimado`, `gps_lon_estimado`, `gps_estimado_de_id` e `gps_estimado_delta_s` são **reescritos a cada rodada** e **limpos** quando não há doador ou quando a foto ganhou coordenada própria.
  10. Coordenada herdada **não** entra na detecção de casa — repetiria a do doador e inflaria a célula modal.
- **Saídas:** `dict[media_id, Heranca]`; as quatro colunas `gps_*_estimado`; evidências `vizinhanca_temporal`. No catálogo real: **13.375 mídias com GPS estimado** (contra 21.753 com GPS próprio).
- **Degradação/falha:** nenhuma doadora na janela → sem herança, sem erro. `campos_confiaveis` vazio → herança não é criada.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_correlacao.py::test_heranca_do_doador_mais_proximo`, `::test_fora_da_janela_da_cidade_ainda_herda_o_pais`, `::test_longe_demais_para_qualquer_campo`, `::test_confianca_decai_com_delta`, `::test_mesma_camera_na_mesma_fonte_nao_doa`, `::test_doadora_de_outra_fonte_mesmo_sem_camera`, `::test_procura_alem_dos_dois_vizinhos_imediatos`, `::test_a_busca_para_na_borda_da_janela`, `::test_o_mais_proximo_vence_mesmo_vindo_do_outro_lado`, `::test_hora_vinda_do_arquivo_vale_menos`; `tests/test_suggestion_engine.py::test_gps_herdado_de_outra_fonte_gera_evidencia_e_destino`, `::test_gps_herdado_dentro_de_viagem_chega_a_sugestao`, `::test_coordenada_herdada_e_persistida_com_doador_e_delta`, `::test_estimativa_some_quando_a_foto_ganha_gps_proprio`.
- **Decisões:** D-024 (testemunha continua doando), D-025 (janela por campo), D-029 (GPS de receptor × de celular pareado), D-074 (concordância).
- **Arquivos:** `fotoorganizer/grouping/correlacao.py:38-57,88-165,222-344,414-436`, `fotoorganizer/classification/engine.py:287-288,350-372,465-494,928-983`.

---

### F-I13 — Correção de deriva de relógio
- **Propósito:** corrigir a linha do tempo de câmeras com relógio errado (fuso não ajustado na viagem, minutos de atraso) antes de cruzar fontes — senão a herança de GPS aponta para a hora errada.
- **Gatilho:** job `sugestoes`, `estimar_offsets`, imediatamente antes de `herdar_gps`.
- **Entradas:** a mesma lista de `FotoRef`.
- **Regras de negócio:**
  1. **Par-âncora** = a mesma foto presente em duas fontes: `hash_rapido` igual, **ou** `hash_perceptual` igual quando o export foi recomprimido.
  2. Só conta par com `source_id` diferente e em que **exatamente uma** das duas tem GPS: a com GPS é a **referência de relógio** (Google/Apple normalizam a hora real); a outra é a câmera.
  3. Câmera `(None, None)` é descartada — não há a que atribuir o offset.
  4. Por câmera: exige `_MIN_ANCORAS = 2`; calcula **mediana** dos desvios e o **MAD** (mediana dos desvios absolutos); descarta se `MAD > _DISPERSAO_MAX = 3 min` — dispersão grande indica pareamento ruim.
  5. Offset aplicado como `quando + offset` na busca de doadora; câmeras sem âncoras suficientes ficam com offset implícito zero.
  6. Loga `"correlação: deriva de relógio estimada para %d câmeras"`.
- **Saídas:** `dict[(make, model), timedelta]`, consumido só por `herdar_gps`. **Nada é gravado no catálogo** — a correção existe apenas durante a geração.
- **Degradação/falha:** sem âncoras → dicionário vazio, herança roda com as horas cruas.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_correlacao.py::test_offset_estimado_pelas_ancoras`, `::test_offset_corrige_a_heranca`, `::test_ancoras_dispersas_sao_descartadas`, `::test_ancora_unica_nao_basta`; `tests/test_suggestion_engine.py::test_deriva_de_relogio_corrigida_pelas_ancoras`.
- **Decisões:** n/a (registrado em `docs/AGRUPAMENTO.md` §2a, lógica 4.1).
- **Arquivos:** `fotoorganizer/grouping/correlacao.py:51-52,167-220`, `fotoorganizer/classification/engine.py:486-491`.

---

### F-I14 — Concordância de duas âncoras
- **Propósito:** usar a doadora do lado perdedor como testemunha — a favor ou **contra** a mais próxima — em vez de descartá-la.
- **Gatilho:** job `sugestoes`, dentro de `herdar_gps`, quando existe doadora dos dois lados.
- **Entradas:** os dois achados (`(delta, doador)` de cada lado) e os `campos_base` já calculados.
- **Regras de negócio:**
  1. Testa **campo a campo**, e **nunca `pais`**: `raio_incerteza` é calibrado para deslocamento de pessoa em até 12 h (teto 50 km), não para o tamanho de um país — duas doadoras a 300 km, claramente no mesmo país, falhariam o teste.
  2. Hora de arquivo em **qualquer** dos três lados envolvidos desativa o teste: um raio calculado sobre Δt arbitrariamente errado não prova nada. Assim a justificativa nunca diz "confirmada" na mesma frase em que avisa que a hora é incerta.
  3. Se o Δt do lado distante **não cabe** na janela daquele campo, o campo segue como âncora única — sem teste, sem regressão.
  4. **Concordam** quando `distancia_haversine(doadorA, doadorB) <= raio_incerteza(Δt_perto) + raio_incerteza(Δt_longe)`.
  5. Concordar **não aumenta o fator** (seria bônus inventado) — só marca `concordancia` e adiciona uma frase à justificativa.
  6. **Discordam** → o campo **não é herdado por ninguém**, nem pelo lado mais próximo: duas doadoras a horas uma da outra, uma de cada lado, significa que a foto do meio está **em trânsito**.
  7. `doador_concordante_id` só é preenchido quando houve ao menos uma concordância.
  8. Limitação declarada, não escondida: ida e volta no mesmo dia entre duas âncoras concordantes (casa → cidade vizinha → casa, sem foto com GPS no meio) produz falso-negativo.
- **Saídas:** `Heranca.campos` filtrado, `Heranca.concordancia`, `Heranca.doador_concordante_id`. No catálogo real: **880 justificativas** com a frase de concordância.
- **Degradação/falha:** sem outro lado → `campos_base` inalterado, `concordancia = ()`.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_correlacao.py::test_duas_ancoras_concordantes_confirmam_sem_inflar_score`, `::test_duas_ancoras_discordantes_nao_herdam_a_granularidade_em_disputa`, `::test_lado_distante_demais_no_tempo_nao_opina_sobre_o_campo_mais_fino`, `::test_pais_nunca_ganha_bonus_de_concordancia`, `::test_ancora_unica_sem_concordancia_por_padrao`, `::test_hora_incerta_em_qualquer_lado_desativa_o_teste_de_concordancia`.
- **Decisões:** D-074.
- **Arquivos:** `fotoorganizer/grouping/correlacao.py:118-165,276-344,346-411`, `fotoorganizer/classification/engine.py:952-957`.

---

### F-I15 — Lugar estimado e raio de incerteza
- **Propósito:** desenhar no mapa o tamanho honesto da dúvida — um círculo, não um ponto — quando a coordenada é da doadora e não da foto.
- **Gatilho:** rota `GET /api/mapa?trip_id=N` ou `?event_id=N`.
- **Entradas:** as mídias do grupo, com `coordenada` (própria ou estimada), `gps_estimado_delta_s`, `gps_estimado_de_id`.
- **Regras de negócio:**
  1. `raio(Δt) = min(RAIO_TETO_M, max(RAIO_PISO_M, VELOCIDADE_PLAUSIVEL_MS × |Δt|))` com `6.0 m/s` (≈ 22 km/h), piso `15 m`, teto `50.000 m`.
  2. **Os três números foram calibrados** contra 2.083 pares reais em que as duas fotos têm GPS próprio e origens diferentes. Achado que derrubou a hipótese de partida: a distância real **satura** — o p90 da banda 6–12 h (25 km) é *menor* que o da banda 30 min–2 h (39 km). Um teto derivado da janela de país daria 259 km e não informaria nada.
  3. `COBERTURA_MEDIDA = 0.936` (ponderada pelas bandas de Δt do acervo); mora ao lado das constantes que a produziram porque a interface promete honestidade em cima dela.
  4. `estimado = False` → ponto cheio, `raio_m = None`.
  5. `estimado = True` **sem** `gps_estimado_delta_s` → `raio_m = RAIO_TETO_M`: "Δt ausente não é Δt zero" — a dúvida máxima é a resposta honesta para "não sei há quanto tempo".
  6. A frase nasce em Python (`frase_do_raio`), **não em TypeScript**, em três formas — no piso fala do receptor de GPS, no teto diz que o raio parou de crescer, no meio explica velocidade × tempo. Constante duplicada é constante que diverge.
  7. Os limites do enquadramento já vêm **esticados pelo raio de cada círculo**: num grupo em que todas herdaram da mesma doadora (o caso comum), a caixa dos pontos tem lado zero e os círculos, 50 km.
  8. `escala` traduz metros em graus na latitude média (`metros_por_grau`), para o círculo sair redondo e não elipse fora do equador.
  9. **Um grupo por vez**: sem cartografia real (D-031), o acervo inteiro numa tela só não tem escala em que informe nada.
  10. Foto fora de alcance **continua no mapa**, com `motivo_indisponivel` — o disco desligado leva a miniatura, não a coordenada. `no_mapa + sem_coordenada == total`; `fora_de_alcance` é subconjunto de `no_mapa`.
  11. A rota é de **leitura pura**: não recalcula herança, não escreve.
- **Saídas:** `{pontos: [...], limites, escala, contagens}` — cada ponto com `estimado`, `raio_m`, `delta_s`, `doadora_id`, `doadora_nome`, `porque`.
- **Degradação/falha:** grupo sem pontos → `{"limites": None, "escala": None}`. Doadora não encontrada no dict → `doadora_nome = None` e a frase usa "de outra foto".
- **Estado:** pronto.
- **Testes que provam:** `tests/test_correlacao.py::test_raio_nunca_vira_ponto`, `::test_raio_cresce_com_a_velocidade_plausivel`, `::test_raio_para_de_crescer_no_teto`, `::test_raio_ignora_o_sinal_do_delta`, `::test_raio_nunca_encolhe_com_o_tempo`, `::test_raio_por_granularidade_bate_com_a_escala_do_campo`, `::test_heranca_carrega_o_proprio_raio`, `::test_frase_do_raio_cita_a_doadora_o_tempo_e_o_tamanho`, `::test_frase_no_piso_fala_do_receptor_e_nao_de_deslocamento`, `::test_frase_no_teto_diz_que_o_raio_parou_de_crescer`, `::test_frase_sem_nome_da_doadora_nao_deixa_buraco`, `::test_frase_acompanha_o_raio_quando_a_constante_mudar`.
- **Decisões:** D-031 (mapa nasce sem tiles), D-032 (raio medido, não suposto), D-033 (foto fora de alcance continua no mapa), D-050/D-065 (o mapa existia e ninguém achava; badge no card corrige).
- **Arquivos:** `fotoorganizer/grouping/correlacao.py:59-84,439-521`, `fotoorganizer/geolocation/escala.py:21-39`, `fotoorganizer/server/app.py:343-437,928-1020`, `scripts/calibrar_raio_incerteza.py`.

---

### F-I16 — Sessões temporais
- **Propósito:** agrupar fotos em *sessões* pela lacuna de tempo entre elas — o primeiro recorte, que ainda não diz o que a sessão é.
- **Gatilho:** job `sugestoes`, `SuggestionEngine._montar_sessoes`.
- **Entradas:** `[(media_id, data_capturada or mtime)]` de todas as mídias organizáveis que têm uma das duas datas.
- **Regras de negócio:**
  1. `GAP_NOVA_VIAGEM = timedelta(days=3)`: ordena por data e corta onde `(data - atual.fim) > gap`.
  2. **Não usa dia de calendário** — uma viagem pode durar semanas; o que separa é a lacuna longa sem fotos ("voltou pra casa").
  3. Foto sem `data_capturada` **e** sem `mtime` fica de fora: não dá para saber a que sessão pertence.
  4. Depois do corte por casa (F-I17), sessões com menos de `_MIN_FOTOS_SESSAO = 2` fotos são descartadas.
  5. **Sessão em que nenhum membro tem `data_capturada`** (100% mtime) **fica neutra sem passar pela cascata**: agrupar por mtime cria uma "viagem" no dia do scan — captura de tela e arquivo recuperado viram passeio. A foto continua catalogada e cai no ramo de não classificadas.
  6. A ordem de entrada não importa: `agrupar_viagens` ordena antes.
- **Saídas:** `list[ViagemDraft]` com `inicio`, `fim`, `media_ids`, `n_fotos`, `periodo_legivel()` (`"dd/mm/aaaa"` ou `"dd/mm/aaaa – dd/mm/aaaa"`).
- **Degradação/falha:** lista vazia → nenhuma sessão, nenhuma exceção.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_grouping.py::test_lacuna_separa_viagens`, `::test_viagem_longa_nao_quebra_por_dia`, `::test_ordem_de_entrada_nao_importa`, `::test_dia_unico_tem_periodo_simples`; `tests/test_suggestion_engine.py::test_fotos_sem_data_de_captura_nao_viram_viagem`.
- **Decisões:** n/a (`docs/AGRUPAMENTO.md` §1).
- **Arquivos:** `fotoorganizer/grouping/temporal.py:13-52`, `fotoorganizer/classification/engine.py:98,496-543`.
- **⚠️ Divergência M1:** a base de tempo mistura `data_capturada` (parede local) com `mtime` (UTC naive). 33,3% de 53.967 registros têm delta múltiplo exato de 1 h. Viagens são imunes (gap de 3 dias); eventos e herança, não.

---

### F-I17 — Transição casa↔fora
- **Propósito:** separar duas viagens coladas que a lacuna temporal não vê — `[viagem A][2 dias em casa][viagem B]` virava uma sessão só.
- **Gatilho:** job `sugestoes`, `SuggestionEngine._dividir_draft`, só quando a casa é conhecida.
- **Entradas:** o `ViagemDraft`, as coordenadas efetivas dos membros e a casa detectada.
- **Regras de negócio:**
  1. **Detecção da casa:** célula GPS modal arredondada a `_PRECISAO_CELULA = 1` casa decimal (≈ 11 km), exigindo `_MIN_FOTOS_GPS = 20` fotos com GPS e `_FRACAO_MINIMA = 0.30` delas na célula. Abaixo disso, "casa desconhecida" e nada acontece.
  2. **Só GPS real entra na detecção** — coordenadas herdadas repetem as dos doadores e inflariam artificialmente a célula modal.
  3. Estado de cada foto: `distancia_km(coords, casa) <= raio_casa_km` (50 km), ou `None` sem coordenada (**herda o estado corrente**).
  4. **A transição só corta quando confirmada pela foto com GPS SEGUINTE no mesmo estado novo**: uma foto isolada (GPS errado, escala rápida perto de casa) não divide uma viagem real.
  5. Distância por haversine, `RAIO_TERRA_KM = 6371.0`.
  6. Sem GPS nenhum ou sem casa conhecida, nada muda.
- **Saídas:** a lista de `ViagemDraft` substituída pelos segmentos.
- **Degradação/falha:** um só segmento → devolve o draft original intacto.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_grouping.py::test_viagens_coladas_separadas_ao_passar_por_casa`, `::test_foto_isolada_em_casa_nao_corta_viagem_real`, `::test_fotos_sem_gps_herdam_o_segmento_corrente`, `::test_sessao_sem_gps_nenhum_fica_inteira`; `tests/test_eventos_home.py::test_detectar_casa_exige_massa_minima`, `::test_detectar_casa_celula_modal`, `::test_detectar_casa_sem_moda_clara`, `::test_distancia_km`; `tests/test_suggestion_engine.py::test_viagens_coladas_separadas_pela_passagem_em_casa`.
- **Decisões:** n/a (`docs/AGRUPAMENTO.md` §1).
- **Arquivos:** `fotoorganizer/grouping/temporal.py:55-113`, `fotoorganizer/geolocation/home.py:13-40`, `fotoorganizer/classification/engine.py:505-517,598-620`.

---

### F-I18 — Cascata de classificação de sessão
- **Propósito:** decidir **o quê** cada sessão é — viagem, evento ou neutra — e **como se chama**, de forma determinística, auditável e testável cenário a cenário.
- **Gatilho:** job `sugestoes`, `classificar_sessao(DadosSessao, ConfigClassificacao)` — função pura.
- **Entradas:** `DadosSessao(pastas, duracao, pais_dominante, dist_mediana_casa_km, periodo_curto, paises_no_tempo, albuns, fonte_dos_albuns, cameras, tipos_de_nome)`.
- **Regras de negócio (ordem é a regra):**
  1. Segmento de pasta em `{"viagens","viagem"}` → **VIAGEM**, origem `pasta`.
  2. Pasta com palavra-chave de evento (`aniversario, casamento, formatura, batizado, cha de bebe, festa, natal, reveillon, ano novo, pascoa, churrasco, show, festival, despedida, confraternizacao, bodas` ou `\b\d{1,3}\s*anos?\b`) → **EVENTO** nomeado pela pasta, `rotulo_de_pasta = True`.
  3a. Um segmento que lista **≥ 2 países** (`identificar_paises`) → **VIAGEM** nomeada pelo **segmento cru**. A lista do dono vale mais que as pernas do GPS: em "Dubai, Thai & Viet", 106 de 2.405 fotos tinham GPS e **nenhuma** nos Emirados. Detecta com a tabela canônica, **nomeia com as palavras do dono**; os países reconhecidos vão para a justificativa.
  3b. País reconhecido na hierarquia da pasta → **VIAGEM** nomeada pelo país, `rotulo_de_pasta = True`.
  4. `dist_mediana_casa_km > dist_viagem_km` (100 km) → **VIAGEM**, origem `gps`.
  5. `pais_dominante` **e** `duracao >= duracao_min_viagem` (3 dias) **e** casa desconhecida → **VIAGEM**, origem `geocoding_offline`. A exigência de casa desconhecida é o resultado do benchmark: com casa conhecida quem decide é a regra 4, senão férias EM CASA (6 dias de GPS a 2 km) viravam "viagem".
  6. Nome de álbum de pasta **e** `duracao <= duracao_max_evento` (2 dias) → **EVENTO** pela pasta; **exceto** se o léxico disser que o nome é `lugar` (→ VIAGEM, origem `lexico`) ou se o léxico conhecer outro nível do caminho (`_opiniao_no_caminho`, da folha à raiz).
  7. Nada acima → **NEUTRA**. Um cluster de horas **nunca** vira viagem sozinho — era o defeito original do v3 (`2026/Serena 15 Anos`, 4 horas, rotulada "Viagem de 09-05").
  8. Nomeação de viagem: país explícito → pernas em ordem cronológica juntadas por `" – "` → `pais_dominante` → `periodo_curto`. **Nunca rótulo vazio.**
  9. `origem_do_rotulo` é separada de `origem` porque divergem: a sessão pode ser viagem pelo GPS e o nome vir do álbum.
  10. Sessão neutra é a **única** que consulta o advisor LLM (F-I31).
  11. Com o léxico desligado (padrão), `tipo_do_nome` devolve `None` e a cascata decide exatamente como decidia antes.
- **Saídas:** `Decisao(tipo, rotulo, origem, justificativa, origem_do_rotulo, rotulo_de_pasta)`; depois `Trip`/`Event` recriados do zero a cada geração.
- **Degradação/falha:** sem resolver, `pais_dominante` é `None` e as regras 4/5 desligam. Sem casa, a regra 4 desliga.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_eventos_home.py::test_classificador_cenarios_chave`, `::test_keywords_de_evento`, `::test_pastas_tecnicas_nao_sao_album`, `::test_nomes_de_album`, `::test_extrair_evento_prefere_keyword`, `::test_nome_de_usuario_nao_e_album`; `tests/test_grouping.py::test_pasta_que_lista_destinos_nomeia_a_viagem_inteira`; `tests/test_paises.py::test_pasta_lista_os_destinos_da_viagem`, `::test_meia_lista_ou_nenhuma_nao_vira_viagem`, `::test_abreviacao_curta_demais_nao_chuta`; `tests/test_suggestion_engine.py::test_aniversario_na_pasta_nao_vira_viagem`, `::test_album_curto_vira_evento_nomeado`, `::test_viagem_nomeada_pelo_pais_dominante`, `::test_pastas_tecnicas_sem_sinal_ficam_neutras`; `tests/test_lexico.py::test_nome_de_lugar_vira_viagem_e_nao_evento`, `::test_nome_de_ocasiao_continua_evento`, `::test_sem_lexico_a_cascata_decide_como_sempre`, `::test_lexico_alcanca_o_lugar_um_nivel_acima_da_folha`, `::test_lexico_reconhece_ocasiao_em_nivel_intermediario`, `::test_lugar_nao_transforma_sessao_longa_em_evento`; benchmark: `scripts/avaliar_agrupamento.py` (19 cenários (contagem real em `scripts/avaliar_agrupamento.py`, 2026-09-20; `docs/EVENTOS.md` ainda diz 17)).
- **Decisões:** D-030 (álbum nomeia, não divide), D-034 (álbum nomeia onde a pasta não nomeia).
- **Arquivos:** `fotoorganizer/grouping/classifier.py:20-262`, `fotoorganizer/grouping/eventos.py:19-134`, `fotoorganizer/geolocation/paises.py:168-207`, `fotoorganizer/classification/engine.py:622-661,745-780`.

---

### F-I19 — Nomeação por álbum de catálogo externo
- **Propósito:** aproveitar as 27.226 nomeações de álbum do Apple Fotos e do Lightroom como **nome** de sessão — sem deixá-las criar nem dividir acontecimento.
- **Gatilho:** job `sugestoes`, `_nomear_por_album`, aplicado **depois** da cascata.
- **Entradas:** `dados.albuns` (tupla `(nome, contagem)` do período, vinda de `_IndiceDeAlbuns`), `dados.cameras`, `dados.fonte_dos_albuns`.
- **Regras de negócio:**
  1. **Três limites, nesta ordem:** sessão neutra continua neutra (nomear o que a cascata não classificou seria detectar evento por álbum, proibido por D-030); quando o rótulo já é segmento de pasta, a pasta ganha; só substitui nome **derivado** (país geocodificado ou período).
  2. Desempate entre álbuns: **não-prateleira antes de prateleira** → **mais fotos primeiro** → **nome mais curto, depois alfabético** (determinismo: "Empolga 2025" e "Empolga as 9 - 2025" têm 159 fotos cada, e o rótulo não pode dançar entre regenerações).
  3. Prateleira (`_PRATELEIRAS`: `ferias, family, viagens, trips, travel, eventos, momentos, memories, melhores, selecao, geral, diversos, casa, trabalho, album, fotos, pictures`…) é **rebaixada, não rejeitada** — a ação menor, que preserva o único sinal num acervo onde o dono só usou a gaveta.
  4. `MIN_FOTOS_ALBUM = 3` — mesmo número e mesma razão de `_MIN_FOTOS_PERNA`.
  5. `album_nomeia` descarta app/serviço (`_APPS` + `_RE_SERVICO`) e **câmera por dois caminhos**: o conjunto aprendido do catálogo **e** a lista de marcas. Os dois são necessários — o maior álbum de um acervo real era "Canon EOS 5D Mark IV" e o catálogo alcançável só conhecia quatro modelos, nenhum deles esse.
  6. `separar_data` tira a data do nome ("Peru - Julho de 2026" nomeia "Peru"); se sobrar só a data, não nomeia.
  7. `_IndiceDeAlbuns` carrega todas as marcações **uma vez por geração** e responde por **bisseção**, **sem folga nas bordas** — a régua é o período que o agrupamento já decidiu. Uma consulta por sessão seria N+1 sobre a maior tabela do catálogo.
  8. `origem_do_rotulo = "album_externo"` (0.55), **abaixo** de `pasta` (0.60): a foto *está* na pasta e apenas *coincide no tempo* com o álbum.
  9. Justificativa concatenada: `"<justificativa da cascata>; nome do álbum '<nome>' (<fonte>), que cobre <N> fotos deste período"`.
- **Saídas:** `Decisao` com `rotulo` novo e `origem_do_rotulo = "album_externo"`. No catálogo real: **1.605 evidências** `viagem|album_externo`.
- **Degradação/falha:** nenhum candidato sobrevive aos filtros → `escolher_album` devolve `None` e a decisão segue intacta.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_nome_de_album.py::test_o_aninhado_especifico_vence_a_prateleira_mais_frequente`, `::test_o_album_do_acontecimento_inteiro_vence_o_aninhado_dentro_dele`, `::test_camera_e_app_nao_nomeiam_nem_quando_sao_maioria`, `::test_punhado_de_fotos_nao_nomeia_o_conjunto`, `::test_empate_de_contagem_e_deterministico`, `::test_a_data_sai_do_nome_como_ja_sai_da_pasta`, `::test_album_que_e_so_data_nao_nomeia`, `::test_pasta_informativa_vence_album`, `::test_pais_lido_da_pasta_tambem_vence_album`, `::test_pasta_tecnica_cede_para_album`, `::test_periodo_sem_nome_nenhum_cede_para_album`, `::test_sessao_neutra_continua_sem_nome_mesmo_com_album`, `::test_album_do_apple_fotos_nomeia_a_viagem`, `::test_a_evidencia_diz_de_onde_o_nome_veio`; `tests/test_albuns.py::test_nomes_que_o_dono_escreveu_nomeiam`, `::test_app_e_servico_nao_nomeiam`, `::test_nome_de_aparelho_nao_nomeia`, `::test_camera_do_proprio_acervo_e_reconhecida_sem_estar_na_lista`, `::test_camera_fora_do_alcance_ainda_e_barrada_pela_marca`.
- **Decisões:** D-028 (Lightroom como fonte), D-030, D-034.
- **Arquivos:** `fotoorganizer/grouping/albuns.py:50-196`, `fotoorganizer/grouping/classifier.py:95,107-140`, `fotoorganizer/classification/engine.py:113,136-201`.

---

### F-I20 — Viagem multi-país (pernas)
- **Propósito:** nomear uma viagem que passou por vários países pelas **pernas em ordem cronológica de chegada**, em vez de só o país com mais fotos.
- **Gatilho:** job `sugestoes`, `_geo_da_sessao`, antes de `classificar_sessao`.
- **Entradas:** os membros da sessão **em ordem temporal**, com coordenada efetiva.
- **Regras de negócio:**
  1. Acumula `paises` (Counter) e `ordem_paises` (ordem de chegada) resolvendo cada coordenada efetiva.
  2. **Corte por granularidade**: para foto com coordenada herdada, o país só conta se `heranca.fator_de("pais")` não for `None`, e a cidade só entra em `lugares` se `fator_de("cidade")` existir. Sem esse corte, uma foto correlata a 6 h nomearia a viagem com a cidade errada.
  3. `pernas` = países com `>= _MIN_FOTOS_PERNA = 3` fotos geocodificadas — uma escala de aeroporto com 1-2 fotos não nomeia a viagem.
  4. **Menos de 2 pernas → `()`**: não é multi-país.
  5. `lugares` = `"Cidade, País"` sem repetição, **até 5** — é o que vai para o payload do advisor e para o contexto da sugestão.
  6. O rótulo sai como `" – ".join(pernas)`: `"Emirados Árabes Unidos – Tailândia – Vietnã"`.
  7. A hierarquia região/cidade de **cada foto** continua refletindo a perna dela, mesmo com a viagem nomeada pelo conjunto.
- **Saídas:** `(pais_dominante, lugares, pernas)`; o rótulo da viagem.
- **Degradação/falha:** sem resolver → `(None, (), ())`. Nenhuma coordenada resolvida → idem.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_suggestion_engine.py::test_viagem_multipais_rotulada_pelas_pernas`; `tests/test_eventos_home.py::test_viagem_multipais_nomeada_pelas_pernas_em_ordem`.
- **Decisões:** D-025 (o corte por granularidade).
- **Arquivos:** `fotoorganizer/classification/engine.py:109,663-703`, `fotoorganizer/grouping/classifier.py:167-181`.

---

### F-I21 — Subdivisão em acontecimentos
- **Propósito:** separar dois acontecimentos no mesmo dia — aniversário de manhã e show à noite — que a lacuna de 3 dias nunca encontra.
- **Gatilho:** job `sugestoes`, `SuggestionEngine._subdividir`, **depois** da classificação; cada bloco é **reclassificado**.
- **Entradas:** `Momento(media_id, quando, lat, lon)` dos membros, com coordenada **efetiva**, e o tipo já decidido da sessão.
- **Regras de negócio:**
  1. **Viagem não se divide.** `dividir_sessao(..., e_viagem=True)` devolve um bloco só — dividir uma viagem produz uma saída por manhã e por tarde, desfazendo "uma viagem é uma pasta".
  2. **Sessão que atravessa noites também não**: `> DURACAO_MAX_ACONTECIMENTO = 20 h` corridas é estadia, mesmo que o classificador a tenha rotulado "evento" por não alcançar o limiar de 3 dias. É o que segura o Pantanal (97 fotos em 3 dias, que a régua partia em quatro).
  3. **A régua é relativa ao ritmo local**, não um intervalo fixo: corta quando `intervalo > mediana(até JANELA=12 intervalos ANTERIORES) × FATOR=6.0`. A janela olha **só para trás** — uma janela simétrica se contamina com o bloco seguinte.
  4. `PISO = 90 min`: nunca corta abaixo disso. Num dia disparando a cada 10 min, 70 min é sete vezes o ritmo e ainda é almoço. 90 e não 45 porque o erro barato é juntar demais — o dono desfaz com um clique.
  5. `TETO = 8 h`: sempre corta acima disso, por mais espaçado que o ritmo venha sendo.
  6. `DESLOCAMENTO_KM = 3.0`: mudar de lugar corta **independente do tempo**, quando há coordenada dos dois lados. 3 km separa bairros sem separar salões do mesmo casamento.
  7. `MIN_FOTOS_EVENTO = 10`: bloco menor é absorvido no vizinho anterior (o primeiro bloco, que não tem anterior, é prependido ao segundo). A Serena 15 Anos tinha 5 fotos de teste às 17:25 — tecnicamente dois eventos, e o dono não reconhece 5 fotos como evento da própria vida.
  8. Um bloco só, por menor que seja, fica: se a sessão inteira tem três fotos, elas são o acontecimento.
  9. Cada bloco vira seu próprio `Event`; nenhum arquivo é tocado.
  10. **Sinais cogitados e não implementados**: câmera/lente (troca de lente é exemplo do que **não** deve cortar), álbum (D-030 — os álbuns se aninham), hora do dia (não há regra "manhã ≠ noite").
- **Saídas:** `list[list[media_id]]` na ordem do tempo; cada bloco reclassificado vira uma `_Sessao`.
- **Degradação/falha:** lista vazia → `[]`; um momento → um bloco. Sem coordenada dos dois lados, `_km` devolve `None` e o deslocamento não opina.
- **Estado:** pronto. **Sem desligamento por configuração** — é incondicional; desligar exige remover a chamada em `engine.py:553-556`.
- **Testes que provam:** `tests/test_eventos_temporais.py::test_aniversario_de_manha_e_show_a_noite_sao_dois`, `::test_viagem_continua_nao_e_partida_na_meia_noite`, `::test_pausa_de_almoco_nao_corta`, `::test_respiro_de_rajada_nao_vira_evento`, `::test_ritmo_lento_ainda_tem_fronteira_pelo_teto`, `::test_mudar_de_lugar_corta_mesmo_com_as_fotos_coladas`, `::test_andar_pelo_bairro_nao_corta`, `::test_coordenada_de_um_lado_so_nao_decide`, `::test_viagem_continua_sendo_uma_pasta_so`, `::test_sessao_que_atravessa_noites_e_um_destino_so`, `::test_festa_que_vira_a_noite_ainda_e_uma_festa`, `::test_fotos_de_teste_nao_viram_evento_proprio`, `::test_bloco_pequeno_no_fim_tambem_e_absorvido`, `::test_sessao_inteira_pequena_continua_existindo`, `::test_dois_eventos_grandes_continuam_dois`; `tests/test_suggestion_engine.py::test_aniversario_de_manha_e_show_a_noite_viram_dois_eventos`.
- **Decisões:** D-030 (álbum não divide). Medições em `docs/EVENTOS.md` e nos commits `076630f` e `6214828`.
- **Arquivos:** `fotoorganizer/grouping/eventos_temporais.py:52-201`, `fotoorganizer/classification/engine.py:545-595`.

---

### F-I22 — Evidência de categoria
- **Propósito:** decidir a categoria de topo do destino — `Viagens`, `Família` ou `Eventos` — pela fonte mais forte que existir.
- **Gatilho:** job `sugestoes`, `SuggestionEngine._categoria`.
- **Entradas:** `media.pasta`, a `_Sessao`, as palavras-chave de curadoria da foto, a proposta de GenAI aprovada para a pasta.
- **Regras de negócio (ordem é a regra):**
  1. Segmento de pasta em `_CATEGORIAS_PASTA` (`viagens|viagem → Viagens`, `familia|família → Família`, `eventos|evento → Eventos`), procurando **da folha para a raiz** → origem `pasta` (0.60).
  2. Tipo da sessão: viagem → `Viagens`; evento → `Eventos`. Origem = `sessao.origem` (0.60–0.85 conforme a regra que decidiu).
  3. **2b — palavra-chave humana** (XMP/IPTC) com o mesmo vocabulário → origem `curadoria` (0.55). Fica **abaixo** da sessão de propósito: a sessão é o mesmo veredito para todas as fotos do grupo, e uma palavra-chave de uma foto só não pode fragmentar esse veredito. Fica **acima** do advisor porque é determinística e grátis.
  4. Advisor de cluster (`sessao.categoria`) → origem `llm` (0.55).
  5. Proposta de GenAI de pasta → origem `llm_pasta` (0.55). É **irmão** do advisor, nunca fundido: a origem chega diferente ao banco porque são afirmações de natureza distinta (nome de pasta × metadado de mídia) e a Revisão precisa distinguir as duas.
  6. Nada acima → `None`, e o destino cai no ramo de não classificadas.
  7. O vocabulário é fechado em três valores, e expandir é **um eixo novo** (tipo de mídia), não mais opções no mesmo campo (D-053).
- **Saídas:** um `_Draft("categoria", ...)`. No catálogo real: 13.271 por `geocoding_offline`, 11.366 por `pasta`.
- **Degradação/falha:** nenhuma — a ausência de categoria é um resultado válido.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_suggestion_engine.py::test_palavra_chave_curadoria_decide_categoria_sem_pasta`, `::test_curadoria_nao_sobrepoe_sessao_de_alta_confianca`, `::test_pasta_vence_palavra_chave_curadoria_divergente`, `::test_advisor_llm_apoia_sessao_neutra`, `::test_advisor_nulo_nao_opina`; `tests/test_cascata_llm_pasta.py::test_advisor_de_cluster_vence_na_categoria`, `::test_determinismo_vence_o_llm`, `::test_sem_proposta_o_resultado_e_identico`.
- **Decisões:** D-057 (palavra-chave vira evidência de categoria), D-053, D-057 (Fase A implementada), D-081.
- **Arquivos:** `fotoorganizer/classification/engine.py:95-97,1027-1083`.

---

### F-I23 — Montagem do destino e confiança final
- **Propósito:** transformar as evidências num caminho de pasta legível e numa confiança que o usuário entende — **o elo mais fraco**, nunca uma soma.
- **Gatilho:** job `sugestoes`, `_persistir_sugestao` + `_salvar_sugestao`.
- **Entradas:** a lista de `_Draft` da foto e o template (de `SettingsRepository.obter_template(TEMPLATE_PADRAO)`).
- **Regras de negócio:**
  1. `TEMPLATE_PADRAO = "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}"`; `campos["ano"]` é derivado da evidência de `data`.
  2. **Uma viagem é uma pasta**: quando há `viagem` ou `evento`, país/região/cidade são zerados do caminho. Não é estético — das 2.405 fotos de uma mesma viagem, 106 tinham coordenada; deixar a hierarquia descer partia a viagem em três pastas conforme **qual foto por acaso gravou GPS**.
  3. Três ramos de destino: **não é foto** → `"Não são fotos/<Rótulo>/<ano>"`; **nada nomeia** (`_CAMPOS_QUE_NOMEIAM` todos vazios) → `"Não classificadas/<ano>/<jul.2023>"`, ou só o ano, ou `"sem data"`; senão → `render_destino(template, campos)`.
  4. `render_destino`: segmento com todos os placeholders vazios é descartado; **valor que já apareceu acima no caminho não repete** (comparação por parte inteira, sem acento e sem caixa — senão "York" sumiria sob "New York"); sobras de separador aparadas; cada segmento normalizado (NFC, inválidos → `_`, `strip(". ")`, máximo **80** caracteres); tudo vazio → `"Não classificadas"`.
  5. `usados` = só as evidências cujo placeholder está no template **e** tem valor. `_contexto_da_sugestao` anexa país/região/cidade que **não** viraram pasta — sem esse vínculo a justificativa existiria no banco e não chegaria a lugar nenhum.
  6. **`elo_mais_fraco(scores) = min(scores)`**, calculado **só sobre `usados`**: contexto que não virou pasta não puxa a confiança para baixo.
  7. Níveis: `>= 0.8 ALTA`, `>= 0.5 MEDIA`, `< 0.5 BAIXA`. Sem evidência → `(BAIXA, 0.0)`.
  8. **Concordância não sobe score**: o draft de `ano` (testemunha da pasta) é removido de `usados` antes do cálculo. `docs/CONFIANCA.md` proíbe soma de confianças.
  9. `resolver_colisao` sufixa `" (2)"`… até 9.999; nunca sobrescreve nome usado.
  10. `versao_logica = "4.1"` é gravado em cada `Evidence` e em cada `Suggestion`.
- **Saídas:** `Suggestion(media_id, destino_sugerido, template, nivel, versao_logica)` + vínculos em `suggestion_evidence`. No catálogo real: **ALTA 40.747 · MEDIA 13.044 · BAIXA 1.305**.
- **Degradação/falha:** sem nenhuma evidência usada → nível BAIXA, score 0.0, destino `"Não classificadas/sem data"`.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_confidence.py::test_mapeamento_de_niveis`, `::test_elo_mais_fraco_manda`, `::test_sem_evidencia_e_baixa`, `::test_tabela_de_referencia_coerente`; `tests/test_templates.py::test_render_completo`, `::test_segmento_vazio_cai_fora`, `::test_tudo_vazio_nao_inventa`, `::test_normalizacao_remove_invalidos`, `::test_normalizacao_limita_comprimento`, `::test_unicode_preservado`, `::test_colisao_recebe_sufixo`, `::test_pais_nao_repete_dentro_do_rotulo_da_viagem`, `::test_cidade_igual_a_regiao_aparece_uma_vez`, `::test_supressao_compara_parte_inteira_nao_pedaco_de_palavra`, `::test_supressao_ignora_acento_e_caixa`; `tests/test_suggestion_engine.py::test_uma_viagem_e_uma_pasta_so`, `::test_nao_classificadas_quebram_por_ano_e_mes`, `::test_mes_nao_invade_destino_que_ja_tem_nome`, `::test_sem_evidencia_fica_baixa_e_nao_inventa`.
- **Decisões:** D-017 (confiança como quantidade, não semáforo), D-018 (a unidade de decisão da Revisão é o grupo), D-043 (`versao_logica` escrito e nunca lido), D-071 (badge "Alta" em "Não classificadas" vira "Sem categoria").
- **Arquivos:** `fotoorganizer/classification/templates.py:24-117`, `fotoorganizer/classification/confidence.py:86-103`, `fotoorganizer/classification/engine.py:100-107,1084-1118,1181-1290`.

---

### F-I24 — Preservação de decisão na regeneração
- **Propósito:** garantir que reprocessar o catálogo nunca desfaça o que o usuário já decidiu.
- **Gatilho:** job `sugestoes`, `_midias_com_decisao` no início de `gerar()`.
- **Entradas:** `Suggestion.status` de todas as sugestões.
- **Regras de negócio:**
  1. Mídia com `status != PENDENTE` (`aprovada`, `rejeitada`, `editada`) é **pulada inteira** no laço de geração.
  2. `_persistir_sugestao` apaga **só as PENDENTES** da mídia, mais os vínculos e todas as `Evidence` daquela mídia, e recria.
  3. `tipo_confirmado` nunca é tocado pelo motor — só pela rota do usuário.
  4. `PastaClassificada` com `origem == "manual"` é **inteiramente intocável**, inclusive nos campos vazios: a máquina não completa o que o dono já assumiu a autoria de decidir.
  5. `NomeClassificado` com `origem == "manual"` nunca é sobrescrito por reclassificação.
  6. Dois recálculos rodam **mesmo para mídia decidida**, porque senão congelariam para sempre: `gps_*_estimado` (`_persistir_herancas`) e `tz_estimado` (`_atualizar_tz_estimado`, CR-01). `location_id` idem (`_resolver_locations`, WR-01).
  7. `trips`/`events` são recriados do zero a cada geração — a limpeza percorre **todas** as mídias, não só as organizáveis, senão o `DELETE` esbarra na FK de uma que foi rebaixada a testemunha.
- **Saídas:** `resultado["preservadas"]` = quantidade de mídias puladas.
- **Degradação/falha:** n/a.
- **Estado:** **parcial.** Não existe mecanismo de **reabertura**: uma sugestão aprovada cujo destino mudaria por reprocessamento fica congelada no que foi aprovado, e nada avisa. A memória do projeto registra a decisão do dono de "reabrir, não congelar", e `plano-refactor.md:288-292` confirma que "A1+A2 saíram sem flag e sem mecanismo de reabertura de sugestões… a decisão fica registrada para a próxima mudança que de fato desloque a hora".
- **Testes que provam:** `tests/test_suggestion_engine.py::test_regeneracao_preserva_decisao_do_usuario`, `::test_regeneracao_de_pendentes_nao_duplica`, `::test_tz_estimado_atualiza_ao_regenerar_sugestoes`, `::test_tz_estimado_atualiza_mesmo_com_sugestao_decidida`, `::test_location_id_resolvido_mesmo_para_sugestao_ja_decidida`; `tests/test_pasta_classificacao_genai.py::test_linha_manual_nao_e_tocada`, `::test_nunca_sobrescreve_campo_ja_preenchido`; `tests/test_lexico.py::test_correcao_do_dono_sobrevive_a_reclassificacao`.
- **Decisões:** D-043; decisão do dono sobre reabertura registrada e **não implementada**.
- **Arquivos:** `fotoorganizer/classification/engine.py:278,316-330,1120-1124,1181-1194`, `fotoorganizer/repositories/pasta_classificacao.py:70-114`, `fotoorganizer/repositories/lexico.py:33-60`.

---

### F-I25 — Descarte de sugestões órfãs
- **Propósito:** não pedir decisão sobre miniatura de cache — sem apagar nada que o usuário tenha decidido.
- **Gatilho:** job `sugestoes`, `_descartar_sugestoes_orfas`, antes do laço de geração.
- **Entradas:** `Suggestion` PENDENTES cuja mídia não é mais `organizavel`.
- **Regras de negócio:**
  1. Alvo: `status == PENDENTE` **e** `NOT MediaFile.organizavel` (papel ≠ ACERVO, ou arquivo ausente, ou arquivo offline).
  2. **Só as PENDENTES.** Aprovada e rejeitada são decisão do usuário, e decisão dele não se apaga por mudança de classificação nossa.
  3. O alvo é uma **subconsulta** (`scalar_subquery`), não uma lista de ids: com 45.822 mídias rebaixadas de uma vez, o `IN (?, ?, …)` estoura o limite de variáveis do SQLite.
  4. Apaga primeiro os vínculos em `suggestion_evidence`, depois as `Suggestion`.
  5. **Nenhuma `MediaFile` e nenhuma `Evidence` é apagada** — a mídia rebaixada continua doando data, GPS e correlação (invariante 8).
  6. Loga `"descartadas %d sugestões de mídia que não é acervo"`.
- **Saídas:** `resultado["descartadas"]` (inteiro).
- **Degradação/falha:** n/a — `rowcount` 0 é resultado válido.
- **Estado:** pronto.
- **Testes que provam:** n/a diretamente; o efeito é coberto por `tests/test_inventario.py::test_testemunha_nao_conta_como_organizavel`, `::test_miniatura_alcancavel_nao_e_organizavel`.
- **Decisões:** D-024 (rebaixar, nunca apagar), D-035 (as 45.822 miniaturas), D-068 ("organizáveis" exige a fonte respondendo).
- **Arquivos:** `fotoorganizer/classification/engine.py:307,1144-1179`, `fotoorganizer/models/catalog.py:273-300`.

---

### F-I26 — Geocodificação reversa offline e cache
- **Propósito:** traduzir coordenada em país/região/cidade **sem que nada saia da máquina**, e sem consultar o dataset duas vezes pelo mesmo lugar.
- **Gatilho:** job `sugestoes`, `_resolver_locations` (para TODA coordenada efetiva, antes de sessão e categoria) e `_evidencias_geo`.
- **Entradas:** `(lat, lon)`.
- **Regras de negócio:**
  1. Dataset **local** (`reverse_geocode`, GeoNames `cities1000`), import **lazy** — monta uma KDTree na primeira consulta e deve rodar fora da thread da UI.
  2. Resultado é o **vizinho mais próximo** entre as cidades do dataset, não um polígono administrativo. Não há raio máximo nem nível de rua.
  3. `pais` ← código ISO traduzido por `PAISES_PT` (tabela estática), com fallback para o nome em inglês quando o código é desconhecido — melhor em inglês do que ausente.
  4. `regiao` ← `limpar_regiao`, que tira sufixo/prefixo administrativo em inglês ("Quảng Nam Province" → "Quảng Nam").
  5. `cidade` fica **no idioma local**: "Hoi An" e "Chiang Mai" são os nomes certos dos lugares, não erros de tradução.
  6. Cache: `cache_key = f"{round(lat,3):.3f},{round(lon,3):.3f}"` (≈ 110 m). Fotos no mesmo lugar reusam a mesma linha de `locations`.
  7. `FONTE = "offline:reverse_geocode/2"` — a **versão** dentro da string é o que invalida o cache quando a nomenclatura muda; sem ela, as fotos já resolvidas guardariam para sempre o nome antigo.
  8. Provider mudo (`None`) **não apaga** o que já se sabia do lugar.
  9. Mesmo lugar com nomenclatura nova → a linha é **reescrita no lugar**, para as fotos já apontadas acompanharem.
  10. `_resolver_locations` memoiza por `cache_key` **dentro do loop**: sem isso, uma viagem de 500 fotos na mesma coordenada arredondada vira 500 SELECTs.
  11. Grava `location_id` **inclusive `None`**: coordenada que deixou de resolver não pode deixar a mídia presa a um país que ela não tem mais.
  12. **Nenhuma rede.** O provider externo opt-in existe só como `Protocol`.
- **Saídas:** linha em `locations`; `MediaFile.location_id`. No catálogo real: **2.203 lugares distintos, 17 países**.
- **Degradação/falha:** qualquer exceção do dataset → `log.warning` + `None`; a cascata cai para nome de pasta e vizinhança. Sem o pacote, `resolver` pode ser `None` e as regras 4/5 da cascata de sessão desligam.
- **Estado:** pronto para o caminho offline. **O provider externo (`geocoding_externo`, 0.75) está na tabela de confiança e não tem implementação.**
- **Testes que provam:** `tests/test_geolocation.py::test_resolver_usa_cache_da_tabela`, `::test_geocoder_offline_real`, `::test_cache_de_lugar_e_reescrito_quando_a_nomenclatura_muda`; `tests/test_paises.py::test_codigo_iso_da_nome_em_portugues`, `::test_codigo_desconhecido_ou_vazio_nao_explode`, `::test_rotulo_administrativo_ingles_sai_da_regiao`, `::test_tabela_iso_sem_nomes_repetidos`, `::test_o_que_nao_e_pais_continua_nao_sendo`.
- **Decisões:** D-051/D-052/D-058 (geocodificação cedo, "geo-first").
- **Arquivos:** `fotoorganizer/geolocation/offline.py:20-57`, `fotoorganizer/geolocation/resolver.py:16-66`, `fotoorganizer/geolocation/paises.py:22-233`, `fotoorganizer/geolocation/base.py:14-36`, `fotoorganizer/classification/engine.py:374-409`.

---

### F-I27 — Fuso estimado por país
- **Propósito:** saber em que fuso a foto provavelmente foi tirada, com granularidade grosseira e honesta, sem dependência nova e sem rede.
- **Gatilho:** job `sugestoes`, `_atualizar_tz_estimado`, para **toda** mídia organizável.
- **Entradas:** o país efetivo, calculado por `_pais_efetivo`.
- **Regras de negócio:**
  1. `_pais_efetivo` repete a cascata geográfica **sem gravar evidência**: GPS próprio → GPS herdado (só se `fator_de("pais")` existir) → país da pasta → país dominante da sessão. Duplicada de propósito, para não arriscar mudar o texto das justificativas existentes.
  2. `media.tz_estimado = TZ_POR_PAIS.get(pais)`; sem país, `None`.
  3. A chave é o **nome em português** (mesma grafia de `PAISES_PT`), não o código ISO: `Evidence.valor` já chega como nome, e recodificar seria trabalho e bug a mais.
  4. Granularidade **grosseira de propósito**: um fuso por país, não geometria coordenada→fuso. `timezonefinder`, `pytz` e `geo-tz` foram descartados (D-07).
  5. Regra de preenchimento: fuso único → IANA da capital; multi-fuso → capital ou maior população; território sem população permanente → fuso fixo mais próximo pela longitude; território sem IANA próprio → o do vizinho com as mesmas regras; Antártida → `Antarctica/McMurdo`.
  6. Recalculado **incondicionalmente** a cada geração, inclusive para mídia com sugestão decidida (CR-01) — antes ficava congelado no valor da última rodada em que a sugestão ainda estava pendente.
  7. O sinal de "fuso conhecido" é `tz_estimado IS NOT NULL`, **nunca** a diferença entre `data_capturada` e `data_capturada_utc`.
- **Saídas:** `MediaFile.tz_estimado`. No catálogo real: `America/Sao_Paulo 11.467`, `America/Santiago 2.322`, `Africa/Accra 1.901`, `Asia/Bangkok 1.293`, `America/New_York 1.214`, `America/Argentina/Buenos_Aires 1.042`.
- **Degradação/falha:** país desconhecido ou ausente → `None`, sem erro.
- **Estado:** pronto como estimativa. **Nenhum código consome `tz_estimado`** além da gravação — a conversão de fuso prevista é da fase 11.
- **Testes que provam:** `tests/test_timezones.py::test_cobre_todos_os_paises_de_paises_pt`, `::test_todo_valor_e_identificador_iana_valido`; `tests/test_suggestion_engine.py::test_tz_estimado_de_gps_proprio`, `::test_tz_estimado_de_pais_herdado`, `::test_tz_estimado_none_sem_pais_conhecido`, `::test_tz_estimado_atualiza_ao_regenerar_sugestoes`, `::test_tz_estimado_atualiza_mesmo_com_sugestao_decidida`.
- **Decisões:** D-038 (dois instantes, e `tz_estimado` como saída).
- **Arquivos:** `fotoorganizer/geolocation/timezones.py:25-305`, `fotoorganizer/classification/engine.py:411-462`, `fotoorganizer/models/catalog.py:218-232`.

---

### F-I28 — Duplicatas visuais (phash + BK-tree)
- **Propósito:** encontrar a mesma imagem em versões diferentes — reexport, recompressão, edição leve, recorte pequeno — sem comparar todo mundo com todo mundo.
- **Gatilho:** job `duplicatas` (`POST /api/duplicatas/detectar`).
- **Entradas:** todas as `MediaFile` com `tamanho > 0`.
- **Regras de negócio:**
  1. `phash` de 64 bits (`imagehash.phash`, DCT sobre 32×32), em hex, gravado em `hash_perceptual`. Calculado **só para quem ainda não tem** e **só se não houver `erro_leitura`**.
  2. Fonte preferida: a **miniatura em cache** (`thumb_cache.get(hash_rapido)`); depois o original. RAW abre pela miniatura embutida do libraw.
  3. BK-tree com distância de Hamming (`(a ^ b).bit_count()`); a busca só desce ramos com `d - max_dist <= dist_filho <= d + max_dist`.
  4. `LIMIAR_VISUAL = 8`: distância 0 é `CONTEUDO`, 1..8 é `VISUAL`.
  5. Ordem de precedência ao classificar um grupo: `VARIANTE` → `SEQUENCIA` → `CONTEUDO` → `VISUAL`.
  6. `EXATO` vem antes, por SHA-256, com `_completar_sha256` calculando o hash completo **só** para candidatos agrupados por `(tamanho, hash_rapido)` com ≥ 2 membros — nunca para o acervo inteiro.
  7. Cada grupo exato mantém **1 representante elegível** na passada de phash, para que uma recompressão da mesma foto agrupe com ele em vez de ficar órfã.
  8. **Só grupos EXATO** recebem resolução automática: bytes idênticos não deixam ambiguidade sobre o conteúdo, só sobre qual caminho é a referência. Os demais dependem de julgamento sobre o conteúdo e ficam `INDEFINIDO`.
  9. Desempate automático (`escolher_principal_automatico`): fonte própria antes de externa → caminho mais organizado (mais segmentos) → nome descritivo antes de genérico (`IMG_1234`) → mais metadado conhecido → `id` menor (estabilidade entre execuções).
  10. Redetecção preserva **só decisão humana**: `resolvido_automaticamente` **não conta** — se contasse, um grupo EXATO travaria no tamanho de quando foi criado e uma terceira cópia idêntica nunca se juntaria a ele.
  11. **Nada é excluído.** A detecção é somente leitura sobre os arquivos.
- **Saídas:** `duplicate_groups` + `duplicate_members`; stats por nível. No catálogo real: `EXATO 200 · CONTEUDO 61 · VISUAL 619 · SEQUENCIA 304 · VARIANTE 164`.
- **Degradação/falha:** imagem indecodificável → `calcular_phash` devolve `None` e a mídia fica fora do agrupamento por phash; `sha256_full` com `OSError` → `warning` e segue.
- **Estado:** **parcial.** ⚠️ M4: `duplicates/phash.py:97` abre a imagem **sem `exif_transpose`**, enquanto `thumbnails/generator.py:51` aplica — duas cópias de uma foto retrato (uma com miniatura em cache, outra sem) produzem phashes diferentes e **não agrupam**. A docstring de `calcular_phash` ("o resultado é o mesmo, a leitura é menor") é falsa nesse caso.
- **Testes que provam:** `tests/test_duplicates.py::test_distancia_hamming`, `::test_bktree_busca_por_distancia`, `::test_bktree_payloads_iguais_agrupados`, `::test_deteccao_exato_e_conteudo`, `::test_deteccao_nao_modifica_arquivos`, `::test_sha256_calculado_so_para_candidatos`, `::test_redeteccao_preserva_decisao`, `::test_grupo_exato_e_resolvido_automaticamente`, `::test_nova_copia_identica_se_junta_a_grupo_resolvido_automaticamente`, `::test_decisao_humana_substitui_resolucao_automatica`, `::test_desfazer_reverte_resolucao_automatica`, `::test_grupo_conteudo_nao_e_resolvido_automaticamente`, `::test_resolucao_prefere_fonte_propria_sobre_externa`, `::test_resolucao_prefere_caminho_mais_organizado_em_empate_de_fonte`, `::test_resolucao_prefere_nome_descritivo_sobre_generico`, `::test_resolucao_desempata_por_id_e_e_estavel_a_ordem_de_entrada`, `::test_resolucao_prefere_quem_sabe_mais_antes_de_cair_no_id`, `::test_riqueza_nao_atropela_os_criterios_anteriores`, `::test_principal_herda_o_metadado_que_so_a_versao_tinha`, `::test_mesma_foto_em_duas_fontes_conta_n_fontes`, `::test_bytes_recuperaveis`.
- **Decisões:** D-042/D-046 (empilhamento de capturas irmãs), D-070 (UI de VARIANTE avisa ao excluir RAW ou JPEG).
- **Arquivos:** `fotoorganizer/duplicates/phash.py:21-97`, `fotoorganizer/duplicates/detector.py:50,120-291`, `fotoorganizer/duplicates/resolucao.py:17-68`, `fotoorganizer/security/hashing.py:20-38`.

---

### F-I29 — Rajadas (SEQUENCIA)
- **Propósito:** reconhecer uma rajada como **escolha do melhor frame**, não como duplicata — apresentar como duplicata induziria a descartar o melhor frame.
- **Gatilho:** job `duplicatas`, dentro de `_grupos_por_phash`.
- **Entradas:** os membros de um grupo de phash: `data_capturada`, `(make, model)`.
- **Regras de negócio:**
  1. `GAP_RAJADA = timedelta(seconds=10)`: **todos** os frames consecutivos a ≤ 10 s um do outro.
  2. Exige **uma só câmera** no grupo, e ela não pode ser `(None, None)`.
  3. **Sem `data_capturada` em algum membro, não se afirma rajada** — não se supõe.
  4. **Rajada tem precedência sobre os dois níveis de phash**: até phash idêntico (cena estática em burst) não é cópia se veio da mesma câmera em segundos.
  5. Mas **perde para VARIANTE**: um par RAW+JPEG é sempre da mesma câmera no mesmo segundo e casaria como rajada — e "rajada" convida a escolher o melhor frame, que ali não é a pergunta.
  6. O nível `SEQUENCIA` **não** recebe resolução automática: qual frame é o melhor é julgamento humano.
  7. O subsegundo (`Composite:SubSecDateTimeOriginal`) existe justamente para desempatar a ordem dentro da rajada, onde seis fotos dividem o mesmo segundo.
- **Saídas:** `DuplicateGroup(nivel=SEQUENCIA)` com membros `INDEFINIDO`. No catálogo real: **304 grupos**.
- **Degradação/falha:** falta de data ou câmera → não é rajada, cai em CONTEUDO ou VISUAL.
- **Estado:** pronto como detecção. **Rajada é agrupamento pronto que a classificação ignora** (`docs/INVENTARIO_DE_SINAIS.md` §7): alimenta só a tela de duplicatas.
- **Testes que provam:** `tests/test_duplicates.py::test_rajada_mesma_camera_vira_sequencia`, `::test_phash_identico_em_rajada_tambem_e_sequencia`, `::test_fotos_parecidas_de_cameras_diferentes_seguem_visuais`, `::test_parecidas_com_horas_de_distancia_nao_sao_rajada`, `::test_sem_data_de_captura_nao_afirma_rajada`, `::test_variante_vence_rajada_na_classificacao`; `tests/test_exiftool_extractor.py::test_subsegundo_desempata_rajada_sem_mudar_a_hora`.
- **Decisões:** n/a.
- **Arquivos:** `fotoorganizer/duplicates/detector.py:52,55-65,225-236`.

---

### F-I30 — Variante de revelação (RAW + JPEG)
- **Propósito:** não pedir que o dono escolha entre o negativo e a cópia de trabalho — `IMG_1234.CR3` e `IMG_1234.JPG` são o **mesmo clique**, e ele quase sempre quer os dois.
- **Gatilho:** job `duplicatas`, dentro de `_grupos_por_phash`, **antes** do teste de rajada.
- **Entradas:** os membros do grupo: `nome`, `extensao`.
- **Regras de negócio:**
  1. Todos os membros com o **mesmo nome base** (`Path(nome).stem.lower()`, um único valor no conjunto).
  2. **Pelo menos duas extensões distintas** no grupo.
  3. **Pelo menos uma delas em `RAW_EXTENSIONS`.**
  4. Casar por nome funciona aqui e não funcionaria entre fotos quaisquer: as duas gravações do mesmo disparo saem com o mesmo número de série do arquivo.
  5. Duas cópias do mesmo `.CR3` em pastas diferentes **não** são variante (exige extensões diferentes) — continuam caindo em `CONTEUDO`, que é onde devem cair.
  6. Testado **antes** da rajada, senão o par casaria como rajada e a interface convidaria a escolher o melhor frame.
  7. Nível `VARIANTE` não recebe resolução automática.
- **Saídas:** `DuplicateGroup(nivel=VARIANTE)`. No catálogo real: **164 grupos**.
- **Degradação/falha:** n/a — o teste é puro sobre nomes e extensões.
- **Estado:** pronto.
- **Testes que provam:** `tests/test_duplicates.py::test_raw_e_jpeg_do_mesmo_clique_sao_variante_nao_duplicata`, `::test_duas_copias_do_mesmo_raw_nao_sao_variante`, `::test_jpeg_e_png_sem_raw_nao_e_variante`, `::test_nomes_base_diferentes_nao_sao_variante`, `::test_variante_vence_rajada_na_classificacao`.
- **Decisões:** D-070 (a UI avisa antes de excluir RAW ou JPEG de um grupo VARIANTE).
- **Arquivos:** `fotoorganizer/duplicates/detector.py:68-92,228-233`, `fotoorganizer/metadata/purepython.py:45`.

---

### F-I31 — Advisor de cluster por GenAI
- **Propósito:** dar uma opinião sobre a sessão que a cascata determinística **não** resolveu — nunca sobre as que ela resolveu.
- **Gatilho:** job `sugestoes`, `_consultar_advisor`, **apenas** para sessão `neutra` e **apenas** quando o advisor foi construído.
- **Entradas:** `ClusterInfo(pastas, exemplos_arquivos[:8], inicio, fim, n_fotos, lugares)`.
- **Regras de negócio:**
  1. **Gate**: `[privacidade] servicos_externos = true` no TOML, mais a lib `anthropic` instalada (`pip install -e ".[llm]"`), mais credencial no ambiente. Sem qualquer um → `None`, 100% local.
  2. **Só metadados saem**. Payload exato, serializado com `ensure_ascii=False`: `{"pastas": [...], "exemplos_de_arquivos": [até 8 nomes], "periodo": {"inicio", "fim"}, "quantidade_de_fotos": int, "lugares_geocodificados": [até 5]}`. **Nunca a imagem.**
  3. Modelo `claude-sonnet-5`, `max_tokens=1024`, `thinking={"type":"disabled"}` explícito (no Opus 5 o padrão passou a ser pensar, e `max_tokens` cobre raciocínio **mais** resposta — 1024 truncaria o JSON no meio).
  4. `output_config` com JSON Schema estrito: `categoria ∈ {Viagens, Eventos, Família} | null`, `evento: string | null`, `justificativa: string`; `additionalProperties: false`, todos `required`.
  5. System prompt manda **devolver nulo quando os metadados não bastarem — "nunca invente"**.
  6. Escolha do modelo **medida**: em 104 clusters reais, Haiku 4.5 afirmava categoria onde Opus recusava em ≥ 19 de 31 discordâncias; Sonnet 5 cai nesse padrão 7 vezes.
  7. `categoria == "Viagens"` **promove a sessão a viagem** e cria `Trip`: sem isso, um "Viagens" do LLM só preenchia `categoria` e a sessão nunca aparecia na aba Viagens. Rótulo: `evento or pais_dominante or periodo_curto()` — **nunca vazio**.
  8. Resultado vira evidência origem `llm`, score **0.55** — abaixo de qualquer evidência determinística, e sempre sujeito a revisão humana.
  9. Justificativa prefixada `"LLM (apenas metadados): "`.
  10. `NullAdvisor` é o padrão: `local = True`, sempre `None`. `ClaudeAdvisor.local = False` — **é isso que a UI usa para indicar envio externo**.
- **Saídas:** `AdvisorResult(categoria, evento, justificativa)`; evidência `llm`; possivelmente um `Trip`/`Event`.
- **Degradação/falha:** rede/auth/limite → `warning` + `None`; `stop_reason == "refusal"` → `info` + `None`; JSON inválido → `warning` + `None`. **A geração nunca cai** — a sessão simplesmente fica sem rótulo.
- **Estado:** pronto e **desligado por padrão**. Zero evidências `llm` no catálogo real — é resíduo por construção.
- **Testes que provam:** `tests/test_suggestion_engine.py::test_advisor_llm_apoia_sessao_neutra`, `::test_advisor_llm_promove_sessao_neutra_a_viagem`, `::test_advisor_llm_viagem_sem_nome_usa_pais_dominante`, `::test_advisor_nulo_nao_opina`; `tests/test_cascata_llm_pasta.py::test_advisor_de_cluster_vence_na_categoria`.
- **Decisões:** D-004 (IA embarcada é superfície de produto, com três restrições), D-022 (Opus 5 com `thinking` desligado), D-047 (o resíduo é 39% das sessões), D-048/D-049 (Haiku inventa onde Opus recusa), D-059/D-060 (Sonnet 5 medido e adotado).
- **Arquivos:** `fotoorganizer/classification/advisor.py:29-176`, `fotoorganizer/classification/engine.py:530-531,705-742`, `fotoorganizer/server/jobs.py:335-346`, `fotoorganizer/classification/confidence.py:40`.
- **⚠️ Divergência M2:** `ClusterInfo.pastas` recebe `media.pasta`, que é o **caminho absoluto** (`scanner.py:441`), enquanto `docs/PRIVACIDADE.md` promete "nomes de pastas".

---

### F-I32 — Classificação de pasta por GenAI
- **Propósito:** preencher cidade/país/categoria/evento em pastas que a hierarquia determinística, o GPS e o advisor de cluster já não resolveram — sob **dois consentimentos**, com custo mostrado antes de gastar e aprovação explícita antes de valer.
- **Gatilho:** rotas `GET|PUT /api/genai-pasta/config`, `GET /api/genai-pasta/candidatas`, `POST /api/genai-pasta/estimar-custo`, `POST /api/genai-pasta/rodar`, `GET /api/genai-pasta/propostas`, `POST /api/genai-pasta/aprovar` — o assistente de 6 etapas (`gate → candidatas → custo → rodando → revisao → concluido`, mais `erro`; ver F-U12 e `06-UI.md` §3.2) da tela.
- **Entradas:** a lista de pastas que o dono confirmou no passo 1.
- **Regras de negócio:**
  1. **Gate de DOIS consentimentos**: `servicos_externos` (chave mestra, TOML) **E** `classificacao_pasta_genai` (opt-in próprio, `application_settings`, gravável pela UI). Um só não basta — este recurso **não pega carona** no consentimento dado ao advisor de cluster. Gate fechado → HTTP 409 com mensagem literal do Copywriting Contract.
  2. **Pré-filtro D-01**: o dono nunca digita nada — o sistema lista sozinho toda pasta com `categoria` **ou** `cidade/país` vazios. `cidade_pais` é **um campo lógico** (basta um resolvido). Duas consultas agregadas, **nunca uma por pasta**. `MediaFile.organizavel` filtra **os dois lados**: evidência presa a miniatura não pode "resolver" um campo.
  3. **Reconciliação**: pasta pedida que já saiu da lista de candidatas (o catálogo mudou entre passos) é **ignorada**, não vira erro.
  4. **Allowlist literal** — `PastaPayload` é tudo que pode atravessar a fronteira, e o corpo é montado **campo a campo por atribuição explícita**, nunca por serialização genérica: `{pasta, n_fotos, periodo, campos_a_preencher, ja_conhecido}`. **Exatamente cinco chaves.** Nunca a imagem, nunca um byte de imagem, nunca miniatura.
  5. **Custo antes de gastar (D-79)**: a prévia usa contagem **local**, deliberadamente conservadora (`3,0 caracteres/token`, abaixo da razão nominal de ~4, para compensar a subcontagem conhecida em PT-BR e JSON). `$2,00`/MTok de entrada, `$10,00`/MTok de saída, câmbio de referência fixo `5,0`. O teto de saída é o **mesmo `max_tokens`** que o payload real leva. `messages.count_tokens` **transmite o payload**, então só roda **depois** da confirmação, e o número exato vai para o resumo pós-execução, não para a prévia.
  6. Modelo `claude-sonnet-5`, `max_tokens = 16000`, `thinking` desabilitado. **UMA chamada para a lista inteira** (D-03) — sem laço de lote, sem chamada por pasta.
  7. System prompt: `null` é a resposta **válida e preferida**; só proponha campos em `campos_a_preencher`; nunca proponha campo que aparece em `ja_conhecido`; justificativa de uma frase em português; responda TODAS as pastas com a grafia exata.
  8. **Filtros sobre a resposta** (a obediência do modelo nunca é pré-requisito de segurança): pasta que o modelo inventou → descartada em silêncio; resposta com os quatro campos `null` → não vira proposta; campo já conhecido → zerado mesmo que respondido.
  9. **Persistência guarda por CAMPO**: campo já preenchido nunca é sobrescrito, mesmo por proposta nova e mesmo divergente. Linha `origem == "manual"` é **inteiramente intocável**.
  10. **Só `status == 'aprovada'` entra na cascata.** `aprovar` marca as listadas e **descarta** as demais; `descartar` só muda status — **nenhuma linha é apagada em nenhum caminho** (invariante 8).
  11. Entrada na cascata em **três pontos, todos como último degrau**: `pais`/`cidade` acima da vizinhança e abaixo da hierarquia determinística; `evento` só quando não há evento de sessão; `categoria` só quando o advisor não decidiu. Origem `llm_pasta`, **chave separada** de `llm` — a Revisão precisa distinguir as duas.
  12. Score `llm_pasta = 0.55`, **medido** (D-081) contra a verdade determinística do próprio catálogo: categoria 2/2, cidade/país recusou 2/2 (`null`, comportamento seguro), **zero erros**. Preliminar — amostra de 4 pastas.
  13. `propostas_pendentes` **não exige o gate**: o dono pode ter desligado o recurso e ainda precisar rever o que já pagou.
  14. Revogar impede sessões **novas**, não desfaz o que já foi aprovado.
- **Saídas:** linhas em `pasta_classificacoes_genai`; propostas achatadas **por campo** (`valor_antes` sempre `None`); `custo_real` quando disponível; evidências `llm_pasta` na geração seguinte.
- **Degradação/falha:** gate fechado → 409; classificador escapa do contrato never-crash → `ClassificacaoIndisponivel` → **HTTP 502 com cópia amigável, e o servidor continua respondendo**; `contar_exato` falha → `custo_real = None` e a UI cai no fallback de estimativa; classificador local/nulo → sessão vazia com custo zero, sem sequer resolver o cliente.
- **Estado:** pronto e **desligado por padrão**. No catálogo real: 3 linhas, todas `status='proposta'` — nenhuma aprovada, logo **nenhuma evidência `llm_pasta` existe hoje**.
- **Testes que provam:** `tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem`, `::test_modelo_e_thinking`, `::test_uma_chamada_para_muitas_pastas`, `::test_falha_nunca_derruba`, `::test_ignora_pasta_que_nao_foi_pedida`, `::test_resposta_incerta_nao_vira_proposta`, `::test_nao_propoe_campo_ja_conhecido`, `::test_nula_e_o_padrao`; `tests/test_candidatas_e_custo_genai.py::test_candidata_pasta_sem_categoria`, `::test_candidata_pasta_sem_cidade_pais`, `::test_pasta_completa_nao_e_candidata`, `::test_pasta_ja_classificada_nao_e_candidata`, `::test_candidata_ignora_evidencia_de_midia_nao_organizavel`, `::test_pasta_so_com_nao_acervo_nao_e_candidata`, `::test_candidatas_ordenadas_por_pasta_deterministico`, `::test_custo_calcula_entrada_e_saida_pelas_constantes_de_preco`, `::test_teto_tokens_saida_vem_do_max_tokens_do_corpo`, `::test_entrada_exata_false_na_estimativa_local`, `::test_estimar_sessao_vazia_devolve_custo_zero`, `::test_contar_exato_cliente_que_levanta_devolve_zero`; `tests/test_pasta_classificacao_genai.py::test_nunca_sobrescreve_campo_ja_preenchido`, `::test_linha_manual_nao_e_tocada`, `::test_so_aprovada_e_lida_pela_cascata`, `::test_descartar_nao_apaga_linha`, `::test_conhecidas_cobre_todos_os_status`; `tests/test_api_genai_pasta.py::test_config_tudo_desligado_por_padrao`, `::test_habilitar_com_mestre_desligado_devolve_409_com_mensagem_exata`, `::test_candidatas_com_gate_desligado_devolve_409_sem_chamar_classificador`, `::test_rodar_com_gate_desligado_devolve_409_e_nada_e_gravado`, `::test_gate_aberto_rodar_grava_propostas_e_separa_sem_resposta`, `::test_aprovar_marca_aprovadas_e_descarta_demais_sem_apagar_linha`, `::test_rodar_com_cliente_que_falha_devolve_502_e_servidor_continua`; `tests/test_cascata_llm_pasta.py::test_evidencia_tem_origem_propria`, `::test_sobrevive_a_segunda_geracao`, `::test_proposta_nao_aprovada_nao_vira_evidencia`, `::test_determinismo_vence_o_llm`, `::test_evento_da_sessao_prevalece`, `::test_sem_proposta_o_resultado_e_identico`.
- **Decisões:** D-079 (prévia híbrida de custo), D-080 (opt-in em `application_settings`, não no TOML), D-081 (score medido).
- **Arquivos:** `fotoorganizer/classification/location_advisor.py:41-289`, `fotoorganizer/classification/candidatas_de_pasta.py:22-120`, `fotoorganizer/classification/custo_genai.py:26-146`, `fotoorganizer/server/genai_pasta.py:42-381`, `fotoorganizer/repositories/pasta_classificacao.py:53-141`, `fotoorganizer/server/app.py:1547-1596`, `fotoorganizer/classification/engine.py:886-900,998-1017,1072-1081`.
- **⚠️ Divergência M2:** `PastaPayload.pasta` recebe `MediaFile.pasta`, que é **caminho absoluto**, enquanto o módulo, a doc de privacidade e a UI prometem "nome da pasta". O teste-prova de privacidade verifica as cinco chaves e termos proibidos, mas **não pega** o caminho absoluto.

---

### F-I33 — Léxico de nomes por GenAI
- **Propósito:** ensinar à cascata o que ela não tem como saber: que "Pantanal" é um lugar aonde se viaja e "Quizomba" é uma festa.
- **Gatilho:** CLI `scripts/classificar_nomes.py --listar | --enviar | --mostrar | --corrigir "Pantanal=lugar"`. **Nunca roda dentro de `gerar()`.**
- **Entradas:** a lista de nomes distintos do acervo, já limpos de data por `separar_data`, incluindo **cada nível nomeável** do caminho (a cascata consulta da folha à raiz).
- **Regras de negócio:**
  1. Classifica o **NOME**, não a sessão — e é isso que o torna barato: são 100 nomes distintos no acervo inteiro, e uma consulta resolve todos.
  2. Quatro categorias: `lugar`, `ocasiao`, `pessoa`, `ruido`.
  3. **Privacidade**: sai da máquina apenas a **LISTA DE PALAVRAS** — nunca imagem, caminho completo, data, coordenada ou contagem. `--listar` mostra exatamente o que sairia, **sem enviar nada**.
  4. Exige `servicos_externos = true` **e** `--enviar` explícito. Sem isso, `LexicoNulo` responde "não sei" para tudo.
  5. Modelo `claude-opus-5`, `max_tokens=16000`, `thinking` desabilitado, lotes de `TAMANHO_DO_LOTE = 200`. Opus **apesar** de o plano recomendar Haiku para rotulagem barata: a recomendação vale quando a chamada é por sessão; aqui é **uma só para o acervo inteiro**, então o critério é qualidade da distinção lugar × ocasião, não custo.
  6. System prompt com exemplos reais do acervo e três regras: na dúvida entre lugar e ocasião, prefira "lugar" **apenas** quando for reconhecidamente topônimo; nome não reconhecido → classifique pela forma e diga isso; responda TODOS na mesma grafia.
  7. **Filtro sobre a resposta**: só nomes que vieram na pergunta e com categoria conhecida — a resposta não pode introduzir nome que o acervo não tem.
  8. O que já foi classificado **nunca é reenviado** (`LexicoRepository.faltantes`); correção manual (`origem='manual'`) **nunca** é sobrescrita pela máquina.
  9. Uso na cascata: **só na regra 6**. Lugar → VIAGEM nomeada pelo lugar; ocasião → EVENTO; se o nome extraído é desconhecido, `_opiniao_no_caminho` procura outro nível. Origem `lexico`, score **0.58** — acima de `llm` (a pergunta é muito mais estreita) e abaixo de `pasta` (a palavra é do dono, o significado é nosso).
  10. Medido: sem o léxico, a regra 6 mandou **Pantanal** (1d23h) e **Visconde de Mauá** (18 fotos) para Eventos — os dois são destino de viagem.
  11. Com o léxico desligado (padrão), `tipo_do_nome` devolve `None` e a cascata decide exatamente como decidia antes.
- **Saídas:** linhas em `nomes_classificados`; `DadosSessao.tipos_de_nome` lido do **cache local** em `gerar()`.
- **Degradação/falha:** rede/auth/limite → `warning` + `{}`; recusa → `info` + `{}`; JSON inválido → `warning` + `{}`. Nunca derruba a geração.
- **Estado:** pronto e **nunca executado neste catálogo** — a tabela `nomes_classificados` está vazia.
- **Testes que provam:** `tests/test_lexico.py::test_nome_de_lugar_vira_viagem_e_nao_evento`, `::test_nome_de_ocasiao_continua_evento`, `::test_sem_lexico_a_cascata_decide_como_sempre`, `::test_lexico_alcanca_o_lugar_um_nivel_acima_da_folha`, `::test_lexico_reconhece_ocasiao_em_nivel_intermediario`, `::test_lugar_nao_transforma_sessao_longa_em_evento`, `::test_so_o_que_falta_sai_da_maquina`, `::test_correcao_do_dono_sobrevive_a_reclassificacao`, `::test_manda_so_as_palavras`, `::test_resposta_nao_pode_inventar_nome`, `::test_falha_nunca_derruba_a_geracao`, `::test_lexico_nulo_e_o_padrao_e_nao_fala_com_ninguem`, `::test_categorias_sao_as_quatro_documentadas`, `::test_a_chave_e_o_nome_extraido_nao_o_segmento_cru`.
- **Decisões:** n/a explícita; racional no cabeçalho de `lexico.py:1-30` e em `docs/AGRUPAMENTO.md` §2 regra 6.
- **Arquivos:** `fotoorganizer/classification/lexico.py:39-197`, `fotoorganizer/repositories/lexico.py:20-60`, `fotoorganizer/grouping/classifier.py:66-76,142-160,244-262`, `scripts/classificar_nomes.py`, `fotoorganizer/server/jobs.py:212-217`.

---

### F-I34 — Cobertura de metadados (medição)
- **Propósito:** decidir **onde** vale ampliar a extração antes de escrever código — ampliar no escuro custa migração e teste sem ganho comprovado.
- **Gatilho:** CLI `.venv/bin/python scripts/cobertura_metadados.py <pasta> [...] [-n 400]`.
- **Entradas:** uma ou mais pastas reais; amostra estratificada por pasta, com semente fixa (reproduzível).
- **Regras de negócio:**
  1. **Somente leitura**: nenhum catálogo é escrito, nenhum arquivo é tocado.
  2. Usa o `PurePythonExtractor` diretamente, sem banco.
  3. Mede vazios em `data_capturada, make, model, lente, orientacao, largura, altura, gps_lat`.
  4. Regra que decorre da medição: **campo que já vem cheio não precisa de código novo, e campo que o arquivo não tem não se resolve com código nenhum.**
  5. Resultado registrado em `docs/COBERTURA_METADADOS.md`, com a correção explícita de 2026-07-26: a frase original extrapolava a amostra (300 fotos de três pastas de material de câmera ≠ o acervo).
- **Saídas:** relatório no terminal; tabela "antes × depois" no doc.
- **Degradação/falha:** n/a.
- **Estado:** pronto. Medição registrada: lente e orientação saíram de 195/300 vazios (65%, todos RAW) para 0; `make`/`model` em CR3 permanecem 99/300 **de propósito**; GPS 300/300 vazio **naquela fatia** (a câmera escreve o compartimento e não preenche).
- **Testes que provam:** n/a — é script de medição, não código de produção.
- **Decisões:** n/a; a medição embasou D-026 (exiftool vira padrão).
- **Arquivos:** `scripts/cobertura_metadados.py:1-27`, `docs/COBERTURA_METADADOS.md`.

---

### F-I35 — Inventário de sinais (medição)
- **Propósito:** separar três coisas que se confundem — o que o dado **oferece**, o que o catálogo **captura** e o que a cascata **usa para decidir**. Sinal capturado e não usado é trabalho pronto parado.
- **Gatilho:** medição manual registrada em `docs/INVENTARIO_DE_SINAIS.md` (2026-07-26).
- **Entradas:** 4.496 fotos com arquivo + 43.309 referências do Apple Fotos.
- **Regras de negócio / achados que viraram código:**
  1. `OffsetTimeOriginal` em 1.527 fotos, capturado e ignorado → virou `data_capturada_utc` (F-I04).
  2. `SubsecTimeOriginal` em 1.524 → entrou na precedência de data para desempatar rajada.
  3. 605 sidecars `.xmp`, 599 com curadoria, **nenhum lido** → virou F-I03.
  4. XMP embutido em 100% dos JPG; IPTC em 21% → viraram base bruta + `NAMESPACE_CURADORIA`.
  5. **Buraco de cobertura**: os 2.852 CR3 (63% do acervo) são ilegíveis pelo Pillow — qualquer sinal de curadoria via Pillow alcança no máximo 34%. Para eles, a curadoria vive nos sidecars.
  6. Nome de arquivo é **sinal morto neste acervo** (100% `ACM_NNNN`, zero datas) — mas as referências do Apple e material de celular têm outro padrão, com data no nome.
  7. Apple Fotos: 99.678 registros, e só GPS e data eram usados. `album` (25.304) e `pessoa` (12.760) são **intenção humana já declarada** — álbum virou F-I19; pessoa continua sem uso.
  8. Rajada é agrupamento pronto que a classificação ignora (F-I29).
  9. **Regra que vale para toda extração daqui em diante: um sinal ausente na amostra não é um sinal ausente no acervo.** A extração trata cada fonte como primeira classe mesmo quando os arquivos disponíveis hoje não a exercitam — e os testes cobrem isso com fixtures sintéticas.
  10. Conclusão de método: nenhum sinal isolado cobre o acervo, e é por isso que a decisão tem de ser por **acúmulo de evidências**, não por eleger um mecanismo.
- **Saídas:** `docs/INVENTARIO_DE_SINAIS.md`; e a lista do que ainda não é consumido.
- **Degradação/falha:** n/a.
- **Estado:** pronto como medição. **O que continua capturado e não usado**: `BodySerialNumber`, `LensSerialNumber`, `Artist`, ISO/abertura/obturador/focal, `Flash`/`WhiteBalance`/`SceneCaptureType`, `xmp:Rating`/`xmp:Label`, campos `crs:` de revelação, `pessoa` e `titulo`/`favorito`/`descricao` do Apple Fotos, e a rajada como sinal de classificação.
- **Testes que provam:** n/a — é documento de medição. O que virou código está coberto nos blocos correspondentes.
- **Decisões:** D-023 (colunas tipadas de direitos e autoria ficam para depois da medição), D-028, D-029, D-051.
- **Arquivos:** `docs/INVENTARIO_DE_SINAIS.md`, `scripts/diagnosticar_fontes.py`, `scripts/medir_heranca_gps.py`, `scripts/medir_impacto_da_data.py`.

---

### F-I36 — Reconhecimento facial
- **Propósito:** sugerir quem está na foto — **sempre como sugestão a confirmar**, com processamento local e embeddings criptografados.
- **Gatilho:** n/a — nenhum gatilho existe no código. `PrivacySettings.reconhecimento_facial` é `False` por padrão e **nunca é lido por nenhum código**.
- **Entradas:** `Path` da imagem (contrato `detectar(path)`).
- **Regras de negócio (contrato, não implementação):**
  1. Desativado por padrão; processamento **100% local**; nenhuma busca de identidade na internet.
  2. Embeddings gravados **criptografados** (chave no Keychain).
  3. Limiar conservador — e **quem decide se é "possível pessoa" é o chamador**, não o provider.
  4. Resultado é **sempre sugestão**; associar um nome exige confirmação humana.
  5. Estados previstos: `detectado → possível → confirmado/incorreto`.
  6. Apagar um perfil remove pessoa + embeddings + ocorrências (cascade).
  7. `FaceDetection(bbox normalizada 0-1, embedding, modelo)`.
- **Saídas:** nenhuma hoje. Tabelas `people`, `face_embeddings`, `face_occurrences` existem e estão **vazias**.
- **Degradação/falha:** `NullFaceProvider.detectar` devolve `[]` sempre. `similaridade` **está implementada de verdade** (cosseno), "pronta para quando houver embeddings reais".
- **Estado:** **stub.** O que existe: o `Protocol`, o provider nulo, a criptografia completa (`Fernet` + `KeychainKeyStore` com `subprocess` sem shell e `FileKeyStore` 0600 de fallback), as tabelas e a associação **manual** via `PeopleRepository`. O que **não** existe: qualquer detector, qualquer dependência de detecção no `pyproject.toml`, e qualquer leitura da flag de configuração.
- **Testes que provam:** `tests/test_faces_privacy.py::test_cifra_e_decifra_embedding`, `::test_chave_persiste_com_permissao_restrita`, `::test_cadastro_e_embedding_cifrado_em_repouso`, `::test_apagar_pessoa_remove_todos_os_vestigios`, `::test_associacao_manual_e_correcao`, `::test_stubs_sao_locais_e_inertes`, `::test_recursos_sensiveis_desligados_por_padrao`, `::test_remover_catalogo_preserva_fotos`.
- **Decisões:** decisão 2 do gate da fase 5 (`docs/PLANO_IA_E_PRODUTO.md` §8): **visão e rostos ficam locais, sem opção remota** — fecha a porta para qualidade de modelo de fronteira e mantém o invariante 4 sem asterisco.
- **Arquivos:** `fotoorganizer/faces/base.py:17-39`, `fotoorganizer/faces/stub.py:13-29`, `fotoorganizer/security/crypto.py:19-78`, `fotoorganizer/config/settings.py:63`, `fotoorganizer/repositories/people.py`.
- **Limitação declarada:** num app desktop a chave precisa estar acessível ao próprio app — quem tem a sessão desbloqueada tem acesso. A criptografia protege o banco **em repouso** (backup copiado, disco acessado por outra conta), não contra código rodando como o usuário. Proteções complementares reais: FileVault e senha de sessão.

---

### F-I37 — Análise visual (visão)
- **Propósito:** responder o que **só o conteúdo da imagem** responde — cena, qualidade, e a fronteira entre dois acontecimentos no mesmo dia, mesmo lugar e mesma câmera.
- **Gatilho:** n/a — nenhum chamador existe. `grep` por `VisionProvider` fora de `fotoorganizer/vision/` não encontra consumidor.
- **Entradas:** `Path` da imagem (contrato `analisar(path)`).
- **Regras de negócio (contrato, não implementação):**
  1. Dois modos previstos: local/privado (padrão) e serviço externo opcional, com opt-in explícito, indicação visual na UI e lista dos arquivos a enviar.
  2. **Rótulos visuais nunca afirmam cidade/vila específica** — só cena (praia, montanha, urbano…).
  3. `VisionResult(rotulos: dict[str, float], tem_pessoas, qualidade_baixa, tipo, fonte)`; `fonte` identifica o provedor para auditoria.
  4. Score de referência já reservado: origem `visao`, **0.30** — o mais baixo da tabela depois de `fs`.
  5. `local: bool` no Protocol é o que a UI usaria para indicar envio externo.
- **Saídas:** nenhuma hoje.
- **Degradação/falha:** `NullVisionProvider.analisar` devolve `None` sempre; "o motor de sugestões já trata a ausência de rótulos visuais".
- **Estado:** **stub.** A auditoria de IA identificou exatamente **três** situações em que nenhum metadado deste acervo distingue os casos: (1) dois acontecimentos no mesmo dia/lugar/câmera; (2) 2001–2018 sem GPS próprio nem doador para herdar — 58 câmeras no acervo e só a EOS 5D Mark IV com receptor embutido; (3) metadado corrompido (1.135 fotos sem modelo, datas no intervalo 2002–2100, scanner de filme gravando a data da digitalização). E recomendou: **consertar a régua antes de chamar modelo** — o corte da meia-noite e a confusão álbum/evento eram erros de regra, e resolvê-los pode reduzir o caso 1 a um resíduo pequeno demais para justificar o download.
- **Testes que provam:** `tests/test_faces_privacy.py::test_stubs_sao_locais_e_inertes`.
- **Decisões:** D-004 (regra determinística antes de modelo), decisão 2 do gate da fase 5 (visão fica local, sem opção remota). A distinção que a auditoria força: **agente embutido** (LLM que decide, com prompt e resposta em linguagem natural) é o que o princípio condena; **modelo local** (imagem → vetor) é determinístico, offline e não é agente — é extrator de característica, como o phash que o app já usa.
- **Arquivos:** `fotoorganizer/vision/base.py:17-44`, `fotoorganizer/vision/stub.py:12-20`, `fotoorganizer/classification/confidence.py:58`, `docs/AUDITORIA_IA.md`, `docs/PLANO_IA_E_PRODUTO.md` §3.
- **Custo, se fosse remoto** (aritmética, não medição): ~1.600 tokens de entrada por foto → $23 (Haiku) a $69 (Sonnet) por 10 mil fotos; $230 a $690 por 100 mil; metade com Batches. **Recomendação explícita: não fazer** — não pelo custo, mas porque cena e qualidade não decidem nada que a cascata já não resolva melhor.

---

## Lacunas e incertezas

1. **Reabertura de sugestão aprovada (F-I24).** O código **congela**: mídia decidida é pulada inteira. A memória do projeto e `plano-refactor.md:288-292` registram a decisão do dono de **reabrir**, explicitamente não implementada ("A1+A2 saíram sem flag e sem mecanismo de reabertura"). A reconstrução precisa saber se deve construir o mecanismo, e com qual gatilho (destino mudou? evidência mudou? `versao_logica` mudou?).

2. **Base de tempo mista (F-I16, M1).** `data_capturada` (parede local) e `mtime` (UTC naive) são intercambiáveis em `engine.py:469,501,571,585`. 33,3% de 53.967 registros com delta múltiplo exato de 1 h. Não sei se a correção é normalizar pelo `tz_estimado`, excluir só-mtime da linha do tempo, ou manter — e as três exigem cenário novo em `scripts/avaliar_agrupamento.py` antes do ajuste.

3. **`exif_transpose` ausente no phash (F-I28, M4).** Corrigir muda **todos** os `hash_perceptual` já gravados e invalida os grupos existentes. Não há medição de quantos grupos mudariam, nem decisão sobre invalidar o cache de phash.

4. **Caminho absoluto no payload da Anthropic (F-I31, F-I32, M2).** Não sei se a promessa de "nome da pasta" deve ser cumprida (enviar só o basename, perdendo o contexto hierárquico que ajuda o modelo) ou se a documentação deve ser corrigida. O teste-prova de privacidade não pega.

5. **Origens declaradas sem produtor.** `gps` (0.95), `geocoding_externo` (0.75), `visao` (0.30) e `agrupamento` (0.70) estão em `SCORES_REFERENCIA` e em `docs/CONFIANCA.md`, mas nenhum código as emite e nenhuma linha de `evidence` no catálogo real as usa. Não sei se são contrato futuro a preservar ou dívida a remover.

6. **`ConfigClassificacao` não é configurável em runtime (F-I18).** `engine.py:252` aceita o parâmetro, `server/jobs.py:225-233` nunca o passa. Os cinco limiares só mudam por código. Não sei se é intencional ou lacuna de UI.

7. **`versao_logica = "4.1"` é escrito e nunca lido.** D-043 registra o achado; `docs/CONFIANCA.md` promete que ele "permite re-gerar sugestões quando a metodologia evoluir e auditar com qual regra cada sugestão foi produzida". A leitura não existe.

8. **Subdivisão de acontecimento sem benchmark próprio (F-I21).** `docs/EVENTOS.md` declara: os 19 cenários (contagem real em `scripts/avaliar_agrupamento.py`, 2026-09-20; `docs/EVENTOS.md` ainda diz 17) de `avaliar_agrupamento.py` cobrem sessão, não subdivisão; não há script equivalente; e **não existe medição no acervo real** do caso positivo que motivou a feature — só timestamps sintéticos. Mudar `PISO`/`TETO`/`FATOR`/`MIN_FOTOS_EVENTO` hoje não tem rede de proteção equivalente.

9. **`/api/midia/{id}/preview` sem teste (F-I06).** Nem a rota, nem o diretório `previews`, nem `_PREVIEW_SIZE` são cobertos. `tests/test_thumbnails.py` só cobre `THUMB_SIZE`.

10. **`_MIN_FOTOS_SESSAO = 2` descarta sessões de 1 foto em silêncio (F-I16).** A foto continua catalogada e sem sessão, caindo em "Não classificadas". Não há log nem métrica, e não encontrei decisão registrada para esse número.

11. **`identidade_de_captura` (Live Photo) é capturada e não é usada (F-I01).** O comentário em `exiftool.py:490-500` diz que a correlação precisa saber que os dois arquivos são a MESMA captura para não tratar um como doador do outro a Δt zero — mas `FotoRef` não tem o campo e `correlacao.py` não o lê. O par `.heic`/`.mov` com fontes ou câmeras diferentes ainda pode herdar um do outro a Δt zero.

12. **Preços da API possivelmente vencidos (F-I32).** `PRECO_ENTRADA_USD_POR_MTOK = 2.0` / `PRECO_SAIDA_USD_POR_MTOK = 10.0` são o promocional de Sonnet 5 datado "até 31/08/2026" em `docs/PLANO_IA_E_PRODUTO.md` §3. Hoje é setembro de 2026. Se voltou a $3/$15, a prévia mostra 33% a menos do que o real — exatamente a falha que o fator conservador de tokens existe para evitar. Não consultei a rede para verificar.

13. **Curadoria capturada e subutilizada (F-I03, F-I35).** `xmp:Rating`, `xmp:Label` e os campos `crs:` de revelação são lidos e gravados, e **nada os consome**. O próprio código diz que usar palavras-chave para inferir LUGAR "fica para quando esse uso existir de fato". O eixo "qualidade e seleção" — ortogonal a onde e quando — não existe no produto.

14. **`_Draft` duplicado por campo não tem guarda (F-I23).** `evidencias[draft.campo] = evidencia` faz o último draft de um campo vencer no destino. Hoje nenhum caminho produz dois drafts do mesmo campo, mas um ramo novo que esqueça o `return` sobrescreveria em silêncio.

15. **Nenhuma medição de custo real com dinheiro (F-I32).** Todos os números são aritmética sobre tokens estimados. `contar_exato` alimenta o resumo pós-execução, mas não há registro de execução real com o total gasto — e `_custo_real` depende de acessar `classificador._client` (atributo privado).


---

# Parte C — Experiência do usuário (F-U)

# 02 — Funcionalidades vistas pelo usuário (contrato de experiência)

Cada bloco descreve **o que o usuário pede e o que a interface promete em
troca**. O motor por trás (scanner, metadados, classificação, operações) é
coberto pelos outros arquivos de `docs/reconstrucao/`; aqui está o contrato
de experiência: gatilho, o que a UI valida, a ordem dos passos, o que muda na
tela e o que acontece quando algo falha.

Template fixo de 10 campos em todos os blocos; `n/a` onde não se aplica.

Convenção de decisões: `D-0NN` com três dígitos refere-se a
`docs/DECISOES.md`. `D-0N` com dois dígitos (ex.: `D-01`, `D-07`) que aparece
em comentários de `EscritaExif.tsx` e `ClassificacaoPasta.tsx` é **decisão
local da UI-SPEC daquele plano**, não do arquivo global — a colisão de
numeração é real e está registrada nas Lacunas.

---

### F-U01 — Grade virtualizada e navegação por teclado

- **Propósito:** percorrer um acervo de centenas de milhares de registros sem
  travar a interface e sem precisar do mouse.
- **Gatilho:** tela `App` aba `Biblioteca` / rota `GET /api/midia?<filtros>&offset&limit` / atalhos `←` `→` `↑` `↓`, `espaço`, `Escape`, `[`, `]`
- **Entradas:** filtros ativos (`FiltrosMidia`), `zoom` (96–320 px, slider em `App.tsx:445-453`), largura do contêiner (medida por `ResizeObserver`).
- **Regras de negócio:**
  1. A grade carrega em páginas de 200 (`useMidia.ts:6`) e só renderiza as linhas visíveis + 4 de overscan (`PhotoGrid.tsx:50-55`).
  2. Cada célula é **miniatura cacheada**, nunca resolução completa (`Miniatura.tsx:76` → `api.thumbUrl`).
  3. O número de colunas é derivado da largura e do zoom, não fixo: `max(1, floor((largura-10)/(zoom+10)))` (`PhotoGrid.tsx:46`), e é reportado ao pai para que `↑`/`↓` andem exatamente uma linha (`PhotoGrid.tsx:47` → `App.tsx:198-199`).
  4. As setas só agem na aba Biblioteca, fora de campo de texto e fora do modo mapa (`App.tsx:193`).
  5. `espaço` abre/fecha o loupe apenas com uma foto selecionada (`App.tsx:204-206`); clique simples seleciona, duplo clique abre o loupe (`PhotoGrid.tsx:115-116`).
  6. A próxima página é buscada por dois gatilhos independentes: ao chegar a 3 linhas do fim visível (`PhotoGrid.tsx:71`) e ao selecionar um índice a menos de 20 do fim carregado (`App.tsx:164`).
  7. Trocar qualquer filtro invalida a seleção e fecha o loupe (`App.tsx:143-146`).
  8. A seleção por teclado sempre rola o item para dentro da janela (`PhotoGrid.tsx:58-64`).
- **Saídas:** célula selecionada ganha contorno de 2 px; o Inspetor à direita passa a descrever a foto; o degrau "no filtro" do rodapé atualiza (`App.tsx:501`).
- **Degradação/falha:** miniatura ausente ou indecodificável (404 em `/thumb`) → ⊘ + data + motivo, nunca imagem quebrada (`Miniatura.tsx:52-72`); célula além do fim carregado → espaçador vazio (`PhotoGrid.tsx:110`); nenhum resultado → estado vazio com "Adicionar pasta…" (`PhotoGrid.tsx:76-86`). **Servidor ocupado (409) não afeta a grade** — ela é só leitura.
- **Estado:** parcial. Falta distinguir "primeira carga" de "vazio" (a tela mostra o estado vazio enquanto a primeira página não chega, `PhotoGrid.tsx:76`); falta o cabeçalho de período fixo previsto em `docs/NAVEGACAO.md:80-83`.
- **Testes que provam:** `webapp/src/App.test.tsx::[ e ] recolhem os painéis laterais`; `webapp/src/App.test.tsx::Biblioteca com grade vazia: o estado vazio da grade também tem o botão`. **Setas, espaço, Escape e duplo clique não têm teste.**
- **Decisões:** `docs/NAVEGACAO.md` decisão 3 (rolagem contínua, não paginação — medido: 200 itens em 98 ms, 103.938 registros contados em 2 ms)
- **Arquivos:** `webapp/src/components/PhotoGrid.tsx:22-131`; `webapp/src/App.tsx:157-218,466-477`; `webapp/src/hooks/useMidia.ts:9-27`; `webapp/src/components/Miniatura.tsx:22-82`

---

### F-U02 — Loupe (vista ampliada)

- **Propósito:** olhar uma foto em tamanho grande, alternar ajustar↔100% e
  andar pela seleção sem voltar à grade — o gesto do Photo Mechanic.
- **Gatilho:** tela `Loupe` (overlay) / rota `GET /api/midia/{id}/preview` / atalhos `espaço` (abre e fecha), `Escape` (fecha), `←` `→` (navegam), duplo clique na célula
- **Entradas:** a lista de itens já carregada (`itens`), o índice selecionado.
- **Regras de negócio:**
  1. Abre em "ajustar à tela"; clique na área central alterna para 100% e de volta (`Loupe.tsx:63,83-87`).
  2. Pré-carrega as prévias de `index-1` e `index+1` para que a navegação seja instantânea (`Loupe.tsx:21-28`).
  3. Trocar de foto reseta o zoom e o estado de falha — a próxima não herda o erro da anterior (`Loupe.tsx:26-27`).
  4. A faixa de contato mostra ±12 vizinhas, clicáveis (`Loupe.tsx:32,92-112`).
  5. O cabeçalho anuncia os atalhos em texto: "espaço/Esc fecha · ←→ navegam · clique = 100%" (`Loupe.tsx:46-48`).
  6. Grade e loupe compartilham o mesmo cache de `useMidia` — navegar no loupe não refaz requisição de listagem (`useMidia.ts:8`).
- **Saídas:** overlay em tela cheia com nome, data em pt-BR, posição "N / M", a imagem e a faixa de contato.
- **Degradação/falha:** prévia que não carrega (404 em `/preview`, `app.py:858,865`) → ⊘ + "Não foi possível carregar esta imagem em alta resolução." + "O arquivo pode ter sido movido, renomeado ou corrompido desde a catalogação."; **o toggle de 100% é desligado** nesse estado, porque não há imagem para ampliar (`Loupe.tsx:63,65-76`). Cabeçalho e faixa continuam funcionando.
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Loupe.test.tsx::prévia que falha ao carregar mostra as duas frases e o glifo ⊘, sem o <img>`; `…::no estado de erro, clicar na área central não alterna o zoom`; `…::navegar para outro índice reseta o estado de falha`; `…::cabeçalho e rodapé continuam renderizando no estado de erro`
- **Decisões:** n/a (referência de classe: Photo Mechanic, `docs/DIRECAO_DE_ARTE.md:5`)
- **Arquivos:** `webapp/src/components/Loupe.tsx:15-114`; `webapp/src/App.tsx:204-209,511-518`

---

### F-U03 — Filtros e busca

- **Propósito:** reduzir o acervo ao conjunto sobre o qual se quer trabalhar,
  com um estado só e sempre visível.
- **Gatilho:** tela `App` aba `Biblioteca` (barra de controles) / rota `GET /api/midia` / atalho `n/a`
- **Entradas:** texto livre (nome ou caminho), ordenação (4 opções), alcance (3 opções), fonte, pasta, recorte vindo de outra aba, mês.
- **Regras de negócio:**
  1. Os sete eixos convergem para um único objeto `FiltrosMidia` (`App.tsx:108-120`), que é também a chave de cache (`useMidia.ts:11`).
  2. **Alcance** tem três valores com explicação em `title`: `tudo` ("seu acervo inteiro, com arquivo local ou sem — miniatura de outro app fica fora"), `organizaveis` ("acervo seu com o arquivo ao alcance agora"), `faltantes` ("o resto: no iCloud, em volume desmontado, ou miniatura de outro app") — `App.tsx:375-382`.
  3. Trocar de aba pelo botão limpa a busca; reclicar a aba já ativa **não** limpa (`App.tsx:227-233`).
  4. Abrir um grupo de Viagens ou uma lacuna do Panorama limpa a busca antes de aplicar o recorte (`App.tsx:292,303`), senão um recorte de 4.812 fotos apareceria como vazio por causa de uma busca antiga.
  5. Fonte e recorte aparecem como **chip removível**; alcance como segmentado; pasta como estado do botão na árvore; mês como "todo o período ✕" na régua.
  6. Controles que não agem na tela atual não aparecem: a barra inteira some no modo mapa (`App.tsx:366,395`), e a fonte só existe em Biblioteca/Revisão/Viagens (`App.tsx:68`).
  7. Validação de valores é do servidor: `alcance` ou `lacuna` desconhecidos respondem 422 (`app.py:631-633`).
- **Saídas:** grade, régua de tempo e degrau "no filtro" do rodapé recalculam juntos.
- **Degradação/falha:** filtro que não devolve nada → estado vazio da grade com a ação de adicionar pasta; volume desmontado → as fotos continuam listadas em `tudo` e somem de `organizaveis`, por desenho.
- **Estado:** parcial. `pasta`, `mes` e `alcance` não viram chip, contra a regra "um estado, uma aparência" de `docs/NAVEGACAO.md:58-60`. Os campos `camera`, `pais`, `cidade`, `palavra_chave` existem no contrato (`api.ts:142-145`) e no servidor (`app.py:622-625`) mas **nenhum controle os preenche**.
- **Testes que provam:** `webapp/src/App.test.tsx::clicar numa lacuna recorta a Biblioteca com chip removível`; `…::abrir uma viagem limpa a busca deixada de outra visita à Biblioteca`; `…::trocar de aba pelo botão limpa a busca deixada na Biblioteca`; `…::clicar na aba já ativa não apaga a busca recém-digitada`; `…::escolher uma pasta na lateral limpa a busca deixada na Biblioteca`
- **Decisões:** D-068 (o que conta como "organizável"); `docs/NAVEGACAO.md` decisão 2 (esquerda é lugar, topo é recorte)
- **Arquivos:** `webapp/src/App.tsx:108-120,317-456`; `webapp/src/api.ts:126-146,595-603`

---

### F-U04 — Recorte por pasta (árvore do disco)

- **Propósito:** responder "onde isso estava?" — para 225.914 registros num
  volume não montado, a pasta de origem é a única pista de lugar que sobrou.
- **Gatilho:** tela `Sidebar` → `ArvoreDePastas` / rota `GET /api/pastas?prefixo=` / atalho `n/a`
- **Entradas:** o caminho navegado (`aberta`), o caminho filtrando (`pastaAtual`).
- **Regras de negócio:**
  1. **Um nível por chamada**, nunca a árvore inteira (`ArvoreDePastas.tsx:7-18`) — com 371 mil registros são dezenas de milhares de pastas.
  2. **Navegar ≠ filtrar**: descer na árvore não muda a grade; só o botão explícito "ver na grade" aplica o recorte (`ArvoreDePastas.tsx:29-31,76-91`).
  3. O recorte é por **prefixo**: a pasta exata e tudo abaixo dela (`api.ts:140`).
  4. Reclicar o botão com o recorte ativo remove o filtro (`ArvoreDePastas.tsx:79`).
  5. Aplicar um recorte de pasta limpa a busca, zera a seleção e leva para a Biblioteca (`App.tsx:254-262`).
  6. Cada filho mostra o total **recursivo** e, quando menor, quantas são alcançáveis agora (`ArvoreDePastas.tsx:121-134`).
  7. Trilha de migalhas sempre presente, começando em "todos os discos" (`ArvoreDePastas.tsx:45-71`).
- **Saídas:** grade recortada; o botão da árvore vira "recorte ativo ✕".
- **Degradação/falha:** volume desmontado → "nenhuma alcançável agora" em vez de esconder a pasta ("o zero é a resposta, não um erro", `ArvoreDePastas.tsx:126-127`); pasta sem subpastas → "só arquivos aqui, sem subpastas" ou "nada nesta pasta" (`:98-104`); carregando → "carregando…" (`:96`). **Sem tratamento de erro de rede próprio.**
- **Estado:** parcial — a régua de tempo (F-U05) **não** respeita o recorte de pasta, porque `GET /api/midia/linha-do-tempo` não aceita o parâmetro (`app.py:676-684`).
- **Testes que provam:** `webapp/src/components/ArvoreDePastas.test.tsx::lista as raízes com a contagem recursiva`; `…::diz quando nada é alcançável agora, em vez de esconder a pasta`; `…::desce um nível ao clicar e oferece a trilha de volta`; `…::navegar não filtra a grade — só o botão explícito filtra`; `…::clicar de novo no recorte ativo remove o filtro`; `…::pasta sem subpasta diz isso em vez de ficar vazia`
- **Decisões:** D-061, D-062, D-063, D-064 (inventário por pasta entra antes do lançamento e como)
- **Arquivos:** `webapp/src/components/ArvoreDePastas.tsx:28-145`; `webapp/src/components/Sidebar.tsx:108-116`; `webapp/src/App.tsx:253-262`

---

### F-U05 — Âncora temporal (régua de meses)

- **Propósito:** alcançar 2015 sem rolar. Num acervo paginado de 200 em 200,
  chegar ao offset de março de 2019 rolando exigiria carregar tudo que veio
  antes.
- **Gatilho:** tela `App` aba `Biblioteca` (coluna à direita da grade) / rota `GET /api/midia/linha-do-tempo?<filtros>` / atalho `n/a`
- **Entradas:** os filtros atuais **menos** o mês escolhido.
- **Regras de negócio:**
  1. O salto é por **filtro**, não por rolagem (`LinhaDoTempo.tsx:16-24`).
  2. A régua mostra os meses do recorte, e por isso a consulta exclui `mes` da chave — senão escolher um mês faria os outros desaparecerem (`LinhaDoTempo.tsx:34-40`).
  3. Clicar no mês ativo limpa o filtro (`LinhaDoTempo.tsx:67`); há ainda "todo o período ✕" fixo no topo quando há mês ativo (`:48-56`).
  4. Cada mês exibe uma barra proporcional à sua contagem, com piso de 4 px — é a única pista de onde o acervo se concentra (`LinhaDoTempo.tsx:74-82`).
  5. Cabeçalho de ano aparece só quando o ano muda (`:59-65`).
- **Saídas:** grade recortada ao mês; o mês ativo destacado.
- **Degradação/falha:** sem meses no recorte → o componente inteiro **desaparece** (`LinhaDoTempo.tsx:42`). Sem estado de carregando e sem estado de erro.
- **Estado:** parcial. (a) `docs/NAVEGACAO.md:80-83` prevê também um "cabeçalho de período fixo no topo enquanto se rola" — não existe. (b) A consulta envia `pasta` e `ordenacao`, que o endpoint ignora (`app.py:676-684`), então **com recorte de pasta a régua mostra os meses do acervo inteiro**.
- **Testes que provam:** `webapp/src/App.test.tsx::a régua de tempo salta filtrando, e dá para voltar`. Sem arquivo de teste próprio.
- **Decisões:** `docs/NAVEGACAO.md` decisão 3 e ordem de implementação item 1
- **Arquivos:** `webapp/src/components/LinhaDoTempo.tsx:25-88`; `webapp/src/App.tsx:478-482`; `webapp/src/api.ts:625-631`

---

### F-U06 — Inspetor: metadados, sugestão e "por quê?"

- **Propósito:** responder, sobre a foto selecionada, o que o catálogo sabe e
  **por que** ele propõe o destino que propõe.
- **Gatilho:** tela `Inspector` (painel direito, aba Biblioteca) / rota `GET /api/midia/{id}` / atalho `]` recolhe o painel
- **Entradas:** a foto selecionada na grade.
- **Regras de negócio:**
  1. O detalhe só é buscado quando há seleção (`enabled: media !== null`, `Inspector.tsx:21`).
  2. Campo vazio **não vira linha vazia**: `Linha` retorna `null` (`Inspector.tsx:274`).
  3. Datas sempre em pt-BR, nunca ISO cru (`data.ts:1-12`).
  4. **A granularidade vai no rótulo**, não no valor: "Lugar", "Lugar · estimado", "Lugar · região estimada", "Lugar · país estimado" (`Inspector.tsx:266-271`) — um lugar herdado de horas atrás diz o país, não a cidade.
  5. Havendo sugestão, o bloco mostra o destino, o badge de confiança e a lista "Por quê?" com uma linha por evidência (campo, valor, nível, justificativa) — `Inspector.tsx:97-124`.
  6. O bloco de estimativa de GPS só aparece **quando não há sugestão**, para não repetir o que a evidência já conta (`Inspector.tsx:76-91`).
  7. Confiança nunca é número: só "Alta"/"Média"/"Baixa" (ou "Sem categoria"), e como quantidade de segmentos (`Confianca.tsx:14-19`).
- **Saídas:** painel de 288 px com thumb, nome, sete campos, blocos condicionais e as evidências.
- **Degradação/falha:** sem seleção → "Selecione uma foto para ver metadados, sugestão e evidências." (`Inspector.tsx:27-30`); sem sugestão → o bloco simplesmente não existe; `GET` que falha → o painel fica com os campos vazios, **sem mensagem de erro**.
- **Estado:** pronto (com a ressalva do erro silencioso de `GET`).
- **Testes que provam:** `webapp/src/components/Inspector.test.tsx::formata a data capturada em pt-BR, não o ISO cru`; `…::mostra o lugar mesmo quando a foto não tem coordenada própria`; `…::mostra de quem o lugar foi herdado, não só que foi`; `…::marca o lugar como estimado no rótulo, não só no texto`; `…::não repete a história da herança quando a evidência já a conta`; `…::foto sem lugar resolvido não inventa linha vazia`; `…::herança de horas anuncia o país, não a cidade`
- **Decisões:** D-017 (confiança como quantidade), D-025 (a janela da herança depende do que se herda), D-071 (badge "Sem categoria")
- **Arquivos:** `webapp/src/components/Inspector.tsx:17-128,266-286`; `webapp/src/components/Confianca.tsx:21-87`; `webapp/src/data.ts:2-12`

---

### F-U07 — Confirmar o tipo da imagem (captura / recebida / baixada)

- **Propósito:** deixar o usuário corrigir o detector sem que a correção seja
  desfeita em silêncio na próxima passagem do motor.
- **Gatilho:** tela `Inspector` (bloco `TipoDaImagem`) / rota `POST /api/midia/{id}/tipo` / atalho `n/a`
- **Entradas:** clique em "Confere", "Não, é foto" ou "desfazer".
- **Regras de negócio:**
  1. A interface **pergunta em vez de afirmar** enquanto `tipo_provisorio` for verdadeiro (`Inspector.tsx:131-136,164-191`).
  2. Só a conclusão de que **não** é foto merece pergunta: `tipo === "foto" && provisorio` não renderiza nada (`Inspector.tsx:161`) — perguntar em 5.071 de 5.601 fotos seria ruído (`:157-160`).
  3. Respondido, o bloco vira "X · classificado por você" com "desfazer", que devolve a decisão ao detector enviando `tipo: null` (`Inspector.tsx:193-208`).
  4. A resposta invalida detalhe, grade e panorama (`Inspector.tsx:149-151`).
  5. O botão fica desabilitado enquanto a mutação está em voo (`:175,183`).
  6. Tipo desconhecido é rejeitado pelo servidor com 422 (`app.py:825`).
- **Saídas:** o bloco troca de pergunta para afirmação; contagens do Panorama podem mudar.
- **Degradação/falha:** erro da mutação **não é exibido** — não há `onError` (`Inspector.tsx:146-153`).
- **Estado:** parcial (falta superfície de erro).
- **Testes que provam:** `webapp/src/components/Inspector.test.tsx::classificação provisória pergunta, em vez de afirmar`; `…::responder grava a palavra do usuário, não a do detector`; `…::classificação já confirmada não volta a perguntar`; `…::foto normal não ganha bloco de tipo`; `…::quem respondeu 'é foto' consegue voltar atrás`
- **Decisões:** D-066 (pasta acentuada em NFD no detector de tipo)
- **Arquivos:** `webapp/src/components/Inspector.tsx:138-209`; `webapp/src/api.ts:606-610`

---

### F-U08 — Metadados brutos do arquivo

- **Propósito:** ver tudo que estava gravado no arquivo — EXIF, GPS, IPTC,
  XMP, RAW — sem pagar por isso em toda seleção.
- **Gatilho:** tela `Inspector` → seção "Metadados do arquivo" / rota `GET /api/midia/{id}/metadados` / atalho `n/a`
- **Entradas:** clique no toggle.
- **Regras de negócio:**
  1. **Fechado por padrão e buscado só ao abrir** (`enabled: aberto`, `Inspector.tsx:220`) — "um JPEG editado traz dezenas de chaves XMP, e o inspetor é recarregado a cada seleção" (`:211-214`).
  2. Agrupado por namespace, com rótulo legível (`Inspector.tsx:243-258`).
  3. O total aparece ao lado do título depois de carregado (`:232`).
- **Saídas:** lista `chave / valor` por namespace.
- **Degradação/falha:** carregando → "lendo…" (`:235-237`); arquivo sem metadado → "Este arquivo não trouxe metadado nenhum." em vez de painel vazio (`:238-242`); erro de rede → nenhuma mensagem.
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Inspector.test.tsx::os metadados do arquivo só são lidos quando o painel abre`; `…::arquivo sem metadado diz isso, em vez de painel vazio`
- **Decisões:** D-021 (precedência XMP → IPTC → EXIF), D-026 (exiftool padrão quando instalado), D-027 (MakerNotes fora da base bruta)
- **Arquivos:** `webapp/src/components/Inspector.tsx:215-261`; `webapp/src/api.ts:109-118,605`

---

### F-U09 — Revisão de sugestões por grupo (aprovar / rejeitar / desfazer)

- **Propósito:** decidir o destino de milhares de fotos com um número de
  gestos que cabe numa sessão. A unidade de decisão é o **grupo de destino**,
  não a foto solta.
- **Gatilho:** tela `Review` (aba Revisão) / rotas `GET /api/sugestoes/grupos`, `GET /api/sugestoes`, `POST /api/sugestoes/acao` / atalhos `Enter`/`espaço` no cabeçalho do grupo
- **Entradas:** status (Pendentes / Aprovadas / Rejeitadas), fonte selecionada na lateral, grupo aberto.
- **Regras de negócio:**
  1. A tela nasce com **todos os grupos dobrados** (`Review.tsx:49-54`): no acervo real são 5.048 pendências em 10 destinos, e a linha por foto não distingue nada.
  2. As contagens e o total são **do banco**, não da página carregada (`Review.tsx:62-72,153-157`) — antes a tela dizia "200 em 3 grupos" para uma fila de 5.048 em 10.
  3. **"Aprovar N" age no grupo inteiro**: a tela manda o `destino`, o servidor resolve os ids (`api.ts:678-686`, `Review.tsx:237`). Sem isso, "Aprovar 597" aprovava as 85 da página.
  4. O cabeçalho lê `origem → destino` na mesma linha (`Review.tsx:201-211`) e avisa, **antes** da aprovação, "N com lugar estimado" e "N fora de alcance" (`:215-229`) — "sem isto o dono aprova 2.405 fotos de um disco desligado sem saber".
  5. O badge de confiança do grupo vira "Sem categoria" quando o destino é "Não classificadas" (`Review.tsx:231` + `sugestoes.ts:9-14`).
  6. Abrir um grupo busca até 200 fotos daquele destino; o que não coube ganha o botão "mostrar mais N · faltam M de T" (`Review.tsx:398,448-457`).
  7. Ações por linha: Aprovar / Rejeitar (status pendente) ou Desfazer (demais) — `Review.tsx:348-373`.
  8. Sugestões vizinhas com mesmo nome+data+câmera e `media_id` diferente ganham o selo com o nome da fonte (`Review.tsx:433-446,318-325`).
  9. Toda ação invalida o prefixo `["sugestoes"]`, recarregando grupos, contagens e páginas (`Review.tsx:80-81,89-90`).
  10. **Aprovar não move nada**: a dica do rodapé diz "o destino só sai do papel em Operações" (`App.tsx:43`).
- **Saídas:** contadores das três abas atualizam; o grupo muda de aba; o total na barra recalcula.
- **Degradação/falha:** fila vazia → "Nada aqui — gere as sugestões ou mude o filtro de status." (`:171-174`); grupo carregando → "carregando…" (`:426-428`); foto fora de alcance → `Miniatura` densa com ⊘ e o motivo no `title` (`:298-311`); **409 de "Gerar/atualizar sugestões" não aparece na tela** — a chamada não tem `.catch` (`:163`).
- **Estado:** parcial — falta a superfície de erro do disparo de job e falta qualquer marca de "sugestão reaberta por reprocessamento".
- **Testes que provam:** `webapp/src/components/Review.test.tsx::agrupa por destino em vez de listar tudo plano`; `…::abre e fecha o grupo pelo teclado, sem depender do mouse`; `…::Enter no botão Aprovar do grupo não fecha o cabeçalho junto`; `…::a contagem do grupo é a do banco, não a da página carregada`; `…::aprovar o grupo manda o destino, não os ids da página`; `…::o grupo diz de onde as fotos vêm — a metade que faltava do par`; `…::avisa quantas do grupo estão fora de alcance antes de aprovar`; `…::avisa quantas fotos do grupo têm lugar estimado`; `…::a linha diz por quê em vez de desenhar imagem quebrada`; `…::sugestões vizinhas com mesmo nome+data+câmera mostram o selo com o nome da fonte…`
- **Decisões:** D-018 (a unidade de decisão é o grupo), D-033 (foto fora de alcance continua visível com o motivo), D-071 ("Sem categoria")
- **Arquivos:** `webapp/src/components/Review.tsx:41-392,394-469`; `webapp/src/api.ts:273-303,644-686`; `webapp/src/sugestoes.ts:7-14`

---

### F-U10 — "Por quê?" de uma sugestão (evidências sob demanda)

- **Propósito:** toda sugestão responde por si, a um clique, com origem e
  justificativa de cada evidência.
- **Gatilho:** tela `Review` (botão de confiança na linha) e `Inspector` (sempre visível) / rota `GET /api/midia/{media_id}` / atalho `n/a`
- **Entradas:** clique no badge de confiança da linha.
- **Regras de negócio:**
  1. Em Revisão a busca é **sob demanda**: "63 linhas não podem disparar 63 requisições no carregamento" (`Review.tsx:471-472`).
  2. Reclicar fecha (`Review.tsx:341`); o botão tem `aria-expanded` (`:343`) e `title` nomeando o arquivo (`:344`).
  3. Cada evidência mostra nível (quantidade, não cor), campo, valor e justificativa (`Review.tsx:491-509`).
  4. Evidência com `origem === "llm_pasta"` ganha a pastilha **"IA · pasta"** numa cor própria, distinta do selo de colisão de fonte — "reusar a mesma cor faria uma proposta de IA parecer outra coisa" (`Review.tsx:495-503`).
  5. No Inspector as mesmas evidências aparecem sem clique, porque o painel já é sobre uma foto só (`Inspector.tsx:109-122`).
  6. O `score` numérico nunca é mostrado; só o rótulo (`Confianca.tsx:14-18`).
- **Saídas:** lista de evidências abaixo da linha.
- **Degradação/falha:** carregando → "carregando…" (`Review.tsx:480-482`); sugestão sem evidência → "Sem evidência registrada para esta sugestão." (`:483-489`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Review.test.tsx::o porquê é buscado só quando o usuário pergunta`; `…::evidência llm_pasta ganha a pastilha`; `…::evidência de outra origem não ganha pastilha`; `webapp/src/components/Inspector.test.tsx::sugestão 'Não classificadas' mostra 'Sem categoria', não 'Alta' (D-071)`
- **Decisões:** D-017, D-071, D-081 (score de `llm_pasta` = 0.55, preliminar)
- **Arquivos:** `webapp/src/components/Review.tsx:339-347,473-512`; `webapp/src/components/Inspector.tsx:109-122`; `webapp/src/api.ts:89-104`

---

### F-U11 — Editar o destino de uma sugestão

- **Propósito:** corrigir à mão o que o motor errou, sem precisar de uma
  segunda aprovação.
- **Gatilho:** tela `Review` (botão ✎ na linha) / rota `PATCH /api/sugestoes/{id}/destino` / atalhos `Enter` salva, `Escape` cancela
- **Entradas:** o novo caminho de destino, digitado.
- **Regras de negócio:**
  1. Edição **inline**, substituindo a linha; input com `autoFocus` (`Review.tsx:254-295,268`).
  2. Valor vazio (após `trim`) não salva (`Review.tsx:120-121`).
  3. Editar marca a sugestão como **editada** no servidor, então ela sai da aba "Pendentes" ao recarregar — "a correção já valeu, não precisa de uma segunda aprovação" (`Review.tsx:93-96`).
  4. Destino inválido responde 422 e a mensagem do servidor aparece **abaixo do campo**, sem travar a edição (`Review.tsx:105,276-280`; `app.py:1194`).
  5. Salvar invalida `["sugestoes"]` e fecha a edição (`Review.tsx:100-104`).
  6. Cancelar descarta o valor digitado (`Review.tsx:114-117`).
- **Saídas:** a linha volta ao modo leitura com o destino novo; o grupo recarrega.
- **Degradação/falha:** 422 do servidor tratado (acima); botão "Salvar" desabilitado durante o `isPending` (`:285`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Review.test.tsx::edita o destino inline e salva via PATCH`; `…::mostra a mensagem do servidor quando o destino editado é inválido (422)`; `…::cancelar a edição descarta o valor digitado`
- **Decisões:** n/a
- **Arquivos:** `webapp/src/components/Review.tsx:97-123,254-295`; `webapp/src/api.ts:657-658`

---

### F-U12 — Classificação de pasta por GenAI (assistente de 6 passos)

- **Propósito:** deixar um modelo externo propor categoria e cidade/país para
  pastas onde esses campos estão vazios — com consentimento explícito, custo
  antes do envio e revisão antes da gravação.
- **Gatilho:** tela `Review` → botão "Classificar pastas por IA…" → modal `ClassificacaoPasta` / rotas `GET|PUT /api/genai-pasta/config`, `GET /api/genai-pasta/candidatas`, `POST /api/genai-pasta/estimar-custo`, `POST /api/genai-pasta/rodar`, `GET /api/genai-pasta/propostas`, `POST /api/genai-pasta/aprovar` / atalho `Escape` fecha (exceto durante a chamada)
- **Entradas:** checkbox de consentimento; seleção de pastas; seleção de propostas a aprovar.
- **Regras de negócio:**
  1. **Gate de dois consentimentos**: `servicos_externos` (chave mestra, só no TOML, sem UI de escrita) **e** `classificacao_pasta_genai` (opt-in próprio, gravável aqui). Os dois precisam ser verdadeiros (`api.ts:464-472`; `ClassificacaoPasta.tsx:104,135-147`).
  2. Antes de habilitar, a tela declara o que sai da máquina: "o nome de cada pasta candidata e os metadados já catalogados (**nunca imagens**) são enviados ao Claude Sonnet 5 numa única chamada por sessão" (`:106-112`).
  3. Habilitar exige o **checkbox marcado**; o botão fica desabilitado sem ele (`:113-132`).
  4. As candidatas vêm de um pré-filtro: só pastas com categoria **ou** cidade/país vazios (`:182-185`). Nascem todas marcadas, com fraseologia **opt-out** ("Desmarque o que não quer incluir") — `:671-675`.
  5. O passo de custo mostra entrada estimada, teto de saída e total, sempre prefixados por "até", em BRL e USD, e afirma: **"Nada foi enviado ainda — os dois números acima são estimativas locais"** (`:284-317`). Estimativa é **local**, nunca um `count_tokens` real, que transmitiria o payload antes do consentimento (`api.ts:489-492`).
  6. Confirmado, a chamada é **uma só** e **não cancelável**: todo caminho de fechar é desligado no passo 3 (`:741,745,772`) e a tela mostra um relógio, não uma barra de progresso falsa (`:337-353,729-731`).
  7. A revisão é **por pasta**, com `antes:` / `depois:` por campo, justificativa a um clique (`ⓘ`), pastilha "IA · pasta" e confiança "Média" fixa (`:412-477`). Todas nascem marcadas.
  8. Pastas sem resposta confiável viram um resumo de **uma linha** com "Ver quais »" expansível — "Claude não teve segurança pra classificar. Nenhuma sugestão foi criada." (`:485-513`).
  9. Aprovar grava só as pastas marcadas **e descarta as demais que estavam em `proposta`** (`genai_pasta.py:374-381` → `pasta_classificacao.py:137-142`; não reaparecem na sessão seguinte); a conclusão mostra o **custo real** (contagem exata) ou o estimado com a ressalva "estimativa — contagem exata indisponível", nunca R$ 0,00 (`:538-595`).
  10. **Recuperação de sessão paga**: se a página recarregar depois de a chamada ter sido cobrada, o assistente reabre direto no passo de revisão a partir de `GET /api/genai-pasta/propostas` (`:624-654`).
  11. Aprovar não escreve destino nenhum: as propostas viram sugestões, que ainda passam pela Revisão — "As sugestões aparecem em Revisão na próxima geração de sugestões" (`:585-587`).
- **Saídas:** propostas aprovadas viram evidências `llm_pasta` nas próximas sugestões (visíveis com a pastilha "IA · pasta" em F-U10).
- **Degradação/falha:** chave mestra desligada → a tela explica e só oferece Cancelar (`:135-147`); zero candidatas → "Nenhuma pasta com categoria ou cidade/país vazios no catálogo atual." + Fechar (`:200-211`); gate fechado no servidor → 409 (`app.py:1556,1563,1570,1577`) exibido acima do passo; falha do modelo → 502 com a cópia pronta do contrato (`app.py:1581-1587`) e passo `erro` com Fechar / Voltar (`:357-382`); falha na consulta de recuperação não trava o assistente (`:647`).
- **Estado:** parcial. (a) O nível de confiança é **fixado em "média" no cliente** porque o endpoint não devolve nível por proposta (`:60-67`). (b) A cópia promete "nome da pasta" enquanto o backend envia o **caminho absoluto** — achado **M2** da auditoria de 2026-09-19 (`ClassificacaoPasta.tsx:107-108` × `genai_pasta.py:224-230`). (c) A mensagem de erro do servidor já vem com o prefixo "Não foi possível classificar:", que `PassoErro` reimprime — prefixo duplicado.
- **Testes que provam:** `webapp/src/components/ClassificacaoPasta.test.tsx::mestre desligado não oferece caixa`; `…::habilitar exige a caixa marcada`; `…::candidatas nascem todas marcadas`; `…::passo de custo mostra "até" no total`; `…::durante a rodada não há como fechar`; `…::erro do servidor vira a cópia do contrato`; `…::duas propostas da mesma pasta viram uma linha`; `…::resumo de sem-resposta é uma linha só`; `…::aprovar envia só as marcadas`; `…::fechar sem aprovar não chama aprovar`; `…::abre no passo 4 quando há proposta pendente`; `…::passo concluído mostra a frase de expectativa`
- **Decisões:** D-079 (prévia de custo híbrida), D-080 (onde mora o opt-in), D-081 (score 0.55 preliminar), D-004 (IA é superfície de produto com restrições), D-022/D-060 (Sonnet 5 no advisor)
- **Arquivos:** `webapp/src/components/ClassificacaoPasta.tsx:82-860`; `webapp/src/api.ts:464-528,701-718`; `webapp/src/components/Review.tsx:158-161,387-389`

---

### F-U13 — Duplicatas e survey de rajadas

- **Propósito:** decidir qual cópia é a principal comparando lado a lado —
  sem que nada seja excluído.
- **Gatilho:** tela `Duplicates` (aba Duplicatas) / rotas `GET /api/duplicatas`, `POST /api/duplicatas/detectar`, `POST /api/duplicatas/{id}/principal|ignorar|desfazer` / atalho `n/a`
- **Entradas:** filtro de nível, grupo selecionado, clique em "Manter esta" / "Melhor frame" / "Manter só esta".
- **Regras de negócio:**
  1. **Nada é excluído**: o usuário marca papéis para a fase de operações (`Duplicates.tsx:17-18`).
  2. Seis filtros de nível: Todos, Idênticos (`exato`), Mesmo conteúdo, Parecidos (`visual`), RAW + JPEG (`variante`), Sequências (`sequencia`) — `:8-15`.
  3. **`sequencia` e `variante` não somam bytes recuperáveis** (`:44-48`): nos dois casos o normal é manter todos os membros.
  4. O texto que orienta a decisão muda por nível (`:144-150`): rajada → "marque o melhor frame"; RAW+JPEG → "normalmente mantenha os dois; marcar uma exclui a outra do plano"; resolvido pelo algoritmo → "Cópia idêntica (SHA-256) — o algoritmo já marcou a principal. Escolha outra se discordar."
  5. Grupo resolvido automaticamente recebe um selo com `title` explicando a origem e convidando ao override (`:135-142`).
  6. O botão de RAW+JPEG carrega a consequência no `title`: "A outra versão sai do plano de cópia — continua no disco de origem, mas não vai para o destino organizado" (`:245-247`).
  7. A comparação usa a **prévia**, não a miniatura (`:225`), porque comparar exige ver.
  8. "Ignorar grupo" e "Desfazer" estão sempre disponíveis (`:152-165`).
  9. Trocar de filtro zera a seleção de grupo (`:58-61`).
- **Saídas:** borda verde + "✓ principal" no membro escolhido; membros ignorados a 50% de opacidade; a lista de grupos marca "decidido ✓" ou "resolvido automaticamente".
- **Degradação/falha:** nenhum grupo no filtro → "Nenhum grupo — rode a detecção." (`:118-122`); nenhum grupo selecionado → "Selecione um grupo para comparar lado a lado." (`:127-130`); prévia que falha → ⊘ + "imagem indisponível" com `title` explicando, **sem afetar os outros membros** (`:201,213-222`); job rodando → botão "Detectando…" desabilitado (`:75-79`); **409 do disparo não aparece** (sem `.catch`, `:74`).
- **Estado:** parcial (superfície de erro do disparo).
- **Testes que provam:** `webapp/src/components/Duplicates.test.tsx::grupo EXATO resolvido pelo algoritmo mostra rótulo distinto de decisão humana`; `…::grupo decidido por humano continua mostrando 'decidido ✓', sem o rótulo automático`; `…::único grupo nasce selecionado e explica a decisão automática, com override manual disponível`; `…::grupo VARIANTE (RAW+JPEG) orienta a manter os dois, não soma no total recuperável e o botão avisa a consequência`; `…::filtro 'RAW + JPEG' existe e isola só os grupos VARIANTE`; `…::membro cuja prévia falha mostra 'imagem indisponível'…`
- **Decisões:** D-070 (UI de duplicata VARIANTE avisa antes de excluir RAW ou JPEG), D-024 (registro que não é acervo é rebaixado, nunca apagado)
- **Arquivos:** `webapp/src/components/Duplicates.tsx:19-262`; `webapp/src/api.ts:659,721-740`

---

### F-U14 — Cards de viagem e evento

- **Propósito:** apresentar o agrupamento explicável do motor "do jeito que se
  mostra pra alguém" — com capa, período e contagem.
- **Gatilho:** tela `Trips` (aba Viagens) / rotas `GET /api/viagens?source_id`, `GET /api/eventos?source_id` / atalhos `Enter`/`espaço` no card
- **Entradas:** fonte selecionada na lateral; clique no card ou no badge "Mapa".
- **Regras de negócio:**
  1. Clicar no card abre o grupo na Biblioteca, vista **lista** (`Trips.tsx:65,73`; `App.tsx:302-307`).
  2. O **badge "Mapa"** abre direto na vista de mapa, e é sempre visível — não só no hover (`Trips.tsx:113,199-209`). Existe porque o mapa "existe mas não tinha nenhuma pista visível de que existe antes de já saber procurar".
  3. O badge é **irmão** do `role="button"` do card, nunca descendente: botão dentro de `role="button"` é anti-padrão ARIA e faz o leitor de tela anunciar duplicado (`Trips.tsx:141-146`). Consequência: nada de `stopPropagation`.
  4. O **selo de origem** ("Álbum" / "Evento detectado") aparece só quando dois cards da **mesma seção Eventos** colidem no nome — sinal de ambiguidade, não decoração permanente (`Trips.tsx:91-100,194-198`). Comparação sem caixa e sem espaço nas pontas.
  5. A capa é **miniatura cacheada** do tamanho do card, nunca a prévia do loupe (`Trips.tsx:162`).
  6. "Carregando" e "realmente vazio" são estados distintos (`Trips.tsx:38-45`).
  7. O filtro de fonte vale nesta tela (`Trips.tsx:8-9`) — antes ficava visível e inerte.
- **Saídas:** grade de cards responsiva (mínimo 260 px), separada em Viagens e Eventos.
- **Degradação/falha:** consultas pendentes → "carregando…" (`:49-53`); catálogo vazio → "Nenhuma viagem ou evento ainda — gere as sugestões na aba Revisão." + botão "Adicionar pasta…" (`:54-59`); capa ausente ou que falha → ⊘ + "capa fora de alcance" em vez de cartão em branco (`:169-176`) — "ele estava mudo, não quebrado" (`:136-139`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Trips.test.tsx::não mostra 'nenhuma viagem' enquanto as consultas ainda estão pendentes (D-072)`; `…::a capa é a miniatura cacheada, não a prévia grande do loupe`; `…::card sem capa alcançável diz 'fora de alcance' em vez de ficar em branco`; `…::badge Mapa abre o grupo direto na vista de mapa, sem também disparar o clique do card (D-050)`; `…::badge Mapa não é descendente do card — foco/Tab alcança os dois independentemente`; `…::dois eventos com o mesmo nome mostram, cada um, de onde vieram (D-03/CONS-02)`; `…::nomes que diferem só por caixa/espaço contam como colisão`
- **Decisões:** D-050 (o mapa existe e ninguém acha), D-065 (badge "Mapa" corrige D-050), D-072 (aba Viagens de 50-120 s para ~0,1 s), D-030/D-034 (álbum nomeia, não divide)
- **Arquivos:** `webapp/src/components/Trips.tsx:28-224`; `webapp/src/App.tsx:299-310`; `webapp/src/api.ts:193-201,632-635`

---

### F-U15 — Mapa do lugar de um grupo

- **Propósito:** responder "de onde veio esta coordenada e quanta dúvida ela
  carrega" — não "qual é o nome da rua".
- **Gatilho:** tela `Mapa` (Biblioteca com grupo aberto, toggle "Mapa"; ou badge "Mapa" do card) / rota `GET /api/mapa?trip_id|event_id` / atalhos `⇥` percorre os lugares, `⏎`/`espaço` abre o painel
- **Entradas:** o grupo aberto (`trip_id` ou `event_id`).
- **Regras de negócio:**
  1. **Nenhuma cartografia, nenhum tile, nenhuma requisição para fora**: mandar lat/lon de foto a terceiro é o que o invariante 4 proíbe (`Mapa.tsx:15-21`). A única requisição é a da API local.
  2. **O desenho é por lugar, não por foto** (`Mapa.tsx:23-29`): "Dubai, Thai & Viet" tem 2.406 fotos sobre 31 coordenadas. Cada marcador diz quantas fotos estão ali.
  3. Linguagem visual: ponto cheio = coordenada lida do arquivo; anel tracejado = lugar herdado, e **o raio é o tamanho da dúvida** (`Mapa.tsx:607-630`).
  4. Um fator de escala para os dois eixos — "a dúvida não tem direção preferida", senão todo círculo viraria elipse (`Mapa.tsx:136-143`).
  5. O rótulo "×N" é **omitido** quando ficaria mais perto do ponto do vizinho do que do seu: "número no ponto errado não é informação parcial, é informação falsa" (`Mapa.tsx:526-547`). Quando isso acontece, o painel **diz quantos lugares ficaram calados** e como vê-los (`:726-734`).
  6. O traço herdeira→doadora só é desenhado quando a doadora está em coordenada diferente — medido, 17.819 de 17.819 pares têm distância zero (`Mapa.tsx:279-297`).
  7. O painel "Neste lugar" usa a frase `porque` **pronta do servidor**, verbatim, para não duplicar a calibração do raio (`Mapa.tsx:693-697,800`).
  8. As duas contagens que explicam o que sumiu ficam **na tela**: "N sem coordenada (não dá para desenhar)" e "N fora de alcance (desenhadas; o arquivo é que não responde)" (`Mapa.tsx:675-687`).
  9. A lista "Fotos aqui" corta em 40 e diz quantas faltam (`:50,867-872`).
  10. Entrar no mapa remove a barra de grade, a régua de tempo e o Inspetor, porque nenhum deles age ali (`App.tsx:366,395,458,491`).
- **Saídas:** SVG com malha, marcadores, traços e rótulos; rodapé com legenda e contagens; painel direito de 300 px.
- **Degradação/falha:** carregando → "Montando o mapa de <nome>…" (`:220-226`); erro → "Não consegui montar o mapa deste grupo." + a mensagem (`:227-236`); **grupo sem nenhuma coordenada** → tela dedicada com ⊘, os números e a próxima ação ("importar uma fonte que grave GPS (iPhone, Apple Fotos) e regerar as sugestões na aba Revisão") — `:243-264`; nesse caso a dica do rodapé também muda, para não convidar a um clique que não existe (`:215-218`, `App.tsx:498`); foto fora de alcance continua desenhada, só sem miniatura (`api.ts:215-217`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Mapa.test.tsx::não sai da máquina: a única requisição é a da API local`; `…::GPS próprio vira ponto cheio; herdado vira círculo tracejado`; `…::clicar no círculo mostra a frase pronta do servidor, sem outra chamada`; `…::as contagens de sem coordenada e fora de alcance aparecem na tela`; `…::grupo sem nenhuma coordenada diz por quê em vez de desenhar nada`; `…::avisa o pai quando o grupo não tem nenhum lugar…`; `…::foto fora de alcance continua desenhada e o painel diz por que não há imagem`; `…::80 fotos sobre 4 coordenadas viram 4 marcadores, não 80`; `…::usa um só fator para os dois eixos — círculo não vira elipse`
- **Decisões:** D-031 (nasce sem tiles), D-032 (raio medido, não suposto), D-033 (foto fora de alcance continua no mapa), D-025 (janela da herança), D-050/D-065 (descoberta do mapa)
- **Arquivos:** `webapp/src/components/Mapa.tsx:193-395,654-875`; `webapp/src/api.ts:203-271,636-643`; `webapp/src/App.tsx:54-56,137-140,458-464`

---

### F-U16 — Panorama: lacunas do acervo

- **Propósito:** abrir o app respondendo "em que estado isso está?" e, mais
  útil, **onde o catálogo não sabe** — com cada lacuna clicável.
- **Gatilho:** tela `Panorama` (aba inicial) / rotas `GET /api/panorama`, `GET /api/fontes`, `GET /api/inventario` / atalho `n/a`
- **Entradas:** clique numa lacuna, num ano ou num formato.
- **Regras de negócio:**
  1. É a aba inicial: "a primeira pergunta de quem tem 30 mil fotos é 'em que estado isso está?', não 'me mostre a grade'" (`App.tsx:71-73`).
  2. Cada lacuna é **um filtro pronto**: o número na tela e o conjunto filtrado são o mesmo (`api.ts:172-173`); clicar recorta a Biblioteca e troca de aba (`Panorama.tsx:192-194`; `App.tsx:287-295`).
  3. Lacuna com contagem zero fica **desabilitada** — "não há conjunto para atacar" (`Panorama.tsx:195`).
  4. A frase declara de qual conjunto as lacunas falam: "as N fotos do seu acervo, estejam elas ao alcance agora ou não" (`Panorama.tsx:176-182`) — e por isso o total é maior que "organizáveis" (D-068).
  5. **"Por câmera" é leitura, não botão**: o catálogo não filtra por câmera hoje, "e um botão que não faz nada é pior do que texto" (`Panorama.tsx:263-265`).
  6. Ano "sem data" vira a lacuna `sem_data`, não um filtro por ano (`Panorama.tsx:257-261`).
  7. Cada lista de facetas corta em 12 e diz "e mais N…" (`:55-59`).
  8. A tabela ano × fonte só aparece quando há fonte com fotos e ano conhecido (`:207`).
- **Saídas:** cartões de lacuna com barra proporcional; tabela ano × fonte; três listas de facetas.
- **Degradação/falha:** carregando → "Lendo o catálogo…" (`:144-150`); catálogo vazio → "Catálogo vazio — adicione uma pasta na barra lateral para começar." + botão "Adicionar pasta…" (`:151-158`); sem lacunas → "Nenhuma lacuna — tudo que o motor precisa está preenchido." (`:179-181`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/App.test.tsx::abre no Panorama e mostra as lacunas do catálogo`; `…::clicar numa lacuna recorta a Biblioteca com chip removível`; `…::lacuna zerada não é clicável — não há conjunto para atacar`; `…::Panorama vazio: clicar 'Adicionar pasta…' abre 'Caminho da pasta de fotos'…`
- **Decisões:** D-068 (o funil e o denominador de "organizáveis")
- **Arquivos:** `webapp/src/components/Panorama.tsx:124-275`; `webapp/src/api.ts:167-191,623`

---

### F-U17 — Inventário por pasta ("O acervo")

- **Propósito:** dizer o que existe, e não só o que dá para abrir agora — num
  acervo em NAS e discos externos, o alcançável é a minoria.
- **Gatilho:** tela `Panorama` → bloco "O acervo" / rota `GET /api/inventario` / atalho `n/a`
- **Entradas:** nenhuma (leitura).
- **Regras de negócio:**
  1. Um cartão por **raiz** de disco, com total de fotos, situação e as fontes que a alimentam (`Panorama.tsx:82-103`).
  2. A situação é uma de três frases: "tudo alcançável", "fora de alcance — volume não montado", ou "N fora de alcance" (`:94-98`).
  3. Um cartão extra para `sem_caminho`: "sem arquivo local / referências de catálogo na nuvem" (`:104-116`).
  4. O funil cheio aparece acima dos cartões (`:78-80`) — "era esta tela que dizia '190.828 conhecidas · 91.937 alcançáveis' enquanto o rodapé dizia '26.023 organizáveis', sem nada ligando os três números" (`:75-77`).
  5. Abrir o Panorama com "5.191 no catálogo" respondia a pergunta errada para quem está tentando descobrir o que tem (`:64-70`).
- **Saídas:** grade de 1–2 colunas de cartões.
- **Degradação/falha:** inventário ausente → o bloco não renderiza (`Panorama.tsx:169`), o resto da tela continua.
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/App.test.tsx::abre com o que existe, não com o que dá para abrir agora`
- **Decisões:** D-061, D-062, D-063, D-064 (inventário por pasta), D-068
- **Arquivos:** `webapp/src/components/Panorama.tsx:64-120`; `webapp/src/api.ts:742-756,624`

---

### F-U18 — Funil do acervo (uma leitura, quatro degraus)

- **Propósito:** parar de mostrar cinco números diferentes para a mesma
  pergunta. Existe porque cinco telas contavam com denominadores diferentes e
  nenhuma dizia qual.
- **Gatilho:** telas `StatusBar` (compacto, todas as abas) e `Panorama` (cheio) / rota `GET /api/funil` / atalho `n/a`
- **Entradas:** o total do filtro da tela atual (`noFiltro`), quando há grade.
- **Regras de negócio:**
  1. Quatro degraus, na ordem em que estreitam: **conhecidas → alcançáveis → organizáveis → no filtro** (`Funil.tsx:35-38`).
  2. Os três primeiros vêm do catálogo na mesma passada e na mesma unidade (foto); o quarto é da tela e conta **registro** — e o `title` avisa que por isso ele pode ser maior (`Funil.tsx:98-102`).
  3. O degrau "no filtro" só aparece quando o filtro realmente muda o conjunto (`:94`).
  4. Cada degrau tem um `title` que explica de onde vem a diferença para o anterior (`:71-92`).
  5. Degrau **clicável leva ao conjunto que descreve** ("conhecidas" → alcance `tudo`; "organizáveis" → alcance `organizaveis`); degrau sem navegação é `<span>`, não botão que finge (`:118-132`).
  6. Clicar num degrau limpa busca, recorte e fonte, e leva para a Biblioteca (`App.tsx:502-508`).
  7. A consulta tem `staleTime` próprio de 5 min, porque recontar custa ~1,4 s e o número só muda com job (`:8-16`).
- **Saídas:** a mesma leitura, nos mesmos termos, no rodapé e no Panorama.
- **Degradação/falha:** enquanto conta, a variante compacta **não ocupa espaço** (`null`) e a cheia diz "contando o acervo…" (`:61-65`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Funil.test.tsx::mostra os três degraus do catálogo na ordem em que estreitam`; `…::o degrau 'no filtro' aparece só quando o filtro muda o conjunto`; `…::o degrau explica de onde vem a diferença para o anterior`; `…::clicar num degrau navega para o conjunto que ele descreve`; `…::sem navegação disponível, os degraus não fingem ser botões`; `…::a variante compacta do rodapé não ocupa espaço enquanto conta`; `webapp/src/App.test.tsx::clicar um degrau do funil na barra de status limpa a busca`
- **Decisões:** D-068
- **Arquivos:** `webapp/src/components/Funil.tsx:12-152`; `webapp/src/components/StatusBar.tsx:157-166`; `webapp/src/App.tsx:499-508`

---

### F-U19 — Escanear uma pasta (com progresso)

- **Propósito:** trazer uma pasta para o catálogo sem bloquear a interface e
  sem tocar em arquivo nenhum.
- **Gatilho:** telas `Sidebar`, `Panorama` (vazio), `PhotoGrid` (vazio), `Trips` (vazio) → modal `ModalCaminho` / rota `POST /api/scan {caminho}` / atalhos `Enter` confirma, `Escape` cancela
- **Entradas:** caminho absoluto digitado.
- **Regras de negócio:**
  1. **Quatro pontos de entrada, um modal só**, dono do `App` — antes o modal vivia na Sidebar, com estado privado, inalcançável na aba Panorama (`App.tsx:125-135`; `ModalCaminho.tsx:5-10`).
  2. Valor vazio (após `trim`) não confirma (`ModalCaminho.tsx:35,48`).
  3. A catalogação é **somente leitura** (invariante 1): nada é movido, renomeado ou alterado.
  4. Só um trabalho por vez: o servidor responde 409 "já existe um trabalho em andamento" (`app.py:1449`), e os botões de disparo ficam desabilitados enquanto `job.rodando` (`Sidebar.tsx:122,128`).
  5. Sucesso fecha o modal; **erro mantém o modal aberto** com a mensagem do servidor ao lado do campo que causou a falha (`App.tsx:524-530`; `ModalCaminho.tsx:20-23`).
  6. O progresso é do **SSE**, e vive na barra de status da janela inteira — o trabalho continua quando o usuário troca de aba (`useJob.ts:49-68`; `StatusBar.tsx:16-19`).
  7. Ao concluir, todas as consultas são invalidadas de uma vez (`useJob.ts:57-60`) e a barra oferece o próximo passo: **"Gerar sugestões"** (`StatusBar.tsx:125-139`).
- **Saídas:** barra de progresso, contadores (processados / vistos, erros, arq/s), e o catálogo inteiro recontado ao fim.
- **Degradação/falha:** pasta inexistente → 422 com o caminho na mensagem (`app.py:1447`); servidor ocupado → 409; conexão SSE caída → reconexão com backoff exponencial até 15 s, consultando `/api/job` a cada tentativa (`useJob.ts:28-47`) — "fechar e nunca voltar era o que congelava os contadores com o disco ainda girando" (`:62-64`); erro de leitura de arquivo não derruba a varredura (contrato do scanner).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/App.test.tsx::Panorama vazio: clicar 'Adicionar pasta…' abre 'Caminho da pasta de fotos' e confirmar dispara POST /api/scan com o caminho digitado`; `…::o mesmo modal é alcançável pelo botão da barra lateral, na aba Biblioteca`; `…::quando o POST /api/scan responde erro, o modal permanece aberto e a mensagem do servidor aparece`; `webapp/src/hooks/useJob.test.tsx::um erro na conexão não congela os contadores: reassina e segue`
- **Decisões:** CONS-05 e "D-07" do plano 04-06 (mesma ação nas quatro telas) — **não** é o D-007 global; LANC-03 (opacidade do backdrop, `App.test.tsx:518`)
- **Arquivos:** `webapp/src/App.tsx:125-135,520-533`; `webapp/src/components/ModalCaminho.tsx:11-54`; `webapp/src/hooks/useJob.ts:94-135`

---

### F-U20 — Importar catálogo (Apple Fotos / Google Takeout)

- **Propósito:** trazer catálogos externos como fonte, sem importar nem
  duplicar arquivo, e avisando antes sobre permissão do macOS.
- **Gatilho:** tela `Sidebar` → "Importar catálogo…" / rota `POST /api/importar {tipo, caminho?}` / atalho `n/a`
- **Entradas:** escolha entre "🍎 Apple Fotos (somente leitura)" e "🌐 Google Takeout (pasta local)"; para o Takeout, o caminho da pasta extraída.
- **Regras de negócio:**
  1. Apple Fotos exibe um **aviso prévio** antes de qualquer chamada: "A importação é somente leitura — nenhuma foto é movida, renomeada ou alterada na sua biblioteca" **e** "O macOS pode pedir Acesso Total ao Disco… em Ajustes → Privacidade e Segurança → Acesso Total ao Disco" (`Sidebar.tsx:281-310`). É melhor o usuário saber antes do que descobrir num erro do macOS (`:278-280`).
  2. Cancelar o aviso **não dispara** a importação (`Sidebar.tsx:175`).
  3. Takeout reusa `ModalCaminho` com outro título (`Sidebar.tsx:163-168`); pasta inexistente → 422 (`app.py:1461`).
  4. A partir daí é o mesmo circuito de job/SSE/invalidação de F-U19, com o rótulo "Importando <apelido>…" (`StatusBar.tsx:10`).
  5. Ao concluir, a barra também oferece "Gerar sugestões" (`StatusBar.tsx:130`).
  6. Fotos importadas sem arquivo local aparecem na Biblioteca por padrão, marcadas, e o controle de alcance é que as isola (`App.tsx:94-97`).
- **Saídas:** fonte nova na lateral com ícone por tipo; contagens recalculadas.
- **Degradação/falha:** 409 se já há trabalho; erro do disparo aparece abaixo das ações da lateral (`Sidebar.tsx:57,154`); fonte cujo volume não responde ganha ⚠ com `title="indisponível"` (`Sidebar.tsx:90-94`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Sidebar.test.tsx::avisa sobre leitura somente e Acesso Total ao Disco antes de importar`; `…::cancelar o aviso não dispara a importação`; `webapp/src/components/StatusBar.test.tsx::importação concluída também oferece gerar sugestões`
- **Decisões:** D-028 (Lightroom como fonte externa), D-035 (miniaturas do Apple Fotos fora do catálogo), D-024 (rebaixar, nunca apagar)
- **Arquivos:** `webapp/src/components/Sidebar.tsx:125-176,278-310`; `webapp/src/hooks/useJob.ts:136-139`

---

### F-U21 — Retomar uma varredura interrompida

- **Propósito:** dar rastro visível a trabalho perdido. "O dono varreu 225 mil
  arquivos num dia e o app abriu no dia seguinte como se nada tivesse
  acontecido."
- **Gatilho:** faixa `RetomarScan`, visível em **qualquer aba** / rota `GET /api/scan/interrompidos` → `POST /api/scan` / atalho `n/a`
- **Entradas:** clique em "Retomar" ou em "✕".
- **Regras de negócio:**
  1. O servidor carimba as sessões órfãs no boot; a UI as transforma em pendência com a ação que a resolve (`RetomarScan.tsx:8-15`).
  2. Só a sessão **mais recente de cada fonte** conta — se um scan posterior concluiu, a interrupção antiga é história (`app.py:1471-1476`).
  3. Retomar é um **novo scan do mesmo caminho**; o incremental pula o que já foi indexado, e o `title` diz isso (`RetomarScan.tsx:50,54`).
  4. "Retomar" fica desabilitado quando há job rodando ou o volume não está montado, com `title` explicando qual dos dois (`:51-56`).
  5. "✕" é **local e da sessão**: "a pendência real só morre quando um scan mais novo da fonte conclui" (`:16-17,60-70`).
  6. A faixa mostra quantos arquivos já tinham sido vistos, quando o número existe (`:40-45`).
- **Saídas:** faixa some ao dispensar ou ao concluir um scan novo daquela fonte.
- **Degradação/falha:** sem pendências → o componente não renderiza nada (`:27-28`); volume desmontado → botão desabilitado com o motivo.
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/RetomarScan.test.tsx::não renderiza nada quando não há varredura interrompida`; `…::oferece a retomada e dispara o scan no mesmo caminho`; `…::desabilita Retomar quando o volume da fonte está fora de alcance`; `…::dispensar esconde a pendência sem chamar o servidor`
- **Decisões:** D-037 ("não visto no walk" ≠ "arquivo apagado")
- **Arquivos:** `webapp/src/components/RetomarScan.tsx:18-74`; `webapp/src/api.ts:441-452,671-672`; `webapp/src/App.tsx:246`

---

### F-U22 — Reapontar uma fonte que mudou de lugar

- **Propósito:** quando o volume remonta noutro ponto (`/Volumes/photo` →
  `/Volumes/photo 1`), reapontar o catálogo em vez de recatalogar tudo.
- **Gatilho:** tela `Sidebar` → botão "↦ mudou de lugar" → `ModalReapontar` / rotas `POST /api/fontes/{id}/reapontar/preview` e `POST /api/fontes/{id}/reapontar` / atalho `n/a`
- **Entradas:** confirmação explícita.
- **Regras de negócio:**
  1. A affordance aparece **só** para as fontes detectadas como remontadas (`GET /api/fontes/reapontamentos`, `Sidebar.tsx:53,96`). A detecção custa um `diskutil` por fonte e por isso vive em consulta própria, não em `/api/fontes` (`api.ts:581-583`).
  2. Uma fonte indisponível **sem** reapontamento possível mostra ⚠, não o botão (`Sidebar.tsx:90-94`).
  3. **Prévia sempre visível antes de confirmar** (invariante 2): prefixo antigo → novo, quantos arquivos de mídia serão reapontados, e quantas referências sem esse prefixo (ex.: `apple://uuid`) ficam **intocadas** (`Sidebar.tsx:220-254`; `api.ts:26-32`).
  4. A frase declara o escopo: "Isto reescreve só o catálogo — nenhum arquivo é tocado no disco" (`Sidebar.tsx:222-226`).
  5. Confirmar exige `{confirmar: true}` no corpo; sem isso o servidor responde 422 (`api.ts:593`; `app.py:592`).
  6. Sucesso invalida `["fontes"]` e `["reapontamentos"]` e fecha o modal (`Sidebar.tsx:205-209`).
  7. A operação grava no audit log (`audit_log_id` no retorno, `api.ts:593`).
- **Saídas:** a fonte volta a ser alcançável; contagens recalculam.
- **Degradação/falha:** prévia carregando → "Verificando…" (`:216`); prévia com erro → a mensagem em vermelho (`:217-219`); confirmação com erro → mensagem própria acima dos botões (`:255-259`); botão "Reapontar" desabilitado sem prévia ou durante a gravação, virando "Reapontando…" (`:267-271`).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/Sidebar.test.tsx::sem fonte movida, nenhuma affordance aparece`; `…::fonte cujo volume remontou mostra o botão, com prévia antes de confirmar`; `…::confirmar reaponta e fecha o modal`; `…::cancelar não chama a escrita`
- **Decisões:** D-036 (reapontar quase reescreveu referência de nuvem como se fosse caminho de disco)
- **Arquivos:** `webapp/src/components/Sidebar.tsx:42-45,96-103,188-276`; `webapp/src/api.ts:12-33,584-594`

---

### F-U23 — Operações físicas: plano → dry-run → cópia verificada

- **Propósito:** a única forma de mexer em arquivo. Cada passo explícito, e
  reversível até o último clique.
- **Gatilho:** tela `Operations` (aba Operações) / rotas `POST /api/operacoes`, `POST /api/operacoes/{id}/dry-run`, `POST /api/operacoes/{id}/executar`, `GET /api/operacoes/{id}/auditoria` / atalho `n/a`
- **Entradas:** pasta de destino da biblioteca organizada (caminho absoluto).
- **Regras de negócio:**
  1. O plano só existe a partir das sugestões **aprovadas** (a tela diz isso no estado vazio, `:137-141`).
  2. **Execução bloqueada até o dry-run aprovar algo**: `podeExecutar = plano.executavel && !job.rodando` — "ter rodado o dry-run não basta: ele precisa ter aprovado alguma coisa" (`:110-111`).
  3. O `title` do botão nomeia a condição que falta: "Rode o dry-run antes de copiar" / "O dry-run não encontrou nenhum arquivo copiável" / "Copia os arquivos para o destino" (`:201-207`).
  4. O **veredito textual** fica sempre visível ao lado dos botões, e em vermelho quando o dry-run rodou e nada é copiável (`:223-231,42-54`) — sem ele, "um plano com todas as origens num volume desmontado se lia como pronto".
  5. O diff mostra `origem → destino` por item, com o prefixo comum extraído para o cabeçalho ("de X / para Y") e removido de cada linha (`:26-40,271-307`).
  6. O relatório do dry-run traz prontos, bytes necessários, bytes livres (verde/vermelho) e a lista de problemas (`:242-269`).
  7. Trocar de plano **zera o relatório** — a evidência é sempre do plano em tela (`:81-82`).
  8. Durante a execução, a faixa afirma o invariante: "os originais permanecem intactos" (`:234-240`), e há Cancelar (`:213-221`).
  9. Na lista lateral, "dry-run: nada copiável" só aparece enquanto ainda há o que copiar — num plano concluído a frase lia como falha ao lado do próprio sucesso (`:160-171`).
  10. A auditoria fica num `<details>` colapsado ao pé da tela (`:310-324`).
  11. A operação é **cópia**, nunca movimentação (invariante 2), e o destino nunca é sobrescrito (invariante 3).
- **Saídas:** itens com status por linha; contadores `concluidos/total` na lista; trilha de auditoria.
- **Degradação/falha:** destino não absoluto ou indisponível → 422 com mensagem no topo (`app.py:1258,1263`; `Operations.tsx:91,130`); 409 "rode o dry-run antes de executar" é prevenido pelo `disabled`; 409 "já existe um trabalho" chega em `setErro` (`:196-198`); item com conflito ou erro mostra a mensagem abaixo da linha (`:301-305`); **não há botão de retomar plano parcial** — reexecutar é clicar "Copiar" de novo.
- **Estado:** parcial — o botão de executar depende de `job.rodando` (SSE) e não de `isPending`, o que é o gatilho de duplo clique descrito no achado **A1** da auditoria de 2026-09-19 (mesmo padrão de `EscritaExif.tsx:395`).
- **Testes que provam:** `webapp/src/components/Operations.test.tsx::sem dry-run, copiar fica bloqueado e a tela diz por quê`; `…::com dry-run, copiar libera e dispara o plano certo`; `…::dry-run sem nada copiável bloqueia, mesmo tendo rodado`; `…::o diff mostra o caminho relativo, sem o prefixo comum das árvores`; `…::estado vazio orienta a próxima ação`; `…::Cancelar de cópia em andamento é neutro em repouso, vermelho só no hover (D-05, CONS-07)`
- **Decisões:** D-011 (execução de plano não foi exercitada), CONS-07 e "D-05" do plano de consistência (cor do Cancelar)
- **Arquivos:** `webapp/src/components/Operations.tsx:26-330`; `webapp/src/api.ts:305-341,660-667`; `webapp/src/hooks/useJob.ts:142-143`

---

### F-U24 — Template do destino

- **Propósito:** decidir em que pasta cada foto cai, com prévia real, sem
  disparar trabalho pesado a cada tecla.
- **Gatilho:** tela `Operations` → seção colapsável "Template do destino" / rotas `GET|PUT /api/configuracoes/template`, `POST /api/configuracoes/template/preview`, `POST /api/sugestoes/gerar` / atalho `n/a`
- **Entradas:** o texto do template.
- **Regras de negócio:**
  1. Vive dentro de Operações porque é a única tela sobre "como o destino é decidido no disco", e nasce fechado com o template atual visível no rótulo (`:26-29,91-95`).
  2. Sete placeholders válidos, listados como chips: `{categoria} {ano} {viagem} {evento} {pais} {regiao} {cidade}` (`:14-22,109-113`) — lista fixa, espelhada do motor.
  3. A prévia segue o campo com **debounce de 350 ms** (`:24,56-59`) e é **renderizada pelo backend** — a UI nunca reimplementa o colapso/dedupe de segmento (`api.ts:428-430`).
  4. Dois exemplos fixos mostram os dois casos: com viagem/evento preenchido e sem (`:100-107,136-141`).
  5. **Salvar e Regenerar são ações distintas de propósito** (`:31-35`): "Regenerar sugestões pendentes" fica desabilitado enquanto houver rascunho não salvo, com `title` dizendo "Salve o template antes de regenerar" (`:145-152`).
  6. Escopo declarado: "Só sugestões pendentes são recriadas — aprovadas, rejeitadas ou com destino editado à mão não mudam" (`:157-160`).
  7. Template vazio não salva (`:128`); placeholder inválido responde 422 e a mensagem aparece inline **sem travar o campo** (`:74,132`; `app.py:1055`).
- **Saídas:** o template salvo passa a valer a partir do próximo plano; regenerar recria as pendentes.
- **Degradação/falha:** erro de salvar e erro de regenerar têm superfícies separadas (`:132,161-163`); o disparo de regenerar **tem** `.catch` (`:79`), ao contrário dos outros dois gatilhos de "gerar sugestões".
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/components/TemplateEditor.test.tsx::mostra o template atual, carregado do servidor`; `…::preview atualiza com debounce ao digitar, sem uma requisição por tecla`; `…::salvar chama PUT com o texto do campo`; `…::placeholder inválido mostra o erro do servidor inline, sem travar o campo`; `…::regenerar sugestões pendentes chama o job de gerar sugestões`; `…::editar o campo sem salvar desabilita regenerar — evita recriar sugestões a partir de um rascunho`
- **Decisões:** n/a
- **Arquivos:** `webapp/src/components/TemplateEditor.tsx:14-168`; `webapp/src/api.ts:422-439,687-691`

---

### F-U25 — Escrita EXIF de localização (in-place, campo vazio)

- **Propósito:** gravar GPS, cidade e país **em campo vazio** do arquivo
  original — a única escrita destrutiva-adjacente permitida, e sempre
  precedida de plano, dry-run e seleção explícita.
- **Gatilho:** tela `EscritaExif` (aba Localização) / rotas `POST /api/exif/plano`, `POST /api/exif/{id}/dry-run`, `POST /api/exif/{id}/executar`, `GET /api/exif/{id}/auditoria` / atalho `n/a`
- **Entradas:** criação do plano (sem parâmetro, escopo global) e a seleção de linhas.
- **Regras de negócio:**
  1. **Campo já preenchido nunca é sobrescrito** — o chip diz "Cidade já preenchida" em cor **neutra**, nunca vermelha: é comportamento esperado (`:23-27,40,85-96`).
  2. A seleção nasce **do servidor**, nunca de "tudo marcado": o backend já decidiu o default por tipo de linha, e duplicar a regra no cliente criaria duas verdades (`:261-265,291-295`).
  3. **Três tipos de linha**: A (escrita direta), B (formato não suportado → sidecar `.xmp`, nasce desmarcada, motivo **visível como texto**), C (pasta sincronizada → aviso aditivo, continua marcada). Uma linha pode ser B e C ao mesmo tempo, e a semântica do checkbox segue a de B (`:456-504`).
  4. O aviso de pasta sincronizada é literal e é aviso, **não bloqueio**: "O app de sincronização pode sobrescrever este arquivo com a versão antiga ou gerar conflito silencioso. Você decide incluir ou não." (`:195-198`).
  5. Gravar exige três condições simultâneas: dry-run aprovou algo, ao menos uma linha marcada, e nenhum job rodando (`:325-326`); o `title` nomeia qual falta (`:396-404`).
  6. A execução envia **a seleção real**, nunca `null`, "para o servidor persistir exatamente o que a tela mostrava" (`:388-392`).
  7. Pós-execução, cada linha troca os chips por um detalhamento ✓/✗/— por campo, e **todo campo em falha é nomeado com o motivo** — nunca um "erro" nu (`:158-193`).
  8. A faixa de execução afirma a garantia: "o original só muda campo por campo, com verificação antes de seguir" (`:430-436`).
  9. Item com falha e backup mostra "Cópia de recuperação preservada — é a forma de desfazer esta gravação." com o caminho no `title` (`:552-567`).
  10. Auditoria completa em `<details>` (`:573-587`).
- **Saídas:** contagem `gravados/total` por plano; detalhamento por linha; trilha de auditoria.
- **Degradação/falha:** nenhum plano possível → bloco "Nada para gravar" explicando por quê e o que fazer antes (`:340-348`); 409 "rode o dry-run antes de gravar" / "nenhum item selecionado" prevenidos pelo `disabled` (`app.py:1417,1422`); 409 "já existe um trabalho" cai em `setErro` (`:393`); Cancelar disponível durante a execução (`:409-417`). **Não há ação de restaurar na UI** — a recuperação é manual, a partir do caminho do backup.
- **Estado:** parcial. (a) A CTA depende de `job.rodando` e não de `isPending` — achado **A1** (`EscritaExif.tsx:395`). (b) A `StatusBar` não tem rótulo para o tipo de job `escrita_exif` e diz "Trabalhando…" (`StatusBar.tsx:8-14,69`). (c) Restaurar backup não é ação de UI.
- **Testes que provam:** `webapp/src/components/EscritaExif.test.tsx::sem dry-run, gravar fica desabilitado`; `…::estado vazio`; `…::linha tipo A mostra o valor que entraria`; `…::campo já preenchido aparece como pulado, não como erro`; `…::desmarcar uma linha muda a contagem da CTA`; `…::desmarcar tudo desabilita a CTA`; `…::a execução envia só os ids marcados`; `…::linha de formato não suportado nasce desmarcada e mostra o motivo`; `…::linha em pasta sincronizada avisa e continua marcada`; `…::linha que é B e C ao mesmo tempo mostra os dois badges`; `…::detalhamento por campo depois da execução`; `…::backup preservado aparece quando há falha`
- **Decisões:** D-075 (escrita EXIF de localização autorizada em campo vazio, revoga parte do invariante 7), D-076 e D-077 (allowlist de formatos), D-078 (andaime IPTC); e as decisões locais da UI-SPEC do plano EXIF (`D-01` a `D-07`, `EXIF-03`, `EXIF-05`) citadas em `EscritaExif.tsx:158,200,213,226,261`
- **Arquivos:** `webapp/src/components/EscritaExif.tsx:15-593`; `webapp/src/api.ts:351-420,692-700`; `webapp/src/hooks/useJob.ts:144-147`

---

### F-U26 — Barra de status: progresso honesto, pausar, cancelar

- **Propósito:** um único lugar, presente em todas as abas, dizendo o que o
  app está fazendo e permitindo intervir — sem spinner modal.
- **Gatilho:** componente `StatusBar` (rodapé da janela) / rotas `GET /api/status`, `GET /api/progresso` (SSE), `POST /api/job/pausar|continuar|cancelar` / atalho `n/a`
- **Entradas:** o estado do job; a dica da aba atual; o total do filtro.
- **Regras de negócio:**
  1. A barra atravessa a janela inteira e é a **mesma em todas as abas**, porque o trabalho continua quando o usuário troca de tela (`:16-19`; `DIRECAO_DE_ARTE.md:43-45`).
  2. Três modos exclusivos: **ativo** (progresso + controles), **concluído** (resumo + próximo passo + dispensar), **repouso** (a dica da aba) — `:43,55,112,152`.
  3. **Progresso honesto**: largura real só quando o total é conhecido; senão barra indeterminada — "nunca fingir um progresso que não temos como medir" (`:45-51,58-59`).
  4. **Pausar só existe para scan** (`:39-41`): mostrá-lo para outros tipos seria uma ação que sempre volta 409.
  5. Pausado é estado próprio: o texto vira "Pausado" (sem reticências) e o botão vira "Continuar" (`:69,82-90`); cancelar continua disponível (`:101-108`).
  6. Após um scan ou import **concluído**, aparece o CTA "Gerar sugestões" — "no acervo real, 86% do organizável ficou sem sugestão porque o fluxo morria aqui, num scan mudo" (`:125-139`). Não aparece após o próprio job de sugestões.
  7. O rodapé mostra o **funil inteiro**, não só um número solto, mais "· N fontes · M erros" (`:157-166`).
  8. Recarregar a página durante um job em andamento **ou pausado** reencontra o trabalho e reassina o SSE (`useJob.ts:74-87`).
- **Saídas:** barra de 28 px de altura, sempre presente.
- **Degradação/falha:** SSE caído → reconexão com backoff exponencial (1 s → 15 s) consultando `/api/job` a cada tentativa (`useJob.ts:28-47`); 409 de pausar/continuar é **silenciado de propósito**, porque o estado do job já é a verdade (`useJob.ts:111-129`); job com status `erro` → a mensagem do servidor em vermelho (`:119-120`).
- **Estado:** parcial — `ROTULO_JOB` não cobre `escrita_exif` nem `reconciliacao` (`:8-14`), que caem em "Trabalhando".
- **Testes que provam:** `webapp/src/components/StatusBar.test.tsx::mostra Pausar durante um scan e chama o endpoint ao clicar`; `…::mostra Continuar e o texto honesto quando o scan está pausado`; `…::continua permitindo cancelar mesmo pausado`; `…::não oferece pausar para um job que não é scan (evita 409 previsível)`; `…::scan concluído oferece o próximo passo: gerar sugestões`; `…::sugestões concluídas não oferecem gerar sugestões de novo`; `…::a barra de progresso é proporcional a processados/vistos`; `…::sem total conhecido a barra fica indeterminada, não fingindo progresso`; `webapp/src/App.test.tsx::a barra de status mostra os totais em qualquer aba`
- **Decisões:** D-068 (o funil no rodapé)
- **Arquivos:** `webapp/src/components/StatusBar.tsx:20-169`; `webapp/src/hooks/useJob.ts:18-152`; `webapp/src/App.tsx:496-509`

---

### F-U27 — Painéis recolhíveis e adaptação da tela à aba

- **Propósito:** densidade profissional — a janela mostra os controles que
  agem na tela atual, e o usuário esconde o que não quer.
- **Gatilho:** tela `App` / rota `n/a` / atalhos `[` (sidebar), `]` (inspetor), `⌘1`/`⌘3` (só no app empacotado)
- **Entradas:** atalhos de teclado.
- **Regras de negócio:**
  1. Três painéis: sidebar (fontes + pastas), centro (grade/tela da aba), inspetor (detalhe) — `docs/DIRECAO_DE_ARTE.md:17-27`, realizado em `App.tsx:248-494`.
  2. `[` e `]` funcionam **em qualquer aba** (`App.tsx:183-190`), mesmo onde o painel correspondente não está montado.
  3. ⌘1/⌘3 são reconhecidos, mas o navegador reserva ⌘1–⌘8 para trocar de aba e nunca entrega essas teclas à página; só passam a funcionar no Tauri (`App.tsx:178-181`).
  4. A sidebar só é montada em Biblioteca / Revisão / Viagens (`App.tsx:68,249`) — "um controle visível age sobre a tela em que está".
  5. O inspetor só existe onde há grade: Biblioteca e não no modo mapa (`App.tsx:491`). No mapa quem ocupa a direita é o painel "neste lugar".
  6. A barra de controles da Biblioteca some inteira no modo mapa (`App.tsx:366,395`).
  7. Os atalhos são anunciados na dica do rodapé, **e a dica só cita `[ fontes` nas telas em que a lateral existe** (`App.tsx:36-37,40-43`).
  8. Em telas estreitas a barra de controles quebra em **dois grupos**, nunca em sub-linhas internas: cada grupo usa `flex-nowrap` + rolagem horizontal própria, para garantir o teto de duas linhas (`App.tsx:318-324,396-398`).
- **Saídas:** painéis somem e voltam; o centro se expande.
- **Degradação/falha:** n/a (estado puramente local).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/App.test.tsx::[ e ] recolhem os painéis laterais`; `…::cada aba renderiza sem quebrar, e o inspetor não invade as sem grade`; `…::a barra lateral só aparece onde ela age`; `…::CONS-06: a barra da Biblioteca empilha em dois grupos, não um flex único`
- **Decisões:** `docs/NAVEGACAO.md` decisões 1 e 2; CONS-06 e "D-08" do plano de consistência (teto de 2 linhas abaixo de `lg`)
- **Arquivos:** `webapp/src/App.tsx:36-48,68,170-213,248-494`; `docs/DIRECAO_DE_ARTE.md:15-47`

---

### F-U28 — Fontes e alcance (o que está online, o que está offline)

- **Propósito:** deixar claro, o tempo todo, que parte do acervo responde
  agora e que parte só existe no catálogo — sem esconder nem inventar.
- **Gatilho:** telas `Sidebar`, `App` (segmentado de alcance), `Panorama`, `StatusBar` / rotas `GET /api/fontes`, `GET /api/status`, `GET /api/funil`, `GET /api/inventario` / atalho `n/a`
- **Entradas:** escolha de fonte e de alcance.
- **Regras de negócio:**
  1. Cada fonte tem ícone por tipo (pasta / Apple Fotos / Google Takeout), rótulo desambiguado e contagem (`Sidebar.tsx:11-15,75-105`).
  2. **Rótulos nunca colidem**: `rotulosDeFontes` cresce a cauda do caminho até distinguir, e cai no caminho literal quando nem isso basta (mesma pasta em caixas diferentes) — `fontes.ts:14-57`. O acervo real tem `/Users/acamerini` e `/users/acamerini`, e a lateral mostrava dois itens idênticos.
  3. Fonte indisponível ganha ⚠; fonte remontada ganha a ação de reapontar (F-U22) em vez do aviso (`Sidebar.tsx:90-103`).
  4. O segmentado de alcance separa três conjuntos, cada um com `title` próprio (`App.tsx:366-393`) — ver F-U03 regra 2.
  5. Fotos importadas do Apple Fotos **sem arquivo local aparecem por padrão**, marcadas: "o dono importou 44.661 fotos e a Biblioteca respondia (0)" (`App.tsx:94-97`).
  6. O funil (F-U18) e o inventário (F-U17) dizem, em números, a distância entre "existe" e "dá para abrir".
  7. Nada sai da máquina por padrão: a única funcionalidade que fala com serviço externo é F-U12, atrás de dois consentimentos.
- **Saídas:** lateral com fontes e contagens; grade filtrada; funil e inventário coerentes entre si.
- **Degradação/falha:** volume desmontado → fotos continuam no catálogo, visíveis em `tudo`, com ⊘ e motivo na miniatura (`Miniatura.tsx:52-72`) e "fora de alcance" nos avisos de Revisão e mapa; registro que não é acervo é **rebaixado a fonte de sinal**, nunca apagado (invariante 8 / D-024).
- **Estado:** pronto.
- **Testes que provam:** `webapp/src/fontes.test.ts::cresce o caminho quando dois nomes curtos colidem`; `…::mesma pasta em caixas diferentes deixa de ser dois rótulos iguais`; `…::nomeia a fonte no chip em vez de dizer a palavra 'fonte'`; `webapp/src/App.test.tsx::abre com o que existe, não com o que dá para abrir agora`
- **Decisões:** D-024 (rebaixar, nunca apagar), D-035 (miniaturas do Apple Fotos), D-068 (o que conta como organizável)
- **Arquivos:** `webapp/src/fontes.ts:27-62`; `webapp/src/components/Sidebar.tsx:29-186`; `webapp/src/App.tsx:94-97,366-393`; `webapp/src/api.ts:3-10`

---

### F-U29 — Configurações e privacidade

- **Propósito:** registrar o que o usuário **consegue** e o que **não
  consegue** ajustar pela interface hoje.
- **Gatilho:** tela `Operations` → `TemplateEditor`; tela `Review` → `ClassificacaoPasta` (passo 0); tela `Sidebar` → `ModalAvisoApple` / rotas `PUT /api/configuracoes/template`, `PUT /api/genai-pasta/config` / atalho `n/a`
- **Entradas:** o template de destino; o opt-in de classificação por GenAI.
- **Regras de negócio:**
  1. **Não existe tela de Configurações.** As duas únicas preferências graváveis pela UI são o template (F-U24) e o opt-in de GenAI (F-U12).
  2. A chave mestra `servicos_externos` **não tem endpoint de escrita** nesta fase: só se muda no TOML, e a tela diz isso ao usuário — "habilite [privacidade] servicos_externos antes de usar este recurso" (`api.ts:702-703`; `ClassificacaoPasta.tsx:137-141`).
  3. O gate de GenAI pode ser desligado de volta pela própria tela, pelo link "Desligar" do passo 1 (`ClassificacaoPasta.tsx:187-197,800`).
  4. A única permissão do sistema operacional que a UI antecipa é o Acesso Total ao Disco, e ela aponta o caminho exato do ajuste (`Sidebar.tsx:293-297`).
  5. Antes de qualquer envio externo, a tela declara **o que** sai (nome da pasta e metadados, nunca imagens), **para onde** (Claude Sonnet 5), **quanto custa** e **como recusar** (`ClassificacaoPasta.tsx:106-112,284-317`).
- **Saídas:** as duas preferências persistidas no servidor.
- **Degradação/falha:** 409 quando a mestra está desligada (`app.py:1556`); 422 quando o template é inválido (`app.py:1049,1055`).
- **Estado:** parcial (é o maior buraco funcional da UI). Não há na interface: tema, limites de CPU/workers, caminho do cache de thumbnails, revogação de consentimento **com apagamento** dos dados já enviados, registro do que já foi enviado, nem qualquer ajuste de face/vision (que seguem desligados por padrão e sem UI).
- **Testes que provam:** `webapp/src/components/ClassificacaoPasta.test.tsx::mestre desligado não oferece caixa`; `…::habilitar exige a caixa marcada`; `webapp/src/components/Sidebar.test.tsx::avisa sobre leitura somente e Acesso Total ao Disco antes de importar`; `webapp/src/components/TemplateEditor.test.tsx::salvar chama PUT com o texto do campo`
- **Decisões:** D-080 (o opt-in mora em `application_settings`, não em `PrivacySettings`/TOML), D-079, D-004
- **Arquivos:** `webapp/src/components/ClassificacaoPasta.tsx:82-151,604-694`; `webapp/src/components/TemplateEditor.tsx:36-168`; `webapp/src/components/Sidebar.tsx:278-310`; `webapp/src/api.ts:464-472,687-705`

---

## Lacunas e incertezas

1. **Reabertura de sugestão após reprocessamento é invisível.** A decisão
   existe (reprocessamento que muda destino manda de volta para revisão), e o
   efeito acontece — a sugestão reaparece em "Pendentes" depois da invalidação
   global do job. Mas **nenhum campo do contrato** (`SugestaoRow`,
   `api.ts:273-282`; `GrupoSugestoes`, `:296-303`) carrega "foi reaberta", e
   nenhuma tela mostra badge, aviso ou o destino anterior. Não determinei se
   falta backend, frontend ou os dois.

2. **Não há tela de Configurações** (F-U29). Falta tema, workers, cache,
   revogação de consentimento com apagamento, e histórico do que já foi
   enviado a serviço externo. Não sei se isso é escopo adiado
   deliberadamente ou dívida não registrada.

3. **Colisão de numeração de decisões.** `EscritaExif.tsx` e
   `ClassificacaoPasta.tsx` citam `D-01`…`D-07` como decisões da UI-SPEC do
   próprio plano; `Operations.test.tsx:174` cita "D-05, CONS-07";
   `App.test.tsx` e `Trips.tsx` citam "D-03/CONS-02" e "CONS-05/D-07". Nenhuma
   dessas é a decisão homônima de `docs/DECISOES.md` (onde D-003 é sobre
   arquivos de prompt e D-007 sobre `ARQUITETURA.md`). **Não localizei os
   documentos UI-SPEC/CONS de origem** — se a reconstrução precisar deles,
   eles não estão em `docs/`.

4. **Três disparos de job sem superfície de erro:** `Review.tsx:163`,
   `Duplicates.tsx:74` e `StatusBar.tsx:133` chamam `job.*()` sem `.catch`. Um
   409 "já existe um trabalho em andamento" vira rejeição não tratada no
   console e **nada** na tela. A reconstrução deve tratar os três.

5. **Nada garante "um job por vez" do lado do cliente.** As CTAs de executar
   plano (`Operations.tsx:200`) e gravar EXIF (`EscritaExif.tsx:395`) dependem
   de `job.rodando`, que só chega pelo SSE, e não do `isPending` da própria
   ação — é o gatilho do achado **A1** (duplo clique inicia duas threads no
   mesmo plano; reproduzido 55/200). O conserto de fundo é no servidor, mas a
   UI deve desabilitar no clique.

6. **Nenhum teste de teclado além de `[`/`]`.** Setas, espaço, Escape, ⌘1/⌘3,
   duplo clique e a guarda de "está digitando" (`App.tsx:172-176`) não têm
   cobertura. É o vocabulário central da categoria e é o que está menos
   protegido contra regressão.

7. **A régua de tempo ignora o recorte de pasta.** `LinhaDoTempo.tsx:36-39`
   envia o objeto de filtros inteiro, mas `GET /api/midia/linha-do-tempo`
   (`app.py:676-684`) não aceita `pasta` (nem `camera`/`pais`/`cidade`/
   `palavra_chave`), e o FastAPI descarta o que não conhece. Identificado por
   leitura cruzada, **não verificado em execução**.

8. **A grade confunde "carregando" com "vazio"** (`PhotoGrid.tsx:76`) —
   exatamente o defeito que D-072 corrigiu em `Trips.tsx:38-45`. Enquanto a
   primeira página não chega, o usuário vê "Nenhuma foto no filtro atual".

9. **Restaurar uma gravação EXIF não é ação de UI.** A tela informa que existe
   uma cópia de recuperação e onde (`EscritaExif.tsx:557-564`), mas a
   restauração é manual, fora do app. Não sei se há endpoint para isso.

10. **Job `reconciliacao` não tem gatilho na interface.** Existe em
    `jobs.py:115-121` e em `POST /api/reconciliacao` (`app.py:1206`), mas
    **nenhuma tela o dispara** e `StatusBar` nem tem rótulo para ele. Ou é
    acionado fora da UI, ou é funcionalidade órfã.

11. **`api.opcoesFiltros` é código morto** (`api.ts:611-618`) e com ele os
    filtros por câmera, país, cidade e palavra-chave: existem no contrato e no
    servidor, e nenhuma tela os oferece. `Panorama.tsx:263-265` documenta a
    consequência visível ("Por câmera é leitura"). Não sei se é vestígio ou
    preparação.

12. **Acessibilidade de modal é uniformemente ausente** nos cinco overlays
    (`ModalCaminho`, `Loupe`, os dois da `Sidebar`, `ClassificacaoPasta`):
    sem `role="dialog"`, sem `aria-modal`, sem rótulo acessível, sem trap de
    foco; os dois modais da Sidebar nem fecham com Escape. Não determinei se
    foi decisão consciente (app local, um usuário) ou omissão.
