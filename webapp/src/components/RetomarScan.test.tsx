import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RetomarScan from "./RetomarScan";
import type { Job } from "../hooks/useJob";
import { montar, servirApi, ROTAS_BASE } from "../test/servidor";

function job(sobrescrever: Partial<Job> = {}): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(async () => {}),
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

const INTERROMPIDO = {
  source_id: 9,
  caminho: "/Users/eu",
  apelido: "acamerini",
  disponivel: true,
  quando: "2026-08-06T00:35:00",
  vistos: 93408,
  indexados: 93400,
};

describe("RetomarScan", () => {
  it("não renderiza nada quando não há varredura interrompida", async () => {
    servirApi(ROTAS_BASE);
    montar(<RetomarScan job={job()} />);
    expect(screen.queryByTestId("retomar-scan")).toBeNull();
  });

  it("oferece a retomada e dispara o scan no mesmo caminho", async () => {
    servirApi({ ...ROTAS_BASE, "/api/scan/interrompidos": [INTERROMPIDO] });
    const escanear = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(<RetomarScan job={job({ escanear })} />);

    await screen.findByText(/foi interrompida/);
    await usuario.click(screen.getByRole("button", { name: "Retomar" }));
    expect(escanear).toHaveBeenCalledWith("/Users/eu");
  });

  it("desabilita Retomar quando o volume da fonte está fora de alcance", async () => {
    servirApi({
      ...ROTAS_BASE,
      "/api/scan/interrompidos": [{ ...INTERROMPIDO, disponivel: false }],
    });
    montar(<RetomarScan job={job()} />);
    const botao = await screen.findByRole("button", { name: "Retomar" });
    expect(botao).toBeDisabled();
  });

  it("dispensar esconde a pendência sem chamar o servidor", async () => {
    const chamadas = servirApi({
      ...ROTAS_BASE,
      "/api/scan/interrompidos": [INTERROMPIDO],
    });
    const usuario = userEvent.setup();
    montar(<RetomarScan job={job()} />);

    await screen.findByText(/foi interrompida/);
    await usuario.click(screen.getByRole("button", { name: "✕" }));
    expect(screen.queryByTestId("retomar-scan")).toBeNull();
    expect(chamadas.every((c) => c.metodo === "GET")).toBe(true);
  });
});
