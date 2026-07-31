# Fase 8 — A tela da decisão, e o que é um evento

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável: código em
`webapp/src/` e `fotoorganizer/`, mais `docs/EVENTOS.md` registrando o modelo
de correlação novo e por que ele substitui o atual.

O dono usou o app e três telas falharam para ele. Duas das falhas têm a mesma
raiz e são baratas; a terceira é de modelo e é a que importa.

## O que foi medido antes de escrever isto

| | |
|---|---|
| Sugestões pendentes | 5.048 |
| …com arquivo alcançável | 4.932 |
| …em volume desmontado | 116 |
| Miniatura de JPG e CR3 alcançáveis | funciona (HTTP 200) |
| Miniatura de arquivo em volume desmontado | HTTP 404, sem explicação na tela |

O primeiro grupo da fila de revisão — `Eventos/2015/Visconde de Maua` — está
inteiro em `/Volumes/photo`, que não está montado. A Biblioteca foi aberta com
a fonte `Externo`, também indisponível. **As duas telas que pareceram
quebradas eram as duas que não tinham como mostrar imagem**, e o app não disse
uma palavra sobre isso: desenhou o ícone de imagem quebrada e ficou quieto.

Isto não é desculpa para a tela — é o diagnóstico. Uma interface que trata
"não alcanço este arquivo" como "imagem quebrada" mente sobre o próprio
estado, e foi o que destruiu a confiança do dono nas três telas de uma vez.

## Problema 1 — A tela de revisão não deixa decidir

É a tela mais importante do sistema e hoje uma linha mostra: miniatura, nome
do arquivo, câmera, horário, a palavra "Média" e dois botões. O destino
sugerido está só no cabeçalho do grupo, e o **porquê não está em lugar
nenhum** — a evidência existe no banco, com justificativa em português, e não
chega à tela.

Alvo: olhando uma linha, o dono sabe para onde a foto vai, por qual regra, com
que firmeza, e o que muda se ele errar — sem abrir outra tela. Quando a foto
não estiver alcançável, a linha diz isso em vez de fingir uma imagem.

Decida a forma. Duas restrições: a evidência já existe (`evidence`, com
origem, score e justificativa legível — não invente outra) e o dono precisa
poder decidir em lote sem perder o rastro do que decidiu.

## Problema 2 — A Biblioteca não mostra imagem

Mesma raiz do problema 1. A grade precisa distinguir três estados que hoje
viram um só: miniatura pronta, miniatura sendo gerada, arquivo fora de
alcance. O terceiro diz por quê e o que fazer (montar o volume, procurar
backup — `fotoorganizer volumes` já sabe a diferença).

## Problema 3 — Evento não é viagem curta

Aqui está o trabalho de verdade, e ele é de modelo, não de tela.

Hoje a aba se chama "Viagens" e o agrupamento é uma cascata temporal: fotos
próximas no tempo viram uma sessão, e a sessão vira viagem ou evento conforme
distância de casa e duração. A consequência é que **dois eventos no mesmo dia
viram um só** — não há como o modelo atual separá-los, porque a régua é o
intervalo entre fotos.

Um dia real tem o aniversário de manhã e o show à noite. São dois
acontecimentos, com o mesmo dia, a mesma cidade e possivelmente a mesma
câmera.

Proponha o modelo de correlação que separa isso, e escreva em `docs/EVENTOS.md`
o que passa a distinguir um evento de outro. Sinais que o catálogo já tem e
que a cascata atual ignora ou subusa:

- **Ritmo de disparo** — um acontecimento tem densidade própria; o intervalo
  entre fotos dentro dele é menor que o intervalo até o próximo.
- **Deslocamento** — mudar de lugar entre dois blocos de fotos, mesmo dentro
  da cidade, separa acontecimentos. Há coordenada própria em poucos arquivos e
  herdada em 4.928 (`gps_lat_estimado`, com Δt e granularidade — ver D-025).
- **Câmera e lente** — trocar de equipamento marca mudança de contexto.
- **Intenção declarada** — 25.304 nomeações de álbum do Apple Fotos e 2.477
  palavras-chave do Lightroom, já filtradas por `grouping/albuns.py` (o que
  nomeia acontecimento × o que nomeia aparelho ou app).
- **Hora do dia** — manhã e noite do mesmo dia raramente são o mesmo evento.

A aba passa a ser de eventos, com viagem como um tipo de evento — não o
contrário.

## Problema 4 — O Apple Fotos entra e some

O dono diz que o sistema conecta, lê as fotos e "esquece". A medição confirma
o sintoma e corrige a causa:

| | |
|---|---|
| Registros importados do Apple Fotos | 44.661 |
| …com data de captura | 44.661 |
| …com GPS | 16.421 |
| …visíveis na Biblioteca | **0** |
| Arquivos em `Photos Library.photoslibrary/originals` | **0 (pasta vazia)** |

A importação está correta: a biblioteca está em "Otimizar armazenamento do
Mac", os originais vivem no iCloud, e `osxphotos` não devolve caminho porque
não há arquivo. O app não pode organizar o que não pode copiar.

O erro é outro: **44.661 fotos do dono viraram invisíveis sem explicação**. Ele
mandou o app ler a biblioteca dele e recebeu um `(0)` na barra lateral.

