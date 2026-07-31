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
    servirApi(ROTAS_BASE);
    montar(<App />);
    expect(await screen.findByText("8 organizáveis · 1 fontes")).toBeInTheDocument();
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
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText(/8 alcançáveis agora/)).toBeInTheDocument();

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
