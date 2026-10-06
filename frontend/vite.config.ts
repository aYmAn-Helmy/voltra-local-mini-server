import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/voltra/",
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    assetsDir: "assets",
    emptyOutDir: true,
  },
});
