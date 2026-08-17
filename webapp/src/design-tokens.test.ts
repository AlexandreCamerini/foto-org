import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

// Resolvido de import.meta.url, não de process.cwd() — process.cwd() muda
// conforme quem invoca o vitest (raiz do repo vs. webapp/), import.meta.url
// não.
const srcDir = dirname(fileURLToPath(import.meta.url));

function listarArquivosTsx(dir: string): string[] {
  const resultado: string[] = [];
  for (const entrada of readdirSync(dir)) {
    const caminho = join(dir, entrada);
    const info = statSync(caminho);
    if (info.isDirectory()) {
      resultado.push(...listarArquivosTsx(caminho));
    } else if (entrada.endsWith(".tsx") && !caminho.includes(".test.")) {
      resultado.push(caminho);
    }
  }
  return resultado;
}

// Remove comentários de bloco (/* ... */) e de linha (// até o fim da linha)
// antes de procurar o peso proibido — sem isso, o próprio comentário que
// documenta a regra ("proibido usar font-medium aqui") derrubaria a regra.
// Comentários de bloco são substituídos preservando as quebras de linha
// internas, para que o número de linha reportado numa violação continue
// batendo com o arquivo original.
function removerComentarios(codigo: string): string {
  const semBloco = codigo.replace(/\/\*[\s\S]*?\*\//g, (bloco) =>
    bloco.replace(/[^\n]/g, ""),
  );
  return semBloco.replace(/\/\/.*$/gm, "");
}

describe("peso de ênfase", () => {
  it("index.css define --font-weight-titulo: 500", () => {
    const css = readFileSync(join(srcDir, "index.css"), "utf-8");
    expect(css).toContain("--font-weight-titulo: 500");
  });

  it("nenhum .tsx de produção usa font-semibold ou font-medium", () => {
    const arquivos = listarArquivosTsx(srcDir);
    const violacoes: string[] = [];

    for (const arquivo of arquivos) {
      const semComentarios = removerComentarios(readFileSync(arquivo, "utf-8"));
      semComentarios.split("\n").forEach((linha, i) => {
        if (/font-(semibold|medium)\b/.test(linha)) {
          violacoes.push(`${relative(srcDir, arquivo)}:${i + 1}`);
        }
      });
    }

    expect(
      violacoes,
      `font-semibold/font-medium sobrevivendo fora de comentário em: ${violacoes.join(", ") || "(nenhum)"} — use font-titulo`,
    ).toEqual([]);
  });

  it("pelo menos 17 call sites usam font-titulo (trava inferior contra apagar em vez de migrar)", () => {
    const arquivos = listarArquivosTsx(srcDir);
    let total = 0;

    for (const arquivo of arquivos) {
      const semComentarios = removerComentarios(readFileSync(arquivo, "utf-8"));
      const ocorrencias = semComentarios.match(/font-titulo\b/g);
      total += ocorrencias ? ocorrencias.length : 0;
    }

    expect(total).toBeGreaterThanOrEqual(17);
  });
});
