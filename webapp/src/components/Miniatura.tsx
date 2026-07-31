import { useState } from "react";

import { api, type Media } from "../api";

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
}: {
  media: Media;
  className?: string;
}) {
  const [falhou, setFalhou] = useState(false);
  const motivo = media.motivo_indisponivel;

  if (motivo || falhou) {
    return (
      <div
        className={`flex flex-col items-center justify-center gap-1 bg-cartao px-1 text-center text-texto-3 ${className}`}
        title={motivo ?? "não consegui gerar a miniatura"}
      >
        <span aria-hidden className="text-texto-3">⊘</span>
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
