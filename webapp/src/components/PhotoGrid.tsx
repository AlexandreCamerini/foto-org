import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef, useState } from "react";

import { Miniatura } from "./Miniatura";
import type { MidiaQuery } from "../hooks/useMidia";
import Botao from "../ui/Botao";

const GAP = 10;

interface Props {
  midia: MidiaQuery;
  zoom: number; // lado da célula em px
  selecionadoIndex: number | null;
  onSelecionar: (index: number) => void;
  onAbrirLoupe: () => void;
  onColunas?: (n: number) => void;
  /** Abre o modal de adicionar pasta do App.tsx (CONS-05/D-07) — mesma ação
   * do botão da Sidebar. */
  onAdicionarPasta: () => void;
}

export default function PhotoGrid({
  midia,
  zoom,
  selecionadoIndex,
  onSelecionar,
  onAbrirLoupe,
  onColunas,
  onAdicionarPasta,
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

  const { itens, total, fetchNextPage, hasNextPage, isFetchingNextPage } =
    midia;

  const colunas = Math.max(1, Math.floor((largura - GAP) / (zoom + GAP)));
  useEffect(() => onColunas?.(colunas), [colunas, onColunas]);
  const linhas = Math.ceil(itens.length / colunas);

  const virtualizer = useVirtualizer({
    count: linhas,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => zoom + GAP,
    overscan: 4,
  });

  // Seleção via teclado mantém o item visível.
  useEffect(() => {
    if (selecionadoIndex !== null && colunas > 0) {
      virtualizer.scrollToIndex(Math.floor(selecionadoIndex / colunas), {
        align: "auto",
      });
    }
  }, [selecionadoIndex, colunas, virtualizer]);

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
      <div className="flex h-full flex-col items-center justify-center gap-3 text-texto-2">
        <span>
          Nenhuma foto no filtro atual — adicione uma pasta ou importe um
          catálogo na barra lateral.
        </span>
        <Botao onClick={onAdicionarPasta}>Adicionar pasta…</Botao>
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
              const index = linha.index * colunas + c;
              const media = itens[index];
              if (!media) return <div key={c} style={{ width: zoom }} />;
              const selecionada = index === selecionadoIndex;
              return (
                <button
                  key={media.id}
                  onClick={() => onSelecionar(index)}
                  onDoubleClick={onAbrirLoupe}
                  title={media.nome}
                  className={`relative shrink-0 overflow-hidden rounded-md bg-cartao outline-offset-[-2px] ${
                    selecionada ? "outline outline-2 outline-acento" : ""
                  }`}
                  style={{ width: zoom, height: zoom }}
                >
                  <Miniatura media={media} className="h-full w-full" />
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
