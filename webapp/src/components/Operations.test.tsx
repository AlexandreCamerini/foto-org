import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Operations from "./Operations";
import type { Job } from "../hooks/useJob";
import { montar, servirApi } from "../test/servidor";

function jobParado(sobrescrever: Partial<Job> = {}): Job {
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
    ...sobrescrever,
  } as Job;
}

function plano(dry_run_em: string | null) {
  return {
    id: 1,
    nome: "Cópia para /destino",
    status: "planejada",
    dry_run_em,
    criado_em: "2026-07-26T10:00:00",
    total_itens: 2,
    concluidos: 0,
    com_conflito: 0,
    com_erro: 0,
  };
}

const ITENS = [
  {
    id: 1,
    origem: "/fotos/2019/DSC_0001.jpg",
    destino: "/destino/Viagens/2019/DSC_0001.jpg",
    status: "planejada",
    conflito: null,
    erro: null,
  },
  {
    id: 2,
    origem: "/fotos/whatsapp/IMG-1.jpg",
    destino: "/destino/Familia/2024/IMG-1.jpg",
    status: "planejada",
    conflito: null,
    erro: null,
  },
];

function rotas(dry_run_em: string | null) {
  return {
    "/api/operacoes": [plano(dry_run_em)],
    "/api/operacoes/1": { ...plano(dry_run_em), itens: ITENS },
    "/api/operacoes/1/auditoria": [
      {
        id: 1,
        quando: "2026-07-26T10:00:00",
        acao: "plano_criado",
        resultado: "ok",
        detalhe: null,
      },
    ],
  };
}

describe("Operações", () => {
  it("sem dry-run, copiar fica bloqueado e a tela diz por quê", async () => {
    servirApi(rotas(null));
    const usuario = userEvent.setup();
    montar(<Operations job={jobParado()} />);

    await usuario.click(await screen.findByText("Cópia para /destino"));

    const copiar = await screen.findByRole("button", {
      name: /Copiar 2 arquivos/,
    });
    expect(copiar).toBeDisabled();
    expect(copiar).toHaveAttribute("title", "Rode o dry-run antes de copiar");
    expect(
      screen.getByText("sem dry-run — nada pode ser copiado ainda"),
    ).toBeInTheDocument();
  });

  it("com dry-run, copiar libera e dispara o plano certo", async () => {
    servirApi(rotas("2026-07-26T10:05:00"));
    const executarPlano = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(<Operations job={jobParado({ executarPlano })} />);

    await usuario.click(await screen.findByText("Cópia para /destino"));
    const copiar = await screen.findByRole("button", {
      name: /Copiar 2 arquivos/,
    });
    expect(copiar).toBeEnabled();

    await usuario.click(copiar);
    expect(executarPlano).toHaveBeenCalledWith(1);
  });

  it("o diff mostra o caminho relativo, sem o prefixo comum das árvores",
    async () => {
      servirApi(rotas(null));
      const usuario = userEvent.setup();
      montar(<Operations job={jobParado()} />);

      await usuario.click(await screen.findByText("Cópia para /destino"));

      expect(await screen.findByText("2019/DSC_0001.jpg")).toBeInTheDocument();
      expect(screen.getByText("→ Viagens/2019/DSC_0001.jpg"))
        .toBeInTheDocument();
      expect(screen.getByText("de /fotos")).toBeInTheDocument();
      expect(screen.getByText("para /destino")).toBeInTheDocument();
    });

  it("estado vazio orienta a próxima ação", async () => {
    servirApi({ "/api/operacoes": [] });
    montar(<Operations job={jobParado()} />);
    expect(
      await screen.findByText("Aprove sugestões na aba Revisão", {
        exact: false,
      }),
    ).toBeInTheDocument();
  });
});
