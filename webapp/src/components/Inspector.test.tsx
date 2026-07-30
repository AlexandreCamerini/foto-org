import { screen } from "@testing-library/react";
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
