import { useCallback, useEffect, useRef, useState } from "react";

import type { FiltrosMidia } from "./api";
import Inspector from "./components/Inspector";
import Loupe from "./components/Loupe";
import Duplicates from "./components/Duplicates";
import Operations from "./components/Operations";
import PhotoGrid from "./components/PhotoGrid";
import Review from "./components/Review";
import Sidebar from "./components/Sidebar";
import Trips from "./components/Trips";
import { useJob } from "./hooks/useJob";
import { useMidia } from "./hooks/useMidia";

const ABAS = [
  "Biblioteca",
  "Viagens",
  "Revisão",
  "Duplicatas",
  "Operações",
] as const;
type Aba = (typeof ABAS)[number];

export default function App() {
  const [aba, setAba] = useState<Aba>("Biblioteca");
  const [fonte, setFonte] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [ordenacao, setOrdenacao] = useState("data_desc");
  const [zoom, setZoom] = useState(160);
  const [selIndex, setSelIndex] = useState<number | null>(null);
  const [loupeAberto, setLoupeAberto] = useState(false);
  // Filtro de agrupamento (clique num card de viagem/evento).
  const [grupo, setGrupo] = useState<{
    trip_id?: number;
    event_id?: number;
    nome: string;
  } | null>(null);
  const colunasRef = useRef(1);

  const filtros: FiltrosMidia = {
    busca: busca || undefined,
    source_id: fonte ?? undefined,
    trip_id: grupo?.trip_id,
    event_id: grupo?.event_id,
    ordenacao,
  };
  const midia = useMidia(filtros);
  const { itens, total, hasNextPage, fetchNextPage } = midia;
  const job = useJob();

  // Filtro novo invalida a seleção por índice.
  useEffect(() => {
    setSelIndex(null);
    setLoupeAberto(false);
  }, [busca, fonte, ordenacao, grupo]);

  const navegar = useCallback(
    (destino: number) => {
      if (total === 0) return;
      const limite = Math.min(itens.length - 1, total - 1);
      const index = Math.max(0, Math.min(destino, limite));
      setSelIndex(index);
      // Chegando perto do fim carregado, puxa a próxima página.
      if (index >= itens.length - 20 && hasNextPage) void fetchNextPage();
    },
    [itens.length, total, hasNextPage, fetchNextPage],
  );

  // Navegação por teclado — o vocabulário universal da categoria.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (aba !== "Biblioteca") return;
      const alvo = e.target as HTMLElement;
      if (alvo.tagName === "INPUT" || alvo.tagName === "SELECT") return;

      const passo: Record<string, number> = {
        ArrowLeft: -1,
        ArrowRight: 1,
        ArrowUp: -colunasRef.current,
        ArrowDown: colunasRef.current,
      };
      if (e.key in passo) {
        e.preventDefault();
        navegar((selIndex ?? -1) === -1 ? 0 : selIndex! + passo[e.key]);
      } else if (e.key === " ") {
        e.preventDefault();
        if (selIndex !== null) setLoupeAberto((v) => !v);
      } else if (e.key === "Escape") {
        setLoupeAberto(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [aba, selIndex, navegar]);

  const onColunas = useCallback((n: number) => {
    colunasRef.current = n;
  }, []);
  const selecionada = selIndex !== null ? (itens[selIndex] ?? null) : null;

  return (
    <div className="flex h-full flex-col">
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
        <Sidebar fonteAtual={fonte} onSelecionar={setFonte} job={job} />

        <main className="flex min-w-0 flex-1 flex-col">
          {aba === "Viagens" && (
            <Trips
              onAbrir={(filtro, nome) => {
                setGrupo({ ...filtro, nome });
                setAba("Biblioteca");
              }}
            />
          )}
          {aba === "Revisão" && <Review job={job} />}
          {aba === "Duplicatas" && <Duplicates job={job} />}
          {aba === "Operações" && <Operations job={job} />}
          {aba === "Biblioteca" && (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                {grupo && (
                  <button
                    onClick={() => setGrupo(null)}
                    className="flex items-center gap-1 rounded-md border border-acento px-2 py-1 text-acento hover:bg-cartao"
                    title="Limpar filtro de agrupamento"
                  >
                    {grupo.nome} ✕
                  </button>
                )}
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
                  midia={midia}
                  zoom={zoom}
                  selecionadoIndex={selIndex}
                  onSelecionar={setSelIndex}
                  onAbrirLoupe={() => setLoupeAberto(true)}
                  onColunas={onColunas}
                />
              </div>

              <footer className="flex items-center gap-3 border-t border-borda px-3 py-1.5 text-texto-2">
                <span className="text-texto-3">
                  ←↑↓→ seleciona · espaço amplia · duplo clique amplia
                </span>
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
          )}
        </main>

        <Inspector media={selecionada} />
      </div>

      {loupeAberto && selIndex !== null && (
        <Loupe
          itens={itens}
          index={selIndex}
          onNavegar={navegar}
          onFechar={() => setLoupeAberto(false)}
        />
      )}
    </div>
  );
}
