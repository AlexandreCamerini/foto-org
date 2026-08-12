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
}: {
  nivel: string;
  rotulo?: boolean;
}) {
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
        <span className={`text-micro ${baixa ? "text-atencao" : "text-texto-2"}`}>
          {ROTULO[nivel] ?? nivel}
        </span>
      )}
      <span className="sr-only">Confiança {ROTULO[nivel] ?? nivel}</span>
    </span>
  );
}
