import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Em dev o Vite roda em :5173 e proxeia /api para o servidor local do
// Foto Organizer; em produção o FastAPI serve o dist/ diretamente.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
});
