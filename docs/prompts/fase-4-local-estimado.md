# Fase 4 — Local estimado por cruzamento entre dispositivos

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável:
`docs/PLANO_LOCAL_ESTIMADO.md`.

O caso do dono, nas palavras dele: fotografa com o iPhone, que grava
coordenadas, e dois minutos depois com a câmera, que não grava. A chance de
ser o mesmo lugar é altíssima, e a foto da câmera deve constar na base com
**local estimado**, com a origem visível.

## O que já existe — leia antes de propor construir

`fotoorganizer/grouping/correlacao.py` já implementa a inferência, como
funções puras:

- correção de deriva de relógio por pares-âncora (a mesma foto presente em
  duas fontes, por hash rápido ou phash, revela o desvio; a mediana por
  câmera corrige a linha do tempo antes do cruzamento);
- herança de GPS pela foto com coordenada mais próxima no tempo corrigido,
  de fonte ou câmera diferente, dentro de `JANELA_HERANCA` (10 min);
- decaimento de confiança por Δt, com confiança cheia até 2 min;
- descarte de âncoras com dispersão acima de 3 min, mínimo de 2 âncoras.

`fotoorganizer/classification/engine.py:209` consome via `herdar_gps`. A fase
2 determina se o resultado chega ao banco e à UI. **A lacuna é o produto ao
redor da inferência, não a inferência.** Se você propuser reimplementar o
algoritmo, justifique com uma falha concreta e medida dele.

## Requisitos

- O local estimado é consultável e filtrável na base, distinguível de
  coordenada lida do arquivo — em qualquer consulta, sempre.
- A evidência que o justifica é recuperável depois: foto-doadora, Δt, deriva
  aplicada, confiança, versão da lógica.
- Nada é escrito no arquivo original.
- O usuário pode confirmar, corrigir ou descartar, e o efeito em cascata é
  visível antes de acontecer.
- Recalcular após um novo scan não perde confirmação manual do usuário.

## Persistência

Proponha onde o local estimado vive. Trate explicitamente:

- coluna dedicada versus reuso da coluna de GPS com um discriminador de
  origem — e por que a segunda opção é armadilha para consultas;
- a linha de `evidence` que sustenta a estimativa, no formato do
  `docs/CONFIANCA.md`, com a justificativa legível pronta ("coordenada
  herdada de IMG_4821.HEIC do iPhone, 1 min 40 s antes, deriva de 3 min
  corrigida, confiança alta");
- precedência quando o usuário confirmou manualmente e um novo scan produz
  estimativa diferente;
- o que acontece com viagens, eventos e pastas que foram agrupados usando
  uma estimativa que o usuário depois descartou.

Inclua a migração Alembic como proposta escrita, não aplicada.

## Generalização do cruzamento

O dono pediu GPS; a mesma linha do tempo corrigida pode doar mais. Avalie,
cada um com confiança própria e critério de aceite:

- fuso horário estimado (a coluna `tz_estimado` já existe e o item 5 do v2 do
  ROADMAP a prevê);
- pertencimento a viagem e a evento;
- pessoas presentes, quando houver reconhecimento confirmado na foto-doadora;
- altitude, direção da câmera, e o que mais o doador trouxer.

Para cada um diga se recomenda incluir agora, e o que o torna arriscado.

## Precisão e calibração

Os parâmetros atuais (`JANELA_HERANCA` de 10 min, dispersão máxima de 3 min,
mínimo de 2 âncoras) parecem escolhidos por bom senso, não por medição. Se
for o caso, diga isso e proponha:

- como medir acerto: que conjunto de dados, com que verdade de referência
  (fotos que *têm* GPS, mascaradas para simular a ausência, é o caminho
  óbvio — descreva o desenho do experimento);
- que métrica reporta o produto ao usuário, se alguma;
- limiares padrão recomendados, e quais o usuário pode ajustar;
- os casos que quebram o método: dois lugares no mesmo minuto, avião,
  fuso trocado no meio da viagem, foto editada com data alterada, dispositivo
  com relógio em deriva contínua e não constante.

## Aceite

`docs/PLANO_LOCAL_ESTIMADO.md` na forma do protocolo, com diagrama ASCII do
fluxo de dados da inferência até a UI, esquema proposto, migração escrita como
proposta, desenho do experimento de precisão, e a tabela de generalização com
recomendação por campo.
