import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/shared/api/client";

const maxQueryRetries = 2;

/** Client errors (4xx) won't succeed on a retry; network and server errors might. */
function shouldRetry(failureCount: number, error: Error): boolean {
  const isClientError = error instanceof ApiError && error.status >= 400 && error.status < 500;
  return !isClientError && failureCount < maxQueryRetries;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: shouldRetry,
    },
    mutations: {
      retry: false,
    },
  },
});
