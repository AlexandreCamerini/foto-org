# Registro de decisões

Uma entrada por decisão, em ordem cronológica. Formato e classes em
`docs/prompts/00-protocolo.md`.

## D-001 — Autonomia cobre documentos e protótipos, não código de produção
- Fase: desenho do processo
- Classe: B
- Data: 2026-07-29
- Contexto: o dono concedeu autonomia para decidir na ausência dele, mas o
  escopo da autonomia não estava definido — decidir o desenho ou também
  implementá-lo.
- Opções: (a) autonomia total, incluindo alterar `fotoorganizer/` e
  `webapp/`; (b) autonomia sobre `docs/**` e `docs/prototipos/**`, código de
  produção atrás de aprovação; (c) esperar resposta antes de qualquer coisa.
- Escolhida: (b)
- Por quê: o entregável pedido é avaliação. Alterar o núcleo durante um
  diagnóstico mistura duas coisas com custos de reversão muito diferentes:
  um documento errado se reescreve, uma migração aplicada e um refactor no
  motor de classificação não.
- Como reverter: trocar a seção "Fronteira do que pode ser alterado" do
  protocolo e reexecutar a fase que precisar de código.
- Status: decidido por timeout

## D-002 — O timeout de 10 minutos não vale para ação irreversível ou externa
- Fase: desenho do processo
- Classe: A
- Data: 2026-07-29
- Contexto: "siga com a decisão recomendada em 10 minutos" aplicado
  literalmente autorizaria seguir sozinho em coisas que não têm volta.
- Opções: (a) timeout para tudo; (b) timeout só para decisão de desenho,
  com uma classe que sempre espera.
- Escolhida: (b) — classe C do protocolo: arquivo original de foto, operação
  física fora de dry-run, catálogo real, `git push`, envio de dado para fora
  da máquina, instalação de dependência de sistema.
- Por quê: autonomia útil é autonomia sobre decisão reversível. Um bloqueio
  de classe C nunca para o resto da fase, então o custo dessa exceção é
  baixo e o custo de não tê-la é alto.
- Como reverter: editar a lista de classe C no protocolo.
- Status: decidido

## D-003 — Um arquivo de prompt por fase, com protocolo compartilhado
- Fase: desenho do processo
- Classe: A
- Data: 2026-07-29
- Contexto: as seis fases podiam virar um documento só ou seis
  auto-contidos.
- Opções: (a) um documento único; (b) seis prompts + `00-protocolo.md`.
- Escolhida: (b)
- Por quê: cada fase roda em sessão limpa, com só o contexto de que precisa.
  Um documento único carrega as seis fases em toda execução e as regras
  comuns ficariam repetidas seis vezes ou implícitas.
- Como reverter: concatenar os arquivos.
- Status: decidido

## D-004 — IA embarcada é superfície de produto, com três restrições
- Fase: 5
- Classe: B
- Data: 2026-07-29
- Contexto: o princípio AI-first "não construa seu próprio agente" recomenda
  não colocar chamadas de LLM no código da aplicação. A fase 5 pede
  exatamente análise de IA dentro do produto.
- Opções: (a) seguir o princípio e manter a IA fora do app, só no agente de
  desenvolvimento; (b) inverter o princípio para produto comercial,
  preservando a preocupação por trás dele como restrição.
- Escolhida: (b), com três restrições na fase 5 — regra determinística
  primeiro; nenhuma infraestrutura de agente caseira, inferência atrás dos
  `Protocol` existentes; saída de modelo entra como evidência, nunca como
  decisão automática.
- Por quê: o princípio foi escrito para ferramenta pessoal, onde a IA é meio.
  Num DAM comercial a inferência é o valor entregue. A preocupação real do
  princípio — não reinventar orquestração e não perder o determinismo —
  continua válida e virou restrição.
- Como reverter: se a medição mostrar que as regras determinísticas cobrem o
  caso de uso, a fase 5 pode concluir que nenhum modelo entra no produto.
  A conclusão está explicitamente permitida no prompt.
- Status: decidido por timeout

## D-005 — Fase 6 pode rodar em paralelo às fases 3 a 5
- Fase: 6
- Classe: A
- Data: 2026-07-29
- Contexto: a ordem numérica sugeria execução sequencial das seis fases.
- Opções: (a) sequencial estrito; (b) 6 em paralelo a partir da fase 2.
- Escolhida: (b)
- Por quê: a avaliação de UX depende do estado atual do webapp e da auditoria
  da fase 2, não do modelo de metadados nem do plano de IA. Serializar custa
  tempo sem reduzir risco.
- Como reverter: rodar na ordem numérica.
- Status: decidido

## D-006 — Fase 1 executada sem subagente
- Fase: 1
- Classe: A
- Data: 2026-07-29
- Contexto: o protocolo permite até 2 subagentes por fase para varredura ampla.
- Opções: (a) dois subagentes, um por metade do código; (b) execução direta.
- Escolhida: (b)
- Por quê: a varredura é ampla mas não independente — cada achado do esquema
  informa a leitura do servidor e vice-versa. Subagente devolveria relatório
  que eu teria de reler inteiro.
- Como reverter: não se aplica; a fase está concluída.
- Status: decidido

## D-007 — `docs/ARQUITETURA.md` não foi corrigido nesta fase
- Fase: 1
- Classe: A
- Data: 2026-07-29
- Contexto: a avaliação encontrou divergências entre `docs/ARQUITETURA.md` /
  `CLAUDE.md` e o código (`SyncProvider` inexistente, dois protocolos não
  documentados, handlers com quatro consultas diretas).
- Opções: (a) corrigir os documentos junto da avaliação; (b) registrar a
  divergência na avaliação e deixar a correção para quem implementar.
- Escolhida: (b)
- Por quê: `CLAUDE.md` está fora da fronteira do protocolo, e a correção certa
  depende de decisão de produto — se sync entra no roadmap, `SyncProvider`
  passa a ser código a escrever, não linha a apagar.
- Como reverter: editar os dois documentos após a decisão sobre sync.
- Status: decidido

## D-008 — Quatro lacunas de esquema classificadas como não-bloqueio de MVP
- Fase: 1
- Classe: B
- Data: 2026-07-29
- Contexto: faltam derivados/linhagem pai-filho, hierarquia de tags, direitos
  de uso e coleções curadas — mesa posta em DAM maduro.
- Opções: (a) migrar agora as quatro; (b) migrar agora só as duas baratas
  (`media_files.parent_id`, `tags.parent_id`) e adiar direitos e coleções;
  (c) registrar todas e não migrar nada nesta rodada.
- Escolhida: (c) para esta fase, recomendando (b) para a primeira rodada de
  implementação.
- Por quê: migração está fora da fronteira do protocolo. As duas baratas ficam
  substancialmente mais caras depois de 500 mil linhas catalogadas, então a
  recomendação é fazê-las antes do primeiro acervo grande — e direitos de uso
  depende do que a fase 3 decidir sobre colunas tipadas.
- Como reverter: as migrações são aditivas; nenhuma perde dado.
- Status: decidido por timeout

## D-009 — `AGENTS.md` deveria ser symlink de `CLAUDE.md`
- Fase: 1
- Classe: A
- Data: 2026-07-29
- Contexto: os dois arquivos são byte-a-byte idênticos (132 linhas, 7.748
  bytes) e independentes — duas fontes de verdade que divergem na primeira
  edição.
- Opções: (a) symlink; (b) manter e sincronizar à mão; (c) apagar um.
- Escolhida: (a), recomendado — não executado, `CLAUDE.md` e `AGENTS.md` estão
  fora da fronteira desta fase.
- Por quê: symlink preserva as duas convenções de nome sem duplicar conteúdo.
- Como reverter: `cp` de volta.
- Status: aguardando (fora da fronteira)

## D-010 — Catálogo isolado por redirecionamento de `HOME`
- Fase: 2
- Classe: A
- Data: 2026-07-29
- Contexto: a fase exige exercitar o app de ponta a ponta, e o catálogo real do
  dono (31 MB) é classe C. O CLI não tem `--data-dir` nem `--config`.
- Opções: (a) editar o `config.toml` real temporariamente; (b) redirecionar
  `HOME` para um diretório temporário; (c) não exercitar e auditar só por
  leitura de código.
- Escolhida: (b)
- Por quê: tudo em `config/paths.py` deriva de `Path.home()`, então o
  redirecionamento isola catálogo, cache, config e logs de uma vez, sem editar
  nenhum arquivo do dono. (a) mexeria em config real; (c) não responderia a
  pergunta da fase.
- Como reverter: apagar o diretório temporário; nada fora dele foi tocado.
- Status: decidido

## D-011 — Execução de plano não foi exercitada
- Fase: 2
- Classe: C
- Data: 2026-07-29
- Contexto: o fluxo de operações foi verificado até o dry-run. Executar copiaria
  arquivos de verdade, ainda que para um diretório temporário.
- Opções: (a) executar contra destino temporário; (b) parar no dry-run.
- Escolhida: (b)
- Por quê: "operação física fora de dry-run" está na classe C do protocolo, sem
  ressalva de destino. A leitura disciplinada é parar, mesmo quando o risco
  concreto é baixo — a regra vale pelo hábito que cria.
- Como reverter: rodar `POST /api/operacoes/{id}/executar` no catálogo isolado
  quando o dono autorizar.
- Status: aguardando (classe C)

## D-012 — `npm install` no worktree tratado como classe A
- Fase: 2
- Classe: A
- Data: 2026-07-29
- Contexto: `webapp/node_modules` não existia no worktree, e sem ele os passos
  3 e 4 de `verificar.sh` não rodam nem o webapp sobe.
- Opções: (a) tratar como dependência de sistema (classe C) e não instalar;
  (b) instalar, por ser escopo de projeto.
- Escolhida: (b)
- Por quê: a classe C fala de dependência **de sistema**. `node_modules` é
  local ao projeto, gitignorado e reversível com `rm -rf` — não altera o
  ambiente do dono fora do worktree.
- Como reverter: `rm -rf webapp/node_modules`.
- Status: decidido

## D-013 — Capturas de tela não versionadas
- Fase: 2
- Classe: B
- Data: 2026-07-29
- Contexto: o protocolo pede captura em `docs/capturas/`. As capturas foram
  feitas e analisadas na sessão, mas a ferramenta de navegador entrega a imagem
  em contexto e não grava arquivo.
- Opções: (a) montar um caminho de captura headless só para persistir PNG;
  (b) transcrever no relatório o que cada captura mostra, com a saída de SQL e
  de API como evidência durável.
- Escolhida: (b)
- Por quê: para os achados desta fase, a saída de SQL e da API é evidência mais
  forte que a imagem — mostra a causa, não só o sintoma. Montar captura
  headless custaria mais que o valor que agrega aqui. A fase 6, que é visual
  por natureza, precisa resolver isso de verdade.
- Como reverter: refazer as capturas com ferramenta que grave em disco.
- Status: decidido por timeout

## D-014 — `design-mirror` substituído por extração via navegador
- Fase: 6 (preparação)
- Classe: A
- Data: 2026-07-29
- Contexto: a skill `brightdata-plugin:design-mirror` exige
  `BRIGHTDATA_API_KEY` e uma zona Unlocker; nenhuma das duas existe no
  ambiente, e o CLI `bdata` não está instalado.
- Opções: (a) pedir ao dono que crie conta e chave de API na Bright Data;
  (b) extrair os tokens abrindo os sites no navegador e lendo o estilo
  computado.
- Escolhida: (b)
- Por quê: `getComputedStyle` na página viva entrega o valor que o usuário
  realmente vê, enquanto o HTML raspado precisa ser interpretado. Não envolve
  terceiro, não exige conta, e é mais preciso. Pedir chave de API ao dono para
  um levantamento que o navegador já resolve seria custo sem ganho.
- Como reverter: configurar as variáveis e rodar a skill como documentada.
- Status: decidido

## D-015 — Peakto rejeitada como referência visual
- Fase: 6 (preparação)
- Classe: B
- Data: 2026-07-29
- Contexto: o dono pediu comparação das três referências antes de escolher. A
  extração mostrou que cyme.io usa Roboto + Fjalla One condensada, ciano sobre
  preto e corpo a 19px/34px — estética de site de agência.
- Opções: (a) espelhar Peakto por ser o concorrente mais próximo; (b) rejeitar
  como referência visual e manter só como referência de arquitetura de
  informação; (c) espelhar as três e mediar.
- Escolhida: (b)
- Por quê: espelhar cyme.io deixaria o app mais parecido com página web, que é
  o oposto do problema relatado. A proximidade funcional de Peakto está na
  organização das fontes, não na aparência do site institucional.
- Como reverter: o comparativo em `docs/REFERENCIAS_DESIGN.md` tem os tokens
  extraídos; basta escolher outra composição.
- Status: decidido por timeout

## D-016 — Fronteira aberta para as quatro correções curtas
- Fase: correções pós-auditoria
- Classe: B
- Data: 2026-07-30
- Contexto: D-001 manteve `fotoorganizer/` e `webapp/` fora da fronteira até
  aprovação. O dono aprovou explicitamente os itens 1, 3, 4 e 7 da auditoria.
- Opções: (a) abrir a fronteira só para esses quatro itens; (b) abrir para
  código de produção em geral.
- Escolhida: (a)
- Por quê: a aprovação foi para uma lista nomeada, não para o diretório. As
  fases 3 a 6 seguem entregando documento até o dono decidir o contrário —
  em especial a migração Alembic da fase 3, que é o que custa caro desfazer.
- Como reverter: os quatro commits são independentes e revertem isolados.
- Status: decidido

## D-017 — Confiança como quantidade, não como semáforo
- Fase: 6
- Classe: B
- Data: 2026-07-30
- Contexto: hoje o nível é um badge colorido ("Média" em âmbar) que não leva a
  lugar nenhum. Precisa virar superfície de entrada da evidência.
- Opções: (a) manter semáforo de três cores, tornando-o clicável; (b) três
  segmentos preenchidos, neutros, com cor só na confiança baixa; (c) percentual
  numérico.
- Escolhida: (b)
- Por quê: numa ferramenta de foto, três cores saturadas competem com a
  imagem — contraria "a foto é a cor da interface". Cor como canal único
  também falha para daltônicos. Quantidade resolve os dois, e reservar a cor
  para a confiança baixa faz o pouco de cor que sobra significar "olhe aqui".
  (c) sugere precisão que o modelo do docs/CONFIANCA.md não tem: o score é
  elo mais fraco, não medida contínua.
- Como reverter: é uma regra de CSS mais o rótulo; nada no modelo de dados.
- Status: decidido por timeout

## D-018 — A unidade de decisão da Revisão passa a ser o grupo
- Fase: 6
- Classe: B
- Data: 2026-07-30
- Contexto: com 63 linhas indistinguíveis, a única ação racional é "Aprovar
  todas" — que é o que a tela oferece no topo. A tela empurra para o
  comportamento que ela deveria evitar.
- Opções: (a) manter lista plana e enriquecer cada linha; (b) agrupar por
  destino sugerido, com aprovação em lote por grupo e desdobramento sob
  demanda; (c) uma foto por vez, em tela cheia.
- Escolhida: (b)
- Por quê: "aprovar as 22 de Viagens/2024 - França" é uma decisão que o usuário
  consegue tomar com a informação que tem; "aprovar a linha 37 de 63" não é.
  (a) melhora a linha mas mantém 63 decisões; (c) não escala para acervo
  grande.
- Como reverter: o desdobramento já mostra a lista plana dentro do grupo.
- Status: decidido por timeout

## D-019 — `defusedxml` declarado, não instalado
- Fase: 3
- Classe: C (respeitada)
- Data: 2026-07-30
- Contexto: o Pillow só analisa XMP com um parser de XML endurecido. O venv é
  compartilhado com o checkout principal, e o dono estava dormindo.
- Opções: (a) instalar no venv; (b) declarar como extra opcional e degradar
  em silêncio; (c) não implementar XMP.
- Escolhida: (b)
- Por quê: instalar num venv compartilhado é alterar o ambiente do dono sem
  ele. (c) desperdiçaria o achado. Com (b), IPTC — que é a metade que não
  precisa de nada — entra hoje, e XMP liga com um comando.
- Como reverter: `pip install -e '.[xmp]'` liga; remover o extra desliga.
- Status: aguardando (classe C)

## D-020 — exiftool não entra nesta rodada
- Fase: 3
- Classe: C (respeitada)
- Data: 2026-07-30
- Contexto: não está instalado; instalar é alterar o ambiente do dono.
- Opções: (a) instalar e medir; (b) implementar o extrator às cegas;
  (c) implementar Python puro agora e deixar a medição pronta.
- Escolhida: (c)
- Por quê: (b) escreveria código que não dá para verificar. (c) entrega IPTC
  e XMP hoje e transforma "exiftool lê mais" de folclore em número quando o
  dono instalar — `scripts/medir_exiftool.py` compara tag a tag por formato.
- Como reverter: `brew install exiftool` e rodar o script.
- Status: aguardando (classe C)

## D-021 — Precedência XMP → IPTC → EXIF
- Fase: 3
- Classe: B
- Data: 2026-07-30
- Contexto: o mesmo campo (autor, direitos, legenda, data) aparece em até três
  padrões, e agora os três chegam ao banco.
- Opções: (a) EXIF primeiro, por ser o do momento do disparo; (b) XMP → IPTC →
  EXIF; (c) sem precedência — guardar os três e nunca escolher.
- Escolhida: (b), com (c) preservado por baixo
- Por quê: XMP costuma ser o mais recentemente escrito (o editor grava ao
  salvar), IPTC vem de quem cataloga profissionalmente, e o EXIF é o que a
  câmera pôs e ninguém revisou. Mas a precedência só decide o valor canônico:
  cada leitura continua sendo evidência com origem própria, então a
  divergência fica visível em vez de resolvida em silêncio.
- Como reverter: a ordem é uma lista; os três valores continuam no banco.
- Status: decidido por timeout (não implementado — depende de D-023)

## D-022 — Advisor sobe para Opus 5 com `thinking` desligado
- Fase: 5
- Classe: A
- Data: 2026-07-30
- Contexto: `MODELO_PADRAO` estava em `claude-opus-4-8`, uma geração atrás.
  A troca não é drop-in: o advisor não passava `thinking`, e o significado
  disso mudou — no 4.8 omitir era não pensar, no Opus 5 é pensar, e
  `max_tokens` cobre raciocínio mais resposta.
- Opções: (a) deixar em 4.8; (b) subir para Opus 5 sem mais nada;
  (c) subir com `thinking: disabled` explícito.
- Escolhida: (c)
- Por quê: (b) truncaria o JSON no meio com `max_tokens=1024`. A tarefa é
  rotular metadados em três categorias — não é onde raciocínio longo paga, e
  desligar também é mais barato.
- Como reverter: uma constante e um parâmetro.
- Status: decidido

## D-023 — Colunas tipadas de direitos e autoria ficam para depois da medição
- Fase: 3 e 5
- Classe: B
- Data: 2026-07-30
- Contexto: com IPTC lido, autor, direitos, licença e crédito existem no banco
  sem ter onde morar — ficam em `metadata_entries`, não filtráveis.
- Opções: (a) migrar agora as quatro colunas; (b) esperar medir quantas chaves
  por foto um acervo real produz.
- Escolhida: (b)
- Por quê: a decisão certa depende do volume, e o volume só se mede com
  exiftool instalado ou com o acervo real — as duas coisas são classe C.
  Migrar antes é adivinhar o formato; a migração é aditiva e barata agora,
  cara com 500 mil linhas já escritas.
- Como reverter: não se aplica; nada foi migrado.
- Status: decidido por timeout

---

## D-024 — Registro que não é acervo é rebaixado, nunca apagado

- Data: 2026-07-31
- Contexto: o scanner entrou no pacote `Photos Library.photoslibrary` e
  catalogou 45.822 miniaturas internas do Apple Fotos (540×360 e semelhantes)
  como se fossem fotos. Elas representavam 89% do acervo local e inundaram a
  revisão: 45.822 das 51.280 sugestões pendentes eram sobre miniatura.
- Opções: (a) apagar as 45.822 do catálogo; (b) rebaixá-las a fonte de sinal,
  fora da grade, da revisão e do plano, mas dentro da correlação.
- Escolhida: (b), e o dono elevou isso a invariante 8 do `CLAUDE.md`.
- Por quê: medido em cópia do catálogo real, apagar derruba as fotos de
  verdade com lugar estimado de **2.117 para 162**. As miniaturas carregam
  GPS que as referências do `osxphotos` não reportam — são a única testemunha
  do lugar de fotos que não têm coordenada própria (nenhum dos 5.601 arquivos
  reais do acervo tem GPS no arquivo). Rebaixar entrega o mesmo alívio na
  revisão (5.458 pendentes) sem perder nada.
- Como reverter: o campo `papel` volta a `acervo` com um UPDATE; nenhuma
  linha foi removida, então não há o que restaurar.
- Status: decidido pelo dono

---

## D-025 — A janela da herança depende do que se herda

- Data: 2026-07-31
- Contexto: 5.434 das 5.601 fotos do acervo do dono não têm lugar nenhum —
  nenhuma tem GPS no arquivo. A janela única de 10 minutos alcança 167. A
  doadora mais próxima de outra origem está a 10–30 min de 762 delas, a
  30 min–2 h de 1.998 e a 2–12 h de outras 2.235.
- Opções: (a) manter 10 min; (b) alargar para 30 min; (c) uma janela por
  campo — cidade em minutos, região em horas, país em mais horas.
- Escolhida: (c).
- Por quê: a granularidade do que dá para afirmar depende do intervalo. Em
  duas horas se troca de cidade, não de país. A janela única era obrigada a
  adotar o limite da cidade e, com isso, jogava fora a informação de país que
  seria segura para milhares de fotos. Uma sugestão errada com aparência de
  fundamentada é pior que nenhuma — e afirmar "Brasil" quando só dá para
  afirmar "Brasil" é o oposto disso.
- Janelas: cidade 10 min, região 2 h, país 12 h. A busca pela doadora usa a
  maior; cada campo entra na evidência só se couber na sua.
- Como reverter: `JANELAS_POR_CAMPO` em `grouping/correlacao.py` volta a um
  valor único; nada é persistido de forma irreversível — regerar refaz.
- Status: decidido pelo dono

---

## D-026 — exiftool passa a ser o extrator padrão quando instalado

- Data: 2026-07-31
- Contexto: o `ExifToolExtractor` que a arquitetura previa desde o começo
  nunca foi construído, e o fallback puro-Python vinha sendo tratado como
  teto. Num acervo real, 2.949 CR3 ficaram sem `Make`/`Model`: o libraw
  entrega abertura, ISO e obturador, não a câmera.
- Opções: (a) manter o puro-Python e aceitar a lacuna; (b) exiftool como
  extra opt-in; (c) exiftool como padrão quando o binário existir.
- Escolhida: (c), com fallback automático.
- Por quê: medido em 40 CR3 do acervo real — câmera identificada 0/40 → 40/40,
  tags 320 → 14.440, e **mais rápido**: 285 ms → 67 ms por arquivo, porque o
  exiftool lê cabeçalho onde o libraw decodifica o RAW inteiro. Não há
  trade-off a ponderar; sem câmera não há correção de deriva de relógio nem
  "outra origem" na herança de GPS, e a lacuna se propaga para a
  classificação inteira.
- Como reverter: `criar_extrator(preferir_exiftool=False)` devolve o
  puro-Python; nada no catálogo depende de qual extrator gravou.
- Status: decidido pelo dono (instalou o binário a pedido)

---

## D-027 — MakerNotes fica fora da base bruta

- Data: 2026-07-31
- Contexto: o extrator novo (D-026) passou a gravar o bloco proprietário do
  fabricante. Num acervo real eram 969.074 linhas — 83% de todo o metadado e
  51,8 MB de texto, contra 4,8 MB de EXIF.
- Opções: (a) manter tudo; (b) manter só campos selecionados do bloco;
  (c) excluir o namespace da base bruta.
