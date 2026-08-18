import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import type {
  CampoExif,
  ItemPlanoExif,
  PlanoExif,
  RelatorioDryRunExif,
} from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

const ROTULO_CAMPO: Record<"gps" | "cidade" | "pais", string> = {
  gps: "GPS",
  cidade: "Cidade",
  pais: "País",
};

/** Texto do chip "pulado" — concordância de gênero por campo, mesmo texto
 *  do exemplo travado na UI-SPEC ("Cidade já preenchida"). */
const JA_PREENCHIDO: Record<"gps" | "cidade" | "pais", string> = {
  gps: "GPS já preenchido",
  cidade: "Cidade já preenchida",
  pais: "País já preenchido",
};

function formatarValorCampo(
  chave: "gps" | "cidade" | "pais",
  valor: CampoExif["valor"],
): string {
  if (chave === "gps" && Array.isArray(valor)) {
    return `GPS ${valor[0].toFixed(4)}, ${valor[1].toFixed(4)}`;
  }
  return `${ROTULO_CAMPO[chave]} ${valor ?? ""}`;
}

/** Um dos três chips de campo de uma linha tipo A/C (ou de uma linha tipo B
 *  rumo ao sidecar — `sufixo` marca isso, ex. " → .xmp"). O `switch` sobre
 *  `StatusCampoExif` é exaustivo de propósito: `gravado`/`falha` só passam
 *  a existir de fato quando a gravação roda de verdade (plano 06-08,
 *  próxima tarefa), mas cair aqui já hoje garante que o TypeScript acusa
 *  quando aquele tratamento esquecer um caso. */
function ChipCampo({
  chave,
  campo,
  sufixo = "",
}: {
  chave: "gps" | "cidade" | "pais";
  campo: CampoExif;
  sufixo?: string;
}) {
  const rotulo = ROTULO_CAMPO[chave];
  switch (campo.status) {
    case "pronto":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-2"
          title={campo.motivo ?? undefined}
        >
          {formatarValorCampo(chave, campo.valor)}
          {sufixo}
        </span>
      );
    case "pulado":
      // Comportamento esperado, não erro: mesmo token de "pulado" usado em
      // toda a tela — nunca a cor reservada a erro.
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-2"
          title={campo.motivo ?? undefined}
        >
          {JA_PREENCHIDO[chave]}
          {sufixo}
        </span>
      );
    case "sem_valor":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-3"
          title={campo.motivo ?? undefined}
        >
          {rotulo} —{sufixo}
        </span>
      );
    case "pendente":
    case "gravado":
    case "falha":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-3"
          title={campo.motivo ?? undefined}
        >
          {rotulo}
          {sufixo}
        </span>
      );
  }
}

/** Motivo exato travado na UI-SPEC (Copywriting Contract, "Sync-folder
 *  warning" tooltip) — aviso, nunca bloqueio (D-07). */
const AVISO_PASTA_SINCRONIZADA =
  "O app de sincronização pode sobrescrever este arquivo com a versão antiga ou gerar conflito silencioso. Você decide incluir ou não.";

/** Linha tipo B (EXIF-05/D-05): badge do motivo de formato não suportado,
 *  motivo sempre visível como texto (não só no `title` — D-05). */
function BadgeFormato({ item }: { item: ItemPlanoExif }) {
  return (
    <span
      className="rounded-full border border-atencao/40 bg-atencao/10 px-2 py-0.5 text-[11px] text-atencao"
      title={item.motivo_nao_suportado ?? undefined}
    >
      ⚠ Formato não suportado — {item.motivo_nao_suportado}
    </span>
  );
}

/** Badge 2 da linha tipo B (D-06): sinal redundante de que esta linha NÃO
 *  escreve no original — sempre junto do badge de formato, nunca sozinho. */
function BadgeSidecar({ item }: { item: ItemPlanoExif }) {
  return (
    <span
      className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-herdado"
      title={item.sidecar_destino ?? undefined}
    >
      ⇢ sidecar .xmp
    </span>
  );
}

