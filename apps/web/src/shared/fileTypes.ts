/** File formats the backend can ingest. */
export type FileType = "pdf" | "docx" | "md" | "txt";

export const fileTypeLabels: Record<FileType, string> = {
  pdf: "PDF",
  docx: "DOCX",
  md: "MD",
  txt: "TXT",
};

/** Value for a file input's `accept` attribute. */
export const acceptedFileTypes = ".pdf,.docx,.md,.markdown,.txt";
