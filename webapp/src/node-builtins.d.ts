// Declarações ambiente mínimas para os built-ins do Node usados por testes
// puros (ex.: webapp/src/design-tokens.test.ts) que leem arquivos do próprio
// repositório em tempo de teste.
//
// Não instala `@types/node`: o projeto webapp não depende de Node em
// runtime (só browser), e a Task 3 do plano 04-01 é explícita em não
// adicionar dependência nova para este teste. Sem esta declaração, `tsc -b`
// (rodado por `npm run build`) falha com "Cannot find module 'node:fs'"
// porque `moduleResolution: bundler` não conhece módulos `node:*` sem tipos
// — vitest roda o arquivo via esbuild, que não checa tipos, então só o
// build sente falta disto. Cobre exatamente as funções usadas hoje; ampliar
// conforme necessário, não copiar o `@types/node` inteiro aqui.
declare module "node:fs" {
  export function readFileSync(path: string, encoding: string): string;
  export function readdirSync(path: string): string[];
  export function statSync(path: string): { isDirectory(): boolean };
}

declare module "node:path" {
  export function dirname(path: string): string;
  export function join(...segments: string[]): string;
  export function relative(from: string, to: string): string;
}

declare module "node:url" {
  export function fileURLToPath(url: string | URL): string;
}
