import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import Inspector from "./Inspector";
import type { Media } from "../api";
import { montar, servirApi } from "../test/servidor";

const MEDIA = { id: 7, nome: "DSC_0100.jpg" } as Media;

/** Detalhe de uma foto que NÃO tem GPS próprio: a coordenada continua nula,
 *  o lugar veio de outra câmera. É o caso que a auditoria da fase 2 pegou
 *  invisível na UI. */
const DETALHE_HERDADO = {
  id: 7,
  nome: "DSC_0100.jpg",
  pasta: "/fotos/Viagens/Camera",
  make: "Canon",
  model: "EOS R5",
  gps_lat: null,
  gps_lon: null,
  gps_estimado: true,
  gps_lat_efetivo: 43.95,
  gps_lon_efetivo: 4.81,
  local: {
    pais: "França",
    regiao: "Provence-Alpes-Côte d'Azur",
    cidade: "Avignon",
    fonte: "offline:reverse_geocode",
    estimado: true,
    granularidade: "cidade",
  },
  estimativa: {
    doadora_id: 6,
    doadora_nome: "IMG_9100.jpg",
    doadora_camera: "Apple iPhone 15 Pro",
    delta_s: 120,
    lat: 43.95,
    lon: 4.81,
  },
  sugestao: {
    id: 1,
    destino: "Viagens/2024 - França",
    nivel: "media",
    status: "pendente",
    evidencias: [
      {
        campo: "cidade",
        origem: "vizinhanca_temporal",
        valor: "Avignon",
        nivel: "media",
        score: 0.75,
        justificativa:
          "GPS herdado de 'IMG_9100.jpg' (Apple iPhone 15 Pro) — tirada a 2min de distância",
      },
    ],
  },
};

