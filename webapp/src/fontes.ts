import type { Fonte } from "./api";

/** O nome curto de uma fonte, quando ele é suficiente. */
function base(fonte: Fonte): string {
  return fonte.apelido ?? fonte.caminho.split("/").filter(Boolean).pop() ?? fonte.caminho;
}

/** Quantos segmentos finais do caminho, para desempatar nomes iguais. */
function cauda(caminho: string, segmentos: number): string {
  const partes = caminho.split("/").filter(Boolean);
  return partes.slice(-segmentos).join("/");
}

/** Rótulo de cada fonte, garantindo que dois nomes iguais não fiquem
 *  indistinguíveis na tela.
 *
 *  O acervo real tem `/Users/acamerini` e `/users/acamerini` — a mesma pasta,
 *  porque o macOS não distingue maiúscula no caminho e as fontes discordam.
 *  A barra lateral mostrava "acamerini (93400)" e "acamerini (695)", dois
 *  itens idênticos com números diferentes, sem nenhuma forma de saber qual
 *  era qual. Nome repetido não é economia de espaço, é ambiguidade.
 *
 *  A desambiguação vai puxando mais um segmento do caminho até os rótulos
 *  ficarem distintos; se nem o caminho inteiro distinguir (mesma pasta, caixa
 *  diferente), sobra o caminho como está escrito — que é justamente a
 *  diferença que resta. */
export function rotulosDeFontes(fontes: Fonte[]): Map<number, string> {
  const rotulos = new Map<number, string>();
  const porNome = new Map<string, Fonte[]>();
  for (const fonte of fontes) {
    const nome = base(fonte);
    porNome.set(nome, [...(porNome.get(nome) ?? []), fonte]);
  }

  for (const [nome, grupo] of porNome) {
    if (grupo.length === 1) {
      rotulos.set(grupo[0].id, nome);
      continue;
    }
    // Empate: cresce a cauda do caminho até separar, com teto na
    // profundidade do caminho mais fundo do grupo.
    const maxSegmentos = Math.max(
      ...grupo.map((f) => f.caminho.split("/").filter(Boolean).length),
    );
    let resolvido = false;
    for (let n = 2; n <= maxSegmentos && !resolvido; n++) {
      const tentativa = grupo.map((f) => cauda(f.caminho, n));
      if (new Set(tentativa).size === grupo.length) {
        grupo.forEach((f, i) => rotulos.set(f.id, tentativa[i]));
        resolvido = true;
      }
    }
    // Mesma pasta em caixas diferentes: o caminho literal é o que sobra.
    if (!resolvido) grupo.forEach((f) => rotulos.set(f.id, f.caminho));
  }
  return rotulos;
}

/** O rótulo de uma fonte só, quando a lista inteira está à mão. */
export function rotuloDeFonte(fontes: Fonte[] | undefined, id: number): string {
  return rotulosDeFontes(fontes ?? []).get(id) ?? "fonte";
}
