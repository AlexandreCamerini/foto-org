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
