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
