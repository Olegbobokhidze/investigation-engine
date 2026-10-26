import clsx from "clsx";
import { LoaderCircle, Upload } from "lucide-react";
import { useRef, useState, type DragEvent, type ReactNode } from "react";

import { acceptedFileTypes } from "@/shared/fileTypes";
import { Badge } from "@/shared/ui/Badge";

interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  /** Files of the upload in progress; empty when idle. */
  uploadingFiles: File[];
  /** Rendered under the drop area when idle, e.g. the results of the last upload. */
  children?: ReactNode;
}

export function UploadDropzone({ onFilesSelected, uploadingFiles, children }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const isUploading = uploadingFiles.length > 0;

  function selectFiles(fileList: FileList | null) {
    const files = Array.from(fileList ?? []);
    if (files.length > 0) onFilesSelected(files);
  }

  function handleDragOver(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (!isUploading) selectFiles(event.dataTransfer.files);
  }

  return (
    <section
      aria-label="Upload documents"
      aria-busy={isUploading}
      onDragOver={handleDragOver}
      onDragLeave={() => {
        setIsDragging(false);
      }}
      onDrop={handleDrop}
      className={clsx(
        "relative flex flex-col gap-4 overflow-hidden rounded-2xl border-[1.5px] border-dashed px-6 py-5.5 transition-colors",
        isUploading || isDragging
          ? "border-accent bg-accent-soft/60"
          : "border-border-dashed bg-surface",
      )}
    >
      <div className="flex flex-wrap items-center gap-5">
        <span className="inline-flex size-12 items-center justify-center rounded-xl bg-accent-soft text-accent">
          {isUploading ? (
            <LoaderCircle
              aria-hidden
              className="size-5.5 animate-spin motion-reduce:animate-none"
            />
          ) : (
            <Upload aria-hidden className="size-5.5" />
          )}
        </span>
        <div className="flex flex-[1_1_260px] flex-col gap-1">
          <span className="text-md font-medium">
            {isUploading ? (
              `Uploading and indexing ${String(uploadingFiles.length)} ${uploadingFiles.length === 1 ? "file" : "files"}…`
            ) : (
              <>
                Drop files here or{" "}
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="cursor-pointer font-medium text-accent underline underline-offset-3 focus-ring"
                >
                  browse
                </button>
              </>
            )}
          </span>
          <span className="text-sm text-ink-muted">
            {isUploading
              ? "Extracting text, splitting it into chunks and embedding them. Large files take a moment."
              : "PDF, DOCX, Markdown or TXT. Files that are already indexed are skipped."}
          </span>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={acceptedFileTypes}
        className="hidden"
        onChange={(event) => {
          selectFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {isUploading ? (
        <ul
          aria-label="Files being uploaded"
          className="flex flex-col gap-2.5 border-t border-accent-border pt-3"
        >
          {uploadingFiles.map((file, index) => (
            <li
              // A file name can repeat within one upload, so the position is part of the key.
              key={`${String(index)}-${file.name}`}
              className="flex flex-wrap items-center gap-x-2.5 gap-y-2 text-sm"
            >
              <span className="font-medium break-all">{file.name}</span>
              <Badge tone="accent" icon={LoaderCircle} isSpinning className="ml-auto">
                Indexing…
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        children
      )}

      {isUploading && (
        <div
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-0.75 overflow-hidden bg-accent/10"
        >
          <div className="h-full w-2/5 animate-indeterminate rounded-full bg-accent motion-reduce:animate-none" />
        </div>
      )}
    </section>
  );
}
