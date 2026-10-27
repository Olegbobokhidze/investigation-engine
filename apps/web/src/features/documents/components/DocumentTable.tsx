import clsx from "clsx";
import { Lock, RefreshCw, Trash2 } from "lucide-react";
import { useRef } from "react";

import { acceptedFileTypes } from "@/shared/fileTypes";
import { Badge } from "@/shared/ui/Badge";
import { FileTypeTag } from "@/shared/ui/FileTypeTag";
import { IconButton } from "@/shared/ui/IconButton";

import type { CorpusDocument } from "../types";

interface DocumentTableProps {
  /** Null while the first page loads: the table shows placeholder rows. */
  documents: CorpusDocument[] | null;
  /** A new search or page is loading; the rows shown are the previous ones. */
  isRefreshing: boolean;
  onReplace: (corpusDocument: CorpusDocument, file: File) => void;
  onDelete: (corpusDocument: CorpusDocument) => void;
  /** Id of the document a replace or delete is running for. */
  busyDocumentId: string | null;
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });

const placeholderRowCount = 8;

export function DocumentTable({
  documents,
  isRefreshing,
  onReplace,
  onDelete,
  busyDocumentId,
}: DocumentTableProps) {
  if (documents?.length === 0) {
    return (
      <p className="rounded-2xl border border-border bg-surface px-6 py-10 text-center text-md text-ink-muted">
        No documents match your search.
      </p>
    );
  }

  return (
    // Shrinks to the space its parent gives it and scrolls inside; the header row stays visible.
    <div
      aria-busy={documents === null || isRefreshing}
      className="min-h-0 overflow-auto rounded-2xl border border-border bg-surface"
    >
      <table className="w-full border-collapse">
        <thead className="sticky top-0 z-10 bg-surface shadow-[inset_0_-1px_0_var(--color-border)]">
          <tr className="text-left text-xs whitespace-nowrap text-ink-muted">
            <th className="py-3 pr-4 pl-6 font-medium">Document</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 text-right font-medium">Chunks</th>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Added</th>
            <th className="px-4 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody
          className={clsx(
            "transition-opacity duration-150",
            isRefreshing && "opacity-50 motion-reduce:opacity-70",
          )}
        >
          {documents === null
            ? Array.from({ length: placeholderRowCount }, (_, index) => (
                <PlaceholderRow key={index} />
              ))
            : documents.map((corpusDocument) => (
                <DocumentRow
                  key={corpusDocument.id}
                  corpusDocument={corpusDocument}
                  onReplace={onReplace}
                  onDelete={onDelete}
                  isBusy={busyDocumentId === corpusDocument.id}
                />
              ))}
        </tbody>
      </table>
    </div>
  );
}

interface PlaceholderBarProps {
  /** Size and placement of the bar. */
  className: string;
}

/** A grey bar the size of the content it stands in for. */
function PlaceholderBar({ className }: PlaceholderBarProps) {
  return (
    <span
      className={clsx(
        "block animate-pulse rounded-md bg-subtle-strong motion-reduce:animate-none",
        className,
      )}
    />
  );
}

/** Same cells and padding as DocumentRow, so the table doesn't jump when the rows arrive. */
function PlaceholderRow() {
  return (
    <tr aria-hidden className="border-b border-border-subtle last:border-b-0">
      <td className="min-w-75 py-3 pr-4 pl-6">
        <div className="flex flex-col gap-1.5 py-0.5">
          <PlaceholderBar className="h-4 w-56" />
          <PlaceholderBar className="h-3 w-36" />
        </div>
      </td>
      <td className="px-4 py-3">
        <PlaceholderBar className="h-5 w-10" />
      </td>
      <td className="px-4 py-3">
        <PlaceholderBar className="ml-auto h-4 w-6" />
      </td>
      <td className="px-4 py-3">
        <PlaceholderBar className="h-5 w-18" />
      </td>
      <td className="px-4 py-3">
        <PlaceholderBar className="h-4 w-22" />
      </td>
      <td className="w-30 px-4 py-3" />
    </tr>
  );
}

interface DocumentRowProps {
  corpusDocument: CorpusDocument;
  onReplace: (corpusDocument: CorpusDocument, file: File) => void;
  onDelete: (corpusDocument: CorpusDocument) => void;
  isBusy: boolean;
}

function DocumentRow({ corpusDocument, onReplace, onDelete, isBusy }: DocumentRowProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isUpload = corpusDocument.origin === "upload";

  return (
    <tr className="border-b border-border-subtle text-md transition-colors last:border-b-0 hover:bg-surface-hover">
      <td className="min-w-75 py-3 pr-4 pl-6">
        <div className="flex flex-col gap-0.5">
          <span className="font-medium">{corpusDocument.title}</span>
          <span className="font-mono text-xs text-ink-muted">{corpusDocument.id}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <FileTypeTag fileType={corpusDocument.fileType} />
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm text-ink-secondary">
        {corpusDocument.chunkCount}
      </td>
      <td className="px-4 py-3">
        {isUpload ? (
          <Badge tone="accent">Uploaded</Badge>
        ) : (
          <Badge tone="neutral" icon={Lock}>
            Dataset
          </Badge>
        )}
      </td>
      <td className="px-4 py-3 text-sm whitespace-nowrap text-ink-secondary">
        {dateFormat.format(new Date(corpusDocument.createdAt))}
      </td>
      <td className="w-30 px-4 py-3">
        {isUpload && (
          <div className="flex justify-end gap-0.5">
            <IconButton
              label={`Replace ${corpusDocument.title}`}
              disabled={isBusy}
              onClick={() => fileInputRef.current?.click()}
            >
              <RefreshCw aria-hidden className="size-4.5" />
            </IconButton>
            <IconButton
              label={`Delete ${corpusDocument.title}`}
              tone="danger"
              disabled={isBusy}
              onClick={() => {
                onDelete(corpusDocument);
              }}
            >
              <Trash2 aria-hidden className="size-4.5" />
            </IconButton>
            <input
              ref={fileInputRef}
              type="file"
              accept={acceptedFileTypes}
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onReplace(corpusDocument, file);
                event.target.value = "";
              }}
            />
          </div>
        )}
      </td>
    </tr>
  );
}
