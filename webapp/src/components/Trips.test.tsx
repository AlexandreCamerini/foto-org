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
  it("não mostra 'nenhuma viagem' enquanto as consultas ainda estão pendentes (D-072)", async () => {
    // As duas consultas eram lentas o bastante no acervo real (D-069 achado
    // 3 — 50-120s+ medidos, N+1 sem índice) para a mensagem de vazio
    // aparecer antes da resposta chegar, mesmo com 190 grupos existentes.
    // Checagem síncrona (sem await): é exatamente a janela entre o mount e
    // a promise do fetch resolver que o bug vivia.
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(
      screen.queryByText(/Nenhuma viagem ou evento ainda/),
    ).not.toBeInTheDocument();
    expect(screen.getByText("carregando…")).toBeInTheDocument();

    // E depois que a resposta chega, o card aparece — não fica preso em
    // "carregando" para sempre.
    expect(await screen.findByText("Dubai")).toBeInTheDocument();
    expect(screen.queryByText("carregando…")).not.toBeInTheDocument();
  });

  it("catálogo genuinamente vazio ainda mostra a mensagem, depois de carregar", async () => {
    servirApi({ "/api/viagens": [], "/api/eventos": [] });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(
      await screen.findByText(/Nenhuma viagem ou evento ainda/),
    ).toBeInTheDocument();
  });

  it("a capa é a miniatura cacheada, não a prévia grande do loupe", async () => {
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    montar(<Trips onAbrir={vi.fn()} />);

    const img = (await screen.findByText("Dubai")).closest('[role="button"]')!
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

    const img = (await screen.findByText("Pantanal")).closest('[role="button"]')!
      .querySelector("img")!;
    fireEvent.error(img);

    expect(screen.getByText("capa fora de alcance")).toBeInTheDocument();
  });

  it("badge Mapa abre o grupo direto na vista de mapa, sem também disparar o clique do card (D-050)", async () => {
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    const onAbrir = vi.fn();
    montar(<Trips onAbrir={onAbrir} />);

    fireEvent.click(await screen.findByTitle("ver onde este grupo aconteceu"));

    expect(onAbrir).toHaveBeenCalledTimes(1);
    expect(onAbrir).toHaveBeenCalledWith({ trip_id: 1 }, "Dubai", "mapa");
  });

  it("clicar no card fora do badge abre na vista padrão (lista)", async () => {
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    const onAbrir = vi.fn();
    montar(<Trips onAbrir={onAbrir} />);

    fireEvent.click(await screen.findByText("Dubai"));

    expect(onAbrir).toHaveBeenCalledTimes(1);
    expect(onAbrir).toHaveBeenCalledWith({ trip_id: 1 }, "Dubai", undefined);
  });

  it.each(["Enter", " "])(
    "card abre por teclado com %s — não é <button> nativo, o app é teclado-first",
    async (tecla) => {
      servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
      const onAbrir = vi.fn();
      montar(<Trips onAbrir={onAbrir} />);

      const card = (await screen.findByText("Dubai")).closest(
        '[role="button"]',
      )!;
      fireEvent.keyDown(card, { key: tecla });

      expect(onAbrir).toHaveBeenCalledTimes(1);
      expect(onAbrir).toHaveBeenCalledWith({ trip_id: 1 }, "Dubai", undefined);
    },
  );

  it("badge Mapa não é descendente do card — foco/Tab alcança os dois independentemente", async () => {
    servirApi({ "/api/viagens": [grupo({})], "/api/eventos": [] });
    montar(<Trips onAbrir={vi.fn()} />);

    const card = (await screen.findByText("Dubai")).closest('[role="button"]')!;
    const badge = screen.getByTitle("ver onde este grupo aconteceu");
    expect(card.contains(badge)).toBe(false);
  });

  it("dois eventos com o mesmo nome mostram, cada um, de onde vieram (D-03/CONS-02)", async () => {
    servirApi({
      "/api/viagens": [],
      "/api/eventos": [
        grupo({ id: 1, nome: "Aniversário", metodo: "album_externo" }),
        grupo({ id: 2, nome: "Aniversário", metodo: "temporal" }),
      ],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(await screen.findByText("Álbum")).toBeInTheDocument();
    expect(screen.getByText("Evento detectado")).toBeInTheDocument();
  });

  it("evento sem nome colidido não ganha selo — sinal de ambiguidade, não decoração permanente", async () => {
    servirApi({
      "/api/viagens": [],
      "/api/eventos": [
        grupo({ id: 1, nome: "Aniversário", metodo: "album_externo" }),
        grupo({ id: 2, nome: "Formatura", metodo: "temporal" }),
      ],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    await screen.findByText("Aniversário");
    expect(screen.queryByText("Álbum")).not.toBeInTheDocument();
    expect(screen.queryByText("Evento detectado")).not.toBeInTheDocument();
  });

  it("duas viagens com o mesmo nome nunca ganham o selo — ele é só de Eventos", async () => {
    servirApi({
      "/api/viagens": [
        grupo({ id: 1, nome: "Praia", metodo: "album_externo" }),
        grupo({ id: 2, nome: "Praia", metodo: "temporal" }),
      ],
      "/api/eventos": [],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(await screen.findAllByText("Praia")).toHaveLength(2);
    expect(screen.queryByText("Álbum")).not.toBeInTheDocument();
    expect(screen.queryByText("Evento detectado")).not.toBeInTheDocument();
  });

  it("nomes que diferem só por caixa/espaço contam como colisão", async () => {
    servirApi({
      "/api/viagens": [],
      "/api/eventos": [
        grupo({ id: 1, nome: "Natal", metodo: "temporal" }),
        grupo({ id: 2, nome: "natal ", metodo: "temporal" }),
      ],
    });
    montar(<Trips onAbrir={vi.fn()} />);

    expect(await screen.findAllByText("Evento detectado")).toHaveLength(2);
  });
});
