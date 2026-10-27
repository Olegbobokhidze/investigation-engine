import { describe, expect, it } from "vitest";

import { readServerSentEvents, type ServerSentEvent } from "./serverSentEvents";

/** A response body that arrives in the given chunks, as a network would deliver it. */
function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>): Promise<ServerSentEvent[]> {
  const events: ServerSentEvent[] = [];
  for await (const event of readServerSentEvents(body)) events.push(event);
  return events;
}

describe("readServerSentEvents", () => {
  it("parses named events separated by blank lines", async () => {
    const events = await collect(
      streamOf('event: step\ndata: {"n":1}\n\nevent: result\ndata: {"n":2}\n\n'),
    );

    expect(events).toEqual([
      { event: "step", data: '{"n":1}' },
      { event: "result", data: '{"n":2}' },
    ]);
  });

  it("joins an event split across network chunks", async () => {
    const events = await collect(streamOf("event: st", 'ep\ndata: {"n"', ":1}\n", "\n"));

    expect(events).toEqual([{ event: "step", data: '{"n":1}' }]);
  });

  it("ignores an unfinished event at the end of the stream", async () => {
    const events = await collect(streamOf('event: step\ndata: {"n":1}\n\nevent: res'));

    expect(events).toHaveLength(1);
  });
});
