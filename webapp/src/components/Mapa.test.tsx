import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Mapa, { agruparPorLugar, projetar } from "./Mapa";
import { montar, servirApi } from "../test/servidor";
import type { DadosMapa, PontoMapa } from "../api";

// Números do catálogo real (medidos em 2026-08-01): o evento "Pantanal" tem
// 97 fotos, 80 no mapa sobre 4 coordenadas distintas, todas fora de alcance;
// "Visconde de Maua" tem 18 fotos e nenhuma coordenada.
const PORQUE_PANTANAL =
  "Lugar herdado de IMG_0001.HEIC, a 2 h de distância — a 5 km/h, a " +
  "velocidade de quem anda por uma cidade contando as paradas, isso dá " +
  "10 km de dúvida.";

function ponto(over: Partial<PontoMapa> = {}): PontoMapa {
  return {
    media_id: 1,
    nome: "DSC_0100.CR3",
    lat: -17.364843,
    lon: -56.775535,
    data_capturada: "2024-07-10T10:32:00",
    camera: "Canon EOS R5",
    motivo_indisponivel: null,
    estimado: true,
    raio_m: 10_000,
    delta_s: 7200,
    doadora_id: 900,
    doadora_nome: "IMG_0001.HEIC",
    porque: PORQUE_PANTANAL,
    ...over,
  };
}

function lido(over: Partial<PontoMapa> = {}): PontoMapa {
  return ponto({
    media_id: 900,
    nome: "IMG_0001.HEIC",
    camera: "Apple iPhone 15 Pro",
    estimado: false,
    raio_m: null,
    delta_s: null,
    doadora_id: null,
    doadora_nome: null,
    porque: null,
    ...over,
  });
}

function dados(over: Partial<DadosMapa> = {}): DadosMapa {
  const pontos = over.pontos ?? [lido(), ponto()];
  return {
    grupo: {
      tipo: "evento",
      id: 2,
      nome: "Pantanal",
      inicio: "2024-07-10T00:00:00",
      fim: "2024-07-14T00:00:00",
    },
    contagens: { total: 2, no_mapa: pontos.length, sem_coordenada: 0, fora_de_alcance: 0 },
    doadoras: [
      {
        id: 900,
        nome: "IMG_0001.HEIC",
        lat: -17.364843,
        lon: -56.775535,
        camera: "Apple iPhone 15 Pro",
        no_grupo: true,
      },
    ],
    limites: {
      lat_min: -17.46,
      lat_max: -17.27,
      lon_min: -56.87,
      lon_max: -56.68,
    },
    escala: { metros_por_grau_lat: 110_900, metros_por_grau_lon: 106_300 },
    nota_do_raio:
      "O círculo é o tamanho da dúvida, não um erro de medição: em 93,6% dos " +
      "pares medidos neste acervo, o lugar verdadeiro cabe dentro dele.",
    ...over,
    pontos,
  };
}

