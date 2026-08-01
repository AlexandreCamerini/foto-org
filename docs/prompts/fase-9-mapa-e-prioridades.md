# Fase 9 — O mapa do lugar estimado, e a ordem do que vem depois

Leia `docs/prompts/00-protocolo.md` primeiro. Entregáveis: código em
`webapp/src/` e `fotoorganizer/`, `docs/LOCAL_ESTIMADO.md` com a fórmula do
raio e sua calibração, e `docs/ROADMAP.md` reordenado com o custo de cada item.

O protótipo `docs/prototipos/03-mapa-local-estimado.html` decidiu a **linguagem**
do lugar estimado — ponto cheio para coordenada lida, ponto vazado para
estimada, traço até a foto que doou, aviso de cascata. Ele fechou dizendo que
o mapa real depende de uma decisão que não é de direção de arte. Esta fase toma
essa decisão e constrói o mapa.

## O que já existe (não redescobrir)

| | |
|---|---|
| Fotos no catálogo | 5.191 |
| …com lugar estimado de outra câmera | 4.944 |
| …sem coordenada nenhuma | 247 |
| Janelas de herança por granularidade (D-025) | cidade 10 min · região 2 h · país 12 h |
| Δt até a doadora, já corrigido de deriva | `MediaFile.gps_estimado_delta_s` |
| Doadora da coordenada | `MediaFile.gps_estimado_de_id` |
| Coordenada herdada | `gps_lat_estimado` / `gps_lon_estimado` |
| Motor de herança | `fotoorganizer/grouping/correlacao.py` |

O dado que o mapa precisa já está no banco e já é corrigido de deriva de
relógio. Esta fase não recalcula herança — ela desenha o que a herança já sabe.

## Problema 1 — Uma estimativa desenhada como ponto mente sobre si mesma

Hoje o lugar estimado é um par de coordenadas: um ponto, visualmente idêntico
a uma medição de GPS. Mas a coordenada herdada é a da **doadora**, não a da
foto — e quanto maior o Δt, mais longe dali a foto pode ter sido tirada. Um
ponto afirma precisão que o dado não tem.

Alvo: um mapa real onde a foto com GPS próprio é um ponto e cada foto herdeira
é um **círculo cujo raio é a incerteza** — a região onde ela plausivelmente
está, dado o Δt até a doadora. O raio é a forma visual do que D-025 já decidiu
em texto: em 10 minutos não se troca de cidade, em 12 horas não se troca de
país.

A fórmula deve ser simples o bastante para caber numa frase na tela quando o
dono perguntar "por quê?", e honesta o bastante para que o círculo contenha o
lugar real. Uma direção que já cabe nos dados, a confirmar ou derrubar com
medição: **raio ≈ velocidade plausível × Δt**, com piso na precisão do próprio
GPS e teto na janela da granularidade que o Δt sustenta. Se a medição indicar
outra fórmula, use a outra e registre por quê.

Calibre contra o acervo, não contra intuição: existem fotos com GPS **próprio**
cuja doadora hipotética também tem GPS próprio — para essas dá para medir a
distância real em função do Δt e verificar em que fração dos casos o raio
proposto de fato contém o lugar verdadeiro. Uma fórmula que acerta em menos de
9 de cada 10 casos está otimista demais para uma interface que promete
honestidade.

Registre em `docs/LOCAL_ESTIMADO.md`: a fórmula, a medição que a calibrou, a
taxa de cobertura observada e como reverter.

## Problema 2 — Mapa real exige decidir de onde vem o mapa

Esta é a decisão que o protótipo adiou, e ela é de privacidade antes de ser de
biblioteca: **pedir um tile a um servidor externo revela ao servidor onde suas
fotos foram tiradas.** Um mapa que carrega tiles de terceiros faz o acervo
vazar por coordenada, sem que nenhum arquivo saia da máquina.

O invariante 4 do `CLAUDE.md` decide a direção: nada sai por padrão. O que
falta escolher é a forma — tiles embarcados, vetor renderizado de dados locais,
ou nenhuma cartografia (posições relativas sobre uma malha, como o protótipo
fez de propósito). Cada opção tem custo de disco, de dependência e de fidelidade
diferentes; a escolha é Classe B do protocolo, com estimativa de tamanho em MB.

Um mapa que só mostra a geometria da correlação — pontos, círculos e traços,
sem ruas — já entrega a maior parte do valor e não tem custo de privacidade
nenhum. Considere-o o piso, não o fracasso.

## Problema 3 — A ordem do resto do backlog

`docs/ROADMAP.md` lista dez itens para v2+ ordenados por valor, escritos antes
de sabermos o que sabemos hoje sobre este acervo: 25 anos de fotos, só 4 com
GPS de receptor próprio (D-029), 45.397 do Lightroom em volume desmontado,
44.661 do Apple Fotos sem arquivo local.

Reordene por **valor entregue por unidade de custo**, com o custo dito em
números, não em adjetivos. Para cada item: o que muda para o dono deste acervo
específico, o esforço, o custo recorrente se houver, e o que ele desbloqueia ou
bloqueia. Um item cujo valor depende de dados que este acervo não tem desce,
por melhor que seja em abstrato.

Duas restrições sobre a ordem: o mapa desta fase entra à frente do que estava
lá; e `docs/EVENTOS.md`, que a fase 8 pediu e não foi escrito, continua
pendente e é barato — trate-o como dívida da fase anterior, não como item novo.

## Fronteira

Os invariantes do `CLAUDE.md` valem inteiros. Em especial: o 4 (nada sai da
máquina por padrão — inclusive coordenada, inclusive via tile) e o 8 (nada que
possa ser referência real de uma foto é apagado).

O mapa é leitura. Ele não corrige coordenada, não reescreve herança e não
executa operação física. Corrigir o lugar de uma foto no mapa, se a fase chegar
lá, é sugestão a aprovar como qualquer outra — e o aviso de cascata do
protótipo ("desfaz também a viagem que elas ajudaram a formar") é parte da
interface, não um detalhe.

## Método

Fatias verticais pela skill `fatia-vertical`, uma por vez, `scripts/verificar.sh`
verde antes de cada commit. A medição que calibra o raio entra antes do desenho
que a usa.

O dono está fora e acompanha pelo controle remoto. Antes de implementar,
entregue um plano curto — as fatias em ordem, o que cada uma resolve, e quais
delas ele decide. Plano que não cabe numa tela de celular não serve.

## Aceite

1. O mapa mostra foto com GPS próprio como ponto e foto herdeira como círculo,
   com o traço até a doadora, no acervo real do dono.
2. O raio vem de uma fórmula registrada em `docs/LOCAL_ESTIMADO.md`, calibrada
   contra pares medidos do próprio acervo, com a taxa de cobertura declarada.
3. Clicar num círculo responde por que ele tem aquele tamanho, em uma frase.
4. Nenhuma requisição sai da máquina ao abrir o mapa — verificável no painel de
   rede do navegador.
5. A escolha de cartografia está em `docs/DECISOES.md` com tamanho em MB e
   forma de reverter.
6. Fotos fora de alcance e sem coordenada aparecem contadas em algum lugar da
   tela, em vez de sumirem em silêncio.
7. `docs/ROADMAP.md` reordenado, com custo por item e o porquê de cada
   movimentação em relação à ordem anterior.
8. `pytest` e `vitest` verdes; cenários de `scripts/avaliar_agrupamento.py`
   não regridem.
