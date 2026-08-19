import { fireEvent, screen } from "@testing-library/react";
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

  it("grupo VARIANTE (RAW+JPEG) orienta a manter os dois, não soma no total recuperável e o botão avisa a consequência", async () => {
    servirApi({ "/api/duplicatas": [grupo({
      id: 9, nivel: "variante", rotulo: "RAW + JPEG do mesmo clique",
      bytes_recuperaveis: 5_000_000,
      membros: [
        membro({ nome: "IMG_1.CR3", tamanho: 30_000_000 }),
        membro({
          member_id: 2, media_id: 2, nome: "IMG_1.JPG", tamanho: 5_000_000,
        }),
      ],
    })] });
    montar(<Duplicates job={jobParado()} />);

    // Orientação específica, não o texto genérico de "escolher uma cópia".
    // Curta o bastante para não truncar no span de uma linha que a carrega
    // (achado da revisão fresh-eyes: a primeira versão, mais longa, cortava
    // antes do aviso "marcar uma exclui a outra"). O fragmento do aviso é
    // exclusivo do cabeçalho — o texto secundário da lista é mais curto e
    // não repete essa frase, por isso findByText (singular) é seguro aqui.
    expect(
      await screen.findByText(/marcar uma exclui a outra do plano/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Marque a cópia a manter como principal."),
    ).not.toBeInTheDocument();

    // Cabeçalho não soma bytes de VARIANTE como "recuperáveis" — só há este
    // grupo no catálogo, e ele não deve contribuir para o total.
    expect(await screen.findByText(/0 B recuperáveis/)).toBeInTheDocument();

    // Mesmo sinal visual de alerta que "sequencia" já tinha — os dois
    // níveis compartilham o mesmo risco (excluir por engano o que deveria
    // ficar). O rótulo aparece 2x (item da lista + cabeçalho do painel,
    // grupo único selecionado por padrão); só o item da lista carrega a cor.
    const rotulos = screen.getAllByText("RAW + JPEG do mesmo clique");
    expect(rotulos.some((el) => el.className.includes("text-atencao")))
      .toBe(true);

    // Botão de cada membro (nenhum é principal ainda) avisa a consequência
    // em vez do rótulo genérico "Manter esta".
    const botoes = screen.getAllByText("Manter só esta");
    expect(botoes).toHaveLength(2);
    for (const botao of botoes) {
      expect(botao).toHaveAttribute(
        "title", expect.stringContaining("sai do plano de cópia"),
      );
    }
  });

  it("filtro 'RAW + JPEG' existe e isola só os grupos VARIANTE", async () => {
    servirApi({ "/api/duplicatas": [
      grupo({ id: 1, nivel: "exato", rotulo: "Bytes iguais" }),
      grupo({ id: 9, nivel: "variante", rotulo: "RAW + JPEG do mesmo clique" }),
    ] });
    montar(<Duplicates job={jobParado()} />);

    await screen.findByText("RAW + JPEG do mesmo clique");
    fireEvent.click(screen.getByRole("button", { name: "RAW + JPEG" }));

    // Grupo variante permanece — aparece na lista e, sendo o único visível,
    // também no cabeçalho do painel de detalhe (daí AllBy).
    expect(screen.getAllByText("RAW + JPEG do mesmo clique").length).toBeGreaterThan(0);
    expect(screen.queryByText("Bytes iguais")).not.toBeInTheDocument();
  });

  it("membro cuja prévia falha mostra 'imagem indisponível' com a explicação completa no title, sem afetar o outro membro do grupo", async () => {
    servirApi({
      "/api/duplicatas": [
        grupo({
          membros: [
            membro({}),
            membro({ member_id: 2, media_id: 2, nome: "b.jpg" }),
          ],
        }),
      ],
    });
    const { container } = montar(<Duplicates job={jobParado()} />);

    await screen.findByText("a.jpg");
    const imgA = container.querySelector<HTMLImageElement>(
      'img[src="/api/midia/1/preview"]',
    )!;
    const imgB = container.querySelector<HTMLImageElement>(
      'img[src="/api/midia/2/preview"]',
    )!;
    expect(imgA).toBeInTheDocument();
    expect(imgB).toBeInTheDocument();

    fireEvent.error(imgA);

    // Só o membro A degrada — o <img> de B continua no documento.
    expect(
      container.querySelector('img[src="/api/midia/1/preview"]'),
    ).not.toBeInTheDocument();
    expect(
      container.querySelector('img[src="/api/midia/2/preview"]'),
    ).toBeInTheDocument();

    expect(screen.getByText("imagem indisponível")).toBeInTheDocument();
    expect(screen.getByText("⊘")).toBeInTheDocument();
    expect(screen.getByText("imagem indisponível").closest("div")).toHaveAttribute(
      "title",
      "O arquivo pode ter sido movido, renomeado ou corrompido desde a catalogação.",
    );
  });

  it("bloco de erro usa bg-cartao, não bg-black — não lê como 'ainda carregando'", async () => {
    servirApi({ "/api/duplicatas": [grupo({})] });
    const { container } = montar(<Duplicates job={jobParado()} />);

    const img = await screen.findByText("a.jpg").then(
      () =>
        container.querySelector<HTMLImageElement>(
          'img[src="/api/midia/1/preview"]',
        )!,
    );
    expect(img.className).toContain("bg-black");

    fireEvent.error(img);

    const bloco = screen.getByText("imagem indisponível").closest("div")!;
    expect(bloco.className).toContain("bg-cartao");
    expect(bloco.className).not.toContain("bg-black");
  });

  it("figcaption com nome, tamanho e botão de papel continua renderizando no estado de erro", async () => {
    servirApi({
      "/api/duplicatas": [
        grupo({ membros: [membro({}), membro({ member_id: 2, media_id: 2, nome: "b.jpg" })] }),
      ],
    });
    const { container } = montar(<Duplicates job={jobParado()} />);

    await screen.findByText("a.jpg");
    const imgA = container.querySelector<HTMLImageElement>(
      'img[src="/api/midia/1/preview"]',
    )!;
    fireEvent.error(imgA);

    expect(screen.getByText("a.jpg")).toBeInTheDocument();
    expect(screen.getAllByText("Manter esta").length).toBeGreaterThan(0);
  });
});
