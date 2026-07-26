import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";
import { ROTAS_BASE, montar, servirApi } from "./test/servidor";

describe("App", () => {
  it("abre no Panorama e mostra as lacunas do catálogo", async () => {
    servirApi(ROTAS_BASE);
    montar(<App />);

    expect(await screen.findByText("8 fotos no catálogo.", { exact: false }))
      .toBeInTheDocument();
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
    expect(await screen.findByText("8 fotos · 1 fontes")).toBeInTheDocument();
  });
});
