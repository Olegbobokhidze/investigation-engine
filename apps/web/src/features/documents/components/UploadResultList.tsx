import { Badge, type BadgeTone } from "@/shared/ui/Badge";

import type { UploadResult } from "../types";

interface UploadResultListProps {
  results: UploadResult[];
}

function describeResult(result: UploadResult): { tone: BadgeTone; text: string } {
  switch (result.status) {
    case "indexed": {
      const { chunkCount } = result.document;
      return {
        tone: "success",
        text: `Indexed · ${String(chunkCount)} ${chunkCount === 1 ? "chunk" : "chunks"}`,
      };
    }
    case "duplicate":
      return { tone: "neutral", text: `Skipped · same content as ${result.duplicateOfId}` };
    case "failed":
      return { tone: "danger", text: `Failed · ${result.error.message}` };
  }
}

export function UploadResultList({ results }: UploadResultListProps) {
  return (
    <ul
      aria-label="Upload results"
      aria-live="polite"
      className="flex flex-col gap-2.5 border-t border-border-subtle pt-3"
    >
      {results.map((result, index) => {
        const { tone, text } = describeResult(result);
        return (
          <li
            // A file name can repeat within one upload, so the position is part of the key.
            key={`${String(index)}-${result.fileName}`}
            className="flex flex-wrap items-center gap-x-2.5 gap-y-2 text-sm"
          >
            <span className="font-medium break-all">{result.fileName}</span>
            <Badge tone={tone} className="ml-auto">
              {text}
            </Badge>
          </li>
        );
      })}
    </ul>
  );
}
