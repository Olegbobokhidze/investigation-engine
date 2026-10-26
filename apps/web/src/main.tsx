import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "@/styles/index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import { env } from "@/shared/config/env";

/** Starts the mock API when enabled; mock code is a separate chunk loaded only then. */
async function enableApiMocking(): Promise<void> {
  if (env.apiMocking === "none") return;
  const { createWorker } = await import("@/mocks/browser");
  await createWorker(env.apiMocking).start({ onUnhandledFrame: "bypass" });
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
