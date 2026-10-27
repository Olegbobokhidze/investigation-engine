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

/** Whether a parsed JSON value is the backend's error envelope. */
export function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
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

/** Sends a request; a failure to reach the server becomes an `ApiError` with status 0. */
async function send(path: string, init: RequestInit | undefined, accept: string) {
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", accept);
  try {
    return await fetch(`${env.apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Can’t reach the server. Check your connection and try again.",
    );
  }
}

/** The `ApiError` for a non-2xx response, from its error envelope when it has one. */
function errorFrom(response: Response, body: unknown): ApiError {
  if (isErrorEnvelope(body)) {
    return new ApiError(response.status, body.error.code, body.error.message);
  }
  return new ApiError(
    response.status,
    "unexpected_error",
    `The server returned an unexpected error (${String(response.status)}).`,
  );
}

/**
 * Sends a request to the API and returns the parsed JSON body.
 * Throws `ApiError` for network failures and non-2xx responses.
 */
export async function apiRequest<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await send(path, init, "application/json");
  const body: unknown =
    response.status === 204 ? undefined : await response.json().catch(() => null);
  if (!response.ok) throw errorFrom(response, body);
  return body as TResponse;
}

/**
 * Sends a request whose response is a stream of Server-Sent Events and returns its body.
 * Errors before the stream starts (validation, rate limit) throw `ApiError` as usual.
 */
export async function apiEventStream(
  path: string,
  init?: RequestInit,
): Promise<ReadableStream<Uint8Array>> {
  const response = await send(path, init, "text/event-stream");
  if (!response.ok) {
    throw errorFrom(response, await response.json().catch(() => null));
  }
  if (response.body === null) {
    throw new ApiError(response.status, "unexpected_error", "The server sent an empty response.");
  }
  return response.body;
}

/** Request options for a JSON body. */
export function jsonBody(data: unknown): Pick<RequestInit, "body" | "headers"> {
  return {
    body: JSON.stringify(data),
    headers: { "Content-Type": "application/json" },
  };
}
