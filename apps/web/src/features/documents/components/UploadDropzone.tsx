import clsx from "clsx";
import { Upload } from "lucide-react";
import { useRef, useState, type DragEvent, type ReactNode } from "react";

import { acceptedFileTypes } from "@/shared/fileTypes";

interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  isUploading: boolean;
  /** Rendered under the drop area, e.g. the results of the last upload. */
  children?: ReactNode;
}

export function UploadDropzone({ onFilesSelected, isUploading, children }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

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
      onDragOver={handleDragOver}
      onDragLeave={() => {
        setIsDragging(false);
      }}
      onDrop={handleDrop}
      className={clsx(
        "flex flex-col gap-4 rounded-2xl border-[1.5px] border-dashed bg-surface px-6 py-5.5 transition-colors",
        isDragging ? "border-accent bg-accent-soft" : "border-border-dashed",
      )}
    >
      <div className="flex flex-wrap items-center gap-5">
        <span className="inline-flex size-12 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <Upload aria-hidden className="size-5.5" />
        </span>
        <div className="flex flex-[1_1_260px] flex-col gap-1">
          <span className="text-md font-medium">
            {isUploading ? (
              "Uploading and indexing…"
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
            PDF, DOCX, Markdown or TXT. Files that are already indexed are skipped.
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
      {children}
    </section>
  );
}
