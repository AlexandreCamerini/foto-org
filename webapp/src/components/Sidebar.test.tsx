import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Sidebar from "./Sidebar";
import type { Job } from "../hooks/useJob";
import { montar, servirApi, ROTAS_BASE } from "../test/servidor";

function jobParado(sobrescrever: Partial<Job> = {}): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(),
    importarApple: vi.fn(async () => {}),
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

describe("Sidebar — importar Apple Fotos", () => {
  it("avisa sobre leitura somente e Acesso Total ao Disco antes de importar", async () => {
    servirApi(ROTAS_BASE);
    const importarApple = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(
      <Sidebar
        fonteAtual={null}
        onSelecionar={vi.fn()}
        job={jobParado({ importarApple })}
      />,
    );

    await usuario.click(await screen.findByText("Importar catálogo…"));
    await usuario.click(screen.getByText(/Apple Fotos/));

    // O aviso aparece ANTES de disparar a importação.
    expect(importarApple).not.toHaveBeenCalled();
    expect(screen.getByText(/somente leitura/)).toBeInTheDocument();
    expect(screen.getByText(/Acesso Total ao Disco/)).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    expect(importarApple).toHaveBeenCalledTimes(1);
  });

  it("cancelar o aviso não dispara a importação", async () => {
    servirApi(ROTAS_BASE);
    const importarApple = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(
      <Sidebar
        fonteAtual={null}
        onSelecionar={vi.fn()}
        job={jobParado({ importarApple })}
      />,
    );

    await usuario.click(await screen.findByText("Importar catálogo…"));
    await usuario.click(screen.getByText(/Apple Fotos/));
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(importarApple).not.toHaveBeenCalled();
    expect(screen.queryByText(/Acesso Total ao Disco/)).not.toBeInTheDocument();
  });
});