describe("Mapa", () => {
  it("não sai da máquina: a única requisição é a da API local", async () => {
    const chamadas = servirApi({ "/api/mapa": dados() });
    montar(<Mapa event_id={2} nome="Pantanal" />);
    await screen.findByText(/2 de 2 fotos no mapa/);

    expect(chamadas.every((c) => c.caminho.startsWith("/api/"))).toBe(true);
    expect(chamadas.map((c) => c.caminho)).toContain("/api/mapa");
  });

  it("GPS próprio vira ponto cheio; herdado vira círculo tracejado", async () => {
    // Duas coordenadas distintas para separar os dois marcadores: no acervo
    // real elas coincidem, e o teste do agrupamento cobre esse caso.
    servirApi({
      "/api/mapa": dados({
        pontos: [lido(), ponto({ lat: -17.3, lon: -56.7 })],
      }),
    });
    const vista = montar(<Mapa event_id={2} nome="Pantanal" />);
    await screen.findByText(/2 de 2 fotos no mapa/);

    const cheio = vista.container.querySelector('[data-tipo="lido"]')!;
    expect(cheio).toBeTruthy();
    // Ponto cheio: círculo preenchido, sem tracejado.
    expect(
      [...cheio.querySelectorAll("circle")].some(
        (c) =>
          c.getAttribute("fill") === "var(--color-texto)" &&
          !c.getAttribute("stroke-dasharray"),
      ),
    ).toBe(true);

    const estimado = vista.container.querySelector('[data-tipo="estimado"]')!;
    expect(estimado).toBeTruthy();
    expect(
      [...estimado.querySelectorAll("circle")].some((c) =>
        c.getAttribute("stroke-dasharray"),
      ),
    ).toBe(true);
  });

  it("clicar no círculo mostra a frase pronta do servidor, sem outra chamada", async () => {
    const chamadas = servirApi({ "/api/mapa": dados() });
    const { container } = montar(<Mapa event_id={2} nome="Pantanal" />);
    await screen.findByText(/2 de 2 fotos no mapa/);

    expect(screen.queryByText(PORQUE_PANTANAL)).not.toBeInTheDocument();
    const antes = chamadas.length;

    fireEvent.click(container.querySelector("[data-lugar]")!);

    expect(screen.getByText(PORQUE_PANTANAL)).toBeInTheDocument();
    expect(
      screen.getByText(/1 foto herdou de IMG_0001\.HEIC/),
    ).toBeInTheDocument();
    expect(chamadas.length).toBe(antes);
  });

  it("as contagens de sem coordenada e fora de alcance aparecem na tela", async () => {
    servirApi({
      "/api/mapa": dados({
        contagens: {
          total: 97,
          no_mapa: 80,
          sem_coordenada: 17,
          fora_de_alcance: 80,
        },
      }),
    });
    montar(<Mapa event_id={2} nome="Pantanal" />);

    expect(await screen.findByText(/17 sem coordenada/)).toBeInTheDocument();
    expect(screen.getByText(/80 fora de alcance/)).toBeInTheDocument();
    // Subconjunto, não soma: as 80 estão desenhadas.
    expect(screen.getByText(/80 de 97 fotos no mapa/)).toBeInTheDocument();
  });

  it("grupo sem nenhuma coordenada diz por quê em vez de desenhar nada", async () => {
    servirApi({
      "/api/mapa": dados({
        grupo: {
          tipo: "evento",
          id: 1,
          nome: "Visconde de Maua",
          inicio: null,
          fim: null,
        },
        pontos: [],
        doadoras: [],
        limites: null,
        escala: null,
        contagens: {
          total: 18,
          no_mapa: 0,
          sem_coordenada: 18,
          fora_de_alcance: 0,
        },
      }),
    });
    const { container } = montar(<Mapa event_id={1} nome="Visconde de Maua" />);

    expect(
      await screen.findByText(/Nenhuma foto deste grupo tem lugar/),
    ).toBeInTheDocument();
    expect(screen.getByText(/18 de 18 fotos estão sem/)).toBeInTheDocument();
    // Nada de quadriculado vazio e mudo.
    expect(container.querySelector("svg")).toBeNull();
  });

  it("avisa o pai quando o grupo não tem nenhum lugar, para a dica do rodapé não convidar a um clique que não existe", async () => {
    servirApi({
      "/api/mapa": dados({
        pontos: [],
        doadoras: [],
        limites: null,
        escala: null,
        contagens: { total: 18, no_mapa: 0, sem_coordenada: 18, fora_de_alcance: 0 },
      }),
    });
    const onEstadoVazio = vi.fn();
    montar(<Mapa event_id={1} nome="Visconde de Maua" onEstadoVazio={onEstadoVazio} />);

    await screen.findByText(/Nenhuma foto deste grupo tem lugar/);
    expect(onEstadoVazio).toHaveBeenLastCalledWith(true);
  });

  it("não avisa estado vazio quando o grupo tem lugar", async () => {
    servirApi({ "/api/mapa": dados({}) });
    const onEstadoVazio = vi.fn();
    montar(<Mapa event_id={1} nome="Pantanal" onEstadoVazio={onEstadoVazio} />);

    await screen.findByText(/no mapa/);
    expect(onEstadoVazio).toHaveBeenLastCalledWith(false);
  });

  it("foto fora de alcance continua desenhada e o painel diz por que não há imagem", async () => {
    servirApi({
      "/api/mapa": dados({
        pontos: [
          ponto({ motivo_indisponivel: "volume /Volumes/Externo desmontado" }),
        ],
        contagens: { total: 1, no_mapa: 1, sem_coordenada: 0, fora_de_alcance: 1 },
      }),
    });
    const { container } = montar(<Mapa event_id={2} nome="Pantanal" />);
    await screen.findByText(/1 de 1 fotos no mapa/);

    fireEvent.click(container.querySelector("[data-lugar]")!);
    expect(
      screen.getByText(/a coordenada está no catálogo, o arquivo é que não responde/),
    ).toBeInTheDocument();
    // Mesmo padrão da Miniatura: motivo em vez de imagem quebrada.
    expect(container.querySelector("img")).toBeNull();
    expect(
      screen.getByText("volume /Volumes/Externo desmontado"),
    ).toBeInTheDocument();
  });
});

