import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type { Faceta } from "../api";

export interface Recorte {
  trip_id?: number;
  event_id?: number;
  lacuna?: string;
  ano?: number;
  extensao?: string;
  nome: string;
}

function Barra({ fracao }: { fracao: number }) {
  return (
    <div className="mt-1 h-0.5 bg-borda">
      <div
        className="h-full bg-acento"
        style={{ width: `${Math.max(2, fracao * 100)}%` }}
      />
    </div>
  );
}

function ListaFacetas({
  titulo,
  itens,
  aoClicar,
}: {
  titulo: string;
  itens: Faceta[];
  aoClicar?: (faceta: Faceta) => void;
}) {
  return (
    <section className="min-w-0 flex-1">
      <h3 className="titulo-painel mb-2">
        {titulo}
      </h3>
      {itens.slice(0, 12).map((f) => (
        <button
          key={f.chave}
          onClick={aoClicar ? () => aoClicar(f) : undefined}
          disabled={!aoClicar}
          className={`flex w-full items-baseline gap-2 rounded px-1.5 py-0.5 text-left ${
            aoClicar ? "hover:bg-cartao" : "cursor-default"
          }`}
        >
          <span className="min-w-0 flex-1 truncate">{f.chave}</span>
          <span className="text-texto-2">{f.quantidade}</span>
        </button>
      ))}
      {itens.length > 12 && (
        <div className="px-1.5 text-texto-3">
          e mais {itens.length - 12}…
        </div>
      )}
    </section>
  );
}

/** Panorama: o que a base sabe, e — mais útil — onde ela não sabe.
 * Cada lacuna é clicável porque contar sem poder agir não resolve nada. */
export default function Panorama({
  aoRecortar,
}: {
  aoRecortar: (recorte: Recorte) => void;
}) {
  const { data } = useQuery({ queryKey: ["panorama"], queryFn: api.panorama });
  // Mesma queryKey da Sidebar: o cache do react-query serve as duas.
  const { data: fontes } = useQuery({
    queryKey: ["fontes"],
    queryFn: api.fontes,
  });

  if (!data) {
    return (
      <div className="flex flex-1 items-center justify-center text-texto-2">
        Lendo o catálogo…
      </div>
    );
  }
  if (data.total === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-texto-2">
        Catálogo vazio — adicione uma pasta na barra lateral para começar.
      </div>
    );
  }

  const anos = data.por_ano.map((a) => a.chave);
  const porFonte = new Map(
    data.cruzamento_ano_fonte.map((c) => [`${c.ano}|${c.source_id}`, c.quantidade]),
  );
  const fontesComFotos = (fontes ?? []).filter((f) => f.fotos > 0);
  const comLacuna = data.lacunas.filter((l) => l.quantidade > 0);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3">
      <p className="mb-3 text-texto-2">
        {data.total} fotos no catálogo.{" "}
        {comLacuna.length === 0
          ? "Nenhuma lacuna — tudo que o motor precisa está preenchido."
          : "Clique numa lacuna para trabalhar só naquele conjunto."}
      </p>

      <section className="mb-5">
        <h3 className="titulo-painel mb-2">
          Lacunas
        </h3>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {data.lacunas.map((l) => (
            <button
              key={l.chave}
              onClick={() =>
                aoRecortar({ lacuna: l.chave, nome: `${l.rotulo}` })
              }
              disabled={l.quantidade === 0}
              className="rounded-md border border-borda bg-cartao px-3 py-2 text-left hover:border-acento disabled:opacity-40 disabled:hover:border-borda"
            >
              <div className="text-[15px]">{l.quantidade}</div>
              <div className="truncate text-texto-2">{l.rotulo}</div>
              <Barra fracao={l.quantidade / data.total} />
            </button>
          ))}
        </div>
      </section>

      {fontesComFotos.length > 0 && anos.length > 0 && (
        <section className="mb-5">
          <h3 className="titulo-painel mb-2">
            Ano por fonte
          </h3>
          <div className="overflow-x-auto">
            <table className="border-collapse">
              <thead>
                <tr className="text-texto-2">
                  <th className="px-2 py-1 text-left font-normal">ano</th>
                  {fontesComFotos.map((f) => (
                    <th
                      key={f.id}
                      className="max-w-32 truncate px-2 py-1 text-right font-normal"
                      title={f.caminho}
                    >
                      {f.apelido ?? f.caminho.split("/").pop()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {anos.map((ano) => (
                  <tr key={ano} className="border-t border-borda">
                    <td className="px-2 py-1">{ano}</td>
                    {fontesComFotos.map((f) => {
                      const n = porFonte.get(`${ano}|${f.id}`) ?? 0;
                      return (
                        <td
                          key={f.id}
                          className={`px-2 py-1 text-right ${
                            n === 0 ? "text-texto-3" : ""
                          }`}
                        >
                          {n === 0 ? "·" : n}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-6">
        <ListaFacetas
          titulo="Por ano"
          itens={data.por_ano}
          aoClicar={(f) =>
            f.chave === "sem data"
              ? aoRecortar({ lacuna: "sem_data", nome: "sem data de captura" })
              : aoRecortar({ ano: Number(f.chave), nome: f.chave })
          }
        />
        {/* Câmera é leitura: o catálogo não filtra por ela hoje, e um botão
            que não faz nada é pior do que texto. */}
        <ListaFacetas titulo="Por câmera" itens={data.por_camera} />
        <ListaFacetas
          titulo="Por formato"
          itens={data.por_extensao}
          aoClicar={(f) =>
            aoRecortar({ extensao: f.chave, nome: `.${f.chave}` })
          }
        />
      </div>
    </div>
  );
}
