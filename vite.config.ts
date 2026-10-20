import { fileURLToPath } from "node:url";
import { readdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const outDir = resolve(rootDir, "site/assets");

// site/assets 同时存放图片库，不能清空整个目录；只清理上一次构建留下的按需加载分块。
function removeStaleChunks(): Plugin {
  return {
    name: "remove-stale-travel-chunks",
    apply: "build",
    buildStart() {
      for (const name of readdirSync(outDir)) {
        if (/^travel-chunk-.+\.js$/.test(name)) rmSync(resolve(outDir, name));
      }
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [removeStaleChunks()],
  build: {
    outDir,
    assetsDir: ".",
    emptyOutDir: false,
    // 分块之间依赖很少，不需要预加载助手；保持入口脚本在 10 KB 预算内。
    modulePreload: false,
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
