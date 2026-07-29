# Avaliação DAM/DAC do Foto Organizer — arquitetura, funcionalidades, UX e base de metadados

Você atua como especialista em pesquisa, catalogação e organização de digital
assets (DAM/DAC), com domínio de metadados de imagem e de GenAI aplicada a
acervos. O objetivo é levar este piloto a produto comercial distribuível.

Trabalhe neste repositório. Leia `CLAUDE.md`, `docs/ARQUITETURA.md`,
`docs/ROADMAP.md`, `docs/CONFIANCA.md`, `docs/COBERTURA_METADADOS.md`,
`docs/INVENTARIO_DE_SINAIS.md` e `docs/PRIVACIDADE.md` antes de concluir
qualquer coisa sobre o estado atual.

## Entregável desta rodada

Diagnóstico e plano — **sem alterar código de produção**. As fases 1–5
produzem documentos; a implementação começa só depois que eu aprovar o
plano da fase 5. Se durante o diagnóstico você encontrar um bug de uma
linha, registre-o no relatório em vez de corrigir.

Escreva tudo em português, no tom dos documentos existentes.

## Restrições que valem em todas as fases

- Os invariantes de segurança do `CLAUDE.md` são o piso do produto
  comercial, não um obstáculo a contornar: catalogação somente leitura,
  operação física só após aprovação, nada sai da máquina sem opt-in
  explícito. Qualquer proposta de nuvem, IA externa ou sync respeita isso
  e diz como.
- Toda afirmação sobre o estado atual do sistema aponta para evidência:
  `arquivo:linha`, saída de comando, resultado de teste ou captura de tela.
  Onde faltar evidência, escreva "não verificado" — isso é uma resposta
  aceitável e melhor que uma suposição.
- Use no máximo 6 subagentes no total, e só para varreduras amplas e
  independentes (ex.: um por domínio na fase 2). Leituras pontuais e
  verificações você faz direto.
- Cada fase termina com um arquivo em `docs/` commitado (mensagem
  convencional, em português). Fases são independentes: se uma travar,
  siga para as outras e registre o bloqueio.

## Fase 1 — Arquitetura (`docs/AVALIACAO_ARQUITETURA.md`)

Avalie o estado real de `fotoorganizer/` e `webapp/` contra o que
`docs/ARQUITETURA.md` promete. Cubra: aderência ao desenho em camadas,
acoplamentos indevidos, os `Protocol` substituíveis (MetadataExtractor,
VisionProvider, FaceRecognitionProvider, GeocodingProvider, SyncProvider) e
o que falta para cada um virar plugin de verdade; esquema do banco frente ao
que o produto precisa; migrações; concorrência e trabalho em background;
convivência da UI PySide6 com o webapp.

Compare com como produtos líderes de DAM organizam essas mesmas camadas
(catálogo, ingestão, derivados, taxonomia, permissões) e diga onde este
desenho está bem posicionado e onde vai quebrar ao escalar para centenas de
milhares de arquivos e vários dispositivos.

## Fase 2 — Auditoria de funcionalidades (`docs/AUDITORIA_FUNCIONALIDADES.md`)

Minha percepção é que muitas funcionalidades não funcionam de ponta a ponta.
Confirme ou refute com execução real, não por leitura de código.

Levante o inventário de funcionalidades declaradas (ROADMAP M0–M7, CLI,
endpoints do servidor, telas do webapp) e classifique cada uma:

| Estado | Significado |
|---|---|
| Funciona | exercitada de ponta a ponta, com evidência anexada |
| Parcial | o núcleo roda, falta caminho de UI, persistência ou caso de borda |
| Órfã | código existe e tem teste, mas nada no fluxo real chama |
| Quebrada | falha ao ser exercitada — anexe o erro |
| Ausente | prometida em doc, sem implementação |

Rode `scripts/verificar.sh` e a suíte de testes; suba o servidor local e o
webapp e exercite as telas principais com dados de demonstração
(`scripts/gerar_demo.py`). Anexe saídas e capturas.

Dois pontos merecem verificação específica, porque parecem prontos no código
e podem não estar no fluxo:

1. `fotoorganizer/grouping/correlacao.py` — herança de GPS entre fontes com
   correção de deriva de relógio. É consumido por
   `fotoorganizer/classification/engine.py`, mas o resultado parece existir
   só em memória durante a sugestão. Verifique se ele chega ao banco, à UI
   e ao inventário.
2. `metadata_entries` — a tabela declara os namespaces `exif | iptc | xmp |
   fs`, e a gravação em `scanner/scanner.py` e `sources/importer.py`
   depende do que o extrator devolve. Meça quais namespaces têm linhas
   num catálogo real e quantas tags por arquivo.

Ordene o resultado por impacto no usuário, com esforço estimado por item.

## Fase 3 — Base de metadados completa (`docs/PLANO_METADADOS.md`)

Quero que cada foto tenha, na base, tudo o que o arquivo carrega — EXIF
(incluindo MakerNotes), XMP, IPTC/IIM, ICC, e o que mais existir por formato
(JPEG, HEIC, TIFF, PNG, WebP, CR3, DNG e demais RAW). Estude os padrões e
proponha o modelo de dados que os acomoda.

