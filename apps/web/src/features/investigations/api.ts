import { useMutation } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "@/shared/api/client";

import type { CreateInvestigationRequest, Investigation } from "./types";

export function createInvestigation(request: CreateInvestigationRequest): Promise<Investigation> {
  return apiRequest("/investigations", { method: "POST", ...jsonBody(request) });
}

export function useCreateInvestigation() {
  return useMutation({ mutationFn: createInvestigation });
}
