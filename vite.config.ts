import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { defineConfig } from "vite";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "./",
  build: {
    outDir: resolve(rootDir, "assets"),
    assetsDir: ".",
    emptyOutDir: false,
    manifest: "vite-manifest.json",
    target: "baseline-widely-available",
    sourcemap: false,
    rolldownOptions: {
      input: resolve(rootDir, "frontend/src/app.ts"),
      output: {
        entryFileNames: "travel-app.js",
        chunkFileNames: "travel-chunk-[hash].js",
        assetFileNames: "travel-app.[ext]"
      }
    }
  }
});
