import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// /api is proxied to the FastAPI backend during development so the app can
// use same-origin relative URLs everywhere. That means the exact same
// fetch() calls work unchanged in production, where api/main.py serves the
// built bundle itself from one origin — no environment-specific base URL,
// no CORS to think about outside this file.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