- Escolhida: (c).
- Por quê: o bloco descreve o estado interno da câmera — modo de foco,
  posição do estabilizador, contador do obturador, temperatura do sensor — e
  nada ali ajuda a decidir viagem, evento ou lugar, que é o que este app faz.
  A opção (b) exigiria manter uma lista por fabricante, e o único campo que
  interessava (`LensType`) já é lido para a coluna `lente`, do JSON inteiro,
  sem depender da base bruta. Medido: catálogo de 164 MB para 51 MB.
- Como reverter: devolver `"MakerNotes": "makernotes"` a `_GRUPOS` em
  `metadata/exiftool.py` e rodar `scan --reprocessar`. O rótulo legível
  continua em `ROTULOS_NAMESPACE`, à espera.
- Status: decidido pelo dono

---

## D-028 — Lightroom entra como fonte externa, e é a principal do discovery

- Data: 2026-07-31
- Contexto: o dono corrigiu uma premissa que eu vinha usando errada — o
  catálogo não é o acervo. O acervo é desconhecido, grande, e espalhado por
  um NAS e HDs externos antigos. Descobri-lo é o objetivo do app, não um
  detalhe.
- Opções: (a) varrer discos quando montados; (b) ler o catálogo do Lightroom;
  (c) as duas.
- Escolhida: (b) primeiro, (a) depois.
- Por quê: o `.lrcat` responde **com os discos desligados**. Medido no acervo
  real: 54.086 fotos conhecidas, 45.397 delas num volume desmontado. Uma
  varredura de disco encontraria zero. E o catálogo traz o que o dono
  decidiu — nota, sinalização, coleção, palavra-chave — que é intenção
  declarada, não inferência nossa.
- Forma: referência, nunca acervo. Nenhum byte de imagem é aberto; o valor
  está em saber que a foto existe, onde estava e o que se sabe dela. O
  `.lrcat` é lido com `immutable=1`: sem lock, sem journal, sem escrita, com
  o Lightroom aberto ao lado (invariante 1).
- Junto: `ExternalAsset` ganhou `caminho_original` — sem ele uma referência
  sabe a data e o GPS e não sabe dizer de que disco veio, que é justamente a
  pergunta do discovery.
- Como reverter: remover a fonte do catálogo; nada mais depende dela.
- Status: decidido pelo dono

---

## D-029 — Câmera com receptor de GPS é sinal diferente de coordenada de celular

- Data: 2026-07-31
- Contexto: o dono informou que algumas Canon têm GPS embutido. Confirmado no
  catálogo do Lightroom: das 58 câmeras do acervo (2001–2026), só a **EOS 5D
  Mark IV** grava coordenada de receptor próprio — 2.878 de 3.633 fotos, 79%.
  A R6m2 tem 248 de 8.366 (3%), que vêm de pareamento com o celular. As
  demais, incluindo Rebel XSi (17.132) e 5D Mark III (11.235), têm zero.
- Decidido: registrar agora que essas duas origens têm confiabilidade
  diferente e que o motor hoje trata as duas como "GPS lido do arquivo",
  confiança alta.
- Por quê: coordenada de celular pareado tem deriva que um receptor embutido
  não tem, e o modelo de evento vai usar deslocamento entre blocos de fotos
  para separar acontecimentos. Uma deriva de centenas de metros lida como
  deslocamento real produz corte onde não houve.
- Consequência maior, e não prevista: **25 anos de acervo e só 4 com GPS**.
  Para 2001–2018 não há coordenada própria nem doador para herdar. Nesse
  período, nome de pasta e álbum não são sinal auxiliar — são o único sinal
  de lugar que existe.
- Como reverter: nada foi implementado; é contexto para o modelo de evento.
- Status: registrado, aguardando o modelo de evento

---

## D-030 — Álbum nomeia, não divide

- Data: 2026-07-31
- Contexto: eu ia usar as 25.304 nomeações de álbum como fronteira de evento.
- Medido: os álbuns se aninham. No mesmo dia, "Férias" (431), "Portugal e
  Italia com as Meninas" (235) e "Family" (177) são a MESMA foto contada três
  vezes, em 29 dias do acervo.
- Decidido: álbum entra como nome e como evidência de intenção; nunca como
  divisor de acontecimento.
- Como reverter: não se aplica; a alternativa produziria eventos sobrepostos.
- Status: decidido por medição

---

## D-031 — O mapa do lugar estimado nasce sem tiles

- Fase: 9 (docs/prompts/fase-9-mapa-e-prioridades.md, Problema 2)
- Classe: B
- Data: 2026-08-01
- Contexto: o protótipo `docs/prototipos/03-mapa-local-estimado.html` fechou
  decidindo a linguagem visual do lugar estimado (ponto cheio × vazado, traço
  até a doadora) e deixou em aberto de onde vem o mapa de verdade — decisão
  que ele mesmo apontou não ser de direção de arte. Pedir um tile a um
  servidor externo por coordenada revela a esse servidor onde cada foto foi
  tirada, foto a foto — é o invariante 4 do `CLAUDE.md` (nada sai da máquina
  sem opt-in) se aplicando a um caminho que ainda não tinha sido nomeado.
- Opções: (a) tiles de um serviço externo (Mapbox/OSM tile server), com cache
  local e consentimento explícito antes da primeira requisição; (b) tiles
  vetoriais embarcados offline (ex.: recorte de OpenStreetMap por região,
  dezenas a poucas centenas de MB conforme a área coberta pelo acervo); (c)
  nenhuma cartografia real — pontos, círculos de incerteza e o traço até a
  doadora desenhados sobre uma malha esquemática, como o próprio protótipo já
  fez de propósito.
- Escolhida: (c) agora; (b) fica candidata em `docs/ROADMAP.md` v2+ para
  quando houver pedido concreto de "ver no mapa de verdade".
- Por quê: (c) tem custo zero — sem dependência nova, sem MB de tile
  embarcado, sem requisição de rede nenhuma ao abrir a tela — e entrega a
  maior parte do valor do problema, que é mostrar a incerteza do lugar
  estimado, não desenhar ruas. (a) está fora por violar o invariante 4 sem
  necessidade: a informação nova desta fase é o raio de incerteza, não a
  cartografia. (b) resolveria sem vazar nada, mas o custo em disco (a
  estimar por região coberta) só se justifica se a interface esquemática se
  mostrar insuficiente na prática.
- Como reverter: trocar o componente de desenho por um que carregue tiles de
  (b) ou (a); nenhum dado persistido depende desta escolha, ela é só de
  apresentação.
- Status: decidido pelo orquestrador, sem objeção do dono no momento da
  execução (sessão interativa, decisão comunicada no plano antes do
  despacho).

---

## D-032 — O raio de incerteza é medido, não suposto pela janela de D-025

- Fase: 9 (docs/prompts/fase-9-mapa-e-prioridades.md, Problema 1)
- Classe: A
- Data: 2026-08-01
- Contexto: D-025 fixou janelas de granularidade por campo (cidade 10 min,
  região 2 h, país 12 h) como texto — "em duas horas se troca de cidade, não
  de país". Esta fase precisava da mesma ideia como número: um raio em
  metros que o mapa desenha como círculo ao redor do ponto herdado. A
  hipótese de partida era ancorar o teto do raio na janela de país (12 h),
  o que daria ~259 km.
- Medido: 2.083 pares reais do acervo em que as duas fotos têm GPS próprio e
  vieram de fontes diferentes — a mesma regra de escolha de doadora que
  `herdar_gps` usa. Para cada par, a distância real entre as duas fotos foi
  comparada ao raio que a fórmula proporia para aquele Δt. Achado central: a
  distância real **satura** antes do teto suposto — o p90 da banda 6–12 h
  (25 km) é *menor* que o p90 da banda 30 min–2 h (39 km). Quem fotografa o
  dia inteiro passa o dia na mesma região; a janela de país nunca é
  alcançada na prática.
- Escolhida: `raio(Δt) = min(50 km, max(15 m, 6 m/s × Δt))` — piso na
  precisão do receptor GPS, teto no platô medido (50 km), não na janela de
  12 h. Cobertura: 93,6% ponderada por Δt (96,2% por dia; bootstrap p5:
  92,4%) — acima do piso de 90% fixado no prompt da fase.
