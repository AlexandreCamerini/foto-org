import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, type FiltrosMidia } from "./api";
import { rotuloDeFonte } from "./fontes";
import Inspector from "./components/Inspector";
import { LinhaDoTempo } from "./components/LinhaDoTempo";
import Loupe from "./components/Loupe";
import Mapa from "./components/Mapa";
import Duplicates from "./components/Duplicates";
import Operations from "./components/Operations";
import Panorama from "./components/Panorama";
import type { Recorte } from "./components/Panorama";
import PhotoGrid from "./components/PhotoGrid";
import RetomarScan from "./components/RetomarScan";
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

// A dica só cita "[ fontes" onde a barra lateral existe — anunciar um atalho
// que não faz nada naquela tela é o mesmo defeito que a lateral inerte tinha.
const DICAS: Record<Aba, string> = {
  Panorama: "clique numa lacuna para recortar a biblioteca",
  Biblioteca: "←↑↓→ seleciona · espaço amplia · [ fontes · ] inspetor",
  Viagens:
    "clique num card para abrir o grupo — lá dá para alternar Lista × Mapa · [ fontes",
  Revisão: "aprove ou rejeite; o destino só sai do papel em Operações · [ fontes",
  Duplicatas: "escolha a principal de cada grupo",
  Operações: "plano → dry-run → cópia verificada; o original nunca é tocado",
};

// O mapa tem outro vocabulário que a grade, e um atalho que não aparece na
// interface não existe. Grupo sem nenhum lugar não tem ponto para clicar
// nem lugar para percorrer — a dica muda junto com a tela vazia, senão
// convida a uma interação que não existe ali.
const DICA_MAPA =
  "clique num ponto para ver as fotos e de onde veio a coordenada · ⇥ percorre os lugares · ⏎ abre";
const DICA_MAPA_VAZIO = "nenhuma foto deste grupo tem lugar estimado";

/** Onde a barra lateral tem efeito.
 *
 * Ela definia `fonte`, que só a Biblioteca lia — nas outras cinco telas ficava
 * visível, clicável e inerte, e foi o que o dono descreveu como "os dois menus
 * não funcionam bem juntos". Um controle visível age sobre a tela em que está;
 * onde não age, não aparece.
 *
 * Duplicatas fica de fora por natureza: um grupo de duplicatas cruza fontes,
 * e filtrar por uma delas esconderia metade de cada par. Operações é sobre
 * planos, não sobre fotos. Panorama é a visão do acervo inteiro. */
const ABAS_COM_FONTE = ["Biblioteca", "Revisão", "Viagens"];

