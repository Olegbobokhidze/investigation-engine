/** Which API calls the browser answers with mock data instead of the backend. */
export type ApiMocking = "all" | "investigations" | "none";

function parseApiMocking(value: string | undefined): ApiMocking {
  if (value === "enabled") return "all";
  if (value === "investigations") return "investigations";
  return "none";
}

/** Typed access to build-time environment variables (see `.env.example`). */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  apiMocking: parseApiMocking(import.meta.env.VITE_API_MOCKING),
} as const;