- Por quê: um teto derivado da janela de país (259 km) teria a mesma
  cobertura medida (93,6%) e um círculo grande demais para informar
  qualquer coisa — a mesma armadilha que D-025 já havia nomeado ("sugestão
  errada com aparência de fundamentada é pior que nenhuma"), aqui aplicada
  ao raio em vez de ao texto da evidência.
- Não modelado: quando a hora de um dos lados vem do mtime do arquivo
  (`Heranca.hora_incerta`), o Δt pode estar errado por anos — nenhum
  multiplicador foi inventado para esse caso sem dado que o sustente; quem
  avisa é a confiança da evidência, não o tamanho do círculo.
- Achado à parte, não resolvido aqui: dos ~6,4% de pares fora do raio, um
  grupo específico (2019-04-19) tem a doadora com coordenada **errada** — o
  Apple Fotos marca a foto em casa, no Rio, no mesmo segundo em que a
  câmera está a 163 km, em Penedo. Nenhum raio conserta doadora errada;
  ficou registrado como tarefa separada (qualidade da doadora), não como
  ajuste de fórmula.
- Como reverter: `VELOCIDADE_PLAUSIVEL_MS`, `RAIO_PISO_M`, `RAIO_TETO_M` em
  `fotoorganizer/grouping/correlacao.py`; `scripts/calibrar_raio_incerteza.py`
  refaz a medição contra o catálogo atual. Nada persistido depende do raio —
  ele é calculado na leitura, nunca gravado.
- Status: decidido por medição.

---

## D-033 — Foto fora de alcance continua no mapa, com o motivo anexado

- Fase: 9 (endpoint `/api/mapa`)
- Classe: A
- Data: 2026-08-01
- Contexto: o plano original pedia que foto fora de alcance (arquivo
  inalcançável — volume desmontado, biblioteca só no iCloud) ficasse fora da
  lista de pontos do mapa, e fosse só contada. Medido: o evento "Pantanal"
  tem 80 das 97 fotos em `/Volumes/Externo`, hoje desligado — excluí-las do
  mapa devolveria uma tela vazia com 80 coordenadas conhecidas no catálogo.
- Decidido: o ponto é desenhado normalmente (coordenada, raio, doadora), leva
  `motivo_indisponivel` no payload para a tela explicar por que não há
  miniatura, e é contado separadamente em `fora_de_alcance` — que é
  subconjunto de `no_mapa`, não soma com ele.
- Por quê: o disco desligado tirou o arquivo, não a coordenada. Esconder o
  ponto apagaria da tela justamente o que o catálogo preservou — é o
  invariante 8 (nada que possa ser referência real de uma foto é apagado)
  aplicado ao mapa, não só à Biblioteca e à Revisão.
- Como reverter: um `continue` em vez de `desenhaveis.append` em
  `fotoorganizer/server/app.py::mapa`, mais ajuste dos testes `test_mapa_*`
  em `tests/test_server_api.py`.
- Status: decidido pelo orquestrador, consistente com o padrão já adotado na
  Biblioteca e na Revisão (`ac9e7f2`, `1b125f7`) e no card de Viagens/Eventos
  (`151e381`).

---

## D-034 — Álbum nomeia onde a pasta não nomeia, e não passa por cima dela

- Fase: backlog v2+, item 3 de `docs/ROADMAP.md` ("eventos nomeados pelo que
  já existe")
- Classe: A
- Data: 2026-08-01
- Contexto: D-030 fechou o que álbum **não** pode fazer (dividir
  acontecimento). Faltava ligar o que ele pode: as 27.226 nomeações de álbum
  do catálogo (25.304 na medição de D-030, o acervo cresceu desde então)
  ainda não chegavam a `Trip.nome`/`Event.nome`. O nome de PASTA já chegava,
  via `grouping/eventos.py::extrair_evento`; o metadado de álbum, não.
- Medido, e é o achado que decidiu tudo: **nenhuma das 27.226 marcações está
  numa foto organizável.** 27.216 vivem nas 44.661 referências do Apple
  Fotos e 10 nas 54.086 do Lightroom — todas com `arquivo_ausente`. Isso tem
  duas consequências opostas:
  - As 44.661 referências do Apple Fotos têm `pasta` **vazia**: para elas o
    álbum não concorre com a pasta, ele é o único nome que existe. As do
    Lightroom são o espelho — caminho rico ("/Volumes/photo/Portfolio/Chile
    e Atacama Abr.18") e quase nenhum álbum. Os dois sinais são
    complementares, não rivais.
  - Como nenhuma delas é acervo, o álbum só alcança uma sessão por
    contemporaneidade, do mesmo jeito que a herança de GPS de D-025.
- Escolhida — a regra de desempate, em três camadas:
  1. **Sessão neutra continua sem nome.** Nomear o que a cascata não
     classificou seria detectar acontecimento por álbum, que é exatamente o
     que D-030 proíbe.
  2. **Pasta ganha quando o rótulo é um segmento de pasta** (regras 2, 3 e 6
     de `docs/AGRUPAMENTO.md`). Uma foto está em uma pasta e em vários
     álbuns ao mesmo tempo; o sinal único vence o múltiplo, e é o que já
     estava testado nos 17 cenários de `scripts/avaliar_agrupamento.py`.
  3. **Álbum entra quando o rótulo é derivado** — país geocodificado
     ("Brasil") ou intervalo de datas ("Viagem de 08-07 a 11-07"), regras 1,
     4 e 5. Esses dizem onde e quando; o destino já carrega os dois em
     outros campos.
  Entre álbuns concorrentes: prateleira por último ("Férias", "Family"),
  depois mais fotos, depois nome mais curto e ordem alfabética.
- Por quê a prateleira desce: por frequência pura, o período de 15 a 31 de
  março de 2019 se chamaria **"Férias"** (4.352 fotos) em vez de **"Portugal
  e Italia com as Meninas"** (3.729) — o aninhamento de D-030 escolhendo o
  nome que diz menos. É o único período do acervo em que a regra diverge de
  "mais frequente", e é justamente o nome que o ROADMAP usava como exemplo
  do resultado desejado. Prateleira é rebaixada e não rejeitada porque
  nenhum período do acervo tem *só* prateleira como candidata: as duas
  opções dão o mesmo resultado hoje, e rebaixar é a ação menor.
- **Ganho medido hoje: zero.** `scripts/medir_nome_de_album.py` regenerou as
  sugestões numa cópia do catálogo real: 7 grupos antes, 7 depois, **0 com
  nome diferente**. As sessões que existem hoje ou já têm nome de pasta
  (Dubai, Pantanal, TERG, Quizomba, Serena, Visconde de Mauá) ou não têm
  álbum aproveitável no período (a viagem "Brasil" de 2026-07 só tem
  "WhatsApp", que `album_nomeia` descarta). No caso do Dubai o álbum existe
  e **concorda** com a pasta ("Dubai, Thai & Viet" nos dois), o que é a
  prova de que a ordem pasta-primeiro não custa nada aqui.
- **Ganho bloqueado, e por quê:** 21 períodos do acervo têm álbum
  aproveitável, cobrindo 20.515 fotos; em **20 deles (20.482 fotos) nenhuma
  pasta nomeia coisa alguma**. Esses períodos não viram sessão porque as
  fotos que os carregam não são acervo alcançável (D-028: original só no
  iCloud). É o mesmo bloqueio que já derrubou os itens 5, 7, 8 e 9 do
  ROADMAP — a ligação está pronta e passa a valer no dia em que esses
  arquivos forem alcançados, sem código novo.
- Confiança: origem nova `album_externo`, 0.55 — **abaixo** de `pasta`
  (0.60), embora as duas sejam palavras que o dono escreveu. A foto *está*
  na pasta e apenas *coincide no tempo* com o álbum; o vínculo é da mesma
  natureza da vizinhança temporal, e a tabela de `docs/CONFIANCA.md` reflete
  isso. `Decisao.origem_do_rotulo` guarda essa origem separada de
  `Decisao.origem`, que continua dizendo de onde veio o tipo: uma viagem
  pode ser viagem pelo GPS e chamar-se pelo álbum.
- Como reverter: `_nomear_por_album` em `fotoorganizer/grouping/classifier.py`
  é o único ponto — devolver `decisao` sem tocar em nada restaura o
  comportamento anterior. `escolher_album` e `_PRATELEIRAS` vivem em
  `fotoorganizer/grouping/albuns.py`; `MIN_FOTOS_ALBUM` é o limiar.
  `scripts/medir_nome_de_album.py` refaz a medição (somente leitura sobre o
  catálogo; a regeneração roda numa cópia temporária). Nada persistido
  depende da regra — `trips`/`events` são recriados a cada `gerar()`.
- Status: decidido por medição

---

## D-035 — As 45.822 miniaturas do Apple Fotos já saíram do catálogo, e o
item 5 do ROADMAP nasce sem o dado que o sustentava

- Fase: backlog v2+, item 5 de `docs/ROADMAP.md` ("análise visual local"),
  medição pedida pelo próprio item antes de qualquer código: "a distribuição
  de datas dessas 45.822 [miniaturas]. Se elas não cobrem 2001–2018, este
  item cai para o fundo junto com o 7."
- Classe: A (é registro de um fato medido e de uma decisão já tomada e
  executada pelo dono — não uma escolha nova).
- Data: 2026-08-02 (registro); a remoção em si aconteceu em 2026-07-31,
  commit `7cdd9e7` ("MakerNotes sai da base bruta, e a poda vira comando do
  projeto"), nunca tinha ganho entrada própria aqui.
- Contexto: fui medir a premissa do item 5 antes de despachar qualquer
  agente, como o próprio ROADMAP manda. Esperava contar anos; encontrei
  **zero linhas** — nenhum registro no catálogo real tem caminho dentro de
  `.photoslibrary`, e a fonte "Apple Fotos" ativa (`source_id=6`, tipo
  `APPLE_PHOTOS`) tem `largura`/`altura` nulas nas 44.661 linhas, ou seja,
  zero pixel local acessível.
- O que aconteceu: `scripts/remover_testemunhas.py` (commit `7cdd9e7`,
  2026-07-31, autoria do dono) já removeu as 45.822 miniaturas internas do
  Apple Fotos do catálogo real. A justificativa está no próprio script e é
  sólida: D-025 trocou a janela única de herança por uma janela por campo, e
  com ela as referências do próprio Apple Fotos (`arquivo_ausente=1`, sem
  pixel mas com data/GPS do osxphotos) passaram a cobrir quase os mesmos
  lugares que as miniaturas cobriam. Medido no acervo real: remover as
  45.822 custou **10 fotos** de 4.938 com lugar — muito longe do "2.117 →
  162" que justificou rebaixá-las (nunca apagá-las) em D-024. A remoção
  cumpre o invariante 8 (não é acervo, não tem endereço próprio, e o que
  perdeu foi renegociado por medição, não descartado às cegas) e tem cópia
  de segurança automática (`_copiar` no próprio script). O que falta, e é o
  motivo desta entrada, é o registro em si: uma remoção de 45.822 linhas do
  catálogo real devia ter D-0XX próprio no dia em que rodou, não só o
  docstring do script. Fica reparado agora.
- Consequência medida para o item 5: a pergunta do ROADMAP ("essas 45.822
  cobrem 2001–2018?") não chega a se colocar — elas não existem mais para
  responder por nada. E o que sobra de pixel local no período é quase nada:
  **18 fotos** de `papel='ACERVO'` inteiro têm `data_capturada` entre 2001 e
  2018 (contra 5.191 fotos de acervo no total). Todo o resto do período —
  inclusive Portugal/Itália, a viagem internacional mais citada nas fases
  anteriores — só existe como referência sem pixel (Lightroom, volume
  desmontado, D-028; ou Apple Fotos, sem `photo.path` por ser só-iCloud).
  Um `VisionProvider` rodando hoje teria 18 fotos de 2001–2018 para olhar,
  não milhares.
- Escolhida: item 5 desce para o fim da lista, ao lado do item 7 — a própria
  condição que o ROADMAP escreveu para isso, só que a resposta é mais forte
  do que "não cobre": não há imagem nenhuma para cobrir. Ambos voltam a fazer
  sentido no dia em que "o item que a lista ainda não tem" (reencontrar os
  volumes, fim de `docs/ROADMAP.md`) entregar acervo remontado — aí sim há
  pixel de 2001–2018 de novo, via Lightroom.
- Como reverter a remoção (não recomendado sem novo motivo): restaurar
  `catalog-antes-da-limpeza-*.db` (a cópia que o próprio script fez) ou
  reconfigurar a fonte 6 como varredura de pasta direta no pacote
  `.photoslibrary` e rodar `scan --reprocessar` — mas a fonte hoje é do tipo
  `APPLE_PHOTOS` (importador osxphotos), não `PASTA`, então "reprocessar"
  sozinho não traz as miniaturas de volta; precisaria de uma fonte nova.
- Status: registrado por medição; reordenação do ROADMAP aplicada nesta
  mesma sessão

## D-036 — Reapontar fonte quase reescreveu referência de nuvem como se
fosse caminho de arquivo

- Fase: `docs/prompts/fase-12-alcance-e-tempo.md`, item A (reapontar fonte
  que mudou de lugar), implementação inicial em 2026-08-09.
- Classe: A (bug pego e corrigido antes do commit — registro do achado e
  da correção, não uma escolha em aberto).
- Contexto: `MediaFile.caminho` nem sempre é caminho de filesystem —
  `sources/importer.py` grava `"apple://<uuid>"` e `"lightroom://<uuid>"`
  para referências de catálogo externo sem arquivo local (44.661 e 54.086
  linhas no acervo real, D-028). A primeira versão de
  `fotoorganizer/sources/reapontar.py` fatiava `caminho[len(prefixo):]`
  sem checar `startswith` — contra uma fonte mista (arquivo + referência),
  reescrevia a referência para dentro do prefixo novo do volume,
  destruindo em silêncio a única testemunha de lugar/data daquela foto
  (violação direta do invariante 8 do CLAUDE.md). Achado por uma revisão
  com contexto isolado (Opus, olhos frescos sobre o diff) antes do
  primeiro commit da fatia, com repro contra o catálogo real do usuário
  em modo somente-leitura.
- Escolhida: `previa`/`aplicar` agora filtram por
  `caminho.startswith(prefixo_antigo)` antes de contar, amostrar ou
  reescrever qualquer linha; o que não bate fica bit-a-bit intocado.
  `PreviaReapontamento.total_ignoradas_sem_prefixo` deixa isso visível ao
  usuário no dry-run. Colisão de caminho (duas linhas caindo no mesmo
  valor pós-reescrita) virou exceção própria (`ColisaoDeCaminho`),
  detectada proativamente e como rede de segurança sobre `IntegrityError`.
- Consequência para o método: fatia-vertical já pedia revisão com olhos
  frescos antes do commit (`SKILL.md` passo 7) — este é o caso que
  justifica o passo por medição, não por princípio: sem ele, a fatia teria
  sido commitada corrompendo referência de nuvem na primeira vez que um
  HD do Lightroom remontasse noutro ponto.

## D-037 — "não visto no walk" quase virou sinônimo de "arquivo apagado"

- Fase: `docs/prompts/fase-12-alcance-e-tempo.md`, item B (terceiro estado
  de alcance + laço de reconciliação), implementação inicial em 2026-08-09.
- Classe: A (dois bugs pegos e corrigidos antes do commit — registro do
  achado e da correção).
- Contexto: a primeira versão de `arquivo_offline` marcava sumiço por
  diferença de conjunto — `conhecidos - vistos` no fim do walk do scan
  (`scanner/scanner.py`). Uma revisão com contexto isolado (Opus) achou
  dois jeitos dessa diferença mentir:
  1. Referência de catálogo externo (`apple://uuid`, `takeout://id`) nunca
     entra em `vistos` (não é caminho de filesystem) — se a `Source` de um
     import do Google Takeout ou Apple Fotos for reaproveitada por um scan
     de pasta comum (`_get_or_create_source` funde as duas), toda
     referência daquela fonte virava `arquivo_offline=True` em massa.
     Repro do revisor confirmou.
  2. `iter_media_files` (`scanner/discovery.py`) engole `OSError` por
     diretório com só um `log.warning` — um NAS que cai ou uma subpasta
     que perde permissão NO MEIO do walk faz o generator simplesmente
     parar de produzir itens dali pra frente, sem exceção. O scan fechava
     `CONCLUIDO` (não `cancelado`) achando que viu a árvore inteira, e
     marcava arquivo de verdade como sumido. Repro com `chmod 000` numa
     subpasta confirmou: arquivos existentes saíram marcados offline.
- Escolhida: fonte única de verdade para "isto é caminho de filesystem?"
  em `scanner/elegibilidade.py`, importada tanto pelo scan quanto pela
  reconciliação (item 1). E duas guardas independentes antes de marcar
  sumiço no scan (item 2): se algum diretório falhou durante a passada,
  não marca nada nesta passada (loga aviso, deixa a reconciliação
  orçada/paciente fechar a lacuna depois); e mesmo sem erro de diretório,
  confirma cada candidato com `Path.exists()` antes de marcar — cobre o
  caso mais sutil de `padroes_ignorados`/extensão mudando entre passadas.
  As duas guardas são complementares: `Path.exists()` sozinho NÃO detecta
  o caso do NAS/permissão (stat exige +x em toda a cadeia de diretórios,
  então também devolve `False` ali) — testado, não é suposição.
- Consequência para o método: a mesma lição de D-036 se repete numa forma
  diferente — "não vi" não é "não existe", em qualquer código que infere
  ausência por omissão em vez de confirmar por medição direta. Melhor não
  marcar nada numa passada duvidosa do que marcar tudo errado; o laço
  orçado que já existia para outro motivo (item B) acabou sendo também a
  rede de segurança certa para este caso.

---

## D-038 — Uma foto tem dois instantes, e o offset não é coluna

- Fase: `docs/prompts/fase-12-alcance-e-tempo.md`, item C (modelo de tempo
  de dois instantes), implementado em 2026-08-09.
- Classe: A
- Contexto: o item C foi escrito supondo que `MediaFile.data_capturada`
  tinha semântica ambígua — ora hora local, ora absoluta. A leitura do
  código antes de implementar mostrou que **não**: `metadata/exiftool.py`
  (`_data()`), `metadata/purepython.py`, `sources/lightroom.py` e
  `sources/apple_photos.py` já descartam qualquer fuso antes de devolver a
  data, este último com o comentário explícito "coerente com EXIF no resto
  do catálogo". A coluna sempre foi a **hora de parede**, por desenho — o
  `localDateTime` do Immich, com outro nome. Não havia ambiguidade a
  desfazer, e por isso nada em `classification/`, `grouping/`,
  `repositories/media.py` ou no webapp mudou: todos eles ordenam e agrupam
  pela hora que a pessoa viveu, que é a hora certa para isso.
- O que faltava era o outro instante, o absoluto — e o achado que decidiu a
  fatia: **o Apple Fotos já sabe o fuso de cada foto e o app jogava fora.**
  A biblioteca guarda `ZTIMEZONEOFFSET`/`ZTIMEZONENAME` por asset; o
  osxphotos entrega `photo.date` já com esse `tzinfo`
  (`photos_datetime.py`, verificado na versão 0.76.1 instalada, com
  conversão de ida e volta conferida para +02:00 e -03:00); e
  `_asset_de()` fazia `replace(tzinfo=None)` na linha seguinte. Preservar
  isso não é inferência nova (isso é a fase 11) — é parar de descartar dado
  medido, no mesmo espírito de D-030 e D-034.
- Escolhida: duas colunas, nenhuma de offset.
  `data_capturada` (hora de parede, inalterada em significado e em uso) e
  `data_capturada_utc` (o mesmo instante, absoluto). O offset é a
  **diferença** entre as duas — guardá-lo numa terceira coluna criaria um
  terceiro lugar para a mesma verdade, livre para discordar dos outros dois
  em silêncio. É a parte do desenho do Immich que vale copiar
  (`docs/referencia-immich/03-modelo-de-dados.md` §3).
- **Igualdade quer dizer "fuso desconhecido", nunca "tirada em UTC".** Vale
  para o backfill da migração `0014` e para toda linha nova: quem grava
  iguala as duas quando não há fuso, e nunca deixa a absoluta nula com a
  local preenchida — isso diria "não sei quando", que é outra coisa e bem
  pior. Quem for derivar offset precisa ler zero como desconhecido.
- **O par é escolhido junto, da mesma origem.** Em `sources/importer.py`,
  casar a hora de parede do arquivo com o instante absoluto do catálogo
  externo inventaria um offset que ninguém mediu — e, sem coluna de offset,
  a mentira seria invisível. A única exceção é quando os dois **concordam
  na hora de parede** (o Apple Fotos importou a data do próprio EXIF): aí é
  a mesma captura descrita duas vezes, e o que se empresta é o **offset**,
  aplicado à hora do arquivo (`_com_o_fuso_do_catalogo`).
- **Concordância medida com tolerância de um segundo, não por igualdade**, e
  isto foi achado por revisão antes do commit: a primeira versão exigia
  igualdade exata de `datetime`, e as duas origens têm precisão diferente
  por construção — 29.023 das 44.661 linhas do Apple Fotos (65%) têm
  microssegundo, e nenhuma das 120.448 de EXIF tem, porque
  `exiftool.py:_data()` faz `split(".")[0]`. A regra teria descartado o fuso
  medido em quase toda foto com arquivo local, em silêncio. Emprestar o
  offset em vez do instante absoluto vem do mesmo achado: copiar o absoluto
  do catálogo ao lado da hora truncada do arquivo deixaria a diferença entre
  as colunas em 1h59min59,184s no lugar de duas horas.
- Limitação aceita: fuso real de +00:00 (Londres/Lisboa no inverno,
  Islândia, Marrocos) fica indistinguível de desconhecido, porque nos dois
  casos as colunas ficam iguais. É inerente ao padrão — o `keepLocalTime` do
  Immich tem a mesma — e a saída não é uma terceira coluna: quando a fase 11
  existir, o sinal de "fuso conhecido" passa a ser `tz_estimado IS NOT NULL`,
  nunca a diferença entre as duas datas. Registrado também no comentário da
  coluna e na nota de `docs/prompts/fase-11-timezone-estimado.md`.
- A migração `0014` **não é atômica** e é escrita sabendo disso: sob pysqlite
  o `ADD COLUMN` comita sozinho, então uma interrupção antes do backfill
  deixaria a coluna criada com `alembic_version` em 0013, e a tentativa
  seguinte morreria em "duplicate column name" — o app deixaria de abrir. O
  que se garante é o suficiente: o `upgrade()` é **seguro para retomar** (só
  adiciona a coluna se ela faltar, e o backfill só preenche o que está nulo,
  para não passar por cima de um fuso real escrito por uma reimportação no
  meio-tempo).
- Sem índice em `data_capturada_utc`: ordenação, recorte por mês/ano e
  agrupamento continuam na coluna local, que já tem o seu
  (`ix_media_files_data_capturada`). Índice sem consumidor é custo de
  escrita em 101 mil linhas em troca de nada. Quando aparecer uma consulta
  que ordene pelo absoluto, ele entra com ela.
- Ficou de fora, com motivo:
  - **Fuso do EXIF/QuickTime** (`OffsetTimeOriginal`, o `Z` que
    `exiftool.py:_data()` já detecta e descarta). Exige `_data()` devolver o
    PAR em vez de só a hora local, o que mexe em todos os campos de data dos
    dois extratores de uma vez. Cabe junto da fase 11, que já vai mexer em
    fuso. `MediaMetadata.data_capturada_utc` já existe esperando, em `None`.
  - **Lightroom**, medido e descartado: dos 54.086 `captureTime` do `.lrcat`
    do dono, **10** trazem fuso colado (0,02%), e `AgHarvestedExifMetadata`
    não tem coluna de offset nenhuma. Não há o que preservar ali.
  - **Google Takeout**, e este é o caso interessante: o `photoTakenTime` do
    sidecar *é* um epoch, ou seja, o instante absoluto exato. Mesmo assim
    fica de fora, porque `google_takeout.py:_data()` produz a hora local com
    `datetime.fromtimestamp(...)` **no fuso da máquina que importou** — não
    no da foto. Preencher o absoluto verdadeiro ao lado dessa local faria a
    diferença entre as duas afirmar o fuso do Mac do dono como se fosse o da
    foto: uma foto de Roma passaria a alegar −03:00. Igualadas, elas dizem
    "não sei o fuso", que é a verdade. O conserto certo é na coluna local, e
    é território da fase 11.
- **O offset do Apple Fotos é o fuso da FOTO, não o do Mac — medido, não
  suposto.** A revisão levantou a hipótese séria de que
  `ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET` fosse o fuso do dispositivo
  que importou, o que faria a fatia gravar medição do Mac do dono como se
  fosse da captura. Investiguei o `Photos.sqlite` real (somente leitura,
  `immutable=1`, 51.845 assets) e o padrão é o **oposto** do temido:
  - Das 7.838 linhas em que o offset efetivo diverge do offset do próprio
    arquivo (`ZEXTENDEDATTRIBUTES.ZTIMEZONEOFFSET`), **7.799 saem do fuso de
    casa** (−03, Rio) enquanto o arquivo insistia nele — é o Apple
    corrigindo relógio de câmera que viajou sem ser acertado, e bate com as
    viagens conhecidas do acervo (D-029). Na direção temida — efetivo virar
    −03 contra um EXIF que dizia outra coisa — há **11 linhas**.
  - Offset praticamente nunca é inventado do nada: das 42.438 linhas com
    offset efetivo, só **4** não têm offset nenhum no próprio arquivo.
  - Quando o Apple não sabe, ele deixa `ZTIMEZONEOFFSET` NULL (9.407
    linhas). O osxphotos então devolve +00:00, os dois instantes saem
    iguais, e a linha diz honestamente "fuso desconhecido" — verificado
    rodando `photos_datetime()` com `tzoffset=None`.
  - `ZINFERREDTIMEZONEOFFSET` **não serve** como discriminador "isto foi
    inferido": está preenchido em 31.656 das 34.596 linhas cujo offset bate
    com o do arquivo (91%, justamente as medidas) e em só 33% das
    divergentes. O Apple guarda a própria inferência ao lado, use-a ou não.
- Por isso **não** restringi o empréstimo de offset a fotos com GPS, que era
  a saída conservadora sugerida: ela descartaria 23.961 linhas (56% de todas
  as que têm offset) das quais apenas 4 não têm respaldo no arquivo, para se
  defender de uma falha medida em 11. E seria incoerente com o que o
  importador já faz ao lado: `asset.gps_lat` do catálogo externo entra em
  `gps_lat`, a coluna medida, não em `gps_lat_estimado` — dado que outro
  catálogo afirma vai para a coluna de fato, com a origem registrada em
  `metadata_entries`. O fuso segue a mesma regra, e ganhou a mesma
  proveniência (chave `data_utc` no namespace da fonte). reimportar o Apple Fotos recupera o fuso das linhas que
  entraram como **referência** (reescritas a cada import — as 44.661 do
  acervo real, que roda em "Otimizar armazenamento"). Asset com arquivo
  local é pulado por assinatura tamanho+mtime inalterada, e só volta a ganhar
  o fuso quando o arquivo mudar. Reprocessar campos que não dependem de ler
  o arquivo seria mudança no importador, e não vale sem um caso concreto.
- Como reverter: a migração `0014` tem `downgrade()`; os pontos de escrita
  são três (`scanner/scanner.py:_gravar`, `sources/importer.py:_gravar` e
  `:_gravar_referencia`) e nenhum leitor depende da coluna ainda — é aditivo
  de ponta a ponta.
- Status: decidido

## D-039 — Referência PhotoPrism + síntese de backlog cruzando as duas leituras
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: dono pediu para levantar o que PhotoPrism e Immich têm de mais
  avançado/diferenciador vs. mercado, para trazer ao foto-organizer — não
  para portar ao PhotoPrism. Já existe leitura completa do Immich
  (`docs/referencia-immich/`, 2026-08-08) e uma auditoria de 453
  capabilities do PhotoPrism feita numa sessão paralela em
  `~/dev/photoprism-develop/.local/audit/photoprism/` (8 domínios, âncoras
  `arquivo:linha` verificadas, mesma licença AGPLv3).
- Opções: (a) reler o PhotoPrism do zero, espelhando os cinco agentes de
  reconhecimento usados no Immich; (b) sintetizar a partir da auditoria já
  feita (já ancorada), dividida pelos três agentes de domínio existentes
  (agente-arquivos/agente-imagem/agente-ux) em vez de leitores genéricos
  novos; (c) pular o mapa de mecanismo e ir direto a um backlog sem
  referência.
- Escolhida: (b)
- Por quê: a auditoria paralela já tem 453 capabilities com âncora
  verificada — reler do zero duplicaria custo sem ganho de precisão. Os
  agentes de domínio do próprio projeto já carregam o contexto de fit ("isso
  já existe aqui? vale para este acervo?") que um leitor genérico não tem —
  soldar leitura e julgamento de fit num único agente evita uma segunda
  rodada de revisão. (c) foi descartada porque o valor do
  `referencia-immich` ("reler custa uma tarde; redescobrir custa meses",
  conforme seu próprio README) se perde sem o mapa equivalente do
  PhotoPrism.
- Como reverter: `docs/referencia-photoprism/` e o novo
  `docs/prompts/fase-14-*.md` são aditivos, docs-only — apagar os arquivos
  não afeta nada.
- Status: decidido

## D-040 — O diferencial não é a linguagem de busca, é o que ela consegue perguntar
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: a DSL de campo único do PhotoPrism (`internal/form/serialize.go:16-191`,
  `search_photos.go:11-99`) é o mecanismo de UX mais sofisticado dos dois mapas
  lidos, e a tentação é propô-la como item por si. Mas "filtro salvável" é table
  stakes: o Lightroom tem coleções inteligentes há mais de uma década, e a busca
  do Google Fotos é melhor que qualquer DSL que este projeto vá escrever. Se o
  item fosse "trazer a DSL", ele morreria no filtro 1 da própria fase.
- Opções: (a) propor a DSL como item de UX, pelo mérito do mecanismo;
  (b) descartar por table stakes; (c) propor o mecanismo, mas justificado pelo
  vocabulário que só este projeto pode oferecer — `confianca:`, `origem:`,
  `versao:`, `papel:`, `lugar:estimado`, `alcance:` — que sai de `evidence`
  (`models/inference.py:39-58`) e de colunas que nenhum app de mercado tem
  porque nenhum registra proveniência por campo.
- Escolhida: (c)
- Por quê: o filtro 1 pergunta se o mercado já faz aquilo. O mercado faz busca
  e faz filtro salvo; o que o mercado não faz — nem pode, com o modelo de dados
  que tem — é responder "me mostre o que foi inferido por vizinhança temporal,
  com confiança baixa, pela lógica 3.9". O mecanismo do PhotoPrism é o veículo;
  o diferencial é a carga. Escrito assim, o item também deixa de ser um pedido
  de UI nova e vira o que de fato é: tornar alcançável um ativo que o M3 já
  pagou e que hoje o usuário não consegue consultar.
- Consequência de desenho: sem o round-trip simétrico (`Serialize`, `:16-77`) o
  item perde a única mitigação decente para "mais uma sintaxe para aprender" —
  clicar nos controles existentes escreve a sintaxe na caixa. Um port que
  implemente só o parser entrega uma caixa de texto que ninguém preenche.
- Como reverter: o item é proposta em `docs/prompts/fase-14-*.md`; nada foi
  implementado.
- Status: decidido

## D-041 — Estado do pipeline no catálogo sai da lista de "vale importar"
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: o README de `docs/referencia-immich/` lista três coisas como "vale
  importar", e uma delas é "o estado do pipeline gravado no catálogo em vez de
  na fila" (`asset_job_status`, `schema/tables/asset-job-status.table.ts:5`, com
  `asset-job.repository.ts:356-369` derivando "o que falta processar" por
  consulta). As outras duas viraram os itens B e C da fase 12 e já foram
  implementadas (D-037, D-038); esta ficou pendente e reapareceu como candidata
  nesta rodada.
- Opções: (a) promover a item da fase 14, honrando a marcação do README;
  (b) descartar por filtro 1, registrando que a marcação anterior usava outra
  régua; (c) deixar sem julgamento, para reaparecer numa terceira rodada.
- Escolhida: (b)
- Por quê: o filtro desta fase é "diferencia vs. produtos de mercado". Estado de
  pipeline é arquitetura interna que o usuário nunca vê — e o que ninguém vê não
  diferencia produto nenhum. A marcação do README do Immich foi feita sob a
  régua da fase 12 ("o que mudaria substancialmente o projeto"), que é outra
  pergunta e admitia resposta de engenharia. Continua sendo boa engenharia: se
  algum dia a fila de background crescer, derivar o pendente por consulta é
  melhor que manter estado de fila. Só não é item de backlog de valor.
- Como reverter: nada foi removido; o julgamento está em
  `docs/prompts/fase-14-*.md` §7.1 e pode ser revisto se a fila crescer.
- Status: decidido

## D-042 — Empilhamento de capturas irmãs: os dois mapas discordavam, e o
desempate não é o argumento de nenhum dos dois
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: `docs/referencia-photoprism/01-ingestao-e-arquivos.md` §11 marca o
  empilhamento (`index_mediafile.go:150-200`, `mediafile_related.go:16`) como
  "vale considerar, M", porque `duplicates/` agrupa hash idêntico e phash mas
  não RAW+JPEG do mesmo clique — bytes diferentes, phash diferente, são
  codificações distintas da mesma cena. `03-ux-e-organizacao.md` §4.3 marca como
  "não vale", alegando que `papel` ACERVO/SINAL já resolve. Os dois mapas do
  mesmo levantamento se contradizem e alguém ia ter que decidir.
- Opções: (a) seguir o mapa 01 e propor como item M; (b) seguir o mapa 03 e
  descartar como já resolvido; (c) rejeitar os dois argumentos e descartar por
  outro motivo, condicionando o retorno a uma medição.
- Escolhida: (c)
- Por quê: o mapa 03 está errado no mérito — `papel` responde "isto é acervo ou
  testemunha", não "estes dois arquivos são o mesmo disparo"; a lacuna que o
  mapa 01 aponta é real. Mas o item morre no filtro 1 desta fase: Lightroom,
  Apple Fotos e Mylio empilham RAW+JPEG, é table stakes do segmento. E o mapa 01
  dimensiona em "M" um problema de tamanho desconhecido: por padrão o Lightroom
  não trata o JPEG ao lado do RAW como foto separada, então o `.lrcat` importado
  (54.086 `captureTime`, D-038) pode já ter escondido metade das capturas irmãs.
  Sem número, "M" é chute.
- Medição que destrava: contar, por fonte, linhas com a mesma `data_capturada` e
  a mesma câmera cuja extensão difere. Não precisa de pixel nem de volume
  montado — roda sobre o catálogo atual, somente leitura.
- Como reverter: volta como candidato de roadmap assim que a medição existir.
- Status: decidido

## D-043 — `versao_logica` é escrito e nunca lido, e o conserto é um token, não
uma fatia
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: `Evidence.versao_logica` e `Suggestion.versao_logica`
  (`models/inference.py:57,75`) são preenchidos com `VERSAO_LOGICA = "4.1"`
  (`classification/engine.py:75,970,1045`) e não aparecem em nenhuma consulta,
  filtro ou operação — grep confirma zero leitores. A auditoria mais cara do
  projeto (qual raciocínio decidiu cada campo) está gravada e é inalcançável.
- Opções: (a) propor "recomputar em massa por origem e versão de lógica,
  preservando o manual" como item próprio, espelhando `asset_face.sourceType` do
  Immich (`asset-face.table.ts:75`, com `metadata.service.ts:968` apagando e
  recriando só as faces de origem `exif`); (b) tratar como token do filtro
  composto (Item A da fase 14); (c) remover a coluna, já que ninguém lê.
- Escolhida: (b)
- Por quê: (a) resolve um problema que este projeto não tem. A preservação do
  manual aqui já é melhor que a do Immich: a decisão do usuário mora em coluna
  própria (`tipo_confirmado`, `gps_lat` vs `gps_lat_estimado`) e a evidência é
  cache derivado, apagado e refeito inteiro a cada passada
  (`classification/engine.py:961`) — recomputar já preserva o manual por
  construção, sem precisar de `sourceType` nem de `lockedProperties`. O que
  falta não é a operação de recomputar, é **enxergar** o que cada versão
  decidiu, e isso é um predicado de filtro. (c) está errado: a coluna custa
  nada e é a única testemunha de qual lógica produziu 101 mil inferências.
- O que muda de resposta: se o motor de sugestões ficar caro o bastante para que
  reprocessar 101 mil registros incomode, a operação escopada de (a) volta a
  fazer sentido — e o token `versao:` já terá provado que o dado é confiável.
- Como reverter: nada implementado; o token é parte da proposta do Item A.
- Status: decidido

## D-044 — A ordem dos itens da fase 14 não é a ordem de valor/custo bruta
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: o Item B da fase 14 (proteger a camada de julgamento: export legível
  + dump agendado com retenção + checagem de esquema no boot) custa **S**; o
  Item A (filtro composto sobre proveniência) custa **M**. Pela régua do
  `ROADMAP.md` — valor por unidade de custo — o mais barato deveria vir antes, e
  o Item B protege literalmente todo o resto: D-024 a D-039 são meses de
  calibração sobre 101.516 registros, e é a única camada que uma nova varredura
  não reconstrói. Hoje não há mecanismo nenhum: `sqlite3 .backup` aparece em
  quatro scripts ad-hoc (`scripts/preparar_versao.sh:121-125`,
  `rebaixar_nao_acervo.py:88-90`, `podar_metadados.py:55`,
  `medir_nome_de_album.py:105-110`), e D-038 já registra que a migração `0014`
  não é atômica e uma interrupção deixaria o app sem abrir.
- Opções: (a) B → A → C, por custo; (b) A → B → C, por valor entregue no caso
  esperado; (c) não ordenar e deixar a decisão para quem for implementar.
- Escolhida: (b)
- Por quê: o valor do Item B é **zero no caso esperado** — é seguro, e seguro só
  entrega na cauda. O Item A entrega todo dia em que o app abrir, e é o único
  dos três que converte em capacidade visível um diferencial pelo qual o projeto
  já pagou (a tabela `evidence`, construída no M3). A régua diz "valor
  entregue", não "risco evitado".
- Ressalva que faz parte da decisão, não a contradiz: quem pesar risco de cauda
  acima de valor contínuo deve inverter os dois. Como o B custa S e não toca em
  nada que o A toca (o A é leitura; o B escreve só em arquivo próprio do app),
  os dois correm em paralelo sem conflito — a ordem é recomendação, não
  dependência.
- Como reverter: trocar a ordem em `docs/prompts/fase-14-*.md` §3-4; não há
  dependência técnica entre os dois.
- Status: decidido

## D-045 — Lib preparatória dos 4 itens da fase 14 (+ item 5 do roadmap), em staging fora da fronteira
- Fase: 14 (Itens A, B, C) + roadmap "Próximas versões" item 5 (Item D)
- Classe: A
- Data: 2026-08-12
- Contexto: o dono ainda não aprovou o plano da fase 5, então
  `fotoorganizer/**`, `webapp/src/**`, migrações Alembic e `pyproject.toml`
  continuam fora de alcance (`docs/prompts/00-protocolo.md:80-88`). Os
  quatro itens já estavam decididos e mapeados (fase 14 + roadmap item 5) e
  o pedido foi preparar a reimplementação inteira — lib, testes, README —
  em `docs/lib-preparatoria/`, pronta para plugar quando o gate abrir, sem
  tocar em código de produção agora.
- Opções: (a) esperar o gate abrir para escrever qualquer código; (b)
  escrever a lib completa em staging dentro de `docs/**`, com testes e
  documentação do ponto de integração; (c) escrever só o desenho (prosa),
  sem código executável.
- Escolhida: (b)
- Por quê: `docs/**` está dentro da fronteira liberada, e o valor de ter
  código testado e pronto para colar é maior que o de prosa — quando o gate
  abrir, a integração vira "colar + ajustar import", não "implementar do
  zero". Os quatro itens nasceram só da descrição de mecanismo em
  `docs/referencia-photoprism/`, `docs/referencia-immich/` e do schema real
  lido em `fotoorganizer/**`/`webapp/src/**` (leitura permitida) — nunca de
  abrir os dois repositórios de referência (ambos AGPLv3).
- O que foi preparado, um diretório por item, cada um com `lib.py` +
  `test_lib.py` + `README.md`:
  - `docs/lib-preparatoria/filtro-proveniencia/` (Item A) — parser +
    serializador simétrico para um filtro composto sobre `evidence`
    (`confianca`, `origem`, `papel`, `lugar:estimado`), sem OU/negação
    nesta versão (mitigação já recomendada na seção 6 do prompt de
    origem). 34 testes.
  - `docs/lib-preparatoria/protecao-julgamento/` (Item B) — export legível
    em JSON (decisão de formato registrada no README do item, não aqui:
    JSON em vez de YAML, zero dependência nova), backup com retenção sobre
    o mesmo padrão `sqlite3 .backup` já usado em quatro scripts, e
    checagem de esquema no boot que cobre nomeadamente o cenário que
    D-038 descreve (migração `0014` não atômica). 24 testes.
  - `docs/lib-preparatoria/deteccao-sidecar-xmp/` (Item C) — resolução
    reversa `.xmp` → mídia principal (sem adivinhar em caso de
    ambiguidade) + classificação em 5 casos para detectar "só o sidecar
    mudou", o gatilho que falta no scanner incremental hoje. 22 testes.
  - `docs/lib-preparatoria/timezone-por-pais/` (Item D, roadmap item 5) —
    `TZ_POR_PAIS` cobrindo os 250 países reais de
    `geolocation/paises.py::PAISES_PT` (o prompt de fase-11 citava "98",
    número desatualizado — medido nesta sessão), todos validados contra
    `zoneinfo.available_timezones()`, mais a função de cálculo que já
    distingue "ganhou tz por GPS próprio" de "ganhou por herança D-025"
    para a medição que o aceite da fase pede. 17 testes.
  - Total: 97 testes, `pytest docs/lib-preparatoria/*/test_lib.py` verde.
- Verificação de contaminação: `grep -rl "photoprism-develop\|~/dev/fot"
  docs/lib-preparatoria/` voltou vazio na versão final. Na primeira
  rodada NÃO voltou vazio — os três README que citavam a restrição de
  licença ("nenhuma linha vem de `~/dev/photoprism-develop` ou
  `~/dev/fot`") continham, eles mesmos, os literais proibidos dentro da
  própria frase de conformidade. Investigado: falso positivo (nenhuma
  linha de código citava os repositórios, só a frase de negação os
  nomeava) — corrigido reformulando as três frases para não conter os
  literais, sem perder o sentido da declaração.
- Nenhuma linha desta sessão veio de abrir arquivo dentro dos dois
  repositórios de referência (ambos AGPLv3) — confirmado pelo grep acima e
  por não haver, no histórico de ferramentas desta sessão, nenhuma leitura
  de caminho fora de `docs/`, `fotoorganizer/`, `webapp/src/` e `scripts/`.
- Como reverter: apagar `docs/lib-preparatoria/`; nada fora dela foi
  tocado.
- Status: decidido

## D-046 — Medição do empilhamento de capturas irmãs: D-042 resolvida, 11,72% do acervo
- Fase: 14
- Classe: A
- Data: 2026-08-12
- Contexto: D-042 descartou "empilhamento de capturas irmãs" (RAW+JPEG do
  mesmo clique) no filtro 1 da fase 14 — é table stakes, Lightroom/Apple
  Fotos/Mylio já empilham — mas deixou uma medição pendente antes de poder
  dimensionar esforço para um retorno futuro como candidato de roadmap:
  "o mapa 01 dimensiona em 'M' um problema de tamanho desconhecido [...]
  sem número, 'M' é chute". A medição prescrita ali ("contar, por fonte,
  linhas com a mesma `data_capturada` e a mesma câmera cuja extensão
  difere") não precisa de pixel nem de volume montado — roda só leitura
  sobre o catálogo atual.
- Medição: `scripts/medir_capturas_irmas.py` (novo, somente leitura, aberto
  com `mode=ro`/`immutable=1`), rodado sobre o catálogo real
  (`~/Library/Application Support/FotoOrganizer/catalog.db`, 940 MB).
  Critério: `papel='ACERVO'` agrupado por `(source_id, data_capturada,
  make, model)` com mais de uma `extensao` distinta no grupo.
- Resultado: **3.846 grupos, 11.331 fotos envolvidas — 11,72% dos 96.692
  registros de `papel='ACERVO'`.** Concentrado quase todo em
  `/Volumes/photo` (3.843 dos 3.846 grupos — o volume Lightroom/RAW
  citado em D-028, hoje desmontado). Par de extensão dominante: `cr2+jpg`
  (3.361 grupos, 87% do total), seguido de `cr2+dng` (397, 10%); o resto
  (`cr2+tif(f)`, `dng+*`, `cr3+jpg`) soma menos de 3%.
- Interpretação: o número é real e não é ruído de rajada de 1 segundo —
  11,72% do acervo organizável é ordem de grandeza relevante, e o padrão
  MUITO concentrado num par só (`cr2+jpg`, 87%) muda o "M" de D-042 de
  chute para estimativa com base: um resolvedor que trate esse par
  específico (mesma fonte + mesmo instante + mesma câmera + `cr2`
  irmanado com `jpg`) cobriria a esmagadora maioria dos casos sem precisar
  tratar a cauda longa de combinações raras.
- O item **continua fora do escopo da fase 14** — a medição não reabre o
  item agora, só destrava o dimensionamento para quando ele voltar como
  candidato de roadmap (a razão do descarte, table stakes de mercado,
  segue valendo; D-042 já separou "descartar por table stakes" de "custo
  desconhecido", e só o segundo motivo esta medição resolve).
- Como reverter: nada a reverter — medição aditiva, somente leitura, nenhum
  arquivo do acervo nem linha do catálogo foi alterada. Quando o item
  voltar como candidato, citar este número em vez de remedir do zero
  (remedir só se o acervo mudar de forma material — novo import, ligação
  do volume `/Volumes/photo`).
- Status: decidido

## D-047 — "resíduo" do advisor é 39% das sessões e 43% do acervo, não zero — PLANO_IA_E_PRODUTO.md §2/§3 revisado
- Fase: 5 (revisão do plano, achado 4 apontado na revisão pedida pelo dono)
- Classe: B
- Data: 2026-08-13
- Contexto: `docs/PLANO_IA_E_PRODUTO.md:56-58` afirma que sessões "neutra"
  (as que chamariam o advisor) são residuais, com base em "zero de 63" no
  catálogo de demonstração SINTÉTICO — nunca medido no acervo real. Pedido
  do dono, em revisão conjunta do plano: medir de verdade antes de aprovar
  a decisão 1 do gate (descer o advisor de Opus 5 para Haiku 4.5).
- Medição: `scripts/medir_uso_do_advisor.py` (novo), rodando o
  `SuggestionEngine.gerar()` REAL sobre uma cópia do catálogo (mesmo padrão
  `sqlite3.Connection.backup()` de `scripts/medir_nome_de_album.py`), com
  um `CountingNullAdvisor` no lugar do advisor de verdade —
  implementa o mesmo `Protocol` que `NullAdvisor` já implementa
  (`fotoorganizer/classification/advisor.py:55-63`), `classificar()` nunca
  faz I/O de rede, só conta a chamada e devolve `None`. **Nenhum dado saiu
  da máquina** — instalar dependência de API/credencial e chamar o advisor
  de verdade é Classe C (sempre espera), a medição não fez isso.
- Resultado sobre o catálogo real (96.692 registros de `papel='ACERVO'`,
  passada completa, ~1h39min de CPU): **266 sessões — 36 viagem, 126
  evento, 104 neutra. 104/266 = 39,10% das sessões, cobrindo 41.901 fotos
  (≈43% do acervo organizável).** Fotos por sessão neutra: mín. 2, média
  402,9, máx. 8.581.
- Correção ao plano: "residual" está errado como descrição do papel do
  advisor no acervo real — é quase 4 em cada 10 sessões. O que o plano
  acerta e continua valendo: o custo em dólar não muda com esse número,
  porque `_consultar_advisor` (`engine.py:560-569`) manda só 8 nomes de
  arquivo de exemplo por sessão (`membros[:8]`), não a lista inteira — uma
  sessão de 8.581 fotos custa a mesma ordem de tokens que uma de 2. O que
  muda é a PROPORÇÃO da decisão do produto que depende do julgamento do
  advisor: se ele errar sistematicamente, não é canto de mapa, é quase
  metade das fotos mal categorizadas.
- Impacto direto na decisão 1 do gate (Opus 5 → Haiku 4.5): a pergunta que
  importa nunca foi custo (a aritmética do plano já mostrava $0,02–$0,16
  para o catálogo inteiro) — é qualidade nos clusters ambíguos. Com 43% do
  acervo passando por esse caminho, uma queda de qualidade ao descer de
  modelo deixou de ser um detalhe de canto e virou o fator que mais pesa na
  decisão. Recomendação revisada: medir Haiku 4.5 × Opus 5 numa amostra dos
  104 clusters neutra reais (localmente reproduzível — `ClusterInfo` de
  cada um já foi capturado por este script) ANTES de aprovar a decisão 1,
  não depois.
- Opções levadas ao dono: (a) aprovar a decisão 1 como está, aceitando o
  risco sem medir qualidade; (b) medir Haiku × Opus nos 104 clusters reais
  antes de aprovar; (c) aprovar Opus 5 (manter o modelo atual) e adiar a
  decisão de custo.
- Recomendada: (b) — é barata (mesma ordem de custo da tabela do plano) e
  transforma uma aposta em decisão informada, exatamente o padrão que este
  projeto já aplica a inferência determinística (evidência antes de
  decisão).
- Como reverter: nada a reverter — medição aditiva, somente leitura, sem
  chamada de API. `docs/PLANO_IA_E_PRODUTO.md` não foi editado (é entregável
  de fase já fechada; a correção fica registrada aqui, não reescrita lá).
- Status: aguardando (classe B — decisão 1 do gate da fase 5 depende desta
  correção antes de o dono decidir)

## D-048 — Comparação Opus 5 × Haiku 4.5 em 5 clusters reais: Haiku inventa onde Opus recusa
- Fase: 5 (revisão do plano, decisão 1 do gate — segue D-047)
- Classe: B
- Data: 2026-08-13
- Contexto: D-047 mudou o peso da decisão 1 (Opus 5 → Haiku 4.5 no advisor)
  ao medir que sessões "neutra" são 39% do total, não resíduo. O dono pediu
  a comparação real antes de decidir, com escopo explícito de 5 clusters
  (amostra, não os 104) — Classe C (envio de metadado para API externa,
  `docs/prompts/00-protocolo.md`), então a chamada real foi feita pelo
  próprio dono no terminal dele, com `ANTHROPIC_API_KEY` própria; nenhuma
  credencial foi manuseada por esta sessão. `scripts/medir_qualidade_advisor.py`
  (novo) reconstrói os 5 clusters por SQL a partir dos mesmos períodos que
  `medir_uso_do_advisor.py` já tinha identificado como sessão "neutra", e
  reusa `ClassificationAdvisor`/`ClaudeAdvisor` (`advisor.py:101-144`) sem
  lógica de chamada nova — só instancia com `model=` diferente para cada
  comparação.
- Resultado: **3 de 5 clusters concordam (`null`/`null` nos dois modelos)**.
  Nas 2 divergências, o padrão é o mesmo nas duas: Haiku 4.5 devolve
  categoria/evento onde Opus 5 recusa por falta de evidência.
  - Cluster "Carnaval da Escola 2001" + "na Praia - Fev 2001" (2 pastas no
    mesmo cluster, histórias diferentes): Opus recusa citando o conflito
    entre as duas pastas; Haiku responde `Eventos/"Carnaval da Escola 2001"`
    lendo só uma das duas pastas, ignorando a outra no mesmo payload.
  - Cluster de virada de ano (31/12–04/01, pastas genéricas, ZERO lugar
    geocodificado): Opus recusa, notando explicitamente "apesar do período
    coincidir com a virada do ano"; Haiku responde
    `Viagens/"Viagem de Ano Novo 2006-2007"` — infere viagem só da
    proximidade de datas, sem nenhum sinal de deslocamento (nem palavra
    "viagem" na pasta, nem GPS, nem lugar geocodificado).
- Interpretação: amostra pequena (n=5, 2 divergências) não crava número, mas
  a direção é consistente e o modo de falha é o previsto antes de medir
  (revisão do dono com a sessão, achado 3): Haiku, nos dois casos em que
  discordou, violou a instrução explícita do próprio `_SYSTEM` prompt do
  advisor — "Se os metadados não bastarem, devolva categoria e evento
  nulos — nunca invente" (`advisor.py:97`) — e Opus a obedeceu nos dois. O
  argumento de custo do plano original segue válido (diferença de centavos);
  o que muda é que "rotular três categorias não precisa de modelo caro"
  (a premissa da decisão 1) tem contraexemplo direto na prática, não só em
  tese.
- Recomendação revisada para a decisão 1: **não descer para Haiku 4.5 sem
  mais evidência** — ou rodar a comparação nos 104 clusters completos para
  virar direção em número, ou (se o custo/latência do Opus 5 for aceitável,
  que a aritmética do plano já mostra que é) manter Opus 5 e fechar a
  decisão 1 como "não, por ora", revisitável se um prompt/schema mais
  restrito para Haiku eliminar esse modo de falha específico.
- Nota de segurança, fora do escopo da decisão de produto: o dono colou a
  API key em texto puro no chat ao compartilhar a saída do comando rodado
  no terminal dele. Nenhuma chamada foi feita por esta sessão com essa
  chave — o comando rodou no terminal do próprio dono — mas o valor ficou
  exposto no histórico da conversa. Recomendado ao dono rotacionar a chave
  no console da Anthropic, independente da decisão 1.
- Como reverter: nada a reverter — nenhuma mudança de código de produto,
  só a medição e o registro.
- Status: aguardando (decisão final da fase 5 é do dono)

## D-049 — Comparação Opus 5 × Haiku 4.5 nos 104 clusters reais: bug no relatório, sinal de D-048 confirmado e reforçado
- Fase: 5 (revisão do plano, decisão 1 do gate — segue D-047 e D-048)
- Classe: A
- Data: 2026-08-13
- Contexto: o dono rodou `scripts/medir_qualidade_advisor.py` nos 104
  clusters reais (não mais os 5 de D-048), no terminal dele, com a própria
  `ANTHROPIC_API_KEY` — 208 chamadas (2 modelos × 104 clusters). Nenhuma
  credencial foi manuseada por esta sessão.
- **Bug encontrado no relatório desta sessão, não no dado**: `Comparacao.padrao`
  comparava `resultado is None` (o objeto `AdvisorResult` inteiro) para
  decidir "o modelo recusou". Mas `ClassificationAdvisor.classificar()`
  quase sempre devolve um `AdvisorResult` de verdade mesmo quando recusa —
  a recusa é `categoria=None` DENTRO do objeto (`advisor.py:97`), não o
  objeto virando `None` (isso só acontece em erro de API/parse). Como o
  objeto nunca é `None` na prática, as três categorias que dependiam dessa
  comparação (`concordam_null`, `haiku_afirma_opus_recusa`,
  `opus_afirma_haiku_recusa`) saíram zeradas por construção, e os 31 casos
  de discordância real caíram todos, sem distinção, em
  `discordam_entre_si`. Corrigido em `scripts/medir_qualidade_advisor.py`
  (`Comparacao.padrao` agora testa `.categoria is None`, com teste manual
  cobrindo os 5 padrões antes de reafirmar o registro).
- **O dado bruto (contagem de categoria por modelo) não tinha o bug** — vem
  direto de `.categoria`, não da comparação quebrada — e por isso dá para
  reconstruir o essencial sem rodar os 104 de novo:

  | | recusou (categoria=None) | comprometeu-se |
  |---|---:|---:|
  | Opus 5 | 82/104 (78,8%) | 22/104 (21,2%) |
  | Haiku 4.5 | 63/104 (60,6%) | 41/104 (39,4%) |

  Concordância exata (mesma categoria E mesmo evento): 73/104. Discordância:
  31/104. Com as duas marginais (82/22 para Opus, 63/41 para Haiku) e o
  total de discordância (31) fixos, a tabela de contingência 2×2 tem um só
  grau de liberdade — mas isso já basta para provar um PISO: pelo menos
  **19 dos 31 clusters discordantes (61% das discordâncias, 18,3% do total
  de 104) são obrigatoriamente "Haiku afirma categoria, Opus recusa"** — a
  matemática da tabela não permite um número menor, só igual ou maior. O
  número exato entre 19 e 31 exigiria rerodar com o bug corrigido; não foi
  rerodado (custo/tempo desnecessário — o piso já é decisivo).
- Interpretação: o achado de D-048 (n=5, Haiku inventa onde Opus recusa)
  **se confirma e se fortalece** em n=104, não enfraquece. Haiku se
  compromete com uma categoria quase 2× mais vezes que Opus (39,4% vs.
  21,2%) sobre o mesmo metadado, e pelo menos 19 dessas vezes é
  especificamente onde Opus — seguindo a MESMA instrução de sistema "nunca
  invente" (`advisor.py:97`) — preferiu não responder.
- Recomendação final para a decisão 1 do gate: **manter Opus 5** no
  advisor. O argumento de custo do plano original (diferença de centavos
  para o catálogo inteiro) nunca foi a razão real da proposta de descer de
  modelo — era a suposição "rotular três categorias não precisa de modelo
  caro", e essa suposição tem agora 19+ contraexemplos medidos, numa fração
  do acervo (39,10% das sessões, D-047) grande o bastante para pesar. Se no
  futuro alguém quiser reabrir a decisão 1, o caminho é enrijecer o
  prompt/schema especificamente para Haiku (ex.: exigir confiança mínima
  explícita, ou threshold de concordância entre duas chamadas) — não trocar
  o modelo sem mudar o contrato.
- Como reverter: nada a reverter — medição e correção de bug em script de
  staging, nenhuma mudança em `fotoorganizer/**`. `docs/PLANO_IA_E_PRODUTO.md`
  segue não editado (entregável de fase fechada); a correção fica registrada
  aqui.
- Status: decidido (recomendação); aprovação final da decisão 1 do gate
  segue sendo do dono

## D-050 — O mapa do lugar estimado (item 1 do roadmap, fase 9) existe e funciona, mas ninguém acha
- Fase: 9 (achado de UX, fora de qualquer fase aberta — registrado por
  verificação ao vivo pedida pelo dono)
- Classe: A
- Data: 2026-08-13
- Contexto: o dono pediu para rodar o item 1 do roadmap ("mapa do lugar
  estimado com raio de incerteza"). Servidor local (`python -m fotoorganizer
  web`, porta 8765) subido contra o catálogo real, sem gerar sugestão nova
  (já havia 96.549 pendentes/143 aprovadas/272 grupos persistidos de antes
  — nenhuma escrita nova no catálogo nesta verificação). Confirmado ao vivo:
  grupo "Brasil" (10–26/04/2009, 2.133 fotos) mostra círculo tracejado de
  raio de incerteza em volta de coordenada herdada (158 fotos herdando de
  `IMG00019-20090423-1706.jpg`, Δt 3h55min, "o raio pode crescer até 50 km"),
  distinto do ponto cheio de coordenada lida, com aviso separado para as 159
  fotos "fora de alcance" (arquivo não responde, D-028/D-033). O mecanismo
  descrito no `ROADMAP.md` item 1 está implementado e correto.
- Achado: o dono tentou navegar até o mapa sozinho, no próprio app, e não
  achou. Não é erro de uso — é desenho: `webapp/src/App.tsx:88-91` decide
  deliberadamente NÃO dar ao mapa uma aba própria ("Lista × Mapa vale só
  quando o recorte É um grupo... por isso é um controle da tela do grupo, e
  não uma sétima aba no topo"). Na prática isso exige 3 passos sem nenhuma
  affordance visual: aba Viagens → abrir um card de viagem específico →
  dentro da Biblioteca que abre, achar o toggle Lista/Mapa (sem ícone, sem
  destaque, só aparece com um grupo já aberto). Nenhum link "ver no mapa"
  existe no Panorama nem nos próprios cards da aba Viagens.
- Por quê o desenho original não é irracional, mas falhou na prática: a
  lógica de "mapa só faz sentido com um grupo" está certa — o problema não é
  a regra, é a ausência de qualquer pista de que a tela existe antes de já
  saber procurá-la. Isso é table stakes de descoberta de feature (nem chega
  a ser um caso de UX complexo), e mesmo assim ninguém achou sem ajuda.
- Não corrigido nesta sessão: `webapp/src/**` segue fora da fronteira até a
  fase 5 ser aprovada (`docs/prompts/00-protocolo.md:80-88`). Registrado
  como achado para entrar no escopo de UX quando a fronteira abrir —
  candidatos óbvios: badge/ícone de mapa no card da aba Viagens quando o
  grupo tem lugar estimado ou lido, ou um atalho direto a partir do
  Panorama na faceta "local_estimado".
- Como reverter: nada a reverter — achado registrado, nenhum código
  alterado.
- Status: decidido (achado registrado; correção fica para fase de UX
  futura)

## D-051 — "Gerar sugestões" não é geo-first por desenho: cascade prioriza pasta/tempo, geocodificação é lazy por sessão

- Fase: diagnóstico solicitado pelo dono, fora de fase aberta (gate da
  fase 5 segue fechado)
- Classe: B
- Data: 2026-08-13
- Contexto: o dono relatou que o botão "Gerar sugestões" não se comporta
  conforme o objetivo central do produto — priorizar geolocalização como
  critério principal, mapeando primeiro todas as fotos com GPS próprio
  (celular + câmera) antes de qualquer correlação por data/hora.
  Investigação em 3 frentes paralelas (implementação atual, decisões/docs
  já registrados, boas práticas de DAM), somente leitura, sem escrita em
  `fotoorganizer/**`/`webapp/src/**`.
- Achado central: a funcionalidade existe e roda ponta a ponta
  (`webapp/src/components/StatusBar.tsx:131` → `POST /api/sugestoes/gerar`
  → `SuggestionEngine.gerar()`, `fotoorganizer/classification/engine.py:243-291`)
  e respeita os invariantes de segurança — nunca move/renomeia (regra 6),
  evidência com confiança expõe origem, exatamente o modelo de
  `docs/CONFIANCA.md` (regra 7). O que falha é a ORDEM: `gerar()` chama
  `_correlacionar` (correlação temporal entre fontes,
  `grouping/correlacao.py`) e `agrupar_viagens` (sessão por gap de 3 dias)
  ANTES de qualquer geocodificação, que só acontece depois, lazy, por
  sessão, dentro de `_classificar`. Viola a regra 1 (mapear GPS de tudo
  primeiro) e a regra 2 (nunca correlacionar por tempo antes de concluir o
  geo) diretamente — e não é acidente: `docs/AGRUPAMENTO.md` documenta essa
  ordem (pasta/álbum → sessão temporal → geo por sessão) como calibrada
  contra 17/17 cenários em `scripts/avaliar_agrupamento.py`. Reordenar é
  inversão de arquitetura com risco de regressão medido, não ajuste
  pontual.
- Gap real e barato de corrigir, separado do ponto acima: XMP e IPTC são
  extraídos e persistidos (`metadata/purepython.py`) mas nenhuma linha em
  `classification/` ou `grouping/` os usa na cascata de evidências —
  regra 4 só parcialmente satisfeita. MakerNote fica de fora por decisão
  deliberada já registrada (D-027); pesquisa externa (PhotoPrism, Immich,
  exiv2) confirma que GPS raramente vive só ali — sem motivo para
  reverter D-027.
- Correção a uma premissa herdada de sessão anterior: o handoff que abriu
  esta sessão registrava "Decisão 3 (inventário por pasta) travada até
  resolver sobreposição de desenho com o Item B (protecao-julgamento)".
  Releitura completa do README do Item B e de todo o corpus de docs não
  encontrou NENHUMA sobreposição — o Item B cobre só export/backup/checagem
  de esquema, nunca toca correlação temporal ou GPS. A única menção real a
  "inventário por pasta" é a decisão 3 do gate em
  `docs/PLANO_IA_E_PRODUTO.md` §8, que trata de timing de lançamento
  (antes/depois), não de conflito técnico. Tratando essa premissa como não
  confirmada; se a trava veio de conversa fora do que está documentado,
  precisa virar decisão própria antes de valer.
- Recomendação — plano faseado, nenhuma fase escreve em
  `fotoorganizer/**`/`webapp/src/**` sem aprovação explícita:
  1. Alimentar XMP/IPTC já extraídos na cascata de evidências (regra 4) —
     baixo risco, não muda ordem de decisão geo/tempo.
  2. Medir (não implementar) se geocodificação global-antes-de-correlação
     muda o resultado do benchmark de 17 cenários e do acervo real —
     decide se a inversão de arquitetura (regra 1-2) vale o custo.
  3. Só se a medição mostrar ganho: reordenar `SuggestionEngine.gerar()` e
     atualizar `docs/AGRUPAMENTO.md`, com o benchmark expandido como
     critério de regressão.
  4. Esclarecer a origem real da trava do inventário por pasta antes de
     decidir a decisão 3 do gate.
  Detalhamento completo, com file:line de cada achado e critério de
  verificação executável por fase, em
  `docs/diagnostico-gerar-sugestoes-geo-first.md`.
- Como reverter: nada a reverter — investigação somente leitura, nenhuma
  linha de `fotoorganizer/**`/`webapp/src/**` foi tocada.
- Status: aguardando (classe B — plano fica pronto para entrar nas fases
  quando o dono aprovar o gate da fase 5; decisão de inverter a ordem
  geo/tempo — item 3 do plano acima — precisa de medição própria antes de
  qualquer aprovação)

## D-052 — Regra 1-2 (geo primeiro) não exige reordenar a cascata de categoria: geocoding e herança de GPS já são funções puras, migráveis para a carga

- Fase: revisão de D-051, mesmo diagnóstico
- Classe: B
- Data: 2026-08-13
- Contexto: o dono, revisando D-051, propôs resolver a violação das
  regras 1-2 (mapear GPS antes de correlacionar por tempo) resgatando
  todos os dados/geolocalização já durante a carga (import/scan), não na
  geração de sugestão — uma base completa desde o início, em vez de
  resolver depois. Verifiquei viabilidade técnica lendo o código dos três
  pontos envolvidos.
- Achado: viável, e com risco bem menor do que a Fase B/C que D-051 havia
  desenhado. `LocationResolver.resolve(session, lat, lon)`
  (`fotoorganizer/geolocation/resolver.py:36-66`) é função pura por
  coordenada, cache-keyed a 3 casas decimais (~110 m) na tabela
  `locations` — zero dependência de sessão, grupo ou classificação, e o
  próprio docstring do módulo já descreve isso. `estimar_offsets` e
  `herdar_gps` (`fotoorganizer/grouping/correlacao.py:63-194`) se
  autodescrevem no cabeçalho do módulo como "funções puras" que operam
  sobre a lista inteira de fotos do catálogo (`list[FotoRef]`) — não
  recebem `_Sessao`, não dependem da cascata de categoria. As três hoje só
  são chamadas de dentro de `SuggestionEngine.gerar()`
  (`engine.py:253,741,763`) porque ninguém as moveu, não por necessidade
  arquitetural.
- Consequência: a cascata de CATEGORIA (Viagens/Família/Eventos,
  `_categoria()`, D-034, calibrada em 17/17 cenários) é código separado
  que consome local JÁ resolvido (país/região/cidade), nunca coordenada
  bruta — mover a geo-resolução para a carga não toca nela e não exige
  refazer o benchmark de categoria. Isso substitui a recomendação de D-051
  ("medir antes de reordenar"): a mudança proposta não é uma inversão de
  cascata, é mover uma função já pura para um estágio anterior do
  pipeline.
- Risco residual, real, a desenhar antes de implementar: hoje a herança é
  recalculada do zero a cada `gerar()`. Persistida na carga, cria um
  problema de invalidação que não existe hoje — uma foto que chega depois
  pode ser doadora melhor (Δt menor) para uma foto já processada, e
  mudança de constante calibrada (D-025, D-032) precisa de forma de
  re-rodar sem reprocessar o catálogo inteiro a cada scan incremental.
  Precedente direto: `Evidence.versao_logica` já resolve o mesmo problema
  para sugestões — o caminho é versionar a herança do mesmo jeito, não
  inventar um mecanismo novo.
- Recomendação revisada: a Fase B do plano de D-051 ("medir se vale a pena
  reordenar") vira Fase B' — desenhar e implementar um passo de
  geo-resolução (GPS próprio + herança) que roda uma vez por scan/carga,
  incremental, com invalidação por `versao_logica`, gravando em
  `media.location_id` e uma tabela de heranças persistida.
  `SuggestionEngine.gerar()` passa a LER o resultado já persistido em vez
  de recalcular. A cascata de categoria não muda uma linha. Detalhe
  atualizado em `docs/diagnostico-gerar-sugestoes-geo-first.md`.
- Como reverter: nada a reverter — ainda não implementado, é refinamento
  de plano sobre leitura de código existente.
- Status: aguardando (plano revisado; pronto para entrar nas fases quando
  o dono aprovar o gate da fase 5)

## D-053 — Categoria travada em 3 valores em dois lugares; expansão é um eixo novo (tipo de mídia), não mais opções no mesmo campo

- Fase: revisão de D-051/D-052, mesmo diagnóstico
- Classe: B
- Data: 2026-08-13
- Contexto: o dono notou que o produto só tem 3 categorias organizacionais
  (Viagens/Família/Eventos) e pediu para pesquisar a taxonomia de sistemas
  de referência (PhotoPrism, Immich, Google Fotos, Apple Fotos, Lightroom)
  para avaliar se cabe mais.
- Achado 1 — o limite é estrutural, em dois lugares independentes: a
  cascata determinística (`_CATEGORIAS_PASTA`, `engine.py:91-93`) E o
  schema JSON do advisor LLM (`enum: ["Viagens", "Eventos", "Família"]`,
  `advisor.py:72`). Mesmo que o modelo "quisesse" propor outra categoria,
  o `output_config` estruturado bloqueia — não é limitação do prompt, é
  limitação de schema.
- Achado 2 — pesquisa (Google Fotos, Apple Fotos, PhotoPrism, Immich,
  Lightroom) mostra que a expansão de taxonomia relevante para este
  projeto é OUTRO EIXO, não mais valores de "por que essa sessão existe":
  tipo/proveniência de mídia — Capturas de Tela, WhatsApp/Mensageria,
  Fotos ao Vivo, Panorama — todos detectáveis só por metadado (resolução,
  ausência de EXIF de câmera, XMP `GPano`/`ContentIdentifier`, padrão de
  nome de arquivo `IMG-YYYYMMDD-WAxxxx`), sem depender de visão
  computacional (que segue fora de escopo, mesmo motivo de D-035). RAW já
  é distinguível por extensão, não precisa de campo novo. Misturar esse
  eixo no campo `categoria` existente seria erro de modelagem — uma foto
  pode ser Panorama E parte de uma Viagem ao mesmo tempo, os dois não
  competem pelo mesmo valor.
  Descartado por sinal fraco/ruidoso: "Documentos/Recibos" e "Selfies" —
  a própria comunidade do Immich reporta falso positivo tentando detectar
  screenshot só por metadado quando EXIF de câmera aparece mesmo em
  captura de tela; Google Fotos resolve os dois via OCR/detecção facial,
  ou seja, visão — fora de escopo pelo mesmo motivo de D-035.
- Achado 3, hipótese não medida: parte dos 39,10% de sessões "neutra"
  (D-047) pode não ser "faltou evidência para Viagens/Família/Eventos" —
  pode ser "genuinamente não é nenhuma das três", como uma sessão inteira
  de capturas de tela ou de fotos recebidas por WhatsApp. A instrução
  "nunca invente" (`advisor.py:97`) está funcionando corretamente nesse
  caso — o problema não é o advisor inventar, é o produto não ter destino
  nenhum para esse conteúdo. Não medido ainda: que fração das sessões
  "neutra" concentra padrão de nome WhatsApp ou resolução de tela de
  dispositivo comum no catálogo real.
- Recomendação: (a) não adicionar valores ao enum de `categoria`
  existente; (b) desenhar um facet novo (`tipo_midia` ou equivalente,
  evidência própria no mesmo modelo de `docs/CONFIANCA.md`) para os
  sinais fortes de metadado (Screenshot, WhatsApp, Live Photo, Panorama);
  (c) medir no catálogo real, ANTES de implementar, se isso reduz a
  fração "neutra" o bastante para justificar o trabalho — mesmo padrão de
  medir-antes-de-decidir que já rege D-024 a D-052.
- Como reverter: nada a reverter — pesquisa e recomendação, nenhum código
  alterado.
- Status: aguardando (classe B — medição no catálogo real é o próximo
  passo antes de qualquer decisão de implementar)

## D-054 — Hipótese de D-053 refutada: sessões "neutra" não são screenshots/WhatsApp disfarçados

- Fase: revisão de D-053, mesmo diagnóstico (Fase E do plano)
- Classe: A — medição com resultado negativo claro, sem julgamento em
  aberto
- Data: 2026-08-13
- Contexto: D-053 levantou a hipótese de que parte dos 39,10% de sessões
  "neutra" (D-047) pudesse ser conteúdo que genuinamente não é Viagens/
  Família/Eventos — sessões inteiras de captura de tela ou fotos recebidas
  por WhatsApp — e recomendou medir antes de desenhar um facet novo.
  `scripts/medir_categorias_ausentes.py` (novo) rodou a passada completa
  sobre as 104 sessões neutra reais (mesmo conjunto de D-047/048/049),
  instrumentando `SuggestionEngine._consultar_advisor` por monkeypatch em
  tempo de execução — nenhum arquivo de `fotoorganizer/**` foi editado —
  para capturar os membros completos de cada sessão, não só os 8 exemplos
  que `ClusterInfo` carrega.
- Resultado: **0 de 104 sessões neutra** (0% das 41.901 fotos) têm
  qualquer traço — nem majoritário, nem parcial, nem um único arquivo —
  de padrão de nome WhatsApp ou de captura de tela. Checagem adicional
  direto no catálogo (fora da amostra de sessões neutra, SQL somente
  leitura) confirma que não é nome perdido na importação: no acervo
  inteiro (`papel='ACERVO'`, 96.692 registros), só 1 arquivo com padrão
  parecido com WhatsApp, 2 com nome de captura de tela, 187 PNG (0,19%).
  O conteúdo genuinamente não está no acervo em volume nenhum — não é
  falso negativo do sinal de metadado.
- Interpretação: a hipótese de D-053 estava errada para este acervo. Faz
  sentido em retrospecto — é uma biblioteca fotográfica curada de 25 anos
  (Canon + Lightroom, D-028/D-029), não um despejo de rolo de celular com
  forward de grupo de WhatsApp. Os 39,10% de sessões "neutra" continuam
  sem explicação alternativa medida — a leitura original de D-047
  (residual genuíno da cascata determinística, grande demais para ser
  ignorado, não pequeno o bastante para ser resíduo) segue de pé.
- Recomendação: **não implementar** o facet `tipo_midia`
  (Screenshot/WhatsApp) com a justificativa de reduzir a fração "neutra"
  — a medição mostra que não reduziria nem uma sessão neste acervo. Se o
  facet tiver valor por outro motivo (filtrar/navegar por tipo de mídia),
  é decisão de produto separada, sem essa medição a favor e sem urgência
  medida.
- Como reverter: nada a reverter — medição negativa, nenhum código de
  produção alterado.
- Status: decidido (hipótese refutada por medição; a recomendação de
  D-053 de "medir antes de implementar" foi seguida, e a resposta é não
  implementar por este motivo)

## D-055 — Fase D fechada: dono confirma que a trava do Item B não tinha base real

- Fase: revisão do diagnóstico, fecha a Fase D do plano de D-051
- Classe: A — confirmação direta do dono, sem julgamento em aberto
- Data: 2026-08-13
- Contexto: D-051 apontou que a premissa herdada do handoff que abriu esta
  sessão ("Decisão 3 do gate travada até resolver sobreposição de desenho
  com o Item B/protecao-julgamento") não tinha base em nenhum documento —
  releitura completa do README do Item B e de todo `docs/DECISOES.md`,
  `docs/PLANO_IA_E_PRODUTO.md` e `docs/ROADMAP.md` não encontrou nenhuma
  sobreposição real. Perguntei diretamente ao dono se confirmava.
- Resposta do dono: confirma — a trava não tem origem real fora dos
  documentos.
- Consequência: a decisão 3 do gate ("inventário por pasta entra antes ou
  depois do lançamento", `docs/PLANO_IA_E_PRODUTO.md` §8) fica livre para
  ser decidida independente do Item B — não precisa mais esperar a
  resolução de um conflito que não existia. A decisão 3 EM SI (timing do
  inventário) segue em aberto; só a trava artificial foi removida, não a
  decisão.
- Como reverter: não se aplica — remoção de uma trava incorreta, nenhum
  código alterado.
- Status: decidido (Fase D do plano de D-051 encerrada; decisão 3 do
  gate segue aguardando o dono, agora sem dependência falsa)

## D-056 — Dono aprova o plano da fase 5 para as Fases A e B' do diagnóstico de "Gerar sugestões"

- Fase: 5 (abre a fronteira, `docs/prompts/fase-5-ia-e-produto.md`)
- Classe: B — decisão do dono, registrada
- Data: 2026-08-13
- Contexto: D-051/D-052 desenharam duas fases de implementação — A
  (alimentar XMP/IPTC na cascata de evidências) e B' (mover
  geo-resolução para a carga) — para corrigir os gaps encontrados no
  diagnóstico de "Gerar sugestões" contra o objetivo geo-first. As duas
  ficaram bloqueadas pela fronteira fechada desde D-001
  (`fotoorganizer/**`, `webapp/src/**`, migrações Alembic,
  `pyproject.toml`, `CLAUDE.md`), que só abre com aprovação formal do
  dono ao plano da fase 5.
- Decisão do dono: "Aprovado", em resposta direta à pergunta "aprovar
  formalmente o plano da fase 5 para destravar as Fases A e B'".
- Escopo tratado como aprovado: implementar a Fase A e a Fase B'
  exatamente como desenhadas em
  `docs/diagnostico-gerar-sugestoes-geo-first.md` e em D-051/D-052 — não
  é abertura geral e irrestrita de `fotoorganizer/**`/`webapp/src/**`
  para qualquer mudança futura, e não inclui a decisão 3 do gate (timing
  do inventário por pasta), que segue explicitamente aberta (D-055).
- Como reverter: os commits de cada fase são independentes e revertem
  isolados, mesmo padrão já usado no projeto (D-016).
- Status: decidido pelo dono

## D-057 — Fase A implementada: palavra-chave XMP/IPTC vira evidência de categoria

- Fase: 5 (implementação, autorizada por D-056)
- Classe: A — execução do que já estava desenhado e aprovado
- Data: 2026-08-13
- Contexto: D-056 abriu a fronteira para a Fase A (alimentar XMP/IPTC na
  cascata de evidências, regra 4 de D-051). Implementada como fatia
  vertical (skill `fatia-vertical`): `fotoorganizer/classification/engine.py`
  ganhou `_carregar_curadoria` (uma consulta por geração, evita N+1) e um
  novo passo em `_categoria()`; `fotoorganizer/classification/confidence.py`
  ganhou a origem `curadoria` (score 0.55, mesmo tier de `album_externo`).
- Achado da revisão com olhos frescos (antes do commit): a ordem original
  colocava a palavra-chave (0.55) ANTES do tipo de sessão decidido por
  GPS/geocodificação (0.85-0.95) na cascata — uma foto isolada com
  palavra-chave divergente (ex.: vinda de álbum externo que só coincide
  no tempo) fragmentaria o destino de uma viagem inteira já decidida com
  alta confiança. Corrigido: palavra-chave só decide quando pasta E
  tipo de sessão não decidiram. Coberto por
  `test_curadoria_nao_sobrepoe_sessao_de_alta_confianca`.
- Verificação: `scripts/verificar.sh` verde (696 testes, 17/17 benchmark,
  108 testes de UI, build); provado no Inspector real contra catálogo
  sintético isolado (HOME redirecionado, mesmo padrão de D-010).
- Efeito no acervo real: quase nulo hoje — só 8 entradas de curadoria no
  catálogo inteiro (D-054). O ganho é a regra 4 satisfeita e o mecanismo
  pronto para quando houver mais tagging XMP/IPTC, não uma melhoria
  medida imediata.
- Como reverter: `git revert 7492853` — commit único e isolado.
- Status: decidido (implementado e commitado, `7492853`)

## D-058 — Fase B' implementada: geo-resolução cedo, com escopo menor do que D-052 previa

- Fase: 5 (implementação, autorizada por D-056) — fecha o plano de D-051
- Classe: A — execução do que já estava desenhado e aprovado, com ajuste
  de escopo descoberto durante a implementação
- Data: 2026-08-13
- Contexto: D-056 abriu a fronteira para a Fase B' (mover geo-resolução
  para a carga, D-052). Ao investigar o código para implementar, ficou
  claro que `_correlacionar`/`_persistir_herancas` (herança de GPS entre
  fontes) JÁ rodavam cedo em `gerar()`, uma vez por catálogo inteiro, e
  já persistiam em colunas (`gps_lat_estimado` etc.) — D-052 tinha
  avaliado isso como não-persistido; estava desatualizado. O que
  realmente era lazy: a GEOCODIFICAÇÃO (`LocationResolver.resolve`,
  coordenada → país/região/cidade), chamada só dentro de
  `_evidencias_geo`, só para fotos sem sugestão decidida nesta rodada.
- Implementado: `fotoorganizer/classification/engine.py` ganhou
  `_resolver_locations(session, midias)`, chamado logo após
  `_persistir_herancas` — resolve `location_id` para TODA foto com
  coordenada (própria ou herdada, via `MediaFile.coordenada`), inclusive
  já decidida e inclusive referência SINAL (usada pela Biblioteca para
  filtrar por país, `repositories/media.py`). `_evidencias_geo` mantido
  sem mudança — continua decidindo quais campos expor por granularidade,
  que depende do objeto `Heranca`, não só do `Location` resolvido.
- Achado da revisão com olhos frescos (antes do commit): sem memoização
  por coordenada dentro do próprio loop, um cluster de centenas de fotos
  da mesma viagem viraria um `SELECT` por foto em vez de um só — a
  tabela `locations` evita recalcular via geocodificação externa, mas
  não evita o `SELECT` repetido dentro da mesma geração. Corrigido com
  um dicionário local por `cache_key`, mesma chave que `LocationResolver`
  já usa.
- Escopo reduzido em relação a D-052: NÃO é ainda um job separado do
  scan/carga — roda dentro de `gerar()`, mesmo padrão de
  `_correlacionar`. Separar em job próprio (a visão original de D-052)
  fica para quando houver necessidade medida de resolver local sem
  esperar geração de sugestão — não implementado agora, sem prazo.
- Verificação: `scripts/verificar.sh` verde (697 testes, 17/17 benchmark,
  108 testes de UI, build); provado via API real do servidor
  (`/api/midia/{id}`) contra catálogo sintético isolado — foto com
  destino editado manualmente, `location_id` zerado à força, volta a
  mostrar o lugar resolvido depois de regenerar.
- Como reverter: `git revert b5f94b2` — commit único e isolado.
- Status: decidido (implementado e commitado, `b5f94b2`). Plano de D-051
  fica com todas as 5 fases concluídas (A, B', D, E) — só a decisão 3 do
  gate (timing do inventário por pasta) segue aberta, sem relação com
  este plano.

## D-059 — Decisão 1 do gate: dono propõe Sonnet 5, ainda não medido — script generalizado para comparar qualquer par de modelos

- Fase: 5 (revisão do plano, decisão 1 do gate — segue D-047/D-048/D-049)
- Classe: B
- Data: 2026-08-13
- Contexto: revisando as três decisões do gate, o dono propôs usar
  Sonnet 5 no advisor em vez de manter Opus 5 (recomendação de D-049) ou
  descer para Haiku 4.5 (opção original do plano, descartada por D-049).
  D-047/048/049 mediram especificamente Opus 5 × Haiku 4.5 nos 104
  clusters reais — Sonnet nunca entrou nessa comparação.
- Por quê não registrar direto: toda decisão desta sessão (D-024 a D-058)
  foi fechada com medição, não com escolha a priori — abrir exceção aqui
  seria inconsistente, ainda mais porque o achado de D-049 (Haiku inventa
  onde Opus recusa, violando "nunca invente") só apareceu medindo, nunca
  teria aparecido em teoria.
- Preparado: `scripts/medir_qualidade_advisor.py` generalizado — antes
  hardcoded para comparar só Opus×Haiku (`Comparacao.opus`/`.haiku`,
  texto do relatório fixo); agora aceita `--modelo-a`/`--modelo-b`
  (default preserva o comportamento anterior: opus-5 vs haiku-4.5,
  nenhuma mudança na comparação histórica de D-048/049). Adicionado
  `"sonnet-5": "claude-sonnet-5"` ao dicionário `MODELOS`. Lógica de
  `.padrao` testada localmente (5 casos, sem chamar API) — idêntica ao
  original, só generalizada. Fica em `scripts/`, fora da fronteira da
  fase 5 (não precisou de D-056).
- Como rodar (classe C — o dono roda, com a própria `ANTHROPIC_API_KEY`,
  esta sessão não manuseia a credencial, mesmo padrão de D-048/049):
  `ANTHROPIC_API_KEY=... .venv/bin/python scripts/medir_qualidade_advisor.py
  --periodos clusters_neutra_104.json --modelo-a opus-5 --modelo-b sonnet-5`
- Não decidido ainda: se Sonnet 5 se comporta como Opus (recusa quando
  falta evidência) ou como Haiku (inventa). Decisão 1 do gate segue
  aberta até essa medição.
- Como reverter: nada a reverter — script generalizado é aditivo,
  comparação Opus×Haiku default preservada.
- Status: aguardando (medição real fica com o dono, classe C)

## D-060 — Decisão 1 do gate fechada: Sonnet 5 no advisor, medido nos 104 clusters reais

- Fase: 5 (revisão do plano, decisão 1 do gate — fecha D-047/D-048/D-049/D-059)
- Classe: B
- Data: 2026-08-13
- Contexto: o dono rodou `scripts/medir_qualidade_advisor.py --modelo-a
  opus-5 --modelo-b sonnet-5` (script generalizado em D-059) contra os
  mesmos 104 clusters "neutra" de D-047/048/049, no terminal dele, com a
  própria `ANTHROPIC_API_KEY`. Nenhuma credencial foi manuseada por esta
  sessão.
- Resultado, comparado com Opus×Haiku (D-049):

  | | Opus × Haiku (D-049) | Opus × Sonnet (agora) |
  |---|---:|---:|
  | Concordância | 73/104 (70,2%) | 86/104 (82,7%) |
  | Discordância | 31/104 (29,8%) | 18/104 (17,3%) |
  | "modelo barato afirma, Opus recusa" | ≥19/104 (18,3%, piso — bug do relatório antigo impediu o número exato) | 7/104 (6,7%), número exato |
  | Modelo barato se compromete | 41/104 (39,4%) | 28/104 (26,9%) |
  | Opus se compromete (baseline) | 22/104 (21,2%) | 23/104 (22,1%) — quase igual; a diferença de 1 é efeito colateral provável da Fase B' (D-058) ter resolvido `location_id`/`lugares` para mais clusters do que na rodada de D-049 |

  Sonnet cai no padrão de risco (afirmar onde Opus recusa) de 2,7 a 4,4×
  menos que Haiku, e se compromete numa taxa muito mais perto de Opus
  (23 vs 28) do que Haiku estava (22 vs 41).
- Achado qualitativo que pesa contra, não só a favor: o primeiro exemplo
  da amostra de risco do Sonnet é **o mesmo cluster** que D-048 já tinha
  flagado como erro do Haiku — "Carnaval da Escola 2001" + "na Praia -
  Fev 2001" (2 pastas, histórias diferentes no mesmo payload). Opus
  recusa citando o conflito; Sonnet, como o Haiku antes dele, lê só uma
  pasta e afirma "Eventos/Carnaval da Escola 2001". Dois outros exemplos
  da amostra inferem "Viagens" só da cadência de pastas diárias
  consecutivas, sem lugar nem palavra de viagem — mesmo tipo de invenção
  da "Viagem de Ano Novo" do Haiku em D-048. Um exemplo ("Peru-Bolivia-
  Chile", nome de pasta que lista 3 países) parece captura correta, não
  erro — Opus só recusou por ruído de outras pastas no mesmo cluster.
- Por que a taxa residual (7/104) é aceitável: todo output do advisor já
  é evidência de confiança média-baixa (0,55, abaixo de qualquer regra
  determinística) e nunca decide sozinho — invariante 2 do projeto
  (operação física só como plano até aprovação humana) segura esse
  resíduo antes de qualquer cópia real acontecer.
- Decisão do dono: confirma Sonnet 5. Aplicado em
  `fotoorganizer/classification/advisor.py::MODELO_PADRAO`
  (`claude-opus-5` → `claude-sonnet-5`), único ponto que decide o modelo
  do advisor — `classification/lexico.py` tem seu próprio
  `MODELO_PADRAO`, não tocado (é um sistema diferente, classificação de
  NOME de pasta/álbum, não medido nesta decisão).
- Verificação: `scripts/verificar.sh` verde (697 testes, 17/17 benchmark,
  108 testes de UI, build) — nenhum teste referencia o modelo diretamente
  (todos usam `FakeAdvisor`/`NullAdvisor`), então a troca não tinha como
  quebrar teste nenhum; a garantia real é a medição acima, não a suíte.
- Como reverter: uma linha (`MODELO_PADRAO`) mais o comentário —
  `git revert` do commit isolado.
- Status: decidido pelo dono. Decisão 1 do gate fechada.

## D-061 — Decisão 3 do gate fechada: inventário por pasta entra antes do lançamento

- Fase: 5 (revisão do plano, decisão 3 do gate — segue D-055, fecha o gate)
- Classe: B
- Data: 2026-08-13
- Contexto: `docs/PLANO_IA_E_PRODUTO.md` §8 já recomendava "antes, é
  barato agora e caro depois" para o inventário por pasta
  (`inventario.json`+`INVENTARIO.md` por pasta de destino, evidência por
  foto). A trava com o Item B (protecao-julgamento) não existia de
  verdade (D-055) — a única pendência real era o dono confirmar o
  timing.
- Recomendação dada: manter "antes", especificamente antes da primeira
  aprovação de execução física real — nenhuma cópia ainda rodou no
  acervo do dono (D-011), então o custo de retrofit ainda não começou a
  se acumular, e o histórico do próprio projeto (D-026, D-035, D-036,
  D-037) mostra retrofit como fonte real de dor, não hipótese.
- Decisão do dono: confirma "antes do lançamento".
- Consequência: as três decisões do gate da fase 5 estão fechadas —
  decisão 1 (Sonnet 5, D-060), decisão 2 (visão/rostos só local, sem
  pendência), decisão 3 (inventário antes do lançamento, aqui). O que
  falta não é mais decisão, é plano de implementação: schema exato de
  `inventario.json`/`INVENTARIO.md`, e onde no pipeline de
  `operations/executor.py` ele entra — não desenhado nesta sessão, fica
  para quando o dono priorizar essa fatia.
- Como reverter: registro de decisão, não código — não se aplica.
- Status: decidido pelo dono. Gate da fase 5 fechado nas três decisões.

## D-062 — Desenho do inventário por pasta pronto para implementar

- Fase: 5 (segue D-061) — desenho, não implementação
- Classe: A — leitura de código existente e proposta técnica, sem
  escrever em `fotoorganizer/**`
- Data: 2026-08-13
- Contexto: D-061 fechou a decisão 3 (inventário antes do lançamento).
  Faltava o desenho técnico — schema, ponto de entrada no pipeline,
  comportamento de falha.
- Desenho completo em `docs/desenho-inventario-por-pasta.md`. Resumo:
  - Hook em `operations/executor.py::_executar_item`, logo depois da
    cópia verificada por hash — nunca antes.
  - Um par `inventario.json`/`INVENTARIO.md` por PASTA de destino
    (`Path(item.destino).parent`), aditivo entre execuções de planos
    diferentes ao longo do tempo, não um par por foto ou por plano.
  - `Suggestion.evidencias` (relationship já existente) dá a lista de
    `Evidence` sem consulta nova — mesmo dado que o Inspector já mostra.
  - `versao_logica` por ENTRADA, não só no cabeçalho — fotos na mesma
    pasta em execuções diferentes podem ter evidência de versões
    diferentes da lógica.
  - `INVENTARIO.md` sempre regenerado por inteiro a partir do JSON
    (nunca editado à parte) — evita os dois divergirem.
  - Falha ao escrever o inventário NÃO desfaz a cópia já verificada —
    vira `AuditLog` + contador visível (`stats["inventario_falhou"]`),
    não bloqueia a operação.
  - Nenhuma migração Alembic (arquivo em disco, não em `catalog.db`);
    nenhuma mudança em `planner.py`/`classification/**`.
- Não decidido: formato exato do Markdown (tabela vs. lista) — fica para
  quando a implementação for aprovada, não bloqueia o desenho de dados.
- Como reverter: nada a reverter — documento novo, nenhum código
  alterado.
- Status: aguardando aprovação do dono para virar fatia de implementação
  (escopo próprio, fora do que D-056 abriu)

## D-063 — Dono aprova a implementação do inventário por pasta

- Fase: 5 (segue D-062)
- Classe: B — decisão do dono, registrada
- Data: 2026-08-13
- Contexto: D-062 entregou o desenho técnico completo. Faltava aprovação
  explícita para abrir `fotoorganizer/operations/**` — escopo que D-056
  não cobria (aquele foi só para as Fases A/B' do diagnóstico de "Gerar
  sugestões").
- Decisão do dono: aprova implementar, exatamente como desenhado em
  D-062/`docs/desenho-inventario-por-pasta.md`.
- Escopo tratado como aprovado: `fotoorganizer/operations/inventario.py`
  (novo) + hook em `executor.py::_executar_item` + testes. Não inclui
  nenhuma mudança em `planner.py`, `classification/**`, nem migração
  Alembic — o próprio desenho já exclui essas três coisas.
- Como reverter: commit isolado da fatia, revertível sozinho.
- Status: decidido pelo dono

## D-064 — Inventário por pasta implementado

- Fase: 5 (implementação, autorizada por D-063) — fecha a decisão 3 do
  gate (D-061)
- Classe: A — execução do que já estava desenhado e aprovado, com
  correções encontradas na revisão antes do commit
- Data: 2026-08-13
- Contexto: D-063 abriu a fronteira para `fotoorganizer/operations/**`.
  Implementado como fatia vertical (skill `fatia-vertical`):
  `fotoorganizer/operations/inventario.py` (novo) + hook em
  `executor.py::_executar_item`, logo depois da cópia verificada por
  hash.
- Achados da revisão com olhos frescos, corrigidos antes do commit:
  1. O `except` no executor capturava só `OSError` — um
     `inventario.json` corrompido por uma escrita anterior interrompida
     levanta `json.JSONDecodeError` (não é `OSError`), que escaparia e
     abortaria o PLANO INTEIRO no meio, deixando cópias já verificadas
     por hash com o commit do item pendente (a sessão fecha sem
     commitar, mas o arquivo físico já foi copiado — na retomada, o
     executor tentaria recopiar e bloquearia por "destino já existe").
     Corrigido: `except Exception` no executor (é auxiliar, nunca pode
     travar a cópia real) e `_carregar` recupera de JSON corrompido
     preservando o arquivo ruim ao lado (`.corrompido-<timestamp>`) em
     vez de propagar.
  2. Escrita não era atômica (`write_text` trunca antes de escrever) —
     era a causa mais provável do próprio cenário do achado 1. Corrigido
     com write-temp + `os.replace` (atômico no mesmo filesystem).
  3. Campo `tamanho` vinha de `media.tamanho` (do momento do scan), não
     do arquivo realmente copiado e verificado nesta execução —
     corrigido para `destino.stat().st_size`.
- Verificação: `scripts/verificar.sh` verde (701 testes, 17/17
  benchmark, 108 testes de UI, build); prova real — plano completo
  (dry-run + execução, cópia de arquivo de verdade) contra catálogo
  sintético isolado, `INVENTARIO.md` gerado e legível, com evidência e
  justificativa por foto.
- O que ficou fora, conforme o desenho: formato exato do Markdown
  (tabela vs. lista, usei lista com seção "Por quê?" por foto) não foi
  revisado com o dono — é decisão de apresentação, não de dado, ajustável
  sem migração.
- Como reverter: `git revert 6efde4e` — commit único e isolado.
- Status: decidido (implementado e commitado, `6efde4e`). Decisão 3 do
  gate (D-061) está fechada tanto na decisão quanto na implementação.

## D-065 — Badge "Mapa" no card de Viagens/Eventos corrige D-050

- Fase: pós-gate (achado de UX, D-050) — primeira fatia de `webapp/src/**`
  desta sessão, fronteira aberta a pedido explícito do dono
- Classe: A — execução de achado já registrado, sem decisão de produto
  em aberto
- Data: 2026-08-13
- Contexto: D-050 registrou que o mapa do lugar estimado existe e
  funciona desde a fase 9, mas é inacessível na prática — 3 passos sem
  nenhuma affordance visual. Candidato óbvio já apontado ali: "badge/
  ícone de mapa no card da aba Viagens quando o grupo tem lugar
  estimado ou lido".
- Implementado: `webapp/src/components/Trips.tsx` ganhou um badge
  "Mapa" sempre visível (não só hover) em todo card de Viagens/Eventos,
  que abre o grupo direto na visão de mapa — não implementei a variante
  condicional ("só quando tem lugar"), porque exigiria mudança de
  backend (a resposta de `/api/viagens`/`/api/eventos` não carrega essa
  informação hoje) e o mapa vazio já tem estado tratado ("nenhuma foto
  deste grupo tem lugar estimado") — mostrar sempre é mais simples e
  resolve o mesmo problema de descoberta.
- Dois achados da revisão com olhos frescos, corrigidos antes do commit:
  1. O card virou `<div role="button">` pra caber o badge dentro, mas a
     primeira versão colocava o badge como FILHO do card — botão
     aninhado em `role="button"` é anti-padrão ARIA. Corrigido: badge e
     card viraram IRMÃOS dentro de um wrapper `relative`, sem
     `stopPropagation` (não são mais descendente/ancestral).
  2. Card deixou de ser `<button>` nativo — operabilidade por teclado
     (Enter/Espaço) passou a depender de `onKeyDown` escrito nesta
     fatia, sem nenhum teste cobrindo, num app que se declara
     teclado-first (`CLAUDE.md`). Adicionado teste de teclado antes do
     commit.
  3. (Separado, achado e corrigido durante a implementação, não pela
     revisão): `App.tsx` tinha um efeito que resetava a visão pra
     "lista" a cada troca de recorte — sobrescrevia a intenção de abrir
     direto no mapa no mesmo ciclo de render. Corrigido com
     `vistaPendente` (`useRef`), gravado antes de `setRecorte` e
     consumido pelo efeito.
- Verificação: `scripts/verificar.sh` verde (701 testes, 17/17
  benchmark, 113 testes de UI, build); provado no dev server contra o
  catálogo real — clique no badge do card "Gana" abre direto no mapa,
  ponto plotado, painel "Neste lugar" explicando a evidência.
- Branch novo (`claude/mapa-descoberta-d050`), não `handoff-fase-14-
  gate-da711b` — aquele já foi mergeado e a branch remota apagada.
- Como reverter: `git revert d0f215d` — commit único e isolado.
- Status: decidido (implementado e commitado, `d0f215d`). D-050 fechado.

## D-066 — Pasta acentuada em NFD não batia como "downloads"/"capturas" no detector de tipo

- Fase: pós-gate — achado reportado de fora da sessão (auditoria de código),
  primeira fatia de `fotoorganizer/classification/**` desta sessão
- Classe: A — bug de correção determinística, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: `tipo_imagem.py:126` fazia só `pasta.lower()` antes de testar
  substring contra `PASTAS_BAIXADA = ("downloads", "transferências",
  "transferencias")` (`grouping/origens.py`). "Transferências" é o nome
  real do Downloads no macOS em PT-BR, e o Finder/APFS grava pasta
  acentuada em NFD — forma decomposta, com o marcador combinante (ex.
  U+0302) intercalado entre as letras-base. Em NFD, nem `"transferencias"
  in pasta` nem `"transferências" in pasta` batem, porque o `in` de
  substring exige contiguidade que o combinante quebra. Resultado: uma
  foto salva em `~/Transferências` (NFD) caía no branch padrão do
  classificador e virava `foto` normal em vez de `baixada` — perdendo o
  sinal "sem dado de câmera + pasta de download" que a regra 4 existe para
  capturar.
  - A mesma constante `PASTAS_BAIXADA` já era usada corretamente em
    `grouping/albuns.py:58`, via `_normalizar()` (NFKD + strip de acento,
    `geolocation/folder_names.py`) — imune a NFC/NFD por construção. Só o
    uso em `classification/tipo_imagem.py` ficara de fora.
  - Correção **não** confere com um precedente citado no relatório que
    originou este achado: não existe decisão D-070 neste `DECISOES.md`,
    e `grouping/datas.py` **não** normaliza Unicode antes de comparar
    contra `_MESES` — o comentário do próprio módulo (linhas 22–24)
    explica que a normalização foi deliberadamente evitada ali porque
    mudaria o comprimento do texto e estragaria os índices usados para
    recortar o nome que sobra depois da data; a cobertura de "março" é
    feita com as duas grafias como chaves literais do dict, não por
    normalização. Ou seja: pasta de mês acentuado em NFD (`.../Março
    2024/`) **continua** sem bater em `_MESES` hoje — bug real, mas
    diferente deste, fora de escopo aqui porque a correção não é um
    `_normalizar()` de uma linha (quebraria o recorte por índice) e não
    foi pedida.
- Implementado: `tipo_imagem.py` passou a normalizar `pasta` com o
  `_normalizar()` já existente em `geolocation/folder_names.py` (reuso,
  sem duplicar) antes das três comparações de pasta dedicada (mensageiro,
  captura, download); o `marca` de cada lista também é normalizado no
  ponto de comparação, mantendo a grafia original na justificativa
  (`"está na pasta de downloads..."` continua citando `'transferências'`
  como veio da constante).
- Teste novo (`tests/test_tipo_imagem.py`): dois casos parametrizados
  NFC/NFD para pasta de downloads e de capturas de tela, escritos e
  confirmados falhando (NFD) antes do fix, verdes depois.
- Verificação: `scripts/verificar.sh` verde (705 testes, 17/17 benchmark,
  113 testes de UI, build).
- Como reverter: reverter o commit desta fatia — isolado em
  `fotoorganizer/classification/tipo_imagem.py` e
  `tests/test_tipo_imagem.py`.
- Status: decidido e implementado. Achado de escopo relacionado (mês
  acentuado em NFD não bate em `grouping/datas.py`) registrado acima,
  corrigido em D-067 logo abaixo.

## D-067 — Mês acentuado em NFD não batia em grouping/datas.py

- Fase: pós-gate — segunda fatia do mesmo achado (D-066), agora em
  `grouping/datas.py`
- Classe: A — bug de correção determinística, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: `_MESES` (`datas.py:25`) tem `"março"` como chave literal
  digitada em NFC. `separar_data` casava o regex `_MES_ALT` (construído a
  partir das chaves de `_MESES`) direto contra o `segmento` cru, sem
  normalizar. Pasta gravada pelo Finder/APFS em NFD (marcador combinante
  decomposto, ex. "c" + U+0327 em vez do "ç" precomposto) tem comprimento
  diferente da forma NFC — o literal "março" do regex simplesmente não
  casa contra a sequência decomposta, então uma pasta como "Chapada dos
  Guimarães Março 2019" em NFD perdia o mês inteiro (só o ano sobrevivia,
  via o padrão mais fraco de fallback).
  - O comentário original do módulo (removido por este commit) explicava
    por que a normalização tinha sido evitada: mudaria o comprimento do
    texto e estragaria os índices (`m.start()`/`m.end()`) usados para
    recortar o nome que sobra depois da data. Essa preocupação é real
    SE a normalização for aplicada só na comparação, mantendo os índices
    presos ao texto original não-normalizado — mas deixa de ser um
    problema se a normalização for feita uma única vez, no início da
    função, sobre a string inteira: daí em diante, casamento e
    fatiamento operam sobre a MESMA string (a já normalizada), então
    índice e conteúdo nunca dessincronizam.
- Implementado: `separar_data()` normaliza `segmento` para NFC
  (`unicodedata.normalize("NFC", segmento)`) como primeiro passo, antes
  de qualquer `_PADROES`. `data_no_caminho()` não precisou de mudança —
  já delega a cada segmento via `separar_data()`. Mantidas as duas
  chaves "março"/"marco" no dict (ortogonal ao NFC/NFD: cobre quem
  digitou sem cedilha, não forma de codificação Unicode). Comentário do
  módulo reescrito para explicar a normalização de string inteira em vez
  de alegar que normalização "estragaria os índices" — não estraga,
  desde que seja global e no início.
- Teste novo (`tests/test_datas_em_pastas.py`): `test_marco_em_nfd_bate_
  igual_a_nfc` (NFC/NFD via `separar_data`) e
  `test_data_no_caminho_reconhece_marco_em_nfd` (NFC/NFD via
  `data_no_caminho`, caminho completo). Confirmados falhando em NFD
  antes do fix (`git stash` do arquivo de produção, teste vermelho,
  `git stash pop`, teste verde) — sem regressão nos 7 casos preexistentes
  de `test_separa_nome_e_data`.
- Verificação: `scripts/verificar.sh` verde (709 testes, 17/17
  benchmark, 113 testes de UI, build).
- Como reverter: reverter o commit desta fatia — isolado em
  `fotoorganizer/grouping/datas.py` e `tests/test_datas_em_pastas.py`.
- Status: decidido e implementado. D-066 (achado relacionado) fechado.

## D-068 — "Organizáveis" passa a exigir a fonte respondendo, e o funil
inteiro passa a ser contado numa passada só

- Fase: manutenção do funil do acervo (commit `4132160`), defeito de
  definição encontrado depois que os três degraus ficaram juntos na tela.
- Classe: B (muda a definição de um número que aparece em toda tela e o
  conjunto que o filtro "Organizáveis" da Biblioteca devolve).
- Data: 2026-08-04
- Contexto: o funil promete que cada degrau é subconjunto do anterior
  (`Funil` em `fotoorganizer/repositories/inventario.py`). "Alcançáveis"
  olhava `Source.disponivel`; "organizáveis" vinha de
  `MediaRepository.estatisticas()["total"]`, que usa `MediaFile.organizavel`
  (`fotoorganizer/models/catalog.py:184`) — papel `ACERVO` e arquivo não
  ausente, sem nenhuma pergunta sobre a fonte estar montada. Observado ao
  vivo: a pasta "Dubai, Thai & Viet" (source_id=3) saiu do disco, e suas
  2.405 fotos seguiam contadas como organizáveis e listadas sob o filtro
  "Organizáveis" com "volume ou pasta fora de alcance" escrito em cada
  miniatura. Hoje a ordem numérica ainda se sustentava por sorte
  (26.023 < 94.557); com a maior parte do acervo desmontada, o funil deixa
  de afunilar. Havia ainda um segundo descasamento, mais silencioso: os dois
  primeiros degraus contam FOTO (caminho distinto) e o terceiro contava
  REGISTRO.
- Medição no catálogo real (`scripts/medir_alcance_do_organizavel.py`, cópia
  por `.backup`, somente leitura; saída completa no commit desta entrada):
  - 197.338 registros; 26.023 organizáveis pela definição antiga.
  - **2.566 registros (9,9%) de acervo estão em fonte que não responde** —
    2.405 do Dubai, 143 de `Pictures/2025_05_24`, 18 de `/Volumes/photo`. As
    três pastas realmente não existem no disco agora.
  - Contando FOTO em vez de registro, o acervo com arquivo cai de 26.023
    para 22.150 — 3.873 registros são a mesma foto catalogada duas vezes (a
    pasta específica e a varredura de `/Users/acamerini`).
  - Acervo alcançável, contado por foto: **21.989**. Só 161 fotos saem por
    indisponibilidade, porque Dubai e 2025_05_24 têm registro gêmeo na
    varredura da home, que responde. (Esses arquivos também não abrem — o
    arquivo sumiu do disco e nada detectou; é defeito separado, ver abaixo.)
  - 143 de 143 sugestões aprovadas estão em fonte indisponível.
- Opções:
  (a) `MediaFile.organizavel` passa a exigir `Source.disponivel`.
  (b) O funil calcula o próprio terceiro degrau com a checagem de fonte, e o
      filtro "Organizáveis" da grade passa a usar o mesmo critério.
  (c) Aceitar que "organizáveis" é classificação de acervo e não de alcance,
      abandonando a promessa de monotonicidade.
- Escolhida: (b).
- Por quê: (a) é destrutiva por um cabo USB. `organizavel` é usada em
  `classification/engine.py:890` para APAGAR sugestões pendentes de tudo que
  não é acervo — com a fonte na definição, desmontar um disco e gerar
  sugestões apagaria as sugestões pendentes das fotos dele (2.566 hoje, o
  acervo inteiro no dia em que o NAS estiver desligado), e o agrupamento em
  viagens/eventos mudaria de forma conforme o que estivesse montado. Estado
  transitório não pode redefinir classificação permanente — é o mesmo
  princípio do invariante 8. (c) mantém na tela um funil que pode deixar de
  afunilar, e o defeito relatado (fotos "organizáveis" que não abrem)
  continuaria. (b) resolve os dois descasamentos de uma vez: o terceiro
  degrau passa a sair da mesma passada de `levantar()`, na mesma unidade
  (foto) e com a mesma resposta sobre quais fontes respondem — a
  monotonicidade vira propriedade de construção, não coincidência a testar.
  A regra de "é acervo" continua com dono único (`MediaFile.organizavel`), e
  `levantar()` a lê como coluna SQL em vez de reescrevê-la; o que se soma é
  o alcance, que é justamente o que aquele módulo já sabe responder.
  Para não recriar o defeito original (dois números para a mesma palavra), o
  filtro "Organizáveis" da grade recebeu o mesmo critério
  (`_acervo_ao_alcance()` em `fotoorganizer/repositories/media.py`), e
  "faltantes" continua sendo exatamente o complemento.
- O que muda na tela: funil 26.023 → **21.989** organizáveis; filtro
  "Organizáveis" da Biblioteca 26.023 → **23.457** registros (a diferença
  entre 21.989 e 23.457 é foto contada uma vez contra célula desenhada duas,
  e o degrau "no filtro" agora diz isso no título). Panorama, revisão,
  motor de sugestões e planner ficam intactos: continuam vendo os 26.023 de
  acervo, montado ou não.
- O que NÃO mudou, de propósito:
  - `operations/planner.py` continua planejando as 143 sugestões aprovadas
    de fonte desmontada. Omitir trabalho já aprovado pelo dono seria pior que
    falhar na frente dele: o dry-run já recusa item por item com "origem
    indisponível" (`operations/executor.py:83`) antes de qualquer cópia.
  - `Source.disponivel` responde pela RAIZ da fonte, não por arquivo. Como
    `/Users/acamerini` é fonte e responde, os registros gêmeos das fotos do
    Dubai continuam contados como alcançáveis mesmo com o arquivo apagado.
    Corrigir isso é outro trabalho (revarredura marcando `arquivo_ausente`),
    e um `stat` por miniatura na grade está descartado pelo custo — ver o
    comentário em `server/app.py:231`.
- Como reverter: `git revert` do commit desta entrada. Nada foi migrado nem
  reescrito no catálogo — a mudança é de leitura, e as contagens antigas
  voltam inteiras.
- Status: decidido

## D-069 — Auditoria pós-gate da fase 5: 18 achados medidos, nenhum é regressão desta sessão

- Fase: pós-gate — auditoria disparada pelo dono testando a UI depois do
  merge de PR #4/#5/#6 e reportando "caos" (fotos que não carregam, filtros
  confusos, classificações erradas)
- Classe: B — 18 candidatos a decisão, nenhuma implementação feita
- Data: 2026-08-14
- Contexto: quatro achados da revisão ao vivo (Teatro→Viagens, Bezerros→
  Eventos, badge "Alta" enganoso em "Não classificadas", "2013/Gana" sem
  prefixo) motivaram uma auditoria mais ampla, em duas frentes: (A) medir a
  extensão real desses padrões e auditar as demais telas vivas (Panorama,
  Biblioteca, Viagens, Revisão, Duplicatas, Operações); (B) checar se
  PhotoPrism/Immich (já auditados em profundidade na fase 14,
  `docs/referencia-photoprism/`, `docs/referencia-immich/`) têm mecanismo
  para inspirar solução.
- Gate obrigatório antes de investigar: `git diff 48c4378 HEAD` (commit
  anterior à sessão inteira → HEAD) mostra ZERO diferenças em
  `grouping/classifier.py`, `grouping/eventos.py`, `classification/
  lexico.py` — o código que decide Teatro/Bezerros já existia, inalterado.
  `engine.py` mudou só em `_categoria` (nova regra 2b, D-057, abaixo da
  checagem que decide esses casos) e `_resolver_locations` (geo cedo,
  D-051/052/058, pode ter mudado a CONTAGEM do achado "Gana" sem mudar a
  regra). **Nenhum dos 18 achados é regressão desta sessão.**
- **Atualização (mesmo dia):** a comparação empírica (rodar `gerar()` real
  com o código de 48c4378 contra cópia do catálogo, ~1h22 de CPU) terminou
  e confirma o diff sem nenhuma divergência — media_id 233091 e 454553
  produzem, com o código pré-sessão, exatamente o mesmo destino/nível/
  evidência que produzem hoje. Fecha a dúvida por completo.
- Frente B fechada sem scrape novo do demo do PhotoPrism: a auditoria de
  código-fonte da fase 14 já mostra que nem PhotoPrism nem Immich têm
  confiança por campo/inferência (só origem, enum fixo) nem categorização
  automática por nome de pasta — confirmado por busca externa
  (WebSearch/WebFetch) sem achar isso em nenhum produto de mercado
  (Lightroom, Mylio, Synology Photos). Badge enganoso e categoria ambígua
  são problemas sem precedente nos produtos de referência, não há
  mecanismo de terceiro para citar — a solução é original do
  foto-organizer. Onde havia mecanismo relevante (achado 9, lote
  assimétrico — clipboard.vue do PhotoPrism), está citado com
  `arquivo:linha`.
- Os 18 achados, com evidência (query SQL real ou `arquivo:linha`), volume
  medido e severidade, estão em
  `docs/auditoria-pos-gate-fase5.md`. Resumo por tier:
  - **Tier 1 (risco de dado / bloqueio de uso básico)**: duplicata VARIANTE
    pode levar a excluir RAW ou JPEG do plano de cópia sem aviso (2.514
    conjuntos candidatos, 1 já confirmado classificado errado — toca o
    invariante de segurança #8 do `CLAUDE.md`); badge "Alta" reflete só
    confiança da data em 29,6% do acervo (28.635 fotos, 97,8% do maior
    bucket "Não classificadas"); aba Viagens falsamente vazia por
    50–120+s (N+1 de query, provável causa direta do "caos" relatado);
    confiança agregada contradiz as evidências de que depende no próprio
    popover "por quê?".
  - **Tier 2 (misclassificação/falha real, escala moderada)**:
    categorização "Eventos" 100% por heurística fraca, nunca por
    vocabulário literal (11.492 fotos); ações de duplicata falham em
    silêncio; inventário por pasta O(n²), vai travar visivelmente na maior
    pasta real (7.618 fotos); Panorama mostra dois números "organizáveis"
    diferentes (96.692 vs 92.792); "Rejeitar em lote" não existe, só
    "Aprovar em lote".
  - **Tier 3 (inconsistência visual/nomenclatura, sem risco de dado)**:
    destino sem prefixo de categoria (668 fotos); mesma viagem fragmentada
    em 5 grafias/categorias na fila de Revisão; 23 de 60 cards de viagem
    chamados "Brasil"; rótulo da sidebar da Biblioteca não bate com o
    total do filtro (5x de diferença); painel "O acervo" sem loading
    state (13–20s de silêncio); plano preso em "executando" após crash
    nunca reconcilia; sem timestamp de última detecção de duplicata.
  - **Tier 4**: grupos de duplicata não explicam por quê foram agrupados.
- Como cheguei aqui: 3 agentes de domínio em paralelo (`agente-arquivos` →
  Operações/Duplicatas; `agente-imagem` → classificação/geolocalização,
  medição da extensão dos 4 achados originais; `agente-ux` → Panorama/
  Biblioteca/Viagens/Revisão, rodando contra o servidor real em
  `127.0.0.1:8765`), mesmo padrão de auditoria paralela por especialidade
  que já produziu `docs/referencia-photoprism/` na fase 14.
- Opções levadas ao dono: (a) revisar os 18 achados e aprovar a ordem de
  correção tier a tier, abrindo a fronteira (`fotoorganizer/**`,
  `webapp/src/**`) achado a achado como de costume; (b) priorizar só o
  Tier 1 (risco de dado + os dois achados de maior escala) para uma
  próxima fatia imediata; (c) tratar como backlog e seguir noutra frente
  primeiro.
- Recomendada: (b) — o achado 1 (VARIANTE) é o único desta lista que toca
  um invariante de segurança do projeto, não só qualidade de sugestão; os
  achados 2-4 do Tier 1 são os de maior volume/visibilidade e explicam a
  maior parte do "caos" relatado.
- Como reverter: nada a reverter — auditoria somente leitura, nenhum
  arquivo de código tocado. `docs/auditoria-pos-gate-fase5.md` e esta
  entrada são aditivos.
- Status: aguardando (classe B — 18 candidatos a decisão, dono escolhe
  ordem e escopo de correção).

## D-070 — Fatia #1 de D-069: UI de duplicata VARIANTE não avisa mais ao excluir RAW ou JPEG

- Fase: pós-gate — primeira fatia do achado 1 (Tier 1) de D-069, fronteira
  aberta a pedido explícito do dono para esta fatia especificamente
- Classe: A — execução de achado já registrado, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: D-069 achado 1 — `webapp/src/components/Duplicates.tsx` tratava
  um grupo VARIANTE (RAW+JPEG do mesmo clique) como duplicata comum
  ("marque a cópia a manter como principal"), quando `fotoorganizer/
  duplicates/detector.py` já documenta que "o dono quase sempre quer os
  dois". Investiguei o backend antes de mexer na UI: `escolher_principal`
  (`repositories/duplicates.py:149-165`) é indiferente ao nível — marcar
  uma como principal marca a outra `VERSAO` para QUALQUER nível, e
  `planner.py:78-86` exclui `VERSAO` do plano de cópia. `_herdar_metadados`
  já protege contra perda de metadado (o invariante 8 não é violado — nada
  é apagado), mas nada avisava que essa é uma decisão diferente para um
  par RAW+JPEG.
- Implementado, só em `Duplicates.tsx` (nenhuma mudança de backend — a
  detecção e a proteção de metadado já estavam corretas):
  1. Filtro novo "RAW + JPEG" na barra de níveis (`NIVEIS`).
  2. Texto de orientação distinto para `variante`, avisando que
     normalmente os dois devem ficar e que marcar uma como principal
     exclui a outra do plano.
  3. Bytes de `variante` fora do total "recuperáveis" do cabeçalho (mesmo
     tratamento que `sequencia` já tinha, e pela mesma razão: não é espaço
     a recuperar quando o normal é manter todos os membros).
  4. Botão por membro: label "Manter só esta" (em vez de "Manter esta") e
     `title` explicando a consequência exata ("a outra versão sai do plano
     de cópia — continua no disco de origem").
  5. Rótulo do grupo na lista lateral ganha a mesma cor de alerta
     (`text-atencao`) que `sequencia` já tinha — mesma classe de risco,
     mesmo sinal visual.
- Não fiz nesta fatia (fora de escopo, ver D-069 nota do achado): rodar
  nova detecção de duplicatas no catálogo real para reclassificar o par já
  confirmado como CONTEUDO por estar desatualizado (grupo id 4880,
  `IMG_3588.CR2`+`.jpg`) — é ação de escrita no catálogo de produção,
  fica para quando o dono clicar "Detectar" normalmente.
- Revisão com olhos frescos (subagente `agente-ux`, contexto isolado, só o
  diff) achou um bug real antes do commit: a primeira versão do texto de
  orientação (163 caracteres) estourava o `truncate` de uma linha do
  `<span>` que o carrega — testado ao vivo contra a página real, cortava
  em "...Ignorar gr" e nunca chegava ao aviso "marcar uma exclui a outra",
  que é o motivo da fatia existir. Corrigido: texto reduzido para 94
  caracteres (perto do precedente de `exato`, 89 caracteres, confirmado
  que cabe). A revisão também achou a inconsistência de cor (item 5 acima,
  incorporado).
- Achado extra durante a verificação na UI real, fora do escopo desta
  fatia, registrado em `docs/auditoria-pos-gate-fase5.md` §2.1 como achado
  19: `/api/duplicatas` devolve os 41.996 grupos do catálogo real numa
  resposta só (58 MB), sem paginação — a tela fica em branco por alguns
  segundos, sem loading state, ao abrir a aba Duplicatas.
- Verificação: `scripts/verificar.sh` verde (701 testes, 17/17 benchmark,
  115 testes de UI — 5 no arquivo desta fatia, 2 novos); provado no dev
  server (`foto-organizer-web-fase-5-audit`, porta 8405) contra o catálogo
  real — filtro "RAW + JPEG" isola corretamente (0 grupos hoje, como
  esperado — a última detecção rodou antes da feature existir), demais
  níveis (`Mesmo conteúdo` testado ao vivo) sem regressão.
- Como reverter: `git revert` do commit desta fatia — só toca
  `Duplicates.tsx`/`.test.tsx`, sem migração nem mudança de schema.
- Status: decidido (implementado e commitado). D-069 achado 1 fechado; os
  outros 17 achados de D-069 continuam aguardando.

- Status: decidido (implementado e commitado). D-069 achado 1 fechado; os
  outros 17 achados de D-069 continuam aguardando.

## D-071 — Fatia #2 de D-069: badge "Alta" em "Não classificadas" vira "Sem categoria"

- Fase: pós-gate — segunda fatia de D-069 (achado 2, Tier 1, o maior em
  extensão numérica da auditoria — 28.635 fotos, 29,6% do acervo), fronteira
  aberta a pedido explícito do dono para esta fatia especificamente
- Classe: A — execução de achado já registrado, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: D-069 achado 2 — sugestões com destino "Não classificadas/..."
  (nenhuma evidência de categoria/viagem/evento, só a data EXIF, score 0.95)
  mostravam badge de confiança "Alta", implicando confiança numa
  classificação que não existe.
- Decisão de desenho, antes de tocar em qualquer código: **não mexer no
  cálculo de `nivel`**. Lido `docs/CONFIANCA.md` e
  `fotoorganizer/classification/confidence.py`/`engine.py::_salvar_sugestao`
  — a regra "elo mais fraco entre os campos USADOS NO DESTINO" está correta
  por definição: para esses casos, o único campo usado É a data, e 0.95 é a
  confiança real da data. O bug não é o score, é a PRESENTAÇÃO — o badge
  "Alta" ao lado de "Não classificadas" implica classificação confiável, que
  simplesmente não existe. Mudar o score seria inventar uma régua nova, na
  contramão do que `docs/CONFIANCA.md` já resolveu; a fatia ficou só em UI.
- Achado relacionado, decidido deixar de fora (achado 4 de D-069, agregado
  contradiz evidência — ex. "Teatro": país/região Média, viagem/categoria
  Alta): investigado e é uma questão DIFERENTE — a exclusão de país/região do
  cálculo quando há viagem/evento é decisão de produto já documentada e
  deliberada (`engine.py`, comentário "UMA VIAGEM É UMA PASTA": a geocodificação
  cobre só uma fração do acervo, então deixar a hierarquia de lugar descer
  fragmentava a viagem em várias pastas por acidente de qual foto tinha GPS).
  Rediscutir essa régua é fatia própria, não bug de badge — fica de fora.
- Implementado:
  1. `webapp/src/sugestoes.ts` (novo): `DESTINO_NAO_CLASSIFICADO` (mesma
     string de `classification/templates.py`) e `naoClassificado(destino)`.
  2. `webapp/src/components/Confianca.tsx`: prop `naoClassificado` — quando
     true, troca os 3 segmentos "Alta/Média/Baixa" por um estado distinto
     "Sem categoria" (3 segmentos vazios — mesma gramática visual, quantidade
     não cor, D-017), com tooltip explicando que a data é confiável mas não
     há categoria.
  3. `webapp/src/components/Review.tsx`: os dois pontos que renderizavam
     `<Confianca nivel={...} />` (cabeçalho do grupo e linha da foto) passam
     `naoClassificado={naoClassificado(destino)}`.
  4. `webapp/src/components/Inspector.tsx`: mesmo ponto (painel de 3 colunas,
     seleção direta na grade) — achado pela revisão fresh-eyes, não pela
     auditoria original (ver abaixo).
  5. Evidência individual (`ev.nivel` no popover "por quê?" e no Inspetor)
     **não muda** — "data: ... Confiança Alta" continua correto: é a
     confiança daquela evidência específica, não do destino agregado.
- Revisão com olhos frescos achou um bug real antes do commit: o Inspetor
  (`Inspector.tsx:100`) renderizava o mesmo badge e tinha ficado de fora da
  primeira versão da fatia — é o caminho mais direto (selecionar foto na
  grade, sem abrir Revisão) e provavelmente o mais percorrido. Corrigido:
  `naoClassificado`/`DESTINO_NAO_CLASSIFICADO` extraídos para
  `webapp/src/sugestoes.ts` (antes viviam só em `Review.tsx`) e aplicados
  também no Inspetor, com teste dedicado.
- Risco identificado e aceito conscientemente: `naoClassificado()` casa a
  string `destino` contra a constante Python duplicada no TS. Hoje é seguro
  (string única, sem parametrização, batida contra `templates.py`/
  `engine.py`), mas nada no CI quebra se a constante do lado Python mudar —
  o sintoma seria o mesmo bug desta fatia voltando em silêncio. Não bloqueou
  a fatia (comentário rastreável ao arquivo/símbolo de origem já reduz o
  risco); um teste de contrato entre backend e frontend fica como debt
  registrado, não resolvido aqui.
- Verificação: `scripts/verificar.sh` verde (701 testes, 17/17 benchmark,
  118 testes de UI — 3 novos: 2 em `Review.test.tsx`, 1 em
  `Inspector.test.tsx`); provado no dev server (porta 8405) contra o
  catálogo real — a linha exata do achado ("20140719-144517 → Não
  classificadas/2014/jul.2014 · 1.784 fotos") mostra "Sem categoria"; casos
  genuinamente classificados ("Teatro → Viagens/2026 - Brasil") continuam
  "Alta" sem regressão; API `/api/midia/450691` confirmada com o mesmo
  contrato que o teste do Inspetor usa.
- Como reverter: `git revert` do commit desta fatia — só toca
  `Confianca.tsx`, `Review.tsx`, `Inspector.tsx`, `sugestoes.ts` (novo) e os
  testes; sem migração, sem mudança de schema, sem tocar em
  `classification/**`.
- Status: decidido (implementado e commitado). D-069 achado 2 fechado; 16
  achados de D-069 continuam aguardando (achado 4 explicitamente NÃO
  resolvido por esta fatia — ver acima).

## D-072 — Fatia #3 de D-069: aba Viagens de 50-120s+ para ~0,1s

- Fase: pós-gate — terceira fatia de D-069 (achado 3, Tier 1 — o mais fácil
  de reproduzir e provavelmente a causa direta do "caos" relatado pelo
  dono), fronteira aberta a pedido explícito do dono para esta fatia
- Classe: A — execução de achado já registrado, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: D-069 achado 3 — `/api/viagens`/`/api/eventos` levavam 50-120s+
  no catálogo real (medido antes de qualquer mudança), fazendo a aba
  Viagens mostrar "Nenhuma viagem ou evento ainda — gere as sugestões na
  aba Revisão" por até 2 minutos mesmo com 190 grupos existentes.
- Investigação antes de escrever código: `_agrupamentos` (server/app.py)
  fazia 1 `SELECT COUNT` por grupo (~190 consultas, N+1 clássico). Rodei
  `EXPLAIN QUERY PLAN` da query real contra o catálogo de produção
  (`sqlite3 -readonly`) e confirmei a causa dominante: `SCAN media_files`
  — `trip_id`/`event_id` não tinham índice, então cada consulta era
  varredura completa de 477 mil linhas. `docs/METODO_DE_TRABALHO.md`/
  princípio já documentado no próprio `catalog.py` ("índice sem consumidor
  é custo de escrita à toa") não tinha sido aplicado aqui porque o
  consumidor (`_agrupamentos`) só passou a existir depois — a fatia fecha
  essa lacuna, não inventa regra nova.
- Duas frentes, as duas dentro desta fatia (nenhuma cabia sozinha sem
  deixar o achado pela metade — resolver só o índice deixaria a UI
  vulnerável ao mesmo bug de "vazio enganoso" na próxima lentidão real;
  resolver só o loading state deixaria os 50-120s intactos):
  1. **Índice** — `Index("ix_media_files_trip_id", ...)` e
     `..._event_id` em `fotoorganizer/models/catalog.py` (mesmo padrão dos
     índices vizinhos, com o consumidor citado no comentário) +
     migração `0017` (`batch_alter_table`/`create_index`, downgrade
     simétrico, mesmo formato de `0007_tipo_confirmado_em_media_files.py`).
  2. **N+1 → agregado** — `_agrupamentos` trocou 1 `SELECT COUNT` por
     grupo por 1 `SELECT ... GROUP BY` para o recorte inteiro.
  3. **Loading state** — `webapp/src/components/Trips.tsx` ganhou
     `isPending` das duas queries; "Nenhuma viagem" só aparece depois que
     as duas resolvem, nunca mais durante o carregamento.
  Deixado de fora conscientemente: `_capa_disponivel` continua 1 query por
  grupo — mas agora indexada (ganho colateral do item 1), e o achado nunca
  apontou ela como a causa dominante. Reescrevê-la (ex.: window function
  para buscar candidatos de todos os grupos numa consulta só) seria
  otimização adicional sem medição pedindo por ela — fica de fora até
  medição mostrar que ainda é gargalo.
- Medido, catálogo real, antes e depois: `/api/viagens` e `/api/eventos`
  caíram de 50-120s+ para **~0,1s cada** (60 viagens, 130 eventos,
  contagens corretas). ~500-1200× mais rápido.
- Revisão com olhos frescos (subagente `agente-arquivos`, contexto
  isolado): nenhum bug achado. Confirmou que `coluna.is_not(None)` é
  estritamente equivalente à query antiga, que `contagens.get(grupo.id, 0)`
  não diverge do comportamento anterior, e que a migração segue o padrão
  exato de migrações anteriores. Achado não-bloqueante registrado: `Trips.tsx`
  não trata `isError` (se uma query falhar, mostra "vazio" em vez de erro)
  — gap pré-existente, fora do que este achado prometia corrigir.
- Verificação: `scripts/verificar.sh` verde (702 testes — 1 novo em
  `tests/test_server_api.py` cobrindo contagem correta por grupo com
  grupo cheio e vazio —, 17/17 benchmark, 120 testes de UI — 2 novos em
  `Trips.test.tsx` cobrindo o estado pendente e o vazio genuíno); migração
  aplicada e provada no dev server (porta 8405) contra o catálogo real —
  log confirma "Running upgrade 0016 -> 0017", `curl` timed antes/depois,
  aba Viagens carrega os 60 cards instantaneamente no navegador.
- Como reverter: `git revert` do commit desta fatia reverte o código; a
  migração tem `downgrade()` simétrico (`drop_index` nos dois índices) se
  precisar desfazer o schema também.
- Status: decidido (implementado e commitado). D-069 achado 3 fechado; 15
  achados de D-069 continuam aguardando.

## D-073 — Mês por extenso sem reconhecimento em grouping/datas.py — achado 5 de D-069

- Fase: pós-gate — resgate de WIP não commitado, encontrado num worktree
  órfão de PR #7 (auditoria pós-gate da fase 5, D-069) ao limpar
  worktrees; branch nova, fora do escopo do #7
- Classe: A — bug de correção determinística, sem decisão de produto em
  aberto
- Data: 2026-08-14
- Contexto: achado 5 de D-069 ("Categorização 'Eventos' por heurística
  fraca") mede 3.220 fotos (48 rótulos) cuja pasta é cronológica
  ("2009/novembro 30", ano na pasta-mãe) virando falso nome de evento —
  `_PADROES` de `separar_data()` não reconhecia "mês por extenso + dia"
  nem "dia de mês de ano" por extenso, então o segmento sobrava inteiro
  como se fosse nome, e a regra 6 da cascata (`grouping/classifier.py`,
  álbum + duração ≤2 dias) promovia isso a evento. Duas lacunas
  relacionadas, mesma raiz:
  - "29 de outubro de 2016" (dia primeiro, por extenso, com ano): 303
    fotos reais tinham destino tipo "Eventos/2016/29 de" — só a cauda
    "outubro de 2016" casava no padrão existente, "29 de" sobrava.
  - "novembro 30" (mês por extenso + dia, SEM ano — o ano mora na
    pasta-mãe, estrutura por dia dentro do ano): não vira `DataDaPasta`
    (falta o ano neste segmento; quem cruza com o ano da árvore é
    `data_no_caminho`), mas precisa ser reconhecido como data e não como
    nome, senão o segmento inteiro sobra igual.
- Implementado: dois padrões novos em `grouping/datas.py` — um regex em
  `_PADROES` para "dia de mês de ano" por extenso, e `_MES_DIA_SEM_ANO`
  (âncora `^...$` no segmento inteiro, de propósito: "Viagem novembro 30"
  é nome de verdade que só CONTÉM a palavra, não pode ser esvaziado) para
  "mês dia" sem ano, com a mesma validação de faixa do dia (1-31) que
  `_montar` já faz pros outros padrões — sem isto, "Julho 85" seria
  engolido como se fosse dia 85.
- Achado durante a revisão, corrigido antes do commit: a normalização NFC
  já resolvida por D-067 (mesmo módulo, sessão anterior) cobre "março"
  acentuado; os dois padrões novos são ortogonais a isso e não precisaram
  de mudança na normalização.
- Teste novo (`tests/test_datas_em_pastas.py`): datas por extenso com dia
  (parametrizado em `test_separa_nome_e_data`), `test_mes_dia_sem_ano_*`
  (esvazia nome, não esvazia nome que só contém a palavra, valida faixa
  do dia) e `test_marco_em_nfd_bate_igual_a_nfc` (NFC/NFD contra os novos
  padrões, não só os antigos). Cenário novo em
  `scripts/avaliar_agrupamento.py` para os dois formatos.
- Verificação: `scripts/verificar.sh` verde.
- Como reverter: reverter o commit desta fatia — isolado em
  `fotoorganizer/grouping/datas.py`, `tests/test_datas_em_pastas.py` e
  `scripts/avaliar_agrupamento.py`.
- Status: decidido e implementado. Achado 5 de D-069 parcialmente
  fechado (a fração 3.220/8.192 da regra 6 que era pasta cronológica); a
  fração por keyword fraca (regra 2, 3.300 fotos) e o resto de "álbum +
  duração" continuam abertos.

---

## D-074 — Herança de GPS confronta os dois lados em vez de só descartar o perdedor

- Fase: fatia independente (fora do roadmap de fase), a pedido do
  orquestrador de agentes.
- Classe: A
- Data: 2026-08-17
- Contexto: `herdar_gps` já buscava doadora dos DOIS lados (antes e
  depois) desde a versão que atravessa vizinhos da mesma origem
  (`procurar`, comentário sobre os 27.117 candidatos barrados), mas
  descartava o lado perdedor inteiro com `min(candidatos, key=...)` — pura
  extrapolação de âncora única. Quando a doadora mais próxima e a mais
  distante discordam geograficamente (uma indica São Paulo, a outra
  Campinas), a foto do meio está em algum lugar EM TRÂNSITO — afirmar a
  cidade da mais próxima como se a outra não existisse é a "sugestão
  errada com aparência de fundamentada" que D-025 já havia nomeado, agora
  aplicada ao caso de duas evidências, não uma.
- Medido: `scripts/calibrar_raio_incerteza.py --concordancia` (mesma
  técnica de D-032 — foto com GPS próprio tratada como herdeira
  hipotética), contra o backup pré-reset com GPS em 4 fontes
  (`catalog-antes-do-reset-20260816-013503.db`, 40.678 fotos com GPS,
  39.443 pares na janela de 12h). Dos 33.889 pares com doadora testável
  dos dois lados (números abaixo já são os corrigidos após a revisão por
  sub-agente ter achado um bug na PRÓPRIA medição — ver "Achado na
  revisão" adiante):
  - **83,8% concordam** (os círculos de incerteza de cada lado se
    sobrepõem) — cobertura real 97,5%, contra 94,2% do subconjunto de
    âncora única na mesma amostra.
  - **2,1% discordam** — e é aí que mora o problema que esta fatia
    resolve: cobertura de só **91,1%** no geral, e **50,9%** (quase cara
    ou coroa) na banda de 1–10 min — quer dizer, quase metade das vezes
    em que os dois lados discordam nessa banda, a coordenada da doadora
    mais próxima sozinha estaria FORA do próprio círculo de incerteza
    dela. É exatamente o padrão de doadora com coordenada errada que
    D-032 já havia flagueado (2019-04-19, Apple Fotos gravando "casa" a
    163 km do lugar real) — só que ali só um caso ficou registrado; a
    medição agora generaliza: quando a doadora mais próxima está errada,
    a mais distante costuma discordar dela, e esse desacordo é o sinal
    que sobrava sem uso.
  - **Testado e descartado**: apertar o raio de incerteza quando os dois
    lados concordam. `min(raio_incerteza(delta_perto),
    raio_incerteza(delta_longe))` já é, por construção,
    `raio_incerteza(delta)` de hoje — `delta` já é sempre o Δt do lado
    mais próximo (a escolha de doadora sempre prefere o mais próximo) e
    `raio_incerteza` é monótona em Δt. Não há aperto de graça aí.
    Testei também um fator de encolhimento extra sobre o raio dos
    concordantes: a cobertura **bruta** sobe suave e engana (dominada
    pelos 94,8% dos pares concordantes que estão a ≤1 min, onde o raio já
    está no piso e quase qualquer fator cobre); ponderando por banda —
    como a própria metodologia de D-032 exige, porque a herdeira real se
    concentra em 30 min–12 h, não em segundos — a banda de 1–10 min só
    alcança 90% de cobertura por volta de K≈0,7–1,0, ou seja, quase sem
    encolhimento livre. **Nenhum fator novo foi adicionado.**
- Escolhida — três regras, sem constante nova:
  1. Cada campo (cidade, região) é confrontado contra o lado oposto
     quando o Δt desse lado também cabe na janela daquele campo
     (D-025). Concordam se a distância entre as duas doadoras cabe na
     soma dos dois `raio_incerteza` — reusa a constante calibrada de
     D-032, não inventa outra.
  2. Concordam: o campo é mantido, com o MESMO fator de sempre (Δt do
     lado mais próximo, sem bônus de score) — só ganha uma marca
     (`Heranca.concordancia`) e uma frase extra na justificativa
     ("confirmada por outra foto do lado oposto no tempo").
  3. Discordam: o campo não é herdado por ninguém — nem pelo lado mais
     próximo. Se uma granularidade mais grossa (ex.: região quando só
     cidade discordou) não chegou a ser testada — porque o Δt do lado
     distante não cabe na janela dela — ela segue como sempre seguiu,
     sem teste, sem regressão.
  País fica de fora do teste inteiro, de propósito: `raio_incerteza` tem
  teto de 50 km (deslocamento de pessoa em 12h), e duas doadoras a
  300 km — claramente no mesmo país — falhariam um teste calibrado
  numa escala cem vezes menor. Resolver isso direito pede
  geocodificação, que `grouping/correlacao.py` deliberadamente não tem.
- Por quê: o ganho real e mensurável é reportar quando NÃO afirmar, não
  inflar confiança quando afirma. A cobertura do subconjunto discordante
  (91,1%, com um poço de 50,9% numa banda inteira) é o preço que o modelo
  anterior pagava em silêncio; descartar esse campo é assumir a incerteza
  real em vez de escondê-la atrás do "doador mais próximo venceu".
- Achado na revisão por sub-agente, antes do commit, na PRÓPRIA medição:
  `montar_pares_duplo` (script) parava na janela mais estreita (cidade,
  600 s) para decidir se um par era "testável", em vez da mais larga que
  o Δt escolhido sustenta (região, 7200 s) — igual `herdar_gps` faz
  campo a campo. Isso subcontava como "única" todo par em que só região
  era de fato confrontada em produção, justamente na banda mais citada
  como evidência (1–10 min). Corrigido antes do commit; os números acima
  já são os corrigidos (eram 78,2%/1,9%/91,5%/48,8%/31.577 antes do
  ajuste — a conclusão não mudou, só a precisão dela).
- Não modelado: hora de qualquer um dos três lados envolvidos (a foto que
  herda, o doador escolhido ou o doador do outro lado) vinda do mtime do
  arquivo derruba a confiabilidade do Δt usado no teste geométrico — o
  campo simplesmente não é testado nesse caso (fica como se só houvesse um
  lado), em vez de inventar um multiplicador de penalidade sem dado que o
  sustente (mesma postura de D-032 para `hora_incerta`). Achado na revisão
  por sub-agente antes do commit: a primeira versão só olhava a hora do
  lado DESCARTADO — deixava passar o caso em que a foto ou o doador
  ESCOLHIDO tinham hora incerta, produzindo uma justificativa que dizia
  "a proximidade pode ser coincidência" e "confirmada por outra foto" na
  mesma frase. Corrigido antes do commit.
- Como reverter: `_confrontar_com_outro_lado` em
  `fotoorganizer/grouping/correlacao.py` é a função isolada — remover a
  chamada em `herdar_gps` volta ao `min(candidatos, ...)` de sempre.
  `scripts/calibrar_raio_incerteza.py --concordancia` refaz a medição
  contra qualquer catálogo.
- Status: decidido por medição.

## D-075 — Escrita EXIF de localização (lat/long, cidade, país) autorizada em campo vazio, revoga parte do invariante 7

- Fase: discussão do milestone v2.0 (`/gsd:new-milestone`), antes do
  roadmap.
- Classe: B
- Data: 2026-08-18
- Contexto: o invariante 7 original ("MVP não implementa exclusão de fotos
  nem escrita de EXIF — futuro: sidecar XMP apenas") tratava sidecar XMP
  como o único caminho futuro para gravar localização corrigida/herdada.
  O dono pediu explicitamente, em conversa, escrita EXIF direta no
  arquivo original para as 3 evidências de localização que o motor de
  sugestões já produz (GPS lat/long herdado por D-074, cidade e país
  inferidos) — perguntado e confirmado via `AskUserQuestion`, não
  assumido.
- Decisão: EXIF direto é autorizado, mas com escopo estreito e o mesmo
  rigor de `operations/`, não uma porta aberta para qualquer campo:
  - Campos: só localização (GPS lat/long, cidade, país). Data, câmera,
    autor e qualquer outro campo EXIF seguem fora de escopo — precisam de
    nova decisão se algum dia entrarem.
  - Só escreve quando o campo já está vazio no original. Nunca sobrescreve
    valor EXIF existente, mesmo que a sugestão discorde dele — mesma
    postura não-destrutiva do invariante 3 (nunca sobrescrever no
    destino), agora aplicada à escrita em metadado do original.
  - Precisa do mesmo pipeline de `operations/`: plano dry-run revisado
    antes de aprovação explícita, hash antes/depois de cada escrita,
    audit log completo. Não é uma escrita direta sem revisão.
  - Refinamento de forma feito no roadmap da Fase 6 (2026-08-18): "hash
    antes/depois" aqui quer dizer fato de auditoria, não critério de
    aprovação — a escrita é mutação intencional, então o hash do arquivo
    inteiro sempre muda. O critério que aprova é diff completo de tags
    (as tags de localização esperadas mudaram e nenhuma outra tag mudou).
    O rigor exigido por este parágrafo continua o mesmo; só a métrica de
    verificação foi precisada.
  - Sidecar XMP deixa de ser o único caminho, mas continua disponível como
    alternativa não-destrutiva quando o dono preferir não tocar o
    original.
- Por quê: sidecar XMP exige que o software consumidor (Lightroom,
  Finder, iCloud, etc.) saiba ler XMP — parte do fluxo real do dono não
  lê. Gravar no EXIF do original torna o dado utilizável em qualquer
  ferramenta, ao custo de ser a primeira escrita em arquivo original do
  produto. O escopo estreito (só localização, só campo vazio) e o rigor
  de `operations/` existem justamente para não abrir precedente maior do
  que o pedido.
- Como reverter: remover a permissão do invariante 7, voltar ao texto
  anterior ("MVP não implementa... futuro: sidecar XMP apenas"); nenhum
  código de escrita EXIF ainda existe neste commit — a decisão precede a
  implementação.
- Status: decidido pelo dono, aguardando fase de implementação (roadmap
  v2.0).

## D-076 — Allowlist de formatos com suporte de escrita EXIF, medida contra o acervo real: nenhum formato aprovou

- Fase: 6 — escrita EXIF de localização, plano 06-04
- Classe: B
- Data: 2026-08-18
- Contexto: D-03/D-04 exigiam medição real, não suposição, de quais
  formatos aceitam a escrita de localização (GPS lat/long, cidade, país —
  D-075) sem sujar nenhuma tag fora de escopo e sem passar a emitir aviso
  novo do exiftool. `fotoorganizer/exif_write/formatos.py` (plano 06-02)
  tinha allowlist provisória (`{jpg, cr2, dng, tif}`, os formatos
  presentes no catálogo, "sem histórico de corrupção documentado" — uma
  suposição razoável, não uma medição). `scripts/testar_escrita_exif.py`
  (plano 06-04) roda o teste, contra cópias descartáveis (`shutil.copy2`
  em `tempfile.mkdtemp()`, nunca no original) de arquivos reais do
  `catalog.db` de produção (1.399 registros de acervo: 1.384 `.jpg`, 12
  `.cr2`, 2 `.dng`, 1 `.tif` — zero `.cr3`/`.heic`/`.heif`, confirma D-09).
  Usa o MESMO caminho de código de produção (`ExifToolWriter.escrever`,
  `verificacao.diferenca`/`campo_gravado`/`avisos`), nunca reimplementa a
  montagem de argumentos.
- Decisão: **nenhum formato aprovou.** `FORMATOS_APROVADOS` passa de
  `{jpg, jpeg, cr2, dng, tif, tiff}` (suposição) para `frozenset()`
  (medido). Tabela completa (amostras = todas as alcançáveis em disco por
  extensão; `.jpeg`/`.tiff` não amostrados separadamente — mesmo
  formato/codec de `.jpg`/`.tif`, mesmo resultado por construção):

  | extensão | amostras | veredito  | motivo medido |
  |----------|---------:|-----------|----------------|
  | .jpg     | 3        | reprovado | tags inesperadas: `IFD1:ThumbnailOffset`, `MPImage2:MPImageStart` |
  | .cr2     | 3        | reprovado | tags inesperadas: `IFD0:PreviewImageStart`, `IFD1:ThumbnailOffset`, `IFD2:StripOffsets`, `IFD3:StripOffsets` |
  | .dng     | 2        | reprovado | tags inesperadas: `IFD0:StripOffsets`, `SubIFD2:JpgFromRawStart`, `SubIFD3/4/5:TileOffsets`, `SubIFD:TileOffsets` |
  | .tif     | 1        | reprovado | tag inesperada `IPTC:EnvelopeRecordVersion` + avisos novos do exiftool (`IPTCDigest is not current`, `Missing required TIFF GPS tag 0x001b GPSProcessingMethod`) |
  | .cr3/.heic/.heif | 0 | sem_amostra | zero arquivos no acervo real hoje (D-09) — não testado, não reprovado |

  O critério aplicado é o de D-04 na íntegra, as três condições juntas:
  (a) `diferenca(antes, depois).inesperadas` vazio; (b) delta de avisos do
  exiftool vazio (`avisos_depois - avisos_antes`, não "zero depois"); (c)
  releitura estrutural (`largura`/`altura`/`data_capturada`/`model` via
  `PurePythonExtractor`) idêntica antes/depois. Uma amostra reprovada
  reprova a extensão inteira (conservador de propósito). Os quatro formatos
  reprovaram todos pela condição (a): a escrita insere um bloco IPTC/XMP
  novo num arquivo que já tinha outros blocos binários (miniatura
  embutida, segunda imagem MPF, dados RAW/tiles), e a inserção desloca os
  ponteiros de offset desses blocos existentes — efeito colateral
  estrutural do próprio exiftool ao reescrever o container, não perda ou
  troca do conteúdo apontado (verificado à parte: o byte a byte da
  miniatura embutida de um `.jpg` real é idêntico antes/depois do
  deslocamento de `IFD1:ThumbnailOffset` — `sha256` batendo). Mas esse
  deslocamento cai fora do escopo hoje reconhecido por
  `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` (plano 06-02), que só cobre o
  caso "arquivo nunca teve bloco IPTC/XMP/GPS nenhum" — não o caso "já
  tinha bloco binário X, e X só mudou de endereço". `.tif` reprova por um
  segundo motivo, independente do deslocamento de offset: uma tag IPTC de
  andaime ainda não catalogada (`EnvelopeRecordVersion`, distinta da já
  aprovada `ApplicationRecordVersion`) e dois avisos genuinamente novos do
  exiftool.

  Achado à parte, corrigido antes desta medição: `verificacao.avisos()`
  (plano 06-02) usava a saída `-j` do exiftool para coletar avisos, que
  **colapsa** tags `Warning`/`Error` repetidas em uma só (medido: um
  `.tif` real com 6 warnings devolvia 1 via `-j`, as 6 via texto plano) e
  incluía o resumo agregado `Validate` no conjunto — um `.jpg` cujos 3
  warnings sumiram após a escrita (o exiftool renormaliza o IFD ao
  reescrever) registrava `"Validate: OK"` como aviso NOVO, quando é
  melhora, não regressão. Corrigido para parsing de texto plano, com
  `Validate` fora do conjunto (não é warning nem error, é uma contagem
  derivada). 2 testes de regressão cobrem os dois casos.
- Por quê: os três critérios juntos, não um só — diff de tags sozinho não
  pega corrupção fora das tags (aviso novo do exiftool pode sinalizar
  problema estrutural que o diff não captura, como o caso do `.tif`);
  aviso sozinho não pega escrita fora de escopo silenciosa (verificado na
  pesquisa: `-GPSLatitude=999` é aceito sem aviso nenhum); releitura
  estrutural prova que o arquivo continua abrindo e lendo igual, não só
  que as tags batem. Reprovar por padrão quando qualquer um dos três falha
  é a postura conservadora que D-04 pede — o risco de aprovar cedo demais
  (mascarar corrupção real) é maior que o custo de reprovar cedo demais
  (usuário some tempo sem escrita direta, sidecar continua disponível).
- **Consequência de escopo, não decidida aqui:** com `FORMATOS_APROVADOS`
  vazio, todo arquivo de todo formato cai hoje no fallback de sidecar XMP
  (D-06/EXIF-05) — não há formato com escrita direta em EXIF disponível
  neste milestone. Os arquivos daquele formato aparecem no plano como
  "formato não suportado" com motivo visível e oferta de sidecar, nunca
  omitidos (D-05). Estender `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` para
  reconhecer deslocamento de offset de bloco binário pré-existente como
  andaime estrutural (o que, pela evidência do byte a byte idêntico da
  miniatura, é candidato plausível a reverter esse resultado para pelo
  menos `.jpg`/`.cr2`/`.dng`) é uma mudança na política de segurança de
  `verificacao.py` — não uma correção de bug — e fica como candidato a
  decisão futura do dono, não decidida por este plano.
- Como reverter: `scripts/testar_escrita_exif.py --json` refaz a medição
  contra qualquer catálogo; `fotoorganizer/exif_write/formatos.py`
  documenta a data e o resultado no próprio docstring do módulo.
- Status: decidido por medição.

## D-077 — Allowlist byte a byte estende D-076: jpg/cr2 passam a aprovar escrita EXIF direta

- Fase: 6 — escrita EXIF de localização, correção de meio-de-fase sobre o
  plano 06-04
- Classe: B
- Data: 2026-08-18
- Contexto: D-076 deixou explicitamente em aberto, como "candidato a
  decisão futura do dono, não decidida por este plano", estender
  `verificacao.TAGS_ESTRUTURAIS_ESPERADAS` para reconhecer deslocamento de
  offset de bloco binário pré-existente como andaime — candidato
  plausível pela evidência anexada a D-076 (byte a byte da miniatura
  embutida de um `.jpg` real idêntico antes/depois do deslocamento de
  `IFD1:ThumbnailOffset`). O dono foi consultado diretamente
  (`AskUserQuestion`) e escolheu explicitamente **"Estender allowlist com
  verificação byte a byte"**: aprovar jpg/cr2/dng se o conteúdo apontado
  pelas tags de offset for idêntico (sha256) antes/depois, só o endereço
  mudando — não estender a allowlist incondicional
  `TAGS_ESTRUTURAIS_ESPERADAS` (que aprovaria pelo NOME da tag, sem checar
  o conteúdo arquivo por arquivo, mascarando corrupção real igual a
  qualquer outra tag daquela lista).
- Decisão: `verificacao.py` ganha uma categoria nova e distinta de
  `TAGS_ESTRUTURAIS_ESPERADAS` —
  `reclassificar_deslocamentos_de_offset(diff, antes, depois,
  arquivo_antes, arquivo_depois)` rebaixa de `inesperadas` para
  `esperadas_condicionais` só a tag de offset/ponteiro (mapa fechado de
  seis sufixos: `ThumbnailOffset`, `PreviewImageStart`, `StripOffsets`,
  `TileOffsets`, `JpgFromRawStart`, `MPImageStart` — as mesmas que
  apareceram como "inesperada" nos três formatos com amostra em D-076)
  cujo par offset+tamanho aponta para um intervalo de bytes sha256-idêntico
  entre o arquivo antes da escrita (o backup `<arquivo>_original` que o
  writer já deixa, por nunca usar `-overwrite_original`) e o arquivo
  depois. Toda borda que impede a prova — tag fora do mapa, tag de
  tamanho irmã ausente, tamanho que mudou junto, contagem de valores que
  não bate, valor não-numérico, leitura que falha — mantém a tag em
  `inesperadas`, fail-safe, nunca promove por omissão.

  `scripts/testar_escrita_exif.py` chama a reclassificação antes de
  aplicar o critério de D-04 (as três condições continuam as mesmas: diff
  sem inesperadas, delta de avisos vazio, releitura estrutural idêntica —
  só o que conta como "inesperada" mudou). Remedição contra o
  `catalog.db` de produção real (cópias descartáveis, nunca o original):

  | extensão | amostras | veredito  | motivo medido |
  |----------|---------:|-----------|----------------|
  | .jpg     | 20/20    | **aprovado** | todo deslocamento medido (`IFD1:ThumbnailOffset`, `MPImage2:MPImageStart`) prova relocação byte a byte — sha256 idêntico |
  | .cr2     | 12/12 (todas as alcançáveis) | **aprovado** | todo deslocamento medido (`IFD0:PreviewImageStart`, `IFD1:ThumbnailOffset`, `IFD2:StripOffsets`, `IFD3:StripOffsets`) prova relocação byte a byte |
  | .dng     | 2/2      | reprovado (inalterado) | `SubIFD:TileOffsets`/`SubIFD3:TileOffsets` têm tiles demais — o exiftool devolve `"(Binary data N bytes, use -b option to extract)"` no dump em vez de lista de inteiros, a prova byte a byte não consegue parsear o offset, fica fail-safe |
  | .tif     | 1/1      | reprovado (inalterado) | motivo de D-076 não é offset — tag `IPTC:EnvelopeRecordVersion` nova + 2 avisos novos do exiftool, fora do escopo desta correção |

  `FORMATOS_APROVADOS` passa de `frozenset()` (D-076) para `{".jpg",
  ".jpeg", ".cr2"}`. Todo arquivo `.dng`/`.tif`/`.cr3`/`.heic`/`.heif`
  continua caindo no fallback de sidecar XMP (D-06/EXIF-05).
- Por quê: verificação byte a byte é a única forma de aprovar relocação
  sem abrir a mesma porta de mascaramento que `TAGS_ESTRUTURAIS_ESPERADAS`
  fecha por desenho (EXIF-04) — aprovar pelo NOME da tag confiaria que
  TODO deslocamento futuro daquela tag, em qualquer arquivo, é sempre
  inofensivo; aprovar pelo CONTEÚDO confia só no que foi medido, arquivo
  por arquivo, a cada escrita. O caso do `.dng` prova o valor da postura
  fail-safe: em vez de estender a lógica para tentar extrair um offset de
  dentro do texto `"(Binary data...)"` (o que seria ler o tamanho da
  descrição, não o offset real — um bug esperando para acontecer), a
  tag simplesmente fica `inesperada` e o formato continua reprovado. É
  mais seguro reprovar um formato que provavelmente é inofensivo do que
  arriscar aprovar um que não é.
- Superseded/relacionado: **supera D-076 em parte** — a tabela de
  veredito de jpg/cr2 muda de "reprovado" para "aprovado"; o achado de
  D-076 sobre `.tif` (motivo distinto, não-offset) **permanece válido e
  inalterado**, não superado por esta decisão. O achado de D-076 sobre o
  byte a byte idêntico da miniatura do `.jpg` é a evidência empírica que
  motivou esta decisão — generalizada aqui para produção, não mais só
  uma observação anexa à medição.
- Como reverter: `scripts/testar_escrita_exif.py --json` refaz a medição
  contra qualquer catálogo, já usando a reclassificação; reverter para o
  comportamento de D-076 exige remover a chamada a
  `reclassificar_deslocamentos_de_offset` do script (a função em si pode
  ficar sem uso, não precisa ser apagada) e restaurar
  `FORMATOS_APROVADOS = frozenset()`.
- Status: decidido pelo dono, medido.
