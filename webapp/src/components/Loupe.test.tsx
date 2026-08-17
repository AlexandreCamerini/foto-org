import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Loupe from "./Loupe";
import type { Media } from "../api";
import { montar } from "../test/servidor";

function media(over: Record<string, unknown>): Media {
  return {
    id: 1,
    nome: "DSC_0100.jpg",
    ...over,
  } as Media;
}

/** A faixa de miniaturas do rodapé usa o mesmo `alt` da prévia principal
 *  (o nome do arquivo) — pegar a prévia pelo `src` de `api.previewUrl`
 *  evita ambiguidade entre os dois `<img>`. */
function getPreview(container: HTMLElement, id: number) {
  return container.querySelector<HTMLImageElement>(
    `img[src="/api/midia/${id}/preview"]`,
  );
}

describe("Loupe", () => {
  it("com a prévia carregando normalmente, o <img> de api.previewUrl está no documento", () => {
    const { container } = montar(
      <Loupe
        itens={[media({ id: 1, nome: "DSC_0100.jpg" })]}
        index={0}
        onNavegar={vi.fn()}
        onFechar={vi.fn()}
      />,
    );

    const img = getPreview(container, 1);
    expect(img).toBeInTheDocument();
    expect(img?.getAttribute("alt")).toBe("DSC_0100.jpg");
  });

  it("prévia que falha ao carregar mostra as duas frases e o glifo ⊘, sem o <img>", () => {
    const { container } = montar(
      <Loupe
        itens={[media({ id: 1, nome: "DSC_0100.jpg" })]}
        index={0}
        onNavegar={vi.fn()}
        onFechar={vi.fn()}
      />,
    );

    fireEvent.error(getPreview(container, 1)!);

    expect(getPreview(container, 1)).not.toBeInTheDocument();
    expect(
      screen.getByText(
        "Não foi possível carregar esta imagem em alta resolução.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "O arquivo pode ter sido movido, renomeado ou corrompido desde a catalogação.",
      ),
    ).toBeInTheDocument();
    const glifo = screen.getByText("⊘");
    expect(glifo).toBeInTheDocument();
    expect(glifo).toHaveAttribute("aria-hidden");
  });

  it("no estado de erro, clicar na área central não alterna o zoom (não há <img> para reaparecer)", () => {
    const { container } = montar(
      <Loupe
        itens={[media({ id: 1, nome: "DSC_0100.jpg" })]}
        index={0}
        onNavegar={vi.fn()}
        onFechar={vi.fn()}
      />,
    );

    fireEvent.error(getPreview(container, 1)!);

    const areaCentral = screen
      .getByText("Não foi possível carregar esta imagem em alta resolução.")
      .closest("div.flex.min-h-0")!;
    fireEvent.click(areaCentral);

    expect(getPreview(container, 1)).not.toBeInTheDocument();
  });

  it("navegar para outro índice reseta o estado de falha — a foto seguinte não herda a falha da anterior", () => {
    const itens = [
      media({ id: 1, nome: "DSC_0100.jpg" }),
      media({ id: 2, nome: "DSC_0200.jpg" }),
    ];
    const { container, rerender } = montar(
      <Loupe itens={itens} index={0} onNavegar={vi.fn()} onFechar={vi.fn()} />,
    );

    fireEvent.error(getPreview(container, 1)!);
    expect(
      screen.getByText(
        "Não foi possível carregar esta imagem em alta resolução.",
      ),
    ).toBeInTheDocument();

    rerender(
      <Loupe itens={itens} index={1} onNavegar={vi.fn()} onFechar={vi.fn()} />,
    );

    expect(
      screen.queryByText(
        "Não foi possível carregar esta imagem em alta resolução.",
      ),
    ).not.toBeInTheDocument();
    expect(getPreview(container, 2)).toBeInTheDocument();
  });

  it("cabeçalho e rodapé continuam renderizando no estado de erro", () => {
    const { container } = montar(
      <Loupe
        itens={[media({ id: 1, nome: "DSC_0100.jpg" })]}
        index={0}
        onNavegar={vi.fn()}
        onFechar={vi.fn()}
      />,
    );

    fireEvent.error(getPreview(container, 1)!);

    expect(screen.getByText("DSC_0100.jpg")).toBeInTheDocument();
    expect(screen.getByText("1 / 1")).toBeInTheDocument();
    expect(
      container.querySelector('img[src="/api/midia/1/thumb"]'),
    ).toBeInTheDocument();
  });
});
