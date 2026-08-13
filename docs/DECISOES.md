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
