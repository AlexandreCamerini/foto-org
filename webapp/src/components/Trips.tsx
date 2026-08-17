import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, type Agrupamento } from "../api";

interface Props {
  /** Fonte escolhida na barra lateral. O controle vale nesta tela também:
   *  antes ele ficava visível aqui e não fazia nada. */
  fonte?: number;
  /** `vista` abre o grupo direto na Biblioteca já no modo pedido — "mapa"
   *  é o que o badge "Mapa" do card usa. Sem isso, o mapa existe (D-050)
   *  mas ninguém acha: 3 passos sem nenhuma pista visual até esta fatia. */
  onAbrir: (
    filtro: { trip_id?: number; event_id?: number },
    nome: string,
    vista?: "lista" | "mapa",
  ) => void;
}

/** Galeria de viagens e eventos como cards com capa — o agrupamento
 * explicável do motor apresentado do jeito que se mostra pra alguém. */
export default function Trips({ onAbrir, fonte }: Props) {
  const { data: viagens, isPending: viagensPendente } = useQuery({
    queryKey: ["viagens", fonte],
    queryFn: () => api.viagens(fonte),
  });
  const { data: eventos, isPending: eventosPendente } = useQuery({
    queryKey: ["eventos", fonte],
    queryFn: () => api.eventos(fonte),
  });

  // As duas consultas eram lentas o bastante (D-069 achado 3 — N+1 sem
  // índice, 50-120s+ medidos no acervo real) para a tela terminar de
  // carregar e mostrar "nenhuma viagem" antes da resposta chegar, mesmo
  // com 190 grupos existentes. "Ainda carregando" e "realmente vazio"
  // não podem ser o mesmo estado.
  const carregando = viagensPendente || eventosPendente;
  const vazio =
    !carregando && (viagens ?? []).length === 0 && (eventos ?? []).length === 0;

  return (
    <div className="h-full overflow-y-auto p-4">
      {carregando && (
        <div className="flex h-full items-center justify-center text-texto-3">
          carregando…
        </div>
      )}
      {vazio && (
        <div className="flex h-full items-center justify-center text-texto-2">
          Nenhuma viagem ou evento ainda — gere as sugestões na aba Revisão.
        </div>
      )}
      {(viagens ?? []).length > 0 && (
        <Secao
          titulo="Viagens"
          itens={viagens!}
          onAbrir={(g, vista) => onAbrir({ trip_id: g.id }, g.nome, vista)}
        />
      )}
      {(eventos ?? []).length > 0 && (
        <Secao
          titulo="Eventos"
          itens={eventos!}
          onAbrir={(g, vista) => onAbrir({ event_id: g.id }, g.nome, vista)}
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
  onAbrir: (g: Agrupamento, vista?: "lista" | "mapa") => void;
}) {
  return (
    <section className="mb-6">
      <div className="titulo-painel mb-3">{titulo}</div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
        {itens.map((g) => (
          <Card
            key={g.id}
            grupo={g}
            onAbrir={() => onAbrir(g)}
            onAbrirMapa={() => onAbrir(g, "mapa")}
          />
        ))}
      </div>
    </section>
  );
}

function Card({
  grupo,
  onAbrir,
  onAbrirMapa,
}: {
  grupo: Agrupamento;
  onAbrir: () => void;
  onAbrirMapa: () => void;
}) {
  const [capaFalhou, setCapaFalhou] = useState(false);
  // A capa é uma miniatura (cacheada, do tamanho do card), não a prévia do
  // loupe — e quando ela não carrega o card diz por quê em vez de ficar em
  // branco. Um evento inteiro num volume desmontado desenhava um cartão vazio,
  // e o dono concluiu que o sistema estava quebrado; ele estava mudo.
  const semCapa = grupo.capa_id == null || capaFalhou;
  return (
    // Wrapper não-interativo: o card (role="button") e o badge "Mapa"
    // (button de verdade) são IRMÃOS aqui, não um dentro do outro —
    // botão aninhado em role="button" é anti-padrão ARIA (nome acessível
    // do filho vaza pro pai, leitor de tela anuncia duplicado). Como
    // resultado, também não precisa mais de stopPropagation: cliques no
    // badge nunca borbulham pro card, porque não são descendentes dele.
    <div className="group relative aspect-[3/2] overflow-hidden rounded-controle bg-cartao">
      <div
        role="button"
        tabIndex={0}
        onClick={onAbrir}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onAbrir();
          }
        }}
        className="absolute inset-0 cursor-pointer text-left outline outline-2 outline-offset-[-2px] outline-transparent transition-colors hover:outline-acento"
      >
        {grupo.capa_id != null && !capaFalhou && (
          <img
            src={api.thumbUrl(grupo.capa_id)}
            alt=""
            loading="lazy"
            onError={() => setCapaFalhou(true)}
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        )}
        {semCapa && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-texto-3">
            <span aria-hidden className="text-2xl">
              ⊘
            </span>
            <span className="text-texto-2">capa fora de alcance</span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-3">
          <div className="mb-0.5 text-realce font-titulo leading-tight">
            {grupo.nome}
          </div>
          <div className="text-texto-2">
            {periodoLegivel(grupo.inicio, grupo.fim)} · {grupo.fotos} fotos
          </div>
        </div>
      </div>
      {/* Achado D-050: o mapa existe (Lista × Mapa, dentro do grupo aberto)
          mas não tinha nenhuma pista visível de que existe antes de já
          saber procurar. Badge sempre visível, não só no hover — é
          exatamente a affordance que faltava. */}
      <button
        onClick={onAbrirMapa}
        title="ver onde este grupo aconteceu"
        className="absolute right-2 top-2 z-10 rounded-full border border-borda bg-janela/80 px-2 py-0.5 text-texto-2 backdrop-blur-sm transition-colors hover:border-borda-forte hover:text-texto"
      >
        Mapa
      </button>
    </div>
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
