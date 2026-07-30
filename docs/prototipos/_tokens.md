# Tokens dos protótipos

Bloco copiado em cada protótipo (eles são autocontidos por decisão: abrem
com duplo clique, sem servidor e sem rede). Fonte: `docs/REFERENCIAS_DESIGN.md`.

```css
:root {
  /* Fundo quase-preto, não preto: dá profundidade sem esmagar sombra. */
  --fundo: #08090A;
  /* Superfície NÃO é cor própria — é branco translúcido sobre o fundo.
     É o que faz a foto mandar na interface: o painel modula o que está
     atrás em vez de competir. */
  --sup-1: rgba(255, 255, 255, 0.02);
  --sup-2: rgba(255, 255, 255, 0.05);
  --sup-3: rgba(255, 255, 255, 0.08);
  --borda: rgba(255, 255, 255, 0.10);
  --borda-forte: rgba(255, 255, 255, 0.18);

  --texto: #F7F8F8;
  --texto-2: #8A8F98;
  --texto-3: #62666D;

  /* Sem acento cromático fixo. Cor é reservada para ESTADO, e mesmo assim
     dessaturada — numa ferramenta de foto, acento saturado compete com a
     imagem. O "acento" default é o próprio branco em opacidade maior. */
  --atencao: #C2833A;   /* precisa de olho humano */
  --herdado: #6E8FA8;   /* veio de outro dispositivo */
  --removido: #A8615A;
  --adicionado: #6E9A78;

  --r: 6px;
  --r-g: 10px;

  --f: -apple-system, "SF Pro Text", "Inter", system-ui, sans-serif;
  /* 13px é a medida de app no Mac. 16px é medida de página web — parte do
     que fazia a UI atual "parecer site". */
  --t-corpo: 13px;
  --t-peq: 11px;
  --t-tit: 15px;
  /* Peso 510 e tracking negativo: hierarquia por tamanho e espaçamento,
     não por peso. Denso sem parecer gritado. */
  --p-tit: 510;
}
```

## Escala de confiança

A regra do `docs/CONFIANCA.md` é que confiança é o elo mais fraco e preserva
as evidências. A tradução visual precisa disso, não de um semáforo:

- **três segmentos** preenchidos 3/3, 2/3, 1/3 — quantidade, não cor;
- **neutro** em alta e média; só a baixa recebe `--atencao`, porque é a
  única que pede olho humano;
- o indicador é **clicável** e abre a evidência que o produziu. Badge que
  não leva à justificativa é decoração.