Entregue:

- Mapa dos padrões relevantes e do que cada um traz que os outros não
  trazem, com atenção ao que muda por formato e por fabricante.
- Estratégia de extração: hoje só existe o extrator puro-Python
  (`fotoorganizer/metadata/purepython.py`); `docs/ROADMAP.md` prevê exiftool
  em batch (`-stay_open`) como item v2. Decida se exiftool entra agora,
  com que política de fallback quando não estiver instalado, e o que isso
  custa em tempo de scan medido, não estimado.
- Modelo de dados: chave-valor genérico em `metadata_entries` versus
  colunas tipadas para os campos consultados com frequência. Diga onde cada
  um ganha, considerando busca, filtro e volume. Inclua migração Alembic
  proposta e impacto no tamanho do catálogo.
- Vocabulário canônico: como o mesmo conceito vindo de EXIF, XMP e IPTC
  converge para um campo só sem perder a origem — isso alimenta diretamente
  o modelo de evidências do `docs/CONFIANCA.md`.
- Interoperabilidade: o que precisa estar na base para exportar/importar em
  padrões que outros DAMs leem, e qual a estratégia de saída do usuário.

## Fase 4 — Local estimado por cruzamento entre dispositivos (`docs/PLANO_LOCAL_ESTIMADO.md`)

O caso concreto: fotografo com o iPhone, que grava coordenadas, e dois
minutos depois com a câmera, que não grava. A probabilidade de ser o mesmo
lugar é altíssima, e a foto da câmera deve constar na base com **local
estimado**, com a origem visível.

A lógica de inferência já existe em `grouping/correlacao.py` (janela de
tolerância, decaimento de confiança por Δt, correção de deriva de relógio
por pares-âncora). O que falta é o produto ao redor dela. Proponha:

- Persistência: onde o local estimado vive no esquema, distinguível de
  coordenada lida do arquivo, com a evidência que o justifica
  (foto-doadora, Δt, deriva aplicada, confiança) consultável depois.
- Reversibilidade e revisão: como o usuário vê, confirma, corrige ou
  descarta uma estimativa, e o que acontece com o que dependia dela.
- Generalização do cruzamento além do GPS: quais outros campos podem ser
  herdados entre dispositivos pela mesma linha do tempo corrigida
  (fuso, evento, viagem, pessoas presentes) e com que confiança.
- Precisão: como medir se a estimativa acerta, com que dados de teste, e
  qual limiar de Δt e de dispersão de âncoras o produto deve usar por
  padrão. Se os parâmetros atuais (`JANELA_HERANCA`, dispersão máxima,
  mínimo de âncoras) não estiverem calibrados com dados reais, diga isso.

## Fase 5 — IA sobre a base e plano de produto (`docs/PLANO_IA_E_PRODUTO.md`)

Com a base estruturada das fases 3 e 4, proponha como a IA decide o melhor
critério de catalogação por foto — ano, evento, viagem, pessoa, local — e
como as fotos são agrupadas fisicamente junto de seu inventário.

- Que decisões cabem em regra determinística sobre os metadados e quais
  pedem modelo. Regra primeiro: só chame modelo onde ele ganha de fato.
- Onde processamento local resolve e onde uma API vale o custo. Para
  qualquer chamada externa: que dados sairiam, com que finalidade, como o
  usuário consente e revoga, e estimativa de custo por 10 mil fotos.
  A skill `claude-api` tem os IDs de modelo e preços correntes — use ela em
  vez de memória.
- Como a saída da IA entra como evidência (origem, confiança, justificativa
  legível, versão da lógica) sem virar decisão automática.
- Formato do inventário que acompanha cada pasta agrupada, e como ele
  permite reconstruir o catálogo se o banco se perder.
- Roadmap priorizado do piloto ao produto comercial: o que falta em
  confiabilidade, empacotamento, onboarding, importação de acervos legados,
  desempenho medido e diferenciação frente aos produtos de referência do
  mercado. Marque o que é pré-requisito de lançamento e o que é posterior.

## Fase 6 — UX e visualização das decisões (`docs/AVALIACAO_UX.md` + protótipos)

A UI hoje me parece pobre visualmente e não deixa claro o que o sistema
decidiu nem por quê. Avalie o webapp contra `docs/DIRECAO_DE_ARTE.md` e
proponha uma linguagem visual em que o usuário enxergue as decisões: mapa,
linha do tempo, agrupamentos, confiança, o antes-e-depois de um plano de
organização, e a diferença entre local lido e local estimado.

Cada proposta entra como protótipo navegável — arquivo HTML ou React
autocontido em `docs/prototipos/`, com dados sintéticos — não como
descrição em texto. Anexe capturas. Fica valendo a regra da direção de arte:
a foto é a cor da interface.

Inclua uma leitura crítica de como os DAMs de referência resolvem
navegação, revisão em lote e transparência de decisão automática, e o que
vale trazer para cá.

---

Ao terminar, abra o resumo com o que mudou na minha compreensão do sistema
— as três coisas que eu provavelmente estava errado a respeito — e só
depois o restante.