describe("agruparPorLugar", () => {
  it("80 fotos sobre 4 coordenadas viram 4 marcadores, não 80", () => {
    // O caso real: a herdeira recebe a coordenada EXATA da doadora, então
    // desenhar por foto empilharia círculos idênticos no mesmo pixel.
    const pontos = [
      ...Array.from({ length: 59 }, (_, i) => ponto({ media_id: i + 1 })),
      ...Array.from({ length: 16 }, (_, i) =>
        ponto({ media_id: 100 + i, lat: -15.501105, lon: -55.405277 }),
      ),
      ...Array.from({ length: 3 }, (_, i) =>
        ponto({ media_id: 200 + i, lat: -17.266748, lon: -56.674912 }),
      ),
      ...Array.from({ length: 2 }, (_, i) =>
        ponto({ media_id: 300 + i, lat: -17.36515, lon: -56.773898 }),
      ),
    ];
    const lugares = agruparPorLugar(dados({ pontos }));

    expect(lugares).toHaveLength(4);
    expect(lugares[0].herdados).toHaveLength(59);
    // Maior primeiro, para o lugar de duas fotos não ficar embaixo do de 59.
    expect(lugares.map((l) => l.herdados.length)).toEqual([59, 16, 3, 2]);
  });

  it("a doadora e as herdeiras que ela doou caem no mesmo lugar", () => {
    const lugares = agruparPorLugar(dados());
    expect(lugares).toHaveLength(1);
    expect(lugares[0].proprios).toHaveLength(1);
    expect(lugares[0].herdados).toHaveLength(1);
    expect(lugares[0].doadoras).toHaveLength(1);
    expect(lugares[0].raio_m).toBe(10_000);
  });
});

describe("projetar", () => {
  it("usa um só fator para os dois eixos — círculo não vira elipse", () => {
    // Caixa achatada: 1° de latitude por 4° de longitude. Com escala por
    // eixo, o raio horizontal e o vertical divergiriam.
    const p = projetar(
      { lat_min: -1, lat_max: 0, lon_min: 0, lon_max: 4 },
      { metros_por_grau_lat: 110_000, metros_por_grau_lon: 110_000 },
    );
    const larguraPx = p.x(4) - p.x(0);
    const alturaPx = p.y(-1) - p.y(0);
    expect(larguraPx / alturaPx).toBeCloseTo(4, 5);
  });

  it("um grupo inteiro numa coordenada só não divide por zero", () => {
    const p = projetar(
      { lat_min: 10, lat_max: 10, lon_min: 20, lon_max: 20 },
      { metros_por_grau_lat: 110_000, metros_por_grau_lon: 108_000 },
    );
    expect(Number.isFinite(p.x(20))).toBe(true);
    expect(Number.isFinite(p.y(10))).toBe(true);
    expect(Number.isFinite(p.pxPorMetro)).toBe(true);
  });
});
