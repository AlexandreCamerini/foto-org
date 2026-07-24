import { useQuery } from "@tanstack/react-query";

import { api } from "../api";

const ICONE_TIPO: Record<string, string> = {
  pasta: "📁",
  apple_photos: "🍎",
  google_takeout: "🌐",
};

interface Props {
  fonteAtual: number | null;
  onSelecionar: (sourceId: number | null) => void;
}

export default function Sidebar({ fonteAtual, onSelecionar }: Props) {
  const { data: fontes } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes });
  const { data: status } = useQuery({ queryKey: ["status"], queryFn: api.status });

  const total = status?.total ?? 0;

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-borda bg-painel">
      <div className="titulo-painel px-3 pb-2 pt-3">Fontes</div>
      <nav className="flex-1 overflow-y-auto">
        <button
          onClick={() => onSelecionar(null)}
          className={`block w-full truncate px-3 py-1.5 text-left hover:bg-cartao ${
            fonteAtual === null ? "border-l-2 border-acento bg-cartao" : ""
          }`}
        >
          Todas as fotos
          <span className="ml-1.5 text-texto-2">({total})</span>
        </button>
        {(fontes ?? []).map((fonte) => (
          <button
            key={fonte.id}
            onClick={() => onSelecionar(fonte.id)}
            title={fonte.caminho}
            className={`block w-full truncate px-3 py-1.5 text-left hover:bg-cartao ${
              fonteAtual === fonte.id ? "border-l-2 border-acento bg-cartao" : ""
            }`}
          >
            <span className="mr-1">{ICONE_TIPO[fonte.tipo] ?? "📁"}</span>
            {fonte.apelido ?? fonte.caminho.split("/").pop()}
            <span className="ml-1.5 text-texto-2">({fonte.fotos})</span>
            {!fonte.disponivel && (
              <span className="ml-1 text-conf-media" title="indisponível">
                ⚠
              </span>
            )}
          </button>
        ))}
      </nav>
      <div className="border-t border-borda px-3 py-2 text-texto-2">
        {total} fotos · {status?.fontes ?? 0} fontes
        {status?.erros ? ` · ${status.erros} erros` : ""}
      </div>
    </aside>
  );
}
