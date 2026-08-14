/** Indicador de confiança.
 *
 * Confiança é QUANTIDADE, não cor: três segmentos preenchidos 3/3, 2/3, 1/3.
 * Dois motivos, os dois em docs/DECISOES.md (D-017):
 *
 * 1. Numa ferramenta de foto, três cores saturadas competem com a imagem —
 *    contraria "a foto é a cor da interface" (docs/DIRECAO_DE_ARTE.md).
 * 2. Cor como canal único falha para daltônicos. Quantidade não falha.
 *
 * Só a confiança baixa recebe cor, porque é a única que pede olho humano.
 * Reservar a cor para ela faz o pouco que sobra significar "olhe aqui".
 */

const ROTULO: Record<string, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};
const PREENCHIDOS: Record<string, number> = { alta: 3, media: 2, baixa: 1 };

export function Confianca({
  nivel,
  rotulo = true,
  naoClassificado = false,
}: {
  nivel: string;
  rotulo?: boolean;
  /** A sugestão não tem nenhuma evidência de categoria/viagem/evento — o
   * `nivel` recebido reflete só a confiança de outro campo (tipicamente a
   * data). Mostrar "Alta"/"Média"/"Baixa" aqui mentiria sobre existir uma
   * classificação: não é baixa confiança, é NENHUMA classificação (D-071).
   * Troca os três segmentos por um traço — a mesma gramática visual
   * (quantidade, não cor) dizendo "zero categoria", não "pouca categoria". */
  naoClassificado?: boolean;
}) {
  if (naoClassificado) {
    return (
      <span
        className="inline-flex shrink-0 items-center gap-1.5"
        title={`Sem categoria — a data é confiável (${ROTULO[nivel] ?? nivel}), mas nada indica para onde esta foto deveria ir.`}
      >
        <span className="flex gap-[2px]" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="block h-[11px] w-[3px] rounded-[1px] bg-realce"
            />
          ))}
        </span>
        {rotulo && (
          <span className="text-[11px] text-texto-2">Sem categoria</span>
        )}
        <span className="sr-only">
          Sem categoria — data confiável, mas nenhuma categoria identificada
        </span>
      </span>
    );
  }
  const cheios = PREENCHIDOS[nivel] ?? 0;
  const baixa = nivel === "baixa";
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1.5"
      title={`Confiança ${ROTULO[nivel] ?? nivel}`}
    >
      <span className="flex gap-[2px]" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={`block h-[11px] w-[3px] rounded-[1px] ${
              i < cheios
                ? baixa
                  ? "bg-atencao"
                  : "bg-texto-2"
                : "bg-realce"
            }`}
          />
        ))}
      </span>
      {rotulo && (
        <span className={`text-[11px] ${baixa ? "text-atencao" : "text-texto-2"}`}>
          {ROTULO[nivel] ?? nivel}
        </span>
      )}
      <span className="sr-only">Confiança {ROTULO[nivel] ?? nivel}</span>
    </span>
  );
}
