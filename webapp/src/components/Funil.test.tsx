import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Funil from "./Funil";
import { montar, servirApi } from "../test/servidor";

// Os números do acervo real na medição de 2026-08-04, que é o caso que
// motivou o funil: cinco telas mostravam cinco destes sem dizer qual era qual.
const FUNIL_REAL = {
  conhecidas: 190_828,
  alcancaveis: 94_557,
  organizaveis: 26_023,
  registros: 197_338,
};

describe("Funil", () => {
  it("mostra os três degraus do catálogo na ordem em que estreitam", async () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    montar(<Funil />);

    expect(await screen.findByText("190.828")).toBeInTheDocument();
    expect(screen.getByText("conhecidas")).toBeInTheDocument();
    expect(screen.getByText("94.557")).toBeInTheDocument();
    expect(screen.getByText("alcançáveis")).toBeInTheDocument();
    expect(screen.getByText("26.023")).toBeInTheDocument();
    expect(screen.getByText("organizáveis")).toBeInTheDocument();
  });

  it("o degrau 'no filtro' aparece só quando o filtro muda o conjunto", async () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    const vista = montar(<Funil noFiltro={20_832} />);
    expect(await screen.findByText("20.832")).toBeInTheDocument();
    expect(screen.getByText("no filtro")).toBeInTheDocument();
    vista.unmount();

    // Filtro que não tirou nada não vira degrau: repetir o mesmo número com
    // outro nome é exatamente o defeito que o funil veio corrigir.
    servirApi({ "/api/funil": FUNIL_REAL });
    montar(<Funil noFiltro={FUNIL_REAL.organizaveis} />);
    await screen.findByText("26.023");
    expect(screen.queryByText("no filtro")).not.toBeInTheDocument();
  });

  it("o degrau explica de onde vem a diferença para o anterior", async () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    montar(<Funil />);

    // 197.338 registros e 190.828 fotos: a explicação precisa estar na tela,
    // senão a diferença lê como erro.
    const conhecidas = await screen.findByTitle(/197.338 registros/);
    expect(conhecidas).toHaveAccessibleDescription;
    expect(screen.getByTitle(/não serem acervo/)).toBeInTheDocument();
  });

  it("clicar num degrau navega para o conjunto que ele descreve", async () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    const aoIrPara = vi.fn();
    montar(<Funil aoIrPara={aoIrPara} />);

    fireEvent.click(await screen.findByText("26.023"));
    expect(aoIrPara).toHaveBeenCalledWith("organizaveis");

    fireEvent.click(screen.getByText("190.828"));
    expect(aoIrPara).toHaveBeenCalledWith("tudo");
  });

  it("sem navegação disponível, os degraus não fingem ser botões", async () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    const { container } = montar(<Funil />);
    await screen.findByText("190.828");
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("a variante compacta do rodapé não ocupa espaço enquanto conta", () => {
    servirApi({ "/api/funil": FUNIL_REAL });
    const { container } = montar(<Funil compacto />);
    // A contagem custa ~1,4s no acervo real; um "contando…" piscando no
    // rodapé a cada tela seria ruído.
    expect(container.textContent).toBe("");
  });
});
