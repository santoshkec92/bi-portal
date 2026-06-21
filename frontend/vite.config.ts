import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, the SPA runs on :5173 and proxies API calls to the FastAPI backend
// on :8000 (so cookies/session work on a single origin from the browser's POV).
// In prod, FastAPI serves the built assets from `backend/static` — no proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Emit the production build straight into the backend's static dir so the
    // single-container image can serve it.
    outDir: "../backend/static",
    emptyOutDir: true,
  },
});
