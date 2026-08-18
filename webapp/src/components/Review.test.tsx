import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Review from "./Review";
import type { Job } from "../hooks/useJob";
import { ROTAS_BASE, erro, montar, servirApi } from "../test/servidor";

// Dublê trivial: isola este arquivo do assistente GenAI inteiro (07-06/07-07
// já têm a suíte própria). Os testes da pastilha no PorQue, mais abaixo,
// NÃO usam este dublê — exercitam o PorQue real, que é o que este plano
// (07-08) alterou.
vi.mock("./ClassificacaoPasta", () => ({
  ClassificacaoPasta: ({ onFechar }: { onFechar: () => void }) => (
    <div>
      <span>Assistente de classificação por IA (mock)</span>
      <button onClick={onFechar}>Fechar mock</button>
    </div>
  ),
}));

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

  it("Gerar/atualizar sugestões usa o contorno padrão, não o preenchido de antes (D-04, CONS-03)", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    montar(<Review job={jobParado()} />);

    const botao = await screen.findByRole("button", {
      name: "Gerar/atualizar sugestões",
    });
    const classes = botao.className.split(" ");
    expect(classes).not.toContain("bg-acento");
    expect(classes).not.toContain("text-texto-invertido");
    expect(classes).toContain("border-borda");
    expect(classes).toContain("bg-cartao");
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

describe("badge de confiança em 'Não classificadas'", () => {
  // D-071: sem nenhuma evidência de categoria/viagem/evento, o nível vem só
  // da confiança da DATA (EXIF, 0.95 → "alta") — mostrar "Alta" ao lado de
  // "Não classificadas" mentia sobre existir uma classificação.
  const SUGESTOES_SEM_CATEGORIA = {
    contagens: { pendente: 2 },
    total: 2,
    itens: [
      {
        id: 1, media_id: 21, nome: "20140719-144517.jpg", pasta: "/fotos/nov",
        destino: "Não classificadas/2014/jul.2014", nivel: "alta",
        status: "pendente", data_capturada: "2014-07-19T14:45:17",
        camera: null, gps_estimado: false,
      },
      {
        id: 2, media_id: 22, nome: "IMG_9100.jpg", pasta: "/fotos/iPhone",
        destino: "Viagens/2024 - França", nivel: "alta", status: "pendente",
        data_capturada: "2024-05-04T10:30:00", camera: "Apple iPhone 15 Pro",
        gps_estimado: false,
      },
    ],
  };
  const GRUPOS_SEM_CATEGORIA = [
    {
      destino: "Não classificadas/2014/jul.2014", total: 1, nivel: "alta",
      estimadas: 0, fora_de_alcance: 0,
      origens: [{ pasta: "/fotos/nov", fotos: 1 }],
    },
    {
      destino: "Viagens/2024 - França", total: 1, nivel: "alta",
      estimadas: 0, fora_de_alcance: 0,
      origens: [{ pasta: "/fotos/iPhone", fotos: 1 }],
    },
  ];

  it("grupo 'Não classificadas' com nível alta mostra 'Sem categoria', não 'Alta'", async () => {
    servirApi({
      "/api/sugestoes": SUGESTOES_SEM_CATEGORIA,
      "/api/sugestoes/grupos": GRUPOS_SEM_CATEGORIA,
    });
    montar(<Review job={jobParado()} />);

    await screen.findByText("Não classificadas/2014/jul.2014");
    // Os dois grupos nascem fechados: o rótulo do cabeçalho é o único
    // "Sem categoria"/"Alta" visível sem abrir nada.
    expect(screen.getByText("Sem categoria")).toBeInTheDocument();
    // O grupo classificado (Viagens), mesmo nível "alta" no fixture,
    // continua mostrando "Alta" normalmente — não é regressão geral.
    expect(screen.getByText("Alta")).toBeInTheDocument();
  });

  it("linha 'Não classificadas' também troca o badge — não só o cabeçalho do grupo",
    async () => {
      servirApi({
        "/api/sugestoes": SUGESTOES_SEM_CATEGORIA,
        "/api/sugestoes/grupos": GRUPOS_SEM_CATEGORIA,
      });
      const usuario = userEvent.setup();
      montar(<Review job={jobParado()} />);

      await abrirGrupo(usuario, "Não classificadas/2014/jul.2014");
      await screen.findByText("20140719-144517.jpg");

      // Cabeçalho do grupo + linha da foto: os dois pontos que usavam
      // <Confianca nivel={...}> têm que refletir a troca.
      expect(screen.getAllByText("Sem categoria").length).toBeGreaterThanOrEqual(2);
    });
});

describe("selo de fonte (CONS-01)", () => {
  // Duas fontes de nomes distintos: o selo precisa mostrar o nome de cada
  // uma, não um rótulo genérico ("fonte 1", "fonte 2").
  const FONTES = [
    {
      id: 1, caminho: "/Volumes/disco-a/fotos", apelido: "Disco A",
      tipo: "pasta" as const, disponivel: true, fotos: 5,
    },
    {
      id: 2, caminho: "/Volumes/disco-b/fotos", apelido: "Disco B",
      tipo: "pasta" as const, disponivel: true, fotos: 5,
    },
  ];

  // Itens 1 e 2 colidem: mesmo nome, data e câmera, media_id diferente — a
  // mesma foto catalogada a partir de duas fontes. Item 3 é o controle:
  // nome diferente, não colide com o vizinho (item 2).
  const SUGESTOES_COLISAO = {
    contagens: { pendente: 3 },
    total: 3,
    itens: [
      {
        id: 1, media_id: 101, nome: "IMG_0001.jpg", pasta: "/fotos/a",
        destino: "Viagens/2024 - Grécia", nivel: "alta", status: "pendente",
        data_capturada: "2024-06-01T09:00:00", camera: "Apple iPhone 15 Pro",
        gps_estimado: false, source_id: 1,
      },
      {
        id: 2, media_id: 102, nome: "IMG_0001.jpg", pasta: "/fotos/b",
        destino: "Viagens/2024 - Grécia", nivel: "alta", status: "pendente",
        data_capturada: "2024-06-01T09:00:00", camera: "Apple iPhone 15 Pro",
        gps_estimado: false, source_id: 2,
      },
      {
        id: 3, media_id: 103, nome: "IMG_0002.jpg", pasta: "/fotos/a",
        destino: "Viagens/2024 - Grécia", nivel: "alta", status: "pendente",
        data_capturada: "2024-06-01T09:05:00", camera: "Apple iPhone 15 Pro",
        gps_estimado: false, source_id: 1,
      },
    ],
  };
  const GRUPOS_COLISAO = [
    {
      destino: "Viagens/2024 - Grécia", total: 3, nivel: "alta",
      estimadas: 0, fora_de_alcance: 0,
      origens: [{ pasta: "/fotos/a", fotos: 2 }, { pasta: "/fotos/b", fotos: 1 }],
    },
  ];

  it("sugestões vizinhas com mesmo nome+data+câmera mostram o selo com o nome da fonte, e o item sem colisão fica sem selo", async () => {
    servirApi({
      "/api/sugestoes": SUGESTOES_COLISAO,
      "/api/sugestoes/grupos": GRUPOS_COLISAO,
      "/api/fontes": FONTES,
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - Grécia");
    const linhasImg1 = await screen.findAllByText("IMG_0001.jpg");
    expect(linhasImg1).toHaveLength(2);

    // Cada uma das duas linhas colididas mostra o selo com o nome da SUA
    // fonte — não um selo único, não o nome da outra.
    const linhaDiscoA = linhasImg1[0].closest("div")!;
    expect(within(linhaDiscoA).getByText("Disco A")).toBeInTheDocument();
    const linhaDiscoB = linhasImg1[1].closest("div")!;
    expect(within(linhaDiscoB).getByText("Disco B")).toBeInTheDocument();

    // O título explica a colisão, não expõe caminho nem id.
    const selos = screen.getAllByTitle(/Mesmo nome, data e câmera/);
    expect(selos).toHaveLength(2);

    // Item de controle: mesma fonte do primeiro item, mas nome diferente —
    // não colide com ninguém, não ganha selo.
    const linhaControle = (await screen.findByText("IMG_0002.jpg")).closest("div")!;
    expect(within(linhaControle).queryByText("Disco A")).not.toBeInTheDocument();
    expect(
      within(linhaControle).queryByTitle(/Mesmo nome, data e câmera/),
    ).not.toBeInTheDocument();
  });

  it("selo cai no rótulo de fallback quando a fonte da sugestão não está no cache", async () => {
    // /api/fontes só conhece a fonte 1 — a sugestão colidida referencia a
    // fonte 2, ausente do cache (ex.: fonte removida entre a geração da
    // sugestão e a revisão). O selo não pode sumir nem quebrar a tela.
    servirApi({
      "/api/sugestoes": SUGESTOES_COLISAO,
      "/api/sugestoes/grupos": GRUPOS_COLISAO,
      "/api/fontes": [FONTES[0]],
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - Grécia");
    await screen.findAllByText("IMG_0001.jpg");

    expect(screen.getByText("fonte")).toBeInTheDocument();
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

describe("botão de classificação de pasta por IA (07-08)", () => {
  it("botão de classificação abre o modal", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await usuario.click(
      await screen.findByText("Classificar pastas por IA…"),
    );

    // Texto que só existe dentro do dublê do modal — prova que ele montou.
    expect(
      await screen.findByText("Assistente de classificação por IA (mock)"),
    ).toBeInTheDocument();
  });

  it("modal fecha e a Revisão continua", async () => {
    servirApi({ "/api/sugestoes": SUGESTOES, "/api/sugestoes/grupos": GRUPOS });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await usuario.click(
      await screen.findByText("Classificar pastas por IA…"),
    );
    await screen.findByText("Assistente de classificação por IA (mock)");

    await usuario.click(screen.getByText("Fechar mock"));

    expect(
      screen.queryByText("Assistente de classificação por IA (mock)"),
    ).not.toBeInTheDocument();
    // A Revisão por baixo continua intacta — fechar o modal não desmontou a
    // tela nem perdeu o estado de grupos.
    expect(
      await screen.findByText("Viagens/2024 - França"),
    ).toBeInTheDocument();
  });
});

describe("pastilha de origem llm_pasta no PorQue (07-08)", () => {
  // Reusa a mesma sugestão (media_id 12) das fixtures de PorQue acima —
  // só o corpo de /api/midia/12 muda entre os dois testes.
  const DETALHE_LLM_PASTA = {
    id: 12,
    nome: "DSC_0100.jpg",
    sugestao: {
      id: 2, destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
      evidencias: [
        {
          campo: "cidade", origem: "llm_pasta", valor: "Lisboa",
          nivel: "media", score: 0.55,
          justificativa: "Nome da pasta sugere Lisboa, Portugal",
        },
      ],
    },
  };
  const DETALHE_GPS = {
    id: 12,
    nome: "DSC_0100.jpg",
    sugestao: {
      id: 2, destino: "Viagens/2024 - França", nivel: "media", status: "pendente",
      evidencias: [
        {
          campo: "cidade", origem: "gps", valor: "Paris",
          nivel: "alta", score: 0.9,
          justificativa: "Coordenada GPS do próprio arquivo",
        },
      ],
    },
  };

  it("evidência llm_pasta ganha a pastilha", async () => {
    servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/grupos": GRUPOS,
      "/api/midia/12": DETALHE_LLM_PASTA,
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    await screen.findByText("DSC_0100.jpg");
    await usuario.click(
      screen.getByTitle("Por que este destino para DSC_0100.jpg?"),
    );

    expect(await screen.findByText("IA · pasta")).toBeInTheDocument();
  });

  it("evidência de outra origem não ganha pastilha", async () => {
    servirApi({
      "/api/sugestoes": SUGESTOES,
      "/api/sugestoes/grupos": GRUPOS,
      "/api/midia/12": DETALHE_GPS,
    });
    const usuario = userEvent.setup();
    montar(<Review job={jobParado()} />);

    await abrirGrupo(usuario, "Viagens/2024 - França");
    await screen.findByText("DSC_0100.jpg");
    await usuario.click(
      screen.getByTitle("Por que este destino para DSC_0100.jpg?"),
    );

    await screen.findByText(/Coordenada GPS do próprio arquivo/);
    expect(screen.queryByText("IA · pasta")).not.toBeInTheDocument();
  });
});
