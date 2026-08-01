import { useState } from "react";

import { api } from "../api";

/** O que a miniatura precisa saber, e só isso. `Media` satisfaz este
 *  formato estruturalmente; o ponto do mapa também, sem precisar fingir
 *  ser uma foto inteira só para desenhar 40×30 pixels. */
export interface AlvoMiniatura {
  id: number;
  nome: string;
  data_capturada: string | null;
  motivo_indisponivel: string | null;
}

/** A miniatura e os três estados que ela precisa separar.
 *
 * Antes existia um só: `<img>` apontando para o endpoint. Quando o arquivo
 * estava num volume desmontado o navegador desenhava o ícone de imagem
 * quebrada, e o dono — que abriu a fila num grupo 100% fora de alcance —
 * concluiu que a tela inteira estava quebrada. Ela não estava; ela estava
 * calada. */
export function Miniatura({
  media,
  className = "",
  denso = false,
}: {
  media: AlvoMiniatura;
  className?: string;
  /** Miniatura pequena demais para caber a frase (a lista do mapa desenha
   *  40×30). Medido: a data sozinha ocupa 50 px a 9px, vazava 5 px para fora
   *  da caixa dos dois lados e o motivo saía com altura zero — texto que não
   *  cabe não é honestidade, é sujeira. No denso fica só o glifo; o motivo
   *  continua no `title` e para leitor de tela, e a linha ao lado já traz
   *  nome e data. */
  denso?: boolean;
}) {
  const [falhou, setFalhou] = useState(false);
  const motivo = media.motivo_indisponivel;

  if ((motivo || falhou) && denso) {
    return (
      <div
        className={`flex items-center justify-center overflow-hidden bg-cartao text-texto-3 ${className}`}
        title={`${media.nome} — ${motivo ?? "não consegui gerar a miniatura"}`}
      >
        <span aria-hidden>⊘</span>
        <span className="sr-only">{motivo ?? "sem miniatura"}</span>
      </div>
    );
  }

  if (motivo || falhou) {
    // Sem imagem, o que o catálogo sabe é tudo que resta — e ele sabe a data
    // de todas as 44.661 do iCloud. Um cartão que só repete "sem arquivo"
    // 44 mil vezes é honesto e inútil; com a data ele volta a ser navegável,
    // que é o que a ordenação por tempo pressupõe.
    const quando = media.data_capturada
      ? new Date(media.data_capturada).toLocaleDateString("pt-BR")
      : null;
    return (
      <div
        className={`flex flex-col items-center justify-center gap-0.5 bg-cartao px-1 text-center text-texto-3 ${className}`}
        title={`${media.nome} — ${motivo ?? "não consegui gerar a miniatura"}`}
      >
        <span aria-hidden>⊘</span>
        {quando && <span className="text-texto-2">{quando}</span>}
        <span className="line-clamp-2 leading-tight">
          {motivo ?? "sem miniatura"}
        </span>
      </div>
    );
  }

  return (
    <img
      src={api.thumbUrl(media.id)}
      alt={media.nome}
      loading="lazy"
      onError={() => setFalhou(true)}
      className={`object-cover ${className}`}
    />
  );
}
