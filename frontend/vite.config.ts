import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/voltra/",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/voltra/api": "http://127.0.0.1:8086",
      "/api": "http://127.0.0.1:8086",
      "/health": "http://127.0.0.1:8086",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    assetsDir: "assets",
    emptyOutDir: true,
  },
});
