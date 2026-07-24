import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { api, type FiltrosMidia, type Media } from "./api";
import PhotoGrid from "./components/PhotoGrid";
import Sidebar from "./components/Sidebar";

const ABAS = ["Biblioteca", "Viagens", "Revisão", "Duplicatas"] as const;
type Aba = (typeof ABAS)[number];

export default function App() {
  const [aba, setAba] = useState<Aba>("Biblioteca");
  const [fonte, setFonte] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [ordenacao, setOrdenacao] = useState("data_desc");
  const [zoom, setZoom] = useState(160);
  const [selecionada, setSelecionada] = useState<Media | null>(null);
  const [total, setTotal] = useState(0);

  const filtros: FiltrosMidia = {
    busca: busca || undefined,
    source_id: fonte ?? undefined,
    ordenacao,
  };

  const onTotal = useCallback((t: number) => setTotal(t), []);

  return (
    <div className="flex h-full flex-col">
      {/* Barra de abas */}
      <header className="flex items-center gap-1 border-b border-borda bg-painel px-3 py-1.5">
        <span className="mr-3 font-semibold">Foto Organizer</span>
        {ABAS.map((nome) => (
          <button
            key={nome}
            onClick={() => setAba(nome)}
            className={`rounded-md px-3 py-1 hover:bg-cartao ${
              aba === nome ? "bg-cartao text-acento" : "text-texto-2"
            }`}
          >
            {nome}
          </button>
        ))}
      </header>

      <div className="flex min-h-0 flex-1">
        <Sidebar fonteAtual={fonte} onSelecionar={setFonte} />

        <main className="flex min-w-0 flex-1 flex-col">
          {aba === "Biblioteca" ? (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                <input
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Buscar por nome ou caminho…"
                  className="w-64 rounded-md border border-borda bg-cartao px-2.5 py-1 outline-none placeholder:text-texto-3 focus:border-acento"
                />
                <select
                  value={ordenacao}
                  onChange={(e) => setOrdenacao(e.target.value)}
                  className="rounded-md border border-borda bg-cartao px-2 py-1"
                >
                  <option value="data_desc">Mais recentes</option>
                  <option value="data_asc">Mais antigas</option>
                  <option value="nome">Nome</option>
                  <option value="tamanho_desc">Maiores</option>
                </select>
                <div className="flex-1" />
                <span className="text-texto-2">{total} fotos</span>
              </div>

              <div className="min-h-0 flex-1">
                <PhotoGrid
                  filtros={filtros}
                  zoom={zoom}
                  selecionadoId={selecionada?.id ?? null}
                  onSelecionar={setSelecionada}
                  onTotal={onTotal}
                />
              </div>

              <footer className="flex items-center gap-3 border-t border-borda px-3 py-1.5 text-texto-2">
                <div className="flex-1" />
                <span>Zoom</span>
                <input
                  type="range"
                  min={96}
                  max={320}
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                  className="w-36 accent-acento"
                />
              </footer>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-texto-2">
              {aba} — em construção nesta fase.
            </div>
          )}
        </main>

        <Inspector media={selecionada} />
      </div>
    </div>
  );
}

function Inspector({ media }: { media: Media | null }) {
  const { data: detalhe } = useQuery({
    queryKey: ["detalhe", media?.id],
    queryFn: () => api.detalhe(media!.id),
    enabled: media !== null,
  });

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-l border-borda bg-painel">
      <div className="titulo-painel px-3 pb-2 pt-3">Inspetor</div>
      {media === null ? (
        <div className="px-3 text-texto-2">
          Selecione uma foto para ver metadados, sugestão e evidências.
        </div>
      ) : (
        <div className="overflow-y-auto px-3 pb-3">
          <img
            src={api.thumbUrl(media.id)}
            alt={media.nome}
            className="mb-2 w-full rounded-md bg-cartao object-contain"
          />
          <div className="mb-2 break-all font-semibold">{media.nome}</div>
          <dl className="space-y-1 text-texto-2">
            <Linha rotulo="Capturada" valor={detalhe?.data_capturada} />
            <Linha
              rotulo="Câmera"
              valor={[detalhe?.make, detalhe?.model].filter(Boolean).join(" ")}
            />
            <Linha rotulo="Lente" valor={detalhe?.lente} />
            <Linha
              rotulo="Dimensões"
              valor={
                detalhe?.largura ? `${detalhe.largura}×${detalhe.altura}` : null
              }
            />
            <Linha
              rotulo="GPS"
              valor={
                detalhe?.gps_lat != null
                  ? `${detalhe.gps_lat.toFixed(4)}, ${detalhe.gps_lon!.toFixed(4)}`
                  : null
              }
            />
            <Linha rotulo="Pasta" valor={detalhe?.pasta} />
          </dl>
        </div>
      )}
    </aside>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor?: string | null }) {
  if (!valor) return null;
  return (
    <div className="flex gap-2">
      <dt className="w-20 shrink-0 text-texto-3">{rotulo}</dt>
      <dd className="break-all">{valor}</dd>
    </div>
  );
}
