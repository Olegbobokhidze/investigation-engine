import { setupWorker } from "msw/browser";

import type { ApiMocking } from "@/shared/config/env";

import { documentHandlers, investigationHandlers } from "./handlers";

/** A service worker that answers the mocked part of the API; other requests go to the network. */
export function createWorker(mocking: Exclude<ApiMocking, "none">) {
  const handlers =
    mocking === "all" ? [...documentHandlers, ...investigationHandlers] : investigationHandlers;
  return setupWorker(...handlers);
}