/** Linha tipo C (D-07): aviso aditivo, a linha continua marcada por
 *  padrão — nunca bloqueio. */
function BadgeSync({ item }: { item: ItemPlanoExif }) {
  return (
    <span
      className="rounded-full border border-atencao/40 bg-atencao/10 px-2 py-0.5 text-[11px] text-atencao"
      title={AVISO_PASTA_SINCRONIZADA}
    >
      ☁ Pasta sincronizada — {item.pasta_sincronizada}
    </span>
  );
}

/** O que o dry-run concluiu — a frase que decide se dá para gravar.
 *  Mesma forma de `Operations.tsx::veredito`, verbo trocado para "gravar". */
function veredito(p: PlanoExif): string {
  if (p.dry_run_em === null) return "sem dry-run — nada pode ser gravado ainda";
  const quando = new Date(p.dry_run_em).toLocaleString();
  if (p.prontos === null) return `dry-run em ${quando}`;
  if (p.prontos === 0)
    return `dry-run ${quando}: nenhum arquivo a gravar (${p.problemas} problemas)`;
  if (p.problemas)
    return `dry-run ${quando}: ${p.prontos} prontos, ${p.problemas} com problema`;
  return `dry-run ${quando}: ${p.prontos} prontos, sem problemas`;
}

/** Escrita EXIF de localização: plano → dry-run → gravação, sempre
 *  in-place — não há para onde copiar, é o próprio arquivo original que
 *  ganha o campo vazio (D-075). Segunda tela do app que escreve fora do
 *  catálogo, no mesmo molde de `Operations.tsx`: cada passo explícito, e
 *  gravar fica bloqueado até o dry-run aprovar. */
