import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Review from "./Review";
import type { Job } from "../hooks/useJob";
import { ROTAS_BASE, erro, montar, servirApi } from "../test/servidor";

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

/** Duas viagens e uma foto solta: o suficiente para ver o agrupamento. */
const SUGESTOES = {
  contagens: { pendente: 3 },
  total: 3,
  itens: [
    {
      id: 1, media_id: 11, nome: "IMG_9100.jpg", pasta: "/fotos/iPhone",
      destino: "Viagens/2024 - França", nivel: "alta", status: "pendente",
      data_capturada: "2024-05-04T10:30:00", camera: "Apple iPhone 15 Pro",
      gps_estimado: false,
    },
    {
      id: 2, media_id: 12, nome: "DSC_0100.jpg", pasta: "/fotos/Camera",
      destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
      data_capturada: "2024-05-04T10:32:00", camera: "Canon EOS R5",
      gps_estimado: true,
    },
    {
      id: 3, media_id: 13, nome: "captura.png", pasta: "/fotos/Diversos",
      destino: "Não classificadas/2026/julho", nivel: "baixa",
      status: "pendente", data_capturada: null, camera: null,
      gps_estimado: false,
    },
  ],
};

/** Os grupos como o servidor os conta — a contagem NÃO vem da página. */
const GRUPOS = [
  {
    destino: "Viagens/2024 - França",
    total: 2, nivel: "media", estimadas: 1, fora_de_alcance: 0,
    origens: [{ pasta: "/fotos/iPhone", fotos: 1 },
              { pasta: "/fotos/Camera", fotos: 1 }],
  },
  {
    destino: "Não classificadas/2026/julho",
    total: 1, nivel: "baixa", estimadas: 0, fora_de_alcance: 0,
    origens: [{ pasta: "/fotos/Diversos", fotos: 1 }],
  },
];

/** A tela nasce com os grupos dobrados: abrir é o gesto que carrega as
 *  fotos daquele grupo. */
async function abrirGrupo(usuario: ReturnType<typeof userEvent.setup>,
                          destino: string) {
  await usuario.click(await screen.findByText(destino));
}

/** O único caminho até Aprovar/Rejeitar de cada foto é abrir o grupo — e o
 *  cabeçalho era um `<header onClick>` sem tabIndex nem onKeyDown: só
 *  mouse chegava lá. Tab até o cabeçalho e Enter precisa abrir o grupo. */
async function abrirGrupoPeloTeclado(
  usuario: ReturnType<typeof userEvent.setup>, destino: string,
) {
  const rotulo = await screen.findByText(destino);
  const cabecalho = rotulo.closest('[role="button"]') as HTMLElement;
  cabecalho.focus();
  await usuario.keyboard("{Enter}");
}

const DETALHE_12 = {
  id: 12, nome: "DSC_0100.jpg",
  sugestao: {
    id: 2, destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
    evidencias: [
      {
        campo: "cidade", origem: "vizinhanca_temporal", valor: "Avignon",
        nivel: "media", score: 0.75,
        justificativa:
          "GPS herdado de 'IMG_9100.jpg' (Apple iPhone 15 Pro) — tirada a 2min de distância",
      },
    ],
  },
};

