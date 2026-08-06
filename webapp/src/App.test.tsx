import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";
import { ROTAS_BASE, montar, servirApi } from "./test/servidor";

describe("App", () => {
  it("abre no Panorama e mostra as lacunas do catálogo", async () => {
    servirApi(ROTAS_BASE);
    montar(<App />);

    // "8 fotos no catálogo" virou "das 8 fotos que dá para organizar agora":
    // o total da tela passou a ser o acervo conhecido, e as lacunas dizem
    // explicitamente sobre que subconjunto falam.
    expect(
      await screen.findByText(/das 8 fotos que dá para organizar agora/),
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

    // E as lacunas ficam explicitamente escopadas ao organizável.
    expect(
      await screen.findByText(/das 8 fotos que dá para organizar agora/),
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
