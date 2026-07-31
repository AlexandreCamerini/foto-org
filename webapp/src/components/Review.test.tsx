import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Review from "./Review";
import type { Job } from "../hooks/useJob";
import { erro, montar, servirApi } from "../test/servidor";

function jobParado(): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(),
    importarApple: vi.fn(),
    importarTakeout: vi.fn(),
    gerarSugestoes: vi.fn(),
    detectarDuplicatas: vi.fn(),
    executarPlano: vi.fn(async () => {}),
    cancelar: vi.fn(),
  } as unknown as Job;
}

/** Duas viagens e uma foto solta: o suficiente para ver o agrupamento. */
const SUGESTOES = {
  contagens: { pendente: 3 },
  itens: [
    {
      id: 1, media_id: 11, nome: "IMG_9100.jpg", pasta: "/fotos/iPhone",
      destino: "Viagens/2024 - França", nivel: "alta", status: "pendente",
      data_capturada: "2024-05-04T10:30:00", camera: "Apple iPhone 15 Pro",
      gps_estimado: false,
    },
    {
      id: 2, media_id: 12, nome: "DSC_0100.jpg", pasta: "/fotos/Camera",
      destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
      data_capturada: "2024-05-04T10:32:00", camera: "Canon EOS R5",
      gps_estimado: true,
    },
    {
      id: 3, media_id: 13, nome: "captura.png", pasta: "/fotos/Diversos",
      destino: "Não classificadas/2026/julho", nivel: "baixa",
      status: "pendente", data_capturada: null, camera: null,
      gps_estimado: false,
    },
  ],
};

const DETALHE_12 = {
  id: 12, nome: "DSC_0100.jpg",
  sugestao: {
    id: 2, destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
    evidencias: [
      {
        campo: "cidade", origem: "vizinhanca_temporal", valor: "Avignon",
        nivel: "media", score: 0.75,
        justificativa:
          "GPS herdado de 'IMG_9100.jpg' (Apple iPhone 15 Pro) — tirada a 2min de distância",
      },
    ],
  },
};

describe("Review", () => {
  it("agrupa por destino em vez de listar tudo plano", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText("Viagens/2024 - França")).toBeInTheDocument();
    expect(screen.getByText("Não classificadas/2026/julho")).toBeInTheDocument();
    expect(screen.getByText("3 em 2 grupos")).toBeInTheDocument();
    // Aprovação em lote é por grupo, não uma varredura global.
    expect(screen.getByText("Aprovar 2")).toBeInTheDocument();
    expect(screen.getByText("Aprovar 1")).toBeInTheDocument();
  });

  it("mostra o nome do arquivo, não o caminho que o truncava", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText("DSC_0100.jpg")).toBeInTheDocument();
    expect(screen.getByText(/Canon EOS R5/)).toBeInTheDocument();
  });

  it("avisa quantas fotos do grupo têm lugar estimado", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText(/1 com lugar estimado/)).toBeInTheDocument();
  });

  it("o porquê é buscado só quando o usuário pergunta", async () => {
    const chamadas = servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/midia/12": DETALHE_12,
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await screen.findByText("DSC_0100.jpg");
    // Nada de 3 requisições de detalhe no carregamento.
    expect(chamadas.filter((c) => c.caminho.startsWith("/api/midia/"))).toHaveLength(0);

    await usuario.click(
      screen.getByTitle("Por que este destino para DSC_0100.jpg?"),
    );

    expect(
      await screen.findByText(/herdado de 'IMG_9100.jpg'/),
    ).toBeInTheDocument();
    expect(chamadas.filter((c) => c.caminho === "/api/midia/12")).toHaveLength(1);
  });

  it("grupo fechado esconde as linhas e mantém o cabeçalho", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await usuario.click(await screen.findByText("Viagens/2024 - França"));
    expect(screen.queryByText("DSC_0100.jpg")).not.toBeInTheDocument();
    expect(screen.getByText("Viagens/2024 - França")).toBeInTheDocument();
  });

  it("edita o destino inline e salva via PATCH", async () => {
    const chamadas = servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/2/destino": {
        id: 2, media_id: 12, nome: "DSC_0100.jpg", pasta: "/fotos/Camera",
        destino: "Viagens/2024 - França (corrigida)", nivel: "media",
        status: "editada",
      },
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await screen.findByText("DSC_0100.jpg");
    await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));

    const campo = screen.getByDisplayValue("Viagens/2024 - França");
    await usuario.clear(campo);
    await usuario.type(campo, "Viagens/2024 - França (corrigida)");
    await usuario.click(screen.getByText("Salvar"));

    await waitFor(() =>
      expect(
        chamadas.find((c) => c.caminho === "/api/sugestoes/2/destino"),
      ).toBeTruthy(),
    );
    const chamada = chamadas.find(
      (c) => c.caminho === "/api/sugestoes/2/destino",
    )!;
    expect(chamada.metodo).toBe("PATCH");
    expect(chamada.corpo).toEqual({
      destino: "Viagens/2024 - França (corrigida)",
    });
  });

  it("mostra a mensagem do servidor quando o destino editado é inválido (422)",
    async () => {
      servirApi({
        "/api/sugestoes": SUGESTOES,
        "/api/sugestoes/2/destino": erro(422, "segmento proibido em '../etc'"),
      });
      const usuario = userEvent.setup();
      montar(<Review job={jobParado()} />);

      await screen.findByText("DSC_0100.jpg");
      await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));

      const campo = screen.getByDisplayValue("Viagens/2024 - França");
      await usuario.clear(campo);
      await usuario.type(campo, "../etc");
      await usuario.click(screen.getByText("Salvar"));

      expect(
        await screen.findByText("segmento proibido em '../etc'"),
      ).toBeInTheDocument();
      // O campo continua editável — o erro não deve fechar a edição.
      expect(screen.getByDisplayValue("../etc")).toBeInTheDocument();
    });

  it("cancelar a edição descarta o valor digitado", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await screen.findByText("DSC_0100.jpg");
    await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));
    await usuario.click(screen.getByText("Cancelar"));

    expect(screen.getByText("DSC_0100.jpg")).toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("Viagens/2024 - França"),
    ).not.toBeInTheDocument();
  });
});