describe("Review", () => {
  it("agrupa por destino em vez de listar tudo plano", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText("Viagens/2024 - França")).toBeInTheDocument();
    expect(screen.getByText("Não classificadas/2026/julho")).toBeInTheDocument();
    expect(screen.getByText("3 em 2 grupos")).toBeInTheDocument();
    // Aprovação em lote é por grupo, não uma varredura global.
    expect(screen.getByText("Aprovar 2")).toBeInTheDocument();
    expect(screen.getByText("Aprovar 1")).toBeInTheDocument();
    // Dobrado por padrão: a decisão é o grupo, não as 3 linhas.
    expect(screen.queryByText("DSC_0100.jpg")).not.toBeInTheDocument();
  });

  it("abre e fecha o grupo pelo teclado, sem depender do mouse", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupoPeloTeclado(usuario, "Viagens/2024 - França");
    expect(await screen.findByText("DSC_0100.jpg")).toBeInTheDocument();

    await usuario.keyboard("{Enter}");
    expect(screen.queryByText("DSC_0100.jpg")).not.toBeInTheDocument();
  });

  it("Enter no botão Aprovar do grupo não fecha o cabeçalho junto", async () => {
    // O keydown do botão borbulha para o header — sem o filtro, aprovar
    // pelo teclado também alternaria aberto/fechado por engano.
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupoPeloTeclado(usuario, "Viagens/2024 - França");
    expect(await screen.findByText("DSC_0100.jpg")).toBeInTheDocument();

    await usuario.tab(); // do cabeçalho para o botão "Aprovar 2"
    expect(screen.getByRole("button", { name: "Aprovar 2" })).toHaveFocus();
    await usuario.keyboard("{Enter}");
    expect(screen.getByText("DSC_0100.jpg")).toBeInTheDocument(); // segue aberto
  });

  it("mostra o nome do arquivo, não o caminho que o truncava", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    expect(await screen.findByText("DSC_0100.jpg")).toBeInTheDocument();
    expect(screen.getByText(/Canon EOS R5/)).toBeInTheDocument();
  });

  it("avisa quantas fotos do grupo têm lugar estimado", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText(/1 com lugar estimado/)).toBeInTheDocument();
  });

  it("o porquê é buscado só quando o usuário pergunta", async () => {
    const chamadas = servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/grupos": GRUPOS,
      "/api/midia/12": DETALHE_12,
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    await screen.findByText("DSC_0100.jpg");
    // Nada de 3 requisições de detalhe no carregamento.
    expect(chamadas.filter((c) => c.caminho.startsWith("/api/midia/"))).toHaveLength(0);

    await usuario.click(
      screen.getByTitle("Por que este destino para DSC_0100.jpg?"),
    );

    expect(
      await screen.findByText(/herdado de 'IMG_9100.jpg'/),
    ).toBeInTheDocument();
    expect(chamadas.filter((c) => c.caminho === "/api/midia/12")).toHaveLength(1);
  });

  it("abrir e fechar o grupo mostra e esconde as linhas", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    expect(await screen.findByText("DSC_0100.jpg")).toBeInTheDocument();

    await usuario.click(screen.getByText("Viagens/2024 - França"));
    expect(screen.queryByText("DSC_0100.jpg")).not.toBeInTheDocument();
    expect(screen.getByText("Viagens/2024 - França")).toBeInTheDocument();
  });

  it("a contagem do grupo é a do banco, não a da página carregada", async () => {
    // O defeito que deixava 4.848 das 5.048 pendências inalcançáveis: a
    // tela pedia 200 itens e deduzia daí o tamanho do grupo, dizendo
    // "85 fotos" e "Aprovar 85" para um grupo de 597.
    servirApi({
      "/api/sugestoes": { contagens: { pendente: 597 }, total: 597, itens: [] },
      "/api/sugestoes/grupos": [{
        destino: "Eventos/2025/TERG", total: 597, nivel: "media",
        estimadas: 0, fora_de_alcance: 0,
        origens: [{ pasta: "/fotos/TERG", fotos: 597 }],
      }],
    });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText(/597 fotos/)).toBeInTheDocument();
    expect(screen.getByText("Aprovar 597")).toBeInTheDocument();
    expect(screen.getByText("597 em 1 grupo")).toBeInTheDocument();
  });

  it("aprovar o grupo manda o destino, não os ids da página", async () => {
    const chamadas = servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/grupos": GRUPOS,
      "/api/sugestoes/acao": { afetadas: 2 },
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await usuario.click(await screen.findByText("Aprovar 2"));

    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === "/api/sugestoes/acao")).toBeTruthy(),
    );
    const acao = chamadas.find((c) => c.caminho === "/api/sugestoes/acao")!;
    expect(acao.corpo).toMatchObject({
      acao: "aprovar", destino: "Viagens/2024 - França", status: "pendente",
    });
    // Sem ids: quem resolve o grupo inteiro é o servidor.
    expect((acao.corpo as { ids?: number[] }).ids).toBeUndefined();
  });

  it("o grupo diz de onde as fotos vêm — a metade que faltava do par", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    montar(<Review job={jobParado()} />);

    // Duas pastas de origem: nomeia a maior e diz que há mais.
    expect(await screen.findByText("iPhone e mais 1")).toBeInTheDocument();
    expect(screen.getByText("Diversos")).toBeInTheDocument();
  });

  it("avisa quantas do grupo estão fora de alcance antes de aprovar", async () => {
    // Aprovar 2.405 fotos de um disco desligado sem saber é o caso que
    // D-033 já obrigou a dizer no mapa; vale igual aqui.
    servirApi({
      "/api/sugestoes": { contagens: { pendente: 97 }, total: 97, itens: [] },
      "/api/sugestoes/grupos": [{
        destino: "Eventos/2023/Pantanal", total: 97, nivel: "media",
        estimadas: 80, fora_de_alcance: 97,
        origens: [{ pasta: "/Volumes/photo/Pantanal", fotos: 97 }],
      }],
    });
    montar(<Review job={jobParado()} />);

    expect(await screen.findByText(/97 fora de alcance/)).toBeInTheDocument();
  });

  it("edita o destino inline e salva via PATCH", async () => {
    const chamadas = servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/grupos": GRUPOS,
      "/api/sugestoes/2/destino": {
        id: 2, media_id: 12, nome: "DSC_0100.jpg", pasta: "/fotos/Camera",
        destino: "Viagens/2024 - França (corrigida)", nivel: "media",
        status: "editada",
      },
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    await screen.findByText("DSC_0100.jpg");
    await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));

    const campo = screen.getByDisplayValue("Viagens/2024 - França");
    await usuario.clear(campo);
    await usuario.type(campo, "Viagens/2024 - França (corrigida)");
    await usuario.click(screen.getByText("Salvar"));

    await waitFor(() =>
      expect(
        chamadas.find((c) => c.caminho === "/api/sugestoes/2/destino"),
      ).toBeTruthy(),
    );
    const chamada = chamadas.find(
      (c) => c.caminho === "/api/sugestoes/2/destino",
    )!;
    expect(chamada.metodo).toBe("PATCH");
    expect(chamada.corpo).toEqual({
      destino: "Viagens/2024 - França (corrigida)",
    });
  });

  it("mostra a mensagem do servidor quando o destino editado é inválido (422)",
    async () => {
      servirApi({
        "/api/sugestoes": SUGESTOES,
        "/api/sugestoes/grupos": GRUPOS,
        "/api/sugestoes/2/destino": erro(422, "segmento proibido em '../etc'"),
      });
      const usuario = userEvent.setup();
      montar(<Review job={jobParado()} />);

      await abrirGrupo(usuario, "Viagens/2024 - França");
      await screen.findByText("DSC_0100.jpg");
      await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));

      const campo = screen.getByDisplayValue("Viagens/2024 - França");
      await usuario.clear(campo);
      await usuario.type(campo, "../etc");
      await usuario.click(screen.getByText("Salvar"));

      expect(
        await screen.findByText("segmento proibido em '../etc'"),
      ).toBeInTheDocument();
      // O campo continua editável — o erro não deve fechar a edição.
      expect(screen.getByDisplayValue("../etc")).toBeInTheDocument();
    });

  it("cancelar a edição descarta o valor digitado", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    await screen.findByText("DSC_0100.jpg");
    await usuario.click(screen.getByTitle("Editar destino de DSC_0100.jpg"));
    await usuario.click(screen.getByText("Cancelar"));

    expect(screen.getByText("DSC_0100.jpg")).toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("Viagens/2024 - França"),
    ).not.toBeInTheDocument();
  });
});

