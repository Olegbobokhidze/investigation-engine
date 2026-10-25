import type { FileType } from "@/shared/fileTypes";

/** Where a document came from. Dataset documents are read-only. */
export type DocumentOrigin = "dataset" | "upload";

export interface CorpusDocument {
  id: string;
  title: string;
  fileType: FileType;
  chunkCount: number;
  origin: DocumentOrigin;
  /** ISO 8601 timestamp. */
  createdAt: string;
}

export interface DocumentPage {
  items: CorpusDocument[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DocumentListParams {
  search: string;
  page: number;
}

/** The outcome for one file in an upload: each file succeeds or fails on its own. */
export type UploadResult =
  | { fileName: string; status: "indexed"; document: CorpusDocument }
  | { fileName: string; status: "duplicate"; duplicateOfId: string }
  | { fileName: string; status: "failed"; error: { code: string; message: string } };

export interface UploadResponse {
  results: UploadResult[];
}
