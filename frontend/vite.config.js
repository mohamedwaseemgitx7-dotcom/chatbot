import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      // In dev, "/api/*" is forwarded to FastAPI, so the browser never makes a cross-origin call.
      proxy: {
        "/api": { target: env.BACKEND_PROXY_TARGET || "http://127.0.0.1:8000", changeOrigin: true },
      },
    },
  };
});
