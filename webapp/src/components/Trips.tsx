import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, type Agrupamento } from "../api";

interface Props {
  onAbrir: (filtro: { trip_id?: number; event_id?: number }, nome: string) => void;
}

/** Galeria de viagens e eventos como cards com capa — o agrupamento
 * explicável do motor apresentado do jeito que se mostra pra alguém. */
export default function Trips({ onAbrir }: Props) {
  const { data: viagens } = useQuery({ queryKey: ["viagens"], queryFn: api.viagens });
  const { data: eventos } = useQuery({ queryKey: ["eventos"], queryFn: api.eventos });

  const vazio = (viagens ?? []).length === 0 && (eventos ?? []).length === 0;

  return (
    <div className="h-full overflow-y-auto p-4">
      {vazio && (
        <div className="flex h-full items-center justify-center text-texto-2">
          Nenhuma viagem ou evento ainda — gere as sugestões na aba Revisão.
        </div>
      )}
      {(viagens ?? []).length > 0 && (
        <Secao
          titulo="Viagens"
          itens={viagens!}
          onAbrir={(g) => onAbrir({ trip_id: g.id }, g.nome)}
        />
      )}
      {(eventos ?? []).length > 0 && (
        <Secao
          titulo="Eventos"
          itens={eventos!}
          onAbrir={(g) => onAbrir({ event_id: g.id }, g.nome)}
        />
      )}
    </div>
  );
}

function Secao({
  titulo,
  itens,
  onAbrir,
}: {
  titulo: string;
  itens: Agrupamento[];
  onAbrir: (g: Agrupamento) => void;
}) {
  return (
    <section className="mb-6">
      <div className="titulo-painel mb-3">{titulo}</div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
        {itens.map((g) => (
          <Card key={g.id} grupo={g} onAbrir={() => onAbrir(g)} />
        ))}
      </div>
    </section>
  );
}

function Card({ grupo, onAbrir }: { grupo: Agrupamento; onAbrir: () => void }) {
  const [capaFalhou, setCapaFalhou] = useState(false);
  return (
    <button
      onClick={onAbrir}
      className="group relative aspect-[3/2] overflow-hidden rounded-lg bg-cartao text-left shadow-sm transition-transform hover:scale-[1.02]"
    >
      {grupo.capa_id != null && !capaFalhou && (
        <img
          src={api.previewUrl(grupo.capa_id)}
          alt=""
          loading="lazy"
          onError={() => setCapaFalhou(true)}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 p-3">
        <div className="mb-0.5 text-[15px] font-semibold leading-tight">
          {grupo.nome}
        </div>
        <div className="text-texto-2">
          {periodoLegivel(grupo.inicio, grupo.fim)} · {grupo.fotos} fotos
        </div>
      </div>
    </button>
  );
}

function periodoLegivel(inicio: string | null, fim: string | null): string {
  if (!inicio) return "sem período";
  const formato: Intl.DateTimeFormatOptions = {
    day: "2-digit",
    month: "short",
    year: "numeric",
  };
  const de = new Date(inicio).toLocaleDateString("pt-BR", formato);
  const ate = fim ? new Date(fim).toLocaleDateString("pt-BR", formato) : de;
  return de === ate ? de : `${de} – ${ate}`;
}