describe("foto fora de alcance", () => {
  it("a linha diz por quê em vez de desenhar imagem quebrada", async () => {
    // O primeiro grupo da fila de um acervo real estava inteiro num volume
    // desmontado. A tela mostrou 18 ícones de imagem quebrada e ficou calada,
    // e o dono concluiu que ela estava quebrada — ela estava muda.
    servirApi({
      ...ROTAS_BASE,
      "/api/sugestoes/grupos": [{
        destino: "Eventos/2015/Visconde", total: 1, nivel: "media",
        estimadas: 0, fora_de_alcance: 1,
        origens: [{ pasta: "/Volumes/photo/Portfolio", fotos: 1 }],
      }],
      "/api/sugestoes": {
        contagens: { pendente: 1 },
        total: 1,
        itens: [{
          id: 1, media_id: 9, nome: "1W0B3275.dng",
          pasta: "/Volumes/photo/Portfolio", destino: "Eventos/2015/Visconde",
          nivel: "media", status: "pendente",
          motivo_indisponivel: "volume ou pasta fora de alcance",
        }],
      },
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Eventos/2015/Visconde");
    expect(
      await screen.findByText("volume ou pasta fora de alcance"),
    ).toBeInTheDocument();
    expect(screen.queryByAltText("1W0B3275.dng")).not.toBeInTheDocument();
  });
});
