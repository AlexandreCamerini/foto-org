import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Duplicates from "./Duplicates";
import type { Job } from "../hooks/useJob";
import { montar, servirApi } from "../test/servidor";

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

function membro(over: Record<string, unknown>) {
  return {
    member_id: 1, media_id: 1, nome: "a.jpg", caminho: "/fotos/a.jpg",
    tamanho: 1000, papel: "indefinido", source_id: 1,
    ...over,
  };
}

function grupo(over: Record<string, unknown>) {
  return {
    id: 1, nivel: "exato", rotulo: "Idênticos", decidido: false,
    resolvido_automaticamente: false, bytes_recuperaveis: 1000, n_fontes: 1,
    membros: [membro({}), membro({ member_id: 2, media_id: 2, nome: "b.jpg" })],
    ...over,
  };
}

describe("Duplicates", () => {
  it("grupo EXATO resolvido pelo algoritmo mostra rótulo distinto de decisão humana", async () => {
    // Com um grupo só, ele aparece na lista E no painel de detalhe (seleção
    // padrão) — daí getAllByText em vez de getByText.
    servirApi({ "/api/duplicatas": [grupo({
      resolvido_automaticamente: true,
      membros: [
        membro({ papel: "principal" }),
        membro({ member_id: 2, media_id: 2, nome: "b.jpg", papel: "versao" }),
      ],
    })] });
    montar(<Duplicates job={jobParado()} />);

    expect(await screen.findAllByText(/resolvido automaticamente/))
      .not.toHaveLength(0);
    expect(screen.queryAllByText(/decidido ✓/)).toHaveLength(0);
  });

  it("grupo decidido por humano continua mostrando 'decidido ✓', sem o rótulo automático", async () => {
    servirApi({ "/api/duplicatas": [grupo({
      decidido: true,
      resolvido_automaticamente: false,
      membros: [
        membro({ papel: "principal" }),
        membro({ member_id: 2, media_id: 2, nome: "b.jpg", papel: "versao" }),
      ],
    })] });
    montar(<Duplicates job={jobParado()} />);

    expect(await screen.findAllByText(/decidido ✓/)).not.toHaveLength(0);
    expect(screen.queryAllByText(/resolvido automaticamente/)).toHaveLength(0);
  });

  it("único grupo nasce selecionado e explica a decisão automática, com override manual disponível", async () => {
    servirApi({ "/api/duplicatas": [grupo({
      resolvido_automaticamente: true,
      membros: [
        membro({ papel: "principal" }),
        membro({ member_id: 2, media_id: 2, nome: "b.jpg", papel: "versao" }),
      ],
    })] });
    montar(<Duplicates job={jobParado()} />);

    expect(
      await screen.findByText(/o algoritmo já marcou a principal/),
    ).toBeInTheDocument();
    // A cópia não escolhida continua com o botão de override manual.
    expect(screen.getByText("Manter esta")).toBeInTheDocument();
  });
});
