import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import {
  ApiError,
  apiEventStream,
  apiRequest,
  isErrorEnvelope,
  jsonBody,
} from "@/shared/api/client";
import { readServerSentEvents } from "@/shared/api/serverSentEvents";

import type {
  CreateInvestigationRequest,
  Investigation,
  InvestigationStep,
  InvestigationStreamEvent,
} from "./types";

export function createInvestigation(request: CreateInvestigationRequest): Promise<Investigation> {
  return apiRequest("/investigations", { method: "POST", ...jsonBody(request) });
}

/**
 * Runs an investigation over `POST /investigations/stream`, calling `onStep` as each step
 * arrives, and resolves with the final investigation.
 */
export async function streamInvestigation(
  request: CreateInvestigationRequest,
  onStep: (step: InvestigationStep) => void,
): Promise<Investigation> {
  const body = await apiEventStream("/investigations/stream", {
    method: "POST",
    ...jsonBody(request),
  });
  for await (const { event, data } of readServerSentEvents(body)) {
    const message = { event, data: JSON.parse(data) as unknown } as InvestigationStreamEvent;
    if (message.event === "step") onStep(message.data);
    else if (message.event === "result") return message.data;
    else if (isErrorEnvelope(message.data)) {
      throw new ApiError(200, message.data.error.code, message.data.error.message);
    }
  }
  throw new ApiError(
    0,
    "stream_interrupted",
    "The connection closed before the investigation finished. Please try again.",
  );
}

/** An investigation whose steps are shown while it runs (`steps`), then its result. */
export function useInvestigationStream() {
  const [steps, setSteps] = useState<InvestigationStep[]>([]);
  const mutation = useMutation({
    mutationFn: (request: CreateInvestigationRequest) => {
      setSteps([]);
      return streamInvestigation(request, (step) => {
        setSteps((previous) => [...previous, step]);
      });
    },
  });
  return { ...mutation, steps };
}