describe("Inspector", () => {
  it("mostra o lugar mesmo quando a foto não tem coordenada própria", async () => {
    servirApi({ "/api/midia/7": DETALHE_HERDADO });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText("Avignon, Provence-Alpes-Côte d'Azur, França"))
      .toBeInTheDocument();
  });

  it("mostra de quem o lugar foi herdado, não só que foi", async () => {
    servirApi({ "/api/midia/7": DETALHE_HERDADO });
    montar(<Inspector media={MEDIA} />);

    expect(
      await screen.findByText(/herdado de 'IMG_9100.jpg'/),
    ).toBeInTheDocument();
    expect(screen.getByText(/2min de distância/)).toBeInTheDocument();
  });

  it("marca o lugar como estimado no rótulo, não só no texto", async () => {
    servirApi({ "/api/midia/7": DETALHE_HERDADO });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText("Lugar · estimado")).toBeInTheDocument();
  });

  it("não repete a história da herança quando a evidência já a conta", async () => {
    servirApi({ "/api/midia/7": DETALHE_HERDADO });
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("Lugar · estimado");
    // Uma vez só: a evidência em "Por quê?" cobre; o bloco extra seria ruído
    // num painel estreito.
    expect(screen.queryByText(/Esta câmera não gravou coordenada/))
      .not.toBeInTheDocument();
  });

  it("sem sugestão, a estimativa ainda se explica", async () => {
    servirApi({ "/api/midia/7": { ...DETALHE_HERDADO, sugestao: null } });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText(/Esta câmera não gravou coordenada/))
      .toBeInTheDocument();
    expect(screen.getByText(/tirada a 2min de distância/)).toBeInTheDocument();
  });

  it("os metadados do arquivo só são lidos quando o painel abre", async () => {
    const chamadas = servirApi({
      "/api/midia/7": DETALHE_HERDADO,
      "/api/midia/7/metadados": {
        total: 2,
        namespaces: [{
          nome: "iptc",
          rotulo: "IPTC (autor, direitos, palavras-chave)",
          itens: [
            { chave: "By-line", valor: "Alexandre Camerini" },
            { chave: "Keywords", valor: "viagem; franca" },
          ],
        }],
      },
    });
    const usuario = userEvent.setup();
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("DSC_0100.jpg");
    expect(chamadas.filter((c) => c.caminho.endsWith("/metadados"))).toHaveLength(0);

    await usuario.click(screen.getByText("Metadados do arquivo"));

    expect(
      await screen.findByText("IPTC (autor, direitos, palavras-chave)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Alexandre Camerini")).toBeInTheDocument();
    expect(chamadas.filter((c) => c.caminho.endsWith("/metadados"))).toHaveLength(1);
  });

  it("arquivo sem metadado diz isso, em vez de painel vazio", async () => {
    servirApi({
      "/api/midia/7": DETALHE_HERDADO,
      "/api/midia/7/metadados": { total: 0, namespaces: [] },
    });
    const usuario = userEvent.setup();
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("DSC_0100.jpg");
    await usuario.click(screen.getByText("Metadados do arquivo"));

    expect(
      await screen.findByText(/não trouxe metadado nenhum/),
    ).toBeInTheDocument();
  });

  it("classificação provisória pergunta, em vez de afirmar", async () => {
    servirApi({
      "/api/midia/7": { ...DETALHE_HERDADO, tipo_imagem: "captura",
                        tipo_provisorio: true },
    });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText(/Isto parece/)).toBeInTheDocument();
    expect(screen.getByText("captura de tela")).toBeInTheDocument();
    expect(screen.getByText("Confere")).toBeInTheDocument();
    expect(screen.getByText("Não, é foto")).toBeInTheDocument();
  });

  it("responder grava a palavra do usuário, não a do detector", async () => {
    const chamadas = servirApi({
      "/api/midia/7": { ...DETALHE_HERDADO, tipo_imagem: "captura",
                        tipo_provisorio: true },
      "/api/midia/7/tipo": { tipo_imagem: "foto", tipo_provisorio: false },
    });
    const usuario = userEvent.setup();
    montar(<Inspector media={MEDIA} />);

    await usuario.click(await screen.findByText("Não, é foto"));

    const post = chamadas.find((c) => c.caminho === "/api/midia/7/tipo");
    expect(post?.metodo).toBe("POST");
    expect(post?.corpo).toEqual({ tipo: "foto" });
  });

  it("classificação já confirmada não volta a perguntar", async () => {
    servirApi({
      "/api/midia/7": { ...DETALHE_HERDADO, tipo_imagem: "captura",
                        tipo_provisorio: false },
    });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText(/classificado por você/)).toBeInTheDocument();
    expect(screen.queryByText("Confere")).not.toBeInTheDocument();
  });

  it("foto normal não ganha bloco de tipo", async () => {
    servirApi({
      "/api/midia/7": { ...DETALHE_HERDADO, tipo_imagem: "foto",
                        tipo_provisorio: false },
    });
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("DSC_0100.jpg");
    expect(screen.queryByText(/Isto parece/)).not.toBeInTheDocument();
    expect(screen.queryByText(/classificado por você/)).not.toBeInTheDocument();
  });

  it("foto sem lugar resolvido não inventa linha vazia", async () => {
    servirApi({
      "/api/midia/7": {
        ...DETALHE_HERDADO, local: undefined, sugestao: null,
        estimativa: undefined, gps_estimado: false,
      },
    });
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("DSC_0100.jpg");
    expect(screen.queryByText("Lugar")).not.toBeInTheDocument();
  });
});


describe("granularidade do lugar herdado", () => {
  it("herança de horas anuncia o país, não a cidade", async () => {
    // A API já devolve regiao/cidade nulas nesse caso (D-025); o que se
    // testa aqui é o rótulo — "Lugar · estimado" seco faria o usuário ler
    // a linha como se a cidade tivesse sido apurada.
    servirApi({
      "/api/midia/7": {
        ...DETALHE_HERDADO,
        // sem sugestão: o bloco de evidências cita a cidade por conta
        // própria, e aqui o alvo é a linha "Lugar".
        sugestao: null,
        local: {
          pais: "França",
          regiao: null,
          cidade: null,
          fonte: "offline:reverse_geocode",
          estimado: true,
          granularidade: "pais",
        },
      },
    });
    montar(<Inspector media={MEDIA} />);

    expect(await screen.findByText("Lugar · país estimado")).toBeInTheDocument();
    expect(screen.getByText("França")).toBeInTheDocument();
    expect(screen.queryByText(/Avignon/)).not.toBeInTheDocument();
  });
});
