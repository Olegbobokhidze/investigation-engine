import type { FileType } from "@/shared/fileTypes";

/** `insufficient_evidence`: the documents don't support an answer, so none is given. */
export type InvestigationStatus = "answered" | "insufficient_evidence";

/** A passage the answer cites. `answer` and conflict summaries refer to it as `[number]`. */
export interface Source {
  number: number;
  documentId: string;
  documentTitle: string;
  fileType: FileType;
  excerpt: string;
}

/** Two or more sources that disagree. The summary cites them with `[number]` markers. */
export interface Conflict {
  summary: string;
}

/** One step the engine took: planning, a tool call, or verification. */
export interface InvestigationStep {
  title: string;
  detail: string;
  /** Short outcome, e.g. "8 results". */
  result: string | null;
}

export interface Investigation {
  id: string;
  question: string;
  status: InvestigationStatus;
  /** Paragraphs are separated by blank lines; citations are `[number]` markers. */
  answer: string;
  sources: Source[];
  conflicts: Conflict[];
  steps: InvestigationStep[];
}

export interface CreateInvestigationRequest {
  question: string;
}
