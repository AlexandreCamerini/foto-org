import { useQuery } from "@tanstack/react-query";

import { api, type FiltrosMidia } from "../api";
import Botao from "../ui/Botao";

const MESES = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
];

function rotulo(mes: string): { ano: string; mes: string } {
  const [ano, m] = mes.split("-");
  return { ano, mes: MESES[Number(m) - 1] ?? m };
}

/** A régua de tempo ao lado da grade.
 *
 * Sem ela, rolar é a única forma de chegar em 2015 — e num acervo de 103.938
 * registros paginados de 200 em 200 isso não é forma. O salto é por FILTRO e
 * não por rolagem: chegar ao offset de março de 2019 rolando exigiria
 * carregar tudo que veio antes.
 *
 * É o que o Lightroom faz e a razão de ele ser elogiado pela navegação
 * justamente onde é criticado pela aparência. */
export function LinhaDoTempo({
  filtros,
  mesAtivo,
  onEscolher,
}: {
  filtros: FiltrosMidia;
  mesAtivo?: string;
  onEscolher: (mes: string | undefined) => void;
}) {
  // Sem `mes` na chave: a régua mostra o acervo do recorte, não do mês
  // escolhido — senão escolher um mês faria os outros desaparecerem dela.
  const { mes: _ignorado, ...semMes } = filtros;
  const { data } = useQuery({
    queryKey: ["linha-do-tempo", semMes],
    queryFn: () => api.linhaDoTempo(semMes),
  });

  if (!data?.length) return null;
  const maior = Math.max(...data.map((d) => d.quantidade));
  let anoAnterior = "";

  return (
    <div className="flex w-24 shrink-0 flex-col overflow-y-auto border-l border-borda">
      {mesAtivo && (
        <Botao
          variante="fantasma"
          onClick={() => onEscolher(undefined)}
          className="sticky top-0 z-10 rounded-none border-b border-borda bg-painel px-2 py-1 text-acento"
        >
          todo o período ✕
        </Botao>
      )}
      {data.map(({ mes, quantidade }) => {
        const { ano, mes: nome } = rotulo(mes);
        const novoAno = ano !== anoAnterior;
        anoAnterior = ano;
        return (
          <div key={mes}>
            {novoAno && (
              <div className="px-2 pt-1.5 text-texto-3">{ano}</div>
            )}
            <button
              onClick={() => onEscolher(mes === mesAtivo ? undefined : mes)}
              title={`${nome}/${ano} · ${quantidade} fotos`}
              className={`flex w-full items-center gap-1.5 px-2 py-0.5 hover:bg-cartao ${
                mes === mesAtivo ? "text-acento" : "text-texto-2"
              }`}
            >
              <span className="w-6 text-left">{nome}</span>
              {/* A barra é a única pista de onde o acervo se concentra —
                  238 meses numa lista sem peso visual não dizem nada. */}
              <span
                aria-hidden
                className={`h-1 rounded-sm ${
                  mes === mesAtivo ? "bg-acento" : "bg-borda-forte"
                }`}
                style={{ width: `${Math.max(4, (quantidade / maior) * 44)}px` }}
              />
            </button>
          </div>
        );
      })}
    </div>
  );
}
