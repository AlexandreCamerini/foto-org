# Fase 6 — UX e visualização das decisões

Leia `docs/prompts/00-protocolo.md` primeiro. Entregáveis:
`docs/AVALIACAO_UX.md` e protótipos navegáveis em `docs/prototipos/`.

A percepção do dono: a UI é pobre visualmente e não deixa claro o que o
sistema decidiu nem por quê. O segundo problema é o grave — um DAM que infere
e não explica não é confiável.

Esta fase é independente das fases 3 a 5 e pode rodar em paralelo a elas.

## Leituras de partida

`docs/DIRECAO_DE_ARTE.md`, `docs/CONFIANCA.md`, `webapp/src/components/`
(Duplicates, Inspector, Loupe, Operations, Panorama, PhotoGrid, Review,
Sidebar, StatusBar, Trips), `webapp/src/index.css`.

## Regra que não se negocia

A foto é a cor da interface, conforme `docs/DIRECAO_DE_ARTE.md`. Toda
proposta respeita isso. Interface que compete com a foto por atenção está
errada, mesmo que fique bonita numa captura isolada.

## Diagnóstico do estado atual

Suba o webapp com dados de demonstração e capture cada tela em
`docs/capturas/`. Para cada uma responda: o que o usuário consegue saber
olhando, o que ele precisa adivinhar, e onde uma decisão do sistema aparece
sem justificativa. Aponte violações concretas da direção de arte, com captura.

Avalie também o que não é estética: densidade de informação, navegação por
teclado, foco visível, estados de carregamento, vazio, erro, progresso,
cancelamento e retomada. Um estado de erro honesto vale mais que uma
animação.

## O problema central — decisão visível

Proponha a linguagem visual em que o usuário enxerga o que o sistema decidiu.
No mínimo:

1. **Mapa** — onde as fotos estão, com distinção clara entre coordenada lida
   e local estimado, e a foto-doadora alcançável a partir da estimativa.
2. **Linha do tempo** — sessões, viagens e lacunas, com as fontes em faixas
   separadas para que o cruzamento entre dispositivos fique visível; é aqui
   que a deriva de relógio corrigida deve aparecer.
3. **Confiança** — como alta, média e baixa se lêem sem virar semáforo
   decorativo, e como o usuário chega da badge à evidência que a sustenta.
4. **Antes e depois de um plano** — a estrutura de pastas atual e a proposta,
   lado a lado, com o que muda destacado, antes de qualquer execução.
5. **Revisão em lote** — aprovar, rejeitar e corrigir centenas de sugestões
   sem perder o rastro do que foi decidido, com desfazer.

## Forma dos protótipos

Cada proposta entra como arquivo autocontido em `docs/prototipos/`, HTML ou
React, com dados sintéticos embutidos, abrindo sem servidor e sem rede.
Anexe a captura de cada um. Protótipo descrito em texto não conta como
entrega desta fase — trabalho visual se avalia olhando.

Não altere `webapp/src/`. Protótipo é proposta; integração vem depois da
aprovação.

## Comparação com o mercado

Como os DAMs de referência resolvem navegação de acervo grande, revisão em
lote e transparência de decisão automática. O que vale trazer, o que não
serve para um produto local-first de um usuário, e onde há espaço para este
produto se diferenciar. Nomeie os produtos e a data da consulta.

## Aceite

`docs/AVALIACAO_UX.md` na forma do protocolo, com as capturas do estado
atual, os cinco protótipos com captura, e uma lista priorizada de mudanças
ordenada por quanto cada uma aumenta a confiança do usuário nas decisões do
sistema — não por esforço de implementação.
