import { screen, waitFor } from "@testing-library/react";
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
      pastaAtual={null}
      onSelecionarPasta={() => {}}
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
      pastaAtual={null}
      onSelecionarPasta={() => {}}
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

describe("Sidebar — reapontar fonte que mudou de lugar", () => {
  const FONTE_MOVIDA = {
    id: 1,
    caminho: "/Volumes/photo/DCIM",
    apelido: "photo",
    tipo: "pasta" as const,
    disponivel: false,
    fotos: 45397,
  };
  const REAPONTAMENTO = {
    source_id: 1,
    apelido: "photo",
    prefixo_antigo: "/Volumes/photo/DCIM",
    prefixo_novo: "/Volumes/photo 1/DCIM",
  };
  const PREVIA = {
    source_id: 1,
    apelido: "photo",
    prefixo_antigo: "/Volumes/photo/DCIM",
    prefixo_novo: "/Volumes/photo 1/DCIM",
    total_media_files: 45397,
    total_ignoradas_sem_prefixo: 0,
    amostra: [
      { antigo: "/Volumes/photo/DCIM/a.jpg", novo: "/Volumes/photo 1/DCIM/a.jpg" },
    ],
  };

  it("sem fonte movida, nenhuma affordance aparece", async () => {
    servirApi(ROTAS_BASE);
    montar(<Sidebar fonteAtual={null}
      pastaAtual={null}
      onSelecionarPasta={() => {}} onSelecionar={vi.fn()} job={jobParado()} />);

    await screen.findByText("Todas as fotos");
    expect(screen.queryByText(/mudou de lugar/)).not.toBeInTheDocument();
  });

  it("fonte cujo volume remontou mostra o botão, com prévia antes de confirmar", async () => {
    servirApi({
      ...ROTAS_BASE,
      "/api/fontes": [FONTE_MOVIDA],
      "/api/fontes/reapontamentos": [REAPONTAMENTO],
      "/api/fontes/1/reapontar/preview": PREVIA,
    });
    const usuario = userEvent.setup();
    montar(<Sidebar fonteAtual={null}
      pastaAtual={null}
      onSelecionarPasta={() => {}} onSelecionar={vi.fn()} job={jobParado()} />);

    await usuario.click(await screen.findByText(/mudou de lugar/));

    expect(await screen.findByText(/45\.397 arquivo\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/Volumes\/photo\/DCIM/)).toBeInTheDocument();
    expect(screen.getByText(/Volumes\/photo 1\/DCIM/)).toBeInTheDocument();
  });

  it("confirmar reaponta e fecha o modal", async () => {
    const chamadas = servirApi({
      ...ROTAS_BASE,
      "/api/fontes": [FONTE_MOVIDA],
      "/api/fontes/reapontamentos": [REAPONTAMENTO],
      "/api/fontes/1/reapontar/preview": PREVIA,
      "/api/fontes/1/reapontar": {
        source_id: 1,
        prefixo_antigo: "/Volumes/photo/DCIM",
        prefixo_novo: "/Volumes/photo 1/DCIM",
        linhas_media_files: 45397,
        audit_log_id: 1,
      },
    });
    const usuario = userEvent.setup();
    montar(<Sidebar fonteAtual={null}
      pastaAtual={null}
      onSelecionarPasta={() => {}} onSelecionar={vi.fn()} job={jobParado()} />);

    await usuario.click(await screen.findByText(/mudou de lugar/));
    await screen.findByText(/45\.397 arquivo\(s\)/);
    await usuario.click(screen.getByRole("button", { name: "Reapontar" }));

    await waitFor(() =>
      expect(screen.queryByText(/Fonte mudou de lugar/)).not.toBeInTheDocument(),
    );
    const reescrita = chamadas.find((c) => c.caminho === "/api/fontes/1/reapontar");
    expect(reescrita?.corpo).toEqual({ confirmar: true });
  });

  it("cancelar não chama a escrita", async () => {
    const chamadas = servirApi({
      ...ROTAS_BASE,
      "/api/fontes": [FONTE_MOVIDA],
      "/api/fontes/reapontamentos": [REAPONTAMENTO],
      "/api/fontes/1/reapontar/preview": PREVIA,
    });
    const usuario = userEvent.setup();
    montar(<Sidebar fonteAtual={null}
      pastaAtual={null}
      onSelecionarPasta={() => {}} onSelecionar={vi.fn()} job={jobParado()} />);

    await usuario.click(await screen.findByText(/mudou de lugar/));
    await screen.findByText(/45\.397 arquivo\(s\)/);
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByText(/Fonte mudou de lugar/)).not.toBeInTheDocument();
    expect(
      chamadas.some((c) => c.caminho === "/api/fontes/1/reapontar" && c.metodo === "POST"),
    ).toBe(false);
  });
});