A Biblioteca precisa mostrá-las, marcadas pelo que são — foto conhecida, sem
arquivo neste Mac — e oferecer a saída, que é do usuário e não do app: baixar
os originais no Apple Fotos. O mesmo tratamento serve para as 45.397 do
Lightroom em volume desmontado; é a mesma categoria com outra causa.

Decida se isso é um modo da Biblioteca, um filtro, ou a grade mostrando tudo
com marcação. A restrição: uma foto sem arquivo continua fora da revisão e do
plano de cópia — ela é visível, não organizável.

## Problema 5 — A barra lateral parece navegação e é filtro

Os dois menus se atrapalham, e o motivo é concreto: a lateral define `fonte`,
o menu de cima define `aba`, e **`fonte` só tem efeito na Biblioteca**. Nas
outras cinco telas a lateral continua visível e clicável sem mudar nada.

Há ainda dois caminhos diferentes para filtrar a mesma grade, com aparência e
tempo de vida distintos: `fonte`, que a lateral define e persiste em silêncio,
e `recorte`, que vem do Panorama ou de Viagens, troca de aba sozinho e aparece
como chip removível.

Alvo: um modelo de navegação em que todo controle visível age sobre o que está
na tela, e em que o estado de filtro é um só, legível e reversível.

Use as skills `design` e `engineering:system-design` para esta parte. Elas
existem para não inventarmos um modelo de navegação por intuição; o resultado
entra em `docs/DIRECAO_DE_ARTE.md` como regra, não como descrição do que foi
feito.

## Problema 6 — Onde a IA entra, e onde ela não entra

O dono observou que não há uso de IA nas correlações. Está certo: a cascata é
determinística e o advisor LLM existe, está desligado por padrão e só é
consultado para sessões que a cascata não resolveu.

Isso foi decisão consciente (D-004): regra determinística antes de modelo,
porque o dono precisa poder auditar "por quê?" e porque errar barato é melhor
que errar caro. A fase não é para abandonar esse princípio — é para revisar
**onde ele deixou valor na mesa**.

Responda com medida, não com opinião: para que parte da correlação de eventos
a regra determinística basta, e para que parte um modelo ganha de forma
demonstrável? Um cenário rotulado que a cascata erra e o modelo acerta vale
mais que um parágrafo de argumento — `scripts/avaliar_agrupamento.py` é onde
isso se mede, e os 17 cenários atuais são o piso a não regredir.

Se a resposta for "modelo ajuda aqui", diga qual, local ou remoto, com que
custo por mil fotos e que dado sai da máquina (`docs/PRIVACIDADE.md` manda).
Se for "a regra basta", diga isso com o número que sustenta.

Chame a skill `ai-firstify:ai-firstify` para esta parte, com uma pergunta
específica: **onde neste app existe uso de IA que a regra determinística não
alcança?** O pedido do dono é que ela confirme ou derrube a hipótese de que
não há — e uma auditoria que só devolve "poderia usar IA em X" sem dizer o que
X ganha sobre a cascata atual não responde nada. O veredito precisa citar caso
concreto do acervo dele.

## Fronteira

Os invariantes do `CLAUDE.md` valem inteiros — em especial o 8: nada que possa
ser a referência real de uma foto é apagado. Reagrupar é regenerar sugestão,
nunca remover registro.

Decisão do dono já tomada e que não se reabre: a organização física é sempre
plano antes de execução, e cópia antes de movimento.

## Método

Fatias verticais pela skill `fatia-vertical`, uma por vez, `scripts/verificar.sh`
verde antes de cada commit. Cenário novo de agrupamento entra em
`scripts/avaliar_agrupamento.py` **antes** de mexer em qualquer limiar.

O dono está fora de casa e responde pelo controle remoto. Decida o rotineiro
sozinho e avise; para o que muda o que o app afirma — modelo de evento, uso de
IA, qualquer coisa que envie dado para fora — pergunte e siga com a
recomendação se não houver resposta em 10 minutos, registrando em
`docs/DECISOES.md` como decidido por timeout.

## Plano antes de código

O dono está fora e acompanha pelo controle remoto. Antes de implementar,
entregue um plano curto: as fatias em ordem, o que cada uma resolve, e quais
delas mudam o que o app afirma (essas ele decide). Plano que não cabe numa
tela de celular não serve para o que ele vai fazer com ele.

Depois disso, implemente uma fatia por vez, avisando ao terminar cada uma.

## Aceite

1. Uma linha da revisão responde destino, regra, firmeza e como desfazer, sem
   abrir outra tela — e diz quando o arquivo está fora de alcance.
2. A grade distingue miniatura pronta, em geração e arquivo inalcançável.
3. As 44.661 fotos do Apple Fotos e as 45.397 do Lightroom aparecem na
   Biblioteca, marcadas pelo que são, e continuam fora da revisão e do plano.
4. Todo controle visível age sobre a tela em que está, e o estado de filtro é
   um só. A regra nova está em `docs/DIRECAO_DE_ARTE.md`.
5. Dois acontecimentos no mesmo dia, na mesma cidade, com a mesma câmera,
   viram dois eventos. Existe cenário rotulado que prova isso e que falhava
   antes.
6. Os 17 cenários atuais continuam passando.
7. `docs/EVENTOS.md` explica o modelo novo, com a medida de antes e depois.
8. O veredito da IA cita caso concreto do acervo: onde a regra basta, onde o
   modelo ganha, e o que custa.
