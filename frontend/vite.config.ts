import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  // Load from current frontend dir, root dir, and backend dir
  const envFrontend = loadEnv(mode, process.cwd(), "");
  const envRoot = loadEnv(mode, path.resolve(process.cwd(), ".."), "");
  const envBackend = loadEnv(mode, path.resolve(process.cwd(), "../backend"), "");

  const env = { ...envRoot, ...envBackend, ...envFrontend, ...process.env };
  const backendUrl = env.BACKEND_URL || env.VITE_BACKEND_URL || "http://127.0.0.1:8000";
  const rawSecret = env.VITE_SECRET_KEY || env.SECRET_KEY || "dev-secret-key";
  const secretKey = rawSecret.replace(/^['"]|['"]$/g, "").trim();

  return {
    plugins: [react()],
    define: {
      "import.meta.env.VITE_SECRET_KEY": JSON.stringify(secretKey),
      "import.meta.env.VITE_BACKEND_URL": JSON.stringify(backendUrl),
    },
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  };
});
