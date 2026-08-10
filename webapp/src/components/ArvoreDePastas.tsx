import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import Botao from "../ui/Botao";

/** A árvore de pastas do disco, um nível por vez.
 *
 * Existe porque este acervo responde melhor a "onde isso estava?" do que a
 * "quando isso foi tirado?". São 225.914 registros num volume que não está
 * montado: para eles a pasta de origem é a única pista de lugar que sobrou —
 * e é ela que o catálogo do Lightroom guarda mesmo com o disco na gaveta.
 *
 * Um nível por chamada, não a árvore inteira. Com 371 mil registros são
 * dezenas de milhares de pastas, e mandar tudo de uma vez para o navegador
 * montar a árvore seria repetir na rede o erro que a grade virtualizada
 * existe para evitar.
 */

const formatar = (n: number) => n.toLocaleString("pt-BR");

interface Props {
  /** Pasta selecionada hoje, ou `null` para "sem recorte de pasta". */
  pastaAtual: string | null;
  onSelecionar: (pasta: string | null) => void;
}

export default function ArvoreDePastas({ pastaAtual, onSelecionar }: Props) {
  // O caminho que está sendo NAVEGADO não é o mesmo que está FILTRANDO: dá
  // para descer na árvore olhando sem trocar o recorte da grade a cada passo.
  const [aberta, setAberta] = useState<string | null>(pastaAtual);
  const { data, isLoading } = useQuery({
    queryKey: ["pastas", aberta],
    queryFn: () => api.pastas(aberta ?? undefined),
  });

  const partes = (aberta ?? "").split("/").filter(Boolean);

  return (
    <div data-testid="arvore-de-pastas" className="flex min-h-0 flex-col">
      <div className="titulo-painel px-3 pb-1 pt-3">Pastas</div>

      {/* Trilha de volta. Sem ela, descer três níveis é um caminho sem
          retorno — e a árvore vira um labirinto em vez de um mapa. */}
      <div className="flex flex-wrap items-center gap-0.5 px-3 pb-1">
        <Botao
          variante="fantasma"
          tamanho="sm"
          className="px-1"
          onClick={() => setAberta(null)}
          title="Voltar à raiz"
        >
          todos os discos
        </Botao>
        {partes.map((parte, i) => (
          <span key={parte + i} className="flex items-center gap-0.5">
            <span aria-hidden className="text-texto-3">
              /
            </span>
            <Botao
              variante="fantasma"
              tamanho="sm"
              className="max-w-28 truncate px-1"
              onClick={() => setAberta("/" + partes.slice(0, i + 1).join("/"))}
              title={"/" + partes.slice(0, i + 1).join("/")}
            >
              {parte}
            </Botao>
          </span>
        ))}
      </div>

      {aberta && (
        <div className="px-3 pb-1">
          <Botao
            tamanho="sm"
            cheio
            onClick={() =>
              onSelecionar(pastaAtual === aberta ? null : aberta)
            }
            className={
              pastaAtual === aberta ? "border-acento text-acento" : ""
            }
            title={
              pastaAtual === aberta
                ? "Remover o recorte desta pasta"
                : "Mostrar na grade só o que está aqui e abaixo"
            }
          >
            {pastaAtual === aberta ? "recorte ativo ✕" : "ver na grade"}
          </Botao>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading && <p className="px-3 py-2 text-texto-3">carregando…</p>}

        {!isLoading && data && data.filhos.length === 0 && (
          <p className="px-3 py-2 text-texto-3">
            {data.aqui > 0
              ? "só arquivos aqui, sem subpastas"
              : "nada nesta pasta"}
          </p>
        )}

        {(data?.filhos ?? []).map((filho) => (
          <button
            key={filho.caminho}
            onClick={() => setAberta(filho.caminho)}
            title={`${filho.caminho} — ${formatar(filho.total)} registros`}
            className={`block w-full px-3 py-1.5 text-left hover:bg-cartao ${
              pastaAtual === filho.caminho
                ? "border-l-2 border-acento bg-cartao"
                : ""
            }`}
          >
            <div className="flex items-baseline gap-1.5">
              <span aria-hidden className="text-texto-3">
                ▸
              </span>
              <span className="min-w-0 flex-1 truncate">{filho.nome}</span>
              <span className="shrink-0 text-texto-2">
                {formatar(filho.total)}
              </span>
            </div>
            {/* Quantas dá para abrir agora. Numa pasta de volume desmontado
                isso é zero, e o zero é a resposta — não um erro. */}
            {filho.alcancaveis < filho.total && (
              <div className="text-micro text-texto-3">
                {filho.alcancaveis === 0
                  ? "nenhuma alcançável agora"
                  : `${formatar(filho.alcancaveis)} alcançáveis`}
              </div>
            )}
          </button>
        ))}

        {data && data.aqui > 0 && (
          <p className="px-3 py-1.5 text-texto-3">
            + {formatar(data.aqui)} solta{data.aqui > 1 ? "s" : ""} nesta pasta
          </p>
        )}
      </div>
    </div>
  );
}
