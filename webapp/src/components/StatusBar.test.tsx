import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import StatusBar from "./StatusBar";
import type { Job } from "../hooks/useJob";
import { montar, servirApi, ROTAS_BASE } from "../test/servidor";

function job(sobrescrever: Partial<Job> = {}): Job {
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
    pausar: vi.fn(),
    continuar: vi.fn(),
    ...sobrescrever,
  } as Job;
}

describe("StatusBar", () => {
  it("mostra Pausar durante um scan e chama o endpoint ao clicar", async () => {
    servirApi(ROTAS_BASE);
    const pausar = vi.fn();
    const usuario = userEvent.setup();
    montar(
      <StatusBar
        job={job({
          estado: {
            status: "rodando",
            tipo: "scan",
            processados: 4,
            vistos: 10,
          },
          rodando: true,
          pausar,
        })}
      />,
    );

    const botao = await screen.findByRole("button", { name: "Pausar" });
    await usuario.click(botao);
    expect(pausar).toHaveBeenCalledTimes(1);
  });

  it("mostra Continuar e o texto honesto quando o scan está pausado", async () => {
    servirApi(ROTAS_BASE);
    const continuar = vi.fn();
    const usuario = userEvent.setup();
    montar(
      <StatusBar
        job={job({
          estado: {
            status: "pausado",
            tipo: "scan",
            processados: 4,
            vistos: 10,
          },
          rodando: false,
          continuar,
        })}
      />,
    );

    expect(await screen.findByText(/Pausado/)).toBeInTheDocument();
    const botao = screen.getByRole("button", { name: "Continuar" });
    await usuario.click(botao);
    expect(continuar).toHaveBeenCalledTimes(1);
  });

  it("continua permitindo cancelar mesmo pausado", async () => {
    servirApi(ROTAS_BASE);
    const cancelar = vi.fn();
    montar(
      <StatusBar
        job={job({
          estado: { status: "pausado", tipo: "scan" },
          rodando: false,
          cancelar,
        })}
      />,
    );
    expect(
      await screen.findByRole("button", { name: "cancelar" }),
    ).toBeInTheDocument();
  });

  it("não oferece pausar para um job que não é scan (evita 409 previsível)", async () => {
    servirApi(ROTAS_BASE);
    montar(
      <StatusBar
        job={job({
          estado: { status: "rodando", tipo: "import", processados: 1 },
          rodando: true,
        })}
      />,
    );
    await screen.findByRole("button", { name: "cancelar" });
    expect(
      screen.queryByRole("button", { name: "Pausar" }),
    ).not.toBeInTheDocument();
  });

  it("scan concluído oferece o próximo passo: gerar sugestões", async () => {
    servirApi(ROTAS_BASE);
    const gerarSugestoes = vi.fn();
    const usuario = userEvent.setup();
    montar(
      <StatusBar
        job={job({
          estado: { status: "concluido", tipo: "scan", processados: 42 },
          gerarSugestoes,
        })}
      />,
    );
    const botao = await screen.findByRole("button", {
      name: "Gerar sugestões",
    });
    await usuario.click(botao);
    expect(gerarSugestoes).toHaveBeenCalledTimes(1);
  });

  it("importação concluída também oferece gerar sugestões", async () => {
    servirApi(ROTAS_BASE);
    montar(
      <StatusBar
        job={job({
          estado: { status: "concluido", tipo: "import", processados: 7 },
        })}
      />,
    );
    expect(
      await screen.findByRole("button", { name: "Gerar sugestões" }),
    ).toBeInTheDocument();
  });

  it("sugestões concluídas não oferecem gerar sugestões de novo", async () => {
    servirApi(ROTAS_BASE);
    montar(
      <StatusBar
        job={job({
          estado: { status: "concluido", tipo: "sugestoes", processados: 9 },
        })}
      />,
    );
    await screen.findByText(/Concluído/);
    expect(
      screen.queryByRole("button", { name: "Gerar sugestões" }),
    ).not.toBeInTheDocument();
  });

  it("a barra de progresso é proporcional a processados/vistos", async () => {
    servirApi(ROTAS_BASE);
    montar(
      <StatusBar
        job={job({
          estado: {
            status: "rodando",
            tipo: "scan",
            processados: 5,
            vistos: 20,
          },
          rodando: true,
        })}
      />,
    );
    const barra = await screen.findByTestId("barra-progresso");
    expect(barra).toHaveStyle({ width: "25%" });
  });

  it("sem total conhecido a barra fica indeterminada, não fingindo progresso", async () => {
    servirApi(ROTAS_BASE);
    montar(
      <StatusBar
        job={job({
          estado: { status: "rodando", tipo: "scan", processados: 3 },
          rodando: true,
        })}
      />,
    );
    await screen.findByText(/Varrendo/);
    expect(screen.queryByTestId("barra-progresso")).not.toBeInTheDocument();
  });
});
