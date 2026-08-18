import { useState } from "react";

import Botao from "../ui/Botao";

/** Modal simples de caminho — compartilhado entre os quatro pontos de
 * entrada que disparam "adicionar pasta" (Sidebar + os três estados vazios,
 * CONS-05/D-07) e o fluxo de importação de Google Takeout, que reusa o
 * mesmo mecanismo com outro título. Antes vivia inteiro dentro de
 * `Sidebar.tsx`, com estado privado — inalcançável por irmãos e inexistente
 * na aba Panorama, onde a `Sidebar` nem está montada. */
export default function ModalCaminho({
  titulo,
  onConfirmar,
  onCancelar,
  erro,
}: {
  titulo: string;
  onConfirmar: (caminho: string) => void;
  onCancelar: () => void;
  /** Mensagem de erro do servidor (ex.: falha do POST /api/scan). Quando
   * presente, aparece acima dos botões e o modal permanece aberto — quem
   * chamou decide, não fechar sozinho, é o que evita engolir a falha. */
  erro?: string | null;
}) {
  const [valor, setValor] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95">
      <div className="w-96 rounded-md border border-borda bg-painel p-4">
        <div className="mb-2 font-titulo">{titulo}</div>
        <input
          autoFocus
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && valor.trim()) onConfirmar(valor.trim());
            if (e.key === "Escape") onCancelar();
          }}
          placeholder="/Users/voce/Pictures/Viagens"
          className="mb-3 w-full rounded-md border border-borda bg-cartao px-3 py-2 outline-none placeholder:text-texto-3 focus:border-acento"
        />
        {erro && <div className="mb-3 text-erro">{erro}</div>}
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma"
            onClick={onCancelar}>
            Cancelar
          </Botao>
          <Botao variante="solido"
            onClick={() => valor.trim() && onConfirmar(valor.trim())}>
            Confirmar
          </Botao>
        </div>
      </div>
    </div>
  );
}
