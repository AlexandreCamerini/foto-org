# Referências de design — comparativo de tokens

Levantado em 2026-07-29 para escolher a base do redesenho do webapp.
Insumo da fase 6 (`docs/prompts/fase-6-ux.md`).

Método: as três referências foram abertas no navegador e os tokens extraídos
do **estilo computado da página viva** (`getComputedStyle`), não de HTML
raspado — valor computado é o que o usuário realmente vê. A skill
`brightdata-plugin:design-mirror` exigiria `BRIGHTDATA_API_KEY` e uma zona
Unlocker, que não existem neste ambiente; o caminho pelo navegador entrega o
mesmo resultado com precisão maior e sem terceiros.

## Comparativo

| | **Linear** | **Peakto (cyme.io)** | **macOS nativo** (Photomator) |
|---|---|---|---|
| Fundo da página | `#08090A` quase-preto azulado | `#000000` preto puro | semântico (`windowBackgroundColor`) |
| Superfície de painel | `rgba(255,255,255,0.05)` translúcido | `#27282D` sólido | materiais / vibrancy do sistema |
| Texto principal | `#F7F8F8` | `#FFFFFF` | `labelColor` |
| Texto secundário | `#8A8F98` | `#B0ECF1` (ciano!) | `secondaryLabelColor` |
| Acento | `#5E6AD2` índigo | `#6CD8E5` ciano | acento **escolhido pelo usuário** no sistema |
| Fonte | Inter Variable / SF Pro Display | Roboto + Fjalla One (display condensada) | SF Pro |
| Peso de título | **510** | 400 (h1) / 700 (h2) | por text style |
| h1 | 64px, tracking −1.408px | 40px, tracking normal | por text style |
| Corpo | 15px / 24px | 19px / 34.2px | 13px é o padrão em app Mac |
| Raio dominante | 6px (22×), depois 8 e 12 | 4px (37×) e 3px (21×) | ~6px em controle padrão |

Os valores do macOS não foram verificados na fonte nesta sessão: as páginas
das Human Interface Guidelines são SPA e não renderizaram no fetch nem no
navegador (redirecionou para outra página). Estão aqui como prática
estabelecida, **não como extração** — confirmar em
`developer.apple.com/design/human-interface-guidelines` antes de virar token.

## Leitura

**Linear é a mais aproveitável, e por um motivo específico.** Ela não pinta
painel: usa branco a 2–8% de opacidade sobre quase-preto — 45 elementos com
`rgba(255,255,255,0.05)` e 19 com `0.02`. O painel **modula o que está atrás**
em vez de introduzir cor própria. Esse é exatamente o mecanismo que implementa
a regra do `docs/DIRECAO_DE_ARTE.md`: a foto é a cor da interface. Nenhuma
outra das três faz isso — Peakto usa `#27282D` sólido, e o macOS resolve com
materiais, que é a mesma ideia implementada pelo sistema operacional.

Dois detalhes de Linear que valem tanto quanto a paleta: **peso 510** nos
títulos, não 700 — hierarquia por tamanho e tracking negativo em vez de peso,
que é o que faz a interface parecer densa sem parecer gritada. E **corpo em
15px com entrelinha 24px**, contra os 16px padrão do navegador que o seu app
usa hoje. Tipografia em escala de web dentro de um app é parte do "parece
site": app Mac trabalha em 13px.

**Peakto deve ser rejeitada como referência visual.** Roboto com Fjalla One
condensada, ciano sobre preto, corpo a 19px com entrelinha de 34px — é
linguagem de site de agência, de 2018. Espelhar cyme.io deixaria o Foto
Organizer **mais** parecido com página web, que é o oposto do pedido. É o
risco que eu tinha levantado sobre o `design-mirror`, e a extração confirmou.

Peakto continua valendo como referência de **arquitetura de informação** — a
barra lateral única com Apple Photos, Lightroom, Capture One e pastas lado a
lado é o problema que o Foto Organizer também tem. Isso se estuda por captura
de tela do app, não pelo CSS do site.

**macOS é a referência de idioma de controle.** É o que resolve o `<select>`
cru, os links de texto na navegação e os botões de bloco no rodapé da barra
lateral. Não é uma paleta a copiar: é um conjunto de semânticas (`labelColor`,
`separatorColor`, acento do usuário) e de métricas de controle.

## Recomendação

Não escolher uma das três, e sim **compor duas camadas**:

1. **Mecânica visual da Linear** — fundo quase-preto, superfícies como branco
   translúcido em vez de painel colorido, escala tipográfica densa com peso
   ~510 e tracking negativo nos títulos, raio de 6px, corpo em 13–15px.
2. **Idioma de controle do macOS** — controles desenhados em vez de herdados
   do navegador, acento vindo da preferência do sistema em vez de fixo, e
   navegação de topo que não seja fileira de links de texto.

E **descartar o índigo `#5E6AD2` da Linear junto com o azul padrão do
Tailwind**. Numa ferramenta de foto, acento cromático fixo compete com a
imagem. O acento deve ser neutro na maior parte da interface e reservado para
estado — o que também resolve o badge de confiança, que hoje é decorativo.

## O que isso não resolve

Nenhuma das três mostra por que o sistema decidiu o que decidiu. Linear é
densa e teclado-first, Peakto unifica fontes, macOS dá idioma — nenhuma tem o
problema de exibir inferência com origem, confiança e justificativa. Nisso não
há referência a espelhar, e é onde a fase 6 precisa desenhar do zero.