export default function EscritaExif({ job }: { job: Job }) {
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [relatorio, setRelatorio] = useState<RelatorioDryRunExif | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  // Ids marcados para entrar na próxima execução (D-01/D-02): o dono aprova
  // o lote inteiro de uma vez e desmarca linhas pontuais. Semeado a partir
  // do servidor (useEffect abaixo), nunca de "todos marcados" — o backend
  // já decidiu o default por tipo de linha (tipo B nasce desmarcado, D-06 é
  // opt-in), e duplicar essa regra no cliente criaria duas verdades.
  const [marcados, setMarcados] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();

  const { data: planos } = useQuery({
    queryKey: ["planosExif"],
    queryFn: api.planosExif,
  });
  const { data: plano } = useQuery({
    queryKey: ["planoExif", selecionado],
    queryFn: () => api.planoExif(selecionado as number),
    enabled: selecionado !== null,
  });
  const { data: auditoria } = useQuery({
    queryKey: ["auditoriaExif", selecionado],
    queryFn: () => api.auditoriaExif(selecionado as number),
    enabled: selecionado !== null,
  });

  // Relatório é sempre do plano em tela — trocar de plano zera a evidência.
  useEffect(() => setRelatorio(null), [selecionado]);

  // Semeia a seleção a partir do plano sempre que o detalhe muda (troca de
  // plano, dry-run recarregando, execução recarregando). Não reage a
  // toggles locais do dono: o `Set` só é substituído quando `plano` (a
  // referência do react-query) muda.
  useEffect(() => {
    if (plano) {
      setMarcados(new Set(plano.itens.filter((i) => i.incluido).map((i) => i.id)));
    }
  }, [plano]);

  const criar = useMutation({
    mutationFn: () => api.criarPlanoExif(),
    onSuccess: (novo) => {
      setErro(null);
      setSelecionado(novo.id);
      void queryClient.invalidateQueries({ queryKey: ["planosExif"] });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const dryRun = useMutation({
    mutationFn: () => api.dryRunExif(selecionado as number),
    onSuccess: (r) => {
      setErro(null);
      setRelatorio(r);
      // O dry-run carimba o plano e escreve na auditoria — as duas
      // precisam recarregar, senão a trilha exibida fica mentindo.
      void queryClient.invalidateQueries({ queryKey: ["planoExif", selecionado] });
      void queryClient.invalidateQueries({
        queryKey: ["auditoriaExif", selecionado],
      });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const executando = job.rodando && job.estado.tipo === "escrita_exif";
  // Ter rodado o dry-run não basta: precisa ter aprovado algo gravável E
  // ter ao menos uma linha marcada (D-02) — desmarcar tudo desabilita a CTA.
  const podeGravar =
    plano != null && plano.executavel && marcados.size > 0 && !job.rodando;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        <Botao onClick={() => criar.mutate()} disabled={criar.isPending}>
          Criar plano de escrita
        </Botao>
        {erro && <span className="text-erro">{erro}</span>}
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-borda">
          {(planos ?? []).length === 0 ? (
            <div className="flex flex-col gap-2 p-3">
              <div className="font-titulo">Nada para gravar</div>
              <p className="text-texto-2">
                Todo arquivo catalogado já tem GPS, cidade e país
                preenchidos, ou nenhuma sugestão de localização foi gerada
                ainda. Gere sugestões em Revisão e aprove-as antes de criar
                um plano aqui.
              </p>
            </div>
          ) : (
            (planos ?? []).map((p) => (
              <button
                key={p.id}
                onClick={() => setSelecionado(p.id)}
                className={`block w-full border-b border-borda px-3 py-2 text-left hover:bg-painel ${
                  selecionado === p.id ? "bg-cartao" : ""
                }`}
              >
                <div className="truncate">{p.nome}</div>
                <div className="text-texto-2">
                  {p.status} · {p.gravados}/{p.total_itens} gravados
                  {p.com_erro > 0 && (
                    <span className="text-erro"> · {p.com_erro} erros</span>
                  )}
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          {plano == null ? (
            <div className="flex flex-1 items-center justify-center text-texto-2">
              Escolha um plano para ver o que será gravado.
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                <Botao
                  onClick={() => dryRun.mutate()}
                  disabled={dryRun.isPending || job.rodando}
                  className="whitespace-nowrap"
                >
                  {dryRun.isPending ? "Simulando…" : "Rodar dry-run"}
                </Botao>
                <Botao
                  variante="solido"
                  onClick={() =>
                    // A seleção real do dono (D-01/D-02) — nunca `null`,
                    // mesmo quando tudo está marcado, para o servidor
                    // persistir exatamente o que a tela mostrava.
                    job
                      .executarEscritaExif(plano.id, Array.from(marcados))
                      .catch((e: Error) => setErro(e.message))
                  }
                  disabled={!podeGravar}
                  title={
                    plano.dry_run_em === null
                      ? "Rode o dry-run antes de gravar"
                      : !plano.executavel
                        ? "O dry-run não encontrou nenhum campo gravável"
                        : marcados.size === 0
                          ? "Nenhum arquivo marcado para gravar"
                          : "Grava os campos vazios no arquivo original"
                  }
                  className="whitespace-nowrap"
                >
                  Gravar {marcados.size} arquivos
                </Botao>
                {executando && (
                  <Botao
                    variante="fantasma"
                    onClick={() => job.cancelar()}
                    className="hover:text-erro"
                  >
                    Cancelar
                  </Botao>
                )}
                <div className="flex-1" />
                <span
                  className={
                    plano.dry_run_em && !plano.executavel
                      ? "text-erro"
                      : "text-texto-2"
                  }
                >
                  {veredito(plano)}
                </span>
              </div>

              {executando && (
                <div className="border-b border-borda px-3 py-1.5 text-texto-2">
                  Gravando {job.estado.processados ?? 0} de{" "}
                  {job.estado.vistos ?? plano.total_itens} — o original só
                  muda campo por campo, com verificação antes de seguir.
                </div>
              )}

              {relatorio && (
                <div className="border-b border-borda bg-painel px-3 py-2">
                  <div>
                    {relatorio.prontos} prontos · {relatorio.campos_a_gravar}{" "}
                    campos a gravar
                    {relatorio.sidecars > 0 && (
                      <> · {relatorio.sidecars} sidecars</>
                    )}
                  </div>
                  {relatorio.problemas.map((p) => (
                    <div key={p} className="text-texto-2">
                      ! {p}
                    </div>
                  ))}
                </div>
              )}

              <div className="min-h-0 flex-1 overflow-y-auto">
                {plano.itens.map((item) => {
                  // Tipo B (EXIF-05/D-05/D-06): sem caminho de escrita
                  // direto — o checkbox controla o sidecar .xmp, não o
                  // arquivo original.
                  const ehTipoB = !item.formato_suportado;
                  // Tipo C (D-07): aviso aditivo, não muda a semântica do
                  // checkbox (a não ser que a linha também seja tipo B).
                  const ehTipoC = item.pasta_sincronizada !== null;
                  // Uma linha pode ser B e C ao mesmo tempo (arquivo não
                  // suportado dentro de pasta sincronizada) — os dois
                  // badges renderizam lado a lado, e a semântica do
                  // checkbox segue a de B (sidecar), nunca a de C.
                  const rotuloCheckbox = ehTipoB
                    ? "Gravar sidecar .xmp para este arquivo"
                    : `Gravar localização em ${item.nome}`;

                  return (
                    <div
                      key={item.id}
                      className={`border-b border-borda px-3 py-1.5 ${
                        ehTipoB ? "bg-atencao/5" : ""
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 shrink-0 rounded-sm border-borda-forte accent-acento"
                          checked={marcados.has(item.id)}
                          onChange={() =>
                            setMarcados((atual) => {
                              const novo = new Set(atual);
                              if (novo.has(item.id)) novo.delete(item.id);
                              else novo.add(item.id);
                              return novo;
                            })
                          }
                          aria-label={rotuloCheckbox}
                        />
                        <span className="min-w-0 flex-1 truncate font-titulo">
                          {item.nome}
                        </span>
                        {(ehTipoB || ehTipoC) && (
                          <div className="flex shrink-0 gap-1.5">
                            {ehTipoB && <BadgeFormato item={item} />}
                            {ehTipoB && <BadgeSidecar item={item} />}
                            {ehTipoC && <BadgeSync item={item} />}
                          </div>
                        )}
                        {!ehTipoB && (
                          <div className="flex shrink-0 gap-3">
                            <ChipCampo chave="gps" campo={item.campos.gps} />
                            <ChipCampo
                              chave="cidade"
                              campo={item.campos.cidade}
                            />
                            <ChipCampo chave="pais" campo={item.campos.pais} />
                          </div>
                        )}
                      </div>

                      {ehTipoB && (
                        <div className="flex items-center gap-3 pl-7 pt-1">
                          <span className="text-[11px] text-texto-2">
                            Gravar sidecar .xmp para este arquivo
                          </span>
                          <div className="flex shrink-0 gap-3">
                            <ChipCampo
                              chave="gps"
                              campo={item.campos.gps}
                              sufixo=" → .xmp"
                            />
                            <ChipCampo
                              chave="cidade"
                              campo={item.campos.cidade}
                              sufixo=" → .xmp"
                            />
                            <ChipCampo
                              chave="pais"
                              campo={item.campos.pais}
                              sufixo=" → .xmp"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {auditoria && auditoria.length > 0 && (
                <details className="border-t border-borda">
                  <summary className="cursor-pointer px-3 py-1.5 text-texto-2">
                    Auditoria ({auditoria.length} registros)
                  </summary>
                  <div className="max-h-48 overflow-y-auto px-3 pb-2">
                    {auditoria.map((linha) => (
                      <div key={linha.id} className="text-texto-2">
                        {new Date(linha.quando).toLocaleTimeString()} ·{" "}
                        {linha.acao} · {linha.resultado}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
