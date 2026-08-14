import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import Botao from "../ui/Botao";

const CHAVE_FUNIL = ["funil"] as const;

/** O catálogo só muda quando um trabalho em background mexe nele; até lá,
 *  refazer a contagem custa ~1,4 s e devolve o mesmo número. */
const VALIDADE_MS = 5 * 60 * 1000;

export function useFunil() {
  return useQuery({
    queryKey: CHAVE_FUNIL,
    queryFn: api.funil,
    staleTime: VALIDADE_MS,
  });
}

export interface DegrauVisivel {
  /** Rótulo do degrau; `null` esconde o degrau (ex.: nenhum filtro ativo). */
  rotulo: string;
  valor: number;
  /** Clicar leva ao conjunto que o degrau descreve. Sem isto o degrau é
   *  leitura, não navegação — e um número que não leva a lugar nenhum foi
   *  parte do problema original. */
  aoClicar?: () => void;
  titulo: string;
}

function formatar(n: number): string {
  return n.toLocaleString("pt-BR");
}

/** A leitura única do acervo: conhecidas → alcançáveis → organizáveis → no
 *  filtro atual. Os três primeiros vêm do catálogo na mesma passada e na
 *  mesma unidade (foto), e por isso estreitam sempre; o quarto é da tela e
 *  conta registro — o que a grade tem para mostrar.
 *
 *  Existe porque cinco telas mostravam cinco números para a mesma pergunta,
 *  cada uma com um denominador diferente e nenhuma dizendo qual. A régua
 *  aqui não é mostrar mais informação — é mostrar a MESMA informação nos
 *  mesmos termos em toda tela, para que a diferença entre os degraus seja
 *  lida como um funil e não como uma contradição.
 *
 *  `compacto` é a variante do rodapé (uma linha, sempre visível); a variante
 *  cheia é a do Panorama, onde a pergunta "o que eu tenho?" é o assunto da
 *  tela inteira. */
export default function Funil({
  noFiltro,
  aoIrPara,
  compacto = false,
}: {
  /** Quantas o filtro atual deixou passar. `undefined` numa tela sem grade. */
  noFiltro?: number;
  /** Navega para um degrau. Ausente numa tela que não filtra a biblioteca. */
  aoIrPara?: (alcance: "tudo" | "organizaveis") => void;
  compacto?: boolean;
}) {
  const { data, isPending } = useFunil();
  if (isPending || !data) {
    return compacto ? null : (
      <div className="text-texto-3">contando o acervo…</div>
    );
  }

  const degraus: DegrauVisivel[] = [
    {
      rotulo: "conhecidas",
      valor: data.conhecidas,
      titulo:
        `${formatar(data.registros)} registros no catálogo são ` +
        `${formatar(data.conhecidas)} fotos: a mesma foto vista pelo disco e ` +
        `por um catálogo externo conta uma vez.`,
      aoClicar: aoIrPara && (() => aoIrPara("tudo")),
    },
    {
      rotulo: "alcançáveis",
      valor: data.alcancaveis,
      titulo:
        "Dá para abrir o arquivo agora — disco montado e não é referência " +
        "de nuvem.",
    },
    {
      rotulo: "organizáveis",
      valor: data.organizaveis,
      titulo:
        "Das alcançáveis, as que são acervo seu: o que entra na revisão e " +
        "no plano de cópia. Miniatura de cache e referência ficam de fora " +
        "por não serem acervo.",
      aoClicar: aoIrPara && (() => aoIrPara("organizaveis")),
    },
  ];
  if (noFiltro !== undefined && noFiltro !== data.organizaveis) {
    degraus.push({
      rotulo: "no filtro",
      valor: noFiltro,
      titulo:
        "Quantas o filtro atual desta tela deixou passar. Este conta " +
        "REGISTRO, e não foto: a mesma foto catalogada por duas fontes " +
        "ocupa duas células na grade — por isso ele pode ser maior que os " +
        "degraus do catálogo.",
    });
  }

  return (
    <div
      className={`flex items-center ${compacto ? "gap-1.5" : "flex-wrap gap-2"}`}
      data-testid="funil"
    >
      {degraus.map((d, i) => (
        <span key={d.rotulo} className="flex items-center gap-1.5">
          {i > 0 && (
            <span aria-hidden className="text-texto-3">
              →
            </span>
          )}
          {d.aoClicar ? (
            <Botao
              variante="fantasma"
              tamanho="sm"
              onClick={d.aoClicar}
              title={d.titulo}
              className="px-1 py-0 text-texto hover:text-texto"
            >
              <Degrau {...d} compacto={compacto} />
            </Botao>
          ) : (
            <span title={d.titulo} className="px-1">
              <Degrau {...d} compacto={compacto} />
            </span>
          )}
        </span>
      ))}
    </div>
  );
}

function Degrau({
  rotulo,
  valor,
  compacto,
}: DegrauVisivel & { compacto: boolean }) {
  return (
    <>
      <span className={compacto ? "text-texto-2" : "text-texto"}>
        {formatar(valor)}
      </span>{" "}
      <span className="text-texto-3">{rotulo}</span>
    </>
  );
}
