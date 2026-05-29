import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const host = process.env.TAURI_DEV_HOST;
// VITE_API_HOST lets you dev against a remote backend (e.g. the Mac Mini).
// Usage:  VITE_API_HOST=http://192.168.1.8:8765 npm run dev
const apiHost = process.env.VITE_API_HOST || "http://127.0.0.1:8765";

export default defineConfig(async () => ({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  clearScreen: false,
  server: {
    port: 3000,
    strictPort: true,
    host: host || false,
    hmr: host ? { protocol: "ws", host, port: 1421 } : undefined,
    watch: { ignored: ["**/src-tauri/**"] },
    // Never cache index.html — JS/CSS assets use content hashes so they
    // are safe to cache aggressively, but index.html must always be fresh.
    headers: {
      "Cache-Control": "no-store",
    },
    proxy: {
      "/api": {
        target: apiHost,
        changeOrigin: true,
      },
      "/uploads": {
        target: apiHost,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash].[ext]",
      },
    },
  },
}));
