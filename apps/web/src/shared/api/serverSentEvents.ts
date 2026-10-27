/** One Server-Sent Event: its `event:` name and its `data:` text. */
export interface ServerSentEvent {
  event: string;
  data: string;
}

/**
 * Reads Server-Sent Events from a response body as they arrive. Events are separated by a
 * blank line; this backend sends one `event:` and one `data:` line per event.
 */
export async function* readServerSentEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader();
  // `stream: true` keeps a character split across two chunks intact.
  const decoder = new TextDecoder();
  let buffered = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });
      let boundary = buffered.indexOf("\n\n");
      while (boundary !== -1) {
        const event = parseEvent(buffered.slice(0, boundary));
        if (event) yield event;
        buffered = buffered.slice(boundary + 2);
        boundary = buffered.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseEvent(block: string): ServerSentEvent | undefined {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice("event:".length).trim();
    else if (line.startsWith("data:")) data.push(line.slice("data:".length).trimStart());
  }
  return data.length > 0 ? { event, data: data.join("\n") } : undefined;
}
