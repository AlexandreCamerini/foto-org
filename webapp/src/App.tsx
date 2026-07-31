import { useCallback, useEffect, useRef, useState } from "react";

import type { FiltrosMidia } from "./api";
import Inspector from "./components/Inspector";
import Loupe from "./components/Loupe";
import Duplicates from "./components/Duplicates";
import Operations from "./components/Operations";
import Panorama from "./components/Panorama";
import type { Recorte } from "./components/Panorama";
import PhotoGrid from "./components/PhotoGrid";
import Review from "./components/Review";
import Sidebar from "./components/Sidebar";
import StatusBar from "./components/StatusBar";
import Trips from "./components/Trips";
import { useJob } from "./hooks/useJob";
import { useMidia } from "./hooks/useMidia";

const ABAS = [
  "Panorama",
  "Biblioteca",
  "Viagens",
  "Revisão",
  "Duplicatas",
  "Operações",
] as const;
type Aba = (typeof ABAS)[number];

const DICAS: Record<Aba, string> = {
  Panorama: "clique numa lacuna para recortar a biblioteca · [ fontes",
  Biblioteca: "←↑↓→ seleciona · espaço amplia · [ fontes · ] inspetor",
  Viagens: "clique num card para ver as fotos do grupo · [ fontes",
  Revisão: "aprove ou rejeite; o destino só sai do papel em Operações",
  Duplicatas: "escolha a principal de cada grupo · [ fontes",
  Operações: "plano → dry-run → cópia verificada; o original nunca é tocado",
};

export default function App() {
  // Abre no Panorama: a primeira pergunta de quem tem 30 mil fotos é "em
  // que estado isso está?", não "me mostre a grade".
  const [aba, setAba] = useState<Aba>("Panorama");
  const [fonte, setFonte] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [ordenacao, setOrdenacao] = useState("data_desc");
  const [zoom, setZoom] = useState(160);
  const [selIndex, setSelIndex] = useState<number | null>(null);
  const [loupeAberto, setLoupeAberto] = useState(false);
  const [sidebarVisivel, setSidebarVisivel] = useState(true);
  const [inspetorVisivel, setInspetorVisivel] = useState(true);
  // Recorte da biblioteca vindo de outra aba: card de viagem/evento no
  // Viagens, lacuna ou faceta no Panorama. Um só, e sempre visível como
  // chip removível — filtro escondido é filtro que confunde.
  const [recorte, setRecorte] = useState<Recorte | null>(null);
  // O dono importou 44.661 fotos do Apple Fotos e a Biblioteca respondia (0):
  // elas não têm arquivo local e ficavam invisíveis. Agora aparecem por
  // padrão, marcadas, e este controle isola o que é acionável.
  const [alcance, setAlcance] = useState("tudo");
  const colunasRef = useRef(1);

  const filtros: FiltrosMidia = {
    busca: busca || undefined,
    source_id: fonte ?? undefined,
    trip_id: recorte?.trip_id,
    event_id: recorte?.event_id,
    lacuna: recorte?.lacuna,
    alcance,
    ano: recorte?.ano,
    extensao: recorte?.extensao,
    ordenacao,
  };
  const midia = useMidia(filtros);
  const { itens, total, hasNextPage, fetchNextPage } = midia;
  const job = useJob();

  // Filtro novo invalida a seleção por índice.
  useEffect(() => {
    setSelIndex(null);
    setLoupeAberto(false);
  }, [busca, fonte, ordenacao, recorte, alcance]);

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
      const alvo = e.target as HTMLElement;
      const digitando =
        alvo.tagName === "INPUT" ||
        alvo.tagName === "SELECT" ||
        alvo.isContentEditable;

      // Recolher os painéis laterais, em qualquer aba. A direção de arte
      // pede ⌘1/⌘3, que só chegam na página no app empacotado — o
      // navegador reserva ⌘1–⌘8 para trocar de aba. Então [ e ] são os
      // atalhos que funcionam hoje, e ⌘1/⌘3 seguem valendo no Tauri.
      const comando = e.metaKey || e.ctrlKey;
      const painel =
        (comando && (e.key === "1" || e.key === "3")) ||
        (!digitando && !comando && (e.key === "[" || e.key === "]"));
      if (painel) {
        e.preventDefault();
        if (e.key === "1" || e.key === "[") setSidebarVisivel((v) => !v);
        else setInspetorVisivel((v) => !v);
        return;
      }
      if (aba !== "Biblioteca" || digitando) return;

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
        {sidebarVisivel && (
          <Sidebar fonteAtual={fonte} onSelecionar={setFonte} job={job} />
        )}

        <main className="flex min-w-0 flex-1 flex-col">
          {aba === "Panorama" && (
            <Panorama
              aoRecortar={(novo) => {
                setRecorte(novo);
                setAba("Biblioteca");
              }}
            />
          )}
          {aba === "Viagens" && (
            <Trips
              onAbrir={(filtro, nome) => {
                setRecorte({ ...filtro, nome });
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
                {recorte && (
                  <button
                    onClick={() => setRecorte(null)}
                    className="flex items-center gap-1 rounded-md border border-acento px-2 py-1 text-acento hover:bg-cartao"
                    title="Limpar recorte"
                  >
                    {recorte.nome} ✕
                  </button>
                )}
                <div className="flex shrink-0 overflow-hidden rounded-md border border-borda">
                  {[
                    ["tudo", "Tudo"],
                    ["organizaveis", "Organizáveis"],
                    ["faltantes", "Fora de alcance"],
                  ].map(([chave, rotulo]) => (
                    <button
                      key={chave}
                      onClick={() => setAlcance(chave)}
                      title={
                        chave === "tudo"
                          ? "tudo que o app conhece, inclusive sem arquivo local"
                          : chave === "organizaveis"
                            ? "só o que dá para revisar e copiar agora"
                            : "só o que está no iCloud ou em volume desmontado"
                      }
                      className={`px-2.5 py-1 ${
                        alcance === chave
                          ? "bg-cartao text-acento"
                          : "text-texto-2 hover:text-texto"
                      }`}
                    >
                      {rotulo}
                    </button>
                  ))}
                </div>
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
                <input
                  type="range"
                  min={96}
                  max={320}
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                  title="Tamanho das miniaturas"
                  className="w-28 accent-acento"
                />
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
            </>
          )}
        </main>

        {/* O inspetor descreve a foto selecionada — só existe onde há grade. */}
        {aba === "Biblioteca" && inspetorVisivel && (
          <Inspector media={selecionada} />
        )}
      </div>

      <StatusBar job={job} dica={DICAS[aba]} />

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
