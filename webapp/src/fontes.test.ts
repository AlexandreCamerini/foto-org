import { describe, expect, it } from "vitest";

import { rotuloDeFonte, rotulosDeFontes } from "./fontes";
import type { Fonte } from "./api";

function fonte(over: Partial<Fonte> & { id: number; caminho: string }): Fonte {
  return {
    apelido: null,
    tipo: "pasta",
    disponivel: true,
    fotos: 0,
    ...over,
  } as Fonte;
}

describe("rotulosDeFontes", () => {
  it("usa o apelido quando existe", () => {
    const r = rotulosDeFontes([
      fonte({ id: 1, caminho: "/Users/eu/Pictures/Lib.photoslibrary", apelido: "Apple Fotos" }),
    ]);
    expect(r.get(1)).toBe("Apple Fotos");
  });

  it("usa o último segmento quando ele já distingue", () => {
    const r = rotulosDeFontes([
      fonte({ id: 1, caminho: "/Users/eu/Pictures/2026" }),
      fonte({ id: 2, caminho: "/Volumes/Externo" }),
    ]);
    expect(r.get(1)).toBe("2026");
    expect(r.get(2)).toBe("Externo");
  });

  it("cresce o caminho quando dois nomes curtos colidem", () => {
    const r = rotulosDeFontes([
      fonte({ id: 1, caminho: "/Users/eu/Pictures/2026" }),
      fonte({ id: 2, caminho: "/Volumes/HD/2026" }),
    ]);
    expect(r.get(1)).toBe("Pictures/2026");
    expect(r.get(2)).toBe("HD/2026");
  });

  it("mesma pasta em caixas diferentes deixa de ser dois rótulos iguais", () => {
    // O caso real do acervo: a barra lateral mostrava "acamerini (93400)" e
    // "acamerini (695)", indistinguíveis. O que resta para separar as duas é
    // exatamente a caixa do caminho — e é isso que o rótulo passa a mostrar.
    const r = rotulosDeFontes([
      fonte({ id: 1, caminho: "/Users/acamerini" }),
      fonte({ id: 2, caminho: "/users/acamerini" }),
    ]);
    expect(r.get(1)).toBe("Users/acamerini");
    expect(r.get(2)).toBe("users/acamerini");
    expect(r.get(1)).not.toBe(r.get(2));
  });
});

describe("rotuloDeFonte", () => {
  it("nomeia a fonte no chip em vez de dizer a palavra 'fonte'", () => {
    // O chip dizia literalmente "Filtrando por fonte ✕": o fallback aparecia
    // sempre, porque pasta comum não tem apelido.
    const fontes = [fonte({ id: 7, caminho: "/Users/eu/Pictures/Dubai" })];
    expect(rotuloDeFonte(fontes, 7)).toBe("Dubai");
  });

  it("sem a lista carregada ainda, não inventa nome", () => {
    expect(rotuloDeFonte(undefined, 7)).toBe("fonte");
  });
});
