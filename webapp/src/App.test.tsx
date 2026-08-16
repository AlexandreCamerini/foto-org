import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";
import { ROTAS_BASE, montar, servirApi } from "./test/servidor";

describe("App", () => {
  it("abre no Panorama e mostra as lacunas do catálogo", async () => {
    servirApi(ROTAS_BASE);
    montar(<App />);

    // "8 fotos no catálogo" virou "das 8 fotos do seu acervo": o total da
    // tela é o acervo conhecido, e as lacunas dizem explicitamente sobre
    // que subconjunto falam. O "estejam ao alcance ou não" é o que separa
    // este número do degrau "organizáveis" do funil, que é menor (D-068).
    expect(
      await screen.findByText(/das 8 fotos do seu acervo/),
    ).toBeInTheDocument();
    expect(screen.getByText("sem data de captura")).toBeInTheDocument();
    expect(screen.getByText("sem coordenada")).toBeInTheDocument();
  });

  it("clicar numa lacuna recorta a Biblioteca com chip removível", async () => {
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByText("sem data de captura"));

    // Trocou de aba e o recorte ficou visível como chip.
    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toBeInTheDocument();
    const chip = screen.getByTitle("Limpar recorte");
    expect(chip).toHaveTextContent("sem data de captura");

    await usuario.click(chip);
    expect(screen.queryByTitle("Limpar recorte")).not.toBeInTheDocument();
  });

  it("lacuna zerada não é clicável — não há conjunto para atacar", async () => {
    servirApi(ROTAS_BASE);
    montar(<App />);

    const vazia = (await screen.findByText("erro ao ler o arquivo"))
      .closest("button");
    expect(vazia).toBeDisabled();
  });

  it("[ e ] recolhem os painéis laterais", async () => {
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    // A lateral não existe mais no Panorama, que é a visão do acervo
    // inteiro: o atalho se testa onde ela age.
    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    expect(await screen.findByText("Fontes")).toBeInTheDocument();
    // "[[" é como o user-event escreve um "[" literal — sozinho ele abre
    // um descritor de tecla.
    await usuario.keyboard("[[");
    await waitFor(() =>
      expect(screen.queryByText("Fontes")).not.toBeInTheDocument(),
    );
    // "[[" é como o user-event escreve um "[" literal — sozinho ele abre
    // um descritor de tecla.
    await usuario.keyboard("[[");
    expect(await screen.findByText("Fontes")).toBeInTheDocument();

    // O inspetor só existe na Biblioteca.
    await usuario.click(screen.getByRole("button", { name: "Biblioteca" }));
    expect(await screen.findByText("Inspetor")).toBeInTheDocument();
    await usuario.keyboard("]");
    await waitFor(() =>
      expect(screen.queryByText("Inspetor")).not.toBeInTheDocument(),
    );
  });

  it("cada aba renderiza sem quebrar, e o inspetor não invade as sem grade",
    async () => {
      servirApi(ROTAS_BASE);
      const usuario = userEvent.setup();
      montar(<App />);
      await screen.findByText("sem data de captura");

      const esperado: [string, string][] = [
        ["Viagens", "Nenhuma viagem"],
        ["Revisão", "Nada aqui"],
        ["Duplicatas", "Nenhum grupo"],
        ["Operações", "Nenhum plano ainda."],
      ];
      for (const [aba, marca] of esperado) {
        await usuario.click(screen.getByRole("button", { name: aba }));
        expect(
          await screen.findByText(marca, { exact: false }),
        ).toBeInTheDocument();
        expect(screen.queryByText("Inspetor")).not.toBeInTheDocument();
      }
    });

  it("a barra de status mostra os totais em qualquer aba", async () => {
    // O rodapé dizia só "8 organizáveis", o último degrau, enquanto outras
    // telas mostravam os degraus de cima com a mesma palavra "fotos". Agora
    // ele carrega o funil inteiro, que é o que torna a diferença legível.
    servirApi(ROTAS_BASE);
    const { container } = montar(<App />);

    const funil = await screen.findByTestId("funil");
    expect(funil).toHaveTextContent("30");
    expect(funil).toHaveTextContent("conhecidas");
    expect(funil).toHaveTextContent("organizáveis");
    expect(container).toHaveTextContent("· 1 fontes");
  });

  it("abrir uma viagem limpa a busca deixada de outra visita à Biblioteca", async () => {
    // Bug relatado: com "IMG" ainda no campo de busca de uma visita
    // anterior, abrir uma viagem de 4.812 fotos mostrava "nenhuma foto no
    // filtro" — a busca antiga filtrava tudo, e a tela não dizia por quê.
    // Depois de REV-03 o clique na aba "Viagens" também limpa a busca — este
    // teste deixou de isolar só `Trips.onAbrir` e passou a cobrir o
    // contrato de saída (busca vazia ao chegar na Biblioteca), não mais o
    // call site sozinho.
    servirApi({
      ...ROTAS_BASE,
      "/api/viagens": [{
        id: 1, nome: "Dubai, Thai & Viet", inicio: "2024-05-01T00:00:00",
        fim: "2024-05-20T00:00:00", metodo: "temporal", fotos: 2405,
        capa_id: null,
      }],
    });
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByText("Biblioteca"));
    const busca = await screen.findByPlaceholderText(
      "Buscar por nome ou caminho…",
    );
    await usuario.type(busca, "IMG");

    await usuario.click(screen.getByText("Viagens"));
    await usuario.click(await screen.findByText("Dubai, Thai & Viet"));

    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toHaveValue("");
  });

  it("trocar de aba pelo botão limpa a busca deixada na Biblioteca", async () => {
    // REV-03, ponto 1/3: o botão de troca de aba ainda não chamava
    // setBusca(""). Sequência escolhida de propósito — nenhum outro
    // handler de REV-03 é tocado — para isolar o botão de aba.
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    const busca = await screen.findByPlaceholderText(
      "Buscar por nome ou caminho…",
    );
    await usuario.type(busca, "IMG");

    await usuario.click(screen.getByRole("button", { name: "Duplicatas" }));
    await usuario.click(screen.getByRole("button", { name: "Biblioteca" }));

    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toHaveValue("");
  });

  it("escolher uma pasta na lateral limpa a busca deixada na Biblioteca", async () => {
    // REV-03, ponto 2/3: onSelecionarPasta (prop de Sidebar) só limpava
    // selIndex, não busca. Nenhum clique em aba entre typar e o gatilho —
    // isso prova onSelecionarPasta, não o botão de aba.
    servirApi({
      ...ROTAS_BASE,
      "/api/pastas": {
        caminho: "/Volumes",
        aqui: 3,
        filhos: [
          {
            nome: "photo",
            caminho: "/Volumes/photo",
            total: 225914,
            alcancaveis: 0,
          },
        ],
      },
    });
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    const busca = await screen.findByPlaceholderText(
      "Buscar por nome ou caminho…",
    );
    await usuario.type(busca, "IMG");

    // A árvore navega um nível (não filtra) antes de "ver na grade" existir
    // — mesmo contrato provado em ArvoreDePastas.test.tsx.
    await usuario.click(await screen.findByText("photo"));
    await usuario.click(
      await screen.findByRole("button", { name: "ver na grade" }),
    );

    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toHaveValue("");
  });

  it("clicar um degrau do funil na barra de status limpa a busca", async () => {
    // REV-03, ponto 3/3: aoIrPara (prop de StatusBar/Funil) não limpava
    // busca. aoIrPara chama setAba("Biblioteca") estando já na Biblioteca,
    // então o botão de aba não participa — isola aoIrPara.
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    const busca = await screen.findByPlaceholderText(
      "Buscar por nome ou caminho…",
    );
    await usuario.type(busca, "IMG");

    const funil = await screen.findByTestId("funil");
    await usuario.click(
      within(funil).getByRole("button", { name: /conhecidas/ }),
    );

    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toHaveValue("");
  });

  it("clicar na aba já ativa não apaga a busca recém-digitada", async () => {
    // Guarda da decisão de discretion do D-03: clicar na aba em que já se
    // está é no-op hoje e continua sendo — não pode destruir o texto que o
    // usuário acabou de digitar.
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    const busca = await screen.findByPlaceholderText(
      "Buscar por nome ou caminho…",
    );
    await usuario.type(busca, "IMG");

    await usuario.click(screen.getByRole("button", { name: "Biblioteca" }));

    expect(
      await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
    ).toHaveValue("IMG");
  });
});


