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

## D-078 — `IPTC:EnvelopeRecordVersion` entra no andaime incondicional; achado à parte de digest IPTC desatualizado fica registrado, não corrigido

- Fase: 6 — escrita EXIF de localização, correção de meio-de-fase sobre o
  checkpoint humano do plano 06-09
- Classe: B
- Data: 2026-08-18
- Contexto: no checkpoint 06-09, o dono rodou uma escrita real contra um
  JPEG real de produção do Canon EOS R6m2 (cópia própria, não o original —
  `~/Desktop/teste-exif/ACM_7122.JPG`, copiada de
  `/Users/acamerini/Pictures/2026/Serena 15 Anos/ACM_7122.JPG`). A escrita
  teve sucesso no nível do exiftool (City="Rio de Janeiro"/Country="Brasil"
  gravados corretamente, confirmado por `exiftool -City -Country` no
  arquivo pós-escrita), mas `verificacao.diferenca()` sinalizou
  `IPTC:EnvelopeRecordVersion` como tag inesperada e reprovou a
  verificação — fail-safe preservou o backup `_original`, item marcou
  `falha`, nada corrompeu, mas a escrita ficou presa fora do fluxo normal.
  A tag já tinha aparecido, sem catalogação, em D-076 (achado do `.tif`:
  "tag inesperada `IPTC:EnvelopeRecordVersion` + avisos novos do
  exiftool") — não perseguida na época porque `.tif` reprovava por um
  segundo motivo independente também, e a remedição de D-077 (jpg/cr2
  20/20 e 12/12) não incluiu nenhuma amostra que exercitasse esta tag
  especificamente.
- Decisão: `IPTC:EnvelopeRecordVersion` (marcador de versão do registro de
  ENVELOPE IPTC, distinto de `IPTC:ApplicationRecordVersion` — marcador de
  versão do registro de APLICAÇÃO, já allowlisted) entra em
  `verificacao.TAGS_ESTRUTURAIS_ESPERADAS`, mesma justificativa das quatro
  entradas originais (D-02) e das três de sidecar (plano 06-05): tag de
  versão obrigatória, escrita sem condição ao criar um bloco IPTC novo,
  não é dado de localização — sempre idêntica para todo arquivo que este
  módulo escreve pela primeira vez. Não é extensão da allowlist byte a
  byte de D-077 (essa cobre deslocamento de offset de bloco binário
  pré-existente, categoria distinta) — é o mesmo tipo de andaime
  incondicional que as outras oito entradas de `TAGS_ESTRUTURAIS_ESPERADAS`
  já cobrem.

  Regressão coberta por dois testes novos em
  `tests/test_exif_write_writer.py`: classificação isolada da tag em
  `estruturais`, e uma escrita completa (GPS+cidade+país) que produz todo
  o andaime obrigatório junto — inclusive esta tag — confirmando
  `diff.inesperadas` vazio e os três campos gravados.

  Remedição de `.jpg` contra o `catalog.db` de produção real (mesmo
  método de D-076/D-077 — cópias descartáveis via `shutil.copy2` em
  `tempfile.mkdtemp()`, nunca o original): 20/20 amostras aprovadas,
  `FORMATOS_APROVADOS` continua `{".jpg", ".jpeg", ".cr2"}` (D-077),
  nenhuma mudança — esta correção fecha uma lacuna de reconhecimento de
  tag, não abre nem fecha suporte de formato novo.
- **Achado à parte, registrado e explicitamente NÃO corrigido aqui:**
  testar a mesma extensão da escrita diretamente contra o arquivo original
  de produção citado no achado
  (`/Users/acamerini/Pictures/2026/Serena 15 Anos/ACM_7122.JPG`, via cópia
  descartável, nunca o original nem a cópia de teste do dono no Desktop)
  confirma que a tag `EnvelopeRecordVersion` deixa de reprovar a
  verificação — mas revela uma SEGUNDA falha, estruturalmente diferente e
  não coberta por esta correção: o arquivo já chega com um bloco IPTC
  pré-existente (gravado por outra ferramenta antes deste app, ex.
  Lightroom — `IPTC:ApplicationRecordVersion`/`Keywords`/`By-line` já
  presentes antes da escrita), e a escrita do exiftool nesse caso produz o
  aviso NOVO `"IPTCDigest is not current. XMP may be out of sync"` — o
  mesmo aviso que já aparecia, também não perseguido, no achado do `.tif`
  em D-076. Nenhuma das 20 amostras genéricas usadas na remedição acima
  tinha bloco IPTC pré-existente (confirmado por inspeção individual),
  então D-076/D-077 nunca mediram este caminho. Não existe hoje mecanismo
  equivalente a `TAGS_ESTRUTURAIS_ESPERADAS` para avisos — reconhecer este
  aviso como andaime inofensivo exigiria um allowlist de avisos novo,
  mudança de política de segurança (mesma classe de decisão que D-076
  deixou em aberto para offsets, resolvida só depois por D-077 com
  aprovação explícita do dono). Fica fora do escopo desta correção
  (`TAGS_ESTRUTURAIS_ESPERADAS` é só para tags, não avisos) — registrado
  como blocker em `STATE.md`, não decidido aqui.
- Por quê: mesmo raciocínio de D-02/D-077 — reconhecer o NOME de uma tag
  de andaime incondicional (sempre idêntica, nunca dado) é seguro; inventar
  um mecanismo de allowlist para avisos, sem medição própria contra o
  acervo real e sem aprovação do dono, seria abrir a mesma porta de
  mascaramento que EXIF-04 fecha por desenho — por isso o achado do
  digest fica registrado, não resolvido, nesta correção.
- Superseded/relacionado: estende D-076 (cataloga a tag que D-076 já tinha
  visto, sem perseguir) e D-077 (usa a mesma allowlist incondicional,
  categoria distinta da allowlist byte a byte). Não supera nem contradiz
  nenhuma das duas — a tabela de D-077 sobre `.tif` continua válida:
  `.tif` ainda reprova, agora só pela causa do aviso (que já estava lá,
  documentada, e não muda com esta correção).
- Como reverter: remover `IPTC:EnvelopeRecordVersion` de
  `TAGS_ESTRUTURAIS_ESPERADAS`; os dois testes de regressão passam a
  falhar, sinalizando a reversão.
- Status: decidido — achado da tag corrigido e medido; achado do digest
  registrado como blocker pendente, aguardando decisão futura do dono.

## D-079 — Prévia de custo do GenAI de pasta: estimativa local antes de confirmar, contagem exata só depois (híbrida)

- Fase: 7 — classificação de pasta por GenAI, `checkpoint:decision`
  bloqueante da Task 1 do plano 07-03, respondido pelo dono via
  `AskUserQuestion` antes da execução da tarefa.
- Classe: B
- Data: 2026-08-18
- Contexto: `07-RESEARCH.md` § Pattern 2 recomendava `client.messages
  .count_tokens` para a prévia de custo do passo 2 do assistente (grátis,
  exato, já no SDK pinado), e `07-UI-SPEC.md` chegou a escrever a tela em
  cima disso (`"Entrada (exata): 3.420 tokens"`). O que a pesquisa não
  considerou: `count_tokens` é uma chamada HTTP para `api.anthropic.com`
  que transmite o payload inteiro (system, schema, lista de pastas) só
  para contar — não custa dinheiro, mas os dados já saíram da máquina.
  Isso colide de frente com o critério de sucesso 2 da Fase 7 no
  `ROADMAP.md` ("nada é enviado antes de ele confirmar") e com o
  invariante 4 do `CLAUDE.md` (indicação prévia do que sai, antes de
  sair). Três opções foram postas ao dono: (a) contagem exata antes de
  confirmar, com aviso explícito de que isso já envia o texto; (b)
  estimativa local, nada sai antes do confirmar, número de entrada fica
  aproximado; (c) híbrida — estimativa local antes, contagem exata depois
  de confirmar, mostrada no resumo pós-execução.
- Decisão: opção (c), híbrida. Nada sai da máquina antes do "Confirmar e
  classificar" (critério 2 do ROADMAP intacto, sem reinterpretação). A
  prévia do passo 2 mostra `Entrada (estimada)` — contagem local
  deliberadamente conservadora (nunca abaixo do real). Depois que o dono
  confirma, `contar_exato()` roda imediatamente antes de
  `messages.create` — a mesma chamada de rede que já ia acontecer de
  qualquer forma, agora só uma etapa adiantada dentro da mesma
  transmissão consentida — e o passo 5 (resumo pós-execução) mostra o
  custo real com a contagem exata de entrada.
- Por quê: a opção (a) foi descartada por violar o critério 2 na letra —
  o dado sairia antes do botão de confirmação, mesmo que o payload fosse
  idêntico ao que seria enviado de qualquer forma; reinterpretar esse
  critério não é decisão de implementação, é decisão do dono, e ele
  preferiu não abrir essa exceção. A opção (b) pura foi descartada porque
  descartava também o número exato que a opção (c) consegue entregar
  sem violar o critério — bastava adiar a contagem exata para
  depois da confirmação, não abrir mão dela. A opção (c) preserva o
  critério 2 e entrega o número exato no mesmo fluxo, só que depois em
  vez de antes — o dono acaba vendo os dois números (estimado e real) em
  vez de só um, o que é estritamente mais informação, não menos.
- Impacto em código (executado nesta mesma sessão, plano 07-03):
  `custo_genai.py::estimar()` sempre devolve `entrada_exata=False`
  (estimativa local, fator conservador documentado no código);
  `custo_genai.py::contar_exato(client, corpo)` existe separado,
  chamado só depois da confirmação (fora do escopo deste plano — o
  ponto de chamada real fica em 07-04, o endpoint que orquestra a
  sessão). `07-UI-SPEC.md` § Copywriting Contract atualizado no mesmo
  commit desta decisão: rótulo do passo 2 vira `"Entrada (estimada):"`
  (era `"Entrada (exata):"`), nota de honestidade do passo 2 reescrita
  para declarar que nada foi enviado ainda, e o passo 5 (Concluído) ganha
  uma linha nova de custo real com a contagem exata pós-confirmação.
- Como reverter: para voltar à opção (a), trocar `estimar()` para receber
  o cliente e chamar `contar_exato()` direto (com `entrada_exata=True`) e
  reverter as três linhas do Copywriting Contract afetadas de volta a
  `"Entrada (exata)"`; nenhuma chamada de rede nova foi introduzida por
  esta decisão que precise ser desfeita além disso. Para voltar à opção
  (b) pura, remover a chamada a `contar_exato()` do ponto de integração
  em 07-04 e a linha de custo real do passo 5.
- Status: decidido pelo dono (não pelo planejador nem pelo executor).

## D-080 — Opt-in de classificação de pasta por GenAI mora em `application_settings`, não em `PrivacySettings`/TOML

- Fase: 7 — classificação de pasta por GenAI, Task 1 do plano 07-04.
- Classe: B
- Data: 2026-08-18
- Contexto: `07-RESEARCH.md` propôs `PrivacySettings.classificacao_pasta_genai`
  no `config.toml`, no mesmo molde de `servicos_externos`. Mas
  `07-UI-SPEC.md` (posterior e aprovado) exige que o passo 0 do assistente
  LIGUE o flag por um checkbox na própria tela, com um link "Desligar"
  sempre disponível depois — ou seja, a UI precisa GRAVAR essa preferência,
  não só lê-la. `PrivacySettings` é uma dataclass `frozen` carregada do
  TOML na subida do processo (`fotoorganizer/config/settings.py`), e o
  servidor não escreve de volta no arquivo TOML em lugar nenhum do código
  — não existe hoje (nem é desejável abrir) um caminho de escrita de
  config.toml pelo processo do app. Colocar o flag lá criaria uma chave que
  a UI mostra mas não consegue gravar.
- Decisão: o opt-in PRÓPRIO do recurso (`classificacao_pasta_genai`) mora
  em `application_settings`, via `SettingsRepository` — o mesmo mecanismo
  que este projeto já usa para "o usuário decidiu algo pela interface"
  (hoje só o template de destino; ver a docstring do próprio módulo).
  `servicos_externos` (a chave MESTRA, invariante 4) continua só no TOML,
  fora do alcance da UI — nenhum endpoint deste plano escreve
  `PrivacySettings`. O gate do recurso é a CONJUNÇÃO dos dois:
  `settings.privacidade.servicos_externos AND
  SettingsRepository.genai_pasta_habilitado()`.
- Por quê: reaproveitar `application_settings` evita inventar um segundo
  mecanismo de "preferência gravável pela UI" quando um já existe e já é
  testado (par `obter_template`/`salvar_template`); manter `servicos_externos`
  fora do TOML preservaria a UI mostrando uma chave que ela não pode
  alterar de fato, quebrando a expectativa de que todo controle visível na
  tela funciona.
- Impacto em código (executado nesta mesma sessão, plano 07-04):
  `fotoorganizer/repositories/settings.py` ganha `CHAVE_GENAI_PASTA` e o
  par `genai_pasta_habilitado()`/`definir_genai_pasta()`, no molde exato de
  `obter_template()`/`salvar_template()`. `fotoorganizer/config/settings.py`
  não ganha nenhum campo novo (`grep -c "classificacao_pasta_genai"` = 0
  nesse arquivo). `fotoorganizer/server/genai_pasta.py::SessaoDeClassificacaoDePasta.liberado()`
  é a conjunção dos dois flags — copiar o gate de UM flag só de
  `jobs.py::_advisor` (que olha só `servicos_externos`) seria a regressão
  nomeada em `07-RESEARCH.md` Pitfall 4, porque esse recurso tem opt-in
  PRÓPRIO, separado do consentimento já dado ao Advisor de cluster.
- Como reverter: mover a chave para `PrivacySettings` exigiria primeiro
  abrir um caminho de escrita de `config.toml` pelo processo do app (mudança
  maior, não coberta por este plano) — não é uma reversão trivial de uma
  linha.
- Status: decidido pelo executor durante a Task 1 do plano 07-04, conforme
  a instrução explícita do `<action>` do plano (registrar a justificativa
  já dada pelo planejador, não uma decisão nova em aberto).

## D-081 — Score de `llm_pasta` medido contra o acervo real: 0.55, preliminar

- Fase: 7 — classificação de pasta por GenAI, Task 2/3 do plano 07-09.
- Classe: B
- Data: 2026-08-18
- Contexto: `SCORES_REFERENCIA["llm_pasta"]` nasceu em 07-05 com o valor
  `0.55` marcado `PROVISÓRIO` — escolhido por analogia ao advisor de
  cluster (`llm`), sem medição própria. A convenção deste projeto (D-074,
  D-059/D-060) é medir contra o acervo real antes de travar um score; um
  número por analogia aqui viraria verdade de base para o índice de saúde
  da Fase 10 sem nunca ter sido checado — a mesma classe de bug que já
  vazou em D-071. Este plano não podia escolher por analogia porque
  `llm_pasta` mede uma pergunta diferente da do advisor de cluster (lê o
  NOME da pasta, uma vez por sessão, não metadado de mídia individual) —
  são origens distintas por design (comentário já existente em
  `confidence.py`), então a taxa de acerto de uma não informa a da outra.
- Método: `scripts/medir_score_llm_pasta.py` (07-09 Task 1) monta a
  amostra a partir das pastas onde a cascata DETERMINÍSTICA já resolveu
  categoria e/ou cidade/país (origem `pasta`, `gps`, `geocoding_offline`
  ou `exif`) — a verdade de referência é o próprio catálogo, exigindo
  unanimidade entre origens determinísticas antes de aceitar um valor
  como verdade (duas pastas com evidência conflitante, ver
  `deferred-items.md` item 1, foram corretamente excluídas). O modelo
  recebe o MESMO `PastaPayload` e o mesmo schema que a produção usaria
  (`location_advisor.py`), com o campo em medição ausente — nunca vê a
  resposta. Cada item cai em um de três baldes: acertou, recusou
  (`null`, comportamento desejado de D-06 quando não dá para saber) ou
  errou (afirmou valor diferente da verdade). O dono rodou o script no
  próprio terminal, com a própria chave (`ANTHROPIC_API_KEY`) — esta
  sessão de desenvolvimento nunca manuseou a credencial, mesmo protocolo
  de D-048/D-049/D-059.
- Resultado numérico (`--limite 60`, 4 pastas na amostra):
  ```
  CATEGORIA
    categoria: 2 itens — acertou 2 (100.0%)  recusou 0 (0.0%)  errou 0 (0.0%)

  CIDADE/PAÍS
    cidade: 2 itens — acertou 0 (0.0%)  recusou 2 (100.0%)  errou 0 (0.0%)
    país:   2 itens — acertou 0 (0.0%)  recusou 2 (100.0%)  errou 0 (0.0%)
  ```
  Zero erros observados nos dois campos — é o sinal que mais importa: o
  padrão "afirma sem base" que D-049 mediu e que motivou trocar de
  modelo (Haiku → Sonnet) não apareceu. `categoria` acertou 2/2.
  `cidade`/`país` recusaram 2/2 (retornaram `null` as duas vezes) — é o
  comportamento seguro de D-06 (nunca inventar quando incerto), não
  evidência de falha, mas também não é sinal positivo de acerto: o
  modelo nunca se comprometeu com um valor nesse campo na amostra.
- Alternativas consideradas: (a) manter `0.55` por analogia ao advisor
  de cluster, sem medir — descartado porque é exatamente o que este
  plano existe para evitar (T-07-09-01); (b) subir para `0.60`
  (igualando a `pasta`, parse determinístico) — descartado porque
  `pasta` é fato lido de um segmento de caminho, `llm_pasta` é
  julgamento sobre string ambígua; igualar os dois esconderia que um é
  determinístico e o outro é inferência, mesmo com zero erros
  observados; (c) descer para abaixo de `0.50` (nasce BAIXA na
  cascata) — descartado porque a taxa de erro (o sinal que mais importa
  aqui) ficou em zero; um número que penaliza mais que `vizinhanca`/
  `curadoria`/`album_externo` (0.55, todos com vínculo mais fraco de
  contemporaneidade) não teria medição que o sustente.
- Escolhida: manter `0.55` — mesmo valor do antigo `PROVISÓRIO`, mas
  agora com medição por trás em vez de analogia. Iguala ao advisor de
  cluster (`llm`) apesar da entrada mais esparsa (uma vez por sessão de
  pasta, não por mídia individual) porque o que a medição prova é
  ausência de alucinação nos dois campos, que é a mesma barra que
  justificou o 0.55 do advisor.
- Limitação de escala: a base de medição da Fase 7 tem só ~1.400
  arquivos e 2 fontes cadastradas em `catalog.db` de produção
  (`~/Pictures/2026` e `/Volumes/Externo/Fotos/Do Peru ao Chile`) — as
  duas fontes que formam o grosso do acervo real (Apple Fotos só-iCloud,
  ~44.661 registros; Lightroom em volume desmontado, ~45.397 registros)
  não estão cadastradas (ARCH-01, deferido, `.planning/STATE.md` §
  Blockers/Concerns). A amostra desta medição — 4 pastas, 2 itens por
  campo — é preliminar mesmo para o padrão já pequeno da fase; não tem o
  porte de D-059/D-060 (104 clusters) nem de D-074 (40.678 fotos). O
  valor é revisitável, e deve ser revisto, quando ARCH-01 reconectar os
  volumes maiores.
- Como reverter: `SCORES_REFERENCIA["llm_pasta"]` em
  `fotoorganizer/classification/confidence.py` é uma linha; o comentário
  ao lado documenta a medição para quem for revisar. Reexecutar
  `scripts/medir_score_llm_pasta.py --limite N` (N maior, quando ARCH-01
  ampliar a base) refaz a medição sem tocar em código de produção — o
  script é só leitura sobre o catálogo.
- Status: decidido pelo dono, via `AskUserQuestion` apresentado pelo
  orquestrador com o relatório real da medição e a tabela de scores já
  travados como baliza.

## D-082 — País no nome da pasta tolera hífen, ano e conector; a tolerância só vale ao lado de um país exato

- Fase: localização estimada, fatia 1 (2026-09-20), primeira das
  funcionalidades priorizadas pelo dono após o mapa de reconstrução
  (`docs/reconstrucao/`).
- Classe: A — regra de classificação medida antes e depois, sem mexer em
  limiar; oito cenários novos no benchmark (quatro positivos, quatro
  guardas): 19 → 27.
- Contexto: 40.369 fotos de acervo (73,3%) não têm lugar nenhum — nem GPS
  próprio nem herança. 26.505 delas estão a mais de 30 dias de qualquer
  doadora com GPS: herança temporal nunca as alcança. O que elas têm é o
  nome da pasta — e o reconhecedor de país (`identificar_paises`/
  `identificar_pais`) exigia o segmento inteiro igual ao nome do país ou
  uma lista em que TODA parte é país. "Peru-Bolivia-Chile" (5.516 fotos),
  "Italia e Franca 2013" (1.649), "Chile e Atacama Abr.18" (880 sem
  lugar), "Portugal e Espanha Carnaval Fev.16" / "Carnaval 2016 -
  Portugal e Espanha" (754 + 754) e "Do Peru ao Chile" não produziam país
  nenhum: no catálogo inteiro não existia uma evidência de `pais` com
  origem `pasta`.
- Medição antes (catálogo real, somente leitura): reconhecedor tolerante
  alcança 8.690 fotos sem lugar em cinco pastas multi-país (candidatos na
  justificativa da viagem, nenhum escolhido como país da foto) e 880 em
  "Chile e Atacama Abr.18". A primeira versão da regra, revisada com
  olhos frescos antes do commit, errava em "Estádio Nilton Santos -
  Guadalupe, RJ" (bairro homônimo de país), "Serra - ES" (→ Serra Leoa,
  por prefixo), "Cabo" (→ Cabo Verde), "Georgia 15 Anos" (aniversário →
  viagem) e "Israel e Maria Casamento" (sobra "Maria Casamento" virava
  cidade). As guardas abaixo vêm daí.
