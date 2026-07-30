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
  local: {
    pais: "França",
    regiao: "Provence-Alpes-Côte d'Azur",
    cidade: "Avignon",
    fonte: "offline:reverse_geocode",
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

  it("foto sem lugar resolvido não inventa linha vazia", async () => {
    servirApi({
      "/api/midia/7": { ...DETALHE_HERDADO, local: undefined, sugestao: null },
    });
    montar(<Inspector media={MEDIA} />);

    await screen.findByText("DSC_0100.jpg");
    expect(screen.queryByText("Lugar")).not.toBeInTheDocument();
  });
});
