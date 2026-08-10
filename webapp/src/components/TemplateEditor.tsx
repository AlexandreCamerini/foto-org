import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

const CHAVE_TEMPLATE = ["configuracoes", "template"] as const;

/** Únicos placeholders que `render_destino` entende hoje
 * (`fotoorganizer/classification/templates.py`, espelhado em
 * `PLACEHOLDERS_TEMPLATE_VALIDOS` no server) — lista fixa nesta fase, não
 * inventar placeholder novo aqui sem mudar o motor primeiro. */
const PLACEHOLDERS_VALIDOS = [
  "categoria",
  "ano",
  "viagem",
  "evento",
  "pais",
  "regiao",
  "cidade",
] as const;

const ATRASO_DEBOUNCE_MS = 350;

/** Editor do template que decide em que pasta cada foto cai ao criar um
 * plano. Vive dentro de Operações — é a única tela sobre "como o destino é
 * decidido no disco" — fechado por padrão para não brigar com a lista de
 * planos ao lado; o rótulo mostra o template atual sem precisar abrir.
 *
 * Salvar (PUT) e regenerar sugestões (POST /api/sugestoes/gerar) são ações
 * distintas de propósito: trocar o texto não pode disparar um job pesado a
 * cada tecla, e "regenerar" só fica liberado quando a tela mostra
 * exatamente o que está salvo no servidor — nada de recriar sugestões a
 * partir de um rascunho que o usuário ainda não confirmou. */
export default function TemplateEditor({ job }: { job: Job }) {
  const [aberto, setAberto] = useState(false);
  const [edicao, setEdicao] = useState<string | null>(null);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [erroRegenerar, setErroRegenerar] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: atual } = useQuery({
    queryKey: CHAVE_TEMPLATE,
    queryFn: api.template,
  });

  const valorServidor = atual?.template ?? "";
  // null = tela mostra o que está salvo; string = rascunho não salvo ainda.
  const valor = edicao ?? valorServidor;
  const semEdicaoPendente = edicao === null;

  // O preview segue o campo, mas só busca depois de uma pausa — sem isso
  // cada tecla vira uma requisição.
  const [debounced, setDebounced] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(valor), ATRASO_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [valor]);

  const preview = useQuery({
    queryKey: [...CHAVE_TEMPLATE, "preview", debounced],
    queryFn: () => api.previewTemplate(debounced),
    enabled: debounced.trim() !== "",
  });

  const salvar = useMutation({
    mutationFn: (t: string) => api.salvarTemplate(t),
    onSuccess: (dados) => {
      setErroSalvar(null);
      setEdicao(null);
      queryClient.setQueryData(CHAVE_TEMPLATE, dados);
    },
    onError: (e: Error) => setErroSalvar(e.message),
  });

  function regenerar() {
    setErroRegenerar(null);
    job.gerarSugestoes().catch((e: Error) => setErroRegenerar(e.message));
  }

  return (
    <div className="border-b border-borda">
      <button
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="titulo-painel flex w-full items-center gap-1.5 px-3 py-2 hover:text-texto"
      >
        <span className="w-2 shrink-0">{aberto ? "▾" : "▸"}</span>
        <span className="shrink-0">Template do destino</span>
        {!aberto && valorServidor && (
          <span className="min-w-0 truncate normal-case text-texto-3">
            — {valorServidor}
          </span>
        )}
      </button>

      {aberto && (
        <div className="px-3 pb-3">
          <p className="mb-2 max-w-2xl text-texto-2">
            Decide em que pasta cada foto cai a partir do próximo plano.
            Placeholder vazio some da linha; quando <code>{"{viagem}"}</code>{" "}
            ou <code>{"{evento}"}</code> está preenchido na sugestão real,{" "}
            <code>{"{pais}"}</code>, <code>{"{regiao}"}</code> e{" "}
            <code>{"{cidade}"}</code> saem vazios — os dois exemplos abaixo
            mostram os dois casos.
          </p>

          <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-texto-3">
            {PLACEHOLDERS_VALIDOS.map((p) => (
              <code key={p}>{`{${p}}`}</code>
            ))}
          </div>

          <input
            aria-label="Template do destino"
            value={valor}
            onChange={(e) => {
              setEdicao(e.target.value);
              setErroSalvar(null);
            }}
            className="mb-2 w-full max-w-2xl rounded-md border border-borda bg-cartao px-2.5 py-1 font-mono outline-none focus:border-acento"
          />

          <div className="mb-3 flex items-center gap-2">
            <Botao
              onClick={() => salvar.mutate(valor)}
              disabled={salvar.isPending || valor.trim() === ""}
            >
              {salvar.isPending ? "Salvando…" : "Salvar"}
            </Botao>
            {erroSalvar && <span className="text-erro">{erroSalvar}</span>}
          </div>

          <div className="mb-3 max-w-2xl space-y-1.5">
            {(preview.data?.exemplos ?? []).map((ex) => (
              <div key={ex.rotulo}>
                <div className="text-texto-3">{ex.rotulo}</div>
                <div className="truncate font-medium">{ex.destino || "—"}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-borda pt-2">
            <Botao
              onClick={regenerar}
              disabled={!semEdicaoPendente || job.rodando}
              title={
                semEdicaoPendente
                  ? "Recria as sugestões pendentes com este template"
                  : "Salve o template antes de regenerar"
              }
              className="whitespace-nowrap"
            >
              Regenerar sugestões pendentes
            </Botao>
            <span className="text-texto-3">
              Só sugestões pendentes são recriadas — aprovadas, rejeitadas ou
              com destino editado à mão não mudam.
            </span>
            {erroRegenerar && (
              <span className="text-erro">{erroRegenerar}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
