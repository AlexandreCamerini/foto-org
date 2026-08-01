# Modelo de navegação

Três decisões que estavam implícitas e por isso vinham sendo tomadas de novo a
cada correção. Escritas aqui para parar de ser reinventadas.

O gatilho foi o dono dizer que a interface ficou ruim depois de três fatias
seguidas de correção. Ele tem razão, e a causa é nomeável: eu adicionei um
controle segmentado, um chip, um placeholder e um rótulo — cada um resolvendo
um problema real — numa tela que nunca foi desenhada para essa quantidade de
estado. Acúmulo não é desenho.

## O que o mercado ensina, com fonte

| Produto | Elogiado por | Criticado por |
|---|---|---|
| Lightroom Classic | fluidez de rolagem em acervo grande; o módulo Biblioteca é DAM de verdade | interface "duas décadas atrasada"; módulos com espaços de cor e capacidades diferentes; mudanças que quebram memória muscular |
| Peakto (CYME) | ler Apple Fotos, Lightroom, Capture One e Aperture sem importar nem duplicar | interface lenta — "o Lightroom rola muito melhor na mesma máquina"; classificação de IA "abaixo de um CLIP ingênuo" |
| Apple Photos (iOS 18) | — | removeu a estrutura de abas por rolagem única; rejeitado a ponto de a Apple reverter parte em 18.2; "ênfase em IA às custas de organização simples" |

Três lições que valem para nós:

1. **Fluidez importa mais que modernidade.** O Lightroom é feio e ninguém
   troca por causa disso; o Peakto é bonito e a lentidão é a queixa número um.
2. **Não tire a estrutura de navegação.** A Apple tentou e recuou.
3. **IA não substitui organização.** Foi a crítica ao iOS 18 e ao Peakto, nos
   dois casos por excesso — o que confirma a D-004 pelo lado de fora.

---

## Decisão 1 — Abas com esqueleto comum, não módulos

**Escolhida:** manter as seis abas compartilhando o esqueleto.

O Lightroom usa módulos com layout próprio e paga por isso: os usuários
reclamam de capacidades diferentes por módulo e de atalhos que mudam de
sentido. Nossa aplicação tem seis telas e um usuário; módulos separados
comprariam inconsistência sem comprar nada.

E o caso Apple é o argumento contra a alternativa oposta: dissolver as abas
numa rolagem única foi rejeitado.

**O que muda:** nada de estrutura. O que estava errado não era a aba — era o
que ficava em volta dela.

## Decisão 2 — Navegação à esquerda, filtro no topo, um estado só

**O defeito:** a barra lateral define `fonte`, o menu de cima define `aba`, e
as duas coisas ocupam o mesmo espaço mental sem obedecer à mesma regra. Além
disso há dois filtros para a mesma grade — `fonte`, que persistia em silêncio,
e `recorte`, que vinha do Panorama, trocava de aba sozinho e virava chip.

**Escolhida:** separar por eixo, não por tela.

- **Esquerda é lugar.** Fonte, e no futuro volume e pasta. Responde "de onde
  estou olhando".
- **Topo é recorte.** Alcance, busca, ordenação, e o chip do que veio de outra
  tela. Responde "o que estou olhando".
- **Um estado, uma aparência.** Todo filtro ativo aparece como chip, no mesmo
  lugar, removível do mesmo jeito — inclusive a fonte, que antes só se via
  destacada na lateral.

**Regra que decorre:** um controle visível age sobre a tela em que está. Onde
não age, não aparece. Já implementado, mas por remendo; agora é regra.

**O que fica melhor com isso:** hoje a lateral some em três telas, e some
inteira. Com o eixo definido, o que some é o que não se aplica — a lateral
some de Operações porque plano não tem lugar, e não porque "não deu tempo de
fazer funcionar".

## Decisão 3 — Rolagem contínua com âncora de tempo

**Medido antes de decidir**, e o resultado corrige a premissa da pergunta: a
grade **já** é virtualizada (`useVirtualizer`) e já rola infinitamente
(`useInfiniteQuery`, páginas de 200). A API devolve 200 itens em 98 ms e conta
103.938 registros em 2 ms. Não há problema de paginação a resolver.

O problema é outro e é de navegação: **100 mil fotos não têm por onde ser
alcançadas**. Rolar é a única forma de chegar em 2015, e isso não é forma.

**Escolhida:** manter a rolagem contínua e acrescentar âncora temporal —
cabeçalho de período fixo no topo enquanto se rola, e um seletor de ano/mês
que salta. É o que o Lightroom faz e é a razão de ele ser elogiado justamente
onde é feio.

**O que NÃO fazer:** paginar. Trocar rolagem por páginas resolveria um
problema que a medição mostra não existir e criaria o que o Peakto tem.

---

## Ordem de implementação

1. **Âncora temporal na grade** — é o que falta para o acervo ser navegável, e
   não depende das outras duas.
2. **Unificar o estado de filtro** — chip único para fonte e recorte.
3. **Mover alcance/busca/ordenação para uma faixa só**, com a mesma gramática.

A decisão 1 não gera trabalho: é o registro de que a estrutura fica como está.

## O que eu revisitaria quando o acervo crescer

O NAS e os dois HDs externos ainda não entraram. Quando entrarem, "fonte"
deixa de ser suficiente como eixo de lugar — vai ser preciso volume acima de
fonte, e a lateral vira árvore. O momento de rever é quando a lista de fontes
passar de uma tela.

E a âncora temporal pressupõe que a foto tem data. Hoje 507 do acervo não têm,
e no acervo completo isso tende a crescer — a grade vai precisar de um balde
"sem data" que não seja o fim da rolagem.

## Fontes

- [Adobe Lightroom review 2025 — Life after Photoshop](https://lifeafterphotoshop.com/adobe-lightroom-review-2025/)
- [P: Refresh the User Interface — Adobe Community](https://community.adobe.com/t5/lightroom-classic-ideas/p-refresh-the-user-interface/idi-p/13202428)
- [Peakto Reviews — Trustpilot](https://www.trustpilot.com/review/cyme.io)
- [AI-Powered Peakto App — PetaPixel](https://petapixel.com/2025/03/18/ai-powered-peakto-app-lets-you-find-the-perfect-image-from-anywhere/)
- [iOS 18 Photos App Redesign: Users Still Divided — MacRumors](https://www.macrumors.com/2024/11/21/apples-photos-app-overhaul-controversial/)
- [Apple gave the Photos app an iOS 18 makeover, and it's a disaster — Pocket-lint](https://www.pocket-lint.com/apple-photos-app-iphone-ios-disaster/)
