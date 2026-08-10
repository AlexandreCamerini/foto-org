import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ArvoreDePastas from "./ArvoreDePastas";
import { montar, servirApi } from "../test/servidor";

const RAIZ = {
  caminho: "",
  aqui: 0,
  filhos: [
    { nome: "Volumes", caminho: "/Volumes", total: 225914, alcancaveis: 0 },
    { nome: "Users", caminho: "/Users", total: 100672, alcancaveis: 94459 },
  ],
};

const DENTRO_DE_VOLUMES = {
  caminho: "/Volumes",
  aqui: 3,
  filhos: [
    { nome: "photo", caminho: "/Volumes/photo", total: 225914, alcancaveis: 0 },
  ],
};

describe("ArvoreDePastas", () => {
  it("lista as raízes com a contagem recursiva", async () => {
    servirApi({ "/api/pastas": RAIZ });
    montar(<ArvoreDePastas pastaAtual={null} onSelecionar={vi.fn()} />);

    expect(await screen.findByText("Volumes")).toBeInTheDocument();
    expect(screen.getByText("225.914")).toBeInTheDocument();
  });

  it("diz quando nada é alcançável agora, em vez de esconder a pasta", async () => {
    // 225.914 registros num volume desmontado: o zero é a resposta, não um
    // erro — esconder a pasta faria o dono achar que as fotos sumiram.
    servirApi({ "/api/pastas": RAIZ });
    montar(<ArvoreDePastas pastaAtual={null} onSelecionar={vi.fn()} />);

    expect(
      await screen.findByText("nenhuma alcançável agora"),
    ).toBeInTheDocument();
  });

  it("desce um nível ao clicar e oferece a trilha de volta", async () => {
    servirApi({ "/api/pastas": RAIZ });
    montar(<ArvoreDePastas pastaAtual={null} onSelecionar={vi.fn()} />);

    // A segunda resposta é o nível de dentro.
    servirApi({ "/api/pastas": DENTRO_DE_VOLUMES });
    await userEvent.click(await screen.findByText("Volumes"));

    expect(await screen.findByText("photo")).toBeInTheDocument();
    // Trilha: dá para voltar sem recarregar a tela.
    expect(
      screen.getByRole("button", { name: "todos os discos" }),
    ).toBeInTheDocument();
  });

  it("navegar não filtra a grade — só o botão explícito filtra", async () => {
    const onSelecionar = vi.fn();
    servirApi({ "/api/pastas": RAIZ });
    montar(<ArvoreDePastas pastaAtual={null} onSelecionar={onSelecionar} />);

    servirApi({ "/api/pastas": DENTRO_DE_VOLUMES });
    await userEvent.click(await screen.findByText("Volumes"));
    await screen.findByText("photo");
    // Descer na árvore olhando não pode trocar o recorte a cada passo.
    expect(onSelecionar).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "ver na grade" }));
    expect(onSelecionar).toHaveBeenCalledWith("/Volumes");
  });

  it("clicar de novo no recorte ativo remove o filtro", async () => {
    const onSelecionar = vi.fn();
    servirApi({ "/api/pastas": DENTRO_DE_VOLUMES });
    montar(
      <ArvoreDePastas pastaAtual="/Volumes" onSelecionar={onSelecionar} />,
    );

    await userEvent.click(
      await screen.findByRole("button", { name: "recorte ativo ✕" }),
    );
    expect(onSelecionar).toHaveBeenCalledWith(null);
  });

  it("pasta sem subpasta diz isso em vez de ficar vazia", async () => {
    servirApi({
      "/api/pastas": { caminho: "/Volumes/photo/2019", aqui: 412, filhos: [] },
    });
    montar(
      <ArvoreDePastas pastaAtual={null} onSelecionar={vi.fn()} />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("só arquivos aqui, sem subpastas"),
      ).toBeInTheDocument(),
    );
  });
});
