import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
// defineConfig do vitest aceita a chave `test` além da config do Vite; o do
// "vite" não, e o tsc reclama.
import { defineConfig } from "vitest/config";

// Em dev o Vite roda em :5173 e proxeia /api para o servidor local do
// Foto Organizer; em produção o FastAPI serve o dist/ diretamente.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
  },
});
