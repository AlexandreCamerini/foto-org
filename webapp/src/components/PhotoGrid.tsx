import { useInfiniteQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useMemo, useRef, useState } from "react";

import { api, type FiltrosMidia, type Media } from "../api";

const PAGINA = 200;
const GAP = 8;

interface Props {
  filtros: FiltrosMidia;
  zoom: number; // lado da célula em px
  selecionadoId: number | null;
  onSelecionar: (media: Media) => void;
  onTotal?: (total: number) => void;
}

export default function PhotoGrid({
  filtros,
  zoom,
  selecionadoId,
  onSelecionar,
  onTotal,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [largura, setLargura] = useState(800);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => setLargura(el.clientWidth));
    observer.observe(el);
    setLargura(el.clientWidth);
    return () => observer.disconnect();
  }, []);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ["midia", filtros],
      queryFn: ({ pageParam }) => api.midia(filtros, pageParam, PAGINA),
      initialPageParam: 0,
      getNextPageParam: (ultima) => {
        const proximo = ultima.offset + ultima.itens.length;
        return proximo < ultima.total ? proximo : undefined;
      },
    });

  const itens = useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.itens),
    [data],
  );
  const total = data?.pages[0]?.total ?? 0;
  useEffect(() => onTotal?.(total), [total, onTotal]);

  const colunas = Math.max(1, Math.floor((largura - GAP) / (zoom + GAP)));
  const linhas = Math.ceil(itens.length / colunas);

  const virtualizer = useVirtualizer({
    count: linhas,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => zoom + GAP,
    overscan: 4,
  });

  // Busca a próxima página quando a última linha entra na janela.
  const linhasVirtuais = virtualizer.getVirtualItems();
  useEffect(() => {
    const ultima = linhasVirtuais.at(-1);
    if (!ultima) return;
    if (ultima.index >= linhas - 3 && hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [linhasVirtuais, linhas, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (total === 0) {
    return (
      <div className="flex h-full items-center justify-center text-texto-2">
        Nenhuma foto no filtro atual — adicione uma pasta ou importe um
        catálogo na barra lateral.
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto px-2">
      <div
        style={{ height: virtualizer.getTotalSize(), position: "relative" }}
      >
        {linhasVirtuais.map((linha) => (
          <div
            key={linha.key}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${linha.start}px)`,
              display: "flex",
              gap: GAP,
              paddingTop: GAP,
            }}
          >
            {Array.from({ length: colunas }, (_, c) => {
              const media = itens[linha.index * colunas + c];
              if (!media) return <div key={c} style={{ width: zoom }} />;
              const selecionada = media.id === selecionadoId;
              return (
                <button
                  key={media.id}
                  onClick={() => onSelecionar(media)}
                  title={media.nome}
                  className={`relative shrink-0 overflow-hidden rounded-md bg-cartao outline-offset-[-2px] ${
                    selecionada ? "outline outline-2 outline-acento" : ""
                  }`}
                  style={{ width: zoom, height: zoom }}
                >
                  <img
                    src={api.thumbUrl(media.id)}
                    alt={media.nome}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
