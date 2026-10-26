/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

/**
 * A production bundle that talks to the real API needs its URL: without it the app would
 * silently fall back to localhost, which only works on the developer's machine.
 */
function assertApiConfigured(mode: string): void {
  const viteEnv = loadEnv(mode, process.cwd(), "VITE_");
  if (viteEnv.VITE_API_MOCKING === "enabled" || viteEnv.VITE_API_BASE_URL) return;
  throw new Error(
    "Production build needs VITE_API_BASE_URL, or VITE_API_MOCKING=enabled to run on mock data.",
  );
}

export default defineConfig(({ command, mode }) => {
  if (command === "build" && mode === "production") assertApiConfigured(mode);

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
