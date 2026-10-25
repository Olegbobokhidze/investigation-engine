import { env } from "@/shared/config/env";

/** An error response from the API, or a request that never reached it (`status` 0). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** The body the backend sends for every handled error (see `core/errors.py`). */
interface ErrorEnvelope {
  error: { code: string; message: string };
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== "object" || body === null || !("error" in body)) return false;
  const { error } = body;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

/**
 * Sends a request to the API and returns the parsed JSON body.
 * Throws `ApiError` for network failures and non-2xx responses.
 */
export async function apiRequest<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Can’t reach the server. Check your connection and try again.",
    );
  }

  const body: unknown =
    response.status === 204 ? undefined : await response.json().catch(() => null);

  if (!response.ok) {
    if (isErrorEnvelope(body)) {
      throw new ApiError(response.status, body.error.code, body.error.message);
    }
    throw new ApiError(
      response.status,
      "unexpected_error",
      `The server returned an unexpected error (${String(response.status)}).`,
    );
  }

  return body as TResponse;
}

/** Request options for a JSON body. */
export function jsonBody(data: unknown): Pick<RequestInit, "body" | "headers"> {
  return {
    body: JSON.stringify(data),
    headers: { "Content-Type": "application/json" },
  };
}
