# Item C — o `.xmp` que muda sem o arquivo mudar

Staging pronto para integrar quando a fase 5 abrir a fronteira. Nasce de
`docs/prompts/fase-14-photoprism-e-sintese.md` §5 — a resolução REVERSA
(dado o `.xmp`, ache a mídia contra um cache em memória) descrita em
`docs/referencia-photoprism/`. Nenhuma linha vem dos repositórios de
referência em si (ambos AGPLv3) — só das descrições de mecanismo já
registradas em `docs/referencia-photoprism/` e `docs/referencia-immich/`.

## O que existe hoje (evidência)

- **A leitura e a fusão do sidecar já são boas — não mexer.**
  `fotoorganizer/metadata/exiftool.py:161-183` (`_sidecar_de`) já resolve
  PARA FRENTE, reconhecendo as duas convenções (`foto.jpg.xmp` do Adobe,
  `foto.xmp` do darktable e de parte do Lightroom — "o primeiro que
  existir vence"). `:186-219` (`_fundir_sidecar`) já funde com a
  precedência certa: o sidecar vence, e se declara qualquer data, TODAS as
  datas do original saem junto, inclusive fuso — para não casar a data do
  editor com o offset da câmera.
- **A lacuna é a detecção, não a leitura.**
  `fotoorganizer/metadata/purepython.py:249-254`
  (`PurePythonExtractor.supported_extensions`) não inclui `.xmp` — só
  `PILLOW_EXTENSIONS | VIDEO_EXTENSIONS` (+ HEIF/RAW quando disponíveis,
  `:43-51`). O scanner nunca enumera o `.xmp` como arquivo (nem para
  ignorá-lo explicitamente).
- **O incremental pula por assinatura da MÍDIA, nunca do sidecar.**
  `fotoorganizer/scanner/scanner.py:281-283` compara
  `self._unchanged_sig(assinatura, stat)`; `:526-534`
  (`_unchanged_sig`) e `:384-402` (`_carregar_conhecidos`) confirmam que a
  assinatura é `(tamanho, mtime_ts, inode)` do arquivo de mídia, lida de
  `fotoorganizer/security/hashing.py:20-29` (`quick_signature`, hash) e das
  colunas `MediaFile.tamanho`/`mtime`/`inode`. Um `.xmp` editado depois da
  indexação não muda nada disso — fica invisível até `scan --reprocessar`
  reler o acervo inteiro (`scanner.py:168`, citado no prompt de origem).

## O que este item entrega

`lib.py`, em dois blocos:

1. **Resolução reversa** — `resolver_sidecar(caminho_xmp, conhecidos)`
   testa as duas convenções (Adobe: remove só `.xmp` do nome completo;
   darktable/Lightroom: `stem` sem extensão, testado contra todo arquivo
   conhecido na mesma pasta com o mesmo `stem`) contra um `frozenset` de
   caminhos já catalogados — nunca uma consulta ao banco por candidato.
   Devolve `ResolucaoSidecar(xmp, midia, ambiguo)`: `ambiguo=True` quando
   mais de um candidato responde (ex.: `foto.jpg` E `foto.cr3` na mesma
   pasta) — o resolvedor NÃO adivinha, mesma regra do mecanismo original.
2. **O gatilho** — `AssinaturaConhecida(mtime_sidecar, mtime_midia)` +
   `classificar(...)` decide entre cinco casos
   (`CasoDeteccao.SEM_MUDANCA/SIDECAR_NOVO/SO_SIDECAR_MUDOU/MIDIA_MUDOU/
   AMBOS_MUDARAM`) comparando o par atual de mtimes com o último
   conhecido. `precisa_reenfileirar(caso)` é `True` para todos os casos
   MENOS `MIDIA_MUDOU` sozinho — que o scan incremental normal já cobre;
   reenfileirar de novo ali seria trabalho duplicado, não uma cobertura a
   mais.

## Decisões (Classe A, ver também `docs/DECISOES.md`)

1. **Só `mtime` na assinatura do sidecar, não `(tamanho, mtime, inode)`
   completo como a mídia usa.** `.xmp` é texto/XML pequeno — tamanho varia
   pouco entre edições e alguns editores reescrevem o arquivo inteiro
   (inode muda, mtime sempre muda). `mtime` sozinho é o sinal barato e
   suficiente; documentado no docstring de `AssinaturaConhecida` para
   quem for integrar não estranhar a assimetria com `quick_signature`.
2. **Ambiguidade nunca escolhe — devolve `ambiguo=True` e para.** É a
   armadilha citada explicitamente no prompt de origem (seção "o que falha
   primeiro"): "`foto.xmp` casando com o `foto.jpg` errado numa pasta com
   `foto.jpg` e `foto.cr3`". A decisão de como resolver (perguntar ao
   usuário, logar e pular, preferir uma extensão) fica para quem integrar
   — este módulo só garante que a ambiguidade nunca vira palpite silencioso.
3. **`resolver_sidecar` recebe `conhecidos` já filtrado pela mesma pasta.**
   Mantém a função pura e barata (comparação em memória, sem depender de
   como o cache real é montado); quem integrar decide se o cache é
   por-pasta ou global com filtro embutido.

## Onde plugar quando a fronteira abrir

- **Descoberta**: `fotoorganizer/scanner/discovery.py` — a função que hoje
  usa `supported_extensions()` do extrator ativo (comentário em
  `metadata/purepython.py:46-50`: "a descoberta só enumera o que está
  nesta lista") precisa enumerar `EXTENSOES_SIDECAR` num segundo conjunto,
  SEM criar linha em `media_files` para eles — o prompt de origem já
  registra essa distinção ("sidecar não é acervo").
- **Scanner incremental**: `fotoorganizer/scanner/scanner.py`, no mesmo
  ponto de `_unchanged_sig`/`_carregar_conhecidos` (`:281-283`,
  `:384-402`) — junto da assinatura da mídia, carregar também
  `mtime` do `.xmp` irmão (via `_sidecar_de`, que já existe) e chamar
  `classificar(...)`. Quando `precisa_reenfileirar` for `True`, reenfileirar
  SÓ o arquivo principal casado por `resolver_sidecar` — não o acervo
  inteiro.
- **Persistência da assinatura do sidecar**: não existe coluna hoje. A
  integração real precisa de um lugar para guardar `mtime_sidecar`
  conhecido por mídia — candidatos naturais são uma coluna nova em
  `MediaFile` (`sidecar_mtime: Mapped[float | None]`, migração Alembic
  nova) ou uma entrada em `metadata_entries` com `namespace="xmp_sidecar"`
  e `chave="mtime"` (reaproveitando o namespace que `exiftool.py:213` já
  usa para as tags do sidecar, sem coluna nova). A escolha entre as duas é
  decisão de quem integrar, não deste item de staging.

## Limitação em aberto, herdada do prompt de origem

Um `.xmp` **apagado** não é detectado pelo caminho incremental — nem
`resolver_sidecar` nem `classificar` são chamados para um arquivo que
sumiu, porque a descoberta simplesmente não o enumera mais naquela
passada. Só um rescan forçado reflete a remoção. Para este projeto a
resposta é provavelmente o invariante 8 (`CLAUDE.md`) aplicado a metadado:
sidecar que some não desfaz o que já foi lido — a entrada em
`metadata_entries` com origem `xmp_sidecar` continua, dizendo de onde
veio. Fica como pergunta em aberto, exatamente como o prompt de origem
registra — não implementada aqui.
