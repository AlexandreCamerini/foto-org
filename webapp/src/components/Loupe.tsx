import { useEffect, useState } from "react";

import { api, type Media } from "../api";
import Botao from "../ui/Botao";

interface Props {
  itens: Media[];
  index: number;
  onNavegar: (index: number) => void;
  onFechar: () => void;
}

/** Vista grande estilo Photo Mechanic: espaço abre, setas navegam,
 * clique alterna ajustar↔100%, Esc volta pra grade. */
export default function Loupe({ itens, index, onNavegar, onFechar }: Props) {
  const media = itens[index];
  const [zoom100, setZoom100] = useState(false);

  // Pré-carrega as vizinhas para navegação instantânea.
  useEffect(() => {
    for (const vizinho of [index - 1, index + 1]) {
      const m = itens[vizinho];
      if (m) new Image().src = api.previewUrl(m.id);
    }
    setZoom100(false);
  }, [index, itens]);

  if (!media) return null;

  const faixa = itens.slice(Math.max(0, index - 12), index + 13);
  const dataLegivel = media.data_capturada
    ? new Date(media.data_capturada).toLocaleString("pt-BR")
    : "sem data";

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/95">
      <header className="flex items-center gap-3 px-4 py-2 text-texto-2">
        <span className="font-titulo text-texto">{media.nome}</span>
        <span>{dataLegivel}</span>
        <span>
          {index + 1} / {itens.length}
        </span>
        <div className="flex-1" />
        <span className="text-texto-3">
          espaço/Esc fecha · ←→ navegam · clique = 100%
        </span>
        <Botao
          variante="fantasma"
          tamanho="sm"
          onClick={onFechar}
          aria-label="Fechar"
        >
          ✕
        </Botao>
      </header>

      <div
        className={`flex min-h-0 flex-1 ${
          zoom100 ? "overflow-auto" : "items-center justify-center overflow-hidden"
        }`}
        onClick={() => setZoom100((v) => !v)}
      >
        <img
          src={api.previewUrl(media.id)}
          alt={media.nome}
          draggable={false}
          className={
            zoom100
              ? "max-w-none cursor-zoom-out"
              : "max-h-full max-w-full cursor-zoom-in object-contain"
          }
        />
      </div>

      <footer className="flex justify-center gap-1 overflow-x-auto px-4 py-2">
        {faixa.map((m) => {
          const i = itens.indexOf(m);
          return (
            <button
              key={m.id}
              onClick={() => onNavegar(i)}
              className={`h-14 w-14 shrink-0 overflow-hidden rounded ${
                i === index ? "outline outline-2 outline-acento" : "opacity-60"
              }`}
            >
              <img
                src={api.thumbUrl(m.id)}
                alt={m.nome}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </button>
          );
        })}
      </footer>
    </div>
  );
}
