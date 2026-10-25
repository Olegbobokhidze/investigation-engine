/** Typed access to build-time environment variables (see `.env.example`). */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  apiMocking: import.meta.env.VITE_API_MOCKING === "enabled",
} as const;
