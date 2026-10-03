/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiTarget = process.env.API_TARGET ?? "http://localhost:8000";
// The pages themselves (docs/10 §4): never framed, never sniffed, and no referrer, so a share link's token in
// /s/... is not sent to another site. The API adds the same headers to its own responses.
const headers = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/v1": { target: apiTarget, changeOrigin: false } },
    watch: { usePolling: true, interval: 300 }, // bind mounts from Windows don't deliver file events
    headers,
  },
  preview: { headers },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    testTimeout: 20_000,
  },
});