- Medição depois (hierarquia velha × nova sobre as 555 pastas / 102.251
  registros do catálogo): **1.927 fotos de acervo ganham país** — "Chile
  e Atacama Abr.18" (1.515, das quais 880 não tinham lugar nenhum) e
  "Chile Jun.15" (412) —, **0 trocam, 0 perdem**, 0 mudanças de cidade.
  As 8.690 multi-país mudam no classificador (viagem nomeada pela lista),
  não na hierarquia. Contra as pastas com país geocodificado do GPS
  próprio: 3 de 3 concordantes.
- Decisão:
  1. Uma parte só conta como país se for país EXATO depois de tirar data
     e conector ("Franca 2013", "Do Peru", "Guiné-Bissau"). Abreviação
     ("Thai") e país seguido de palavra ("Espanha Carnaval") só valem
     quando outra parte do mesmo segmento já é país exato.
  2. Dois ou mais países no mesmo segmento é sinal forte — valem onde
     estiverem (partes separadas por `, & + / " e " " ao " " - "`;
     hífen colado separa só se todos os pedaços forem país). Palavra de
     festa não desfaz a lista ("Portugal e Espanha - Natal 2015").
  3. Sigla de estado brasileiro em qualquer parte desqualifica o
     segmento inteiro, lista ou não ("Guadalupe - RJ", "Brasil e
     Portugal - RJ"): é endereço, não roteiro.
  4. Um país só vale se for a PRIMEIRA parte do segmento e não houver
     palavra de evento no segmento ("Georgia 15 Anos", "Israel e Maria
     Casamento"). Vocabulário de evento e de pasta técnica passa a morar
     em `grouping/segmentos.py`, módulo folha, para `geolocation/` e
     `grouping/eventos.py` lerem a mesma lista sem ciclo.
  5. Pasta multi-país não escolhe `pais`; a varredura continua para
     baixo (".../Peru-Bolivia-Chile/Peru/Cusco" → Peru/Cusco). A viagem é
     nomeada com as palavras do dono e a justificativa lista os países
     (regra 3 do classificador, já existente). O ramo de UM país continua
     rotulando pelo país ("Chile"), como já fazia para o segmento exato —
     o ano do template separa "2015 - Chile" de "2018 - Chile"; nomear
     com as palavras do dono aqui carregaria "Abr.18"/"Jun.15", que
     `separar_data` não reconhece.
  6. A sobra do segmento do país ("Atacama") NÃO vira cidade nesta fatia:
     sem o dataset offline confirmar que é lugar, seria inventar
     localização. Subpasta técnica abaixo do país ("[Developed]", "2019")
     também não é cidade — antes era.
- Alternativas rejeitadas: aceitar país em qualquer posição (traz o
  bairro Guadalupe); prefixo solto (196 palavras de 4 letras viram
  país); exigir lista completa como antes (perde 8.690 fotos); listar os
  países como valor de `pais` (duplicaria o segmento no destino).
- Limitações conhecidas, todas para a fatia 2 (dataset de cidades):
  cidade homônima de país na primeira parte ("Granada e Sevilha 2018" →
  Granada; "Franca" sozinha → França, risco que já existia); país + nome
  de pessoa sem palavra de festa ("Israel e Maria 2019" → viagem Israel,
  onde antes era evento — zero ocorrências no acervo hoje); prefixo ao
  lado de país exato aceita qualquer palavra de 4 letras que seja prefixo
  único ("Espanha e Fran" → França); país único com palavra de festa fica
  sem país ("Chile - Reveillon 2018"), como antes.
- Como reverter: `git revert` do commit desta fatia; os cenários novos
  do benchmark passam a falhar, que é o comportamento desejado de uma
  reversão consciente.
- Status: decidido pelo dono (fatia 1 de localização estimada escolhida
  entre quatro opções medidas), implementado e commitado nesta fatia
  (`feat: país no nome da pasta tolera hífen, ano e conector`).

## D-083 — Cidade no nome da pasta vale quando o dataset offline a confirma; vira lugar (não coordenada herdada) com raio de 15 km

- Fase: localização estimada, fatia 2 (2026-09-20), continuação de D-082.
- Classe: A — regra medida antes e depois no acervo real; nenhum dado sai
  da máquina (o dataset é o mesmo GeoNames do geocoding reverso, já no
  `.venv`).
- Contexto: depois de D-082, 40.369 fotos de acervo seguiam sem lugar; 895
  delas — sem GPS e sem doadora — estão em pastas que nomeiam uma cidade:
  "Maracatu Rural - Nazare da Mata - PE" (260), "madrid" (230), "Amsterdam
  2016" (201), "Paris 2016" (79), "Festa do Papangu - Bezerros - PE" (63),
  "Rio de Janeiro" (62, em duas pastas). Dizer
  "cidade = Amsterdam" só pelo texto seria inventar lugar: "3 Picos" não é
  Picos (PI), "Guadalupe - RJ" não é a ilha, "Lapa" e "Grajaú" são bairros
  do Rio e cidades de São Paulo, "Centro" e "Panorama" são cidades
  pequenas em algum país.
- Medição antes (pastas cujas fotos têm GPS próprio): cidade exata acerta
  sempre que a pasta É a cidade — Rio 1 km, Paris 2 km, Amsterdam 2 km,
  Bordeaux 1 km, Nova Friburgo 0 km, Niterói 12 km; erra por 450–600 km
  quando a cidade é só pasta-mãe e a subpasta nomeia outro lugar ("Paris
  2016/Aquitânia - Quai Salvette"). Homônimos menores ("Paris" TX 25 mil,
  "Centro" IT 43 mil, "Panorama" GR 17 mil) ficam abaixo do piso.
- Calibração do raio (`scripts/calibrar_raio_cidade.py`, com os pisos da
  decisão): 10 pastas / 58 fotos com GPS próprio cujo nome é cidade
  confirmada — erro máximo 4,2 km (Paris), mediana 1,4 km. Niterói, que
  só entra com contexto (país no caminho), fica a 12 km do centro. **15 km
  cobre todos os casos medidos** e ainda é "uma cidade", não "uma região"
  — o teto de 50 km da herança (D-032) seria dúvida demais para quem sabe
  a cidade. Piso mais baixo que 500 mil sem contexto traria Niterói de
  volta, mas também Grajaú (384 mil, distrito de SP), Santos, Olinda,
  Vitória e Aurora (EUA): a régua ficou do lado de não inventar.
- A primeira versão desta fatia gravava o centroide em `gps_*_estimado`,
  os mesmos campos da herança. A revisão com olhos frescos mostrou o
  furo: o planner de escrita EXIF seleciona por `gps_lat_estimado IS NOT
  NULL` e gravaria no arquivo ORIGINAL um ponto com 15 km de dúvida como
  GPS (895 arquivos); e o Inspector, que só afirma o país quando não há
  Δt, esconderia a cidade que a fatia foi buscar. Daí o desenho abaixo.
- Decisão:
  1. `geolocation/cidades.py`: a cidade só vale confirmada no dataset —
     nome exato (tabela de apelidos PT → GeoNames: "Tóquio" → Tokyo,
     "Genebra" → Genève…), e piso de população por contexto: nome solto
     exige ≥ 500 mil (Amsterdam, Madrid, Paris, Rio); país escrito no
     caminho ou grafia da tabela baixa para ≥ 50 mil; sigla de UF no
     segmento baixa para ≥ 10 mil com o estado obrigatório ("Nazaré da
     Mata - PE"). Homônimo é desempatado pelo país do caminho, pela UF e
     por último pela população ("Paris" é a da França).
  2. Só vale a cidade do **segmento nomeador mais fundo**: pasta técnica
     e pasta só-data são puladas; se a subpasta nomeia algo que o dataset
     não conhece, nenhum ancestral vale — a foto está onde a subpasta
     diz. Parte que é país, UF ou palavra de evento não é candidata.
  3. O centroide vive **só em `locations`** (`Location` de fonte
     `pasta:cidades/1`, chave de cache com país + estado + nome — "Trindade"
     em GO e em PE são duas), apontado por `media_files.location_id`.
     **Nunca em `gps_*_estimado`**: por construção fica fora do plano de
     escrita EXIF, da detecção de casa, da distância de casa das sessões e
     da correlação (que só leem GPS próprio e herança). O planner EXIF
     também exclui cidade/país de `Location` de fonte `pasta:` — é a origem
     mais fraca (0,60) e a escrita no original é a operação mais
     irreversível do app; incluí-la é decisão explícita do dono, não desta
     fatia. Roda em
     `_estimar_por_pasta`, depois da herança e do geocoding, só para quem
     não tem coordenada nenhuma; quem não tem coordenada nem cidade
     confirmada perde o `location_id` (pasta renomeada não deixa lugar
     órfão). Doadora real continua valendo mais que a pasta.
  4. Evidência de `pais`/`regiao`/`cidade` com origem `pasta` (0,60,
     `docs/CONFIANCA.md`), justificativa "'Amsterdam' no nome da pasta
     ('Amsterdam 2016'), cidade confirmada no dataset offline". O nome sai
     como o dataset grava ("Tokyo"), a mesma grafia que o geocoding
     reverso dá às fotos com GPS — senão "Tóquio" e "Tokyo" viravam duas
     pastas no destino (mesma razão de `canonizar_pais`).
  5. Mapa e Inspector leem o centroide do `Location`: ponto com
     `origem = "pasta"`, círculo de `RAIO_CIDADE_M` = 15 km e frase
     própria; o painel "Por que este lugar" diz "N fotos estão aqui pelo
     nome da pasta" em vez de "herdaram de ?"; o Inspector rotula "Lugar ·
     pela pasta" e mostra a cidade inteira. `origem` (`arquivo | doadora |
     pasta`) passa a sair em todo ponto do mapa e no `local` do detalhe.
  6. `tz_estimado` usa o país da cidade confirmada antes do país por
     texto, só para quem não tem coordenada.
  7. O índice de cidades guarda só tuplas curtas das cidades ≥ 10 mil
     hab., com lock — não os 155 mil dicionários do arquivo.
- Alternativas rejeitadas: reaproveitar `gps_*_estimado` (vaza para a
  escrita EXIF); coluna nova de proveniência (migração para um fato que
  `locations.fonte` já carrega); piso de população único e baixo (traz
  "Centro"/"Lapa"/"Aurora"); aceitar cidade de pasta-mãe (450 km de erro
  medido); raio por população (Niterói, 456 mil hab., fica a 12 km do
  centroide — a fórmula dava 7 km); reaproveitar o raio da herança (50 km).
- Limitações conhecidas: cidade média sem contexto ("Niterói 2016",
  "Petrópolis", "Cabo Frio", "Bordeaux") não vale — o dono escreve o
  país no caminho ou a UF no segmento e ela passa a valer; nome de
  pessoa que é cidade grande ("Sofia", "Salvador", "Victoria",
  "Santiago", "Lima") passa pelo piso — zero ocorrências nas 555 pastas
  do catálogo, mas é a classe de falso positivo que sobra, e só o país
  no caminho a desfaz; a grade não tem faceta própria para "lugar pela
  pasta" (só `sem_gps`, que passa a excluí-las, e `local_estimado`, que
  é da herança) — candidata a fatia de UI; o rodapé do mapa mostra a nota
  do raio da herança mesmo quando o grupo só tem círculos de cidade, e a
  lista "Fotos aqui" rotula os dois como "estimado"; cidade homônima de país como país da pasta ("Granada e Sevilha
  2018" → o país "Granada" de D-082 filtra Sevilha para fora; zero
  ocorrências no acervo); cidade escrita de forma que o dataset não
  conhece ("Atacama", "Pantanal", "3 Picos") continua sem lugar — é a
  fronteira da fatia 2, candidata ao GenAI de pasta.
- Medição depois: 895 fotos de acervo sem GPS e sem doadora passam a ter
  cidade e centroide (1.492 sem GPS nessas pastas, as demais já tinham
  doadora); em pastas com GPS próprio, 58/58 fotos dentro do raio.
- Como reverter: `git revert` do commit desta fatia; os `Location` de
  fonte `pasta:` ficam órfãos e inofensivos (a rodada seguinte de
  `gerar()` refaz `location_id`).
- Status: decidido pelo dono (fatia 2 de localização estimada),
  implementado e commitado nesta fatia.

## D-084 — Uma resposta só para "quando a foto foi tirada": EXIF, senão o nome do arquivo, senão o mtime em hora de parede

- Fase: localização estimada, fatia 3 (2026-09-20) — opção 3 escolhida
  pelo dono entre as quatro medidas na fatia 1 ("fechar furos M1/M5").
- Classe: A — medido antes e depois no catálogo real; nenhum limiar muda.
- Contexto: a auditoria de 2026-09-19 (M1/M5 em
  `docs/reconstrucao/08-ERROS_CONHECIDOS.md`) apontou que a linha do tempo
  do motor fazia `data_capturada or mtime` em cinco lugares
  (`engine.py`: correlação, sessões, acontecimentos, transição casa↔fora),
  misturando hora de PAREDE (`data_capturada`, D-038) com UTC naive (o
  `mtime` que o scanner grava com `_ts`); e que a evidência de data já
  preferia a data escrita no nome do arquivo ao mtime, enquanto a linha do
  tempo ignorava o nome — `IMG-20150420-WA0001.jpg` copiado em 2024 ganhava
  `{ano}` 2015 e sessão de 2024.
- Medição antes (catálogo real, 2026-09-20):
  - 957 fotos de acervo só-mtime sem lugar. Convertendo o mtime para hora
    de parede (com `tz_estimado` — só 23 têm — ou o fuso da máquina), a
    doadora mais próxima continua a mais de 12 h em **todas**: o furo M1
    não rende herança nenhuma neste acervo hoje. O "33% com delta exato de
    hora" da auditoria é real, mas essas fotos têm `data_capturada` e o
    mtime nem entra.
  - As 205 fotos sem lugar com doadora a ≤ 12 h são **todas** "mesma fonte
    e mesma câmera" (regra 1 da herança: câmera com receptor de GPS que
    pega em uns quadros e não em outros). Não é tempo: é uma regra a
    revisar como opção própria, fora desta fatia.
  - M5 real e pequeno: no acervo inteiro, 1.072 fotos são só-mtime e 57
    delas têm data no nome (54 com hora, 3 só dia) — 9 entre as sem lugar
    (`IMG_20140706_111834.jpg` com mtime de 2014-11-19, capturas de tela
    `iScreen Shoter - 20230622141938732.jpg`).
  - Decisão do dono, informado desses números: seguir mesmo assim — o
    defeito é de correção (duas bases de tempo na mesma comparação) e o
    custo é baixo; o ganho hoje é a honestidade da linha do tempo e os
    próximos lotes de WhatsApp/capturas, não as 957.
- Decisão:
  1. `grouping/datas.quando_da_foto(data_capturada, nome, mtime,
     tz_padrao=...)` → `Quando(instante, origem, precisao)`: EXIF
     (`exif`, segundo) > data no nome (`nome`; segundo quando o nome traz a
     hora — `IMG_20140706_111834`, `2024-03-15 às 10.30.22`,
     `20230622141938732` —, senão dia, posto ao meio-dia: erro máximo de
     12 h, não 24) > mtime convertido de UTC para a hora de parede pelo
     `tz_padrao` do motor — por omissão `fuso_da_maquina()`: a zona IANA
     de `TZ` ou de `/etc/localtime`, com horário de verão histórico (o
     offset de agora aplicado a janeiro de 2015 erraria uma hora) — `fs`,
     segundo.
  2. O motor usa `_quando(media)` nos cinco lugares. Na correlação só
     entra quem tem precisão de segundo; `hora_do_arquivo` (penalidade 0,6
     de D-025) vale para `fs` e para `nome`. Data só de dia agrupa por
     sessão e acontecimento, mas não mede minutos até doadora nenhuma.
  3. A evidência de data pelo mtime passa a mostrar a hora de parede, com
     a justificativa dizendo que foi levada ao fuso desta máquina.
  4. `DataDoNome` ganha `com_hora`; os padrões de nome reconhecem a hora
     separada da data (`_`, `-`, espaço, "às", "at") e, colada, só com os
     três dígitos de milissegundo da captura de tela do macOS — um número
     corrido de 14 dígitos continua serial, não data. Hora inválida não
     invalida o dia; com hora, `texto` cita o trecho inteiro.
  5. O que NÃO muda: a linha do tempo dos álbuns externos
     (`_IndiceDeAlbuns.__init__`, `data or mtime` em SELECT cru) e a
     ordenação da grade (`repositories/media.py`: `data_capturada` com
     `nulls_last()` — as 1.072 fotos só-mtime caem no fim da grade, sem
     entrar na linha do tempo que o motor agora sabe calcular) — fora do
     alcance de uma função Python por linha; registrados como dívida.
- Alternativas rejeitadas: coluna nova para o instante unificado (é
  derivável das três já existentes, e D-038 já proibiu o terceiro lugar
  para a mesma verdade); converter o mtime pelo `tz_estimado` da foto —
  parece mais honesto para foto tirada fora, mas o `tz_estimado` nasce da
  própria rodada (país herdado): a primeira versão desta fatia fazia isso
  e o teste mostrou a linha do tempo mudar de rodada para rodada (1ª herda
  Avignon com o fuso da máquina, 2ª converte pelo fuso de Paris e perde a
  cidade). Fuso único e determinístico, a premissa dita em voz alta: o
  mtime de uma cópia feita nesta máquina está no fuso dela; tratar data só
  de dia como segundo (mediria minutos que não existem).
- Medição depois: mesma de antes para herança (0 fotos novas); 153 fotos
  mudam de dia de calendário na linha do tempo (57 pelo nome, o resto
  pela conversão do mtime), 0 mudam de ano, 0 perdem papel de doadora;
  toda foto só-mtime passa a entrar na linha do tempo na hora de parede.
- Como reverter: `git revert` do commit desta fatia.
- Status: decidido pelo dono, implementado e commitado nesta fatia.


## D-085 — Janela de país da herança de GPS sobe de 12h para 48h

- Fase: localização estimada, fatia 4 (2026-09-20) — opção 2 escolhida
  pelo dono entre as opções medidas ao fechar a fatia 3, com pedido
  explícito de testar 24h e 48h antes de decidir.
- Classe: A — estende D-025 com medição contra o acervo real; cidade
  (10 min) e região (2h) inalteradas.
- Contexto: D-025 fixou 12h porque era a maior janela sustentada pelos
  dados de então. 957 fotos de acervo continuavam sem lugar mesmo depois
  de D-084 corrigir a base de tempo, todas a mais de 12h de qualquer
  doadora.
- Medição (`scripts/calibrar_janela_pais.py`, técnica de doadora
  hipotética de D-032/D-074 — fotos com GPS nos dois lados, uma escondida,
  país da doadora comparado ao país real por geocodificação offline; UM
  par por candidata, a doadora ÚNICA que `herdar_gps` de fato escolheria —
  **a primeira versão desta calibração contava os dois lados como pares
  independentes, o que `herdar_gps` nunca faz para país; a revisão com
  olhos frescos achou o erro antes do commit e os números abaixo já são
  os corrigidos**, rodados de novo com a metodologia certa):

  | janela | cobertura ATÉ esta janela | cobertura na FAIXA nova | acurácia por par NA FAIXA | acurácia por dia NA FAIXA |
  |---|---|---|---|---|
  | 12h (linha de base, nunca medida antes) | 13.373 fotos | — (0–12h) | 86,7% (2.551/2.942) | 97,2% (erro em 3/41 dias) |
  | 24h | 15.796 fotos | +2.423 (12–24h) | 91,6% (596/651) | 97,5% (erro em 1/23 dias) |
  | 48h | 18.196 fotos | +4.823 (24–48h) | 91,2% (478/524) | 90,5% (erro em 2/21 dias) |

  **Cobertura é cumulativa** (cada linha soma sobre a anterior — o ganho
  marginal de 48h sobre 24h é +2.400, não +4.823); **acurácia é marginal**,
  só da faixa nova que aquela janela passa a aceitar (12h mede 0–12h; 24h
  mede 12–24h; 48h mede 24–48h) — não misturar as duas leituras. Achado
  que muda a leitura da fatia: **24h e 48h são mais precisas por par do
  que a janela de 12h já em produção**, que nunca tinha sido medida por
  doadora hipotética até agora. Os erros que sobram
  concentram-se em viagens de fronteira reais — Patagônia/Tierra del
  Fuego fev/2020 (Chile↔Argentina, a maior parte dos erros nas três
  faixas), Brasil↔Bolívia jul/2023 (Pantanal) — não em erro de
  geocodificação; é o limite estrutural que D-025 já registrou
  (`raio_incerteza` não serve para escala de país, D-074).
- Decisão: `JANELAS_POR_CAMPO["pais"]` de `grouping/correlacao.py` sobe
  para 48h. O dono escolheu 48h antes da correção da metodologia (quando
  os números pareciam mostrar um trade-off mais duro); a medição corrigida
  sustenta a escolha com folga maior do que a informada na hora — 48h
  erra menos por par do que a própria janela de 12h atual, ao custo de
  acurácia por dia um pouco menor que 24h (90,5% vs 97,5%, 2 viagens com
  erro em vez de 1).
- **O que muda e não é aditivo** (achado da revisão, não previsto na
  primeira versão desta decisão): o fator de confiança de
  `campos_confiaveis` decai dentro da PRÓPRIA janela — alargá-la achata a
  rampa e SOBE o fator de heranças que já existiam, mesmo Δt, mesma
  doadora, sem evidência nova. Medido sobre o catálogo persistido: das
  13.375 heranças de país já ativas com Δt ≤ 12h, 12.818 têm o fator
  alterado; 249 sobem de badge BAIXA→MÉDIA (nenhuma desce, nenhuma sai de
  ALTA — o fator vai de 0,6 a 1,0 dentro da rampa, e mesmo no **teto**
  (fator 1,0) o score fica em `0,75×1,0=0,75`, abaixo do piso de ALTA
  0,8; é isso que garante o limite, não o piso da rampa). Remedindo
  direto de `herdar_gps` sobre as refs, em vez de ler o que está
  persistido: 13.373/12.753/247 — 2 heranças e 65 fatores a menos que a
  base persistida, não por arredondamento: são POPULAÇÕES diferentes (o
  catálogo tem 13.375 linhas com `gps_estimado_delta_s`; a re-execução
  filtra por `precisao == "segundo"`, D-084 — 2 fotos a menos entram no
  cálculo desde a base, e o restante da diferença nos fatores vem de
  arredondamento de ponto flutuante nas bordas exatas da rampa). Ordem de
  grandeza igual nas duas bases. Nenhum doador, delta ou campo de
  cidade/região muda — só a leitura de confiança do país, porque
  a fórmula mede posição relativa dentro da janela, não posição absoluta
  no tempo. Aceito como consequência do próprio desenho de D-025 ("decai
  dentro da PRÓPRIA janela"), não como bug — mas precisa estar escrito
  para quem revisar Revisão/Mapa não estranhar ~250 fotos "sem mudar
  nada" mudando de cor.
- **Guardas novas em `exif_write/planner.py`** (achado da revisão, em
  três rodadas): herança só-país nunca mais entra como candidata a
  **GPS exato** nem a **nome de cidade** gravável no arquivo original —
  nem pela perna de GPS nem quando a linha entra pela perna de cidade/país
  (a `Location` é resolvida do MESMO ponto herdado, sem olhar
  granularidade, então uma herança fraca demais para GPS ou cidade ainda
  podia aparecer com esses campos preenchidos: a tela já escondia essa
  cidade — `_campos_do_lugar`, `server/app.py` — mas o plano de escrita
  propunha gravá-la mesmo assim). Sem estas guardas, D-085 faria o plano
  propor gravar no original o ponto exato ou o nome da cidade de uma
  doadora a até 47h de distância — em escala de país isso pode ser
  centenas de km do lugar real, violando o que EXIF-02/invariante 7
  prometem (só campo vazio, valor confiável).
  1. **Primeira versão** (rodada 1): janela fixa `_JANELA_ESCRITA_GPS_S`
     = janela de "região" (2h) só para GPS; cidade sem guarda.
  2. **Rodada 2**: achado que cidade vazava pela perna de cidade/país
     (a `Location` tem cidade mesmo em herança só-país) — guarda de
     cidade adicionada, com janela própria `_JANELA_ESCRITA_CIDADE_S`
     (10 min).
  3. **Rodada 2, mesmo commit**: `_JANELA_ESCRITA_GPS_S` redefinida para
     `RAIO_TETO_M/VELOCIDADE_PLAUSIVEL_MS` (~2h19min, o domínio em que
     `raio_incerteza` satura) em vez da janela de região (2h) — para
     desacoplar do nome errado. **Isso abriu uma fresta de 19 minutos**
     (Δt de 2h00 a 2h19) em que a herança já é só-país por
     `campos_confiaveis`, mas a nova janela ainda a deixava passar como
     GPS gravável — 566 mídias no acervo real. Achado pela revisão com
     olhos frescos antes do commit.
  4. **Correção final** (a que ficou): as duas janelas paralelas saem;
     o planner chama `campos_confiaveis` DIRETO — o mesmo predicado que
     `_campos_do_lugar` já usa na tela — e testa `"regiao" in campos` para
     GPS, `"cidade" in campos` para cidade. Nenhuma constante para
     divergir de novo. A candidatura em SQL (WHERE) volta a ser barata e
     larga (qualquer `gps_lat_estimado`, qualquer Δt); a exigência real
     é só em Python, uma vez, na função `_campos_da_heranca`. GPS PRÓPRIO
     (não herdado) continua sustentando cidade sempre — a guarda é sobre
     herança, nunca sobre GPS medido no próprio arquivo. País segue sem
     guarda: D-025 o sustenta em qualquer Δt da própria janela, por
     desenho. Lição registrada: uma janela paralela para a mesma pergunta
     que o motor já responde ("este Δt ainda é preciso?") é o padrão que
     abriu esta fresta — usar o predicado do motor direto, nunca
     redeclarar um valor que já existe em outro lugar, é o que sobrou
     como regra desta fatia.
- `scripts/calibrar_raio_incerteza.py` (achado da revisão): importava
  `JANELA_HERANCA` de `correlacao.py` para decidir até onde buscar par —
  como essa constante agora é o máximo de `JANELAS_POR_CAMPO` (48h,
  dominado por país), a calibração de `raio_incerteza`/`COBERTURA_MEDIDA`
  passou a incluir pares de escala de país, que ela nunca foi calibrada
  para medir (medido: cobertura por dia caía de 97,0% para 79,6% com essa
  contaminação). Corrigido: janela própria e fixa (`_JANELA_MOVIMENTO =
  12h`), independente da janela de país — `COBERTURA_MEDIDA = 0.936`
  continua reproduzindo (93,5% medido de novo após a correção).
- **A cobertura de 93,6% continua sem valer para os círculos de 12–48h**
  (achado da revisão): desacoplar a calibração do raio da janela de país
  resolveu a contaminação, mas não criou uma medição nova para a faixa
  que D-085 passou a alcançar — ela simplesmente ficou fora, como sempre
  esteve. Medido à parte: círculos de heranças de 12–48h cobrem 70,7%
  bruto / 59,0% por dia (contra 94,9%/97,0% dos círculos ≤12h) — bem
  abaixo da promessa impressa no mapa. Corrigido: `/api/mapa` passa a
  detectar herança além de 12h no grupo e trocar `NOTA_DO_RAIO` por
  `NOTA_DO_RAIO_ALEM_DA_MEDICAO`, que não cita o número — a legenda deixa
  de prometer uma cobertura que não foi medida naquela escala.
- O que NÃO muda: `RAIO_TETO_M` (50 km) — é função de `Δt` direto, não da
  largura da janela, e já satura bem antes de 12h (D-032).
- **Dívida registrada, não corrigida nesta fatia**: `_coords`
  (`classification/engine.py`) devolve a coordenada da doadora sem
  checar se o Δt sustenta "pais" antes de alimentar
  `dist_mediana_casa_km` e `dividir_por_transicao_casa` — herança
  só-país (2h–48h) participa da distância de casa e da divisão
  casa/viagem com um ponto que a evidência engine só admite como país,
  não como posição. Pré-existente (já valia para 2h–12h antes de D-085);
  D-085 só estende o alcance. Fora do escopo desta fatia — anotado para
  não ficar escondido.
- Alternativas rejeitadas: 24h (ganho menor; com a metodologia corrigida,
  a acurácia por par é quase idêntica à de 48h — não há janela "segura"
  que evite viagem de fronteira, e 48h dobra a cobertura pelo mesmo
  risco); teste de concordância (D-074) aplicado a país — já rejeitado em
  D-025/D-074 por escala incompatível; deixar a escrita EXIF aceitar
  qualquer granularidade (rejeitado pela guarda nova acima).
- Limitação conhecida, não escondida: viagem por região de fronteira
  (Patagônia, Pantanal, tríplice fronteira) continua sujeita a herdar o
  país errado dentro de 48h — é o preço explícito desta escolha, medido,
  não uma surpresa. Corrigir isso de verdade pede geocodificação nos dois
  lados (como o teste de concordância faz para cidade/região), fora desta
  fatia. Duas escalas de score de país convivem no catálogo até a próxima
  geração de sugestões: mídia com sugestão já decidida (pula
  `_evidencias_geo`) mantém o score da rampa de 12h até ser regerada.
- Como reverter: `JANELAS_POR_CAMPO["pais"]` volta a `timedelta(hours=12)`
  em `grouping/correlacao.py`; nada é persistido de forma irreversível —
  regerar sugestões refaz. As guardas do planner EXIF (GPS e cidade) e a
  nota condicional do mapa podem ficar mesmo assim, revertendo só a
  janela de país.
- Status: decidido pelo dono; a medição que embasou a escolha continha um
  erro de metodologia, corrigido e reexecutado antes do commit — a
  conclusão (48h) se sustenta, com margem melhor do que a informada
  originalmente. Implementado e commitado nesta fatia.

---

## D-086 — Regra 1 da herança: câmera com receptor GPS confirmado pode doar para si mesma, com confiança rebaixada por falta de amostra

- Fase: localização estimada, fatia 5 (2026-09-20) — opção 1 do dono entre
  três alternativas apresentadas ao fechar a fatia 4 (implementar com
  janela pequena e confiança rebaixada / validar mecanismo contra uma
  segunda câmera antes / abandonar), pulando deliberadamente a validação
  intermediária.
- Classe: B — abre uma exceção pontual em `FotoRef.outra_origem`
  (`grouping/correlacao.py`), não muda nenhuma janela existente.
- Contexto: D-029 (2026-07-31) registrou que a EOS 5D Mark IV tem receptor
  de GPS embutido de verdade (2.878/3.633 fotos, 79% — confirmado no
  catálogo do Lightroom) e ficou "aguardando o modelo de evento". Hoje
  `outra_origem` proíbe qualquer doação dentro da mesma fonte+câmera —
  regra pensada para câmera comum, que não tem por que "confiar em si
  mesma" mais do que o relógio já confia. Para a 5D Mark IV isso descarta
  doadoras válidas: a foto sem GPS ao lado, na mesma sessão, que também
  veio do mesmo receptor.
- Medição (read-only contra o catálogo real, mesma técnica de doadora
  hipotética de D-032/074/085):
  - Órfãs elegíveis (sem doadora de outra origem dentro da janela do
    campo, mas com candidata same-câmera ≤48h): 205 fotos — 171 EOS 5D
    Mark IV, 25 iPhone 6, 9 BlackBerry 9500. Só a 5D Mark IV tem a
    justificativa de D-029 (receptor real); iPhone 6 e BlackBerry ficam
    de fora da regra — GPS de celular não tem essa distinção de mecanismo.
  - Distribuição de Δt das 171 órfãs da 5D Mark IV até a doadora
    same-câmera mais próxima: ≤10min 59 · 10-30min 142 · 30min-2h 211 ·
    2-6h 4 · 6h+ 0. **99% do ganho (412/416 pares candidatos) está em
    ≤2h** — não há cauda longa que justifique uma janela dedicada maior
    que as já existentes (`regiao`, 2h).
  - **Calibração de acurácia não rendeu amostra útil**: testando doadora
    hipotética nas 3.277 fotos da 5D Mark IV que já têm GPS próprio, a
    doadora same-câmera mais próxima fica a ≤10min em 99,8% dos casos
    (fotos em rajada/sessão contínua) — sobram só 5 pares nas faixas de
    10min-2h, a faixa que a regra precisa justificar. Amostra pequena
    demais para medir acurácia com confiança (diferente de D-082/083/085,
    que tinham centenas a milhares de pares na faixa relevante).
- Decisão: `FotoRef.outra_origem` **não muda** (continua exatamente como
  antes — cross-source só). A exceção mora num método novo,
  `mesma_camera_confiavel`, usado só como FALLBACK dentro de `procurar`:
  o laço varre o lado inteiro da janela por uma doadora de outra origem
  primeiro; só aceita a same-câmera quando não existe nenhuma. A câmera
  elegível é `CAMERAS_RECEPTOR_GPS_CONFIAVEL` (hoje: só EOS 5D Mark IV —
  lista medida, não "toda Canon"). A janela reaproveita `JANELAS_POR_CAMPO`
  sem constante nova (mesmo motivo de D-085: nunca duplicar uma janela
  que já existe). Como a acurácia não foi medida, a doação same-câmera
  carrega uma penalidade de confiança dedicada
  (`_PENALIDADE_MESMA_CAMERA = 0.6`, mesmo valor de
  `_PENALIDADE_HORA_DE_ARQUIVO` por precedente, motivo diferente:
  aqui o Δt é confiável, a acurácia da doação é que não tem amostra) —
  aplicada em `campos_confiaveis(..., mesma_camera=True)`, dentro de
  `herdar_gps`. Com o teto de `vizinhanca_temporal` já em 0.75 (nunca
  chega a alta, D-085), a penalidade derruba TODO o intervalo (0-48h)
  para baixo do piso de média (0,5) — confirmado por varredura, não só
  no melhor caso — e a justificativa em `_evidencias_geo` diz
  explicitamente que a doadora é a própria câmera e que não há amostra
  medida.
- Por quê a confiança rebaixada em vez de tratar como herança normal: o
  modelo de evidências (docs/CONFIANCA.md) exige que a sugestão responda
  "por quê" — aqui o "por quê" é um argumento de mecanismo (D-029), não
  uma medição como todas as outras fatias desta sequência. Alegar o
  mesmo patamar de confiança sem o mesmo tipo de evidência quebraria essa
  regra. O dono foi avisado da lacuna de calibração antes de escolher
  esta opção e decidiu prosseguir mesmo assim.
- **Achados da revisão com olhos frescos, corrigidos antes do commit**
  (dois deles reais e sérios — a primeira versão implementada nesta
  fatia tinha um bug de deslocamento e um vazamento de segurança):
  1. **Não-aditivo, de novo** (crítico do ponto de vista de qualidade,
     mesma classe de erro que D-085 já tinha cometido uma vez): a
     primeira versão deixava `outra_origem` aceitar same-câmera
     incondicionalmente, então `procurar` retornava a primeira doadora
     válida — e a same-câmera, quase sempre mais perto no tempo (rajada),
     **deslocava** uma doadora de outra origem que já era válida e
     medida. Medido no catálogo real antes da correção: 298 heranças
     trocadas de doadora, 296 com a badge rebaixada de média para baixa
     SEM motivo — a doadora medida ainda existia, só não era mais
     escolhida. Corrigido reestruturando `procurar`: cross-source sempre
     vence; same-câmera só entra quando não há nenhuma de outra origem
     no mesmo lado dentro da janela (fallback de verdade, não
     concorrente). `outra_origem` voltou a ser exatamente o método
     original — a exceção não vive mais nele.
  2. **Vazamento para a escrita EXIF** (o achado mais sério): a alegação
     original desta decisão — "não muda o plano de escrita EXIF, a
     penalidade só afeta a badge" — **era falsa**. `exif_write/planner.py`
     decide o que é seguro escrever pelo Δt (`campos_confiaveis`), não
     pelo fator de confiança; como a doadora same-câmera costuma estar
     mais perto no tempo que a cross-source que existia antes, o MESMO
     Δt encolhido passava a sustentar `regiao`/`cidade` no predicado de
     Δt, sem o planner saber que a origem daquele Δt não tinha amostra
     nenhuma. Medido no catálogo real antes da correção: 437 fotos
     passariam a ter GPS exato/cidade oferecidos para escrita no arquivo
     ORIGINAL a partir de uma doação sem amostra de acurácia. Corrigido
     com uma coluna nova, `gps_estimado_mesma_camera` (migração 0021),
     persistida em `_persistir_herancas`; o planner (`_campos_da_heranca`
     + guarda nova) e a tela de detalhe (`_campos_do_lugar`, que o
     próprio comentário do planner já dizia usar "a MESMA função") agora
     recusam GPS exato e cidade quando a flag é `True` — só país
     continua sem guarda (D-025, ungated por desenho, mecanismo-agnóstico).
  3. `calibrar_janela_pais.py` (a calibração de D-085) usa
     `FotoRef.outra_origem` ao vivo — a primeira versão desta fatia
     contaminava essa medição sem avisar (a faixa de 24-48h caía de 524
     para 201 pares, -62%). Resolvido de graça pela correção do achado 1:
     como `outra_origem` voltou ao comportamento original, a calibração
     de D-085 nunca mais vê a exceção. Confirmado, não só deduzido.
  4. A frase de concordância (D-074, "confirmada por outra foto do lado
     oposto") podia empilhar com a frase de mecanismo ("sem amostra
     medida") na mesma justificativa — duas afirmações que se
     contradizem lendo em sequência. A corroboração geométrica de D-074
     foi calibrada para doadora de outra origem, não para este caso;
     corrigido suprimindo a frase de concordância quando `mesma_camera`
     é verdadeiro (o score não muda — concordância nunca somou score,
     só texto).
  5. O teste `test_campos_confiaveis_mesma_camera_penaliza_todos_os_campos`
     comparava `round(fator*0.6, 3)` contra o fator JÁ arredondado —
     passava só em Δt onde o fator é exatamente 1.0 (dupla rolagem de
     arredondamento diverge do valor real no resto da rampa). Reescrito
     com tolerância sobre vários Δt. Faltava também um teste que
     exercitasse o cenário do achado 1 (doadora same-câmera mais perto E
     cross-source mais longe presentes ao mesmo tempo) — adicionado.
- **Rodada 3, sobre o diff da rodada 2**: a correção do achado 1 preferia
  cross-source só DENTRO do mesmo lado (antes/depois) — o `min()` final
  ainda comparava os dois lados só por Δt cru, então uma same-câmera de
  um lado ainda podia deslocar uma cross-source do OUTRO lado. Medido:
  298 deslocamentos caíram para 43 (grande melhora, não zero) e **1
  caso real perdeu uma oferta de escrita de `regiao` que tinha antes da
  fatia** (regressão, não só badge injusta). `_evidencias_geo` também
  continuava oferecendo região/cidade para o destino sugerido — 201/205
  heranças same-câmera propunham copiar para uma pasta de cidade que a
  tela e o planner já recusavam. Corrigido: `procurar` agora devolve
  `(delta, candidata, cross: bool)`; a escolha final roda sobre os
  achados `cross=True` de QUALQUER lado quando existe pelo menos um, e
  só cai para o fallback quando nenhum dos dois lados tem cross-source.
  `_evidencias_geo` ganhou `if heranca.mesma_camera and campo != "pais": continue`
  (depois substituído, ver rodada 4). Reconfirmado no catálogo real após
  a correção: **0 deslocamentos, 0 heranças preexistentes afetadas**, as
  162 órfãs recuperadas continuam com 0 novas ofertas de GPS exato/cidade
  — a fatia é estritamente aditiva.
- **Rodada 4, sobre o diff da rodada 3**: dois achados novos, nenhum
  bloqueante. (a) A justificativa dizia "a essa distância dá para
  afirmar o país, não a cidade" para heranças same-câmera de Δt curto —
  motivo ERRADO: o corte não é por Δt (2min sustentaria cidade em
  condições normais), é por falta de amostra medida; o texto contradizia
  a si mesmo ("tirada a 2min" seguido de "a essa distância..."). (b) uma
  testemunha same-câmera (o lado que NÃO foi escolhido como doadora)
  ainda podia conceder o selo "confirmada" (D-074) a uma herança
  cross-source medida — 1 ocorrência real (a mesma media do achado da
  rodada 3). Corrigido: `Heranca.campos` agora é capado em `[("pais", fator)]`
  na origem (`herdar_gps`, logo após `_confrontar_com_outro_lado`), não
  mais filtrado em `_evidencias_geo` — isso fez `Heranca.granularidade`
  virar `"pais"` sozinho e consertou de quebra uma terceira superfície
  não sinalizada antes (`engine.py`, nome de viagem/sessão a partir da
  coordenada herdada, que também lia a cidade indevidamente). A cláusula
  de justificativa ganhou um caso dedicado para `mesma_camera` com o
  motivo certo ("sem amostra medida de acurácia, por isso só o país é
  afirmado"), substituindo a genérica. `_confrontar_com_outro_lado`
  passou a receber a tupla `(delta, candidata, cross)` inteira e trata
  testemunha `cross=False` como base não confiável — mesmo tratamento
  que já dava a `hora_do_arquivo`. Reconfirmado no catálogo real: 0
  heranças com concordância alterada (era 1), fatia continua
  estritamente aditiva. Duas guardas que ficaram inalcançáveis por
  construção (`concordancia` sempre vazia para same-câmera) foram
  removidas em vez de mantidas como defesa-em-profundidade morta.
- Alternativas rejeitadas: validar o mecanismo contra a DJI FC8482 (100%
  de cobertura própria) antes de decidir — o dono pulou essa etapa
  intermediária explicitamente; abandonar a regra 1 por falta de amostra
  — rejeitada pelo dono, que aceitou o argumento de mecanismo como
  suficiente com a confiança rebaixada.
- Limitação conhecida, não escondida: os números de acurácia de D-082 a
  D-085 vieram de medição; esta fatia não tem equivalente — é a primeira
  decisão da sequência de localização estimada sustentada só por
  mecanismo. Se o padrão de disparo do receptor da 5D Mark IV mudar
  (câmera trocada, firmware, uso diferente), a premissa "gaps longos são
  raros" pode deixar de valer sem que nada aqui detecte a mudança. A
  exiftool `metadata/exiftool.py` não faz `.strip()` no make/model lido
  (diferente do extrator puro-Python, que faz) — risco latente de a
  tupla de câmera não bater com `CAMERAS_RECEPTOR_GPS_CONFIAVEL` por
  espaço sobrando; hoje os valores do catálogo real estão limpos
  (confirmado), então não é falha ativa — anotado, não corrigido nesta
  fatia (pré-existente, mais largo que esta regra).
- Como reverter: remover o fallback em `procurar` (a chamada a
  `foto.mesma_camera_confiavel`) e a coluna `gps_estimado_mesma_camera`
  fica inofensiva mas sempre `False`; nada é persistido de forma
  irreversível — regerar sugestões refaz.
- Status: decidido pelo dono; quatro rodadas de revisão com olhos frescos
  (mesmo agente, contexto mantido) — a primeira implementação tinha um
  bug de deslocamento e um vazamento para a escrita EXIF, a segunda
  correção só resolveu metade do deslocamento e vazava para o destino
  sugerido, a terceira correção acertou a conclusão mas errava o
  motivo na justificativa. Confirmado no catálogo real, na versão final:
  estritamente aditiva (0 heranças preexistentes tocadas, 162 novas).
  Implementado e commitado nesta fatia.

---

## D-087 — Desempate de doadora em Δt igual: prefere GPS direto do arquivo (EXIF) sobre catálogo externo

- Fase: localização estimada, fatia 6 (2026-09-20) — opção "doadora
  suspeita" do dono, entre as três alternativas apresentadas ao fechar a
  fatia 5 (audit A1/A2, regerar sugestões — ação do dono, ou esta).
- Classe: B — desempate pontual em `procurar` (`herdar_gps`), não muda
  nenhuma janela nem introduz mecanismo novo de detecção/descarte de
  doadora (ver "Alternativas rejeitadas").
- Contexto: D-032 (2026-08-01) já tinha flagueado, sem corrigir, um caso
  concreto — 2019-04-19, o catálogo Apple Fotos grava a foto em "casa" no
  Rio no mesmo segundo em que a câmera real está a 163 km, em Penedo.
  Registrado como "tarefa separada de qualidade da doadora", nunca
  implementado. `herdar_gps` escolhe a doadora mais próxima no tempo; em
  caso de empate exato, a ordem de desempate era incidental (a ordem da
  consulta ao banco), não desenhada.
- Medição (read-only contra o catálogo real, 101.122 mídias, 21.670 com
  GPS próprio):
  - O padrão de D-032 é raro, não sistêmico: só 92 fotos com GPS próprio
    (0,4%) discordam de um vizinho temporal muito próximo (>5x o raio
    esperado, >5 km, ≤15 min). A coordenada "casa" em si (-22,9657,
    -43,1892) aparece 310 vezes em 84 dias — normal para quem mora lá;
    o problema é só quando ela aparece num dia em que outra evidência
    contradiz.
  - Rodando `herdar_gps` de produção sobre o catálogo completo: só 4
    heranças reais hoje estão perto de uma doadora suspeita — e nas 4, a
    doadora correta (câmera, não "casa") já tinha sido escolhida. Empate
    resolvido por sorte da ordem da consulta, não por desenho — a
    garantia não existia, só o resultado tinha dado certo até agora.
  - **Impacto medido: zero heranças erradas no catálogo hoje.** Avisado
    disso, o dono escolheu ainda assim o fix cirúrgico (desempate
    determinístico), como seguro contra a coincidência não se repetir a
    favor no futuro — não como correção de bug ativo.
- Decisão: `FotoRef` ganha `gps_direto_do_arquivo: bool = True`. Fonte
  tipo `pasta` (scan de arquivo, GPS só pode ter vindo do EXIF) sempre é
  `True`; fonte de catálogo externo (`Source.tipo` via
  `_correlacionar`, uma consulta só, não por foto) é `True` apenas se
  `tipo == SourceType.PASTA`. `photo.location` do osxphotos (Apple
  Fotos) não distingue GPS real de captura de localização atribuída
  manualmente no app ("Assign a Location") — não há como saber com
  certeza qual dos dois gerou um valor específico sem reextrair o EXIF
  do arquivo (fora de escopo desta fatia; ver "Limitação conhecida").
  `procurar` (`grouping/correlacao.py`) agora, ao encontrar a primeira
  doadora cross-source de um lado, continua andando enquanto o Δt não
  mudar (doadores estão ordenados no tempo — um empate real forma um
  bloco contíguo) e escolhe, dentro do bloco empatado, a melhor por
  `_prioridade_de_desempate` — **hora confiável primeiro**,
  `gps_direto_do_arquivo` como critério secundário só entre candidatas
  com hora igualmente confiável; sem preferência aplicável, mantém a
  primeira encontrada (comportamento de antes, inalterado). A mesma
  prioridade decide também o empate ENTRE os dois lados (antes/depois),
  não só dentro de cada lado — a forma exata do caso original de D-032
  tem as duas doadoras em lados opostos. Generalizado para QUALQUER Δt
  empatado, não só Δt=0 exato.
- **Achado da revisão com olhos frescos, corrigido antes do commit**: a
  primeira versão do desempate olhava só `gps_direto_do_arquivo`, sem
  `hora_do_arquivo` — e podia trocar uma doadora com hora de EXIF
  (`data_capturada` preenchida) por uma de pasta com hora vinda do
  MTIME, mesmo que a fonte não fosse o problema daquele caso. Como
  `hora_incerta` penaliza TODOS os fatores de confiança da herança (não
  só o campo de GPS), essa troca era pior que a que a fatia existe para
  evitar. Também a MINHA PRÓPRIA verificação inicial estava incompleta:
  usava `data_capturada` bruta como `quando`, sem passar pelo cascade
  real (`quando_da_foto`) nem popular `hora_do_arquivo` — por isso só
  via 96 heranças "trocadas, todas cosméticas" quando a conta real
  (com o cascade certo) era 549 trocas, 425 delas piorando o fator.
  Corrigido: `_prioridade_de_desempate` ordena por
  `(hora_do_arquivo, not gps_direto_do_arquivo)` — hora decide primeiro.
  A mesma 2ª rodada achou uma variante: se a ÓRFÃ já tem hora incerta,
  `hora_incerta` final (`foto.hora_do_arquivo or doador.hora_do_arquivo`)
  é `True` de qualquer jeito — priorizar a hora da doadora nesse caso
  rebaixava `gps_direto_do_arquivo` sem ganho nenhum. Corrigido:
  `_prioridade_de_desempate(foto, candidata)` só prioriza hora da
  doadora quando `not foto.hora_do_arquivo` (senão os dois empatam no
  primeiro critério e o segundo, fonte, decide sozinho).
- Verificação de regressão (catálogo real, 102.248 refs com precisão de
  segundo, cascade `quando_da_foto` real, versão pré-fatia obtida via
  `git show HEAD:` do commit de D-086 para comparação fiel): **0
  heranças sumiram, 0 novas, 0 com fator PIOR** — 790 heranças com
  `doador_id` trocado E fator MELHOR, 124 trocas cosméticas (fator
  idêntico), 161 heranças ganharam `concordancia` que não tinham (0
  perderam). Os 4 casos reais de D-032 continuam corretos.
- Alternativas rejeitadas: mecanismo geral de "doadora suspeita"
  (descartar do pool qualquer doadora cujo GPS discorde de um vizinho
  próximo no tempo, não só em empate) — era a opção original oferecida,
  mas o dono preferiu o escopo menor dado o achado de impacto zero hoje;
  fica registrada como opção futura se o padrão voltar a aparecer com
  impacto real. Reextrair EXIF de toda foto do catálogo Apple para
  confirmar proveniência exata do GPS — caro (subprocesso por arquivo)
  para resolver um caso que hoje não tem incidente ativo.
- Limitação conhecida, não escondida: `gps_direto_do_arquivo` é um
  proxy por TIPO DE FONTE (`pasta` vs. catálogo externo), não uma
  proveniência exata por foto — uma foto de catálogo externo cujo EXIF
  também tem GPS real (o caso comum: iPhone com GPS de verdade
  sincronizado no Apple Fotos) é tratada como "não confiável" mesmo
  sendo, na prática, tão boa quanto uma foto de pasta; o inverso também
  vale — um JPEG exportado do Apple Fotos com localização atribuída no
  app, salvo numa pasta e escaneado como fonte `pasta`, ganharia
  `gps_direto_do_arquivo=True` e venceria sistematicamente uma doadora
  Apple corretamente medida no mesmo Δt (o espelho exato de D-032, não
  medido — nenhuma ocorrência encontrada no catálogo real, mas o proxy
  por tipo de fonte não a impediria). O desempate só entra em jogo
  quando há empate de Δt E desacordo geográfico E hora igualmente
  confiável — nesse caso raro, errar a favor da fonte mais verificável
  (pasta) é a escolha mais segura mesmo sabendo que ocasionalmente
  descarta uma doadora Apple que também estava certa. Resolver com
  precisão pediria marcar a proveniência por VALOR (não por fonte) no
  momento da importação — fora de escopo desta fatia, registrado para o
  futuro. `scripts/calibrar_janela_pais.py` e
  `scripts/calibrar_raio_incerteza.py` continuam sem `gps_direto_do_arquivo`
  (o segundo já reimplementa sua própria noção de "outra origem",
  deliberadamente decoupled desde D-086) — decisão consistente com o
  precedente: calibração mede deslocamento/janela, não a política de
  desempate, e as duas perguntas são independentes.
  **Achado da 2ª rodada de revisão, também registrado e não corrigido**:
  em desacordo geográfico real E hora em conflito (uma doadora com hora
  confiável mas geograficamente errada vs. uma com hora incerta mas
  certa), `_prioridade_de_desempate` escolhe a de hora confiável —
  prioriza a badge honesta (não afirmar mais do que a hora sustenta)
  sobre o valor geograficamente certo. É a leitura consistente com D-025
  ("sugestão errada com aparência de fundamentada é pior que nenhuma"):
  a doadora de hora incerta já carrega a penalidade (`hora_incerta`,
  badge cai, justificativa avisa "a proximidade pode ser coincidência"),
  então o sistema nunca afirma o lugar errado com confiança que não tem
  — mas também não escolhe ativamente o lugar certo quando ele exigiria
  confiar numa hora que não é confiável. Zero ocorrências no catálogo
  real (as 2.222 doadoras empatadas hoje concordam geograficamente em
  100% dos casos). Um segundo efeito, também sem ocorrência real: o
  desempate pode trocar a REPRESENTANTE do lado perdedor (a testemunha
  do teste de concordância D-074), removendo `regiao`/`cidade` de uma
  herança cuja doadora escolhida, Δt e `hora_incerta` não mudaram —
  mecanismo latente achado por fuzz (80.000 cenários sintéticos, 616
  com esse padrão), zero no catálogo real.
- Como reverter: remover `gps_direto_do_arquivo` de `FotoRef`
  (`grouping/correlacao.py`) e o parâmetro volta a `True` sempre,
  equivalente a apagar o bloco de desempate em `procurar`; `_correlacionar`
  perde a consulta a `Source.tipo`. Nada persistido depende disso — GPS
  herdado nunca é gravado como se fosse próprio, e o EXIF do arquivo
  original não é tocado por este mecanismo.
- Status: decidido pelo dono; a primeira implementação tinha um bug de
  prioridade (fonte antes de hora) achado pela revisão com olhos
  frescos e corrigido antes do commit — a medição inicial que a
  aprovou também estava incompleta e foi refeita com o cascade real.
  Implementado e commitado nesta fatia.

---

## D-088 — Justificativa de viagem multi-país cita todas as pernas, não só o país dominante

- Fase: fora do roadmap — achado direto do dono usando o app (não medição
  prévia). Início de um novo foco: suspender o backlog e concentrar
  esforço em robustecer o que já foi entregue, em vez de funcionalidade
  nova.
- Classe: A — corrige texto que o dono leu como classificação errada.
- Contexto: dono relatou "fotos da Holanda sendo classificadas como
  França" numa viagem de 13 dias (03–16/10/2016, pastas `Paris 2016` +
  `Amsterdam 2016`, álbum Apple Fotos "Franca-Holanda"). Investigação via
  `/api/midia/{id}` contra o catálogo real (só leitura): a evidência
  `pais` da foto (campo que diz onde ELA está) já estava correta —
  "Países Baixos". O erro era na evidência `viagem` (e `categoria`, que
  reusa a mesma frase): a justificativa da SESSÃO/VIAGEM inteira dizia
  "fotos com GPS em França ao longo de 13 dias" para QUALQUER foto da
  viagem, inclusive as da perna Holanda — porque
  `fotoorganizer/grouping/classifier.py`, regra 5 da cascata ("estadia
  geocodificada"), usava `pais_dominante` (um único país, o mais
  frequente na viagem inteira) na frase, mesmo quando a viagem já era
  reconhecida como multi-país para efeito de RÓTULO
  (`paises_no_tempo`, usado uma dezena de linhas acima na mesma função
  para nomear "França – Países Baixos").
- Decisão: a frase da regra 5 passa a citar `paises_no_tempo` (join com
  " – ", mesmo separador do rótulo — não " e ": doze nomes canônicos de
  país já contêm " e " no próprio nome — Bósnia e Herzegovina, Trinidad
  e Tobago, São Tomé e Príncipe — e "GPS em Croácia e Bósnia e
  Herzegovina" leria como três destinos, achado da revisão com olhos
  frescos) quando há 2+ pernas; com 1 perna só, comportamento inalterado
  (`pais_dominante` sozinho). Nova função `_paises_em_texto` em
  `classifier.py`. Verificado contra a sessão REAL do dono (1.242 fotos,
  duas pernas acima do `_MIN_FOTOS_PERNA`): frase passa a dizer "fotos
  com GPS em França – Países Baixos ao longo de 14 dias" — a mesma
  frase, agora correta, para qualquer foto da viagem.
- Por quê a foto não recebe uma frase própria dizendo em qual perna ELA
  está: o Inspetor já mostra, ao lado, a evidência `pais` calculada por
  FOTO (que já estava certa) — o par (país da foto + país(es) da viagem)
  já lê coerente sem precisar de uma terceira frase.
- Achados da revisão com olhos frescos, **não corrigidos nesta fatia**
  (pré-existentes, fora do escopo da correção pontual, registrados para
  decisão própria):
  1. `classification/engine.py` (`_evidencias_geo`, passo de vizinhança)
     — foto sem coordenada própria NEM herança dentro da janela recebe
     `pais_dominante` (um só) como evidência de `pais` — não só na
     frase, no VALOR do campo. Hoje as 3.926 linhas desse tipo no
     catálogo real são todas de viagens de um país só (não manifesta o
     bug), mas é o único caminho estrutural por onde uma foto poderia
     mesmo virar "Holanda classificada como França" de verdade (não só
     no texto). Requer decisão: usar `paises_no_tempo` aqui também, ou
     não afirmar país nenhum quando a viagem é multi-país e a foto não
     tem evidência própria.
  2. `classifier.py`, regra 3, segundo ramo (país lido do NOME da pasta)
     — nomeia e justifica com o país da pasta mesmo quando o GPS de toda
     a sessão contradiz. Caso real encontrado: 35 fotos de 14/06/2015,
     evidência `pais` = "Brasil" nas 35, rotuladas "Chile" por causa da
     pasta "Chile Jun.15". Pode ser comportamento intencional (D-030:
     pasta é palavra do dono, vence dedução) OU pasta digitada errada
     pelo próprio dono — precisa de decisão do dono, não é bug óbvio de
     código.
- Alternativas rejeitadas: nenhuma — correção mínima e direta, sem
  desenho alternativo cogitado.
- Como reverter: `git revert` neste commit; `_paises_em_texto` e o uso de
  `paises_no_tempo` na regra 5 saem, frase volta a citar só
  `pais_dominante`. Nada persistido depende disso além de `Evidence`
  (reescrita a cada `gerar()`; sugestões já decididas mantêm o texto
  antigo até reprocessar — limitação pré-existente do modelo, não desta
  fatia).
- Status: decidido, implementado e commitado. Revisão com olhos frescos
  rodada uma vez, achados aplicados (separador, robustez do teste);
  achados 1 e 2 acima ficam registrados para o dono priorizar.

---

## D-089 — Hemisfério errado na escrita de GPS em XMP (sidecar e direto) — A2 da auditoria

- Fase: fora do roadmap — o dono pediu foco em "consertar o que já
  entregamos" em vez de backlog novo; A2 era o achado mais grave ainda
  aberto da auditoria completa de 2026-09-19 (`docs/reconstrucao/08-ERROS_CONHECIDOS.md`).
- Classe: A — dado geograficamente errado gravável em arquivo real do
  dono, com verificação que aprovava a escrita errada como sucesso.
- Contexto: `ExifToolWriter.escrever()` sempre gravava GPS como
  `-GPSLatitude={abs(lat)}` + `-GPSLatitudeRef={N/S}` (par equivalente de
  longitude) — correto para EXIF binário real (a Ref é a ÚNICA forma de
  o formato guardar hemisfério), mas quando o alvo é um sidecar `.xmp`
  autônomo, `GPSLatitudeRef`/`GPSLongitudeRef` sem prefixo de grupo não
  são graváveis nesse contexto — o exiftool aceita a escrita em silêncio,
  sem efeito, e o valor (sempre positivo) fica gravado como se fosse
  hemisfério norte/leste. `(-22.95, -43.18)` — Rio de Janeiro, sul/oeste
  — virava `"22,57.0N"/"43,10.8E"` no sidecar: um ponto em outro lugar do
  planeta. A verificação de sucesso (`campo_gravado`) só checava
  PRESENÇA da tag, nunca o valor — a escrita errada passava como
  sucesso.
- Medição: zero arquivos reais do dono corrompidos. Cruzei
  `exif_write_items` (nenhum item com `sidecar_destino` chegou a
  `GRAVADO` para `gps`) com o `audit_log` (fonte independente: 115
  linhas `escrita_exif_verificada|ok`, todas com `tags_gravadas`
  idênticas — só cidade/país, nunca GPS, e todos os alvos `.jpg/.JPG`
  diretos, nenhum sidecar criado). O caminho que tinha o bug nunca foi
  de fato executado contra um arquivo do dono; os 2.060 itens `PRONTO`
  com sidecar pendente são exatamente a população que o teria acionado
  na próxima execução.
- Decisão — três correções, uma medição negativa, uma decisão de
  reverter:
  1. `exif_write/writer.py`: sidecar passa a gravar `-GPSLatitude={lat}`/
     `-GPSLongitude={lon}` (valor ASSINADO, sem Ref) — a XMP aceita o
     hemisfério embutido na própria string ("22,57.0S"). Verificado
     contra o exiftool real (13.55) nos quatro hemisférios e no caso
     Δ=0 (equador/Greenwich).
  2. `exif_write/verificacao.py`: nova `gps_valor_correto(lat_lon, diff,
     sidecar)` — confere o par GRAVADO contra o PEDIDO (reconstruindo
     sinal do Ref no caminho direto), não só presença. Falha FECHADA
     numa Ref fora de `{N,S}`/`{E,W}` — não assume positivo por padrão
     na própria dimensão que existe para proteger. `exif_write/executor.py`
     chama essa checagem a mais para `gps`, com mensagem de motivo
     distinta de "rejeitado pelo exiftool" (que seria factualmente
     errada — o exiftool aceitou, o app que recusou o resultado).
  3. **Achado da revisão com olhos frescos, mais sério que o original**:
     o mesmo bug existia no caminho DIRETO, de um jeito pior — quando o
     arquivo já tem GPS gravado só em `XMP-exif:` (comum em foto que
     passou por Lightroom/Aftershoot, sem nenhuma tag do grupo binário
     `GPS:`), `-GPSLatitude=` sem prefixo de grupo é ambíguo: o exiftool
     resolvia para o grupo XMP já existente (em vez de criar um bloco
     EXIF binário novo) e SOBRESCREVIA a coordenada real com hemisfério
     errado — sem backup (não é a primeira escrita do bloco) e aprovado
     por todas as verificações, incluinda a nova do item 2. Corrigido em
     duas camadas: `_campo_ja_preenchido` (`executor.py`) passa a
     reconhecer `XMP-exif:GPSLatitude`/`GPSLongitude` como "campo já
     preenchido" também no caminho direto (bloqueia a escrita na
     origem — é a checagem AO VIVO que decide `PULADO`, e depois desta
     correção é a ÚNICA proteção que resta nesse caminho, ver item 4);
     `writer.py` passa a gravar o caminho direto com prefixo de grupo
     explícito (`-GPS:GPSLatitude=`, mesma convenção de `verificacao.py`)
     — defesa em profundidade, verificado contra o exiftool real que
     isso cria um bloco EXIF binário novo sem tocar no XMP pré-existente.
  4. **Cogitado e REVERTIDO**: fechar o ponto cego do CATÁLOGO (o
     leitor, `metadata/exiftool.py`, só lê `Composite:GPSLatitude`, que
     o exiftool não sintetiza quando o GPS mora só em XMP — a foto
     entra como "sem GPS", vira alvo de herança e não passa pela guarda
     de `gps_direto_do_arquivo`, D-087) com um fallback para
     `XMP:GPSLatitude`/`GPSLongitude` bruto. Verificado contra o
     exiftool real que o fallback FUNCIONAVA para XMP embutido de
     terceiro — mas `_fundir_sidecar` mistura, na MESMA chave, o pacote
     de um editor de terceiro E o sidecar que o PRÓPRIO app escreve a
     partir de uma coordenada ESTIMADA/HERDADA (`exif_write/writer.py`).
     Sem marca de proveniência no sidecar, o fallback lia de volta a
     PRÓPRIA estimativa do app como se fosse GPS medido — derrotando por
     dentro exatamente a distinção que `gps_direto_do_arquivo` (D-087)
     existe para proteger, e inflando a herança em cadeia sem nenhuma
     evidência real por trás. Revertido: o leitor continua só com
     `Composite:GPSLatitude`/`GPSLongitude` — subestimar GPS (foto com
     GPS só em XMP embutido de terceiro entra como "sem GPS") é a
     direção segura do erro; superestimar (estimativa lida como
     medição) não é. Corrigir isso direito pede distinguir "sidecar de
     terceiro" de "sidecar que o app gerou" — marca no pacote na escrita,
     ou cruzar com `exif_write_items.sidecar_destino` — fora do escopo
     desta fatia, registrado para o futuro.
- Por quê os itens 1-3 e não o item 4: os três primeiros fecham risco de
  ESCRITA ERRADA em arquivo real (a categoria de dano que A2 nomeou); o
  item 4 era uma melhoria de CATALOGAÇÃO (a foto aparecer com lugar no
  mapa), que por sua vez abriu um risco novo pior que o que resolvia. A
  régua do dono para esta fase ("consertar o que já entregamos") favorece
  fechar o buraco medido, não abrir um novo maior atrás dele.
- Quatro rodadas de revisão com olhos frescos (mesmo agente, resumido
  via SendMessage): a 1ª confirmou o writer/verificação/executor
  corretos; a 2ª achou o crítico do caminho direto (writer.py) e dois
  altos (`_campo_ja_preenchido`, o leitor) que a 1ª rodada não tinha
  pedido para olhar; a 3ª confirmou o crítico fechado nos dois níveis e
  achou o problema novo do item 4 (fallback do leitor lavando
  estimativa); a 4ª confirmou a reversão limpa e achou um comentário
  desatualizado (corrigido nesta versão) mais esta entrada faltando (o
  próprio D-089, agora escrito).
- Achados menores, registrados sem correção: `hash_pre`/`hash_pos`
  gravados em `ExifWriteItem` mas nunca comparados neste módulo
  (diferente de `operations/executor.py`, que compara) — fora do tema
  GPS especificamente; `scripts/testar_escrita_exif.py` (gate de
  aprovação de formato) continua usando só `campo_gravado`, sem
  `gps_valor_correto` nem `sidecar=` — script standalone, não caminho de
  produção; um sidecar `.xmp` cuja escrita reprove por
  `gps_valor_correto` fica no disco (arquivo novo, sem `_original` para
  restaurar) e planos futuros recusam mexer nele — praticamente
  inalcançável depois do item 3 (a escrita nem é mais tentada quando já
  tinha XMP), mas não impossível por desenho; `_campo_ja_preenchido`
  exige os DOIS (`lat` e `lon`) presentes no fallback XMP do caminho
  direto — um XMP corrompido/parcial (só latitude) não bloqueia a
  escrita, hoje inofensivo porque o writer já usa `-GPS:` explícito
  (resulta num bloco EXIF novo ao lado de uma tag órfã, não sobrescrita).
- Como reverter: os itens 1-3 são independentes e reversíveis
  separadamente — `git revert` neste commit desfaz os três juntos; nada
  persistido depende disso (GPS herdado nunca é gravado como se fosse
  próprio, e a escrita em arquivo original segue o mesmo rigor de
  dry-run/hash/audit log de sempre, invariante 7 do CLAUDE.md).
- Status: decidido, implementado e commitado. Zero arquivos reais
  afetados — a correção fechou uma janela antes dela ser usada contra o
  acervo do dono.

## D-090 — Corrida no JobManager (check-then-act sem lock) — A1 da auditoria

- Fase: continuação de "consertar o que já entregamos" (mesma decisão de
  escopo de D-085 a D-089), autônoma, autorizada pelo dono para rodar
  durante a noite.
- Achado original (auditoria 2026-09-19, severidade ALTO): `ocupado()` (o
  check) e a criação/partida da thread do job (o act), em
  `server/jobs.py`, não eram atômicos — dois POSTs simultâneos (duplo
  clique real, medido 55/200 sem tuning) podiam os dois passar no check
  antes de qualquer um setar `self._thread`, iniciando duas threads sobre
  o mesmo plano. Com escrita EXIF, o exiftool não usa
  `-overwrite_original` de propósito (o backup `_original` é a rede de
  segurança até a verificação aprovar, `exif_write/writer.py`); uma
  segunda chamada do exiftool sobre o mesmo arquivo, antes da primeira
  terminar, renomeia a versão JÁ MODIFICADA por cima do backup — destrói
  a única cópia intacta do original, sem nada para restaurar.
- Investigação (agente Explore, antes da correção) achou uma SEGUNDA
  janela de corrida, independente da primeira, que a sugestão original da
  auditoria ("lock em `_iniciar`") não fechava sozinha:
  `iniciar_execucao`/`iniciar_escrita_exif` criam o `ExecutionControl` e
  gravam `self._exec_control` ANTES de chamar `_iniciar` — um lock só
  dentro de `_iniciar` corrige "duas threads", mas não corrige duas
  chamadas sobrescrevendo `self._exec_control` entre si. Consequência: a
  thread vencedora roda com o `ExecutionControl` que ela recebeu por
  parâmetro (closure), mas `cancelar()` lê `self._exec_control` do campo
  — se uma chamada perdedora foi a última a escrever ali, `cancelar()`
  vira no-op silencioso (o botão "Cancelar" para de funcionar, sem erro
  visível).
- Correção: `self._lock` virou `threading.RLock()` (era `Lock()`
  simples), e o corpo inteiro de `_iniciar`, `iniciar_execucao` e
  `iniciar_escrita_exif` passou a rodar sob `with self._lock:` — do check
  `ocupado()` até `self._thread.start()`, incluindo a criação do
  `ExecutionControl`. RLock (não Lock) porque `iniciar_execucao`/
  `iniciar_escrita_exif` seguram o lock e chamam `_iniciar`, que também o
  adquire — mesma thread, reentrante. `_iniciar` continua com seu próprio
  check interno (agora redundante para essas duas rotas, necessário para
  as outras seis que chamam `_iniciar` direto).
- Verificação: teste de estresse (não revisão por diff — corrida não se
  vê num diff), `tests/test_jobs_concorrencia.py`. Duas provas: (1) N=50
  chamadas a `_iniciar` soltas pela mesma `threading.Barrier` — sem o
  fix, reproduziu 2 a 5 threads iniciadas em 3/3 rodadas; com o fix,
  exatamente 1 em 5/5 rodadas. (2) N=30 chamadas a `iniciar_execucao`
  soltas pela mesma barreira, com `_rodar_execucao` substituído por um
  stub que registra o `ExecutionControl` recebido — sem o fix, mais de um
  controle "visto" (thread real rodando com um controle diferente do que
  ficou em `self._exec_control`); com o fix, sempre exatamente 1, e
  `self._exec_control is controles_vistos[0]`.
- Escopo deixado de fora, mesma causa raiz, correlato: `self._control`
  (o `ScanControl` do scan/reconciliação, distinto de
  `ExecutionControl`) é reatribuído em `_iniciar` e lido diretamente do
  atributo de instância em `_rodar_scan`/`_rodar_reconciliacao`, em vez
  de receber por parâmetro/closure como `_rodar_execucao`/
  `_rodar_escrita_exif` fazem — mesma classe de risco (controle
  trocado sob corrida) se duas chamadas a `iniciar_scan`/
  `iniciar_reconciliacao` colidirem. Não corrigido nesta fatia: o achado
  original (A1) e o pedido do dono eram sobre escrita EXIF/execução de
  plano; scan/reconciliação têm proteção adicional de UI (não expostos a
  duplo clique do mesmo jeito) e ficam para decisão separada.
- Como reverter: `git revert` neste commit — mudança contida a
  `server/jobs.py` (lock) e ao teste novo; nenhum dado persistido
  depende disso.
- Status: decidido, implementado e commitado.

## D-091 — Correção manual de localização no Inspector

- Fase: continuação de "consertar o que já entregamos", autônoma,
  autorizada pelo dono para rodar durante a noite — o pedido original
  desta sessão inteira ("não vi uma forma de avisar do erro ou tentar
  consertar" a localização no Inspetor), investigado, adiado enquanto
  D-085 a D-090 resolviam bugs concretos de localização, e retomado
  agora como o terceiro item de três.
- Lacuna confirmada por investigação (antes de implementar): não existia
  NENHUM campo de override de usuário para localização — `tipo_imagem`
  já tinha `tipo_confirmado` (0007), país/região/cidade não tinham
  equivalente. Cascata geo (`_evidencias_geo`) e `_pais_efetivo`
  (tz_estimado, CR-01) recalculam do zero a cada `gerar()`; uma correção
  manual seria desfeita em silêncio na próxima regeneração, exatamente
  como `tipo_imagem` era antes de 0007.
- Desenho: mesmo padrão de `tipo_confirmado`, replicado em TRÊS campos
  independentes (`pais_confirmado`, `regiao_confirmado`,
  `cidade_confirmado` — migração 0022) porque, ao contrário de tipo
  (valor único, lista fechada), lugar tem três granularidades e o
  usuário pode só querer corrigir uma. Não entra em `Location`: essa
  tabela é cache POR COORDENADA (~110m), compartilhada por todas as
  fotos que caem no mesmo bucket — gravar a correção lá vazaria para
  fotos de outro momento que só coincidem no mesmo lugar.
- Quatro camadas tocadas, todas com o MESMO gancho no topo ("usuário
  manda, cascata não decide"), porque a investigação achou três
  consumidores independentes de geo, não um:
  1. `classification/engine.py::_evidencias_geo` — evidência/sugestão.
     Confirmar QUALQUER campo bloqueia a cascata geo INTEIRA (não só o
     campo confirmado) — evita misturar uma correção com um palpite não
     confirmado no mesmo destino.
  2. `classification/engine.py::_pais_efetivo` — sem isto, `tz_estimado`
     continuaria vindo da cascata antiga mesmo com o país corrigido na
     tela; o fuso gravado divergiria silenciosamente do que o Inspetor
     mostra.
  3. `exif_write/planner.py` — sem isto, a correção do usuário nunca
     chegaria ao EXIF gravado no arquivo original: a tela mostraria uma
     coisa, o arquivo gravaria outra. Ao contrário do valor inferido, o
     confirmado ignora as guardas de granularidade/Δt/pela_pasta (elas
     existem para não escrever um PALPITE fraco, não para desconfiar de
     uma correção explícita) e abre candidatura mesmo sem GPS/Location
     nenhum (usuário pode digitar o lugar de próprio punho).
  4. `server/app.py::detalhe_midia` — o bloco `"local"` da resposta
     precisa mostrar a correção, não só a cascata; se só o motor
     soubesse, o Inspetor continuaria exibindo o valor errado até a
     próxima geração de sugestões.
- API: `POST /api/midia/{id}/local` (espelha `/tipo`) — full-replace
  nos três campos, não parcial (`LocalBody`, os três `None` devolve tudo
  à cascata). Decisão explícita: parcial exigiria distinguir "campo
  omitido" de "campo null" no corpo, ambiguidade que o padrão de
  `tipo_confirmado` (um campo só) nunca precisou resolver; full-replace
  empurra a responsabilidade pro cliente, que já tem os três valores
  atuais em mãos (veio do GET) — mais simples e sem estado ambíguo no
  servidor.
- UI: componente novo `LocalizacaoDaImagem` no Inspector, logo abaixo de
  `TipoDaImagem` (mesma posição relativa, mesmo padrão de mutação/
  invalidação de query) — três campos de texto livre, "Salvar"/
  "Cancelar" quando editando, "corrigido por você" + "desfazer"/"editar"
  quando já confirmado, "lugar errado? corrigir" caso contrário. Sem
  dropdown/enum: país/cidade são texto livre, ao contrário do tipo
  (lista fechada).
- Verificado: 5 testes de motor (`test_suggestion_engine.py`, cascata
  geo + tz_estimado sobrevivem a regeneração, campo confirmado sozinho
  não inventa os outros dois), 2 de planner
  (`test_exif_write_planner.py`, confirmado vence Location e abre
  candidatura sem GPS), 1 de API (`test_server_api.py`) e 5 de UI
  (`Inspector.test.tsx`) — 1103 testes Python / 192 vitest, tudo verde
  (mesmos 3 falhas + 23 erros de sandbox pré-existentes, documentados
  desde a auditoria). Provado na UI real contra o catálogo do dono
  (servidor local, build de produção do webapp): abri uma foto do
  acervo real, corrigi cidade para um valor de teste, confirmei que
  "Lugar" e a badge "corrigido por você" atualizaram, e desfiz — o
  catálogo real volta ao estado original, nenhum resíduo de teste
  ficou gravado.
- Status: decidido, implementado, verificado na UI real, commitado.

## D-092 — Limpeza de sugestões antigas em lote, não item a item

- Fase: continuação de "consertar o que já entregamos", autônoma,
  autorizada pelo dono para rodar durante a noite — terceiro dos três
  itens pedidos ("_persistir_sugestao é o gargalo de verdade", medido
  pela revisão do cache do LocationResolver da mesma noite).
- Achado: `_persistir_sugestao` limpava a sugestão PENDENTE antiga e as
  evidências de CADA mídia individualmente (SELECT + 2 DELETE, dentro do
  laço principal de `gerar()`, ×55 mil numa regeneração real) — e um
  `session.flush()` explícito ao final da limpeza. Medido num catálogo
  sintético de 8k mídias (mesmo banco, antes/depois de cada mudança):
  - Remover só o `flush()` explícito (deixando o autoflush do
    SQLAlchemy cobrir): ~15s → ~15s. Dentro do ruído, sem ganho real —
    o autoflush do próximo SELECT já fazia o mesmo trabalho, só
    adiado. Mantido de qualquer forma (não piora, simplifica), mas não
    é a correção.
  - A causa real: cada SELECT de "sugestão antiga desta mídia" também
    disparava autoflush de TODO o lote ainda pendente de commit — o
    item 500 de um lote de 500 forçava flush dos 499 anteriores só
    para rodar uma consulta trivial que quase sempre voltava vazia.
- Correção: `_limpar_sugestoes_antigas` (staticmethod novo) apaga em
  BLOCO a sugestão pendente antiga e as evidências de um lote inteiro
  (3 DELETEs cobrindo até 500 media_ids via `IN`, bem abaixo do teto de
  variáveis do SQLite), chamada UMA VEZ por lote, ANTES do laço que
  gera e persiste as sugestões novas desse mesmo lote — não mais dentro
  de `_persistir_sugestao`, que agora só insere. `gerar()` passa a
  iterar em fatias de `_TAMANHO_LOTE` (=500, mesmo número do commit de
  sempre) via `range()`, em vez de contador `% 500`. Medido: regeneração
  de 8k caiu de ~15s para ~3,9s (~4x) — bem acima do que os DELETEs em
  si explicariam; o ganho real é evitar o autoflush em cascata dentro
  do lote.
- Risco considerado e descartado: limpar tudo de uma vez, no início de
  `gerar()` inteiro (antes do laço), em vez de por lote — pareceria a
  otimização mais óbvia, mas troca a garantia de resumo por velocidade:
  o bulk-delete cedo ficaria durável no PRIMEIRO commit, e uma queda
  no meio da rodada deixaria toda mídia AINDA NÃO alcançada sem
  sugestão nenhuma (hoje: mantém a antiga). Real nesta mesma sessão —
  o processo anterior foi interrompido de propósito (SIGKILL) porque
  travava o servidor inteiro. Por lote (não a rodada inteira) preserva
  exatamente a granularidade de resumo de hoje: só o lote em voo
  (≤500) se perde numa queda; os não alcançados mantêm a sugestão
  antiga intacta.
- Verificado: 2 testes novos (`test_suggestion_engine_lote.py`) — N >
  2×`_TAMANHO_LOTE` atravessa a fronteira do lote sem perder/duplicar
  mídia; uma exceção simulada no início do 2º lote deixa o 1º lote
  novo (commitado) e o 2º INTACTO (mesma linha, não apagada) — prova
  direta da garantia de resumo acima. Suíte completa (1103 Python / 192
  vitest) verde, mesmos artefatos de sandbox de sempre.
- Escopo deixado de fora: bulk-delete cedo (acima) foi cogitado e
  descartado por risco, não implementado de forma alguma — não há
  vestígio dele no código.
- Como reverter: `git revert` neste commit — muda só a forma de limpar
  (SQL, não semântica); estado final de `suggestions`/`evidence` é
  idêntico ao código anterior para o mesmo input.
- Status: decidido, implementado, testado, commitado.
- Addendum — verificação diferencial contra o catálogo real (rodou em
  paralelo, terminou depois do commit): `gerar()` executado duas vezes
  em cópias descartáveis (102.251 mídias reais), uma com o código
  anterior (`c28ed5c`), outra com este. Resultado: **zero divergência**
  — `suggestions`/`evidence`/`suggestion_evidence`/`trips`/`events` e os
  campos que `gerar()` grava em `media_files` batem por hash, incluindo
  os IDS ABSOLUTOS (o delete/insert em lote não deslocou o autoincrement
  na mesma sequência que o código antigo). Tempo real (máquina sob
  carga concorrente): 1415,95s → 771,28s (1,84x — menor que o 4x do
  benchmark sintético, esperado: no catálogo real o preâmbulo de
  `gerar()` — correlação de GPS, sessões — é custo fixo grande que este
  fix não tocou; só o laço de persistência encurtou). Achado da revisão,
  incorporado: comentário em `_limpar_sugestoes_antigas` documentando o
  acoplamento latente (a limpeza em lote assume que `_persistir_sugestao`
  só grava evidência da PRÓPRIA mídia — verdade hoje, mas não garantida
  pelo tipo).

## D-093 — `useJob` fica "rodando" desde o clique, não só depois do POST responder

- Fase: item deixado de fora de D-090 (A1) por escopo — a análise de
  backlog desta sessão (2026-09-22) achou e o dono aprovou implementar.
- Lacuna: o lock de `JobManager` (D-090) fecha a corrida no SERVIDOR, mas
  `useJob.rodando` (`webapp/src/hooks/useJob.ts`) só refletia
  `estado.status === "rodando"` — que só é gravado DEPOIS que a promise
  do `fetch` resolve. Todo botão com `disabled={!podeX || job.rodando}`
  (`EscritaExif.tsx`, `Operations.tsx`) ficava sem proteção nenhuma na
  janela entre o clique e a resposta — exatamente a janela que o duplo
  clique real explora. Com D-090 já corrigido no servidor, o pior caso
  virou "409 tratado, ruidoso" em vez de "duas threads reais", mas a
  lacuna do cliente continuava real.
- Correção: `disparar()` (a função única por trás de TODOS os disparos de
  job — scan, importação, gerar sugestões, detectar duplicatas, executar
  plano, executar escrita EXIF, pausar, continuar) grava um estado
  `disparando` síncrono no início, libera em `finally` (cobre o caminho
  de erro — `pausar`/`continuar` engolem 409 sem chamar `setEstado`).
  `rodando` vira `estado.status === "rodando" || disparando`. Um lugar
  só, todos os botões que já checavam `job.rodando` ganham a proteção de
  graça — não precisou tocar `EscritaExif.tsx` nem `Operations.tsx`.
- Verificado: 2 testes novos em `useJob.test.tsx` — `rodando` vira `true`
  no instante do clique (antes do `await` da promise resolver, via
  `act()` síncrono) e continua `false` depois de um POST que falha (prova
  do `finally`). Suíte completa (194 vitest, `tsc -b` limpo) verde.
- Status: decidido, implementado, testado, commitado.

## D-094 — Caminho absoluto de pasta nunca sai da máquina: só o nome curto que a tela mostra

- Fase: item 2 da análise de backlog de 2026-09-22 (M2 da auditoria de
  2026-09-19, severidade média), aprovado pelo dono.
- Achado: os dois envios à API da Anthropic levavam `MediaFile.pasta`
  INTEIRO — `server/genai_pasta.py::_payloads` (classificação de pasta por
  GenAI, `PastaPayload.pasta`) e `classification/engine.py::_consultar_advisor`
  (advisor de cluster, `ClusterInfo.pastas`). Isso inclui nome de usuário
  (`/Users/acamerini`), nome de volume/NAS (`/Volumes/photo`) e a árvore
  inteira do acervo. Enquanto isso, `PRIVACIDADE.md`, o cabeçalho de
  `location_advisor.py`, D-081 e a própria tela (`pastaCurta()` em
  `ClassificacaoPasta.tsx`, que mostra só as duas últimas pastas)
  prometiam "nome da pasta". O teste-prova
  (`test_payload_nunca_envia_imagem`) não pegava porque monta o
  `PastaPayload` à mão com um nome curto — o vazamento era na camada de
  cima. Violação real do invariante 4 (minimização de dados), não só
  documentação desatualizada. `lexico.py` (3º chamador) envia nomes de
  segmento, não caminhos — mas `scripts/classificar_nomes.py` oferecia
  CADA segmento do caminho absoluto ao filtro `nome_de_album`, e
  "Externo"/"acamerini" passam nele (achado da revisão); corrigido para
  iterar só `segmentos_uteis(pasta)`.
- Decisão: um helper único, `classification/pasta_curta.py` —
  `nome_curto(pasta)` = as duas últimas pastas do caminho, sem barra
  inicial, o MESMO recorte de `pastaCurta()` na UI ("o que é mostrado é o
  que é enviado"); `nomes_curtos_unicos(pastas)` desempata colisão
  (`/a/2015/Fotos` × `/b/2015/Fotos`) com um segmento a mais só para quem
  colide. Colisão importa porque a resposta do modelo é casada de volta
  pelo nome enviado — sem desempate, uma proposta iria para a pasta
  errada. Alternativa cogitada e descartada: caminho relativo à raiz da
  fonte (mais contexto para o modelo, ex. `Viagens/2016 - Franca-Holanda/
  Amsterdam`) — descartada porque a UI mostraria menos do que é enviado,
  exatamente a classe de problema que M2 nomeia; e a cascata determinística
  já consome a raiz de categoria (`Viagens/`) antes de a pasta virar
  candidata de GenAI.
- Implementação: `_payloads` devolve também `{curto: absoluto}` e `rodar()`
  traduz a resposta de volta — banco (`pasta_classificacoes`), propostas e
  `pastas_sem_resposta` continuam na chave local de sempre; nome ecoado que
  não estava no pedido é ignorado. `candidatas()` calcula os nomes curtos
  sobre a lista INTEIRA, o mesmo conjunto que `_payloads` usa, e devolve
  `pasta_enviada` por candidata; a lista da UI passa a mostrar esse campo
  (caminho absoluto só no tooltip). `scripts/medir_score_llm_pasta.py`
  passa a montar o payload com o mesmo recorte (senão mediria uma entrada
  que a produção não envia — o 0,55 preliminar de D-081 foi medido com o
  caminho absoluto, isto é, com MAIS contexto do que o modelo vê agora;
  remedir antes de travar o score).
- Verificado: `test_pasta_curta.py` (recorte, sem usuário/volume, colisão,
  caminho irredutível), `test_api_genai_pasta.py` (classificador injetado
  recebe só `Viagens/Peru 2023`; candidatas/propostas/pendentes respondem
  pelo absoluto; nome não pedido vira `pastas_sem_resposta`),
  `test_suggestion_engine.py` (advisor de cluster nunca vê `/Users`),
  termos `users/` e `volumes/` na lista de proibidos do teste-prova de
  privacidade. Suítes Python e vitest completas verdes.
- Revisão com olhos frescos (opus, diff isolado), incorporada antes do
  commit: (1) caminho RASO vazava volume/usuário mesmo com o recorte —
  `/Volumes/Externo/Estrada Real` (caso real, 2.624 fotos) virava
  `Externo/Estrada Real`; agora `segmentos_uteis()` corta a raiz de
  infraestrutura (`Users`/`Volumes`/`home`) e o segmento seguinte ANTES
  do recorte. (2) No advisor de cluster a desambiguação escalava
  segmentos à toa (cópia local + NAS da mesma foto caem no mesmo cluster
  → subia até o caminho inteiro); lá não há resposta a casar, então usa
  `nome_curto` direto. (3) Barra invertida é nome válido no macOS e eu a
  normalizava como separador — fundia `Fotos\2016` com `Fotos/2016` numa
  colisão inexistente; só `/` separa agora. (4) Colisão irredutível
  (barra final, raiz de dois volumes) deixava a última pasta sobrescrever
  a outra no mapa de volta; `nomes_curtos_unicos` agora garante
  injetividade com sufixo ` (2)`. (5) `scripts/medir_qualidade_advisor.py`
  ainda montava `ClusterInfo.pastas` absoluto — corrigido. (6) Os
  proibidos `/users/` nunca casariam (nome curto não começa com barra) —
  virou `users/`. Aceito sem correção: a revisão do passo 4 da UI ainda
  usa `pastaCurta(absoluto)` com `…/` (duas colisões aparecem iguais lá —
  é tela pós-chamada, nada sai da máquina por ela); e a garantia "mostrado
  = enviado" depende de dois snapshots (candidatas no passo 1, payload no
  rodar) — uma candidata nova que colida no intervalo faz sair um segmento
  a mais do que o dono viu, sem quebrar o casamento de volta.
- Status: decidido, implementado, testado, commitado.

## D-095 — Timeout na escrita EXIF e plano de escrita órfão reconciliado no boot

- Fase: item 3 da análise de backlog de 2026-09-22 (B13 e item 10 de
  `docs/reconstrucao/09-MELHORIAS.md`, auditoria de 2026-09-19), aprovado
  pelo dono.
- Achado 1: `ExifToolWriter.escrever()` chamava `subprocess.run` sem
  `timeout`. O exiftool reescreve o arquivo inteiro; num NAS via SMB que
  some no meio da escrita (caso real do acervo: `/Volumes/photo` é
  smbfs), o processo ficava pendurado e o job de escrita inteiro com ele —
  sem sinal nenhum na UI, sem como cancelar (o cancelamento é cooperativo
  entre itens). O leitor (`verificacao.py`) já tinha 30 s.
- Achado 2, descoberto ao corrigir o 1: `subprocess.TimeoutExpired` NÃO é
  `OSError`. Só adicionar o timeout faria a exceção atravessar
  `_executar_item` (que só capturava `OSError`), derrubar `executar()` e
  deixar o plano preso em EXECUTANDO — exatamente o órfão do achado 3.
- Achado 3: só o fim feliz, o cancelamento ou o erro escrevem o status
  final do plano. App fechado ou Mac desligado no meio deixava o plano
  EXECUTANDO para sempre e a tela mentindo sobre trabalho em curso — o
  scan já tinha reconciliação no boot (`scanner.reconciliar_orfas` →
  INTERROMPIDO); a escrita EXIF não.
- Decisão: (1) `TIMEOUT_ESCRITA_S = 120` no writer (RAW de dezenas de MB
  em SMB leva segundos; um volume que sumiu não pode levar para sempre),
  parâmetro `timeout` em `escrever()`. (2) No executor, `TimeoutExpired`
  é capturado NO ITEM: campos tentados viram FALHA com motivo "exiftool
  não respondeu em Ns e foi encerrado", `hash_pos` é medido e o item diz
  se o original está "intacto" ou "ALTERADO", aponta o `_original` e o
  `_exiftool_tmp` que o exiftool tenha deixado — e não apaga NADA
  (invariante 8: quem restaura é o dono). Auditoria `resultado="timeout"`
  com `original_alterado`, `backup`, `temporario`. O plano segue para o
  próximo item e fecha em ERRO. `except OSError` do item vira
  `except (OSError, SubprocessError)`. (3) `ExifWriteStatus.INTERROMPIDA`
  novo; `exif_write/reconciliacao.py::reconciliar_planos_orfaos` carimba
  todo EXECUTANDO no boot (hook de startup em `server/app.py`, ao lado
  do de scan) com auditoria `execucao_exif_interrompida` e
  `itens_restantes`. Rerodar retoma: a execução já reconfere ao vivo,
  item a item, o que está gravado. Migração 0023 alarga o
  `Enum(native_enum=False)` da coluna `status` (o nome mais longo era
  EXECUTANDO, 10; INTERROMPIDA tem 12 — SQLite não impõe, mas o schema
  declarado ficaria mentindo e um Postgres futuro recusaria); downgrade
  converte INTERROMPIDA→ERRO antes de estreitar.
- Verificado: writer com "binário" que só dorme (`sleep 5`, timeout 0,3
  s → `TimeoutExpired` em < 3 s, sem exiftool); executor com dublê que
  estoura só para `limpa.jpg` — o outro item do plano é gravado
  normalmente (prova que o plano CONTINUA), original intacto sem backup
  sobrando, plano em ERRO (não EXECUTANDO), auditoria `timeout`; pior
  caso simulado (escrita real acontece e SÓ ENTÃO o processo é dado como
  travado): item diz "original ALTERADO", `backup_original` aponta o
  `_original`, que continua no disco; reconciliação unitária
  (EXECUTANDO→INTERROMPIDA, idempotente, plano concluído não é tocado,
  auditoria com `itens_restantes` correto) e no boot real via TestClient
  (API devolve `"interrompida"` e `executavel: true` — o botão Gravar
  continua liberado para retomar). Suíte completa: 1121 Python, mesmos
  artefatos de sandbox de sempre.
- Revisão com olhos frescos (opus, diff isolado; scripts de reprodução
  contra o exiftool real), incorporada antes do commit: (1) `run(timeout=)`
  mata com SIGKILL, que pula o handler de SIGINT do próprio exiftool — quem
  apaga o `<alvo>_exiftool_tmp`. O temporário parcial deixado bloqueia
  TODA escrita futura naquele arquivo ("Temporary file already exists") e
  o item passaria a falhar para sempre como "valor rejeitado" sem dizer
  por quê; no sidecar sobra um `.xmp` truncado que vira "já existe" em
  todo dry-run seguinte. Correção: `Popen` + `communicate(timeout)` →
  SIGINT → folga de 5 s → SIGKILL (`writer._executar`); no executor, o
  temporário e o sidecar parcial que comprovadamente nasceram DESTA
  escrita (temporário: não existia antes; sidecar: a guarda do topo já
  recusaria se existisse) são removidos — nunca o original nem o
  `_original`; e o `stderr` do exiftool entra na auditoria das falhas.
  (2) Morto entre os dois renames, o alvo não existe e o item dizia
  "original intacto" (hash não lido → `alterado=False`) — fato falso na
  auditoria (invariante 3). Agora quatro estados: intacto / alterado /
  AUSENTE (com instrução de restaurar do `_original`) / não conferido.
  (3) `verificacao.dump` devolve `{}` em falha/timeout de leitura e a
  reconferência ao vivo lia isso como "tudo vazio" — escrevia por cima de
  campo preenchido (a verificação pegava, com backup, mas era uma escrita
  a mais no original). Guarda nova: `{}` em arquivo existente é "não
  conferido — nada gravado". (4) A reconciliação no boot passa a apontar
  o item que estava em voo (determinístico: primeiro pendente por id) e
  os `_original`/temporário que ficaram ao lado dele — a retomada veria o
  campo "já preenchido" e pularia sem nunca apontar o backup órfão.
  (5) Mutantes que sobreviviam ganharam teste: `except` sem
  `SubprocessError`, timeout padrão não passado, migração 0023 ausente
  ou sem o `UPDATE` do downgrade. Aceito sem correção, registrado: dois
  servidores no mesmo catálogo (o `launch.json` tem cinco entradas) fazem
  o segundo carimbar INTERROMPIDA num plano vivo no primeiro — o mesmo
  furo do precedente do scan; correção é lock de instância no catálogo,
  decisão separada. E depois do `kill()`, `wait()` sem teto: um filho preso
  em I/O não interrompível num SMB pendurado não morre — limite do SO, não
  do app.
- Fora desta fatia, mesma família: `operations/executor.py` (cópia física)
  tem o MESMO órfão EXECUTANDO sem reconciliação no boot (D-069 Tier 3,
  item 6 de 09-MELHORIAS) — decisão separada, porque `OperationStatus`
  precisaria do mesmo membro novo e a tela de Operações tem mapa de cores
  por status.
- Status: decidido, implementado, testado, commitado.

## D-096 — CI mínimo: GitHub Actions roda `scripts/verificar.sh` com exiftool

- Fase: item 4 (último) da análise de backlog de 2026-09-22 (M6 de
  `docs/reconstrucao/08-ERROS_CONHECIDOS.md`), aprovado pelo dono depois de
  D-093/D-094/D-095.
- Achado: sem `.github/workflows`, todo teste marcado `@tem_exiftool`
  (`skipif(not ExifToolExtractor.disponivel())` — `test_exif_write_executor.py`,
  `test_exif_write_writer.py`, `test_exif_write_cancelamento.py`,
  `test_exiftool_extractor.py`) passava verde sem executar em qualquer
  ambiente sem o binário — inclusive o caminho mais perigoso do projeto
  (escrita real em arquivo, D-075). Rodar `scripts/verificar.sh` era 100%
  manual, disciplina do dono, sem rede de segurança em push/PR.
- Correção: `.github/workflows/ci.yml`, um job só (`ubuntu-latest`,
  Python 3.12, Node 20), `apt-get install libimage-exiftool-perl`,
  `.venv` criado do zero com `pip install -e ".[dev]"` (mesmo contrato de
  `scripts/instalar.sh` — CI e local nunca divergem sobre o que
  `verificar.sh` espera encontrar), `npm ci` em `webapp/`, e então
  `scripts/verificar.sh` sem `--rapido` (a UI é o entregável — build e
  vitest quebrados são fatia quebrada, não só o motor Python). `ubuntu`
  em vez de `macos`: a suíte não tem nada específico de macOS (osxphotos
  é lazy-import, gated por `pytest.importorskip`), e o runner Linux é uma
  fração do custo/tempo de minutos do runner macOS hospedado.
- Achado colateral (só apareceu rodando a suíte num venv limpo com
  `[dev]`, sem o extra opcional `[apple]` — exatamente o ambiente que o
  CI cria): `test_video_entra_junto_com_a_foto`
  (`tests/test_apple_photos.py`) fazia `import osxphotos` cru, com um
  comentário prometendo "pulado abaixo se ausente" que nunca existiu —
  sem o pacote instalado, `ModuleNotFoundError` virava FALHA, não skip.
  Todo dev local que já tinha `osxphotos` (via `--llm`/`--apple` alguma
  vez) nunca via isso. Corrigido com o mesmo `pytest.importorskip` que o
  teste vizinho (`test_biblioteca_inacessivel_da_erro_claro`) já usava —
  sem isso, o primeiro run do CI nasceria vermelho por um motivo alheio
  ao objetivo da fatia.
- Verificado: `pip install -e ".[dev]"` e a suíte completa (1156 passed +
  2 skipped de 1158 coletados) rodados de ponta a ponta num venv novo,
  isolado do `.venv` do projeto (que já tinha `osxphotos`/`anthropic`
  instalados e mascararia o achado colateral); os mesmos 2 testes
  voltaram a rodar de verdade (não skip) quando reexecutados no `.venv`
  real, com `osxphotos` presente (1158 passed/0 skipped) — a guarda não
  esconde o caminho feliz. `scripts/verificar.sh` completo (sem
  `--rapido`) local: 1158 pytest + 195 vitest + build, verde.
- Fora desta fatia, registrado: `rawpy`/`pillow-heif` resolvem limpo em
  wheel macOS/arm64 nesta verificação; o CI real em `ubuntu-latest`
  (manylinux) é a prova definitiva, só disponível depois do primeiro push
  — risco considerado baixo (pacotes maduros, wheels manylinux
  publicadas). Risco mais direto e já auto-documentado pelo projeto
  (`docs/reconstrucao/07-INTEGRACOES.md`): todo o comportamento fino de
  escrita EXIF (`writer.py`/`verificacao.py`, grupo `-GPS:` explícito,
  `writable='false'` do XMP em sidecar, exit code que mente em falha
  parcial) foi verificado só contra o exiftool 13.55 (Homebrew local); o
  `libimage-exiftool-perl` do Ubuntu 24.04/`ubuntu-latest` é 12.76 —
  quase um ano mais velho. Os testes `@tem_exiftool` rodam pela primeira
  vez contra essa versão só depois do primeiro push; se vier vermelho,
  isolar se é regressão real ou skew de versão antes de mexer no código.
- Status: decidido, implementado, testado localmente, aguardando o
  primeiro push para confirmação no GitHub Actions.

## D-097 — Aviso de digest IPTC de terceiro não reprova mais escrita correta

- Fase: achado em produção durante a execução real do plano 3 (9.843
  arquivos, GPS/cidade/país) — não veio do backlog planejado, veio de
  investigar por que itens processados apareciam em FALHA.
- Contexto: o servidor foi interrompido no meio da execução (ação do
  dono) com 1941/9843 itens processados. D-095 reconciliou o plano
  (EXECUTANDO → INTERROMPIDA) corretamente no boot seguinte; ao apurar o
  progresso antes de retomar, 329 dos 1941 processados estavam em FALHA
  com um único motivo: `"exiftool passou a avisar: ['Warning: IPTCDigest
  is not current. XMP may be out of sync']"`.
- Achado: investigado item a item contra o acervo real (4 amostras:
  `/Volumes/Externo/2026/Serena 15 Anos/ACM_7122.JPG` e mais 3), com
  backup `_original` ainda no disco em todos. `verificacao.diferenca()`
  no par real (depois de `reclassificar_deslocamentos_de_offset`, D-077,
  que corretamente rebaixa `MPImage2:MPImageStart` — não era o problema)
  mostrava `esperadas` com exatamente as tags de Cidade/País pedidas e
  `inesperadas` vazio: a escrita em si estava CORRETA. O único motivo do
  FALHA era `novos_avisos`. Causa raiz, confirmada contra o código-fonte
  do exiftool (`Photoshop.pm`) e reproduzida numa fixture sintética:
  `Photoshop:IPTCDigest` é um checksum de TERCEIRO (Adobe — Lightroom/
  Photoshop) que registra o digest do bloco IPTC no momento em que essa
  ferramenta sincronizou por último; gravar qualquer tag IPTC depois
  (aqui, `-IPTC:City=`/`-IPTC:Country-PrimaryLocationName=`) muda o
  `File:CurrentIPTCDigest` real sem o exiftool recalcular o checksum
  congelado — `-validate` sempre avisa "desatualizado" depois de
  QUALQUER escrita IPTC num arquivo que já tinha esse checksum de
  terceiro (comum em fotos que passaram por Lightroom/Photoshop antes).
  Este módulo nunca gerencia esse checksum — fora do escopo estreito de
  D-075 (GPS/cidade/país) — e o D-04 (delta de avisos, "nenhum aviso
  novo") não previa essa classe de aviso benigno, só a de corrupção real.
- Correção: `verificacao.py` ganha `AVISOS_ESTRUTURAIS_ESPERADOS`
  (frozenset de uma string, mesmo espírito de `TAGS_ESTRUTURAIS_ESPERADAS`
  — "nunca um prefixo inteiro isento", cada entrada justificada) e
  `avisos_inesperados(antes, depois)` = delta menos essa allowlist;
  `executor.py` troca o `avisos_depois - avisos_antes` cru pela função
  nova. Avaliado e descartado: parametrizar por campo (só ignorar quando
  cidade/pais foram escritos) — verificado empiricamente que uma escrita
  só-GPS nunca toca IPTC, então o aviso mecanicamente não tem como
  aparecer fora desse escopo; a allowlist incondicional já é segura sem
  a complexidade extra.
- Verificado: reproduzido contra o exiftool real (gravar
  `Photoshop:IPTCDigest` igual ao digest atual e depois qualquer tag
  IPTC reproduz o aviso de forma determinística); 4 testes novos em
  `test_exif_write_executor.py` (2 puros sobre `avisos_inesperados`, 1
  ponta a ponta provando que a escrita correta deixa de reprovar, 1
  contraprova — GPS pedido e nunca escrito continua reprovando pelo
  diff de tags, a allowlist não mascara erro real). Confirmado com
  mutante: revertendo a correção manualmente, os 2 testes de integração
  falham (a rede de regressão pega a regressão se ela voltar). Suíte
  completa: 1162 Python, verde.
- Revisão com olhos frescos (agente-arquivos, adversarial, antes de
  autorizar retomar a gravação real), incorporada: (1) achado real — os
  2 testes de integração inicialmente escritos passavam COM ou SEM a
  correção (falso-positivo): o helper de simulação lia
  `File:CurrentIPTCDigest` de um arquivo que nunca teve bloco IPTC
  (`tests/fixtures.py::make_jpeg` só escreve EXIF), a leitura vinha
  vazia, e gravar `Photoshop:IPTCDigest` vazio era um no-op silencioso
  do exiftool — o cenário real nunca era exercitado. Corrigido: o helper
  agora grava uma tag IPTC inócua primeiro, criando o bloco de que o
  digest depende, e o teste de mutante confirmou a correção do teste.
  (2) achado operacional, não de código: os 329 itens já marcados FALHA
  não entram em `pendentes` de `executar()` (filtro é por
  `CampoStatus.PRONTO`) — retomar precisa rodar `dry_run(3)` de novo
  antes de `executar(3)`, para a reconferência ao vivo (EXIF-02)
  reclassificar esses 329 de FALHA para PULADO (campo já preenchido de
  verdade no arquivo, confirmado nas 4 amostras). (3) pesquisado no
  código-fonte do exiftool se o aviso poderia mascarar corrupção real:
  não — ele é comparação pura de dois hashes de terceiro, e uma
  corrupção que mudasse o CONTEÚDO do bloco IPTC continuaria pega pelo
  diff de tags (`inesperadas`), camada complementar, não substituída
  por esta allowlist.
- Fora desta fatia, registrado sem correção: `formatos.py` ainda cita
  "IPTCDigest desatualizado" como motivo de `.tif` reprovar (D-076,
  comentário desatualizado à luz desta decisão) — inofensivo porque
  `.tif` vai para sidecar independentemente desse aviso, mas vale
  atualizar o comentário num commit futuro.
- Status: decidido, implementado, testado (incluindo contra 4 itens
  reais do acervo e com teste de mutante), revisado com olhos frescos.
  Plano 3 ainda não retomado — próximo passo é `dry_run(3)` seguido de
  `executar(3)`.
- **Addendum** (mesma sessão, ao rodar o `dry_run(3)` de retomada de
  verdade): confirmado no acervo real que a reconferência ao vivo
  reclassificou 314/329 itens de FALHA para PULADO (o valor já estava
  correto no arquivo, exatamente como previsto) — mas `item.erro`
  (mensagem de topo, distinta do motivo por campo) nunca era limpo por
  `dry_run()`, só por `executar()`, e esses 314 itens não entram mais em
  `pendentes` (nada PRONTO neles) — nunca reentrariam em `_executar_item`
  para ganhar essa limpeza. Sem correção, o catálogo diria "329 com erro"
  para sempre, mesmo com os campos já corrigidos. Não é risco de
  segurança (nenhum arquivo é tocado por essa mensagem), só honestidade
  do relatório. Corrigido: `dry_run()` limpa `item.erro` quando a
  reconferência ao vivo não encontra mais FALHA em nenhum dos 3 campos;
  mantém o erro quando a reconferência confirma que o valor continua
  inválido (2 testes novos, incluindo a contraprova). Fora desta fatia,
  registrado sem correção: os `_original` que o exiftool deixou ao lado
  desses 314 arquivos (das falsas reprovações) não têm caminho de
  limpeza automática — eles nunca reentram no branch que apaga o backup
  (`todos_gravados` em `_executar_item`), porque não há mais nada PRONTO
  a escrever. Seguro (invariante 8: quem decide apagar backup é o dono),
  só deixa ~314 arquivos `_original` acumulados na árvore que o scanner
  trata como somente-leitura — decisão de limpeza automática fica para
  outra fatia.
