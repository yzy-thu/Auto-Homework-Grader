import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      "/api/grade/stream": {
        target: "http://localhost:5001",
        changeOrigin: true,
        timeout: 0,        // no proxy timeout for SSE
        proxyTimeout: 0,   // no proxy timeout for SSE
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            // Ensure no buffering for SSE
            proxyRes.headers["Cache-Control"] = "no-cache";
            proxyRes.headers["X-Accel-Buffering"] = "no";
          });
        },
      },
      "/api": {
        target: "http://localhost:5001",
        changeOrigin: true,
      },
    },
  },
});
