import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "@/styles/index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import { env } from "@/shared/config/env";

/** Starts the mock API when enabled; the import keeps mock code out of real builds. */
async function enableApiMocking(): Promise<void> {
  if (!env.apiMocking) return;
  const { worker } = await import("@/mocks/browser");
  await worker.start({ onUnhandledFrame: "bypass" });
}

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element #root is missing from index.html");

void enableApiMocking().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