describe("o acervo, antes das lacunas", () => {
  it("abre com o que existe, não com o que dá para abrir agora", async () => {
    // Num acervo real eram 100.164 fotos conhecidas e 4.932 alcançáveis. A
    // tela abria com "5.191 no catálogo" e escondia o resto — respondendo a
    // pergunta errada para quem está tentando descobrir o que tem.
    servirApi(ROTAS_BASE);
    montar(<App />);

    expect(await screen.findByText("O acervo")).toBeInTheDocument();
    // Dois funis na tela — o do Panorama e o do rodapé — e é justamente o
    // ponto: os dois dizem o mesmo número com a mesma palavra.
    const funis = screen.getAllByTestId("funil");
    expect(funis.length).toBeGreaterThan(0);
    for (const funil of funis) {
      expect(funil).toHaveTextContent("30");
      expect(funil).toHaveTextContent("conhecidas");
      expect(funil).toHaveTextContent("alcançáveis");
    }

    // O disco na gaveta aparece, com o motivo.
    expect(screen.getByText("/Volumes/photo")).toBeInTheDocument();
    expect(
      screen.getByText(/fora de alcance — volume não montado/),
    ).toBeInTheDocument();

    // E as lacunas ficam explicitamente escopadas ao acervo.
    expect(
      await screen.findByText(/das 8 fotos do seu acervo/),
    ).toBeInTheDocument();
  });
});

describe("os dois menus", () => {
  it("a barra lateral só aparece onde ela age", async () => {
    // Ela definia `fonte`, que só a Biblioteca lia. Nas outras cinco telas
    // ficava visível, clicável e inerte — o que o dono descreveu como "os
    // dois menus não funcionam bem juntos".
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    // Panorama: é a visão do acervo inteiro, sem filtro de fonte.
    await screen.findByText("O acervo");
    expect(screen.queryByText("Fontes")).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Biblioteca" }));
    expect(await screen.findByText("Fontes")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Revisão" }));
    expect(screen.getByText("Fontes")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Operações" }));
    expect(screen.queryByText("Fontes")).not.toBeInTheDocument();
  });
});

describe("âncora temporal", () => {
  it("a régua de tempo salta filtrando, e dá para voltar", async () => {
    // Com 103.938 registros paginados de 200 em 200, chegar em 2015 rolando
    // exigiria carregar tudo que veio antes. O salto é por filtro.
    servirApi(ROTAS_BASE);
    const usuario = userEvent.setup();
    montar(<App />);

    await usuario.click(await screen.findByRole("button", { name: "Biblioteca" }));
    // O ano aparece como cabeçalho e o mês como botão clicável.
    expect(await screen.findByText("2024")).toBeInTheDocument();
    await usuario.click(screen.getByTitle("jun/2024 · 5 fotos"));

    expect(await screen.findByText(/todo o período/)).toBeInTheDocument();
  });
});