export default function App() {
  // Abre no Panorama: a primeira pergunta de quem tem 30 mil fotos é "em
  // que estado isso está?", não "me mostre a grade".
  const [aba, setAba] = useState<Aba>("Panorama");
  const [fonte, setFonte] = useState<number | null>(null);
  // Recorte pela árvore do disco. Ortogonal à fonte: uma fonte pode abranger
  // vários volumes, e uma pasta pode ter chegado por mais de uma fonte.
  const [pasta, setPasta] = useState<string | null>(null);
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
  const [mes, setMes] = useState<string | undefined>(undefined);
  // Lista × Mapa vale só quando o recorte É um grupo: o mapa responde "onde
  // foi esta viagem", pergunta que não existe para a biblioteca inteira nem
  // para um recorte por ano ou extensão. Por isso é um controle da tela do
  // grupo, e não uma sétima aba no topo.
  const [visaoGrupo, setVisaoGrupo] = useState<"lista" | "mapa">("lista");
  // Mesma queryKey da Sidebar: o cache do react-query serve as duas.
  const { data: fontes } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes });
  const colunasRef = useRef(1);

  const filtros: FiltrosMidia = {
    busca: busca || undefined,
    source_id: fonte ?? undefined,
    trip_id: recorte?.trip_id,
    event_id: recorte?.event_id,
    lacuna: recorte?.lacuna,
    alcance,
    mes,
    ano: recorte?.ano,
    extensao: recorte?.extensao,
    pasta: pasta ?? undefined,
    ordenacao,
  };
  const midia = useMidia(filtros);
  const { itens, total, hasNextPage, fetchNextPage } = midia;
  const job = useJob();

  const grupoAberto =
    recorte?.trip_id !== undefined || recorte?.event_id !== undefined;
  const noMapa = aba === "Biblioteca" && grupoAberto && visaoGrupo === "mapa";
  const [mapaVazio, setMapaVazio] = useState(false);

  // Filtro novo invalida a seleção por índice.
  useEffect(() => {
    setSelIndex(null);
    setLoupeAberto(false);
  }, [busca, fonte, ordenacao, recorte, alcance, mes]);

  // Recorte novo volta para a lista: um mapa de outro grupo herdado do
  // anterior seria a tela certa respondendo pela viagem errada.
  useEffect(() => setVisaoGrupo("lista"), [recorte]);

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
      // No mapa não há grade: as setas navegariam uma seleção invisível.
      if (aba !== "Biblioteca" || digitando || noMapa) return;

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
  }, [aba, selIndex, navegar, noMapa]);

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
            className={`rounded-full px-3.5 py-1 transition-colors duration-[var(--dur-micro)] hover:bg-cartao ${
              aba === nome ? "bg-cartao text-texto" : "text-texto-2"
            }`}
          >
            {nome}
          </button>
        ))}
      </header>

      {/* Pendência de trabalho perdido, visível em qualquer aba: uma
          varredura interrompida sem rastro foi como o dono perdeu um dia
          inteiro de scan sem saber. */}
      <RetomarScan job={job} />

      <div className="flex min-h-0 flex-1">
        {sidebarVisivel && ABAS_COM_FONTE.includes(aba) && (
          <Sidebar
            fonteAtual={fonte}
            onSelecionar={setFonte}
            pastaAtual={pasta}
            onSelecionarPasta={(p) => {
              setPasta(p);
              // Escolher pasta é escolher um conjunto: manter a seleção de
              // uma foto que pode não estar mais na grade deixaria o inspetor
              // descrevendo algo que sumiu da tela.
              setSelIndex(null);
              if (p) setAba("Biblioteca");
            }}
            job={job}
          />
        )}

        <main className="flex min-w-0 flex-1 flex-col">
          {/* O filtro ativo aparece igual nas três telas em que vale. Antes a
              fonte só se via destacada na lateral e o recorte virava chip:
              dois estados de filtro com aparências diferentes, e nenhum jeito
              de saber, olhando o conteúdo, por que ele estava reduzido. */}
          {fonte !== null && ABAS_COM_FONTE.includes(aba) && (
            <div className="flex items-center gap-2 border-b border-borda px-3 py-1.5">
              <span className="text-texto-3">Filtrando por</span>
              <button
                onClick={() => setFonte(null)}
                className="flex items-center gap-1 rounded-full border border-borda-forte bg-painel px-2.5 py-0.5 hover:bg-cartao"
                title="Mostrar todas as fontes"
              >
                {rotuloDeFonte(fontes, fonte)} ✕
              </button>
            </div>
          )}
          {aba === "Panorama" && (
            <Panorama
              aoRecortar={(novo) => {
                // Uma busca de texto deixada de outra visita à Biblioteca
                // fazia um recorte de 4.812 fotos aparecer como "vazio" —
                // a tela mostrava a mensagem genérica de biblioteca vazia
                // em vez de dizer que era a busca antiga filtrando tudo.
                setBusca("");
                setRecorte(novo);
                setAba("Biblioteca");
              }}
            />
          )}
          {aba === "Viagens" && (
            <Trips
              fonte={fonte ?? undefined}
              onAbrir={(filtro, nome) => {
                setBusca("");
                setRecorte({ ...filtro, nome });
                setAba("Biblioteca");
              }}
            />
          )}
          {aba === "Revisão" && <Review job={job} fonte={fonte ?? undefined} />}
          {aba === "Duplicatas" && <Duplicates job={job} />}
          {aba === "Operações" && <Operations job={job} />}
          {aba === "Biblioteca" && (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                {recorte && (
                  <button
                    onClick={() => setRecorte(null)}
                    className="flex items-center gap-1 rounded-full border border-borda-forte bg-painel px-2.5 py-1 hover:bg-cartao"
                    title="Limpar recorte"
                  >
                    {recorte.nome} ✕
                  </button>
                )}
                {/* O mapa é uma VISÃO do grupo aberto, não um destino de
                    navegação: aparece junto do chip que diz qual grupo está
                    aberto, e some quando não há grupo. */}
                {grupoAberto && (
                  <div className="flex shrink-0 overflow-hidden rounded-full border border-borda">
                    {[
                      ["lista", "Lista"],
                      ["mapa", "Mapa"],
                    ].map(([chave, rotulo]) => (
                      <button
                        key={chave}
                        onClick={() => setVisaoGrupo(chave as "lista" | "mapa")}
                        title={
                          chave === "lista"
                            ? "as fotos do grupo na grade"
                            : "onde o grupo aconteceu — e de onde veio cada coordenada"
                        }
                        className={`px-3 py-1 ${
                          visaoGrupo === chave
                            ? "bg-cartao text-texto"
                            : "text-texto-2 hover:text-texto"
                        }`}
                      >
                        {rotulo}
                      </button>
                    ))}
                  </div>
                )}
                {/* No mapa, nada da barra de grade se aplica — e controle
                    visível que não age sobre a tela em que está é o defeito
                    que a barra lateral já teve. */}
                {!noMapa && (
                  <>
                <div className="flex shrink-0 overflow-hidden rounded-full border border-borda">
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
                      className={`px-3 py-1 ${
                        alcance === chave
                          ? "bg-cartao text-texto"
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
                  className="w-64 border-borda bg-cartao outline-none placeholder:text-texto-3 focus:border-acento"
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
                {/* O contador saiu daqui. Ele dizia "197338 fotos" enquanto a
                    lateral dizia "26023" e o rodapé outra coisa — três
                    denominadores, nenhum rótulo. Quem responde "quantas estou
                    vendo" agora é o degrau "no filtro" do funil, no rodapé,
                    ao lado dos degraus que explicam a diferença. De quebra a
                    barra encolhe: ela exigia 1011px só para si e era o que
                    empurrava a busca por baixo do inspetor em tela estreita. */}
                <input
                  type="range"
                  min={96}
                  max={320}
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                  title="Tamanho das miniaturas"
                  className="w-28 accent-acento"
                />
                  </>
                )}
              </div>

              {noMapa ? (
                <Mapa
                  trip_id={recorte?.trip_id}
                  event_id={recorte?.event_id}
                  nome={recorte?.nome}
                  onEstadoVazio={setMapaVazio}
                />
              ) : (
                <div className="flex min-h-0 flex-1">
                  <div className="min-h-0 min-w-0 flex-1">
                    <PhotoGrid
                      midia={midia}
                      zoom={zoom}
                      selecionadoIndex={selIndex}
                      onSelecionar={setSelIndex}
                      onAbrirLoupe={() => setLoupeAberto(true)}
                      onColunas={onColunas}
                    />
                  </div>
                  <LinhaDoTempo
                    filtros={filtros}
                    mesAtivo={mes}
                    onEscolher={setMes}
                  />
                </div>
              )}
            </>
          )}
        </main>

        {/* O inspetor descreve a foto selecionada — só existe onde há grade.
            No mapa quem ocupa a direita é o painel "neste lugar". */}
        {aba === "Biblioteca" && !noMapa && inspetorVisivel && (
          <Inspector media={selecionada} />
        )}
      </div>

      <StatusBar
        job={job}
        dica={noMapa ? (mapaVazio ? DICA_MAPA_VAZIO : DICA_MAPA) : DICAS[aba]}
        // O degrau "no filtro" só existe onde há filtro: nas outras abas a
        // grade não está na tela e o número seria de outra pergunta.
        noFiltro={aba === "Biblioteca" ? total : undefined}
        aoIrPara={(novo) => {
          setAba("Biblioteca");
          setAlcance(novo);
          setRecorte(null);
          setFonte(null);
        }}
      />

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
