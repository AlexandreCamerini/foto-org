import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Trips from "./Trips";
import { montar, servirApi } from "../test/servidor";

function grupo(over: Record<string, unknown>) {
  return {
    id: 1,
    nome: "Dubai",
    inicio: "2024-05-01T00:00:00",
    fim: "2024-05-08T00:00:00",
    metodo: "temporal",
    fotos: 120,
    capa_id: 48910,
    ...over,
  };
}

describe("Trips", () => {
  it("a capa é a miniatura cacheada, não a prévia grande do loupe", async () => {
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    montar(<Trips onAbrir={vi.fn()} />);

    const img = (await screen.findByText("Dubai")).closest("button")!
      .querySelector("img")!;
    expect(img.getAttribute("src")).toBe("/api/midia/48910/thumb");
  });

  it("card sem capa alcançável diz 'fora de alcance' em vez de ficar em branco", async () => {
    // Evento inteiro num volume desmontado: o motor não achou nenhuma foto
    // com miniatura em cache, então não há capa. O card não pode desenhar um
    // retângulo vazio e deixar o dono achar que a tela quebrou.
    servirApi({
      "/api/viagens": [],
      "/api/eventos": [grupo({ nome: "Visconde de Maua", capa_id: null })],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(await screen.findByText("Visconde de Maua")).toBeInTheDocument();
    expect(screen.getByText("capa fora de alcance")).toBeInTheDocument();
  });

  it("capa que falha ao carregar degrada para o mesmo aviso honesto", async () => {
    servirApi({
      "/api/viagens": [],
      "/api/eventos": [grupo({ nome: "Pantanal", capa_id: 3248 })],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    const img = (await screen.findByText("Pantanal")).closest("button")!
      .querySelector("img")!;
    fireEvent.error(img);

    expect(screen.getByText("capa fora de alcance")).toBeInTheDocument();
  });
});
