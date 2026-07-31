# Fase 7 — A jornada da decisão, no acervo real

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável: código em
`webapp/src/` mais `docs/JORNADA_DA_DECISAO.md` registrando o que mudou e
por quê.

O dono está usando o app no acervo dele e não consegue decidir. Esta fase
não é de diagnóstico nem de protótipo — a fase 6 já fez as duas coisas e as
propostas estão em `docs/AVALIACAO_UX.md`. Esta fase entrega telas que
funcionam no catálogo real.

## O que mudou desde a fase 6

A fase 6 desenhou para 63 sugestões em 4 grupos. O catálogo real tem outra
ordem de grandeza:

| Medida | Valor |
|---|---|
| Arquivos catalogados | 94.732 |
| Sugestões pendentes | 4.353 |
| Sugestões já aprovadas | 143 |
| Sem data de captura | 35.772 |
| Sem coordenada | 46.330 |
| Lugar herdado de outra câmera | 158 |

Trate a escala como restrição de projeto, não como detalhe de implementação.
Uma tela que pede uma decisão por sugestão exige 4.353 decisões, e nenhuma
melhoria de linha resolve isso. A pergunta que orienta a fase é **quantas
decisões o usuário precisa tomar para organizar o acervo**, e a resposta boa
está em dezenas, não em milhares.

Itens 1 a 6 da lista priorizada da fase 6 já estão no produto. Faltam o 7
(antes/depois do plano), o 8 (linha do tempo por fonte) e o 9 (mapa) — e o 9
continua dependendo da decisão de dados offline × serviço externo, que é
matéria de `docs/PRIVACIDADE.md`.

## Leituras de partida

`docs/AVALIACAO_UX.md` (as cinco propostas e a lista priorizada),
`docs/DIRECAO_DE_ARTE.md`, `docs/CONFIANCA.md`, `docs/AGRUPAMENTO.md`,
`webapp/src/components/` (Review, Operations, Panorama, Inspector, Trips),
`fotoorganizer/classification/engine.py` e `fotoorganizer/server/app.py`.

## Fronteira desta fase

`webapp/src/` **é** o alvo do trabalho — a regra da fase 6 que proibia tocar
nele está encerrada. Alterar `fotoorganizer/server/` e os repositórios é
esperado quando a tela precisa de um dado que a API ainda não expõe.

Os invariantes de segurança do `CLAUDE.md` continuam valendo integralmente.
Executar operação física sobre os arquivos do dono é classe C: proponha,
mostre o plano, e pare.

## Os três problemas, em ordem de dor

### 1. A revisão não é decidível na escala real

Hoje a Revisão agrupa por destino e permite aprovar o grupo inteiro. Ainda
assim o dono trava. Descubra por quê medindo, não supondo: rode o webapp
contra o catálogo real, percorra a tela com as 4.353 sugestões e registre o
que você observa — tempo de resposta, quantos grupos aparecem, qual o maior,
quantos têm uma sugestão só, e o que a tela responde sem abrir o Inspetor.

O alvo é que, olhando um grupo, o usuário saiba qual é o conjunto, por que
aquele destino, quão firme é a evidência e o que acontece se ele errar —
antes de clicar. Onde a informação não couber, prefira revelar sob demanda a
comprimir tudo na linha.

Considere também que nem toda sugestão merece revisão individual: as que se
sustentam em evidência forte e repetida podem ser tratadas em conjunto, desde
que o usuário veja o conjunto e possa recusá-lo inteiro.

Teclado é requisito, não enfeite — a fase 6 propôs `↑↓ ↵ ⌫ ? ⇧↵` e nada
disso existe hoje.

### 2. Falta a simulação da biblioteca resultante

O dono pediu, com estas palavras, "uma simulação clara do que acontecerá após
a geração das sugestões". Isso é uma superfície nova e **anterior** ao plano
de operações: assim que as sugestões existem, ele quer ver a biblioteca que
elas produzem — a árvore de pastas proposta, quantas fotos em cada uma, o que
sobra fora de qualquer destino, e onde a proposta se apoia em lugar estimado
ou em data ausente.

O `docs/prototipos/05-plano-antes-depois.html` desenhou o antes/depois no
momento da execução. Aproveite a linguagem visual dele, mas entenda que o
momento é outro: aqui ainda não há plano, e a pergunta do usuário é "aceito
esta organização?", não "executo esta cópia?".

Deixe visível o que a simulação **não** promete. Uma pasta proposta a partir
de 3.000 fotos sem data é frágil, e o usuário precisa enxergar essa fragilidade
na própria árvore.

### 3. A organização precisa sobreviver ao segundo uso

Nada hoje descreve o que acontece quando o dono adiciona 500 fotos novas a um
acervo já organizado. Sem isso o produto é um mutirão único, não uma
ferramenta.

Defina e implemente o ciclo recorrente: o que a segunda passagem reaproveita,
o que ela reprocessa, como as decisões já tomadas continuam valendo, e como o
usuário vê num relance o que chegou de novo desde a última vez. O Panorama é
o candidato natural a ser a porta desse ciclo.

## Método

Fatias verticais, uma por vez, seguindo a skill `fatia-vertical`: teste junto
com o código, `scripts/verificar.sh` verde, commit pequeno em português.

Cada fatia observável é exercitada no catálogo real e capturada em
`docs/capturas/`. Tela nova entra com smoke em `webapp/src/**/*.test.tsx`.

Ordene as fatias por quanto cada uma reduz o número de decisões que o dono
precisa tomar. Quando duas empatarem, entregue primeiro a que ele consegue
usar sozinha.

## Aceite

1. A Revisão responde, no catálogo real e sem abrir outra tela: que fotos
   são, quando, de que câmera, por que este destino, quão firme é a evidência
   e como desfazer.
2. A tela permanece responsiva com as 4.353 sugestões carregadas; registre o
   número medido em `docs/JORNADA_DA_DECISAO.md`.
3. Existe uma simulação da biblioteca resultante, alcançável logo após gerar
   as sugestões, mostrando a árvore proposta, a contagem por pasta, o que fica
   de fora e onde a proposta é frágil.
4. O ciclo recorrente está implementado e documentado, com o Panorama
   mostrando o que chegou desde a última passagem.
5. `docs/JORNADA_DA_DECISAO.md` traz, para cada fatia: o que mudou, a captura,
   a medida antes e depois, e as decisões registradas conforme o protocolo.
6. Uma estimativa honesta de quantas decisões o dono ainda precisa tomar para
   organizar os 94.732 arquivos, comparada com o número de hoje.

Se alguma fatia não couber, entregue as demais por inteiro e diga qual ficou
de fora e por quê — reduzir o escopo é decisão do dono.
