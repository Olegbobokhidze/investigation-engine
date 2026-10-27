import { delay, http, HttpResponse } from "msw";

import type { CorpusDocument, DocumentPage, UploadResult } from "@/features/documents/types";
import type {
  CreateInvestigationRequest,
  Investigation,
  InvestigationStreamEvent,
} from "@/features/investigations/types";
import { env } from "@/shared/config/env";
import type { FileType } from "@/shared/fileTypes";

import {
  answeredInvestigation,
  initialDocuments,
  insufficientEvidenceInvestigation,
} from "./fixtures";

/** In-memory stand-in for the backend's document store; resets on page reload. */
let documents = [...initialDocuments];

const apiUrl = (path: string) => `${env.apiBaseUrl}${path}`;

const fileTypesByExtension: Record<string, FileType> = {
  pdf: "pdf",
  docx: "docx",
  md: "md",
  markdown: "md",
  txt: "txt",
};

function fileTypeOf(fileName: string): FileType | undefined {
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  return fileTypesByExtension[extension];
}

function errorResponse(status: number, code: string, message: string) {
  return HttpResponse.json({ error: { code, message } }, { status });
}

function randomId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().slice(0, 6)}`;
}

/** Roughly one chunk per 1,500 bytes, like the backend's default chunk size. */
function estimateChunkCount(file: File): number {
  return Math.max(1, Math.ceil(file.size / 1500));
}

function findEditableDocument(id: string) {
  const corpusDocument = documents.find((candidate) => candidate.id === id);
  if (!corpusDocument) {
    return { error: errorResponse(404, "not_found", `Document ${id} does not exist.`) };
  }
  if (corpusDocument.origin === "dataset") {
    return {
      error: errorResponse(403, "forbidden", "Dataset documents are read-only."),
    };
  }
  return { corpusDocument };
}

function indexFile(file: File): UploadResult {
  const fileType = fileTypeOf(file.name);
  if (!fileType) {
    return {
      fileName: file.name,
      status: "failed",
      error: { code: "unsupported_format", message: "unsupported file type" },
    };
  }
  if (file.size === 0) {
    return {
      fileName: file.name,
      status: "failed",
      error: { code: "empty_document", message: "no readable text" },
    };
  }
  const duplicate = documents.find((candidate) => candidate.title === file.name);
  if (duplicate) {
    return { fileName: file.name, status: "duplicate", duplicateOfId: duplicate.id };
  }

  const corpusDocument: CorpusDocument = {
    id: randomId("doc"),
    title: file.name,
    fileType,
    chunkCount: estimateChunkCount(file),
    origin: "upload",
    createdAt: new Date().toISOString(),
  };
  documents = [corpusDocument, ...documents];
  return { fileName: file.name, status: "indexed", document: corpusDocument };
}

export const documentHandlers = [
  http.get(apiUrl("/documents"), async ({ request }) => {
    await delay(300);
    const params = new URL(request.url).searchParams;
    const page = Number(params.get("page") ?? "1");
    const pageSize = Number(params.get("pageSize") ?? "20");
    const search = (params.get("search") ?? "").toLowerCase();

    const matching = documents.filter(
      (candidate) =>
        candidate.title.toLowerCase().includes(search) || candidate.id.includes(search),
    );
    const body: DocumentPage = {
      items: matching.slice((page - 1) * pageSize, page * pageSize),
      total: matching.length,
      page,
      pageSize,
    };
    return HttpResponse.json(body);
  }),

  http.post(apiUrl("/documents"), async ({ request }) => {
    await delay(1200);
    const formData = await request.formData();
    const files = formData.getAll("files").filter((entry) => entry instanceof File);
    return HttpResponse.json({ results: files.map(indexFile) });
  }),

  http.put(apiUrl("/documents/:id"), async ({ params, request }) => {
    await delay(900);
    const { corpusDocument, error } = findEditableDocument(String(params.id));
    if (error) return error;

    const file = (await request.formData()).get("file");
    if (!(file instanceof File)) {
      return errorResponse(422, "invalid_input", "Attach the replacement file.");
    }
    const fileType = fileTypeOf(file.name);
    if (!fileType) {
      return errorResponse(422, "unsupported_format", "Use a PDF, DOCX, Markdown or TXT file.");
    }

    const replaced: CorpusDocument = {
      ...corpusDocument,
      title: file.name,
      fileType,
      chunkCount: estimateChunkCount(file),
    };
    documents = documents.map((candidate) => (candidate.id === replaced.id ? replaced : candidate));
    return HttpResponse.json(replaced);
  }),

  http.delete(apiUrl("/documents/:id"), async ({ params }) => {
    await delay(400);
    const { corpusDocument, error } = findEditableDocument(String(params.id));
    if (error) return error;

    documents = documents.filter((candidate) => candidate.id !== corpusDocument.id);
    return new HttpResponse(null, { status: 204 });
  }),
];

function mockInvestigation(question: string): Investigation {
  const fixture = /refund/i.test(question)
    ? insufficientEvidenceInvestigation
    : answeredInvestigation;
  return { id: randomId("inv"), question, ...fixture };
}

/** One Server-Sent Event, formatted as the backend sends it. */
function serverSentEvent({ event, data }: InvestigationStreamEvent): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

export const investigationHandlers = [
  http.post(apiUrl("/investigations"), async ({ request }) => {
    await delay(1800);
    const { question } = (await request.json()) as CreateInvestigationRequest;
    return HttpResponse.json(mockInvestigation(question));
  }),

  // Sends the fixture's steps one by one, then the result, like the real stream.
  http.post(apiUrl("/investigations/stream"), async ({ request }) => {
    const { question } = (await request.json()) as CreateInvestigationRequest;
    const investigation = mockInvestigation(question);
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      async start(controller) {
        for (const step of investigation.steps) {
          await delay(500);
          controller.enqueue(encoder.encode(serverSentEvent({ event: "step", data: step })));
        }
        controller.enqueue(
          encoder.encode(serverSentEvent({ event: "result", data: investigation })),
        );
        controller.close();
      },
    });
    return new HttpResponse(body, { headers: { "Content-Type": "text/event-stream" } });
  }),
];
